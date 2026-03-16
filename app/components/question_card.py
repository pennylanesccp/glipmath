from __future__ import annotations

from html import escape

import streamlit as st

from app.components.navigation import build_query_link
from modules.domain.models import DisplayAlternative, Question


def render_question_content(
    *,
    question: Question,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
    question_answered: bool,
    is_correct: bool | None,
) -> None:
    """Render the question statement plus either selectable or answered alternatives."""

    st.markdown(
        f"""
        <article class="gm-question-card">
            <p class="gm-question-statement">{_escape_multiline(question.statement)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )

    option_markup = "\n".join(
        _build_option_markup(
            alternative=alternative,
            selected_option_id=selected_option_id,
            question_answered=question_answered,
            is_correct=is_correct,
        )
        for alternative in alternatives
    )
    st.markdown(f'<section class="gm-options">{option_markup}</section>', unsafe_allow_html=True)


def render_bottom_action_bar(
    *,
    question_answered: bool,
    has_selection: bool,
    is_correct: bool | None,
) -> None:
    """Render the sticky action area at the bottom of the question screen."""

    if question_answered:
        result_class = "gm-result-card gm-result-card--correct" if is_correct else "gm-result-card"
        result_text = "Você acertou" if is_correct else "Você errou"
        primary_action = (
            f'<a class="gm-link-button gm-link-button--primary" href="{build_query_link(glipmath_action="next")}">'
            "Próxima questão"
            "</a>"
        )
        left_slot = f'<div class="{result_class}">{result_text}</div>'
    else:
        primary_class = "gm-link-button gm-link-button--primary"
        if not has_selection:
            primary_class += " is-disabled"
        primary_href = build_query_link(glipmath_action="submit") if has_selection else ""
        primary_action = (
            f'<a class="{primary_class}" href="{primary_href}">Verificar resposta</a>'
        )
        left_slot = (
            f'<a class="gm-link-button gm-link-button--skip" href="{build_query_link(glipmath_action="skip")}">'
            "Pular questão"
            "</a>"
        )

    st.markdown(
        f"""
        <div class="gm-bottom-action">
            <div class="gm-bottom-action-row">
                {left_slot}
                {primary_action}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_question_state(message: str) -> None:
    """Render a lightweight empty state when no question matches the current filter."""

    st.markdown(
        f"""
        <div class="gm-info-card">
            {escape(message)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_option_markup(
    *,
    alternative: DisplayAlternative,
    selected_option_id: str | None,
    question_answered: bool,
    is_correct: bool | None,
) -> str:
    option_class = _option_class(
        alternative=alternative,
        selected_option_id=selected_option_id,
        question_answered=question_answered,
        is_correct=is_correct,
    )
    option_body = f"""
        <span class="gm-option-radio"></span>
        <span class="gm-option-content">
            <span class="gm-option-text">{escape(alternative.alternative_text)}</span>
            {_build_explanation_markup(alternative, question_answered)}
        </span>
    """

    if question_answered:
        return f'<div class="{option_class}">{option_body}</div>'

    return (
        f'<a class="{option_class}" href="{build_query_link(glipmath_select=alternative.option_id)}">'
        f"{option_body}"
        "</a>"
    )


def _build_explanation_markup(alternative: DisplayAlternative, question_answered: bool) -> str:
    if not question_answered or not alternative.explanation:
        return ""
    return f'<span class="gm-option-explanation">{escape(alternative.explanation)}</span>'


def _option_class(
    *,
    alternative: DisplayAlternative,
    selected_option_id: str | None,
    question_answered: bool,
    is_correct: bool | None,
) -> str:
    classes = ["gm-option"]
    if not question_answered:
        if alternative.option_id == selected_option_id:
            classes.append("gm-option--selected")
        return " ".join(classes)

    if alternative.is_correct:
        classes.append("gm-option--correct")
        return " ".join(classes)

    if is_correct:
        classes.append("gm-option--neutral")
    elif alternative.option_id == selected_option_id:
        classes.append("gm-option--wrong-selected")
    else:
        classes.append("gm-option--wrong")
    return " ".join(classes)


def _escape_multiline(text: str) -> str:
    return escape(text).replace("\n", "<br />")
