from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import streamlit as st

from modules.domain.models import (
    AnswerAttempt,
    AnswerEvaluation,
    DisplayAlternative,
    Question,
    QuestionAlternative,
    User,
    UserProgressSnapshot,
)
from modules.utils.datetime_utils import utc_now

SESSION_ID_KEY = "glipmath_session_id"
AUTHENTICATED_USER_EMAIL_KEY = "glipmath_authenticated_user_email"
AUTHENTICATED_USER_SCOPE_KEY = "glipmath_authenticated_user_scope"
AUTHENTICATED_USER_KEY = "glipmath_authenticated_user"
AUTHENTICATED_RUN_LOGGED_KEY = "glipmath_authenticated_run_logged"
CURRENT_WORKSPACE_KEY = "glipmath_current_workspace"
CURRENT_STUDENT_VIEW_KEY = "glipmath_current_student_view"
CURRENT_PROFESSOR_TOOL_KEY = "glipmath_current_professor_tool"
PROFESSOR_AUTHORING_AI_ASSISTED_KEY = "glipmath_professor_authoring_ai_assisted"
PROFESSOR_NOTICE_KEY = "glipmath_professor_notice"
CURRENT_QUESTION_ID_KEY = "glipmath_current_question_id"
CURRENT_QUESTION_KEY = "glipmath_current_question"
CURRENT_ALTERNATIVES_KEY = "glipmath_current_alternatives"
QUESTION_POOL_KEY = "glipmath_question_pool"
QUESTION_POOL_SCOPE_KEY = "glipmath_question_pool_scope"
LEADERBOARD_RANK_KEY = "glipmath_leaderboard_rank"
LEADERBOARD_TOTAL_USERS_KEY = "glipmath_leaderboard_total_users"
LEADERBOARD_ISSUES_KEY = "glipmath_leaderboard_issues"
LEADERBOARD_LOADED_KEY = "glipmath_leaderboard_loaded"
QUESTION_STARTED_AT_KEY = "glipmath_question_started_at"
QUESTION_ANSWERED_KEY = "glipmath_question_answered"
LAST_ANSWER_RESULT_KEY = "glipmath_last_answer_result"
QUESTION_SELECTION_KEY = "glipmath_question_selection"
SUBMISSION_IN_PROGRESS_KEY = "glipmath_submission_in_progress"
SKIPPED_QUESTION_IDS_KEY = "glipmath_skipped_question_ids"
INVALID_QUESTION_IDS_KEY = "glipmath_invalid_question_ids"
USER_PROGRESS_SNAPSHOT_KEY = "glipmath_user_progress_snapshot"
USER_PROGRESS_ISSUES_KEY = "glipmath_user_progress_issues"
USER_PROGRESS_LOADED_KEY = "glipmath_user_progress_loaded"
USER_ANSWERED_QUESTION_IDS_KEY = "glipmath_user_answered_question_ids"
SUBJECT_FILTER_KEY = "glipmath_subject_filter"
TOPIC_FILTER_KEY = "glipmath_topic_filter"
SUBJECT_FILTERS_KEY = "glipmath_subject_filters"
TOPIC_FILTERS_KEY = "glipmath_topic_filters"
PROJECT_FILTER_KEY = "glipmath_project_filter"


