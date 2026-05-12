from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    # Streamlit Community Cloud runs the entrypoint by file path, so ensure the repo
    # root is importable before loading app/modules packages.
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from modules.auth.streamlit_joserfc_patch import install_streamlit_joserfc_auth_patch

install_streamlit_joserfc_auth_patch()

from app.components.theme import apply_app_theme
from app.pages.login_page import render_login_page, render_not_authorized_page
from app.pages.main_page import render_main_page
from app.pages.professor_page import render_professor_page
from app.pages.student_dashboard_page import render_student_dashboard_page
from app.state.session_state import (
    bind_authenticated_user,
    clear_current_question,
    get_current_professor_tool,
    get_current_student_view,
    get_current_workspace,
    ensure_question_pool_scope,
    get_answered_question_ids,
    get_authenticated_user,
    get_current_alternatives,
    get_current_question,
    get_current_question_id,
    get_invalid_question_ids,
    get_leaderboard_position,
    get_question_pool,
    get_project_filter,
    get_skipped_question_ids,
    get_subject_filters,
    get_topic_filters,
    get_user_progress_snapshot,
    get_user_progress_snapshot_issues,
    has_loaded_user_progress_snapshot,
    has_loaded_leaderboard_position,
    has_logged_authenticated_run,
    initialize_session_state,
    mark_question_invalid,
    mark_authenticated_run_logged,
    set_current_question,
    set_current_professor_tool,
    set_current_student_view,
    set_current_workspace,
    set_leaderboard_position,
    set_project_filter,
    set_question_pool,
    set_subject_filters,
    set_topic_filters,
    set_user_progress_snapshot,
)
from modules.auth.auth_service import get_authenticated_identity, trigger_logout
from modules.auth.authorization_service import AuthorizationService
from modules.config.settings import AppSettings, load_settings
from modules.domain.models import (
    DisplayAlternative,
    Question,
    QuestionIndexEntry,
    StudentDashboardSummary,
    StudentSubjectPerformance,
    User,
    UserProgressSnapshot,
)
from modules.services.answer_service import AnswerService, parse_user_progress_snapshot_dataframe
from modules.services.leaderboard_service import parse_leaderboard_position_dataframe
from modules.services.question_service import (
    QuestionFilterSelection,
    SubjectTopicGroup,
    build_display_alternatives,
    format_project_label,
    build_subject_topic_groups,
    filter_question_ids_by_filters,
    format_question_filter_label,
    find_question_by_id,
    normalize_multi_question_filters,
    parse_project_options_dataframe,
    parse_question_bank_dataframe,
    parse_question_index_dataframe,
    parse_single_question_dataframe,
    select_question_batch_ids,
)
from modules.services.streak_service import compute_day_streak_from_activity_dates
from modules.services.student_dashboard_service import (
    parse_student_dashboard_summary_dataframe,
    parse_student_subject_performance_dataframe,
)
from modules.services.user_service import (
    resolve_available_project_options,
    resolve_effective_project_for_user,
)
from modules.storage.answer_repository import AnswerRepository
from modules.storage.bigquery_client import BigQueryClient, BigQueryError
from modules.storage.question_repository import QuestionRepository
from modules.storage.user_access_repository import UserAccessRepository
from modules.utils.datetime_utils import today_in_timezone
from modules.utils.logging_utils import configure_logging, get_logger
from modules.utils.normalization import normalize_email

QUESTION_PREFETCH_BATCH_SIZE = 10


@dataclass(slots=True)
class RuntimeContext:
    """Runtime dependencies for the app entrypoint."""

    question_repository: QuestionRepository
    user_access_repository: UserAccessRepository
    answer_repository: AnswerRepository
    answer_service: AnswerService
    authorization_service: AuthorizationService


def _normalize_filters_for_subject_group_shape(
    *,
    normalized_filters: QuestionFilterSelection,
    subject_topic_groups: list[SubjectTopicGroup],
) -> QuestionFilterSelection:
    if len(subject_topic_groups) != 1 or not normalized_filters.subjects:
        return normalized_filters
    return QuestionFilterSelection(
        subjects=(),
        topics=normalized_filters.topics,
    )


