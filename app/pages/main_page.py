from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

from app.state.session_state import (
    append_user_answer_attempt,
    clear_current_question,
    clear_question_skip,
    get_last_answer_result,
    get_project_filter,
    get_question_selection,
    get_question_started_at,
    get_session_id,
    initialize_session_state,
    is_current_question_answered,
    is_submission_in_progress,
    mark_question_answered,
    mark_question_skipped,
    set_project_filter,
    set_question_selection,
    set_subject_filter,
    start_submission,
    finish_submission,
)
from app.ui.question_session import format_elapsed_time, normalize_subject_filter
from app.ui.template_renderer import asset_to_data_uri
from modules.domain.models import DisplayAlternative, Question, User
from modules.services.answer_service import AnswerService
from modules.services.question_service import format_project_label, format_subject_label
from modules.services.question_service import find_display_alternative
from modules.storage.bigquery_client import BigQueryError
from modules.utils.datetime_utils import utc_now

FIRE_ICON_RELATIVE_PATH = "assets/icons/fire-svgrepo-com.svg"
PODIUM_ICON_RELATIVE_PATH = "assets/icons/pedestal-podium-svgrepo-com.svg"
TIMER_ICON_RELATIVE_PATH = "assets/icons/timer-outline-svgrepo-com.svg"


def render_main_page(
    *,
    user: User,
    current_question: Question | None,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    project_options: list[str],
    selected_project: str | None,
    subject_options: list[str],
    selected_subject: str,
    day_streak: int,
    question_streak: int,
    leaderboard_position: str,
) -> None:
    """Render and drive the authenticated question/session page."""

    initialize_session_state()
    _apply_live_page_styles()

    fire_icon_data_uri = _load_icon_data_uri(FIRE_ICON_RELATIVE_PATH)
    podium_icon_data_uri = _load_icon_data_uri(PODIUM_ICON_RELATIVE_PATH)
    timer_icon_data_uri = _load_icon_data_uri(TIMER_ICON_RELATIVE_PATH)

    normalized_subject = _normalize_selected_subject(selected_subject, subject_options)
    question_answered = is_current_question_answered()
    last_result = get_last_answer_result()
    selected_option_id = _selected_option_id_for_render(current_question.id_question if current_question else None)
    elapsed_seconds = _resolve_elapsed_seconds(
        question_answered=question_answered,
        last_result=last_result,
    )
    answer_is_correct = bool(last_result.get("is_correct")) if last_result else False
    timer_started_at = get_question_started_at()

    _render_controls_bar(
        user=user,
        project_options=project_options,
        selected_project=selected_project,
        subject_options=subject_options,
        selected_subject=normalized_subject,
        streak_text=_format_streak_text(day_streak, question_streak),
        rank_text=_format_rank_text(leaderboard_position),
        timer_elapsed_seconds=elapsed_seconds,
        timer_started_at=timer_started_at,
        timer_running=not question_answered and current_question is not None,
        fire_icon_data_uri=fire_icon_data_uri,
        podium_icon_data_uri=podium_icon_data_uri,
        timer_icon_data_uri=timer_icon_data_uri,
    )

    if current_question is None:
        st.html(
            _build_info_card_html(
                "Nenhuma questão disponível para este filtro no momento.<br><br>"
                "Troque a disciplina acima ou carregue mais questões."
            )
        )
        return

    st.html(_build_question_card_html(current_question.statement))

    if question_answered:
        _render_answered_state(
            alternatives=alternatives,
            selected_option_id=selected_option_id,
            answer_is_correct=answer_is_correct,
        )
        return

    _render_pending_state(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        selected_option_id=selected_option_id,
    )


