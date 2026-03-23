from __future__ import annotations

import re

from typing import Literal

import streamlit as st

from app.ui.question_session import render_question_session_template, text_to_html
from app.ui.template_renderer import asset_to_data_uri, render_template
from modules.domain.models import DisplayAlternative

NOOP_TARGET = "#preview-static"
SUBJECT_OPTIONS = ["Todas", "Matematica", "Portugues", "Ciencias"]
QUESTION_PREVIEW_LABELS = {
    "pending": "Resposta pendente",
    "correct": "Resposta correta",
    "wrong": "Resposta incorreta",
    "empty": "Sem questoes",
}
PREVIEW_SHELL_STYLE = """
<style>
.gm-preview-shell a,
.gm-preview-shell button,
.gm-preview-shell form,
.gm-preview-shell summary {
    cursor: default !important;
    pointer-events: none !important;
}
</style>
""".strip()


def build_login_preview_html(*, button_disabled: bool) -> str:
    """Render the login template as a static preview."""

    html = render_template(
        "pages/auth_login.html",
        {
            "LOGO_DATA_URI": asset_to_data_uri("assets/brand/ide-logo.png"),
            "GOOGLE_BUTTON_HREF": NOOP_TARGET,
            "GOOGLE_BUTTON_CLASS": " is-disabled" if button_disabled else "",
        },
    )
    return _make_static_preview(html)


def build_question_preview_html(
    *,
    scenario: Literal["pending", "correct", "wrong", "empty"],
    subject_menu_open: bool,
) -> str:
    """Render the question-session template as a static preview."""

    if scenario == "empty":
        html = render_question_session_template(
            selected_subject="Matematica",
            subject_options=SUBJECT_OPTIONS,
            streak_text="5d / 14x",
            rank_text="#7 / 38",
            timer_elapsed_seconds=0,
            timer_running=False,
            logout_href=NOOP_TARGET,
            question_statement_html=text_to_html("Nenhuma questao disponivel para esse filtro agora."),
            alternatives=[],
            selected_option_id=None,
            question_answered=False,
            answer_is_correct=False,
            empty_state_html=(
                '<div class="gm-info-card">'
                f"{text_to_html('Troque a disciplina acima para testar outro estado da interface.')}"
                "</div>"
            ),
        )
        return _make_static_preview(_force_subject_menu_state(html, subject_menu_open=subject_menu_open))

    selected_option_id = None
    question_answered = False
    answer_is_correct = False

    if scenario == "pending":
        selected_option_id = "option_b"
    elif scenario == "correct":
        selected_option_id = "option_c"
        question_answered = True
        answer_is_correct = True
    elif scenario == "wrong":
        selected_option_id = "option_b"
        question_answered = True
    else:
        raise ValueError(f"Unsupported preview scenario: {scenario}")

    html = render_question_session_template(
        selected_subject="Matematica",
        subject_options=SUBJECT_OPTIONS,
        streak_text="5d / 14x",
        rank_text="#7 / 38",
        timer_elapsed_seconds=95,
        timer_running=not question_answered,
        logout_href=NOOP_TARGET,
        question_statement_html=text_to_html(
            "Uma maquina produz 12 pecas em 3 minutos.\n"
            "Mantendo o mesmo ritmo, quantas pecas ela produz em 8 minutos?"
        ),
        alternatives=_build_question_alternatives(),
        selected_option_id=selected_option_id,
        question_answered=question_answered,
        answer_is_correct=answer_is_correct,
    )
    return _make_static_preview(_force_subject_menu_state(html, subject_menu_open=subject_menu_open))


def _build_question_alternatives() -> list[DisplayAlternative]:
    return [
        DisplayAlternative(
            option_id="option_a",
            alternative_text="24 pecas",
            explanation="Essa conta manteria o total original, sem ampliar o tempo.",
            is_correct=False,
        ),
        DisplayAlternative(
            option_id="option_b",
            alternative_text="30 pecas",
            explanation="Voce multiplicou por 2,5 em vez de usar a razao entre 8 e 3 minutos.",
            is_correct=False,
        ),
        DisplayAlternative(
            option_id="option_c",
            alternative_text="32 pecas",
            explanation="A taxa e de 4 pecas por minuto, entao em 8 minutos o total e 32.",
            is_correct=True,
        ),
        DisplayAlternative(
            option_id="option_d",
            alternative_text="36 pecas",
            explanation="Isso consideraria 4,5 pecas por minuto, o que nao bate com o enunciado.",
            is_correct=False,
        ),
    ]


def _force_subject_menu_state(html: str, *, subject_menu_open: bool) -> str:
    if not subject_menu_open:
        return html
    return html.replace(
        '<details class="gm-subject-menu">',
        '<details class="gm-subject-menu" open>',
        1,
    )


def _make_static_preview(html: str) -> str:
    preview_html = re.sub(r'href="[^"]*"', f'href="{NOOP_TARGET}"', html)
    preview_html = re.sub(r'action="[^"]*"', f'action="{NOOP_TARGET}"', preview_html)
    return f"{PREVIEW_SHELL_STYLE}\n<div class=\"gm-preview-shell\">{preview_html}</div>"


def main() -> None:
    """Run the static HTML preview app."""

    st.set_page_config(
        page_title="GlipMath HTML Preview",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.title("Preview das paginas HTML")
    st.caption("Os links, formularios e botoes abaixo foram neutralizados de proposito.")

    preview_page = st.radio(
        "Tela",
        options=["login", "question"],
        format_func=lambda value: "Login" if value == "login" else "Sessao de questao",
        horizontal=True,
    )

    if preview_page == "login":
        button_disabled = st.checkbox("Mostrar botao do Google desabilitado", value=False)
        html = build_login_preview_html(
            button_disabled=button_disabled,
        )
    else:
        scenario = st.selectbox(
            "Cenario",
            options=list(QUESTION_PREVIEW_LABELS),
            format_func=QUESTION_PREVIEW_LABELS.get,
        )
        subject_menu_open = st.checkbox("Abrir menu de disciplinas", value=False)
        html = build_question_preview_html(
            scenario=scenario,
            subject_menu_open=subject_menu_open,
        )

    st.markdown(html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