def main() -> None:
    """Streamlit entrypoint."""

    base_dir = REPO_ROOT
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
    apply_app_theme()

    identity = get_authenticated_identity()
    if identity is None:
        render_login_page(settings)
        return

    try:
        context = build_runtime_context(settings)
        authorized_user = _resolve_authorized_user(
            authorization_service=context.authorization_service,
            email=identity.email,
            fallback_name=identity.name,
        )
        if authorized_user is None:
            render_not_authorized_page(settings, identity.email)
            return

        if not has_logged_authenticated_run():
            logger.info(
                "Starting authenticated app run | environment=%s | project_id=%s | location=%s | user_email=%s",
                settings.environment,
                settings.gcp.project_id,
                settings.gcp.location,
                authorized_user.email,
            )
            mark_authenticated_run_logged()
        question_table_id = settings.bigquery.question_bank_table_id(settings.gcp.project_id)
        answers_table_id = settings.bigquery.answers_table_id(settings.gcp.project_id)
        user_access_table_id = settings.bigquery.user_access_table_id(settings.gcp.project_id)

        project_options, project_option_issues = _resolve_project_options_for_user(
            user=authorized_user,
            question_repository=context.question_repository,
            question_table_id=question_table_id,
        )
        selected_project = _resolve_selected_project_for_user(
            user=authorized_user,
            project_options=project_options,
        )
        selected_project, current_workspace = render_sidebar_ui(
            user=authorized_user,
            project_options=project_options,
            selected_project=selected_project,
        )
        current_student_view = get_current_student_view()
        effective_project_scope = resolve_effective_project_for_user(
            authorized_user,
            selected_project=selected_project,
        )

        if current_workspace == "professor":
            _render_diagnostics(
                settings=settings,
                question_issues=list(project_option_issues),
                answer_issues=[],
            )
            render_professor_page(
                selected_project=effective_project_scope,
                question_repository=context.question_repository,
                user_access_repository=context.user_access_repository,
                gemini_api_keys=settings.gemini.api_keys,
                gemini_model=settings.gemini.model,
            )
            _render_sidebar_logout_button()
            return

        if current_student_view == "stats":
            dashboard_summary, dashboard_summary_issues = load_student_dashboard_summary(
                context.answer_repository,
                answers_table_id,
                user_email=authorized_user.email,
                cohort_key=effective_project_scope,
            )
            subject_performance, subject_performance_issues = load_student_subject_performance(
                context.answer_repository,
                answers_table_id,
                user_email=authorized_user.email,
                cohort_key=effective_project_scope,
            )
            _render_diagnostics(
                settings=settings,
                question_issues=list(project_option_issues),
                answer_issues=list(dashboard_summary_issues) + list(subject_performance_issues),
            )
            render_student_dashboard_page(
                user=authorized_user,
                selected_project=effective_project_scope,
                summary=dashboard_summary,
                subject_performance=subject_performance,
            )
            _render_sidebar_logout_button()
            return

        question_index, question_index_issues = load_active_question_index(
            context.question_repository,
            question_table_id,
            effective_project_scope,
        )
        normalized_filters = normalize_multi_question_filters(
            question_index,
            subjects=get_subject_filters(),
            topics=get_topic_filters(),
        )
        subject_topic_groups = build_subject_topic_groups(question_index)
        normalized_filters = _normalize_filters_for_subject_group_shape(
            normalized_filters=normalized_filters,
            subject_topic_groups=subject_topic_groups,
        )
        if normalized_filters.subjects != get_subject_filters() or normalized_filters.topics != get_topic_filters():
            set_subject_filters(normalized_filters.subjects)
            set_topic_filters(normalized_filters.topics)
            clear_current_question()
            st.rerun()

        _ensure_user_progress_snapshot_loaded(
            answer_repository=context.answer_repository,
            answers_table_id=answers_table_id,
            user_email=authorized_user.email,
            timezone_name=settings.timezone,
        )
        user_progress = get_user_progress_snapshot(authorized_user.email)

        leaderboard_rank, leaderboard_total_users, leaderboard_issues = _ensure_leaderboard_position_loaded(
            answer_repository=context.answer_repository,
            answers_table_id=answers_table_id,
            user_access_table_id=user_access_table_id,
            user_email=authorized_user.email,
            role=authorized_user.role,
            cohort_key=effective_project_scope if not authorized_user.has_global_project_access else None,
        )

        current_question, current_alternatives, question_lookup_issues = resolve_current_question(
            question_repository=context.question_repository,
            question_table_id=question_table_id,
            cohort_key=effective_project_scope,
            active_question_ids=filter_question_ids_by_filters(question_index, normalized_filters),
            answered_question_ids=get_answered_question_ids(authorized_user.email),
        )
    except BigQueryError as exc:
        logger.exception(
            "BigQuery-backed app startup failed for user_email=%s",
            identity.email,
        )
        st.title(settings.app_name)
        st.error(str(exc))
        if settings.environment != "prod":
            st.caption(f"Log detalhado: `{base_dir / 'logs' / 'glipmath.log'}`")
            st.exception(exc.__cause__ or exc)
        return

    question_issues = list(project_option_issues) + list(question_index_issues) + list(question_lookup_issues)
    answer_issues = get_user_progress_snapshot_issues(authorized_user.email) + list(leaderboard_issues)
    _render_diagnostics(
        settings=settings,
        question_issues=question_issues,
        answer_issues=answer_issues,
    )

    render_main_page(
        user=authorized_user,
        current_question=current_question,
        alternatives=current_alternatives,
        answer_service=context.answer_service,
        subject_topic_groups=subject_topic_groups,
        selected_subjects=normalized_filters.subjects,
        selected_topics=normalized_filters.topics,
        selected_filter_label=format_question_filter_label(normalized_filters),
        day_streak=compute_day_streak_from_activity_dates(
            user_progress.activity_dates,
            today=today_in_timezone(settings.timezone),
        ),
        question_streak=user_progress.question_streak,
        leaderboard_position=_resolve_leaderboard_position(leaderboard_rank, leaderboard_total_users),
    )
    _render_sidebar_logout_button()


