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
    REMOVE_STUDENT_PENDING_TARGET_KEY,
    AuthoringAlternativeDraft,
    QuestionAuthoringDraft,
    USER_ACCESS_WRITE_PERMISSION_ERROR_HINT,
    _clear_remove_student_confirmation,
    _consume_add_student_email_reset_request,
    _consume_pending_authoring_draft_update,
    _format_add_student_error,
    _get_pending_student_removal,
    _handle_remove_student,
    _handle_polish_with_ai,
    _is_user_access_write_permission_error,
    _request_remove_student_confirmation,
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


def test_remove_student_confirmation_round_trips_through_session_state(monkeypatch) -> None:
    reruns: list[str] = []
    fake_st = SimpleNamespace(
        session_state={},
        rerun=lambda: reruns.append("rerun"),
    )
    monkeypatch.setattr(professor_page, "st", fake_st)

    _request_remove_student_confirmation(
        email="aluno@example.com",
        project_key="rumo_etec",
    )

    assert fake_st.session_state[REMOVE_STUDENT_PENDING_TARGET_KEY] == {
        "email": "aluno@example.com",
        "project_key": "rumo_etec",
    }
    assert _get_pending_student_removal(project_key="rumo_etec") == "aluno@example.com"
    assert _get_pending_student_removal(project_key="outro_projeto") is None
    assert reruns == ["rerun"]

    _clear_remove_student_confirmation()

    assert REMOVE_STUDENT_PENDING_TARGET_KEY not in fake_st.session_state


def test_handle_remove_student_deactivates_access_and_sets_notice(monkeypatch) -> None:
    notices: list[tuple[str, str]] = []
    errors: list[str] = []
    reruns: list[str] = []
    fake_st = SimpleNamespace(
        session_state={
            REMOVE_STUDENT_PENDING_TARGET_KEY: {
                "email": "aluno@example.com",
                "project_key": "rumo_etec",
            }
        },
        error=lambda message: errors.append(str(message)),
        rerun=lambda: reruns.append("rerun"),
    )
    monkeypatch.setattr(professor_page, "st", fake_st)
    monkeypatch.setattr(
        professor_page,
        "set_professor_notice",
        lambda kind, message: notices.append((kind, message)),
    )

    class FakeUserAccessRepository:
        def __init__(self) -> None:
            self.calls: list[dict[str, str]] = []

        def deactivate_student_access(self, *, user_email: str, cohort_key: str) -> int:
            self.calls.append(
                {
                    "user_email": user_email,
                    "cohort_key": cohort_key,
                }
            )
            return 1

    repository = FakeUserAccessRepository()

    _handle_remove_student(
        email=" ALUNO@Example.com ",
        project_key="Rumo_Etec",
        user_access_repository=repository,
    )

    assert repository.calls == [
        {
            "user_email": "aluno@example.com",
            "cohort_key": "rumo_etec",
        }
    ]
    assert REMOVE_STUDENT_PENDING_TARGET_KEY not in fake_st.session_state
    assert notices == [
        (
            "success",
            "Acesso removido para aluno@example.com neste projeto.",
        )
    ]
    assert errors == []
    assert reruns == ["rerun"]


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
        def __init__(self, *, api_keys: tuple[str, ...], model: str | None) -> None:
            self.api_keys = api_keys
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
        gemini_api_keys=("secret",),
        gemini_model="gemini-test",
    )

    assert len(errors) == 1
    assert "A IA retornou uma questao invalida" in errors[0]
    assert "alternative_text values must be unique" in errors[0]
    assert reruns == []