def initialize_session_state() -> None:
    """Ensure all GlipMath session keys exist."""

    st.session_state.setdefault(SESSION_ID_KEY, uuid4().hex)
    st.session_state.setdefault(AUTHENTICATED_USER_EMAIL_KEY, None)
    st.session_state.setdefault(AUTHENTICATED_USER_SCOPE_KEY, None)
    st.session_state.setdefault(AUTHENTICATED_USER_KEY, None)
    st.session_state.setdefault(AUTHENTICATED_RUN_LOGGED_KEY, False)
    st.session_state.setdefault(CURRENT_WORKSPACE_KEY, "student")
    st.session_state.setdefault(CURRENT_STUDENT_VIEW_KEY, "practice")
    st.session_state.setdefault(CURRENT_PROFESSOR_TOOL_KEY, None)
    st.session_state.setdefault(PROFESSOR_AUTHORING_AI_ASSISTED_KEY, False)
    st.session_state.setdefault(PROFESSOR_NOTICE_KEY, None)
    st.session_state.setdefault(CURRENT_QUESTION_ID_KEY, None)
    st.session_state.setdefault(CURRENT_QUESTION_KEY, None)
    st.session_state.setdefault(CURRENT_ALTERNATIVES_KEY, [])
    st.session_state.setdefault(QUESTION_POOL_KEY, [])
    st.session_state.setdefault(QUESTION_POOL_SCOPE_KEY, None)
    st.session_state.setdefault(LEADERBOARD_RANK_KEY, None)
    st.session_state.setdefault(LEADERBOARD_TOTAL_USERS_KEY, 0)
    st.session_state.setdefault(LEADERBOARD_ISSUES_KEY, [])
    st.session_state.setdefault(LEADERBOARD_LOADED_KEY, False)
    st.session_state.setdefault(QUESTION_STARTED_AT_KEY, None)
    st.session_state.setdefault(QUESTION_ANSWERED_KEY, False)
    st.session_state.setdefault(LAST_ANSWER_RESULT_KEY, None)
    st.session_state.setdefault(QUESTION_SELECTION_KEY, None)
    st.session_state.setdefault(SUBMISSION_IN_PROGRESS_KEY, False)
    st.session_state.setdefault(SKIPPED_QUESTION_IDS_KEY, [])
    st.session_state.setdefault(INVALID_QUESTION_IDS_KEY, [])
    st.session_state.setdefault(USER_PROGRESS_SNAPSHOT_KEY, None)
    st.session_state.setdefault(USER_PROGRESS_ISSUES_KEY, [])
    st.session_state.setdefault(USER_PROGRESS_LOADED_KEY, False)
    st.session_state.setdefault(USER_ANSWERED_QUESTION_IDS_KEY, [])
    st.session_state.setdefault(SUBJECT_FILTER_KEY, "Todas")
    st.session_state.setdefault(TOPIC_FILTER_KEY, None)
    st.session_state.setdefault(SUBJECT_FILTERS_KEY, [])
    st.session_state.setdefault(TOPIC_FILTERS_KEY, [])
    st.session_state.setdefault(PROJECT_FILTER_KEY, None)


def get_session_id() -> str:
    """Return the stable session identifier for the current browser session."""

    initialize_session_state()
    return str(st.session_state[SESSION_ID_KEY])


def bind_authenticated_user(user: User) -> None:
    """Reset user-scoped session state when the authenticated user changes."""

    initialize_session_state()
    user_scope = f"{user.email}|{user.role}|{user.cohort_key}"
    current_email = st.session_state[AUTHENTICATED_USER_EMAIL_KEY]
    current_scope = st.session_state[AUTHENTICATED_USER_SCOPE_KEY]
    if current_email == user.email and current_scope == user_scope:
        return

    st.session_state[AUTHENTICATED_USER_EMAIL_KEY] = user.email
    st.session_state[AUTHENTICATED_USER_SCOPE_KEY] = user_scope
    st.session_state[AUTHENTICATED_USER_KEY] = {
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "cohort_key": user.cohort_key,
        "accessible_cohort_keys": list(user.accessible_cohort_keys),
    }
    st.session_state[AUTHENTICATED_RUN_LOGGED_KEY] = False
    st.session_state[CURRENT_WORKSPACE_KEY] = "student"
    st.session_state[CURRENT_STUDENT_VIEW_KEY] = "practice"
    st.session_state[CURRENT_PROFESSOR_TOOL_KEY] = None
    st.session_state[PROFESSOR_AUTHORING_AI_ASSISTED_KEY] = False
    st.session_state[PROFESSOR_NOTICE_KEY] = None
    st.session_state[SESSION_ID_KEY] = uuid4().hex
    st.session_state[SKIPPED_QUESTION_IDS_KEY] = []
    st.session_state[INVALID_QUESTION_IDS_KEY] = []
    st.session_state[USER_PROGRESS_SNAPSHOT_KEY] = None
    st.session_state[USER_PROGRESS_ISSUES_KEY] = []
    st.session_state[USER_PROGRESS_LOADED_KEY] = False
    st.session_state[USER_ANSWERED_QUESTION_IDS_KEY] = []
    st.session_state[SUBJECT_FILTER_KEY] = "Todas"
    st.session_state[TOPIC_FILTER_KEY] = None
    st.session_state[SUBJECT_FILTERS_KEY] = []
    st.session_state[TOPIC_FILTERS_KEY] = []
    st.session_state[PROJECT_FILTER_KEY] = None
    st.session_state[QUESTION_POOL_KEY] = []
    st.session_state[QUESTION_POOL_SCOPE_KEY] = None
    st.session_state[LEADERBOARD_RANK_KEY] = None
    st.session_state[LEADERBOARD_TOTAL_USERS_KEY] = 0
    st.session_state[LEADERBOARD_ISSUES_KEY] = []
    st.session_state[LEADERBOARD_LOADED_KEY] = False
    clear_current_question()