@st.cache_resource(show_spinner=False)
def build_runtime_context(settings: AppSettings) -> RuntimeContext:
    """Create repositories and services from configuration."""

    logger = get_logger(__name__)
    logger.debug(
        "Building runtime context | project_id=%s | question_table=%s | user_access_table=%s | answers_table=%s",
        settings.gcp.project_id,
        settings.bigquery.question_bank_table_id(settings.gcp.project_id),
        settings.bigquery.user_access_table_id(settings.gcp.project_id),
        settings.bigquery.answers_table_id(settings.gcp.project_id),
    )
    bigquery_client = BigQueryClient(
        project_id=settings.gcp.project_id,
        location=settings.gcp.location,
        service_account_info=settings.service_account_info,
        allow_application_default_credentials=False,
    )
    question_repository = QuestionRepository(
        bigquery_client,
        settings.bigquery.question_bank_table_id(settings.gcp.project_id),
    )
    user_access_repository = UserAccessRepository(
        bigquery_client,
        settings.bigquery.user_access_table_id(settings.gcp.project_id),
    )
    answer_repository = AnswerRepository(
        bigquery_client,
        answers_table_id=settings.bigquery.answers_table_id(settings.gcp.project_id),
        user_access_table_id=settings.bigquery.user_access_table_id(settings.gcp.project_id),
    )
    return RuntimeContext(
        question_repository=question_repository,
        user_access_repository=user_access_repository,
        answer_repository=answer_repository,
        answer_service=AnswerService(
            answer_repository=answer_repository,
            timezone_name=settings.timezone,
            app_version=settings.app_version,
        ),
        authorization_service=AuthorizationService(user_access_repository=user_access_repository),
    )


