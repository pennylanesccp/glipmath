from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import streamlit as st

from modules.domain.models import AnswerAttempt, AnswerEvaluation, DisplayAlternative, Question, QuestionAlternative, User
from modules.services.answer_service import append_answer_history, extract_answered_question_ids
from modules.utils.datetime_utils import utc_now

SESSION_ID_KEY = "glipmath_session_id"
AUTHENTICATED_USER_EMAIL_KEY = "glipmath_authenticated_user_email"
AUTHENTICATED_USER_SCOPE_KEY = "glipmath_authenticated_user_scope"
AUTHENTICATED_RUN_LOGGED_KEY = "glipmath_authenticated_run_logged"
CURRENT_QUESTION_ID_KEY = "glipmath_current_question_id"
CURRENT_QUESTION_KEY = "glipmath_current_question"
CURRENT_ALTERNATIVES_KEY = "glipmath_current_alternatives"
QUESTION_STARTED_AT_KEY = "glipmath_question_started_at"
QUESTION_ANSWERED_KEY = "glipmath_question_answered"
LAST_ANSWER_RESULT_KEY = "glipmath_last_answer_result"
QUESTION_SELECTION_KEY = "glipmath_question_selection"
SUBMISSION_IN_PROGRESS_KEY = "glipmath_submission_in_progress"
SKIPPED_QUESTION_IDS_KEY = "glipmath_skipped_question_ids"
INVALID_QUESTION_IDS_KEY = "glipmath_invalid_question_ids"
USER_ANSWER_HISTORY_KEY = "glipmath_user_answer_history"
USER_ANSWER_HISTORY_ISSUES_KEY = "glipmath_user_answer_history_issues"
USER_ANSWER_HISTORY_LOADED_KEY = "glipmath_user_answer_history_loaded"
USER_ANSWERED_QUESTION_IDS_KEY = "glipmath_user_answered_question_ids"
SUBJECT_FILTER_KEY = "glipmath_subject_filter"
PROJECT_FILTER_KEY = "glipmath_project_filter"


def initialize_session_state() -> None:
    """Ensure all GlipMath session keys exist."""

    st.session_state.setdefault(SESSION_ID_KEY, uuid4().hex)
    st.session_state.setdefault(AUTHENTICATED_USER_EMAIL_KEY, None)
    st.session_state.setdefault(AUTHENTICATED_USER_SCOPE_KEY, None)
    st.session_state.setdefault(AUTHENTICATED_RUN_LOGGED_KEY, False)
    st.session_state.setdefault(CURRENT_QUESTION_ID_KEY, None)
    st.session_state.setdefault(CURRENT_QUESTION_KEY, None)
    st.session_state.setdefault(CURRENT_ALTERNATIVES_KEY, [])
    st.session_state.setdefault(QUESTION_STARTED_AT_KEY, None)
    st.session_state.setdefault(QUESTION_ANSWERED_KEY, False)
    st.session_state.setdefault(LAST_ANSWER_RESULT_KEY, None)
    st.session_state.setdefault(QUESTION_SELECTION_KEY, None)
    st.session_state.setdefault(SUBMISSION_IN_PROGRESS_KEY, False)
    st.session_state.setdefault(SKIPPED_QUESTION_IDS_KEY, [])
    st.session_state.setdefault(INVALID_QUESTION_IDS_KEY, [])
    st.session_state.setdefault(USER_ANSWER_HISTORY_KEY, [])
    st.session_state.setdefault(USER_ANSWER_HISTORY_ISSUES_KEY, [])
    st.session_state.setdefault(USER_ANSWER_HISTORY_LOADED_KEY, False)
    st.session_state.setdefault(USER_ANSWERED_QUESTION_IDS_KEY, [])
    st.session_state.setdefault(SUBJECT_FILTER_KEY, "Todas")
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
    st.session_state[AUTHENTICATED_RUN_LOGGED_KEY] = False
    st.session_state[SESSION_ID_KEY] = uuid4().hex
    st.session_state[SKIPPED_QUESTION_IDS_KEY] = []
    st.session_state[INVALID_QUESTION_IDS_KEY] = []
    st.session_state[USER_ANSWER_HISTORY_KEY] = []
    st.session_state[USER_ANSWER_HISTORY_ISSUES_KEY] = []
    st.session_state[USER_ANSWER_HISTORY_LOADED_KEY] = False
    st.session_state[USER_ANSWERED_QUESTION_IDS_KEY] = []
    st.session_state[SUBJECT_FILTER_KEY] = "Todas"
    st.session_state[PROJECT_FILTER_KEY] = None
    clear_current_question()