def get_authenticated_user() -> User | None:
    """Return the cached authorized user for the current browser session."""

    initialize_session_state()
    raw_user = st.session_state[AUTHENTICATED_USER_KEY]
    if not isinstance(raw_user, dict):
        return None

    email = _string_or_none(raw_user.get("email"))
    if not email:
        return None

    return User(
        email=email,
        name=_string_or_none(raw_user.get("name")),
        role=_string_or_none(raw_user.get("role")) or "student",
        cohort_key=_string_or_none(raw_user.get("cohort_key")) or "all",
        accessible_cohort_keys=tuple(
            _string_or_none(value)
            for value in raw_user.get("accessible_cohort_keys", [])
            if _string_or_none(value)
        ),
    )


def has_loaded_user_progress_snapshot(user_email: str) -> bool:
    """Return whether the current user's progress snapshot is already in session."""

    initialize_session_state()
    return (
        st.session_state[AUTHENTICATED_USER_EMAIL_KEY] == user_email
        and bool(st.session_state[USER_PROGRESS_LOADED_KEY])
    )


def has_logged_authenticated_run() -> bool:
    """Return whether the current authenticated session already emitted its startup log."""

    initialize_session_state()
    return bool(st.session_state[AUTHENTICATED_RUN_LOGGED_KEY])


def mark_authenticated_run_logged() -> None:
    """Mark the current authenticated session startup as already logged."""

    initialize_session_state()
    st.session_state[AUTHENTICATED_RUN_LOGGED_KEY] = True


def get_current_workspace() -> str:
    """Return the selected authenticated workspace."""

    initialize_session_state()
    workspace = _string_or_none(st.session_state[CURRENT_WORKSPACE_KEY]) or "student"
    if workspace not in {"student", "professor"}:
        return "student"
    return workspace


def get_current_student_view() -> str:
    """Return the selected student-space view."""

    initialize_session_state()
    current_view = _string_or_none(st.session_state[CURRENT_STUDENT_VIEW_KEY]) or "practice"
    if current_view not in {"practice", "stats"}:
        return "practice"
    return current_view


def set_current_workspace(workspace: str | None) -> None:
    """Persist the selected authenticated workspace."""

    initialize_session_state()
    normalized_workspace = _string_or_none(workspace) or "student"
    if normalized_workspace not in {"student", "professor"}:
        normalized_workspace = "student"
    st.session_state[CURRENT_WORKSPACE_KEY] = normalized_workspace


def set_current_student_view(view_name: str | None) -> None:
    """Persist the selected student-space view."""

    initialize_session_state()
    normalized_view = _string_or_none(view_name) or "practice"
    if normalized_view not in {"practice", "stats"}:
        normalized_view = "practice"
    st.session_state[CURRENT_STUDENT_VIEW_KEY] = normalized_view


def get_current_professor_tool() -> str | None:
    """Return the selected professor-space menu item."""

    initialize_session_state()
    return _string_or_none(st.session_state[CURRENT_PROFESSOR_TOOL_KEY])


def set_current_professor_tool(tool_name: str | None) -> None:
    """Persist the selected professor-space menu item."""

    initialize_session_state()
    st.session_state[CURRENT_PROFESSOR_TOOL_KEY] = _string_or_none(tool_name)


def get_professor_authoring_ai_assisted() -> bool:
    """Return whether the current professor draft was last polished with AI."""

    initialize_session_state()
    return bool(st.session_state[PROFESSOR_AUTHORING_AI_ASSISTED_KEY])


def set_professor_authoring_ai_assisted(value: bool) -> None:
    """Persist whether the current professor draft was AI-assisted."""

    initialize_session_state()
    st.session_state[PROFESSOR_AUTHORING_AI_ASSISTED_KEY] = bool(value)


def get_professor_notice() -> dict[str, str] | None:
    """Return the latest professor-space flash message."""

    initialize_session_state()
    value = st.session_state[PROFESSOR_NOTICE_KEY]
    if not isinstance(value, dict):
        return None

    kind = _string_or_none(value.get("kind"))
    message = _string_or_none(value.get("message"))
    if not kind or not message:
        return None
    return {"kind": kind, "message": message}


def set_professor_notice(kind: str, message: str) -> None:
    """Persist one professor-space flash message."""

    initialize_session_state()
    normalized_kind = _string_or_none(kind) or "info"
    normalized_message = _string_or_none(message)
    if normalized_message is None:
        st.session_state[PROFESSOR_NOTICE_KEY] = None
        return
    st.session_state[PROFESSOR_NOTICE_KEY] = {
        "kind": normalized_kind,
        "message": normalized_message,
    }


def clear_professor_notice() -> None:
    """Clear any professor-space flash message."""

    initialize_session_state()
    st.session_state[PROFESSOR_NOTICE_KEY] = None


