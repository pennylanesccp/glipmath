from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import streamlit as st

from app.components.header import PracticeHeaderMetrics
from app.components.theme import apply_app_themea
from app.pages.login_page import render_login_page, render_not_authorized_page
from app.pages.main_page import render_main_page
from app.state.session_state import (
    bind_authenticated_user,
    clear_current_question,
    get_answered_question_ids,
    get_current_alternatives,
    get_current_question_id,
    get_invalid_question_ids,
    get_skipped_question_ids,
    get_subject_filter,
    get_user_answer_history,
    get_user_answer_history_issues,
    has_loaded_user_answer_history,
    initialize_session_state,
    mark_question_invalid,
    set_current_question,
    set_user_answer_history,
)
from modules.auth.auth_service import get_authenticated_identity
from modules.auth.authorization_service import AuthorizationService
from modules.config.settings import AppSettings, load_settings
from modules.domain.models import AnswerAttempt, DisplayAlternative, LeaderboardEntry, Question, QuestionIndexEntry
from modules.services.answer_service import AnswerService, parse_answers_dataframe
from modules.services.leaderboard_service import (
    find_user_position,
    format_position,
    parse_leaderboard_dataframe,
)
from modules.services.question_service import (
    build_display_alternatives,
    build_subject_options,
    filter_question_ids_by_subject,
    parse_question_index_dataframe,
    parse_single_question_dataframe,
    select_next_question_id,
)
from modules.services.streak_service import compute_day_streak, compute_question_streak
from modules.storage.answer_repository import AnswerRepository
from modules.storage.bigquery_client import BigQueryClient, BigQueryError
from modules.storage.question_repository import QuestionRepository
from modules.utils.logging_utils import configure_logging, get_logger


@dataclass(slots=True)
class RuntimeContext:
    """Runtime dependencies for the app entrypoint."""

    question_repository: QuestionRepository
    answer_repository: AnswerRepository
    answer_service: AnswerService


