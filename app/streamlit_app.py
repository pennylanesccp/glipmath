from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from app.components.theme import apply_app_theme
from app.pages.login_page import render_login_page, render_not_authorized_page
from app.pages.main_page import render_main_page
from app.state.session_state import initialize_session_state
from modules.auth.auth_service import get_authenticated_identity
from modules.auth.authorization_service import AuthorizationService
from modules.config.settings import AppSettings, load_settings
from modules.services.answer_service import AnswerService, parse_answers_dataframe
from modules.services.question_service import parse_question_bank_dataframe
from modules.storage.answer_repository import AnswerRepository
from modules.storage.bigquery_client import BigQueryClient, BigQueryError
from modules.storage.question_repository import QuestionRepository


@dataclass(slots=True)
class RuntimeContext:
    """Runtime dependencies for the app entrypoint."""

    question_repository: QuestionRepository
    answer_repository: AnswerRepository
    answer_service: AnswerService


def main() -> None:
    """Streamlit entrypoint."""

    st.set_page_config(
        page_title="GlipMath",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    initialize_session_state()
    apply_app_theme()

    base_dir = Path(__file__).resolve().parents[1]
    settings = load_settings(base_dir=base_dir)
    identity = get_authenticated_identity()

    if identity is None:
        render_login_page(settings)
        return

    authorized_user = AuthorizationService().authorize(
        identity.email,
        fallback_name=identity.name,
    )
    if authorized_user is None:
        render_not_authorized_page(settings, identity.email)
        return

    try:
        context = build_runtime_context(settings)
        question_frame = context.question_repository.load_frame()
        user_answer_frame = context.answer_repository.load_user_frame(authorized_user.email)
    except BigQueryError as exc:
        st.title(settings.app_name)
        st.error(str(exc))
        return

    questions, question_issues = parse_question_bank_dataframe(question_frame)
    answers, answer_issues = parse_answers_dataframe(user_answer_frame)

    _render_diagnostics(
        settings=settings,
        question_issues=question_issues,
        answer_issues=answer_issues,
    )
    render_main_page(
        settings=settings,
        user=authorized_user,
        questions=questions,
        answers=answers,
        answer_service=context.answer_service,
    )


@st.cache_resource(show_spinner=False)
def build_runtime_context(settings: AppSettings) -> RuntimeContext:
    """Create repositories and services from configuration."""

    bigquery_client = BigQueryClient(
        project_id=settings.gcp.project_id,
        location=settings.gcp.location,
        service_account_info=settings.service_account_info,
    )
    question_repository = QuestionRepository(
        bigquery_client,
        settings.bigquery.question_bank_table_id(settings.gcp.project_id),
    )
    answer_repository = AnswerRepository(
        bigquery_client,
        answers_table_id=settings.bigquery.answers_table_id(settings.gcp.project_id),
        leaderboard_view_id=settings.bigquery.leaderboard_view_id(settings.gcp.project_id),
    )
    return RuntimeContext(
        question_repository=question_repository,
        answer_repository=answer_repository,
        answer_service=AnswerService(
            answer_repository=answer_repository,
            timezone_name=settings.timezone,
            app_version=settings.app_version,
        ),
    )


def _render_diagnostics(
    *,
    settings: AppSettings,
    question_issues: list[str],
    answer_issues: list[str],
) -> None:
    issues = question_issues + answer_issues
    if not issues:
        return
    if settings.environment == "prod":
        st.warning("Alguns registros invalidos foram ignorados.")
        return

    with st.expander("Diagnostico dos dados", expanded=False):
        for issue in issues:
            st.write(f"- {issue}")


if __name__ == "__main__":
    main()
