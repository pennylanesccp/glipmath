from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

import pandas as pd

from modules.services.question_service import parse_question_bank_dataframe
from modules.utils.datetime_utils import to_iso_timestamp, utc_now
from modules.utils.normalization import clean_optional_text

QUESTION_AUTHORING_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "statement": {"type": "string"},
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
            "minItems": 3,
            "maxItems": 3,
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
    "required": ["statement", "correct_answer", "wrong_answers"],
}
DIFFICULTY_OPTIONS: tuple[tuple[str, str], ...] = (
    ("1_basico", "1. Básico"),
    ("2_facil", "2. Fácil"),
    ("3_medio", "3. Médio"),
    ("4_dificil", "4. Difícil"),
    ("5_avancado", "5. Avançado"),
)
DIFFICULTY_LABEL_BY_VALUE = {
    value: label
    for value, label in DIFFICULTY_OPTIONS
}
MANUAL_QUESTION_SOURCE = "espaco_professor_manual_v1"
AI_POLISHED_QUESTION_SOURCE = "espaco_professor_ai_v1"


class StructuredGenerationClient(Protocol):
    """Protocol for AI clients that can return structured JSON."""

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """Return one structured JSON payload."""


@dataclass(frozen=True, slots=True)
class AuthoringAlternativeDraft:
    """One editable alternative draft in the professor workspace."""

    alternative_text: str | None = None
    explanation: str | None = None


@dataclass(frozen=True, slots=True)
class QuestionAuthoringDraft:
    """One teacher-authored question draft before persistence."""

    project_key: str | None = None
    subject: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    statement: str | None = None
    correct_answer: AuthoringAlternativeDraft = AuthoringAlternativeDraft()
    wrong_answers: tuple[AuthoringAlternativeDraft, ...] = (
        AuthoringAlternativeDraft(),
        AuthoringAlternativeDraft(),
        AuthoringAlternativeDraft(),
    )


