from __future__ import annotations

import re

from typing import Literal

import streamlit as st
import streamlit.components.v1 as components

from app.ui.question_session import render_question_session_template, text_to_html
from app.ui.template_renderer import asset_to_data_uri, render_template
from modules.domain.models import DisplayAlternative

NOOP_TARGET = "#preview-static"
SUBJECT_OPTIONS = ["Tudo", "Matematica", "Portugues", "Ciencias"]
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


def build_login_preview_html(*, button_disabled: bool) -> str:
    """Render the login template as a static preview."""

    html = render_template(
        "pages/auth_login.html",
        {
            "LOGO_DATA_URI": asset_to_data_uri("assets/brand/gliptec-logo.png"),
            "GOOGLE_G_DATA_URI": asset_to_data_uri("assets/icons/google-g-logo.svg"),
        },
    )
    disabled_attr = " disabled" if button_disabled else ""
    static_button = (
        '<div class="st-key-gm_login_google_button">'
        f'<button type="button"{disabled_attr}>'
        '<span data-testid="stMarkdownContainer"><p>Continuar com Google</p></span>'
        "</button>"
        "</div>"
    )
    footnote_html = render_template("pages/auth_login_footnote.html", {})
    return _make_static_preview(f"{html}\n{static_button}\n{footnote_html}")


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
        selected_subject="Matematica",
        subject_options=SUBJECT_OPTIONS,
        streak_text="5d / 14x",
        rank_text="#7 / 38",
        timer_elapsed_seconds=95,
        timer_running=not question_answered,
        logout_href=NOOP_TARGET,
        question_statement_html=text_to_html(
            "Uma maquina produz 12 pecas em 3 minutos.\n"
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
    _apply_preview_shell()
    st.title("Preview das páginas HTML")
    st.caption("Os links, formulários e botões abaixo foram neutralizados de propósito.")

    preview_page = st.radio(
        "Tela",
        options=["login", "question"],
        format_func=lambda value: "Login" if value == "login" else "Sessão de questão",
        horizontal=True,
    )

    if preview_page == "login":
        button_disabled = st.checkbox("Mostrar botão do Google desabilitado", value=False)
        html = build_login_preview_html(
            button_disabled=button_disabled,
        )
        preview_height = 760
    else:
        scenario = st.selectbox(
            "Cenário",
            options=list(QUESTION_PREVIEW_LABELS),
            format_func=QUESTION_PREVIEW_LABELS.get,
        )
        subject_menu_open = st.checkbox("Abrir menu de disciplinas", value=False)
        html = build_question_preview_html(
            scenario=scenario,
            subject_menu_open=subject_menu_open,
        )
        preview_height = 1080

    components.html(html, height=preview_height, scrolling=True)


def _apply_preview_shell() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top, rgba(79, 70, 229, 0.16), transparent 28%),
                linear-gradient(180deg, #eff6ff 0%, #f8fafc 100%);
        }

        .stApp,
        .stApp label,
        .stApp span,
        .stApp div {
            color: #0f172a;
        }

        .stApp h1 {
            color: #312e81;
        }

        .stApp p {
            color: #475569;
        }

        [data-testid="stMarkdownContainer"] p {
            color: #475569;
        }

        [data-baseweb="radio"] label,
        [data-baseweb="checkbox"] label,
        [data-baseweb="select"] * {
            color: #0f172a !important;
        }

        [data-baseweb="select"] > div,
        [data-baseweb="radio"] > div,
        [data-baseweb="checkbox"] > div {
            background: rgba(255, 255, 255, 0.88);
            border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