def has_loaded_leaderboard_position(user_email: str) -> bool:
    """Return whether the current user's leaderboard snapshot is already in session."""

    initialize_session_state()
    return (
        st.session_state[AUTHENTICATED_USER_EMAIL_KEY] == user_email
        and bool(st.session_state[LEADERBOARD_LOADED_KEY])
    )


def set_leaderboard_position(
    user_email: str,
    rank: int | None,
    total_users: int,
    *,
    issues: list[str] | None = None,
) -> None:
    """Persist the current user's leaderboard snapshot in session state."""

    _bind_authenticated_user_email(user_email)
    st.session_state[LEADERBOARD_RANK_KEY] = int(rank) if rank is not None else None
    st.session_state[LEADERBOARD_TOTAL_USERS_KEY] = max(int(total_users), 0)
    st.session_state[LEADERBOARD_ISSUES_KEY] = list(issues or [])
    st.session_state[LEADERBOARD_LOADED_KEY] = True


def get_leaderboard_position(user_email: str) -> tuple[int | None, int, list[str]]:
    """Return the cached leaderboard snapshot for the current authenticated user."""

    if not has_loaded_leaderboard_position(user_email):
        return None, 0, []

    raw_rank = st.session_state[LEADERBOARD_RANK_KEY]
    raw_total_users = st.session_state[LEADERBOARD_TOTAL_USERS_KEY]
    raw_issues = st.session_state[LEADERBOARD_ISSUES_KEY]
    rank = int(raw_rank) if raw_rank is not None else None
    total_users = max(int(raw_total_users), 0) if raw_total_users is not None else 0
    issues = [str(issue) for issue in raw_issues] if isinstance(raw_issues, list) else []
    return rank, total_users, issues


def set_user_progress_snapshot(
    user_email: str,
    snapshot: UserProgressSnapshot,
    *,
    issues: list[str] | None = None,
) -> None:
    """Persist the current user's compact progress snapshot in session state."""

    _bind_authenticated_user_email(user_email)
    st.session_state[USER_PROGRESS_SNAPSHOT_KEY] = {
        "answered_question_ids": list(snapshot.answered_question_ids),
        "activity_dates": [value.isoformat() for value in snapshot.activity_dates],
        "question_streak": max(int(snapshot.question_streak), 0),
    }
    st.session_state[USER_PROGRESS_ISSUES_KEY] = list(issues or [])
    st.session_state[USER_PROGRESS_LOADED_KEY] = True
    st.session_state[USER_ANSWERED_QUESTION_IDS_KEY] = list(snapshot.answered_question_ids)


def get_user_progress_snapshot(user_email: str) -> UserProgressSnapshot:
    """Return the current user's compact progress snapshot from session state."""

    if not has_loaded_user_progress_snapshot(user_email):
        return UserProgressSnapshot()

    raw_snapshot = st.session_state[USER_PROGRESS_SNAPSHOT_KEY]
    if not isinstance(raw_snapshot, dict):
        return UserProgressSnapshot()

    raw_answered_question_ids = raw_snapshot.get("answered_question_ids", [])
    raw_activity_dates = raw_snapshot.get("activity_dates", [])
    raw_question_streak = raw_snapshot.get("question_streak", 0)
    answered_question_ids = tuple(
        sorted(
            {
                int(value)
                for value in raw_answered_question_ids
                if value is not None and str(value).strip()
            }
        )
    )
    activity_dates = tuple(
        sorted(
            {
                parsed_date
                for value in raw_activity_dates
                for parsed_date in [_parse_local_date(value)]
                if parsed_date is not None
            },
            reverse=True,
        )
    )
    question_streak = max(int(raw_question_streak or 0), 0)
    return UserProgressSnapshot(
        answered_question_ids=answered_question_ids,
        activity_dates=activity_dates,
        question_streak=question_streak,
    )


def get_user_progress_snapshot_issues(user_email: str) -> list[str]:
    """Return any issues found while loading the user's progress snapshot."""

    if not has_loaded_user_progress_snapshot(user_email):
        return []
    raw_issues = st.session_state[USER_PROGRESS_ISSUES_KEY]
    if not isinstance(raw_issues, list):
        return []
    return [str(issue) for issue in raw_issues]


def append_user_answer_attempt(user_email: str, answer: AnswerAttempt) -> None:
    """Append one new answer attempt to the current user's in-session progress snapshot."""

    _bind_authenticated_user_email(user_email)
    current_snapshot = get_user_progress_snapshot(user_email)
    updated_question_ids = tuple(
        sorted({*current_snapshot.answered_question_ids, answer.id_question})
    )
    updated_activity_dates = tuple(
        sorted(
            {
                *current_snapshot.activity_dates,
                _answer_activity_date(answer),
            },
            reverse=True,
        )
    )
    set_user_progress_snapshot(
        user_email,
        UserProgressSnapshot(
            answered_question_ids=updated_question_ids,
            activity_dates=updated_activity_dates,
            question_streak=(current_snapshot.question_streak + 1) if answer.is_correct else 0,
        ),
        issues=get_user_progress_snapshot_issues(user_email),
    )


