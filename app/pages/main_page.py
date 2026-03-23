from __future__ import annotations

import streamlit as st

from app.state.session_state import (
    append_user_answer_attempt,
    clear_current_question,
    clear_question_skip,
    get_last_answer_result,
    get_question_selection,
    get_question_started_at,
    get_session_id,
    initialize_session_state,
    is_current_question_answered,
    is_submission_in_progress,
    mark_question_answered,
    mark_question_skipped,
    set_question_selection,
    set_subject_filter,
    start_submission,
    finish_submission,
)
from app.ui.question_session import (
    build_page_href,
    normalize_subject_filter,
    render_question_session_template,
    text_to_html,
)
from modules.auth.auth_service import trigger_logout
from modules.domain.models import DisplayAlternative, Question, User
from modules.services.answer_service import AnswerService
from modules.services.question_service import find_display_alternative
from modules.storage.bigquery_client import BigQueryError
from modules.utils.datetime_utils import utc_now


def render_main_page(
    *,
    user: User,
    current_question: Question | None,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    subject_options: list[str],
    selected_subject: str,
    day_streak: int,
    question_streak: int,
    leaderboard_position: str,
) -> None:
    """Render and drive the authenticated question/session page."""

    initialize_session_state()
    normalized_subject = _normalize_selected_subject(selected_subject, subject_options)
    _consume_page_actions(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        subject_options=subject_options,
        selected_subject=normalized_subject,
    )

    question_answered = is_current_question_answered()
    last_result = get_last_answer_result()
    selected_option_id = _selected_option_id_for_render(current_question.id_question if current_question else None)
    elapsed_seconds = _resolve_elapsed_seconds(
        question_answered=question_answered,
        last_result=last_result,
    )
    answer_is_correct = bool(last_result.get("is_correct")) if last_result else False

    if current_question is None:
        page_html = render_question_session_template(
            selected_subject=normalized_subject,
            subject_options=subject_options,
            streak_text=_format_streak_text(day_streak, question_streak),
            rank_text=_format_rank_text(leaderboard_position),
            timer_elapsed_seconds=0,
            timer_running=False,
            logout_href=build_page_href(
                subject=normalized_subject,
                action="logout",
            ),
            question_statement_html=text_to_html("Nenhuma questao disponivel para esse filtro agora."),
            alternatives=[],
            selected_option_id=None,
            question_answered=False,
            answer_is_correct=False,
            empty_state_html=(
                '<div class="gm-info-card">'
                f"{text_to_html('Troque a disciplina acima ou carregue mais questoes.')}"
                "</div>"
            ),
        )
        st.markdown(page_html, unsafe_allow_html=True)
        return

    page_html = render_question_session_template(
        selected_subject=normalized_subject,
        subject_options=subject_options,
        streak_text=_format_streak_text(day_streak, question_streak),
        rank_text=_format_rank_text(leaderboard_position),
        timer_elapsed_seconds=elapsed_seconds,
        timer_running=not question_answered,
        logout_href=build_page_href(
            subject=normalized_subject,
            action="logout",
        ),
        question_statement_html=text_to_html(current_question.statement),
        alternatives=alternatives,
        selected_option_id=selected_option_id,
        question_answered=question_answered,
        answer_is_correct=answer_is_correct,
    )
    st.markdown(page_html, unsafe_allow_html=True)


def _consume_page_actions(
    *,
    user: User,
    current_question: Question | None,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    subject_options: list[str],
    selected_subject: str,
) -> None:
    requested_subject = _normalize_selected_subject(_get_query_value("subject"), subject_options)
    if requested_subject != selected_subject:
        set_subject_filter(None if requested_subject == "Todas" else requested_subject)
        clear_current_question()
        _reset_page_query_params(subject=requested_subject)
        st.rerun()

    selected_option_id = _get_query_value("select")
    if selected_option_id and current_question is not None and not is_current_question_answered():
        if find_display_alternative(alternatives, selected_option_id) is not None:
            set_question_selection(selected_option_id)
        _reset_page_query_params(subject=requested_subject)
        st.rerun()

    action = (_get_query_value("action") or "").strip().lower()
    if not action:
        return

    if action == "logout":
        trigger_logout()
        st.stop()

    if current_question is None:
        _reset_page_query_params(subject=requested_subject)
        st.rerun()

    if action == "skip" and not is_current_question_answered():
        mark_question_skipped(current_question.id_question)
        clear_current_question()
        _reset_page_query_params(subject=requested_subject)
        st.rerun()

    if action == "next" and is_current_question_answered():
        clear_current_question()
        _reset_page_query_params(subject=requested_subject)
        st.rerun()

    if action != "submit" or is_current_question_answered():
        _reset_page_query_params(subject=requested_subject)
        st.rerun()

    chosen_option_id = get_question_selection()
    selected_alternative = find_display_alternative(alternatives, chosen_option_id)
    if selected_alternative is None:
        _reset_page_query_params(subject=requested_subject)
        st.rerun()

    if is_submission_in_progress():
        _reset_page_query_params(subject=requested_subject)
        st.rerun()

    start_submission()
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
    except (BigQueryError, ValueError):
        finish_submission()
        raise

    append_user_answer_attempt(user.email, evaluation.record)
    clear_question_skip(current_question.id_question)
    mark_question_answered(evaluation, selected_option_id=selected_alternative.option_id)
    _reset_page_query_params(subject=requested_subject)
    st.rerun()


def _selected_option_id_for_render(current_question_id: int | None) -> str | None:
    if current_question_id is None:
        return None
    if is_current_question_answered():
        last_result = get_last_answer_result()
        if last_result and int(last_result.get("id_question", -1)) == current_question_id:
            selected = str(last_result.get("selected_option_id") or "").strip()
            return selected or None
    return get_question_selection()


def _resolve_elapsed_seconds(
    *,
    question_answered: bool,
    last_result: dict[str, object] | None,
) -> int:
    if question_answered and last_result:
        try:
            return max(int(round(float(last_result.get("time_spent_seconds", 0) or 0))), 0)
        except (TypeError, ValueError):
            return 0

    started_at = get_question_started_at()
    if started_at is None:
        return 0
    return max(int((utc_now() - started_at).total_seconds()), 0)


def _normalize_selected_subject(subject: str | None, subject_options: list[str]) -> str:
    normalized_subject = normalize_subject_filter(subject)
    if normalized_subject in subject_options:
        return normalized_subject
    return "Todas"


def _format_streak_text(day_streak: int, question_streak: int) -> str:
    return f"{max(day_streak, 0)}d / {max(question_streak, 0)}x"


def _format_rank_text(leaderboard_position: str) -> str:
    text = str(leaderboard_position or "").strip()
    return text or "#-"


def _reset_page_query_params(*, subject: str) -> None:
    st.query_params.clear()
    st.query_params["subject"] = normalize_subject_filter(subject)


def _get_query_value(key: str) -> str | None:
    raw_value = st.query_params.get(key)
    if raw_value is None:
        return None
    if isinstance(raw_value, list):
        return str(raw_value[0]).strip() if raw_value else None
    text = str(raw_value).strip()
    return text or None