def _render_controls_bar(
    *,
    user: User,
    project_options: list[str],
    selected_project: str | None,
    subject_options: list[str],
    selected_subject: str,
    streak_text: str,
    rank_text: str,
    timer_elapsed_seconds: int,
    timer_started_at: datetime | None,
    timer_running: bool,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> None:
    normalized_project = _normalize_selected_project(selected_project, project_options)

    if user.is_teacher and project_options:
        chosen_project = st.selectbox(
            "Projeto",
            options=project_options,
            index=project_options.index(normalized_project) if normalized_project in project_options else 0,
            format_func=format_project_label,
            key="gm_project_filter_select",
            label_visibility="collapsed",
        )
    else:
        chosen_project = None

    selected_project_from_state = get_project_filter()
    normalized_choice_project = _normalize_selected_project(chosen_project, project_options)
    if normalized_choice_project != _normalize_selected_project(selected_project_from_state, project_options):
        st.session_state.pop("gm_subject_filter_select", None)
        set_project_filter(normalized_choice_project)
        set_subject_filter(None)
        clear_current_question()
        st.rerun()

    subject_col, metrics_col = st.columns(
        [1.95, 1.45],
        vertical_alignment="center",
    )

    with subject_col:
        chosen_subject = st.selectbox(
            "Disciplina",
            options=subject_options,
            index=subject_options.index(selected_subject) if selected_subject in subject_options else 0,
            format_func=format_subject_label,
            key="gm_subject_filter_select",
            label_visibility="collapsed",
        )

    with metrics_col:
        _render_metrics_bar(
            streak_text=streak_text,
            rank_text=rank_text,
            timer_elapsed_seconds=timer_elapsed_seconds,
            timer_started_at=timer_started_at,
            timer_running=timer_running,
            fire_icon_data_uri=fire_icon_data_uri,
            podium_icon_data_uri=podium_icon_data_uri,
            timer_icon_data_uri=timer_icon_data_uri,
        )

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
        st.html(_build_info_card_html("Esta questão não possui alternativas disponíveis."))
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
                "Pular questão",
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
        st.info("Sua resposta ainda está sendo enviada.")
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
) -> None:
    for alternative in alternatives:
        st.html(
            _build_answer_review_card_html(
                alternative=alternative,
                selected_option_id=selected_option_id,
            )
        )

    status_col, next_col = st.columns([1, 2], vertical_alignment="center")
    with status_col:
        st.html(_build_answer_status_chip_html(answer_is_correct))
    with next_col:
        if st.button("Próxima questão", type="primary", use_container_width=True):
            clear_current_question()
            st.rerun()


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
        st.warning("Seleção inválida para a questão atual.")
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


def _build_metric_chip_html(
    value_text: str,
    icon_data_uri: str,
    *,
    is_timer: bool = False,
    timer_running: bool = False,
) -> str:
    pulse_html = ""
    timer_class = ""
    if is_timer:
        timer_class = " gm-live-metric--timer"
        if timer_running:
            pulse_html = '<span class="gm-live-metric-dot" aria-hidden="true"></span>'

    icon_html = ""
    if icon_data_uri:
        icon_html = (
            f'<img class="gm-live-metric-icon" src="{escape(icon_data_uri, quote=True)}" alt="" aria-hidden="true" />'
        )

    return (
        f'<div class="gm-live-metric{timer_class}">'
        f"{pulse_html}"
        f"{icon_html}"
        f'<span class="gm-live-metric-value">{escape(value_text)}</span>'
        "</div>"
    )


