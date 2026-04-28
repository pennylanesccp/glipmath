from __future__ import annotations

from datetime import datetime
from html import escape
import re

import streamlit as st

from app.state.session_state import (
    append_user_answer_attempt,
    clear_current_question,
    clear_question_skip,
    get_last_answer_result,
    get_question_selection,
    get_question_started_at,
    get_session_id,
    get_subject_filters,
    get_topic_filters,
    initialize_session_state,
    is_current_question_answered,
    is_submission_in_progress,
    mark_question_answered,
    mark_question_skipped,
    set_question_selection,
    set_subject_filters,
    set_topic_filters,
    start_submission,
    finish_submission,
)
from app.ui.markdown_renderer import markdown_to_html, markdown_to_plain_text
from app.ui.question_session import format_elapsed_time
from app.ui.template_renderer import asset_to_data_uri
from modules.domain.models import DisplayAlternative, Question, User
from modules.services.answer_service import AnswerService
from modules.services.question_service import (
    SubjectTopicGroup,
    format_subject_label,
    format_topic_label,
)
from modules.services.question_service import find_display_alternative
from modules.storage.bigquery_client import BigQueryError
from modules.utils.datetime_utils import utc_now

CALENDAR_ICON_RELATIVE_PATH = "assets/icons/calendar.png"
FIRE_ICON_RELATIVE_PATH = "assets/icons/fire-svgrepo-com.svg"
PODIUM_ICON_RELATIVE_PATH = "assets/icons/pedestal-podium-svgrepo-com.svg"
TIMER_ICON_RELATIVE_PATH = "assets/icons/timer-outline-svgrepo-com.svg"
TIMER_WARNING_THRESHOLD_SECONDS = 120
FENCED_CODE_BLOCK_PATTERN = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)
DAY_STREAK_DESCRIPTION = "Dias seguidos com atividade."
QUESTION_STREAK_DESCRIPTION = "Sequência atual de respostas corretas."
RANK_DESCRIPTION = "Sua posição atual no ranking."
TIMER_DESCRIPTION = "Tempo gasto na questão atual."


