from __future__ import annotations

import streamlit as st

from app.components.header import PracticeHeaderMetrics, render_question_header
from app.components.navigation import clear_query_param, get_query_param
from app.components.question_card import (
    render_bottom_action_bar,
    render_empty_question_state,
    render_question_content,
)
from app.state.session_state import (
    append_user_answer_attempt,
    clear_question_skip,
    clear_current_question,
    get_last_answer_result,
    get_question_selection,
    get_question_started_at,
    get_session_id,
    get_subject_filter_label,
    initialize_session_state,
    is_current_question_answered,
    mark_question_answered,
    mark_question_skipped,
    set_question_selection,
    set_subject_filter,
)
from modules.auth.auth_service import trigger_logout
from modules.config.settings import AppSettings
from modules.domain.models import DisplayAlternative, Question, User
from modules.services.answer_service import AnswerService
from modules.services.question_service import find_display_alternative
from modules.storage.bigquery_client import BigQueryError
from modules.utils.datetime_utils import utc_now


def render_main_page(
    *,
    settings: AppSettings,
    user: User,
    current_question: Question | None,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    subject_options: list[str],
    header_metrics: PracticeHeaderMetrics,
) -> None:
    """Render the authenticated application page."""

    initialize_session_state()
    question_answered = is_current_question_answered()
    last_result = get_last_answer_result()

    elapsed_seconds = _current_elapsed_seconds(last_result, question_answered)
    selected_subject = render_question_header(
        base_dir=str(settings.repository_root),
        subject_options=subject_options,
        selected_subject=get_subject_filter_label(),
        metrics=header_metrics,
        elapsed_seconds=elapsed_seconds,
        timer_running=bool(current_question is not None and not question_answered),
    )
    if selected_subject != get_subject_filter_label():
        set_subject_filter(None if selected_subject == "Todas" else selected_subject)
        clear_current_question()
        st.rerun()

    if _handle_page_action(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
    ):
        st.stop()

    question_answered = is_current_question_answered()
    last_result = get_last_answer_result()
    selected_option_id = _current_selected_option_id(
        current_question=current_question,
        question_answered=question_answered,
        last_result=last_result,
    )

    if current_question is None:
        render_empty_question_state("Nenhuma questão ativa e válida está disponível para esse filtro no momento.")
        return

    render_question_content(
        question=current_question,
        alternatives=alternatives,
        selected_option_id=selected_option_id,
        question_answered=question_answered,
        is_correct=_result_is_correct(last_result) if question_answered else None,
    )
    render_bottom_action_bar(
        question_answered=question_answered,
        has_selection=selected_option_id is not None,
        is_correct=_result_is_correct(last_result) if question_answered else None,
    )


def _handle_page_action(
    *,
    user: User,
    current_question: Question | None,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
) -> bool:
    """Handle query-driven page actions before the main screen renders."""

    pending_selection = get_query_param("glipmath_select")
    if pending_selection and current_question is not None and not is_current_question_answered():
        if find_display_alternative(alternatives, pending_selection) is not None:
            set_question_selection(pending_selection)
    if pending_selection:
        clear_query_param("glipmath_select")

    action = get_query_param("glipmath_action")
    if action is None:
        return False
    clear_query_param("glipmath_action")

    if action == "logout":
        trigger_logout()
        return True

    if current_question is None:
        return False

    if action == "skip" and not is_current_question_answered():
        mark_question_skipped(current_question.id_question)
        clear_current_question()
        st.rerun()
        return True

    if action == "next" and is_current_question_answered():
        clear_current_question()
        st.rerun()
        return True

    if action != "submit" or is_current_question_answered():
        return False

    selected_option_id = get_question_selection()
    selected_alternative = find_display_alternative(alternatives, selected_option_id)
    if selected_alternative is None:
        return False

    started_at = get_question_started_at() or utc_now()
    elapsed_seconds = max((utc_now() - started_at).total_seconds(), 0.0)
    try:
        evaluation = answer_service.submit_answer(
            user=user,
            question=current_question,
            selected_alternative=selected_alternative,
            session_id=get_session_id(),
            time_spent_seconds=elapsed_seconds,
        )
    except (BigQueryError, ValueError) as exc:
        st.error(f"Não foi possível registrar a resposta: {exc}")
        return False

    clear_question_skip(current_question.id_question)
    append_user_answer_attempt(user.email, evaluation.record)
    mark_question_answered(evaluation, selected_option_id=selected_alternative.option_id)
    st.rerun()
    return True


def _current_selected_option_id(
    *,
    current_question: Question | None,
    question_answered: bool,
    last_result: dict[str, object] | None,
) -> str | None:
    if (
        question_answered
        and current_question is not None
        and last_result
        and last_result.get("id_question") == current_question.id_question
    ):
        selected_option_id = last_result.get("selected_option_id")
        return str(selected_option_id) if selected_option_id is not None else None
    return get_question_selection()


def _current_elapsed_seconds(
    last_result: dict[str, object] | None,
    question_answered: bool,
) -> float:
    if question_answered and last_result:
        try:
            return max(float(last_result.get("time_spent_seconds", 0.0) or 0.0), 0.0)
        except (TypeError, ValueError):
            return 0.0

    started_at = get_question_started_at()
    if started_at is None:
        return 0.0
    return max((utc_now() - started_at).total_seconds(), 0.0)


def _result_is_correct(last_result: dict[str, object] | None) -> bool:
    return bool(last_result and last_result.get("is_correct"))
