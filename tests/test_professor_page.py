from types import SimpleNamespace

from app.pages import professor_page
from app.pages.professor_page import (
    ADD_STUDENT_EMAIL_KEY,
    ADD_STUDENT_EMAIL_RESET_REQUEST_KEY,
    AUTHORING_CORRECT_EXPLANATION_KEY,
    AUTHORING_CORRECT_TEXT_KEY,
    AUTHORING_DIFFICULTY_KEY,
    AUTHORING_PENDING_DRAFT_UPDATE_KEY,
    AUTHORING_STATEMENT_KEY,
    AUTHORING_SUBJECT_KEY,
    AUTHORING_TOPIC_KEY,
    AUTHORING_WRONG_EXPLANATION_KEYS,
    AUTHORING_WRONG_TEXT_KEYS,
    AuthoringAlternativeDraft,
    QuestionAuthoringDraft,
    USER_ACCESS_WRITE_PERMISSION_ERROR_HINT,
    _consume_add_student_email_reset_request,
    _consume_pending_authoring_draft_update,
    _format_add_student_error,
    _handle_polish_with_ai,
    _is_user_access_write_permission_error,
    _request_authoring_draft_update,
)
from modules.storage.bigquery_client import BigQueryError
import streamlit as st


def test_detects_user_access_write_permission_error() -> None:
    message = (
        "BigQuery insert failed: 403 POST https://bigquery.googleapis.com/... "
        "Permission bigquery.tables.updateData denied on table "
        "ide-math-app:glipmath_core.user_access"
    )

    assert _is_user_access_write_permission_error(message) is True


def test_formats_user_access_write_permission_error_with_actionable_hint() -> None:
    exc = BigQueryError(
        "BigQuery insert failed: Permission bigquery.tables.updateData denied on table "
        "ide-math-app:glipmath_core.user_access"
    )

    assert _format_add_student_error(exc) == USER_ACCESS_WRITE_PERMISSION_ERROR_HINT


def test_keeps_unrelated_add_student_errors_unchanged() -> None:
    exc = ValueError("E-mail invalido.")

    assert _format_add_student_error(exc) == "E-mail invalido."


def test_consume_add_student_email_reset_request_clears_widget_value() -> None:
    st.session_state[ADD_STUDENT_EMAIL_KEY] = "aluno@example.com"
    st.session_state[ADD_STUDENT_EMAIL_RESET_REQUEST_KEY] = True

    _consume_add_student_email_reset_request()

    assert st.session_state[ADD_STUDENT_EMAIL_KEY] == ""
    assert ADD_STUDENT_EMAIL_RESET_REQUEST_KEY not in st.session_state


def test_consume_pending_authoring_draft_update_applies_matching_project(monkeypatch) -> None:
    fake_st = SimpleNamespace(session_state={})
    ai_assisted_values: list[bool] = []
    monkeypatch.setattr(professor_page, "st", fake_st)
    monkeypatch.setattr(
        professor_page,
        "set_professor_authoring_ai_assisted",
        lambda value: ai_assisted_values.append(bool(value)),
    )

    _request_authoring_draft_update(
        QuestionAuthoringDraft(
            project_key="rumo_etec",
            subject="Matematica",
            topic="divisao",
            difficulty="2_facil",
            statement="Quanto e 12 dividido por 3?",
            correct_answer=AuthoringAlternativeDraft(
                alternative_text="4",
                explanation="12 dividido por 3 e 4.",
            ),
            wrong_answers=(
                AuthoringAlternativeDraft("3", "3 x 3 e 9."),
                AuthoringAlternativeDraft("5", "5 x 3 e 15."),
                AuthoringAlternativeDraft("6", "6 x 3 e 18."),
            ),
        ),
        ai_assisted=True,
    )

    _consume_pending_authoring_draft_update(project_key="rumo_etec")

    assert fake_st.session_state[AUTHORING_SUBJECT_KEY] == "Matematica"
    assert fake_st.session_state[AUTHORING_TOPIC_KEY] == "divisao"
    assert fake_st.session_state[AUTHORING_DIFFICULTY_KEY] == "2_facil"
    assert fake_st.session_state[AUTHORING_STATEMENT_KEY] == "Quanto e 12 dividido por 3?"
    assert fake_st.session_state[AUTHORING_CORRECT_TEXT_KEY] == "4"
    assert fake_st.session_state[AUTHORING_CORRECT_EXPLANATION_KEY] == "12 dividido por 3 e 4."
    assert [fake_st.session_state[key] for key in AUTHORING_WRONG_TEXT_KEYS] == ["3", "5", "6"]
    assert [fake_st.session_state[key] for key in AUTHORING_WRONG_EXPLANATION_KEYS] == [
        "3 x 3 e 9.",
        "5 x 3 e 15.",
        "6 x 3 e 18.",
    ]
    assert ai_assisted_values == [True]
    assert AUTHORING_PENDING_DRAFT_UPDATE_KEY not in fake_st.session_state


def test_handle_polish_with_ai_shows_error_for_invalid_ai_payload(monkeypatch) -> None:
    errors: list[str] = []
    reruns: list[str] = []
    fake_st = SimpleNamespace(
        session_state={},
        error=lambda message: errors.append(str(message)),
        warning=lambda message: None,
        rerun=lambda: reruns.append("rerun"),
    )
    monkeypatch.setattr(professor_page, "st", fake_st)

    class FakeGeminiClient:
        def __init__(self, *, api_key: str | None, model: str | None) -> None:
            self.api_key = api_key
            self.model = model

    class FakeAuthoringService:
        def __init__(self, client: object) -> None:
            self.client = client

        def polish_draft(self, draft: QuestionAuthoringDraft) -> QuestionAuthoringDraft:
            raise ValueError("alternative_text values must be unique within a question.")

    from modules.ai import gemini_client

    monkeypatch.setattr(gemini_client, "GeminiClient", FakeGeminiClient)
    monkeypatch.setattr(professor_page, "QuestionAuthoringService", FakeAuthoringService)

    _handle_polish_with_ai(
        draft=QuestionAuthoringDraft(
            project_key="rumo_etec",
            subject="Matematica",
            topic="divisao",
            difficulty="2_facil",
        ),
        gemini_api_key="secret",
        gemini_model="gemini-test",
    )

    assert len(errors) == 1
    assert "A IA retornou uma questao invalida" in errors[0]
    assert "alternative_text values must be unique" in errors[0]
    assert reruns == []