def render_main_page(
    *,
    user: User,
    current_question: Question | None,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
    selected_filter_label: str,
    day_streak: int,
    question_streak: int,
    leaderboard_position: str,
) -> None:
    """Render and drive the authenticated question/session page."""

    initialize_session_state()
    _apply_live_page_styles()

    calendar_icon_data_uri = _load_icon_data_uri(CALENDAR_ICON_RELATIVE_PATH)
    fire_icon_data_uri = _load_icon_data_uri(FIRE_ICON_RELATIVE_PATH)
    podium_icon_data_uri = _load_icon_data_uri(PODIUM_ICON_RELATIVE_PATH)
    timer_icon_data_uri = _load_icon_data_uri(TIMER_ICON_RELATIVE_PATH)

    question_answered = is_current_question_answered()
    last_result = get_last_answer_result()
    selected_option_id = _selected_option_id_for_render(current_question.id_question if current_question else None)
    elapsed_seconds = _resolve_elapsed_seconds(
        question_answered=question_answered,
        last_result=last_result,
    )
    answer_is_correct = bool(last_result.get("is_correct")) if last_result else False
    timer_started_at = get_question_started_at()

    _render_sidebar_subject_topic_filters(
        subject_topic_groups=subject_topic_groups,
        selected_subjects=selected_subjects,
        selected_topics=selected_topics,
        selected_filter_label=selected_filter_label,
    )
    _render_metrics_bar(
        day_streak_text=_format_day_streak_text(day_streak),
        question_streak_text=_format_question_streak_text(question_streak),
        rank_text=_format_rank_text(leaderboard_position),
        timer_elapsed_seconds=elapsed_seconds,
        timer_started_at=timer_started_at,
        timer_running=not question_answered and current_question is not None,
        calendar_icon_data_uri=calendar_icon_data_uri,
        fire_icon_data_uri=fire_icon_data_uri,
        podium_icon_data_uri=podium_icon_data_uri,
        timer_icon_data_uri=timer_icon_data_uri,
    )

    if current_question is None:
        st.html(
            _build_info_card_html(
                "Nenhuma questão disponível para este filtro no momento.<br><br>"
                "Abra a barra lateral para ajustar projeto, espaço, disciplina ou tópico."
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

    _render_pending_state_compact(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        selected_option_id=selected_option_id,
    )


def _render_controls_bar(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
    selected_filter_label: str,
    streak_text: str,
    rank_text: str,
    timer_elapsed_seconds: int,
    timer_started_at: datetime | None,
    timer_running: bool,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> None:
    subject_col, metrics_col = st.columns(
        [1.65, 1.35],
        vertical_alignment="center",
    )

    with subject_col:
        _render_subject_topic_filter_multiselect(
            subject_topic_groups=subject_topic_groups,
            selected_subjects=selected_subjects,
            selected_topics=selected_topics,
            selected_filter_label=selected_filter_label,
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


def _render_sidebar_subject_topic_filters(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
    selected_filter_label: str,
) -> None:
    if not subject_topic_groups:
        return

    single_subject_mode = _use_topic_only_filter(subject_topic_groups)
    group_specs = _subject_topic_group_specs(subject_topic_groups)
    _ensure_sidebar_subject_topic_filter_widget_state(
        subject_topic_groups=subject_topic_groups,
        selected_subjects=selected_subjects,
        selected_topics=selected_topics,
    )
    _refresh_select_all_filters_checkbox_state(subject_topic_groups)
    draft_subjects, draft_topics = _read_sidebar_subject_topic_filter_widget_state(subject_topic_groups)
    select_all_active = _all_filter_widgets_checked(subject_topic_groups)

    with st.sidebar:
        with st.container():
            st.html('<div class="gm-sidebar-filter-stack-hook"></div>')

            with st.container():
                st.html('<div class="gm-sidebar-subject-topic-filters-hook"></div>')
                st.divider()
                st.caption("Filtros")
                st.checkbox(
                    "Todas as questões",
                    key=_select_all_filters_checkbox_key(),
                    on_change=_toggle_all_sidebar_subject_topic_filter_widgets,
                    args=(group_specs,),
                )

                if not single_subject_mode:
                    with st.container():
                        st.html('<div class="gm-sidebar-subject-filter-section-hook"></div>')
                        st.caption("Matérias")
                        for group in subject_topic_groups:
                            st.checkbox(
                                format_subject_label(group.subject),
                                key=_subject_checkbox_key(group.subject),
                                disabled=select_all_active,
                            )

                if _all_topic_filter_keys(group_specs):
                    with st.container():
                        st.html(
                            '<div class="gm-sidebar-topic-filter-group-hook '
                            'gm-sidebar-topic-filter-group-hook--separate"></div>'
                        )
                        st.caption("Tópicos")
                        for group in subject_topic_groups:
                            for topic in group.topics:
                                label = format_topic_label(topic)
                                if not single_subject_mode:
                                    label = f"{format_subject_label(group.subject)} / {label}"
                                st.checkbox(
                                    label,
                                    key=_topic_checkbox_key(group.subject, topic),
                                    disabled=select_all_active,
                                )
                elif single_subject_mode:
                    for group in subject_topic_groups:
                        st.checkbox(
                            format_subject_label(group.subject),
                            key=_subject_checkbox_key(group.subject),
                            disabled=select_all_active,
                        )

            draft_subjects, draft_topics = _read_sidebar_subject_topic_filter_widget_state(subject_topic_groups)
            has_pending_changes = draft_subjects != selected_subjects or draft_topics != selected_topics
            with st.container():
                st.html('<div class="gm-sidebar-apply-filters-hook"></div>')
                if st.button(
                    "Aplicar filtros",
                    key="gm_sidebar_apply_subject_topic_filters",
                    type="primary",
                    use_container_width=True,
                    disabled=not has_pending_changes,
                ):
                    _apply_subject_topic_filters(subjects=draft_subjects, topics=draft_topics)


def _render_subject_topic_filter_multiselect(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
    selected_filter_label: str,
) -> None:
    single_subject_mode = _use_topic_only_filter(subject_topic_groups)
    group_specs = _subject_topic_group_specs(subject_topic_groups)
    _sync_subject_topic_filter_widget_state(
        subject_topic_groups=subject_topic_groups,
        selected_subjects=selected_subjects,
        selected_topics=selected_topics,
    )

    with st.popover(
        selected_filter_label,
        use_container_width=True,
        width="stretch",
        key="gm_subject_topic_filter_popover",
    ):
        if selected_subjects or selected_topics:
            if st.button(
                "Limpar filtro",
                key="gm_clear_subject_topic_filters",
                type="tertiary",
                use_container_width=True,
            ):
                _apply_subject_topic_filters(subjects=(), topics=())

        for group in subject_topic_groups:
            if not single_subject_mode:
                st.checkbox(
                    format_subject_label(group.subject),
                    key=_subject_checkbox_key(group.subject),
                    on_change=_toggle_subject_filter,
                    args=(group.subject, group_specs),
                )

            with st.container():
                hook_class = "gm-topic-filter-group-hook"
                if single_subject_mode:
                    hook_class += " gm-topic-filter-group-hook--single-subject"
                st.html(f'<div class="{hook_class}"></div>')
                for topic in group.topics:
                    st.checkbox(
                        format_topic_label(topic),
                        key=_topic_checkbox_key(group.subject, topic),
                        on_change=_toggle_topic_filter,
                        args=(group.subject, topic, group_specs),
                    )

def _render_subject_topic_filter(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
    selected_filter_label: str,
) -> None:
    with st.popover(
        selected_filter_label,
        use_container_width=True,
        width="stretch",
        key="gm_subject_topic_filter_popover",
    ):
        if st.button(
            "Todas as matérias",
            key="gm_filter_all_subjects",
            type="tertiary",
            use_container_width=True,
        ):
            _apply_subject_topic_filter(subject=None, topic=None)

        for group in subject_topic_groups:
            expander_label = format_subject_label(group.subject)
            with st.expander(
                expander_label,
                expanded=selected_subject == group.subject,
            ):
                if st.button(
                    f"Toda {expander_label}",
                    key=f"gm_filter_subject_{group.subject}",
                    type="tertiary",
                    use_container_width=True,
                ):
                    _apply_subject_topic_filter(subject=group.subject, topic=None)

                for topic in group.topics:
                    topic_label = format_topic_label(topic)
                    button_label = (
                        f"✓ {topic_label}"
                        if selected_subject == group.subject and selected_topic == topic
                        else topic_label
                    )
                    if st.button(
                        button_label,
                        key=f"gm_filter_topic_{group.subject}_{topic}",
                        type="tertiary",
                        use_container_width=True,
                    ):
                        _apply_subject_topic_filter(subject=group.subject, topic=topic)


def _render_pending_state_compact(
    *,
    user: User,
    current_question: Question,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    selected_option_id: str | None,
) -> None:
    _, content_col, _ = st.columns([0.03, 0.94, 0.03], vertical_alignment="top")
    with content_col:
        _render_pending_interaction_fragment(
            user=user,
            current_question=current_question,
            alternatives=alternatives,
            answer_service=answer_service,
            selected_option_id=selected_option_id,
        )


@st.fragment
def _render_pending_interaction_fragment(
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

    selected_option_id = _render_pending_alternative_radio(
        current_question_id=current_question.id_question,
        alternatives=alternatives,
        selected_option_id=selected_option_id,
    )

    with st.container():
        st.html('<div class="gm-pending-actions-hook"></div>')
        skip_col, verify_col = st.columns([0.88, 2.12], gap="small", vertical_alignment="bottom")
        with skip_col:
            skip_clicked = st.button(
                "Pular",
                key=f"gm_skip_question_{current_question.id_question}",
                use_container_width=True,
            )
        with verify_col:
            verify_clicked = st.button(
                "Verificar resposta",
                key=f"gm_verify_question_{current_question.id_question}",
                type="primary",
                use_container_width=True,
            )

    if skip_clicked:
        mark_question_skipped(current_question.id_question)
        clear_current_question()
        st.rerun()

    if not verify_clicked:
        return

    pending_selection = get_question_selection() or selected_option_id
    if pending_selection is None:
        st.warning("Selecione uma alternativa antes de verificar.")
        return

    if is_submission_in_progress():
        st.info("Sua resposta ainda está sendo enviada.")
        return

    set_question_selection(pending_selection)
    _submit_selected_answer(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        selected_option_id=pending_selection,
    )


def _render_pending_alternative_radio(
    *,
    current_question_id: int,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
) -> str | None:
    with st.container():
        st.html('<div class="gm-live-pending-options-hook"></div>')
        st.html('<div class="gm-live-pending-label">Escolha uma alternativa</div>')

        option_ids = [alternative.option_id for alternative in alternatives]
        label_by_option_id = {
            alternative.option_id: _format_pending_widget_label(alternative.alternative_text)
            for alternative in alternatives
        }
        selection_index = option_ids.index(selected_option_id) if selected_option_id in option_ids else None
        selected_option = st.radio(
            "Escolha uma alternativa",
            options=option_ids,
            index=selection_index,
            key=f"gm_pending_alternative_radio_{current_question_id}",
            format_func=lambda option_id: label_by_option_id[option_id],
            label_visibility="collapsed",
        )

    normalized_selection = str(selected_option).strip() if selected_option is not None else None
    if normalized_selection != get_question_selection():
        set_question_selection(normalized_selection)
    return normalized_selection


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

    selected_option_id = _render_pending_alternative_picker(
        alternatives=alternatives,
        selected_option_id=selected_option_id,
    )

    with st.container():
        st.html('<div class="gm-pending-actions-hook"></div>')
        skip_col, verify_col = st.columns([0.88, 2.12], gap="small", vertical_alignment="bottom")
        with skip_col:
            skip_clicked = st.button(
                "Pular",
                key=f"gm_skip_question_{current_question.id_question}",
                use_container_width=True,
            )
        with verify_col:
            verify_clicked = st.button(
                "Verificar resposta",
                key=f"gm_verify_question_{current_question.id_question}",
                type="primary",
                use_container_width=True,
            )

    if skip_clicked:
        mark_question_skipped(current_question.id_question)
        clear_current_question()
        st.rerun()

    if not verify_clicked:
        return

    pending_selection = get_question_selection() or selected_option_id
    if pending_selection is None:
        st.warning("Selecione uma alternativa antes de verificar.")
        return

    if is_submission_in_progress():
        st.info("Sua resposta ainda está sendo enviada.")
        return

    set_question_selection(pending_selection)
    _submit_selected_answer(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        selected_option_id=pending_selection,
    )


def _render_pending_alternative_picker(
    *,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
) -> str | None:
    st.markdown("Escolha uma alternativa")

    for alternative in alternatives:
        is_selected = alternative.option_id == selected_option_id
        card_col, action_col = st.columns([4.2, 1.35], vertical_alignment="center")
        with card_col:
            st.html(
                _build_pending_alternative_card_html(
                    alternative=alternative,
                    is_selected=is_selected,
                )
            )
        with action_col:
            select_clicked = st.button(
                "Escolhida" if is_selected else "Escolher",
                key=f"gm_select_alternative_{alternative.option_id}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
                help=f"Selecionar alternativa: {markdown_to_plain_text(alternative.alternative_text)}",
            )
        if select_clicked:
            set_question_selection(alternative.option_id)
            st.rerun()

    return selected_option_id


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
    description: str = "",
    is_timer: bool = False,
    timer_warning: bool = False,
) -> str:
    timer_class = ""
    if is_timer:
        timer_class = " gm-live-metric--timer"
    if timer_warning:
        timer_class += " gm-live-metric--timer-warning"
    normalized_description = str(description or "").strip()
    escaped_description = escape(normalized_description, quote=True)
    tooltip_html = ""
    if normalized_description:
        tooltip_html = (
            '<span class="gm-live-metric-tooltip" role="tooltip">'
            f"{escape(normalized_description)}"
            "</span>"
        )

    icon_html = ""
    if icon_data_uri:
        icon_html = (
            f'<img class="gm-live-metric-icon" src="{escape(icon_data_uri, quote=True)}" alt="" aria-hidden="true" />'
        )

    return (
        f'<button class="gm-live-metric{timer_class}" type="button"'
        f' aria-label="{escaped_description or escape(value_text, quote=True)}"'
        f' title="{escaped_description or escape(value_text, quote=True)}">'
        f"{icon_html}"
        f'<span class="gm-live-metric-value">{escape(value_text)}</span>'
        f"{tooltip_html}"
        "</button>"
    )


def _build_metrics_bar_html(
    *,
    day_streak_text: str,
    question_streak_text: str,
    rank_text: str,
    timer_text: str,
    timer_warning: bool,
    calendar_icon_data_uri: str,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> str:
    return (
        '<div class="gm-live-metrics-bar">'
        f"{_build_metric_chip_html(day_streak_text, calendar_icon_data_uri, description=DAY_STREAK_DESCRIPTION)}"
        f"{_build_metric_chip_html(question_streak_text, fire_icon_data_uri, description=QUESTION_STREAK_DESCRIPTION)}"
        f"{_build_metric_chip_html(rank_text, podium_icon_data_uri, description=RANK_DESCRIPTION)}"
        f"{_build_metric_chip_html(timer_text, timer_icon_data_uri, description=TIMER_DESCRIPTION, is_timer=True, timer_warning=timer_warning)}"
        "</div>"
    )


def _render_metrics_bar(
    *,
    day_streak_text: str,
    question_streak_text: str,
    rank_text: str,
    timer_elapsed_seconds: int,
    timer_started_at: datetime | None,
    timer_running: bool,
    calendar_icon_data_uri: str,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> None:
    if timer_running:
        _render_live_metrics_bar_fragment(
            day_streak_text=day_streak_text,
            question_streak_text=question_streak_text,
            rank_text=rank_text,
            timer_elapsed_seconds=timer_elapsed_seconds,
            timer_started_at=timer_started_at,
            calendar_icon_data_uri=calendar_icon_data_uri,
            fire_icon_data_uri=fire_icon_data_uri,
            podium_icon_data_uri=podium_icon_data_uri,
            timer_icon_data_uri=timer_icon_data_uri,
        )
        return

    st.html(
        _build_metrics_bar_html(
            day_streak_text=day_streak_text,
            question_streak_text=question_streak_text,
            rank_text=rank_text,
            timer_text=format_elapsed_time(timer_elapsed_seconds),
            timer_warning=_is_timer_warning(timer_elapsed_seconds),
            calendar_icon_data_uri=calendar_icon_data_uri,
            fire_icon_data_uri=fire_icon_data_uri,
            podium_icon_data_uri=podium_icon_data_uri,
            timer_icon_data_uri=timer_icon_data_uri,
        )
    )


@st.fragment(run_every="1s")
def _render_live_metrics_bar_fragment(
    *,
    day_streak_text: str,
    question_streak_text: str,
    rank_text: str,
    timer_elapsed_seconds: int,
    timer_started_at: datetime | None,
    calendar_icon_data_uri: str,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> None:
    live_elapsed_seconds = _resolve_live_timer_seconds(
        timer_elapsed_seconds=timer_elapsed_seconds,
        timer_started_at=timer_started_at,
    )
    st.html(
        _build_metrics_bar_html(
            day_streak_text=day_streak_text,
            question_streak_text=question_streak_text,
            rank_text=rank_text,
            timer_text=format_elapsed_time(live_elapsed_seconds),
            timer_warning=_is_timer_warning(live_elapsed_seconds),
            calendar_icon_data_uri=calendar_icon_data_uri,
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


def _build_pending_alternative_card_html(
    *,
    alternative: DisplayAlternative,
    is_selected: bool,
) -> str:
    card_class = "gm-live-card gm-live-pending-choice-card"
    if is_selected:
        card_class += " gm-live-pending-choice-card--selected"

    return (
        f'<section class="{card_class}">'
        f'<div class="gm-live-answer-text">{_text_to_html(alternative.alternative_text)}</div>'
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


def _selected_option_id_for_render(current_question_id: int | None) -> str | None:
    if current_question_id is None:
        return None
    if is_current_question_answered():
        last_result = get_last_answer_result()
        if last_result and int(last_result.get("id_question", -1)) == current_question_id:
            selected = str(last_result.get("selected_option_id") or "").strip()
            return selected or None
    return get_question_selection()


def _format_pending_widget_label(markdown_text: str) -> str:
    unwrapped_text = FENCED_CODE_BLOCK_PATTERN.sub(
        lambda match: match.group(1).strip(),
        markdown_text,
    )
    normalized_text = unwrapped_text.strip()
    return normalized_text or markdown_to_plain_text(markdown_text)


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
    return format_elapsed_time(
        _resolve_live_timer_seconds(
            timer_elapsed_seconds=timer_elapsed_seconds,
            timer_started_at=timer_started_at,
        )
    )


def _resolve_live_timer_seconds(
    *,
    timer_elapsed_seconds: int,
    timer_started_at: datetime | None,
) -> int:
    if timer_started_at is None:
        return max(int(timer_elapsed_seconds), 0)

    live_elapsed_seconds = max(
        int((utc_now() - timer_started_at).total_seconds()),
        int(timer_elapsed_seconds),
        0,
    )
    return live_elapsed_seconds


def _is_timer_warning(elapsed_seconds: int) -> bool:
    return int(elapsed_seconds) >= TIMER_WARNING_THRESHOLD_SECONDS


def _use_topic_only_filter(subject_topic_groups: list[SubjectTopicGroup]) -> bool:
    return len(subject_topic_groups) == 1


def _subject_checkbox_key(subject: str) -> str:
    return f"gm_filter_subject_checkbox_{subject}"


def _select_all_filters_checkbox_key() -> str:
    return "gm_filter_select_all_checkbox"


def _topic_checkbox_key(subject: str, topic: str) -> str:
    return f"gm_filter_topic_checkbox_{subject}_{topic}"


def _sidebar_filter_widget_scope_key() -> str:
    return "gm_sidebar_filter_widget_scope"


def _sidebar_filter_widget_applied_signature_key() -> str:
    return "gm_sidebar_filter_widget_applied_signature"


def _subject_topic_group_specs(
    subject_topic_groups: list[SubjectTopicGroup],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple((group.subject, tuple(group.topics)) for group in subject_topic_groups)


def _all_subject_filter_keys(
    subject_topic_group_specs: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[str, ...]:
    return tuple(subject for subject, _topics in subject_topic_group_specs)


def _all_topic_filter_keys(
    subject_topic_group_specs: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (subject, topic)
        for subject, topics in subject_topic_group_specs
        for topic in topics
    )


def _all_filters_selected(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
) -> bool:
    return not selected_subjects and not selected_topics


def _sync_subject_topic_filter_widget_state(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
) -> None:
    all_selected = _all_filters_selected(
        subject_topic_groups=subject_topic_groups,
        selected_subjects=selected_subjects,
        selected_topics=selected_topics,
    )
    selected_subject_set = set(selected_subjects)
    selected_topic_set = set(selected_topics)

    st.session_state[_select_all_filters_checkbox_key()] = all_selected

    for group in subject_topic_groups:
        st.session_state[_subject_checkbox_key(group.subject)] = (
            not all_selected
            and group.subject in selected_subject_set
        )
        for topic in group.topics:
            st.session_state[_topic_checkbox_key(group.subject, topic)] = (
                not all_selected
                and (group.subject, topic) in selected_topic_set
            )


def _sidebar_filter_widgets_ready(subject_topic_groups: list[SubjectTopicGroup]) -> bool:
    if _select_all_filters_checkbox_key() not in st.session_state:
        return False

    for group in subject_topic_groups:
        if _subject_checkbox_key(group.subject) not in st.session_state:
            return False
        for topic in group.topics:
            if _topic_checkbox_key(group.subject, topic) not in st.session_state:
                return False
    return True


def _filter_selection_signature(
    *,
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    return tuple(sorted(selected_subjects)), tuple(sorted(selected_topics))


def _ensure_sidebar_subject_topic_filter_widget_state(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
) -> None:
    group_specs = _subject_topic_group_specs(subject_topic_groups)
    applied_signature = _filter_selection_signature(
        selected_subjects=selected_subjects,
        selected_topics=selected_topics,
    )
    if (
        st.session_state.get(_sidebar_filter_widget_scope_key()) != group_specs
        or st.session_state.get(_sidebar_filter_widget_applied_signature_key()) != applied_signature
        or not _sidebar_filter_widgets_ready(subject_topic_groups)
    ):
        _sync_subject_topic_filter_widget_state(
            subject_topic_groups=subject_topic_groups,
            selected_subjects=selected_subjects,
            selected_topics=selected_topics,
        )
        st.session_state[_sidebar_filter_widget_scope_key()] = group_specs
        st.session_state[_sidebar_filter_widget_applied_signature_key()] = applied_signature


def _all_filter_widgets_checked(_subject_topic_groups: list[SubjectTopicGroup]) -> bool:
    return bool(st.session_state.get(_select_all_filters_checkbox_key()))


def _refresh_select_all_filters_checkbox_state(_subject_topic_groups: list[SubjectTopicGroup]) -> None:
    st.session_state.setdefault(_select_all_filters_checkbox_key(), False)


def _read_sidebar_subject_topic_filter_widget_state(
    subject_topic_groups: list[SubjectTopicGroup],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    group_specs = _subject_topic_group_specs(subject_topic_groups)
    if not group_specs:
        return (), ()

    if _all_filter_widgets_checked(subject_topic_groups):
        return (), ()

    selected_subjects = tuple(
        subject
        for subject in _all_subject_filter_keys(group_specs)
        if bool(st.session_state.get(_subject_checkbox_key(subject)))
    )
    selected_topics = tuple(
        (subject, topic)
        for subject, topic in _all_topic_filter_keys(group_specs)
        if bool(st.session_state.get(_topic_checkbox_key(subject, topic)))
    )
    return selected_subjects, selected_topics


def _toggle_all_sidebar_subject_topic_filter_widgets(
    subject_topic_group_specs: tuple[tuple[str, tuple[str, ...]], ...],
) -> None:
    target_value = bool(st.session_state.get(_select_all_filters_checkbox_key()))
    if not target_value:
        return

    for subject, topics in subject_topic_group_specs:
        st.session_state[_subject_checkbox_key(subject)] = False
        for topic in topics:
            st.session_state[_topic_checkbox_key(subject, topic)] = False


def _toggle_all_subject_topic_filters() -> None:
    if bool(st.session_state.get(_select_all_filters_checkbox_key())):
        set_subject_filters(())
        set_topic_filters(())
        clear_current_question()
        return

    if not get_subject_filters() and not get_topic_filters():
        st.session_state[_select_all_filters_checkbox_key()] = True


def _toggle_subject_filter(
    subject: str,
    _subject_topic_group_specs: tuple[tuple[str, tuple[str, ...]], ...] | None = None,
) -> None:
    selected_subjects = set(get_subject_filters())
    selected_topics = set(get_topic_filters())

    if bool(st.session_state.get(_subject_checkbox_key(subject))):
        selected_subjects.add(subject)
    else:
        selected_subjects.discard(subject)

    if selected_subjects:
        selected_topics = {
            topic_pair
            for topic_pair in selected_topics
            if topic_pair[0] in selected_subjects
        }

    set_subject_filters(selected_subjects)
    set_topic_filters(selected_topics)
    clear_current_question()


def _toggle_topic_filter(
    subject: str,
    topic: str,
    _subject_topic_group_specs: tuple[tuple[str, tuple[str, ...]], ...] | None = None,
) -> None:
    selected_subjects = set(get_subject_filters())
    selected_topics = set(get_topic_filters())
    topic_pair = (subject, topic)

    if bool(st.session_state.get(_topic_checkbox_key(subject, topic))):
        selected_topics.add(topic_pair)
    else:
        selected_topics.discard(topic_pair)

    set_subject_filters(selected_subjects)
    set_topic_filters(selected_topics)
    clear_current_question()


def _apply_subject_topic_filters(
    *,
    subjects: tuple[str, ...],
    topics: tuple[tuple[str, str], ...],
) -> None:
    if subjects == get_subject_filters() and topics == get_topic_filters():
        return

    set_subject_filters(subjects)
    set_topic_filters(topics)
    clear_current_question()
    st.rerun()


def _apply_subject_topic_filter(
    *,
    subject: str | None,
    topic: str | None,
) -> None:
    subjects = (subject,) if subject else ()
    topics = ((subject, topic),) if subject and topic else ()
    _apply_subject_topic_filters(subjects=subjects, topics=topics)


def _format_day_streak_text(day_streak: int) -> str:
    return str(max(day_streak, 0))


def _format_question_streak_text(question_streak: int) -> str:
    return str(max(question_streak, 0))


def _format_rank_text(leaderboard_position: str) -> str:
    text = str(leaderboard_position or "").strip()
    if not text:
        return "#-"
    return text.replace(" / ", "/").replace(" /", "/").replace("/ ", "/")


def _text_to_html(text: str | None) -> str:
    return markdown_to_html(text)


def _load_icon_data_uri(relative_path: str) -> str:
    try:
        return asset_to_data_uri(relative_path)
    except FileNotFoundError:
        return ""


def _apply_live_page_styles() -> None:
    st.html(
        """
        <style>
        :root {
            --gm-topbar-alignment-offset: 0.2rem;
            --gm-live-card-inline-padding: 1rem;
            --gm-pending-choice-gap: 0.48rem;
            --gm-pending-choice-label-gap: 0.16rem;
            --gm-pending-choice-padding-block: 0.56rem;
            --gm-pending-choice-padding-inline: 0.62rem;
            --gm-sidebar-section-gap: 0.34rem;
            --gm-sidebar-group-gap: 0.18rem;
            --gm-sidebar-group-indent: 1.18rem;
            --gm-sidebar-divider-margin-top: 0.12rem;
            --gm-sidebar-divider-margin-bottom: 0.28rem;
            --gm-sidebar-caption-margin-top: 0.22rem;
            --gm-sidebar-caption-margin-bottom: 0.02rem;
            --gm-sidebar-actions-gap: 0.16rem;
            --gm-sidebar-actions-padding-top: 0.34rem;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top, rgba(37, 99, 235, 0.12), transparent 26%),
                linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%) !important;
        }

        .block-container {
            max-width: 480px;
            padding-top: 0.1rem;
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

        section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
            color: #0f172a;
        }

        section[data-testid="stSidebar"] {
            border-left: none !important;
            border-right: 1px solid #dbeafe !important;
            box-shadow: 18px 0 40px rgba(15, 23, 42, 0.1) !important;
        }

        section[data-testid="stSidebar"] > div {
            background: rgba(255, 255, 255, 0.96) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button {
            border-radius: 1rem;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-filter-stack-hook) {
            gap: var(--gm-sidebar-section-gap) !important;
            padding-top: 0.04rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) {
            gap: var(--gm-sidebar-section-gap) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) hr,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) hr {
            margin: var(--gm-sidebar-divider-margin-top) 0 var(--gm-sidebar-divider-margin-bottom) !important;
            border-color: #dbeafe !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) [data-testid="stCaptionContainer"] {
            margin: var(--gm-sidebar-caption-margin-top) 0 var(--gm-sidebar-caption-margin-bottom) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-topic-filter-group-hook) {
            gap: var(--gm-sidebar-group-gap) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-topic-filter-group-hook) [data-testid="stCheckbox"] {
            margin-bottom: 0 !important;
            margin-left: var(--gm-sidebar-group-indent) !important;
            width: calc(100% - var(--gm-sidebar-group-indent)) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-topic-filter-group-hook--single-subject) [data-testid="stCheckbox"],
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-topic-filter-group-hook--separate) [data-testid="stCheckbox"] {
            margin-left: 0 !important;
            width: 100% !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-apply-filters-hook),
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) {
            gap: var(--gm-sidebar-actions-gap) !important;
            padding-top: var(--gm-sidebar-actions-padding-top) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] p {
            color: #ffffff !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-live-pending-options-hook) {
            gap: var(--gm-pending-choice-label-gap) !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-pending-actions-hook) > div[data-testid="stHorizontalBlock"] {
            box-sizing: border-box !important;
            flex-wrap: nowrap !important;
            padding-inline: var(--gm-live-card-inline-padding) !important;
            width: 100% !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-pending-actions-hook) > div[data-testid="stHorizontalBlock"] > div {
            min-width: 0 !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-pending-actions-hook) > div[data-testid="stHorizontalBlock"] > div:first-child {
            flex: 0 0 5.9rem !important;
            width: 5.9rem !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-pending-actions-hook) > div[data-testid="stHorizontalBlock"] > div:last-child {
            flex: 1 1 0 !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-pending-actions-hook) [data-testid="stButton"] > button {
            white-space: nowrap !important;
        }

        .gm-live-metrics-bar {
            align-items: center;
            display: flex;
            gap: 0.62rem;
            justify-content: center;
            min-height: 2.55rem;
            width: 100%;
        }

        .gm-live-metric {
            align-items: center;
            appearance: none;
            background: transparent;
            border: 0;
            color: #1e3a8a;
            cursor: help;
            display: inline-flex;
            font-size: 1.12rem;
            font-weight: 800;
            gap: 0.36rem;
            justify-content: flex-start;
            line-height: 1;
            min-height: 2.55rem;
            padding: 0;
            position: relative;
            width: auto;
        }

        .gm-live-metric:focus {
            outline: none;
        }

        .gm-live-metric:focus-visible {
            box-shadow: 0 0 0 0.16rem rgba(37, 99, 235, 0.22);
            border-radius: 0.9rem;
        }

        .gm-live-metric-icon {
            display: block;
            flex: 0 0 auto;
            height: 1.42rem;
            width: 1.42rem;
        }

        .gm-live-metric-value {
            color: #1e3a8a;
            font-weight: 800;
            white-space: nowrap;
        }

        .gm-live-metric-tooltip {
            background: rgba(15, 23, 42, 0.94);
            border-radius: 0.8rem;
            bottom: calc(-100% - 0.55rem);
            color: #f8fafc;
            font-size: 0.73rem;
            font-weight: 600;
            left: 50%;
            line-height: 1.35;
            max-width: 10rem;
            opacity: 0;
            padding: 0.5rem 0.62rem;
            pointer-events: none;
            position: absolute;
            text-align: center;
            transform: translate(-50%, -0.18rem);
            transition: opacity 0.16s ease, transform 0.16s ease;
            white-space: normal;
            z-index: 20;
        }

        .gm-live-metric:hover .gm-live-metric-tooltip,
        .gm-live-metric:focus .gm-live-metric-tooltip,
        .gm-live-metric:focus-visible .gm-live-metric-tooltip,
        .gm-live-metric:active .gm-live-metric-tooltip {
            opacity: 1;
            transform: translate(-50%, 0);
        }

        .gm-live-metric--timer-warning,
        .gm-live-metric--timer-warning .gm-live-metric-value {
            color: #dc2626 !important;
        }

        .gm-live-metric--timer-warning .gm-live-metric-icon {
            filter: brightness(0) saturate(100%) invert(24%) sepia(97%) saturate(2652%) hue-rotate(351deg) brightness(89%) contrast(95%);
        }

        div[data-testid="stElementContainer"]:has(.gm-live-metrics-bar) {
            align-items: center;
            box-sizing: border-box;
            display: flex;
            min-height: calc(2.55rem + var(--gm-topbar-alignment-offset));
            padding-top: var(--gm-topbar-alignment-offset);
            width: 100%;
        }

        div[data-testid="stElementContainer"]:has(.gm-live-metrics-bar) > div {
            width: 100%;
        }

        .gm-live-card {
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 1.25rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
            margin-bottom: 0 !important;
            padding: 1rem var(--gm-live-card-inline-padding) 0.95rem;
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

        .gm-live-question-text > :first-child,
        .gm-live-answer-text > :first-child,
        .gm-live-answer-explanation > :first-child {
            margin-top: 0;
        }

        .gm-live-question-text > :last-child,
        .gm-live-answer-text > :last-child,
        .gm-live-answer-explanation > :last-child {
            margin-bottom: 0;
        }

        .gm-live-question-text p,
        .gm-live-question-text ul,
        .gm-live-question-text ol,
        .gm-live-answer-text p,
        .gm-live-answer-text ul,
        .gm-live-answer-text ol,
        .gm-live-answer-explanation p,
        .gm-live-answer-explanation ul,
        .gm-live-answer-explanation ol {
            margin: 0 0 0.55rem;
        }

        .gm-live-question-text pre,
        .gm-live-answer-text pre,
        .gm-live-answer-explanation pre {
            background: #0f172a;
            border-radius: 0.95rem;
            color: #e2e8f0;
            margin: 0.55rem 0;
            overflow-x: auto;
            padding: 0.85rem 0.95rem;
            white-space: pre-wrap;
        }

        .gm-live-question-text code,
        .gm-live-answer-text code,
        .gm-live-answer-explanation code {
            background: #eff6ff;
            border-radius: 0.45rem;
            color: #1e3a8a;
            font-family: "Consolas", "Courier New", monospace;
            font-size: 0.94em;
            padding: 0.12rem 0.34rem;
        }

        .gm-live-question-text pre code,
        .gm-live-answer-text pre code,
        .gm-live-answer-explanation pre code {
            background: transparent;
            color: inherit;
            padding: 0;
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
            margin-left: auto;
            margin-right: auto;
            max-width: calc(100% - 1.1rem);
            width: calc(100% - 1.1rem);
        }

        .gm-live-pending-label {
            color: #7b8498;
            font-size: 0.88rem;
            font-weight: 600;
            margin: 0.1rem 0 0;
        }

        .gm-live-pending-choice-card {
            margin-bottom: 0 !important;
            max-width: none;
            padding: var(--gm-pending-choice-padding-block) var(--gm-pending-choice-padding-inline) !important;
            width: 100%;
        }

        .gm-live-pending-choice-link {
            color: inherit !important;
            cursor: pointer !important;
            display: block;
            margin: 0;
            text-decoration: none !important;
            width: 100%;
        }

        .gm-live-pending-choice-link:hover .gm-live-pending-choice-card {
            border-color: #93c5fd;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
        }

        .gm-live-pending-choice-link:focus-visible {
            outline: none;
        }

        .gm-live-pending-choice-link:focus-visible .gm-live-pending-choice-card {
            border-color: #60a5fa;
            box-shadow: 0 0 0 0.18rem rgba(96, 165, 250, 0.26);
        }

        .gm-live-pending-choice-row {
            align-items: flex-start;
            display: flex;
            gap: var(--gm-pending-choice-gap);
        }

        .gm-live-pending-choice-dot {
            background: #eef4ff;
            border: 1.5px solid #bfd4ff;
            border-radius: 999px;
            display: inline-block;
            flex: 0 0 auto;
            height: 1rem;
            margin-top: 0.18rem;
            width: 1rem;
        }

        .gm-live-pending-choice-dot--selected {
            background: #2563eb;
            border-color: #2563eb;
            box-shadow: inset 0 0 0 0.18rem #ffffff;
        }

        .gm-live-pending-choice-card--selected {
            background: #edf4ff;
            border-color: #93c5fd;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
        }

        .gm-live-pending-choice-card--selected .gm-live-answer-text {
            color: #1d4ed8;
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

        div[data-testid="stPopover"] > button {
            align-items: center;
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 999px !important;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06) !important;
            color: #0f172a !important;
            cursor: pointer !important;
            display: inline-flex !important;
            justify-content: space-between !important;
            min-height: 2.55rem !important;
            padding-inline: 0.95rem !important;
            text-align: left !important;
            width: 100% !important;
        }

        div[data-testid="stPopover"] > button * {
            color: #0f172a !important;
            font-weight: 500 !important;
        }

        div[data-testid="stPopover"] [data-testid="stPopoverBody"] {
            background: #ffffff !important;
        }

        div[data-testid="stPopover"] [data-testid="stPopoverBody"] > div,
        div[data-testid="stPopover"] div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stPopover"] div[data-testid="stVerticalBlockBorderWrapper"] > div,
        div[data-testid="stPopover"] div[data-testid="stContainer"],
        div[data-testid="stPopover"] div[data-testid="stElementContainer"],
        div[data-testid="stPopover"] div[data-testid="stElementContainer"] > div {
            background: #ffffff !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        div[data-testid="stPopover"] [data-testid="stVerticalBlock"] {
            align-items: stretch !important;
        }

        div[data-testid="stPopover"] [data-testid="stButton"] {
            width: 100% !important;
        }

        div[data-testid="stPopover"] [data-testid="stButton"] > button {
            justify-content: flex-start !important;
            text-align: left !important;
        }

        div[data-testid="stPopover"] [data-testid="stButton"] > button * {
            text-align: left !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] {
            width: 100% !important;
            margin: 0 !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-topic-filter-group-hook) [data-testid="stCheckbox"] {
            margin-left: 1.75rem !important;
            width: calc(100% - 1.75rem) !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-topic-filter-group-hook--single-subject) [data-testid="stCheckbox"] {
            margin-left: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] label {
            align-items: center !important;
            cursor: pointer !important;
            gap: 0.55rem !important;
            justify-content: flex-start !important;
            padding: 0.1rem 0 !important;
            width: 100% !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] label > div:last-child,
        div[data-testid="stPopover"] [data-testid="stCheckbox"] [data-testid="stMarkdownContainer"] {
            flex: 0 1 auto !important;
            width: auto !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] [data-testid="stMarkdownContainer"] p {
            color: #0f172a !important;
            font-weight: 600 !important;
            margin: 0 !important;
            text-align: left !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] input {
            cursor: pointer !important;
        }

        div[data-testid="stPopover"] [data-testid="stHorizontalBlock"],
        div[data-testid="stPopover"] [data-testid="stHorizontalBlock"] > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        div[data-testid="stPopover"] div[data-testid="stButton"] button[kind="tertiary"] {
            background: #f8fbff !important;
            border: 1px solid #dbeafe !important;
            border-radius: 0.9rem !important;
            box-shadow: none !important;
            color: #1e3a8a !important;
            font-weight: 700 !important;
            justify-content: flex-start !important;
            min-height: 2.5rem !important;
            text-align: left !important;
        }

        div[data-testid="stPopover"] div[data-testid="stButton"] button[kind="tertiary"]:hover {
            background: #eef4ff !important;
            border-color: #bfdbfe !important;
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
            gap: 0.55rem !important;
        }

        div[data-testid="stForm"] form > div[data-testid="stVerticalBlock"] > div {
            margin: 0 !important;
        }

        div[data-testid="stRadio"] {
            display: block !important;
            margin-left: auto !important;
            margin-right: auto !important;
            max-width: calc(100% - 1.1rem) !important;
            width: calc(100% - 1.1rem) !important;
        }

        div[data-testid="stRadio"] > label {
            color: #0f172a;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        div[data-testid="stElementContainer"]:has(div[data-testid="stRadio"]),
        div[data-testid="stElementContainer"]:has(div[data-testid="stRadio"]) > div,
        div[data-testid="stRadio"],
        div[data-testid="stRadio"] > div:first-of-type,
        div[data-testid="stRadio"] > div,
        div[data-testid="stRadio"] [role="radiogroup"] {
            width: 100% !important;
            max-width: none !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] {
            align-self: stretch !important;
            align-items: stretch !important;
            display: flex !important;
            flex-direction: column !important;
            gap: var(--gm-pending-choice-gap) !important;
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > * {
            align-self: stretch !important;
            display: block !important;
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > * > * {
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
            column-gap: var(--gm-pending-choice-gap) !important;
            display: grid !important;
            grid-template-columns: 1rem minmax(0, 1fr);
            inline-size: 100% !important;
            justify-self: stretch !important;
            margin-bottom: 0 !important;
            max-width: none !important;
            min-width: 100% !important;
            padding: var(--gm-pending-choice-padding-block) var(--gm-pending-choice-padding-inline) !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] * {
            color: #0f172a !important;
            opacity: 1 !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child,
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child > div {
            align-items: center !important;
            background: #eef4ff !important;
            border: 1.5px solid #bfd4ff !important;
            border-radius: 999px !important;
            box-shadow: none !important;
            color: #bfd4ff !important;
            display: inline-flex !important;
            flex: 0 0 auto !important;
            height: 1rem !important;
            justify-content: center !important;
            min-height: 1rem !important;
            min-width: 1rem !important;
            width: 1rem !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:last-child {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"],
        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] > div,
        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] p {
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] input[type="radio"] {
            accent-color: #dbeafe !important;
            cursor: pointer !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child *,
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child > div * {
            fill: #eef4ff !important;
            color: #bfd4ff !important;
            stroke: #bfd4ff !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: #edf4ff;
            border-color: #93c5fd;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) input[type="radio"] {
            accent-color: #2563eb !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div {
            background: #2563eb !important;
            border-color: #2563eb !important;
            color: #ffffff !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) * {
            color: #1d4ed8 !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child *,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div * {
            fill: #2563eb !important;
            color: #2563eb !important;
            stroke: #2563eb !important;
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

        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stFormSubmitButton"] button {
            background: #edf4ff !important;
            border: 1px solid #93c5fd !important;
            color: #1d4ed8 !important;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.1) !important;
        }

        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stFormSubmitButton"] button:hover {
            background: #e2eeff !important;
            border-color: #60a5fa !important;
            color: #1d4ed8 !important;
        }

        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button[kind="primary"],
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFormSubmitButton"] button,
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stFormSubmitButton"] button {
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

        @media (max-width: 380px) {
            div[data-testid="stVerticalBlock"]:has(.gm-pending-actions-hook) > div[data-testid="stHorizontalBlock"] > div:first-child,
            div[data-testid="stVerticalBlock"]:has(.gm-pending-actions-hook) > div[data-testid="stHorizontalBlock"] > div:last-child {
                flex: 1 1 0 !important;
                width: auto !important;
            }
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
