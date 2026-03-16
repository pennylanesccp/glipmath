from __future__ import annotations

import streamlit as st

from app.state.session_state import QUESTION_SELECTION_KEY
from modules.domain.models import DisplayAlternative, Question


def render_question_card(
    question: Question,
    alternatives: list[DisplayAlternative],
    *,
    disabled: bool,
    selected_option_id: str | None = None,
) -> str | None:
    """Render the current question and return the selected option ID."""

    with st.container(border=True):
        st.subheader("Questao do momento")
        metadata: list[str] = []
        if question.source:
            metadata.append(f"Fonte: {question.source}")
        if question.topic:
            metadata.append(f"Topico: {question.topic}")
        if question.difficulty:
            metadata.append(f"Dificuldade: {question.difficulty}")
        if metadata:
            st.caption(" | ".join(metadata))
        st.markdown(question.statement)

        option_ids = [alternative.option_id for alternative in alternatives]
        if disabled:
            selected_index = option_ids.index(selected_option_id) if selected_option_id in option_ids else 0
            return st.radio(
                "Alternativas",
                options=option_ids,
                format_func=lambda option_id: _format_alternative(option_id, alternatives),
                index=selected_index,
                key=f"{QUESTION_SELECTION_KEY}_disabled_{question.id_question}",
                disabled=True,
            )

        return st.radio(
            "Alternativas",
            options=option_ids,
            format_func=lambda option_id: _format_alternative(option_id, alternatives),
            index=None,
            key=QUESTION_SELECTION_KEY,
        )


def _format_alternative(option_id: str, alternatives: list[DisplayAlternative]) -> str:
    for alternative in alternatives:
        if alternative.option_id == option_id:
            return alternative.alternative_text
    return option_id
