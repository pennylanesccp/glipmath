from __future__ import annotations

import streamlit as st

from app.state.session_state import QUESTION_SELECTION_KEY
from modules.domain.models import Question


def render_question_card(
    question: Question,
    *,
    disabled: bool,
    selected_choice: str | None = None,
) -> str | None:
    """Render the current question and return the selected choice label."""

    st.subheader("Questao")
    st.caption(f"Fonte: {question.source}")
    st.markdown(question.statement)

    options = [label for label, _ in question.available_choices()]
    if disabled:
        selected_index = options.index(selected_choice) if selected_choice in options else 0
        return st.radio(
            "Alternativas",
            options=options,
            format_func=lambda label: _format_choice(label, question),
            index=selected_index,
            key=f"{QUESTION_SELECTION_KEY}_disabled_{question.id_question}",
            disabled=True,
        )

    return st.radio(
        "Alternativas",
        options=options,
        format_func=lambda label: _format_choice(label, question),
        index=None,
        key=QUESTION_SELECTION_KEY,
    )


def _format_choice(label: str, question: Question) -> str:
    return f"{label}. {question.choices[label]}"
