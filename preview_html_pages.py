from __future__ import annotations

import re

from typing import Literal

import streamlit as st

from app.ui.question_session import render_question_session_template, text_to_html
from app.ui.template_renderer import asset_to_data_uri, render_template
from modules.domain.models import DisplayAlternative

NOOP_TARGET = "#preview-static"
SUBJECT_OPTIONS = ["Todas", "Matemática", "Português", "Ciências"]
QUESTION_PREVIEW_LABELS = {
    "pending": "Resposta pendente",
    "correct": "Resposta correta",
    "wrong": "Resposta incorreta",
    "empty": "Sem questões",
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


def build_login_preview_html(*, theme_mode: str, button_disabled: bool) -> str:
    """Render the login template as a static preview."""

    html = render_template(
        "pages/auth_login.html",
        {
            "THEME_NAME": theme_mode,
            "THEME_TOGGLE_HREF": NOOP_TARGET,
            "THEME_TOGGLE_CLASS": (
                "gm-theme-toggle--dark" if theme_mode == "dark" else "gm-theme-toggle--light"
            ),
            "LOGO_DATA_URI": asset_to_data_uri("assets/brand/ide-logo.png"),
            "GOOGLE_BUTTON_HREF": NOOP_TARGET,
            "GOOGLE_BUTTON_CLASS": " is-disabled" if button_disabled else "",
        },
    )
    return _make_static_preview(html)


def build_question_preview_html(
    *,
    theme_mode: str,
    scenario: Literal["pending", "correct", "wrong", "empty"],
    subject_menu_open: bool,
) -> str:
    """Render the question-session template as a static preview."""

    if scenario == "empty":
        html = render_question_session_template(
            theme_mode=theme_mode,
            selected_subject="Matemática",
            subject_options=SUBJECT_OPTIONS,
            streak_text="5d / 14x",
            rank_text="#7 / 38",
            timer_elapsed_seconds=0,
            timer_running=False,
            logout_href=NOOP_TARGET,
            question_statement_html=text_to_html("Nenhuma questão disponível para esse filtro agora."),
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
        theme_mode=theme_mode,
        selected_subject="Matemática",
        subject_options=SUBJECT_OPTIONS,
        streak_text="5d / 14x",
        rank_text="#7 / 38",
        timer_elapsed_seconds=95,
        timer_running=not question_answered,
        logout_href=NOOP_TARGET,
        question_statement_html=text_to_html(
            "Uma máquina produz 12 peças em 3 minutos.\n"
            "Mantendo o mesmo ritmo, quantas peças ela produz em 8 minutos?"
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
            alternative_text="24 peças",
            explanation="Essa conta manteria o total original, sem ampliar o tempo.",
            is_correct=False,
        ),
        DisplayAlternative(
            option_id="option_b",
            alternative_text="30 peças",
            explanation="Você multiplicou por 2,5 em vez de usar a razão entre 8 e 3 minutos.",
            is_correct=False,
        ),
        DisplayAlternative(
            option_id="option_c",
            alternative_text="32 peças",
            explanation="A taxa é de 4 peças por minuto, então em 8 minutos o total é 32.",
            is_correct=True,
        ),
        DisplayAlternative(
            option_id="option_d",
            alternative_text="36 peças",
            explanation="Isso consideraria 4,5 peças por minuto, o que não bate com o enunciado.",
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


def _theme_label(theme_mode: str) -> str:
    return "Claro" if theme_mode == "light" else "Escuro"


def main() -> None:
    """Run the static HTML preview app."""

    st.set_page_config(
        page_title="GlipMath HTML Preview",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.title("Preview das páginas HTML")
    st.caption("Os links, formulários e botões abaixo foram neutralizados de propósito.")

    preview_page = st.radio(
        "Tela",
        options=["login", "question"],
        format_func=lambda value: "Login" if value == "login" else "Sessão de questão",
        horizontal=True,
    )
    theme_mode = st.radio(
        "Tema",
        options=["dark", "light"],
        format_func=_theme_label,
        horizontal=True,
    )

    if preview_page == "login":
        button_disabled = st.checkbox("Mostrar botão do Google desabilitado", value=False)
        html = build_login_preview_html(
            theme_mode=theme_mode,
            button_disabled=button_disabled,
        )
    else:
        scenario = st.selectbox(
            "Cenário",
            options=list(QUESTION_PREVIEW_LABELS),
            format_func=QUESTION_PREVIEW_LABELS.get,
        )
        subject_menu_open = st.checkbox("Abrir menu de disciplinas", value=False)
        html = build_question_preview_html(
            theme_mode=theme_mode,
            scenario=scenario,
            subject_menu_open=subject_menu_open,
        )

    st.markdown(html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