@st.cache_data(show_spinner=False, ttl=300)
def load_active_project_options(
    _question_repository: QuestionRepository,
    question_table_id: str,
) -> tuple[list[str], list[str]]:
    """Load and cache the distinct active project/cohort keys for teacher filtering."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    project_frame = _question_repository.load_active_project_frame()
    project_options, issues = parse_project_options_dataframe(project_frame)
    logger.debug(
        "Loaded active project options | table_id=%s | count=%s | issues=%s | elapsed_ms=%.2f",
        question_table_id,
        len(project_options),
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return project_options, issues


def _resolve_project_options_for_user(
    *,
    user: User,
    question_repository: QuestionRepository,
    question_table_id: str,
) -> tuple[list[str], list[str]]:
    active_project_options: list[str] = []
    issues: list[str] = []
    if user.has_global_project_access:
        active_project_options, issues = load_active_project_options(
            question_repository,
            question_table_id,
        )

    return resolve_available_project_options(user, active_project_options), issues


def _resolve_selected_project_for_user(
    *,
    user: User,
    project_options: list[str],
) -> str | None:
    selected_project = get_project_filter()
    default_project = resolve_effective_project_for_user(
        user,
        selected_project=selected_project,
    )

    if project_options:
        if selected_project in project_options:
            return selected_project
        if default_project in project_options:
            return default_project
        return project_options[0]
    return default_project


def render_sidebar_ui(
    *,
    user: User,
    project_options: list[str],
    selected_project: str | None,
) -> tuple[str | None, str]:
    """Apply sidebar styles and render authenticated navigation controls."""

    _apply_workspace_shell_styles()
    return _render_authenticated_shell_sidebar(
        user=user,
        project_options=project_options,
        selected_project=selected_project,
    )


def _render_authenticated_shell_sidebar(
    *,
    user: User,
    project_options: list[str],
    selected_project: str | None,
) -> tuple[str | None, str]:
    project_choice = selected_project
    current_workspace = "student"

    with st.sidebar:
        if len(project_options) > 1:
            with st.container():
                st.html('<div class="gm-sidebar-section-hook gm-sidebar-project-section-hook"></div>')
                st.caption("PROJETO")
                project_choice = st.selectbox(
                    "Projeto",
                    options=project_options,
                    index=project_options.index(selected_project) if selected_project in project_options else 0,
                    format_func=_format_project_option_label,
                    key="gm_global_project_filter_select",
                    label_visibility="collapsed",
                )

        if user.can_access_professor_space:
            with st.container():
                st.html('<div class="gm-sidebar-section-hook gm-sidebar-workspace-section-hook"></div>')
                st.caption("ESPA\u00c7O")
                current_workspace = get_current_workspace()
                st.html('<div class="gm-sidebar-workspace-buttons-hook"></div>')
                workspace_choice = _render_workspace_button_group(current_workspace)
            normalized_workspace = workspace_choice if workspace_choice in {"student", "professor"} else "student"
            if normalized_workspace != current_workspace:
                set_current_workspace(normalized_workspace)
                clear_current_question()
                st.rerun()
            current_workspace = normalized_workspace
        else:
            if get_current_workspace() != "student":
                set_current_workspace("student")
            if get_current_professor_tool() is not None:
                set_current_professor_tool(None)

        if current_workspace == "student":
            with st.container():
                st.html('<div class="gm-sidebar-section-hook gm-sidebar-view-section-hook"></div>')
                st.caption("VIS\u00c3O")
                current_student_view = get_current_student_view()
                student_view_choice = st.segmented_control(
                    "Vis\u00e3o do aluno",
                    options=["practice", "stats"],
                    default=current_student_view,
                    format_func=_format_student_view_label,
                    key="gm_student_view_segmented_control",
                    label_visibility="collapsed",
                    width="stretch",
                )
            normalized_student_view = (
                student_view_choice if student_view_choice in {"practice", "stats"} else "practice"
            )
            if normalized_student_view != current_student_view:
                set_current_student_view(normalized_student_view)
                if normalized_student_view == "practice":
                    clear_current_question()
                st.rerun()

    if project_choice != get_project_filter():
        st.session_state.pop("gm_subject_filter_select", None)
        set_project_filter(project_choice)
        set_subject_filters(())
        set_topic_filters(())
        clear_current_question()
        st.rerun()

    return project_choice, current_workspace


def _render_workspace_button_group(current_workspace: str) -> str:
    student_col, professor_col = st.columns(2, gap="small")
    with student_col:
        student_clicked = st.button(
            "Aluno",
            key="gm_workspace_student_button",
            type="primary" if current_workspace == "student" else "secondary",
            use_container_width=True,
        )
    with professor_col:
        professor_clicked = st.button(
            "Professor",
            key="gm_workspace_professor_button",
            type="primary" if current_workspace == "professor" else "secondary",
            use_container_width=True,
        )

    if student_clicked:
        return "student"
    if professor_clicked:
        return "professor"
    return current_workspace


def _render_sidebar_logout_button() -> None:
    with st.sidebar:
        with st.container():
            st.html('<div class="gm-sidebar-section-hook gm-sidebar-logout-button-hook"></div>')
            st.divider()
            if st.button(
                "Sair",
                key="gm_sidebar_logout_button",
                type="secondary",
                use_container_width=True,
            ):
                trigger_logout()


@st.cache_data(show_spinner=False, ttl=300)
def load_active_question_index(
    _question_repository: QuestionRepository,
    question_table_id: str,
    cohort_key: str | None,
) -> tuple[list[QuestionIndexEntry], list[str]]:
    """Load and cache the active-question index for the current table."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    question_index_frame = _question_repository.load_active_index_frame(cohort_key=cohort_key)
    question_index, issues = parse_question_index_dataframe(question_index_frame)
    logger.debug(
        "Loaded active question index | table_id=%s | cohort_key=%s | count=%s | issues=%s | elapsed_ms=%.2f",
        question_table_id,
        cohort_key,
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
    cohort_key: str | None,
) -> tuple[Question | None, list[str]]:
    """Load and cache one fully parsed question for display."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    question_frame = _question_repository.load_question_frame_by_id(
        id_question,
        cohort_key=cohort_key,
    )
    question, issues = parse_single_question_dataframe(question_frame)
    logger.debug(
        "Loaded question snapshot | table_id=%s | id_question=%s | cohort_key=%s | found=%s | issues=%s | elapsed_ms=%.2f",
        question_table_id,
        id_question,
        cohort_key,
        question is not None,
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return question, issues


@st.cache_data(show_spinner=False, ttl=300)
def load_question_batch(
    _question_repository: QuestionRepository,
    question_table_id: str,
    question_ids: tuple[int, ...],
    cohort_key: str | None,
) -> tuple[list[Question], list[str]]:
    """Load and cache a batch of fully parsed questions for the active pool."""

    if not question_ids:
        return [], []

    logger = get_logger(__name__)
    started_at = perf_counter()
    question_frame = _question_repository.load_question_frames_by_ids(
        list(question_ids),
        cohort_key=cohort_key,
    )
    questions, issues = parse_question_bank_dataframe(question_frame)
    logger.debug(
        "Loaded question batch | table_id=%s | requested=%s | loaded=%s | cohort_key=%s | issues=%s | elapsed_ms=%.2f",
        question_table_id,
        len(question_ids),
        len(questions),
        cohort_key,
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return questions, issues


@st.cache_data(show_spinner=False, ttl=120)
def load_user_progress_snapshot(
    _answer_repository: AnswerRepository,
    answers_table_id: str,
    *,
    user_email: str,
    timezone_name: str,
) -> tuple[UserProgressSnapshot, list[str]]:
    """Load and cache one user's compact progress snapshot."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    progress_frame = _answer_repository.load_user_progress_snapshot_frame(
        user_email=user_email,
        timezone_name=timezone_name,
    )
    snapshot, issues = parse_user_progress_snapshot_dataframe(progress_frame)
    logger.debug(
        "Loaded user progress snapshot | table_id=%s | user_email=%s | answered_questions=%s | activity_dates=%s | question_streak=%s | issues=%s | elapsed_ms=%.2f",
        answers_table_id,
        user_email,
        len(snapshot.answered_question_ids),
        len(snapshot.activity_dates),
        snapshot.question_streak,
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return snapshot, issues


@st.cache_data(show_spinner=False, ttl=60)
def load_leaderboard_position(
    _answer_repository: AnswerRepository,
    answers_table_id: str,
    user_access_table_id: str,
    *,
    user_email: str,
    role: str,
    cohort_key: str | None,
) -> tuple[int | None, int, list[str]]:
    """Load and cache only the current user's leaderboard rank plus total users."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    leaderboard_frame = _answer_repository.load_user_leaderboard_position_frame(
        user_email=user_email,
        role=role,
        cohort_key=cohort_key,
    )
    rank, total_users, issues = parse_leaderboard_position_dataframe(leaderboard_frame)
    logger.debug(
        "Loaded leaderboard position | answers_table_id=%s | user_access_table_id=%s | user_email=%s | role=%s | cohort_key=%s | rank=%s | total_users=%s | issues=%s | elapsed_ms=%.2f",
        answers_table_id,
        user_access_table_id,
        user_email,
        role,
        cohort_key,
        rank,
        total_users,
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return rank, total_users, issues


@st.cache_data(show_spinner=False, ttl=120)
def load_student_dashboard_summary(
    _answer_repository: AnswerRepository,
    answers_table_id: str,
    *,
    user_email: str,
    cohort_key: str | None,
) -> tuple[StudentDashboardSummary, list[str]]:
    """Load and cache one learner dashboard summary for the current project scope."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    summary_frame = _answer_repository.load_user_dashboard_summary_frame(
        user_email=user_email,
        cohort_key=cohort_key,
    )
    summary, issues = parse_student_dashboard_summary_dataframe(summary_frame)
    logger.debug(
        "Loaded student dashboard summary | answers_table_id=%s | user_email=%s | cohort_key=%s | total_answers=%s | total_correct=%s | total_wrong=%s | issues=%s | elapsed_ms=%.2f",
        answers_table_id,
        user_email,
        cohort_key,
        summary.total_answers,
        summary.total_correct,
        summary.total_wrong,
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return summary, issues


@st.cache_data(show_spinner=False, ttl=120)
def load_student_subject_performance(
    _answer_repository: AnswerRepository,
    answers_table_id: str,
    *,
    user_email: str,
    cohort_key: str | None,
) -> tuple[list[StudentSubjectPerformance], list[str]]:
    """Load and cache lightweight per-subject learner dashboard metrics."""

    logger = get_logger(__name__)
    started_at = perf_counter()
    subject_frame = _answer_repository.load_user_subject_performance_frame(
        user_email=user_email,
        cohort_key=cohort_key,
    )
    subject_performance, issues = parse_student_subject_performance_dataframe(subject_frame)
    logger.debug(
        "Loaded student subject performance | answers_table_id=%s | user_email=%s | cohort_key=%s | subjects=%s | issues=%s | elapsed_ms=%.2f",
        answers_table_id,
        user_email,
        cohort_key,
        len(subject_performance),
        len(issues),
        (perf_counter() - started_at) * 1000,
    )
    return subject_performance, issues


def _ensure_user_progress_snapshot_loaded(
    *,
    answer_repository: AnswerRepository,
    answers_table_id: str,
    user_email: str,
    timezone_name: str,
) -> UserProgressSnapshot:
    if not has_loaded_user_progress_snapshot(user_email):
        snapshot, issues = load_user_progress_snapshot(
            answer_repository,
            answers_table_id,
            user_email=user_email,
            timezone_name=timezone_name,
        )
        set_user_progress_snapshot(user_email, snapshot, issues=issues)
    return get_user_progress_snapshot(user_email)


def _resolve_authorized_user(
    *,
    authorization_service: AuthorizationService,
    email: str | None,
    fallback_name: str | None,
) -> User | None:
    normalized_email = normalize_email(email)
    if not normalized_email:
        return None

    cached_user = get_authenticated_user()
    if cached_user is not None and normalize_email(cached_user.email) == normalized_email:
        bind_authenticated_user(cached_user)
        return cached_user

    authorized_user = authorization_service.authorize(
        normalized_email,
        fallback_name=fallback_name,
    )
    if authorized_user is None:
        return None
    bind_authenticated_user(authorized_user)
    return authorized_user


def _ensure_leaderboard_position_loaded(
    *,
    answer_repository: AnswerRepository,
    answers_table_id: str,
    user_access_table_id: str,
    user_email: str,
    role: str,
    cohort_key: str | None,
) -> tuple[int | None, int, list[str]]:
    if not has_loaded_leaderboard_position(user_email):
        rank, total_users, issues = load_leaderboard_position(
            answer_repository,
            answers_table_id,
            user_access_table_id,
            user_email=user_email,
            role=role,
            cohort_key=cohort_key,
        )
        set_leaderboard_position(
            user_email,
            rank,
            total_users,
            issues=issues,
        )
    return get_leaderboard_position(user_email)


def resolve_current_question(
    *,
    question_repository: QuestionRepository,
    question_table_id: str,
    cohort_key: str | None,
    active_question_ids: list[int],
    answered_question_ids: set[int],
) -> tuple[Question | None, list[DisplayAlternative], list[str]]:
    """Resolve the current question, prefetched in batches when possible."""

    issues: list[str] = []
    active_question_id_set = {int(question_id) for question_id in active_question_ids}
    pool_scope_key = _build_question_pool_scope_key(
        cohort_key=cohort_key,
        active_question_ids=active_question_id_set,
    )
    ensure_question_pool_scope(pool_scope_key)

    current_question_id = get_current_question_id()
    current_question = get_current_question()
    current_alternatives = get_current_alternatives()

    if current_question_id is not None and current_question_id not in active_question_id_set:
        clear_current_question()
        current_question_id = None
        current_question = None
        current_alternatives = []

    if current_question_id is not None and current_alternatives:
        if current_question is not None and current_question.id_question == current_question_id:
            return current_question, current_alternatives, []

        pooled_question = find_question_by_id(get_question_pool(), current_question_id)
        if pooled_question is not None:
            return pooled_question, current_alternatives, []

        current_question, current_issues = load_question_snapshot(
            question_repository,
            question_table_id,
            current_question_id,
            cohort_key,
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
    question_pool = _prune_question_pool(
        question_pool=get_question_pool(),
        active_question_ids=active_question_id_set,
        excluded_question_ids=excluded_question_ids,
    )
    set_question_pool(question_pool, scope_key=pool_scope_key)

    next_question, question_pool = _take_next_question_from_pool(question_pool)
    if next_question is not None:
        set_question_pool(question_pool, scope_key=pool_scope_key)
        alternatives = build_display_alternatives(next_question)
        set_current_question(next_question, alternatives)
        return next_question, alternatives, issues

    while True:
        batch_question_ids = tuple(
            select_question_batch_ids(
                active_question_id_set,
                excluded_question_ids,
                limit=QUESTION_PREFETCH_BATCH_SIZE,
            )
        )
        if not batch_question_ids:
            return None, [], issues

        batch_questions, current_issues = load_question_batch(
            question_repository,
            question_table_id,
            batch_question_ids,
            cohort_key,
        )
        issues.extend(current_issues)

        batch_questions_by_id = {
            question.id_question: question
            for question in batch_questions
        }
        missing_question_ids = [
            question_id
            for question_id in batch_question_ids
            if question_id not in batch_questions_by_id
        ]
        for missing_question_id in missing_question_ids:
            issues.append(f"question_bank row for id_question {missing_question_id} was not found.")
            mark_question_invalid(missing_question_id)
            excluded_question_ids.add(missing_question_id)

        question_pool = [
            batch_questions_by_id[question_id]
            for question_id in batch_question_ids
            if question_id in batch_questions_by_id
        ]
        next_question, remaining_pool = _take_next_question_from_pool(question_pool)
        if next_question is not None:
            set_question_pool(remaining_pool, scope_key=pool_scope_key)
            alternatives = build_display_alternatives(next_question)
            set_current_question(next_question, alternatives)
            return next_question, alternatives, issues

        excluded_question_ids.update(batch_question_ids)


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
        st.warning("Alguns registros inválidos foram ignorados.")
        return

    with st.expander("Diagnóstico dos dados", expanded=False):
        for issue in issues:
            st.write(f"- {issue}")


def _resolve_leaderboard_position(rank: int | None, total_users: int) -> str:
    if rank is None or total_users <= 0:
        return "#-"
    return f"#{rank} / {total_users}"


def _format_project_option_label(project_key: str) -> str:
    return format_project_label(project_key)


def _format_student_view_label(view_name: str) -> str:
    return "Estat\u00edsticas" if view_name == "stats" else "Quest\u00f5es"


def _apply_workspace_shell_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --gm-sidebar-section-gap: 0.28rem;
            --gm-sidebar-section-margin-bottom: 24px;
            --gm-sidebar-horizontal-padding: 1.25rem;
            --gm-sidebar-caption-margin-top: 0;
            --gm-sidebar-caption-margin-bottom: 0.24rem;
            --gm-sidebar-actions-padding-top: 1rem;
        }

        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
            padding-left: var(--gm-sidebar-horizontal-padding) !important;
            padding-right: var(--gm-sidebar-horizontal-padding) !important;
        }

        div[data-testid="stSelectbox"] label p,
        div[data-testid="stSelectbox"] label span {
            color: #334155 !important;
            font-weight: 700 !important;
        }

        div[data-testid="stSelectbox"] {
            cursor: pointer !important;
            margin-bottom: 0;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 0.78rem !important;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05) !important;
            cursor: pointer !important;
            min-height: 2.55rem !important;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"],
        div[data-testid="stSelectbox"] [data-baseweb="select"] *,
        div[data-testid="stSelectbox"] [data-baseweb="select"] input {
            cursor: pointer !important;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] * {
            color: #0f172a !important;
        }

        div[data-baseweb="popover"],
        div[data-baseweb="popover"] [role="listbox"] {
            background: #ffffff !important;
            border: 1px solid #dbeafe !important;
            border-radius: 1rem !important;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12) !important;
            cursor: pointer !important;
        }

        div[data-baseweb="popover"] ul,
        div[data-baseweb="popover"] li,
        div[data-baseweb="popover"] [role="option"] {
            background: #ffffff !important;
            cursor: pointer !important;
        }

        div[data-baseweb="popover"] *,
        div[data-baseweb="popover"] [role="option"] * {
            color: #0f172a !important;
        }

        div[data-baseweb="popover"] [role="option"]:hover {
            background: #f8fbff !important;
        }

        div[data-baseweb="popover"] [role="option"][aria-selected="true"] {
            background: #eef2ff !important;
        }

        div[data-testid="stSegmentedControl"] {
            margin: 0;
            width: 100% !important;
            max-width: 100% !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] {
            margin: var(--gm-sidebar-caption-margin-top) 0 var(--gm-sidebar-caption-margin-bottom) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] p {
            color: #94a3b8 !important;
            font-size: 0.64rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.16em !important;
            line-height: 1.1 !important;
            text-transform: uppercase !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-section-hook) {
            gap: var(--gm-sidebar-section-gap) !important;
            margin-bottom: var(--gm-sidebar-section-margin-bottom) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) {
            gap: 0.44rem !important;
            margin-bottom: 0 !important;
            padding-top: var(--gm-sidebar-actions-padding-top) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-workspace-buttons-hook) [data-testid="stHorizontalBlock"] {
            gap: 0.42rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-workspace-buttons-hook) [data-testid="stHorizontalBlock"] > div {
            min-width: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-workspace-buttons-hook) [data-testid="stButton"] > button {
            min-height: 2.45rem !important;
            border-radius: 0.78rem !important;
            box-shadow: none !important;
            font-size: 0.82rem !important;
            font-weight: 750 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-workspace-buttons-hook) [data-testid="stButton"] > button[kind="primary"] {
            background: #eff6ff !important;
            border: 1px solid #93c5fd !important;
            color: #1d4ed8 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-workspace-buttons-hook) [data-testid="stButton"] > button[kind="primary"] p {
            color: #1d4ed8 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) hr {
            margin: 0.25rem 0 0.78rem !important;
            border-color: #dbe5f1 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button {
            background: #fff7f7 !important;
            border: 1px solid #fecaca !important;
            color: #b91c1c !important;
            box-shadow: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button p {
            color: #b91c1c !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button:hover {
            background: #fee2e2 !important;
            border-color: #fca5a5 !important;
            color: #991b1b !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button:hover p {
            color: #991b1b !important;
        }

        div[data-testid="stSegmentedControl"] > div {
            width: 100% !important;
            max-width: 100% !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [data-baseweb="button-group"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radiogroup"] {
            display: flex !important;
            justify-content: stretch !important;
            align-items: center !important;
            gap: 0.18rem !important;
            width: 100% !important;
            max-width: 100% !important;
            padding: 0.18rem !important;
            margin: 0 !important;
            background: #f1f5f9 !important;
            border: 1px solid #dbe5f1 !important;
            border-radius: 0.78rem !important;
            box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] > div,
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radiogroup"] > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button,
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[kind="primary"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[kind="secondary"] {
            position: relative !important;
            flex: 1 1 0 !important;
            min-height: auto !important;
            padding: 0.42rem 0.4rem !important;
            margin: 0 !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 0.6rem !important;
            box-shadow: none !important;
            color: #64748b !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            justify-content: center !important;
            line-height: 1.15 !important;
            text-align: center !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"] p,
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button p {
            color: inherit !important;
            font-size: inherit !important;
            line-height: inherit !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"]:hover,
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button:hover {
            color: #334155 !important;
            background: rgba(255, 255, 255, 0.64) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"][aria-selected="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"][aria-pressed="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[aria-checked="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[aria-selected="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[kind="primary"] {
            color: #0f172a !important;
            background: #ffffff !important;
            border-color: #dbe5f1 !important;
            box-shadow: 0 3px 8px rgba(15, 23, 42, 0.08) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _build_question_pool_scope_key(
    *,
    cohort_key: str | None,
    active_question_ids: set[int],
) -> str:
    return json.dumps(
        {
            "cohort_key": cohort_key,
            "active_question_ids": sorted(active_question_ids),
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _prune_question_pool(
    *,
    question_pool: list[Question],
    active_question_ids: set[int],
    excluded_question_ids: set[int],
) -> list[Question]:
    seen_question_ids: set[int] = set()
    pruned_pool: list[Question] = []
    for question in question_pool:
        if question.id_question in seen_question_ids:
            continue
        if question.id_question not in active_question_ids:
            continue
        if question.id_question in excluded_question_ids:
            continue
        seen_question_ids.add(question.id_question)
        pruned_pool.append(question)
    return pruned_pool


def _take_next_question_from_pool(
    question_pool: list[Question],
) -> tuple[Question | None, list[Question]]:
    if not question_pool:
        return None, []
    return question_pool[0], question_pool[1:]


if __name__ == "__main__":
    main()
