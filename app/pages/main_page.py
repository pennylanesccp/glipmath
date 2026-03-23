from __future__ import annotations

from html import escape

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
from app.ui.question_session import format_elapsed_time, normalize_subject_filter
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
    _apply_live_page_styles()

    normalized_subject = _normalize_selected_subject(selected_subject, subject_options)
    _render_topbar(
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

    st.html(
        _build_stats_row_html(
            streak_text=_format_streak_text(day_streak, question_streak),
            rank_text=_format_rank_text(leaderboard_position),
            timer_text=format_elapsed_time(elapsed_seconds),
            timer_running=not question_answered and current_question is not None,
        )
    )

    if current_question is None:
        st.html(
            _build_info_card_html(
                "Nenhuma questao disponivel para esse filtro agora.<br><br>"
                "Troque a disciplina acima ou carregue mais questoes."
            )
        )
        return

    st.html(_build_question_card_html(current_question.statement))

    if question_answered:
        _render_answered_state(
            alternatives=alternatives,
            selected_option_id=selected_option_id,
            answer_is_correct=answer_is_correct,
            last_result=last_result,
        )
        if st.button("Proxima questao", type="primary", use_container_width=True):
            clear_current_question()
            st.rerun()
        return

    _render_pending_state(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        selected_option_id=selected_option_id,
    )


def _render_topbar(
    *,
    subject_options: list[str],
    selected_subject: str,
) -> None:
    controls_col, logout_col = st.columns([4, 1], vertical_alignment="bottom")
    current_index = subject_options.index(selected_subject) if selected_subject in subject_options else 0

    with controls_col:
        chosen_subject = st.selectbox(
            "Disciplina",
            options=subject_options,
            index=current_index,
            key="gm_subject_filter_select",
        )

    with logout_col:
        if st.button("Sair", type="secondary", use_container_width=True):
            trigger_logout()
            st.stop()

    normalized_choice = _normalize_selected_subject(chosen_subject, subject_options)
    if normalized_choice != selected_subject:
        set_subject_filter(None if normalized_choice == "Todas" else normalized_choice)
        clear_current_question()
        st.rerun()


def _render_pending_state(
    *,
    user: User,
    current_question: Question,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    selected_option_id: str | None,
) -> None:
    if not alternatives:
        st.html(_build_info_card_html("Essa questao nao possui alternativas disponiveis."))
        return

    option_ids = [alternative.option_id for alternative in alternatives]
    option_labels = {
        alternative.option_id: alternative.alternative_text
        for alternative in alternatives
    }
    selected_index = _find_option_index(option_ids, selected_option_id)

    skip_clicked = False
    verify_clicked = False
    pending_selection: str | None = None

    with st.form(key=f"gm_question_form_{current_question.id_question}", clear_on_submit=False):
        pending_selection = st.radio(
            "Escolha uma alternativa",
            options=option_ids,
            index=selected_index,
            format_func=option_labels.get,
            label_visibility="visible",
        )
        skip_col, verify_col = st.columns([1, 2], vertical_alignment="bottom")
        with skip_col:
            skip_clicked = st.form_submit_button(
                "Pular questao",
                use_container_width=True,
            )
        with verify_col:
            verify_clicked = st.form_submit_button(
                "Verificar resposta",
                type="primary",
                use_container_width=True,
            )

    if skip_clicked:
        mark_question_skipped(current_question.id_question)
        clear_current_question()
        st.rerun()

    if not verify_clicked:
        return

    set_question_selection(pending_selection)
    if pending_selection is None:
        st.warning("Selecione uma alternativa antes de verificar.")
        return

    if is_submission_in_progress():
        st.info("Sua resposta ainda esta sendo enviada.")
        return

    _submit_selected_answer(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        selected_option_id=pending_selection,
    )


def _render_answered_state(
    *,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
    answer_is_correct: bool,
    last_result: dict[str, object] | None,
) -> None:
    feedback_message = "Resposta registrada."
    if last_result:
        feedback_message = str(last_result.get("feedback_message") or feedback_message)

    if answer_is_correct:
        st.success(feedback_message)
    else:
        st.error(feedback_message)

    for alternative in alternatives:
        st.html(
            _build_answer_review_card_html(
                alternative=alternative,
                selected_option_id=selected_option_id,
                answer_is_correct=answer_is_correct,
            )
        )


def _submit_selected_answer(
    *,
    user: User,
    current_question: Question,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    selected_option_id: str,
) -> None:
    selected_alternative = find_display_alternative(alternatives, selected_option_id)
    if selected_alternative is None:
        st.warning("Selecao invalida para a questao atual.")
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
    except (BigQueryError, ValueError):
        finish_submission()
        raise

    append_user_answer_attempt(user.email, evaluation.record)
    clear_question_skip(current_question.id_question)
    mark_question_answered(evaluation, selected_option_id=selected_alternative.option_id)
    st.rerun()


def _build_stats_row_html(
    *,
    streak_text: str,
    rank_text: str,
    timer_text: str,
    timer_running: bool,
) -> str:
    pulse_html = ""
    if timer_running:
        pulse_html = '<span class="gm-live-chip-dot" aria-hidden="true"></span>'

    return (
        '<div class="gm-live-chip-row">'
        f'<div class="gm-live-chip">Sequencia: {escape(streak_text)}</div>'
        f'<div class="gm-live-chip">Ranking: {escape(rank_text)}</div>'
        f'<div class="gm-live-chip gm-live-chip--timer">{pulse_html}Tempo: {escape(timer_text)}</div>'
        "</div>"
    )


def _build_question_card_html(statement: str) -> str:
    return (
        '<section class="gm-live-card gm-live-question-card">'
        '<div class="gm-live-card-title">Questao</div>'
        f'<div class="gm-live-question-text">{_text_to_html(statement)}</div>'
        "</section>"
    )


def _build_info_card_html(message_html: str) -> str:
    return (
        '<section class="gm-live-card gm-live-info-card">'
        f"<div>{message_html}</div>"
        "</section>"
    )


def _build_answer_review_card_html(
    *,
    alternative: DisplayAlternative,
    selected_option_id: str | None,
    answer_is_correct: bool,
) -> str:
    status_class = "gm-live-answer-card"
    badge_text = "Alternativa"

    if alternative.is_correct:
        status_class += " gm-live-answer-card--correct"
        badge_text = "Resposta correta"
    elif not answer_is_correct and alternative.option_id == selected_option_id:
        status_class += " gm-live-answer-card--wrong"
        badge_text = "Sua resposta"
    elif alternative.option_id == selected_option_id:
        status_class += " gm-live-answer-card--selected"
        badge_text = "Sua resposta"

    explanation_html = ""
    if alternative.explanation:
        explanation_html = (
            '<div class="gm-live-answer-explanation">'
            f"{_text_to_html(alternative.explanation)}"
            "</div>"
        )

    return (
        f'<section class="gm-live-card {status_class}">'
        f'<div class="gm-live-answer-badge">{escape(badge_text)}</div>'
        f'<div class="gm-live-answer-text">{_text_to_html(alternative.alternative_text)}</div>'
        f"{explanation_html}"
        "</section>"
    )


def _find_option_index(option_ids: list[str], selected_option_id: str | None) -> int | None:
    if not selected_option_id:
        return None
    try:
        return option_ids.index(selected_option_id)
    except ValueError:
        return None


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


def _text_to_html(text: str | None) -> str:
    return escape(str(text or "").strip()).replace("\n", "<br>")


def _apply_live_page_styles() -> None:
    st.html(
        """
        <style>
        .gm-live-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin: 0.25rem 0 1rem;
        }

        .gm-live-chip {
            align-items: center;
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 999px;
            box-shadow: 0 8px 24px rgba(37, 99, 235, 0.08);
            color: #1e3a8a;
            display: inline-flex;
            font-size: 0.92rem;
            font-weight: 700;
            gap: 0.5rem;
            min-height: 2.35rem;
            padding: 0 0.95rem;
        }

        .gm-live-chip-dot {
            background: #2563eb;
            border-radius: 999px;
            display: inline-block;
            height: 0.5rem;
            width: 0.5rem;
        }

        .gm-live-card {
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 1.25rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
            margin-bottom: 1rem;
            padding: 1.1rem 1.15rem;
        }

        .gm-live-card-title {
            color: #475569;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin-bottom: 0.7rem;
            text-transform: uppercase;
        }

        .gm-live-question-text,
        .gm-live-answer-text,
        .gm-live-answer-explanation,
        .gm-live-info-card {
            color: #0f172a;
            font-size: 1rem;
            line-height: 1.6;
        }

        .gm-live-answer-badge {
            color: #475569;
            font-size: 0.8rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
            text-transform: uppercase;
        }

        .gm-live-answer-card--correct {
            background: #f0fdf4;
            border-color: #bbf7d0;
        }

        .gm-live-answer-card--correct .gm-live-answer-badge,
        .gm-live-answer-card--correct .gm-live-answer-text,
        .gm-live-answer-card--correct .gm-live-answer-explanation {
            color: #166534;
        }

        .gm-live-answer-card--wrong {
            background: #fef2f2;
            border-color: #fecaca;
        }

        .gm-live-answer-card--wrong .gm-live-answer-badge,
        .gm-live-answer-card--wrong .gm-live-answer-text,
        .gm-live-answer-card--wrong .gm-live-answer-explanation {
            color: #b91c1c;
        }

        .gm-live-answer-card--selected {
            background: #eef2ff;
            border-color: #c7d2fe;
        }

        .gm-live-answer-card--selected .gm-live-answer-badge,
        .gm-live-answer-card--selected .gm-live-answer-text,
        .gm-live-answer-card--selected .gm-live-answer-explanation {
            color: #3730a3;
        }

        .gm-live-answer-explanation {
            border-top: 1px solid rgba(148, 163, 184, 0.22);
            margin-top: 0.7rem;
            padding-top: 0.7rem;
        }

        div[data-testid="stRadio"] > label {
            color: #0f172a;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            align-items: flex-start;
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 1rem;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.75rem;
            padding: 0.95rem 1rem;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: #eef2ff;
            border-color: #818cf8;
        }

        div[data-testid="stButton"] button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 1rem;
            font-weight: 700;
            min-height: 3rem;
        }
        </style>
        """
    )