def get_answered_question_ids(user_email: str) -> set[int]:
    """Return the answered question IDs for the current authenticated user."""

    if not has_loaded_user_progress_snapshot(user_email):
        return set()

    raw_ids = st.session_state[USER_ANSWERED_QUESTION_IDS_KEY]
    if not isinstance(raw_ids, list):
        return set()
    return {int(value) for value in raw_ids if value is not None}


def get_current_question_id() -> int | None:
    """Return the current question identifier from session state."""

    initialize_session_state()
    value = st.session_state[CURRENT_QUESTION_ID_KEY]
    return int(value) if value is not None else None


def get_current_question() -> Question | None:
    """Return the current question snapshot from session state."""

    initialize_session_state()
    return _deserialize_question(st.session_state[CURRENT_QUESTION_KEY])


def get_current_alternatives() -> list[DisplayAlternative]:
    """Return the current randomized alternatives from session state."""

    initialize_session_state()
    raw_alternatives = st.session_state[CURRENT_ALTERNATIVES_KEY]
    if not isinstance(raw_alternatives, list):
        return []

    alternatives: list[DisplayAlternative] = []
    for item in raw_alternatives:
        if not isinstance(item, dict):
            continue
        try:
            alternatives.append(
                DisplayAlternative(
                    option_id=str(item["option_id"]),
                    alternative_text=str(item["alternative_text"]),
                    explanation=_string_or_none(item.get("explanation")),
                    is_correct=bool(item["is_correct"]),
                )
            )
        except KeyError:
            continue
    return alternatives


def get_question_selection() -> str | None:
    """Return the current in-session selected option ID."""

    initialize_session_state()
    value = st.session_state[QUESTION_SELECTION_KEY]
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def set_question_selection(option_id: str | None) -> None:
    """Persist the selected option identifier for the active question."""

    initialize_session_state()
    st.session_state[QUESTION_SELECTION_KEY] = _string_or_none(option_id)


def set_current_question(question: Question, alternatives: list[DisplayAlternative]) -> None:
    """Store the active question and reset submission-specific state."""

    initialize_session_state()
    st.session_state[CURRENT_QUESTION_ID_KEY] = question.id_question
    st.session_state[CURRENT_QUESTION_KEY] = _serialize_question(question)
    st.session_state[CURRENT_ALTERNATIVES_KEY] = [
        {
            "option_id": alternative.option_id,
            "alternative_text": alternative.alternative_text,
            "explanation": alternative.explanation,
            "is_correct": alternative.is_correct,
        }
        for alternative in alternatives
    ]
    st.session_state[QUESTION_STARTED_AT_KEY] = utc_now()
    st.session_state[QUESTION_ANSWERED_KEY] = False
    st.session_state[LAST_ANSWER_RESULT_KEY] = None
    st.session_state[QUESTION_SELECTION_KEY] = None
    st.session_state[SUBMISSION_IN_PROGRESS_KEY] = False


def get_question_pool() -> list[Question]:
    """Return the prefetched question pool for the current session scope."""

    initialize_session_state()
    raw_pool = st.session_state[QUESTION_POOL_KEY]
    if not isinstance(raw_pool, list):
        return []
    return [
        question
        for question in (_deserialize_question(item) for item in raw_pool)
        if question is not None
    ]


def get_question_pool_scope() -> str | None:
    """Return the scope signature attached to the current prefetched question pool."""

    initialize_session_state()
    return _string_or_none(st.session_state[QUESTION_POOL_SCOPE_KEY])


def ensure_question_pool_scope(scope_key: str | None) -> None:
    """Reset the prefetched question pool when the active question scope changes."""

    initialize_session_state()
    normalized_scope_key = _string_or_none(scope_key)
    if st.session_state[QUESTION_POOL_SCOPE_KEY] == normalized_scope_key:
        return
    st.session_state[QUESTION_POOL_SCOPE_KEY] = normalized_scope_key
    st.session_state[QUESTION_POOL_KEY] = []


def set_question_pool(
    questions: list[Question],
    *,
    scope_key: str | None = None,
) -> None:
    """Persist the prefetched question pool for the current session scope."""

    initialize_session_state()
    if scope_key is not None:
        st.session_state[QUESTION_POOL_SCOPE_KEY] = _string_or_none(scope_key)
    st.session_state[QUESTION_POOL_KEY] = [_serialize_question(question) for question in questions]


