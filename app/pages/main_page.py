from __future__ import annotations

import streamlit as st

from app.components.header import render_header
from app.components.leaderboard_card import render_leaderboard
from app.components.metric_cards import render_metric_cards
from app.components.question_card import render_question_card
from app.state.session_state import (
    clear_current_question,
    finish_submission,
    get_current_alternatives,
    get_current_question_id,
    get_last_answer_result,
    get_question_started_at,
    get_session_id,
    initialize_session_state,
    is_current_question_answered,
    is_submission_in_progress,
    mark_question_answered,
    set_current_question,
    start_submission,
)
from modules.auth.auth_service import trigger_logout
from modules.config.settings import AppSettings
from modules.domain.models import AnswerAttempt, DisplayAlternative, LeaderboardEntry, Question, User
from modules.services.answer_service import AnswerService
from modules.services.leaderboard_service import find_user_position, format_position
from modules.services.question_service import (
    build_display_alternatives,
    find_display_alternative,
    find_question_by_id,
    select_next_question,
)
from modules.services.streak_service import compute_day_streak, compute_question_streak
from modules.storage.bigquery_client import BigQueryError
from modules.utils.datetime_utils import today_in_timezone, utc_now


def render_main_page(
    *,
    settings: AppSettings,
    user: User,
    questions: list[Question],
    answers: list[AnswerAttempt],
    leaderboard: list[LeaderboardEntry],
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

    leaderboard_entry = find_user_position(leaderboard, user)
    current_date = today_in_timezone(settings.timezone)

    render_metric_cards(
        day_streak=compute_day_streak(
            answers,
            timezone_name=settings.timezone,
            today=current_date,
        ),
        question_streak=compute_question_streak(answers),
        leaderboard_position=format_position(leaderboard_entry, len(leaderboard)),
    )
    render_leaderboard(leaderboard, current_user_email=user.email)

    current_question, alternatives = _ensure_current_question(questions, answers)
    if current_question is None:
        st.info("Nao ha questoes ativas e validas disponiveis no momento.")
        return

    last_result = get_last_answer_result()
    question_answered = is_current_question_answered()
    selected_option_id = (
        str(last_result.get("selected_option_id"))
        if question_answered and last_result and last_result.get("id_question") == current_question.id_question
        else None
    )
    chosen_option_id = render_question_card(
        current_question,
        alternatives,
        disabled=question_answered,
        selected_option_id=selected_option_id,
    )

    if not question_answered:
        submit_disabled = is_submission_in_progress()
        if st.button(
            "Enviar resposta",
            type="primary",
            use_container_width=True,
            disabled=submit_disabled,
        ):
            selected_alternative = find_display_alternative(alternatives, chosen_option_id)
            if selected_alternative is None:
                st.warning("Selecione uma alternativa antes de responder.")
                return

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
            except (BigQueryError, ValueError) as exc:
                finish_submission()
                st.error(f"Nao foi possivel registrar a resposta: {exc}")
                return
            mark_question_answered(evaluation, selected_option_id=selected_alternative.option_id)
            st.rerun()
        return

    _render_answer_feedback(last_result)
    if st.button("Proxima questao", type="primary", use_container_width=True):
        clear_current_question()
        st.rerun()


def _ensure_current_question(
    questions: list[Question],
    answers: list[AnswerAttempt],
) -> tuple[Question | None, list[DisplayAlternative]]:
    current_question = find_question_by_id(questions, get_current_question_id())
    current_alternatives = get_current_alternatives()
    if current_question is not None and current_alternatives:
        return current_question, current_alternatives

    answered_question_ids = {answer.id_question for answer in answers}
    next_question = select_next_question(questions, answered_question_ids)
    if next_question is None:
        return None, []

    alternatives = build_display_alternatives(next_question)
    set_current_question(next_question.id_question, alternatives)
    return next_question, alternatives


def _render_answer_feedback(last_result: dict[str, object] | None) -> None:
    if not last_result:
        return

    is_correct = bool(last_result.get("is_correct"))
    correct_alternative_text = str(last_result.get("correct_alternative_text", ""))
    correct_explanation = _string_or_none(last_result.get("correct_explanation"))
    selected_explanation = _string_or_none(last_result.get("selected_explanation"))
    feedback_message = _string_or_none(last_result.get("feedback_message"))

    if is_correct:
        st.success("Voce acertou.")
    else:
        st.error("Voce errou.")

    st.write(f"Resposta correta: **{correct_alternative_text}**")
    if feedback_message:
        st.caption(feedback_message)
    if correct_explanation:
        st.write(f"Explicacao: {correct_explanation}")
    if selected_explanation and not is_correct:
        st.write(f"Explicacao da alternativa escolhida: {selected_explanation}")


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
