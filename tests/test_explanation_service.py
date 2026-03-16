from modules.ai.explanation_service import ExplanationService
from modules.domain.models import Question, QuestionAlternative


class FakeAiClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.last_prompt: str | None = None
        self.last_schema: dict[str, object] | None = None
        self.last_temperature: float | None = None

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: dict[str, object],
        temperature: float = 0.2,
    ) -> dict[str, object]:
        self.last_prompt = prompt
        self.last_schema = response_schema
        self.last_temperature = temperature
        return self.payload


def _build_question() -> Question:
    return Question(
        id_question=101,
        statement="Quanto e 3 + 4?",
        correct_answer=QuestionAlternative("7", None),
        wrong_answers=(
            QuestionAlternative("6", None),
            QuestionAlternative("8", "Ja existe."),
        ),
        subject="matematica",
        topic="aritmetica",
        difficulty="facil",
        source="seed",
    )


def test_build_prompt_includes_statement_and_all_alternatives() -> None:
    service = ExplanationService(FakeAiClient(payload={}))

    prompt = service.build_prompt(_build_question())

    assert "Quanto e 3 + 4?" in prompt
    assert "- 7" in prompt
    assert "- 6" in prompt
    assert "- 8" in prompt
    assert "Preserve cada `alternative_text` exatamente como foi fornecido." in prompt


def test_parse_response_reorders_wrong_answers_to_match_question_order() -> None:
    service = ExplanationService(FakeAiClient(payload={}))
    question = _build_question()

    parsed = service.parse_response(
        question,
        {
            "correct_answer": {
                "alternative_text": "7",
                "explanation": "Somar 3 com 4 resulta em 7.",
            },
            "wrong_answers": [
                {
                    "alternative_text": "8",
                    "explanation": "Isso soma uma unidade a mais.",
                },
                {
                    "alternative_text": "6",
                    "explanation": "Isso soma uma unidade a menos.",
                },
            ],
        },
    )

    assert parsed.correct_answer.explanation == "Somar 3 com 4 resulta em 7."
    assert [answer.alternative_text for answer in parsed.wrong_answers] == ["6", "8"]
    assert [answer.explanation for answer in parsed.wrong_answers] == [
        "Isso soma uma unidade a menos.",
        "Isso soma uma unidade a mais.",
    ]


def test_parse_response_rejects_unknown_alternative_text() -> None:
    service = ExplanationService(FakeAiClient(payload={}))

    try:
        service.parse_response(
            _build_question(),
            {
                "correct_answer": {
                    "alternative_text": "7",
                    "explanation": "Correta.",
                },
                "wrong_answers": [
                    {
                        "alternative_text": "9",
                        "explanation": "Errada.",
                    },
                    {
                        "alternative_text": "6",
                        "explanation": "Errada.",
                    },
                ],
            },
        )
    except ValueError as exc:
        assert str(exc) == "Gemini returned an unknown wrong alternative text."
    else:
        raise AssertionError("Expected ValueError for unknown wrong alternative text.")


def test_generate_explanations_calls_ai_client_and_merge_preserves_existing_text() -> None:
    ai_client = FakeAiClient(
        payload={
            "correct_answer": {
                "alternative_text": "7",
                "explanation": "Somar 3 com 4 resulta em 7.",
            },
            "wrong_answers": [
                {
                    "alternative_text": "6",
                    "explanation": "Faltou uma unidade.",
                },
                {
                    "alternative_text": "8",
                    "explanation": "Sobrou uma unidade.",
                },
            ],
        }
    )
    service = ExplanationService(ai_client)
    question = _build_question()

    generated = service.generate_explanations(question)
    merged = service.merge_missing_explanations(question, generated)

    assert ai_client.last_prompt is not None
    assert ai_client.last_schema is not None
    assert ai_client.last_temperature == 0.2
    assert merged.correct_answer.explanation == "Somar 3 com 4 resulta em 7."
    assert [answer.explanation for answer in merged.wrong_answers] == [
        "Faltou uma unidade.",
        "Ja existe.",
    ]
