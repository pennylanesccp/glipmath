from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import streamlit as st

from modules.domain.models import AnswerEvaluation
from modules.utils.datetime_utils import utc_now

SESSION_ID_KEY = "glipmath_session_id"
CURRENT_QUESTION_ID_KEY = "glipmath_current_question_id"
QUESTION_STARTED_AT_KEY = "glipmath_question_started_at"
QUESTION_ANSWERED_KEY = "glipmath_question_answered"
LAST_ANSWER_RESULT_KEY = "glipmath_last_answer_result"
QUESTION_SELECTION_KEY = "glipmath_question_selection"


def initialize_session_state() -> None:
    """Ensure all GlipMath session keys exist."""

    st.session_state.setdefault(SESSION_ID_KEY, uuid4().hex)
    st.session_state.setdefault(CURRENT_QUESTION_ID_KEY, None)
    st.session_state.setdefault(QUESTION_STARTED_AT_KEY, None)
    st.session_state.setdefault(QUESTION_ANSWERED_KEY, False)
    st.session_state.setdefault(LAST_ANSWER_RESULT_KEY, None)
    st.session_state.setdefault(QUESTION_SELECTION_KEY, None)


def get_session_id() -> str:
    """Return the stable session identifier for the current browser session."""

    initialize_session_state()
    return str(st.session_state[SESSION_ID_KEY])


def get_current_question_id() -> int | None:
    """Return the current question identifier from session state."""

    initialize_session_state()
    value = st.session_state[CURRENT_QUESTION_ID_KEY]
    return int(value) if value is not None else None


def set_current_question(id_question: int) -> None:
    """Store the active question and reset submission-specific state."""

    initialize_session_state()
    st.session_state[CURRENT_QUESTION_ID_KEY] = id_question
    st.session_state[QUESTION_STARTED_AT_KEY] = utc_now()
    st.session_state[QUESTION_ANSWERED_KEY] = False
    st.session_state[LAST_ANSWER_RESULT_KEY] = None
    st.session_state[QUESTION_SELECTION_KEY] = None


def clear_current_question() -> None:
    """Clear the active question so a new one can be selected."""

    initialize_session_state()
    st.session_state[CURRENT_QUESTION_ID_KEY] = None
    st.session_state[QUESTION_STARTED_AT_KEY] = None
    st.session_state[QUESTION_ANSWERED_KEY] = False
    st.session_state[LAST_ANSWER_RESULT_KEY] = None
    st.session_state[QUESTION_SELECTION_KEY] = None


def get_question_started_at() -> datetime | None:
    """Return the UTC timestamp when the current question was shown."""

    initialize_session_state()
    value = st.session_state[QUESTION_STARTED_AT_KEY]
    return value if isinstance(value, datetime) else None


def is_current_question_answered() -> bool:
    """Return whether the current question was already submitted."""

    initialize_session_state()
    return bool(st.session_state[QUESTION_ANSWERED_KEY])


def mark_question_answered(evaluation: AnswerEvaluation) -> None:
    """Persist the latest submission outcome in session state."""

    initialize_session_state()
    st.session_state[QUESTION_ANSWERED_KEY] = True
    st.session_state[LAST_ANSWER_RESULT_KEY] = {
        "id_question": evaluation.record.id_question,
        "selected_choice": evaluation.record.selected_choice,
        "correct_choice": evaluation.record.correct_choice,
        "is_correct": evaluation.record.is_correct,
        "feedback_message": evaluation.feedback_message,
    }


def get_last_answer_result() -> dict[str, object] | None:
    """Return the latest stored answer result for the current question."""

    initialize_session_state()
    value = st.session_state[LAST_ANSWER_RESULT_KEY]
    return value if isinstance(value, dict) else None
