from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

try:
    from streamlit_dynamic_filters import DynamicFiltersHierarchical
except ModuleNotFoundError:  # pragma: no cover - dependency is installed in app runtime.
    DynamicFiltersHierarchical = None

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
from app.ui.live_quiz.components import (
    _build_info_card_html,
    _build_metrics_bar_html,
)
from app.ui.live_quiz.sections import (
    render_answer_result_actions as _render_answer_result_actions,
    render_answer_review_cards as _render_answer_review_cards,
    render_pending_actions as _render_pending_actions,
    render_pending_alternative_radio as _render_pending_alternative_radio,
    render_question_card as _render_question_card,
    render_quiz_section_gap as _render_quiz_section_gap,
)
from app.ui.live_quiz.styles import _apply_live_page_styles
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
SIDEBAR_FILTER_SUBJECT_COLUMN = "Mat\u00e9ria"
SIDEBAR_FILTER_TOPIC_COLUMN = "T\u00f3pico"


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

    if question_answered:
        _render_answered_quiz(
            current_question=current_question,
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


def _render_sidebar_subject_topic_filters(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
    selected_filter_label: str,
) -> None:
    if not subject_topic_groups:
        return

    _ensure_sidebar_subject_topic_filter_widget_state(
        subject_topic_groups=subject_topic_groups,
        selected_subjects=selected_subjects,
        selected_topics=selected_topics,
    )

    with st.sidebar:
        with st.container():
            st.html('<div class="gm-sidebar-section-hook gm-sidebar-filter-stack-hook"></div>')
            st.html('<div class="gm-sidebar-separator gm-sidebar-filter-separator-hook"></div>')
            st.caption("FILTROS")

            with st.container():
                st.html('<div class="gm-sidebar-subject-topic-filters-hook"></div>')
                _render_sidebar_dynamic_subject_topic_filters(subject_topic_groups)

            draft_subjects, draft_topics = _read_sidebar_subject_topic_filter_widget_state(subject_topic_groups)
            has_pending_changes = draft_subjects != selected_subjects or draft_topics != selected_topics
            with st.container():
                st.html('<div class="gm-sidebar-apply-filters-hook"></div>')
                if st.button(
                    "Aplicar filtros",
                    key="gm_sidebar_apply_subject_topic_filters",
                    type="secondary",
                    use_container_width=True,
                    disabled=not has_pending_changes,
                ):
                    _apply_subject_topic_filters(subjects=draft_subjects, topics=draft_topics)


def _render_sidebar_dynamic_subject_topic_filters(
    subject_topic_groups: list[SubjectTopicGroup],
) -> None:
    if DynamicFiltersHierarchical is None:
        st.warning(
            "Instale streamlit-dynamic-filters para carregar os filtros din\u00e2micos."
        )
        return

    filter_frame = _build_sidebar_dynamic_filter_frame(subject_topic_groups)
    filter_columns = _sidebar_dynamic_filter_columns(subject_topic_groups)
    if filter_frame.empty or not filter_columns:
        return

    dynamic_filters = DynamicFiltersHierarchical(
        filter_frame,
        filters=list(filter_columns),
        filters_name=_sidebar_dynamic_filters_key(),
    )
    _display_sidebar_dynamic_filter_controls(
        dynamic_filters=dynamic_filters,
        filter_columns=filter_columns,
        subject_topic_groups=subject_topic_groups,
    )


def _display_sidebar_dynamic_filter_controls(
    *,
    dynamic_filters: DynamicFiltersHierarchical,
    filter_columns: tuple[str, ...],
    subject_topic_groups: list[SubjectTopicGroup],
) -> None:
    filters_changed = False
    remaining_hierarchy = list(filter_columns)
    filters_state_key = dynamic_filters.filters_name

    for filter_column in filter_columns:
        if filter_column == SIDEBAR_FILTER_TOPIC_COLUMN:
            remaining_hierarchy.remove(filter_column)
            filters_changed = (
                _render_sidebar_grouped_topic_filter_control(
                    subject_topic_groups=subject_topic_groups,
                    filters_state_key=filters_state_key,
                )
                or filters_changed
            )
            continue

        filtered_frame = dynamic_filters.filter_df(except_filter_tab=remaining_hierarchy)
        remaining_hierarchy.remove(filter_column)
        options = sorted(
            (
                str(option)
                for option in filtered_frame[filter_column].dropna().unique().tolist()
                if str(option)
            ),
            key=str.casefold,
        )

        current_values = _coerce_dynamic_filter_values(
            st.session_state[filters_state_key].get(filter_column)
        )
        valid_values = [value for value in current_values if value in options]
        if list(current_values) != valid_values:
            st.session_state[filters_state_key][filter_column] = valid_values
            filters_changed = True

        selected_values = st.multiselect(
            filter_column,
            options,
            default=valid_values,
            key=_sidebar_dynamic_multiselect_key(filter_column),
            placeholder=_sidebar_filter_placeholder(filter_column),
            label_visibility="collapsed",
        )
        if selected_values != st.session_state[filters_state_key][filter_column]:
            st.session_state[filters_state_key][filter_column] = selected_values
            _clear_sidebar_topic_checkbox_widget_keys()
            filters_changed = True

    if filters_changed:
        st.rerun()


def _render_sidebar_grouped_topic_filter_control(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    filters_state_key: str,
) -> bool:
    filters_state = st.session_state[filters_state_key]
    subject_by_label = _sidebar_subject_key_by_label(subject_topic_groups)
    selected_subjects = {
        subject_by_label[label]
        for label in _coerce_dynamic_filter_values(
            filters_state.get(SIDEBAR_FILTER_SUBJECT_COLUMN)
        )
        if label in subject_by_label
    }
    visible_groups = [
        group
        for group in subject_topic_groups
        if group.topics and (not selected_subjects or group.subject in selected_subjects)
    ]
    topic_labels = _sidebar_topic_label_by_key(subject_topic_groups)
    visible_topic_keys = [
        (group.subject, topic)
        for group in visible_groups
        for topic in group.topics
    ]
    visible_topic_labels = [
        topic_labels[topic_key]
        for topic_key in visible_topic_keys
        if topic_key in topic_labels
    ]
    current_topic_labels = _coerce_dynamic_filter_values(
        filters_state.get(SIDEBAR_FILTER_TOPIC_COLUMN)
    )
    selected_topic_labels = [
        label for label in visible_topic_labels if label in current_topic_labels
    ]
    state_changed = list(current_topic_labels) != selected_topic_labels
    if state_changed:
        filters_state[SIDEBAR_FILTER_TOPIC_COLUMN] = selected_topic_labels

    selected_topic_set = set(selected_topic_labels)
    popover_label = _sidebar_topic_popover_label(
        selected_topic_labels=selected_topic_labels,
        subject_topic_groups=subject_topic_groups,
    )
    with st.popover(
        popover_label,
        key="gm_sidebar_topic_filter_popover",
        use_container_width=True,
    ):
        show_subject_groups = len(visible_groups) > 1
        next_topic_labels: list[str] = []
        for group in visible_groups:
            modifier = "" if show_subject_groups else " gm-topic-filter-group-hook--single-subject"
            with st.container():
                st.html(f'<div class="gm-topic-filter-group-hook{modifier}"></div>')
                if show_subject_groups:
                    st.html(
                        '<div class="gm-topic-filter-group-title">'
                        f"{escape(format_subject_label(group.subject))}"
                        "</div>"
                    )
                for topic in group.topics:
                    topic_key = (group.subject, topic)
                    internal_label = topic_labels[topic_key]
                    if st.checkbox(
                        format_topic_label(topic),
                        value=internal_label in selected_topic_set,
                        key=_sidebar_topic_checkbox_key(subject=group.subject, topic=topic),
                    ):
                        next_topic_labels.append(internal_label)

    if next_topic_labels != selected_topic_labels:
        filters_state[SIDEBAR_FILTER_TOPIC_COLUMN] = next_topic_labels
        state_changed = True
    return state_changed


def _sidebar_topic_popover_label(
    *,
    selected_topic_labels: list[str],
    subject_topic_groups: list[SubjectTopicGroup],
) -> str:
    if not selected_topic_labels:
        return "Selecione os tópicos"
    if len(selected_topic_labels) > 1:
        return f"{len(selected_topic_labels)} tópicos selecionados"

    topic_keys = _sidebar_topic_keys_by_label(subject_topic_groups).get(
        selected_topic_labels[0],
        (),
    )
    if not topic_keys:
        return "1 tópico selecionado"
    return format_topic_label(topic_keys[0][1])


def _sidebar_filter_placeholder(filter_column: str) -> str:
    if filter_column == SIDEBAR_FILTER_SUBJECT_COLUMN:
        return "Selecione as mat\u00e9rias"
    return "Selecione os t\u00f3picos"


def _render_pending_state_compact(
    *,
    user: User,
    current_question: Question,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    selected_option_id: str | None,
) -> None:
    _render_pending_interaction_fragment(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        selected_option_id=selected_option_id,
    )


def _render_answered_quiz(
    *,
    current_question: Question,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
    answer_is_correct: bool,
) -> None:
    with st.container(key="gm_quiz_flow", gap=None):
        _render_question_card(current_question.statement)
        _render_quiz_section_gap("after-question")
        _render_answered_state(
            alternatives=alternatives,
            selected_option_id=selected_option_id,
            answer_is_correct=answer_is_correct,
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
    with st.container(key="gm_quiz_flow", gap=None):
        _render_question_card(current_question.statement)
        _render_quiz_section_gap("after-question")

        if not alternatives:
            st.html(_build_info_card_html("Esta questão não possui alternativas disponíveis."))
            return

        selected_option_id = _render_pending_alternative_radio(
            current_question_id=current_question.id_question,
            alternatives=alternatives,
            selected_option_id=selected_option_id,
        )
        _render_quiz_section_gap("before-pending-actions")
        skip_clicked, verify_clicked = _render_pending_actions(current_question.id_question)

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


def _render_answered_state(
    *,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
    answer_is_correct: bool,
) -> None:
    next_clicked = _render_answer_result_actions(
        answer_is_correct=answer_is_correct,
        button_key="gm_next_question_top",
    )
    _render_quiz_section_gap("after-answer-actions")
    _render_answer_review_cards(
        alternatives=alternatives,
        selected_option_id=selected_option_id,
    )
    _render_quiz_section_gap("before-bottom-answer-actions")
    next_clicked = (
        _render_answer_result_actions(
            answer_is_correct=answer_is_correct,
            button_key="gm_next_question_bottom",
        )
        or next_clicked
    )
    if next_clicked:
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


def _sidebar_dynamic_filters_key() -> str:
    return "gm_sidebar_subject_topic_dynamic_filters"


def _sidebar_dynamic_multiselect_key(filter_column: str) -> str:
    return f"{_sidebar_dynamic_filters_key()}{filter_column}"


def _sidebar_topic_checkbox_key(*, subject: str, topic: str) -> str:
    return f"gm_sidebar_topic_checkbox::{subject}::{topic}"


def _clear_sidebar_topic_checkbox_widget_keys() -> None:
    for key in tuple(st.session_state):
        if str(key).startswith("gm_sidebar_topic_checkbox::"):
            st.session_state.pop(key, None)


def _clear_sidebar_dynamic_multiselect_widget_keys() -> None:
    for filter_column in (SIDEBAR_FILTER_SUBJECT_COLUMN, SIDEBAR_FILTER_TOPIC_COLUMN):
        st.session_state.pop(_sidebar_dynamic_multiselect_key(filter_column), None)
    _clear_sidebar_topic_checkbox_widget_keys()


def _sidebar_dynamic_filter_columns(
    subject_topic_groups: list[SubjectTopicGroup],
) -> tuple[str, ...]:
    if not any(group.topics for group in subject_topic_groups):
        return (SIDEBAR_FILTER_SUBJECT_COLUMN,)
    if _use_topic_only_filter(subject_topic_groups):
        return (SIDEBAR_FILTER_TOPIC_COLUMN,)
    return (SIDEBAR_FILTER_SUBJECT_COLUMN, SIDEBAR_FILTER_TOPIC_COLUMN)


def _build_sidebar_dynamic_filter_frame(
    subject_topic_groups: list[SubjectTopicGroup],
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    single_subject_mode = _use_topic_only_filter(subject_topic_groups)
    for group in subject_topic_groups:
        subject_label = format_subject_label(group.subject)
        for topic in group.topics:
            rows.append(
                {
                    SIDEBAR_FILTER_SUBJECT_COLUMN: subject_label,
                    SIDEBAR_FILTER_TOPIC_COLUMN: _sidebar_topic_filter_label(
                        subject=group.subject,
                        topic=topic,
                        single_subject_mode=single_subject_mode,
                    ),
                }
            )

        if not group.topics and not single_subject_mode:
            rows.append(
                {
                    SIDEBAR_FILTER_SUBJECT_COLUMN: subject_label,
                    SIDEBAR_FILTER_TOPIC_COLUMN: "",
                }
            )

    columns = list(_sidebar_dynamic_filter_columns(subject_topic_groups))
    return pd.DataFrame(rows, columns=columns)


def _sidebar_topic_filter_label(
    *,
    subject: str,
    topic: str,
    single_subject_mode: bool,
) -> str:
    topic_label = format_topic_label(topic)
    if single_subject_mode:
        return topic_label
    return f"{format_subject_label(subject)} / {topic_label}"


def _sidebar_subject_label_by_key(
    subject_topic_groups: list[SubjectTopicGroup],
) -> dict[str, str]:
    return {
        group.subject: format_subject_label(group.subject)
        for group in subject_topic_groups
    }


def _sidebar_subject_key_by_label(
    subject_topic_groups: list[SubjectTopicGroup],
) -> dict[str, str]:
    return {
        label: subject
        for subject, label in _sidebar_subject_label_by_key(subject_topic_groups).items()
    }


def _sidebar_topic_label_by_key(
    subject_topic_groups: list[SubjectTopicGroup],
) -> dict[tuple[str, str], str]:
    single_subject_mode = _use_topic_only_filter(subject_topic_groups)
    return {
        (group.subject, topic): _sidebar_topic_filter_label(
            subject=group.subject,
            topic=topic,
            single_subject_mode=single_subject_mode,
        )
        for group in subject_topic_groups
        for topic in group.topics
    }


def _sidebar_topic_keys_by_label(
    subject_topic_groups: list[SubjectTopicGroup],
) -> dict[str, tuple[tuple[str, str], ...]]:
    topics_by_label: dict[str, list[tuple[str, str]]] = {}
    for topic_key, label in _sidebar_topic_label_by_key(subject_topic_groups).items():
        topics_by_label.setdefault(label, []).append(topic_key)
    return {
        label: tuple(topic_keys)
        for label, topic_keys in topics_by_label.items()
    }


def _coerce_dynamic_filter_values(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item))
    return ()


def _sync_sidebar_dynamic_filter_widget_state(
    *,
    subject_topic_groups: list[SubjectTopicGroup],
    selected_subjects: tuple[str, ...],
    selected_topics: tuple[tuple[str, str], ...],
) -> None:
    subject_labels = _sidebar_subject_label_by_key(subject_topic_groups)
    topic_labels = _sidebar_topic_label_by_key(subject_topic_groups)
    state: dict[str, list[str]] = {
        column: []
        for column in _sidebar_dynamic_filter_columns(subject_topic_groups)
    }

    if SIDEBAR_FILTER_SUBJECT_COLUMN in state:
        subject_order = _all_subject_filter_keys(
            _subject_topic_group_specs(subject_topic_groups)
        )
        state[SIDEBAR_FILTER_SUBJECT_COLUMN] = [
            subject_labels[subject]
            for subject in subject_order
            if subject in selected_subjects and subject in subject_labels
        ]

    if SIDEBAR_FILTER_TOPIC_COLUMN in state:
        selected_topic_set = set(selected_topics)
        topic_order = _all_topic_filter_keys(
            _subject_topic_group_specs(subject_topic_groups)
        )
        state[SIDEBAR_FILTER_TOPIC_COLUMN] = [
            topic_labels[topic_key]
            for topic_key in topic_order
            if topic_key in selected_topic_set and topic_key in topic_labels
        ]

    st.session_state[_sidebar_dynamic_filters_key()] = state


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


def _sidebar_filter_widgets_ready(subject_topic_groups: list[SubjectTopicGroup]) -> bool:
    state = st.session_state.get(_sidebar_dynamic_filters_key())
    if not isinstance(state, dict):
        return False

    for column in _sidebar_dynamic_filter_columns(subject_topic_groups):
        if column not in state:
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
        _clear_sidebar_dynamic_multiselect_widget_keys()
        _sync_sidebar_dynamic_filter_widget_state(
            subject_topic_groups=subject_topic_groups,
            selected_subjects=selected_subjects,
            selected_topics=selected_topics,
        )
        st.session_state[_sidebar_filter_widget_scope_key()] = group_specs
        st.session_state[_sidebar_filter_widget_applied_signature_key()] = applied_signature


def _read_sidebar_subject_topic_filter_widget_state(
    subject_topic_groups: list[SubjectTopicGroup],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    group_specs = _subject_topic_group_specs(subject_topic_groups)
    if not group_specs:
        return (), ()

    state = st.session_state.get(_sidebar_dynamic_filters_key(), {})
    if not isinstance(state, dict):
        return (), ()

    subject_by_label = _sidebar_subject_key_by_label(subject_topic_groups)
    selected_subject_set = {
        subject_by_label[label]
        for label in _coerce_dynamic_filter_values(
            state.get(SIDEBAR_FILTER_SUBJECT_COLUMN)
        )
        if label in subject_by_label
    }
    selected_subjects = tuple(
        subject
        for subject in _all_subject_filter_keys(group_specs)
        if subject in selected_subject_set
    )

    topics_by_label = _sidebar_topic_keys_by_label(subject_topic_groups)
    selected_topic_set = {
        topic_key
        for label in _coerce_dynamic_filter_values(
            state.get(SIDEBAR_FILTER_TOPIC_COLUMN)
        )
        for topic_key in topics_by_label.get(label, ())
        if not selected_subject_set or topic_key[0] in selected_subject_set
    }
    selected_topics = tuple(
        (subject, topic)
        for subject, topic in _all_topic_filter_keys(group_specs)
        if (subject, topic) in selected_topic_set
    )
    return selected_subjects, selected_topics


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


def _format_day_streak_text(day_streak: int) -> str:
    return str(max(day_streak, 0))


def _format_question_streak_text(question_streak: int) -> str:
    return str(max(question_streak, 0))


def _format_rank_text(leaderboard_position: str) -> str:
    text = str(leaderboard_position or "").strip()
    if not text:
        return "#-"
    return text.replace(" / ", "/").replace(" /", "/").replace("/ ", "/")


def _load_icon_data_uri(relative_path: str) -> str:
    try:
        return asset_to_data_uri(relative_path)
    except FileNotFoundError:
        return ""