class QuestionAuthoringService:
    """Validate, polish, and serialize teacher-authored question drafts."""

    def __init__(self, ai_client: StructuredGenerationClient) -> None:
        self._ai_client = ai_client

    def build_prompt(self, draft: QuestionAuthoringDraft) -> str:
        """Build the Gemini prompt for polishing a teacher-authored draft."""

        guidance_lines = [
            f"- Projeto: {draft.project_key}" if draft.project_key else None,
            f"- Matéria: {draft.subject}" if draft.subject else None,
            f"- Tópico: {draft.topic}" if draft.topic else None,
            (
                f"- Dificuldade alvo: {format_difficulty_label(draft.difficulty)}"
                if draft.difficulty
                else None
            ),
        ]
        provided_fields = [
            f"Enunciado atual:\n{draft.statement}" if draft.statement else None,
            (
                "Alternativa correta sugerida:\n"
                f"- Texto: {draft.correct_answer.alternative_text}\n"
                f"- Explicação: {draft.correct_answer.explanation}"
                if draft.correct_answer.alternative_text or draft.correct_answer.explanation
                else None
            ),
        ]
        for index, wrong_answer in enumerate(draft.wrong_answers, start=1):
            if wrong_answer.alternative_text or wrong_answer.explanation:
                provided_fields.append(
                    f"Alternativa errada {index} sugerida:\n"
                    f"- Texto: {wrong_answer.alternative_text}\n"
                    f"- Explicação: {wrong_answer.explanation}"
                )

        metadata_block = "\n".join(line for line in guidance_lines if line) or "- Sem metadados fornecidos"
        hints_block = "\n\n".join(line for line in provided_fields if line) or "Nenhum rascunho textual adicional foi fornecido."

        return (
            "Você está ajudando um professor a montar uma questão de múltipla escolha para o GlipMath.\n"
            "Gere uma questão completa e bem escrita.\n"
            "Regras obrigatórias:\n"
            "- Retorne exatamente um enunciado, 1 alternativa correta e 3 alternativas erradas.\n"
            "- Cada alternativa deve ter uma explicação curta e didática.\n"
            "- As quatro alternativas devem ser distintas e plausíveis.\n"
            "- Use markdown quando isso ajudar, incluindo blocos de código se o contexto pedir.\n"
            "- Preserve a intenção do professor quando ele já tiver fornecido texto, mas você pode reescrever para melhorar clareza.\n"
            "- Se quase nada tiver sido preenchido, crie a questão usando apenas os metadados.\n"
            "- Use português do Brasil por padrão, a menos que o próprio rascunho indique claramente outro idioma.\n\n"
            f"Metadados obrigatórios:\n{metadata_block}\n\n"
            f"Rascunho fornecido pelo professor:\n{hints_block}\n"
        )

    def polish_draft(self, draft: QuestionAuthoringDraft) -> QuestionAuthoringDraft:
        """Generate one polished question draft from the current teacher hints."""

        payload = self._ai_client.generate_json(
            prompt=self.build_prompt(draft),
            response_schema=QUESTION_AUTHORING_RESPONSE_SCHEMA,
            temperature=0.4,
        )
        return self.parse_response(draft, payload)

    def parse_response(
        self,
        draft: QuestionAuthoringDraft,
        payload: dict[str, Any],
    ) -> QuestionAuthoringDraft:
        """Parse and validate the Gemini authoring payload."""

        if not isinstance(payload, dict):
            raise ValueError("Gemini payload must be an object.")

        statement = _require_text(payload.get("statement"), "statement")
        correct_answer = _parse_alternative(
            payload.get("correct_answer"),
            field_name="correct_answer",
        )
        wrong_answers_payload = payload.get("wrong_answers")
        if not isinstance(wrong_answers_payload, list) or len(wrong_answers_payload) != 3:
            raise ValueError("wrong_answers must contain exactly 3 alternatives.")

        wrong_answers = tuple(
            _parse_alternative(item, field_name=f"wrong_answers[{index}]")
            for index, item in enumerate(wrong_answers_payload)
        )
        _ensure_unique_alternatives(correct_answer, wrong_answers)

        return QuestionAuthoringDraft(
            project_key=draft.project_key,
            subject=draft.subject,
            topic=draft.topic,
            difficulty=draft.difficulty,
            statement=statement,
            correct_answer=correct_answer,
            wrong_answers=wrong_answers,
        )


def format_difficulty_label(value: str | None) -> str:
    """Return the friendly label for one normalized difficulty value."""

    normalized_value = normalize_difficulty_value(value)
    if normalized_value is None:
        return ""
    return DIFFICULTY_LABEL_BY_VALUE.get(normalized_value, normalized_value)


def normalize_difficulty_value(value: str | None) -> str | None:
    """Normalize one difficulty option from widget state."""

    normalized_value = clean_optional_text(value)
    if not normalized_value:
        return None
    normalized_value = normalized_value.lower()
    return normalized_value if normalized_value in DIFFICULTY_LABEL_BY_VALUE else None


def validate_draft_for_ai(draft: QuestionAuthoringDraft) -> list[str]:
    """Return validation issues for the AI polishing workflow."""

    issues: list[str] = []
    if not clean_optional_text(draft.project_key):
        issues.append("Selecione um projeto para usar o polimento com IA.")
    if not clean_optional_text(draft.subject):
        issues.append("Preencha a matéria para usar o polimento com IA.")
    if not clean_optional_text(draft.topic):
        issues.append("Preencha o tópico para usar o polimento com IA.")
    if normalize_difficulty_value(draft.difficulty) is None:
        issues.append("Selecione uma dificuldade válida para usar o polimento com IA.")
    return issues


