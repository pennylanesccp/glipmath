from __future__ import annotations

import streamlit as st

from app.components.header import render_header
from app.components.leaderboard_card import render_leaderboard
from app.components.metric_cards import render_metric_cards
from app.components.question_card import render_question_card
from app.state.session_state import (
    clear_current_question,
    get_current_question_id,
    get_last_answer_result,
    get_question_started_at,
    get_session_id,
    initialize_session_state,
    is_current_question_answered,
    mark_question_answered,
    set_current_question,
)
from modules.auth.auth_service import trigger_logout
from modules.config.settings import AppSettings
from modules.domain.models import AnswerRecord, AppUser, Question
from modules.services.answer_service import AnswerService, answers_for_user
from modules.services.leaderboard_service import (
    compute_leaderboard,
    find_user_position,
    format_position,
)
from modules.services.question_service import find_question_by_id, select_next_question
from modules.services.streak_service import compute_day_streak, compute_question_streak
from modules.storage.sheets_client import StorageError
from modules.utils.datetime_utils import today_in_timezone, utc_now


def render_main_page(
    *,
    settings: AppSettings,
    user: AppUser,
    all_users: list[AppUser],
    questions: list[Question],
    answers: list[AnswerRecord],
    answer_service: AnswerService,
) -> None:
    """Render the authenticated application page."""

    initialize_session_state()

    if render_header(
        app_name=settings.app_name,
        user_name=user.display_name,
        user_email=user.email,
    ):
        trigger_logout()
        st.stop()

    user_answers = answers_for_user(answers, user)
    leaderboard = compute_leaderboard(all_users, answers)
    leaderboard_entry = find_user_position(leaderboard, user)
    current_date = today_in_timezone(settings.timezone)

    render_metric_cards(
        day_streak=compute_day_streak(
            user_answers,
            timezone_name=settings.timezone,
            today=current_date,
        ),
        question_streak=compute_question_streak(user_answers),
        leaderboard_position=format_position(leaderboard_entry, len(leaderboard)),
    )
    render_leaderboard(leaderboard, current_user_id=user.id_user)

    current_question = _ensure_current_question(questions, user_answers)
    if current_question is None:
        st.info("Nao ha questoes ativas e validas disponiveis no momento.")
        return

    last_result = get_last_answer_result()
    question_answered = is_current_question_answered()
    selected_choice = (
        str(last_result.get("selected_choice"))
        if question_answered and last_result and last_result.get("id_question") == current_question.id_question
        else None
    )
    chosen_choice = render_question_card(
        current_question,
        disabled=question_answered,
        selected_choice=selected_choice,
    )

    if not question_answered:
        if st.button("Responder", type="primary", use_container_width=True):
            if not chosen_choice:
                st.warning("Selecione uma alternativa antes de responder.")
                return

            started_at = get_question_started_at() or utc_now()
            elapsed_seconds = max((utc_now() - started_at).total_seconds(), 0.0)
            try:
                evaluation = answer_service.submit_answer(
                    user=user,
                    question=current_question,
                    selected_choice=chosen_choice,
                    session_id=get_session_id(),
                    time_spent_seconds=elapsed_seconds,
                    existing_answers=answers,
                )
            except (StorageError, ValueError) as exc:
                st.error(f"Nao foi possivel registrar a resposta: {exc}")
                return
            mark_question_answered(evaluation)
            st.rerun()
        return

    _render_answer_feedback(last_result)
    if st.button("Proxima questao", type="primary", use_container_width=True):
        clear_current_question()
        st.rerun()


def _ensure_current_question(
    questions: list[Question],
    user_answers: list[AnswerRecord],
) -> Question | None:
    current_question = find_question_by_id(questions, get_current_question_id())
    if current_question is not None:
        return current_question

    answered_question_ids = {answer.id_question for answer in user_answers}
    next_question = select_next_question(questions, answered_question_ids)
    if next_question is None:
        return None

    set_current_question(next_question.id_question)
    return next_question


def _render_answer_feedback(last_result: dict[str, object] | None) -> None:
    if not last_result:
        return

    is_correct = bool(last_result.get("is_correct"))
    correct_choice = str(last_result.get("correct_choice", ""))
    feedback_message = str(last_result.get("feedback_message", ""))

    if is_correct:
        st.success("Voce acertou.")
    else:
        st.error("Voce errou.")
    st.write(f"Resposta correta: **{correct_choice}**")
    if feedback_message:
        st.caption(feedback_message)
