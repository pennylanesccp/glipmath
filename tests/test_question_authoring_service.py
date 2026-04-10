from modules.services.question_authoring_service import (
    AI_POLISHED_QUESTION_SOURCE,
    AuthoringAlternativeDraft,
    QuestionAuthoringDraft,
    QuestionAuthoringService,
    build_question_row_from_draft,
    format_difficulty_label,
    normalize_difficulty_value,
    validate_draft_for_ai,
    validate_draft_for_submission,
)


class FakeGenerationClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.prompts: list[str] = []

    def generate_json(self, *, prompt: str, response_schema: dict[str, object], temperature: float = 0.4) -> dict[str, object]:
        self.prompts.append(prompt)
        assert response_schema["type"] == "object"
        assert temperature == 0.4
        return self.payload


def test_validate_draft_for_ai_requires_only_metadata() -> None:
    draft = QuestionAuthoringDraft()

    issues = validate_draft_for_ai(draft)

    assert issues == [
        "Selecione um projeto para usar o polimento com IA.",
        "Preencha a matéria para usar o polimento com IA.",
        "Preencha o tópico para usar o polimento com IA.",
        "Selecione uma dificuldade válida para usar o polimento com IA.",
    ]


def test_validate_draft_for_submission_requires_full_question_content() -> None:
    draft = QuestionAuthoringDraft(
        project_key="crescer_e_conectar",
        subject="Matemática",
        topic="divisão",
        difficulty="1_basico",
    )

    issues = validate_draft_for_submission(draft)

    assert "Preencha o enunciado antes de enviar." in issues
    assert "Preencha a alternativa correta antes de enviar." in issues
    assert "Preencha a explicação da alternativa correta antes de enviar." in issues
    assert "Preencha a alternativa errada 1 antes de enviar." in issues
    assert "Preencha a explicação da alternativa errada 3 antes de enviar." in issues


def test_build_question_row_from_draft_returns_canonical_question_bank_row() -> None:
    draft = QuestionAuthoringDraft(
        project_key="crescer_e_conectar",
        subject="Matemática",
        topic="divisão",
        difficulty="2_facil",
        statement="João dividiu 12 figurinhas em 3 grupos iguais. Quantas ficaram em cada grupo?",
        correct_answer=AuthoringAlternativeDraft(
            alternative_text="4",
            explanation="12 dividido por 3 é igual a 4.",
        ),
        wrong_answers=(
            AuthoringAlternativeDraft("3", "3 x 3 é 9, então faltam figurinhas."),
            AuthoringAlternativeDraft("5", "5 x 3 é 15, então passou do total."),
            AuthoringAlternativeDraft("6", "6 x 3 é 18, então passou do total."),
        ),
    )

    row = build_question_row_from_draft(
        draft,
        source=AI_POLISHED_QUESTION_SOURCE,
    )

    assert row["subject"] == "matematica"
    assert row["topic"] == "divisao"
    assert row["difficulty"] == "2_facil"
    assert row["source"] == AI_POLISHED_QUESTION_SOURCE
    assert row["cohort_key"] == "crescer_e_conectar"
    assert row["is_active"] is True
    assert row["correct_answer"] == {
        "alternative_text": "4",
        "explanation": "12 dividido por 3 é igual a 4.",
    }
    assert len(row["wrong_answers"]) == 3
    assert isinstance(row["id_question"], int)
    assert row["id_question"] > 0


def test_question_authoring_service_polishes_payload_and_preserves_metadata() -> None:
    service = QuestionAuthoringService(
        FakeGenerationClient(
            {
                "statement": "Qual é a raiz quadrada de 81?",
                "correct_answer": {
                    "alternative_text": "9",
                    "explanation": "9 x 9 = 81.",
                },
                "wrong_answers": [
                    {
                        "alternative_text": "8",
                        "explanation": "8 x 8 = 64.",
                    },
                    {
                        "alternative_text": "7",
                        "explanation": "7 x 7 = 49.",
                    },
                    {
                        "alternative_text": "6",
                        "explanation": "6 x 6 = 36.",
                    },
                ],
            }
        )
    )
    draft = QuestionAuthoringDraft(
        project_key="rumo_etec",
        subject="Matemática",
        topic="radiciação",
        difficulty="3_medio",
    )

    polished = service.polish_draft(draft)

    assert polished.project_key == "rumo_etec"
    assert polished.subject == "Matemática"
    assert polished.topic == "radiciação"
    assert polished.difficulty == "3_medio"
    assert polished.statement == "Qual é a raiz quadrada de 81?"
    assert polished.correct_answer.alternative_text == "9"
    assert [answer.alternative_text for answer in polished.wrong_answers] == ["8", "7", "6"]


def test_difficulty_helpers_normalize_and_format_labels() -> None:
    assert normalize_difficulty_value("2_facil") == "2_facil"
    assert normalize_difficulty_value("invalida") is None
    assert format_difficulty_label("5_avancado") == "5. Avançado"