def has_loaded_user_answer_history(user_email: str) -> bool:
    """Return whether the current user's answer snapshot is already in session."""

    initialize_session_state()
    return (
        st.session_state[AUTHENTICATED_USER_EMAIL_KEY] == user_email
        and bool(st.session_state[USER_ANSWER_HISTORY_LOADED_KEY])
    )


def has_logged_authenticated_run() -> bool:
    """Return whether the current authenticated session already emitted its startup log."""

    initialize_session_state()
    return bool(st.session_state[AUTHENTICATED_RUN_LOGGED_KEY])


def mark_authenticated_run_logged() -> None:
    """Mark the current authenticated session startup as already logged."""

    initialize_session_state()
    st.session_state[AUTHENTICATED_RUN_LOGGED_KEY] = True


def set_user_answer_history(
    user_email: str,
    answers: list[AnswerAttempt],
    *,
    issues: list[str] | None = None,
) -> None:
    """Persist the current user's parsed answer history in session state."""

    _bind_authenticated_user_email(user_email)
    st.session_state[USER_ANSWER_HISTORY_KEY] = list(answers)
    st.session_state[USER_ANSWER_HISTORY_ISSUES_KEY] = list(issues or [])
    st.session_state[USER_ANSWER_HISTORY_LOADED_KEY] = True
    st.session_state[USER_ANSWERED_QUESTION_IDS_KEY] = sorted(extract_answered_question_ids(answers))


def get_user_answer_history(user_email: str) -> list[AnswerAttempt]:
    """Return the current user's parsed answer history from session state."""

    if not has_loaded_user_answer_history(user_email):
        return []
    raw_answers = st.session_state[USER_ANSWER_HISTORY_KEY]
    if not isinstance(raw_answers, list):
        return []
    return [answer for answer in raw_answers if isinstance(answer, AnswerAttempt)]


def get_user_answer_history_issues(user_email: str) -> list[str]:
    """Return any issues found while loading the user's answer snapshot."""

    if not has_loaded_user_answer_history(user_email):
        return []
    raw_issues = st.session_state[USER_ANSWER_HISTORY_ISSUES_KEY]
    if not isinstance(raw_issues, list):
        return []
    return [str(issue) for issue in raw_issues]


def append_user_answer_attempt(user_email: str, answer: AnswerAttempt) -> None:
    """Append one new answer attempt to the current user's in-session history."""

    _bind_authenticated_user_email(user_email)
    updated_answers = append_answer_history(get_user_answer_history(user_email), answer)
    st.session_state[USER_ANSWER_HISTORY_KEY] = updated_answers
    st.session_state[USER_ANSWERED_QUESTION_IDS_KEY] = sorted(extract_answered_question_ids(updated_answers))
    st.session_state[USER_ANSWER_HISTORY_LOADED_KEY] = True


def get_answered_question_ids(user_email: str) -> set[int]:
    """Return the answered question IDs for the current authenticated user."""

    if not has_loaded_user_answer_history(user_email):
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
    raw_question = st.session_state[CURRENT_QUESTION_KEY]
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
    st.session_state[CURRENT_QUESTION_KEY] = {
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
    st.session_state[SUBJECT_FILTER_KEY] = _string_or_none(subject) or "Todas"


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
    st.session_state[AUTHENTICATED_RUN_LOGGED_KEY] = False
    st.session_state[SESSION_ID_KEY] = uuid4().hex
    st.session_state[SKIPPED_QUESTION_IDS_KEY] = []
    st.session_state[INVALID_QUESTION_IDS_KEY] = []
    st.session_state[USER_ANSWER_HISTORY_KEY] = []
    st.session_state[USER_ANSWER_HISTORY_ISSUES_KEY] = []
    st.session_state[USER_ANSWER_HISTORY_LOADED_KEY] = False
    st.session_state[USER_ANSWERED_QUESTION_IDS_KEY] = []
    st.session_state[SUBJECT_FILTER_KEY] = "Todas"
    st.session_state[PROJECT_FILTER_KEY] = None
    clear_current_question()


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
