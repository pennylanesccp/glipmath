from __future__ import annotations

import streamlit as st

from app.state.session_state import get_question_selection, set_question_selection
from app.ui.live_quiz.components import (
    _build_answer_review_card_html,
    _build_answer_status_chip_html,
    _build_question_card_html,
    _format_pending_widget_label,
)
from modules.domain.models import DisplayAlternative


def render_question_card(
    statement: str,
    *,
    subject_label: str = "",
    topic_label: str = "",
) -> None:
    """Render the full-width question surface."""

    st.html(
        _build_question_card_html(
            statement,
            subject_label=subject_label,
            topic_label=topic_label,
        )
    )


def render_quiz_section_gap(name: str) -> None:
    """Render a visible, explicit gap between major quiz sections."""

    st.html(
        f'<div class="gm-quiz-section-gap gm-quiz-section-gap--{name}" '
        'aria-hidden="true"></div>'
    )


def render_pending_alternative_radio(
    *,
    current_question_id: int,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
) -> str | None:
    """Render pending alternatives and persist the in-session selection."""

    with st.container(key="gm_quiz_pending_alternatives"):
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


def render_pending_actions(current_question_id: int) -> tuple[bool, bool]:
    """Render skip and verify actions and return their click states."""

    with st.container(key="gm_quiz_pending_actions"):
        st.html(
            '<div class="gm-quiz-action-row-hook '
            'gm-quiz-action-row-hook--pending" aria-hidden="true"></div>'
        )
        skip_col, verify_col = st.columns([1, 2], gap="small", vertical_alignment="bottom")
        with skip_col:
            skip_clicked = st.button(
                "Pular",
                key=f"gm_skip_question_{current_question_id}",
                use_container_width=True,
            )
        with verify_col:
            verify_clicked = st.button(
                "Verificar resposta",
                key=f"gm_verify_question_{current_question_id}",
                type="primary",
                use_container_width=True,
            )
    return bool(skip_clicked), bool(verify_clicked)


def render_answer_result_actions(
    *,
    answer_is_correct: bool,
    button_key: str,
) -> bool:
    """Render one full-width answer status/action row."""

    hook_modifier = "top" if button_key.endswith("_top") else "bottom"
    with st.container(key=f"gm_quiz_answer_actions_{hook_modifier}"):
        status_col, next_col = st.columns([1, 2], vertical_alignment="center")
        with status_col:
            st.html(_build_answer_status_chip_html(answer_is_correct))
        with next_col:
            return bool(
                st.button(
                    "Próxima questão",
                    key=button_key,
                    type="primary",
                    use_container_width=True,
                )
            )


def render_answer_review_cards(
    *,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
) -> None:
    """Render answer review cards with explicit gaps between cards."""

    for index, alternative in enumerate(alternatives):
        if index:
            render_quiz_section_gap("between-answer-reviews")
        st.html(
            _build_answer_review_card_html(
                alternative=alternative,
                selected_option_id=selected_option_id,
            )
        )