def clear_current_question() -> None:
    """Clear the active question so a new one can be selected."""

    initialize_session_state()
    st.session_state[CURRENT_QUESTION_ID_KEY] = None
    st.session_state[CURRENT_QUESTION_KEY] = None
    st.session_state[CURRENT_ALTERNATIVES_KEY] = []
    st.session_state[QUESTION_STARTED_AT_KEY] = None
    st.session_state[QUESTION_ANSWERED_KEY] = False
    st.session_state[LAST_ANSWER_RESULT_KEY] = None
    st.session_state[QUESTION_SELECTION_KEY] = None
    st.session_state[SUBMISSION_IN_PROGRESS_KEY] = False


def get_question_started_at() -> datetime | None:
    """Return the UTC timestamp when the current question was shown."""

    initialize_session_state()
    value = st.session_state[QUESTION_STARTED_AT_KEY]
    return value if isinstance(value, datetime) else None


def is_current_question_answered() -> bool:
    """Return whether the current question was already submitted."""

    initialize_session_state()
    return bool(st.session_state[QUESTION_ANSWERED_KEY])


def is_submission_in_progress() -> bool:
    """Return whether a submission is currently being processed."""

    initialize_session_state()
    return bool(st.session_state[SUBMISSION_IN_PROGRESS_KEY])


def start_submission() -> None:
    """Set the transient submission lock."""

    initialize_session_state()
    st.session_state[SUBMISSION_IN_PROGRESS_KEY] = True


def finish_submission() -> None:
    """Release the transient submission lock."""

    initialize_session_state()
    st.session_state[SUBMISSION_IN_PROGRESS_KEY] = False


def mark_question_answered(
    evaluation: AnswerEvaluation,
    *,
    selected_option_id: str,
) -> None:
    """Persist the latest submission outcome in session state."""

    initialize_session_state()
    st.session_state[QUESTION_ANSWERED_KEY] = True
    st.session_state[SUBMISSION_IN_PROGRESS_KEY] = False
    st.session_state[LAST_ANSWER_RESULT_KEY] = {
        "id_question": evaluation.record.id_question,
        "selected_option_id": selected_option_id,
        "selected_alternative_text": evaluation.record.selected_alternative_text,
        "correct_alternative_text": evaluation.record.correct_alternative_text,
        "is_correct": evaluation.record.is_correct,
        "feedback_message": evaluation.feedback_message,
        "correct_explanation": evaluation.correct_explanation,
        "selected_explanation": evaluation.selected_explanation,
        "time_spent_seconds": evaluation.record.time_spent_seconds,
    }


def get_last_answer_result() -> dict[str, object] | None:
    """Return the latest stored answer result for the current question."""

    initialize_session_state()
    value = st.session_state[LAST_ANSWER_RESULT_KEY]
    return value if isinstance(value, dict) else None


def get_skipped_question_ids() -> set[int]:
    """Return the questions skipped during the current browser session."""

    initialize_session_state()
    raw_ids = st.session_state[SKIPPED_QUESTION_IDS_KEY]
    if not isinstance(raw_ids, list):
        return set()
    return {int(value) for value in raw_ids if value is not None}


def get_invalid_question_ids() -> set[int]:
    """Return question IDs rejected during the current browser session."""

    initialize_session_state()
    raw_ids = st.session_state[INVALID_QUESTION_IDS_KEY]
    if not isinstance(raw_ids, list):
        return set()
    return {int(value) for value in raw_ids if value is not None}


def mark_question_invalid(id_question: int) -> None:
    """Prevent a malformed question row from being selected again this session."""

    invalid_ids = get_invalid_question_ids()
    invalid_ids.add(id_question)
    st.session_state[INVALID_QUESTION_IDS_KEY] = sorted(invalid_ids)


def mark_question_skipped(id_question: int) -> None:
    """Remember a skipped question so the next selection prefers a different one."""

    skipped_ids = get_skipped_question_ids()
    skipped_ids.add(id_question)
    st.session_state[SKIPPED_QUESTION_IDS_KEY] = sorted(skipped_ids)


def clear_question_skip(id_question: int) -> None:
    """Remove a question from the skipped pool after it is answered."""

    skipped_ids = get_skipped_question_ids()
    if id_question in skipped_ids:
        skipped_ids.remove(id_question)
        st.session_state[SKIPPED_QUESTION_IDS_KEY] = sorted(skipped_ids)


def get_subject_filter() -> str | None:
    """Return the selected subject filter, or None for all subjects."""

    subject_filters = get_subject_filters()
    topic_filters = get_topic_filters()
    if len(subject_filters) == 1 and not topic_filters:
        return subject_filters[0]
    initialize_session_state()
    value = _string_or_none(st.session_state[SUBJECT_FILTER_KEY])
    if value is None or value == "Todas":
        return None
    return value