def _build_metrics_bar_html(
    *,
    streak_text: str,
    rank_text: str,
    timer_text: str,
    timer_running: bool,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> str:
    return (
        '<div class="gm-live-metrics-bar">'
        f"{_build_metric_chip_html(streak_text, fire_icon_data_uri)}"
        f"{_build_metric_chip_html(rank_text, podium_icon_data_uri)}"
        f"{_build_metric_chip_html(timer_text, timer_icon_data_uri, is_timer=True, timer_running=timer_running)}"
        "</div>"
    )


def _render_metrics_bar(
    *,
    streak_text: str,
    rank_text: str,
    timer_elapsed_seconds: int,
    timer_started_at: datetime | None,
    timer_running: bool,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> None:
    if timer_running:
        _render_live_metrics_bar_fragment(
            streak_text=streak_text,
            rank_text=rank_text,
            timer_elapsed_seconds=timer_elapsed_seconds,
            timer_started_at=timer_started_at,
            fire_icon_data_uri=fire_icon_data_uri,
            podium_icon_data_uri=podium_icon_data_uri,
            timer_icon_data_uri=timer_icon_data_uri,
        )
        return

    st.html(
        _build_metrics_bar_html(
            streak_text=streak_text,
            rank_text=rank_text,
            timer_text=format_elapsed_time(timer_elapsed_seconds),
            timer_running=False,
            fire_icon_data_uri=fire_icon_data_uri,
            podium_icon_data_uri=podium_icon_data_uri,
            timer_icon_data_uri=timer_icon_data_uri,
        )
    )


@st.fragment(run_every="1s")
def _render_live_metrics_bar_fragment(
    *,
    streak_text: str,
    rank_text: str,
    timer_elapsed_seconds: int,
    timer_started_at: datetime | None,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> None:
    st.html(
        _build_metrics_bar_html(
            streak_text=streak_text,
            rank_text=rank_text,
            timer_text=_resolve_live_timer_text(
                timer_elapsed_seconds=timer_elapsed_seconds,
                timer_started_at=timer_started_at,
            ),
            timer_running=True,
            fire_icon_data_uri=fire_icon_data_uri,
            podium_icon_data_uri=podium_icon_data_uri,
            timer_icon_data_uri=timer_icon_data_uri,
        )
    )


def _build_question_card_html(statement: str) -> str:
    return (
        '<section class="gm-live-card gm-live-question-card">'
        '<div class="gm-live-card-title">Questão</div>'
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
) -> str:
    status_class = "gm-live-answer-card"
    badge_text = "Alternativa"

    if alternative.is_correct:
        status_class += " gm-live-answer-card--correct"
        badge_text = "Gabarito"
    else:
        status_class += " gm-live-answer-card--wrong"

    if alternative.option_id == selected_option_id:
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


def _build_answer_status_chip_html(answer_is_correct: bool) -> str:
    status_class = "gm-live-status-chip--correct" if answer_is_correct else "gm-live-status-chip--wrong"
    status_text = "Você acertou" if answer_is_correct else "Você errou"
    return (
        f'<div class="gm-live-status-chip {status_class}">'
        f"{escape(status_text)}"
        "</div>"
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


def _resolve_live_timer_text(
    *,
    timer_elapsed_seconds: int,
    timer_started_at: datetime | None,
) -> str:
    if timer_started_at is None:
        return format_elapsed_time(timer_elapsed_seconds)

    live_elapsed_seconds = max(
        int((utc_now() - timer_started_at).total_seconds()),
        int(timer_elapsed_seconds),
        0,
    )
    return format_elapsed_time(live_elapsed_seconds)


def _normalize_selected_subject(subject: str | None, subject_options: list[str]) -> str:
    normalized_subject = normalize_subject_filter(subject)
    if normalized_subject in subject_options:
        return normalized_subject
    return "Todas"


def _normalize_selected_project(
    project: str | None,
    project_options: list[str],
) -> str | None:
    if not project_options:
        return None
    if project in project_options:
        return project
    return project_options[0]


def _format_streak_text(day_streak: int, _question_streak: int) -> str:
    return str(max(day_streak, 0))


def _format_rank_text(leaderboard_position: str) -> str:
    text = str(leaderboard_position or "").strip()
    if not text:
        return "#-"
    return text.split("/")[0].strip()


def _text_to_html(text: str | None) -> str:
    return escape(str(text or "").strip()).replace("\n", "<br>")


def _load_icon_data_uri(relative_path: str) -> str:
    try:
        return asset_to_data_uri(relative_path)
    except FileNotFoundError:
        return ""


def _apply_live_page_styles() -> None:
    st.html(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top, rgba(37, 99, 235, 0.12), transparent 26%),
                linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%) !important;
        }

        .block-container {
            max-width: 480px;
            padding-top: 0.45rem;
            padding-bottom: 0.75rem;
        }

        .block-container > div[data-testid="stVerticalBlock"] {
            gap: 0.55rem !important;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.55rem !important;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 0.55rem !important;
        }

        .gm-live-metrics-bar {
            align-items: center;
            display: flex;
            gap: 0.8rem;
            justify-content: flex-end;
            min-height: 2.7rem;
            width: 100%;
        }

        .gm-live-metric {
            align-items: center;
            color: #1e3a8a;
            display: inline-flex;
            font-size: 1.08rem;
            font-weight: 800;
            gap: 0.48rem;
            justify-content: flex-end;
            line-height: 1;
            min-height: 2.7rem;
            padding: 0;
            width: auto;
        }

        .gm-live-metric-dot {
            background: #2563eb;
            border-radius: 999px;
            display: inline-block;
            height: 0.58rem;
            width: 0.58rem;
        }

        .gm-live-metric-icon {
            display: block;
            flex: 0 0 auto;
            height: 1.28rem;
            width: 1.28rem;
        }

        .gm-live-metric-value {
            color: #1e3a8a;
            font-weight: 800;
            white-space: nowrap;
        }

        .gm-live-card {
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 1.25rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
            margin-bottom: 0 !important;
            padding: 1rem 1rem 0.95rem;
        }

        .gm-live-card-title {
            color: #475569;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin-bottom: 0.45rem;
            text-transform: uppercase;
        }

        .gm-live-question-text,
        .gm-live-answer-text,
        .gm-live-answer-explanation,
        .gm-live-info-card {
            color: #0f172a;
            font-size: 0.98rem;
            line-height: 1.5;
        }

        .gm-live-answer-badge {
            color: #475569;
            font-size: 0.74rem;
            font-weight: 700;
            margin-bottom: 0.45rem;
            text-transform: uppercase;
        }

        .gm-live-answer-card--correct {
            background: #f3fff6;
            border-color: #9ae6b4;
        }

        .gm-live-answer-card {
            margin-bottom: 0 !important;
        }

        .gm-live-answer-card--correct .gm-live-answer-badge,
        .gm-live-answer-card--correct .gm-live-answer-text,
        .gm-live-answer-card--correct .gm-live-answer-explanation {
            color: #166534;
        }

        .gm-live-answer-card--wrong {
            background: #fff4f4;
            border-color: #f5a3a3;
        }

        .gm-live-answer-card--wrong .gm-live-answer-badge,
        .gm-live-answer-card--wrong .gm-live-answer-text,
        .gm-live-answer-card--wrong .gm-live-answer-explanation {
            color: #b91c1c;
        }

        .gm-live-answer-explanation {
            border-top: 1px solid rgba(148, 163, 184, 0.22);
            margin-top: 0.55rem;
            padding-top: 0.55rem;
        }

        .gm-live-status-chip {
            align-items: center;
            border-radius: 1rem;
            display: flex;
            font-size: 0.96rem;
            font-weight: 800;
            justify-content: center;
            min-height: 3rem;
            width: 100%;
        }

        .gm-live-status-chip--correct {
            background: #f3fff6;
            border: 1px solid #9ae6b4;
            color: #166534;
        }

        .gm-live-status-chip--wrong {
            background: #fff4f4;
            border: 1px solid #f5a3a3;
            color: #b91c1c;
        }

        div[data-testid="stSelectbox"] label p,
        div[data-testid="stSelectbox"] label span {
            color: #334155 !important;
            font-weight: 700 !important;
        }

        div[data-testid="stSelectbox"] {
            cursor: pointer !important;
            margin-bottom: 0.2rem;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 999px !important;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06) !important;
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
        div[data-baseweb="popover"] > div,
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

        div[data-testid="stForm"] {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stForm"] form {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            margin-top: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stForm"] form > div,
        div[data-testid="stForm"] [data-testid="stElementContainer"] {
            width: 100% !important;
        }

        div[data-testid="stForm"] form > div[data-testid="stVerticalBlock"] {
            gap: 0.38rem !important;
        }

        div[data-testid="stForm"] form > div[data-testid="stVerticalBlock"] > div {
            margin: 0 !important;
        }

        div[data-testid="stRadio"] {
            display: block !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] > label {
            color: #0f172a;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        div[data-testid="stRadio"] > div:first-of-type,
        div[data-testid="stRadio"] > div,
        div[data-testid="stRadio"] [role="radiogroup"] {
            width: 100% !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] {
            align-self: stretch !important;
            align-items: stretch !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 0.55rem !important;
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > * {
            align-self: stretch !important;
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            align-items: flex-start;
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 1rem;
            box-sizing: border-box;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            cursor: pointer !important;
            display: flex !important;
            flex: 1 1 auto !important;
            margin-bottom: 0 !important;
            max-width: none !important;
            min-width: 100% !important;
            padding: 0.9rem 1rem;
            width: 100% !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
            color: #dbeafe !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] * {
            color: #0f172a !important;
            opacity: 1 !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:last-child {
            flex: 1 1 auto !important;
            min-width: 0 !important;
        }

        div[data-testid="stRadio"] input[type="radio"] {
            accent-color: #dbeafe !important;
            cursor: pointer !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] svg {
            fill: #dbeafe !important;
            color: #dbeafe !important;
            stroke: #dbeafe !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: #edf4ff;
            border-color: #93c5fd;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) input[type="radio"] {
            accent-color: #2563eb !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) * {
            color: #1d4ed8 !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] svg {
            fill: #2563eb !important;
            color: #2563eb !important;
            stroke: #2563eb !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
            color: #475569 !important;
        }

        div[data-testid="stButton"] button[kind="secondary"],
        div[data-testid="stFormSubmitButton"] button {
            background: #edf4ff !important;
            border: 1px solid #93c5fd !important;
            color: #1d4ed8 !important;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.1) !important;
        }

        div[data-testid="stButton"] button[kind="secondary"]:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            background: #e2eeff !important;
            border-color: #60a5fa !important;
            color: #1d4ed8 !important;
        }

        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button[kind="primary"],
        div[data-testid="stForm"] form div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stFormSubmitButton"] button {
            background: #1e40af !important;
            border: 1px solid #1e3a8a !important;
            color: #ffffff !important;
            box-shadow: 0 12px 24px rgba(37, 99, 235, 0.22) !important;
        }

        div[data-testid="stButton"] button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 1rem;
            cursor: pointer !important;
            font-weight: 700;
            min-height: 2.9rem;
        }

        div[data-testid="stAlert"] {
            background: #ffffff !important;
            border: 1px solid #dbeafe !important;
            color: #0f172a !important;
        }

        div[data-testid="stAlert"] * {
            color: #0f172a !important;
        }
        </style>
        """
    )
