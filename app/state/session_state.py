from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import streamlit as st

from modules.domain.models import AnswerEvaluation, DisplayAlternative
from modules.utils.datetime_utils import utc_now

SESSION_ID_KEY = "glipmath_session_id"
CURRENT_QUESTION_ID_KEY = "glipmath_current_question_id"
CURRENT_ALTERNATIVES_KEY = "glipmath_current_alternatives"
QUESTION_STARTED_AT_KEY = "glipmath_question_started_at"
QUESTION_ANSWERED_KEY = "glipmath_question_answered"
LAST_ANSWER_RESULT_KEY = "glipmath_last_answer_result"
QUESTION_SELECTION_KEY = "glipmath_question_selection"
SUBMISSION_IN_PROGRESS_KEY = "glipmath_submission_in_progress"
SKIPPED_QUESTION_IDS_KEY = "glipmath_skipped_question_ids"
THEME_MODE_KEY = "glipmath_theme_mode"


def initialize_session_state() -> None:
    """Ensure all GlipMath session keys exist."""

    st.session_state.setdefault(SESSION_ID_KEY, uuid4().hex)
    st.session_state.setdefault(CURRENT_QUESTION_ID_KEY, None)
    st.session_state.setdefault(CURRENT_ALTERNATIVES_KEY, [])
    st.session_state.setdefault(QUESTION_STARTED_AT_KEY, None)
    st.session_state.setdefault(QUESTION_ANSWERED_KEY, False)
    st.session_state.setdefault(LAST_ANSWER_RESULT_KEY, None)
    st.session_state.setdefault(QUESTION_SELECTION_KEY, None)
    st.session_state.setdefault(SUBMISSION_IN_PROGRESS_KEY, False)
    st.session_state.setdefault(SKIPPED_QUESTION_IDS_KEY, [])
    st.session_state.setdefault(THEME_MODE_KEY, "dark")


def get_session_id() -> str:
    """Return the stable session identifier for the current browser session."""

    initialize_session_state()
    return str(st.session_state[SESSION_ID_KEY])


def get_current_question_id() -> int | None:
    """Return the current question identifier from session state."""

    initialize_session_state()
    value = st.session_state[CURRENT_QUESTION_ID_KEY]
    return int(value) if value is not None else None


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


def set_current_question(id_question: int, alternatives: list[DisplayAlternative]) -> None:
    """Store the active question and reset submission-specific state."""

    initialize_session_state()
    st.session_state[CURRENT_QUESTION_ID_KEY] = id_question
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


def get_theme_mode() -> str:
    """Return the current UI theme mode."""

    initialize_session_state()
    mode = str(st.session_state[THEME_MODE_KEY]).strip().lower()
    return "light" if mode == "light" else "dark"


def set_theme_mode(mode: str) -> None:
    """Persist the selected UI theme mode."""

    initialize_session_state()
    st.session_state[THEME_MODE_KEY] = "light" if mode == "light" else "dark"


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