def get_subject_filter_label() -> str:
    """Return the display label for the selected subject filter."""

    return get_subject_filter() or "Todas"


def set_subject_filter(subject: str | None) -> None:
    """Persist the selected subject filter."""

    initialize_session_state()
    normalized_subject = _string_or_none(subject)
    st.session_state[SUBJECT_FILTER_KEY] = normalized_subject or "Todas"
    st.session_state[SUBJECT_FILTERS_KEY] = [normalized_subject] if normalized_subject else []
    st.session_state[TOPIC_FILTERS_KEY] = []


def get_topic_filter() -> str | None:
    """Return the selected topic filter, or None for all topics."""

    topic_filters = get_topic_filters()
    subject_filters = get_subject_filters()
    if len(topic_filters) == 1 and not subject_filters:
        return topic_filters[0][1]
    initialize_session_state()
    return _string_or_none(st.session_state[TOPIC_FILTER_KEY])


def set_topic_filter(topic: str | None) -> None:
    """Persist the selected topic filter."""

    initialize_session_state()
    normalized_topic = _string_or_none(topic)
    st.session_state[TOPIC_FILTER_KEY] = normalized_topic
    st.session_state[TOPIC_FILTERS_KEY] = []
    if normalized_topic:
        subject = get_subject_filter()
        if subject:
            st.session_state[TOPIC_FILTERS_KEY] = [(subject, normalized_topic)]
    st.session_state[SUBJECT_FILTERS_KEY] = [get_subject_filter()] if get_subject_filter() else []


def get_subject_filters() -> tuple[str, ...]:
    """Return the selected full-subject filters for the learner screen."""

    initialize_session_state()
    raw_subjects = st.session_state[SUBJECT_FILTERS_KEY]
    if not isinstance(raw_subjects, list):
        return ()
    normalized_subjects = sorted(
        {
            normalized_subject
            for subject in raw_subjects
            for normalized_subject in [_string_or_none(subject)]
            if normalized_subject
        },
        key=str.casefold,
    )
    return tuple(normalized_subjects)


def set_subject_filters(subjects: list[str] | tuple[str, ...] | set[str]) -> None:
    """Persist the selected full-subject filters for the learner screen."""

    initialize_session_state()
    normalized_subjects = sorted(
        {
            normalized_subject
            for subject in subjects
            for normalized_subject in [_string_or_none(subject)]
            if normalized_subject
        },
        key=str.casefold,
    )
    st.session_state[SUBJECT_FILTERS_KEY] = normalized_subjects
    st.session_state[SUBJECT_FILTER_KEY] = normalized_subjects[0] if len(normalized_subjects) == 1 else "Todas"


def get_topic_filters() -> tuple[tuple[str, str], ...]:
    """Return the selected specific topic filters for the learner screen."""

    initialize_session_state()
    raw_topics = st.session_state[TOPIC_FILTERS_KEY]
    if not isinstance(raw_topics, list):
        return ()

    normalized_topics = sorted(
        {
            (normalized_subject, normalized_topic)
            for item in raw_topics
            if isinstance(item, (list, tuple)) and len(item) == 2
            for normalized_subject in [_string_or_none(item[0])]
            for normalized_topic in [_string_or_none(item[1])]
            if normalized_subject and normalized_topic
        },
        key=lambda item: (item[0].casefold(), item[1].casefold()),
    )
    return tuple(normalized_topics)


def set_topic_filters(topics: list[tuple[str, str]] | tuple[tuple[str, str], ...] | set[tuple[str, str]]) -> None:
    """Persist the selected topic-level filters for the learner screen."""

    initialize_session_state()
    normalized_topics = sorted(
        {
            (normalized_subject, normalized_topic)
            for item in topics
            if len(item) == 2
            for normalized_subject in [_string_or_none(item[0])]
            for normalized_topic in [_string_or_none(item[1])]
            if normalized_subject and normalized_topic
        },
        key=lambda item: (item[0].casefold(), item[1].casefold()),
    )
    st.session_state[TOPIC_FILTERS_KEY] = normalized_topics
    st.session_state[TOPIC_FILTER_KEY] = normalized_topics[0][1] if len(normalized_topics) == 1 else None


def get_project_filter() -> str | None:
    """Return the selected project filter, or None when unset."""

    initialize_session_state()
    return _string_or_none(st.session_state[PROJECT_FILTER_KEY])


def set_project_filter(project: str | None) -> None:
    """Persist the selected project filter."""

    initialize_session_state()
    st.session_state[PROJECT_FILTER_KEY] = _string_or_none(project)


