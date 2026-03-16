from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from modules.domain.models import Question, QuestionAlternative
from modules.utils.normalization import clean_optional_text

EXPLANATION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "correct_answer": {
            "type": "object",
            "properties": {
                "alternative_text": {"type": "string"},
                "explanation": {"type": "string"},
            },
            "required": ["alternative_text", "explanation"],
        },
        "wrong_answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "alternative_text": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["alternative_text", "explanation"],
            },
        },
    },
    "required": ["correct_answer", "wrong_answers"],
}


class StructuredGenerationClient(Protocol):
    """Protocol for AI clients that can return structured JSON."""

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Return one structured JSON payload."""


@dataclass(frozen=True, slots=True)
class QuestionExplanationUpdate:
    """Generated explanations for one question."""

    correct_answer: QuestionAlternative
    wrong_answers: tuple[QuestionAlternative, ...]


class ExplanationService:
    """Generate and validate offline explanation enrichments for question rows."""

    def __init__(self, ai_client: StructuredGenerationClient) -> None:
        self._ai_client = ai_client

    def build_prompt(self, question: Question) -> str:
        """Build the Gemini prompt for one question."""

        metadata_lines = [
            f"- Materia: {question.subject}" if question.subject else None,
            f"- Topico: {question.topic}" if question.topic else None,
            f"- Dificuldade: {question.difficulty}" if question.difficulty else None,
            f"- Fonte: {question.source}" if question.source else None,
        ]
        wrong_answers_block = "\n".join(
            f"- {wrong_answer.alternative_text}" for wrong_answer in question.wrong_answers
        )
        metadata_block = "\n".join(
            line for line in metadata_lines if line
        ) or "- Nenhum metadado adicional"

        return (
            "Voce esta enriquecendo um banco de questoes de multipla escolha para um app "
            "educacional em portugues do Brasil.\n"
            "Gere explicacoes curtas, claras e didaticas em portugues-BR.\n"
            "Regras obrigatorias:\n"
            "- Preserve cada `alternative_text` exatamente como foi fornecido.\n"
            "- `correct_answer.explanation` deve explicar por que a alternativa correta esta certa.\n"
            "- Cada item de `wrong_answers` deve explicar por que aquela alternativa esta errada.\n"
            "- Nao use markdown, listas numeradas ou texto fora do JSON estruturado.\n"
            "- Mantenha cada explicacao em 1 a 3 frases curtas.\n\n"
            f"Enunciado:\n{question.statement}\n\n"
            f"Metadados:\n{metadata_block}\n\n"
            f"Alternativa correta:\n- {question.correct_answer.alternative_text}\n\n"
            f"Alternativas erradas:\n{wrong_answers_block}\n"
        )

    def generate_explanations(self, question: Question) -> QuestionExplanationUpdate:
        """Generate explanations for one question and validate the structured response."""

        payload = self._ai_client.generate_json(
            prompt=self.build_prompt(question),
            response_schema=EXPLANATION_RESPONSE_SCHEMA,
            temperature=0.2,
        )
        return self.parse_response(question, payload)

    def parse_response(
        self,
        question: Question,
        payload: dict[str, Any],
    ) -> QuestionExplanationUpdate:
        """Parse and validate the Gemini explanation payload."""

        if not isinstance(payload, dict):
            raise ValueError("Gemini payload must be an object.")

        correct_mapping = _require_mapping(payload.get("correct_answer"), "correct_answer")
        correct_text = _require_text(
            correct_mapping.get("alternative_text"),
            "correct_answer.alternative_text",
        )
        if _normalize_alternative_text(correct_text) != _normalize_alternative_text(
            question.correct_answer.alternative_text
        ):
            raise ValueError("Gemini returned a mismatched correct alternative text.")

        generated_correct = QuestionAlternative(
            alternative_text=question.correct_answer.alternative_text,
            explanation=_require_text(
                correct_mapping.get("explanation"),
                "correct_answer.explanation",
            ),
        )

        wrong_payload = payload.get("wrong_answers")
        if not isinstance(wrong_payload, list):
            raise ValueError("wrong_answers must be a list.")

        expected_wrong_answers = {
            _normalize_alternative_text(answer.alternative_text): answer.alternative_text
            for answer in question.wrong_answers
        }
        generated_wrong_answers: dict[str, QuestionAlternative] = {}
        for index, item in enumerate(wrong_payload):
            wrong_mapping = _require_mapping(item, f"wrong_answers[{index}]")
            alternative_text = _require_text(
                wrong_mapping.get("alternative_text"),
                f"wrong_answers[{index}].alternative_text",
            )
            normalized_text = _normalize_alternative_text(alternative_text)
            if normalized_text not in expected_wrong_answers:
                raise ValueError("Gemini returned an unknown wrong alternative text.")
            if normalized_text in generated_wrong_answers:
                raise ValueError("Gemini returned duplicate wrong alternative texts.")

            generated_wrong_answers[normalized_text] = QuestionAlternative(
                alternative_text=expected_wrong_answers[normalized_text],
                explanation=_require_text(
                    wrong_mapping.get("explanation"),
                    f"wrong_answers[{index}].explanation",
                ),
            )

        missing_wrong_answers = set(expected_wrong_answers) - set(generated_wrong_answers)
        if missing_wrong_answers:
            raise ValueError("Gemini did not return explanations for every wrong alternative.")

        ordered_wrong_answers = tuple(
            generated_wrong_answers[_normalize_alternative_text(answer.alternative_text)]
            for answer in question.wrong_answers
        )

        return QuestionExplanationUpdate(
            correct_answer=generated_correct,
            wrong_answers=ordered_wrong_answers,
        )

    def merge_missing_explanations(
        self,
        question: Question,
        generated: QuestionExplanationUpdate,
    ) -> QuestionExplanationUpdate:
        """Preserve existing explanations and fill only the missing ones."""

        generated_wrong_by_key = {
            _normalize_alternative_text(answer.alternative_text): answer
            for answer in generated.wrong_answers
        }
        merged_correct = QuestionAlternative(
            alternative_text=question.correct_answer.alternative_text,
            explanation=question.correct_answer.explanation
            or generated.correct_answer.explanation,
        )
        merged_wrong_answers = tuple(
            QuestionAlternative(
                alternative_text=wrong_answer.alternative_text,
                explanation=wrong_answer.explanation
                or generated_wrong_by_key[
                    _normalize_alternative_text(wrong_answer.alternative_text)
                ].explanation,
            )
            for wrong_answer in question.wrong_answers
        )

        return QuestionExplanationUpdate(
            correct_answer=merged_correct,
            wrong_answers=merged_wrong_answers,
        )


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    return value


def _require_text(value: Any, field_name: str) -> str:
    text = clean_optional_text(value)
    if not text:
        raise ValueError(f"{field_name} cannot be blank.")
    return text


def _normalize_alternative_text(value: str) -> str:
    normalized = clean_optional_text(value)
    return (normalized or "").casefold()