def main() -> None:
    """Streamlit entrypoint."""

    base_dir = Path(__file__).resolve().parents[1]

    st.set_page_config(
        page_title="GlipMath",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    initialize_session_state()
    settings = load_settings(base_dir=base_dir)
    logger = configure_logging(
        level="DEBUG" if settings.environment != "prod" else "INFO",
        log_file=base_dir / "logs" / "glipmath.log",
    )
    logger.info(
        "Starting app run | environment=%s | project_id=%s | location=%s",
        settings.environment,
        settings.gcp.project_id,
        settings.gcp.location,
    )
    apply_app_theme()
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
        bind_authenticated_user(authorized_user.email)
        question_index, question_index_issues = load_active_question_index(
            context.question_repository,
            settings.bigquery.question_bank_table_id(settings.gcp.project_id),
        )
        _ensure_user_answer_history_loaded(
            answer_repository=context.answer_repository,
            answers_table_id=settings.bigquery.answers_table_id(settings.gcp.project_id),
            user_email=authorized_user.email,
        )
        leaderboard_entries, leaderboard_issues = load_leaderboard_snapshot(
            context.answer_repository,
            settings.bigquery.leaderboard_view_id(settings.gcp.project_id),
        )
        answer_history = get_user_answer_history(authorized_user.email)
        selected_subject = get_subject_filter()
        subject_options = build_subject_options(question_index)
        current_question, current_alternatives, question_lookup_issues = resolve_current_question(
            question_repository=context.question_repository,
            question_table_id=settings.bigquery.question_bank_table_id(settings.gcp.project_id),
            active_question_ids=filter_question_ids_by_subject(question_index, selected_subject),
            answered_question_ids=get_answered_question_ids(authorized_user.email),
        )
    except BigQueryError as exc:
        logger.exception(
            "BigQuery-backed app startup failed for user_email=%s",
            authorized_user.email,
        )
        st.title(settings.app_name)
        st.error(str(exc))
        if settings.environment != "prod":
            st.caption(f"Log detalhado: `{base_dir / 'logs' / 'glipmath.log'}`")
            st.exception(exc.__cause__ or exc)
        return

    question_issues = list(question_index_issues) + list(question_lookup_issues)
    answer_issues = get_user_answer_history_issues(authorized_user.email) + list(leaderboard_issues)
    user_position = find_user_position(leaderboard_entries, authorized_user)

    _render_diagnostics(
        settings=settings,
        question_issues=question_issues,
        answer_issues=answer_issues,
    )
    render_main_page(
        settings=settings,
        user=authorized_user,
        current_question=current_question,
        alternatives=current_alternatives,
        answer_service=context.answer_service,
        subject_options=subject_options,
        header_metrics=PracticeHeaderMetrics(
            day_streak=compute_day_streak(answer_history, timezone_name=settings.timezone),
            question_streak=compute_question_streak(answer_history),
            leaderboard_position=format_position(user_position, len(leaderboard_entries)),
        ),
    )


@st.cache_resource(show_spinner=False)
def build_runtime_context(settings: AppSettings) -> RuntimeContext:
    """Create repositories and services from configuration."""

    logger = get_logger(__name__)
    logger.debug(
        "Building runtime context | project_id=%s | question_table=%s | answers_table=%s",
        settings.gcp.project_id,
        settings.bigquery.question_bank_table_id(settings.gcp.project_id),
        settings.bigquery.answers_table_id(settings.gcp.project_id),
    )
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


@st.cache_data(show_spinner=False, ttl=300)
def load_active_question_index(
    _question_repository: QuestionRepository,
    question_table_id: str,
) -> tuple[list[QuestionIndexEntry], list[str]]:
    """Load and cache the active-question index for the current table."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    question_index_frame = _question_repository.load_active_index_frame()
    question_index, issues = parse_question_index_dataframe(question_index_frame)
    logger.debug(
        "Loaded active question index | table_id=%s | count=%s | issues=%s | elapsed_ms=%.2f",
        question_table_id,
        len(question_index),
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return question_index, issues


@st.cache_data(show_spinner=False, ttl=300)
def load_question_snapshot(
    _question_repository: QuestionRepository,
    question_table_id: str,
    id_question: int,
) -> tuple[Question | None, list[str]]:
    """Load and cache one fully parsed question for display."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    question_frame = _question_repository.load_question_frame_by_id(id_question)
    question, issues = parse_single_question_dataframe(question_frame)
    logger.debug(
        "Loaded question snapshot | table_id=%s | id_question=%s | found=%s | issues=%s | elapsed_ms=%.2f",
        question_table_id,
        id_question,
        question is not None,
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return question, issues


@st.cache_data(show_spinner=False, ttl=120)
def load_user_answer_history(
    _answer_repository: AnswerRepository,
    answers_table_id: str,
    user_email: str,
) -> tuple[list[AnswerAttempt], list[str]]:
    """Load and cache one user's parsed answer history."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    answer_frame = _answer_repository.load_user_frame(user_email)
    answers, issues = parse_answers_dataframe(answer_frame)
    logger.debug(
        "Loaded user answer history | table_id=%s | user_email=%s | answers=%s | issues=%s | elapsed_ms=%.2f",
        answers_table_id,
        user_email,
        len(answers),
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return answers, issues


@st.cache_data(show_spinner=False, ttl=120)
def load_leaderboard_snapshot(
    _answer_repository: AnswerRepository,
    leaderboard_view_id: str,
) -> tuple[list[LeaderboardEntry], list[str]]:
    """Load and cache the leaderboard analytics view."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    leaderboard_frame = _answer_repository.load_leaderboard_frame()
    entries, issues = parse_leaderboard_dataframe(leaderboard_frame)
    logger.debug(
        "Loaded leaderboard snapshot | view_id=%s | entries=%s | issues=%s | elapsed_ms=%.2f",
        leaderboard_view_id,
        len(entries),
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return entries, issues


def _ensure_user_answer_history_loaded(
    *,
    answer_repository: AnswerRepository,
    answers_table_id: str,
    user_email: str,
) -> list[AnswerAttempt]:
    if not has_loaded_user_answer_history(user_email):
        answers, issues = load_user_answer_history(
            answer_repository,
            answers_table_id,
            user_email,
        )
        set_user_answer_history(user_email, answers, issues=issues)
    return get_user_answer_history(user_email)


def resolve_current_question(
    *,
    question_repository: QuestionRepository,
    question_table_id: str,
    active_question_ids: list[int],
    answered_question_ids: set[int],
) -> tuple[Question | None, list[DisplayAlternative], list[str]]:
    """Resolve the current question, selecting and caching one if needed."""

    issues: list[str] = []
    current_question_id = get_current_question_id()
    current_alternatives = get_current_alternatives()
    if current_question_id is not None and current_question_id not in active_question_ids:
        clear_current_question()
        current_question_id = None
        current_alternatives = []

    if current_question_id is not None and current_alternatives:
        current_question, current_issues = load_question_snapshot(
            question_repository,
            question_table_id,
            current_question_id,
        )
        if current_question is not None and not current_issues:
            return current_question, current_alternatives, []
        issues.extend(current_issues)
        mark_question_invalid(current_question_id)
        clear_current_question()

    excluded_question_ids = (
        set(answered_question_ids)
        | get_skipped_question_ids()
        | get_invalid_question_ids()
    )

    while True:
        next_question_id = select_next_question_id(active_question_ids, excluded_question_ids)
        if next_question_id is None:
            return None, [], issues

        next_question, current_issues = load_question_snapshot(
            question_repository,
            question_table_id,
            next_question_id,
        )
        if next_question is not None and not current_issues:
            alternatives = build_display_alternatives(next_question)
            set_current_question(next_question.id_question, alternatives)
            return next_question, alternatives, issues

        issues.extend(current_issues or [f"question_bank row for id_question {next_question_id} was not found."])
        mark_question_invalid(next_question_id)
        excluded_question_ids.add(next_question_id)


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