def _bind_authenticated_user_email(user_email: str) -> None:
    initialize_session_state()
    current_email = st.session_state[AUTHENTICATED_USER_EMAIL_KEY]
    if current_email == user_email:
        return

    st.session_state[AUTHENTICATED_USER_EMAIL_KEY] = user_email
    st.session_state[AUTHENTICATED_USER_SCOPE_KEY] = None
    st.session_state[AUTHENTICATED_USER_KEY] = None
    st.session_state[AUTHENTICATED_RUN_LOGGED_KEY] = False
    st.session_state[CURRENT_WORKSPACE_KEY] = "student"
    st.session_state[CURRENT_STUDENT_VIEW_KEY] = "practice"
    st.session_state[CURRENT_PROFESSOR_TOOL_KEY] = None
    st.session_state[PROFESSOR_AUTHORING_AI_ASSISTED_KEY] = False
    st.session_state[PROFESSOR_NOTICE_KEY] = None
    st.session_state[SESSION_ID_KEY] = uuid4().hex
    st.session_state[SKIPPED_QUESTION_IDS_KEY] = []
    st.session_state[INVALID_QUESTION_IDS_KEY] = []
    st.session_state[USER_PROGRESS_SNAPSHOT_KEY] = None
    st.session_state[USER_PROGRESS_ISSUES_KEY] = []
    st.session_state[USER_PROGRESS_LOADED_KEY] = False
    st.session_state[USER_ANSWERED_QUESTION_IDS_KEY] = []
    st.session_state[SUBJECT_FILTER_KEY] = "Todas"
    st.session_state[TOPIC_FILTER_KEY] = None
    st.session_state[SUBJECT_FILTERS_KEY] = []
    st.session_state[TOPIC_FILTERS_KEY] = []
    st.session_state[PROJECT_FILTER_KEY] = None
    st.session_state[QUESTION_POOL_KEY] = []
    st.session_state[QUESTION_POOL_SCOPE_KEY] = None
    st.session_state[LEADERBOARD_RANK_KEY] = None
    st.session_state[LEADERBOARD_TOTAL_USERS_KEY] = 0
    st.session_state[LEADERBOARD_ISSUES_KEY] = []
    st.session_state[LEADERBOARD_LOADED_KEY] = False
    clear_current_question()


def _serialize_question(question: Question) -> dict[str, object]:
    return {
        "id_question": question.id_question,
        "statement": question.statement,
        "correct_answer": {
            "alternative_text": question.correct_answer.alternative_text,
            "explanation": question.correct_answer.explanation,
        },
        "wrong_answers": [
            {
                "alternative_text": wrong_answer.alternative_text,
                "explanation": wrong_answer.explanation,
            }
            for wrong_answer in question.wrong_answers
        ],
        "subject": question.subject,
        "topic": question.topic,
        "difficulty": question.difficulty,
        "source": question.source,
        "cohort_key": question.cohort_key,
        "created_at_utc": question.created_at_utc,
        "updated_at_utc": question.updated_at_utc,
    }


def _deserialize_question(raw_question: object) -> Question | None:
    if not isinstance(raw_question, dict):
        return None

    try:
        raw_correct = raw_question["correct_answer"]
        raw_wrong_answers = raw_question["wrong_answers"]
        if not isinstance(raw_correct, dict) or not isinstance(raw_wrong_answers, list):
            return None

        return Question(
            id_question=int(raw_question["id_question"]),
            statement=str(raw_question["statement"]),
            correct_answer=QuestionAlternative(
                alternative_text=str(raw_correct["alternative_text"]),
                explanation=_string_or_none(raw_correct.get("explanation")),
            ),
            wrong_answers=tuple(
                QuestionAlternative(
                    alternative_text=str(item["alternative_text"]),
                    explanation=_string_or_none(item.get("explanation")),
                )
                for item in raw_wrong_answers
                if isinstance(item, dict) and "alternative_text" in item
            ),
            subject=_string_or_none(raw_question.get("subject")),
            topic=_string_or_none(raw_question.get("topic")),
            difficulty=_string_or_none(raw_question.get("difficulty")),
            source=_string_or_none(raw_question.get("source")),
            cohort_key=_string_or_none(raw_question.get("cohort_key")),
            created_at_utc=raw_question.get("created_at_utc") if isinstance(raw_question.get("created_at_utc"), datetime) else None,
            updated_at_utc=raw_question.get("updated_at_utc") if isinstance(raw_question.get("updated_at_utc"), datetime) else None,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_local_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = _string_or_none(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _answer_activity_date(answer: AnswerAttempt) -> date:
    if answer.answered_at_local is not None:
        return answer.answered_at_local.date()
    return answer.answered_at_utc.date()