def validate_draft_for_submission(draft: QuestionAuthoringDraft) -> list[str]:
    """Return validation issues for manual BigQuery submission."""

    issues = validate_draft_for_ai(draft)
    if not clean_optional_text(draft.statement):
        issues.append("Preencha o enunciado antes de enviar.")
    if not clean_optional_text(draft.correct_answer.alternative_text):
        issues.append("Preencha a alternativa correta antes de enviar.")
    if not clean_optional_text(draft.correct_answer.explanation):
        issues.append("Preencha a explicação da alternativa correta antes de enviar.")

    for index, wrong_answer in enumerate(draft.wrong_answers, start=1):
        if not clean_optional_text(wrong_answer.alternative_text):
            issues.append(f"Preencha a alternativa errada {index} antes de enviar.")
        if not clean_optional_text(wrong_answer.explanation):
            issues.append(f"Preencha a explicação da alternativa errada {index} antes de enviar.")
    return issues


def build_question_row_from_draft(
    draft: QuestionAuthoringDraft,
    *,
    source: str,
) -> dict[str, object]:
    """Build one canonical question-bank row from a validated authoring draft."""

    generated_at = utc_now()
    row = {
        "id_question": generate_question_id(),
        "statement": _require_text(draft.statement, "statement"),
        "correct_answer": {
            "alternative_text": _require_text(
                draft.correct_answer.alternative_text,
                "correct_answer.alternative_text",
            ),
            "explanation": _require_text(
                draft.correct_answer.explanation,
                "correct_answer.explanation",
            ),
        },
        "wrong_answers": [
            {
                "alternative_text": _require_text(
                    wrong_answer.alternative_text,
                    f"wrong_answers[{index}].alternative_text",
                ),
                "explanation": _require_text(
                    wrong_answer.explanation,
                    f"wrong_answers[{index}].explanation",
                ),
            }
            for index, wrong_answer in enumerate(draft.wrong_answers)
        ],
        "subject": _require_text(draft.subject, "subject"),
        "topic": _require_text(draft.topic, "topic"),
        "difficulty": _require_text(
            normalize_difficulty_value(draft.difficulty),
            "difficulty",
        ),
        "source": _require_text(source, "source"),
        "cohort_key": _require_text(draft.project_key, "project_key"),
        "is_active": True,
        "created_at_utc": to_iso_timestamp(generated_at),
        "updated_at_utc": to_iso_timestamp(generated_at),
    }
    questions, issues = parse_question_bank_dataframe(pd.DataFrame([row]))
    if not questions:
        issue_text = issues[0] if issues else "question row is invalid."
        raise ValueError(issue_text)
    return row


def generate_question_id() -> int:
    """Generate a positive INT64-compatible question identifier."""

    return int.from_bytes(uuid4().bytes[:8], "big") & 0x7FFFFFFFFFFFFFFF


def build_empty_draft(project_key: str | None = None) -> QuestionAuthoringDraft:
    """Return an empty authoring draft for UI initialization."""

    return QuestionAuthoringDraft(project_key=clean_optional_text(project_key))


def _parse_alternative(value: Any, *, field_name: str) -> AuthoringAlternativeDraft:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    return AuthoringAlternativeDraft(
        alternative_text=_require_text(
            value.get("alternative_text"),
            f"{field_name}.alternative_text",
        ),
        explanation=_require_text(
            value.get("explanation"),
            f"{field_name}.explanation",
        ),
    )


def _ensure_unique_alternatives(
    correct_answer: AuthoringAlternativeDraft,
    wrong_answers: tuple[AuthoringAlternativeDraft, ...],
) -> None:
    seen: set[str] = set()
    all_answers = (correct_answer, *wrong_answers)
    for answer in all_answers:
        normalized_text = _require_text(answer.alternative_text, "alternative_text").casefold()
        if normalized_text in seen:
            raise ValueError("alternative_text values must be unique within a question.")
        seen.add(normalized_text)


def _require_text(value: Any, field_name: str) -> str:
    text = clean_optional_text(value)
    if not text:
        raise ValueError(f"{field_name} cannot be blank.")
    return text
