from __future__ import annotations

import streamlit as st

from app.state.session_state import get_theme_mode, set_theme_mode

THEMES = {
    "dark": {
        "background": "#0B1120",
        "surface": "#111827",
        "surface_alt": "#1F2937",
        "text": "#E5E7EB",
        "muted": "#94A3B8",
        "border": "#334155",
        "accent": "#22C55E",
        "accent_text": "#04130A",
        "danger": "#F87171",
    },
    "light": {
        "background": "#F8FAFC",
        "surface": "#FFFFFF",
        "surface_alt": "#E2E8F0",
        "text": "#102A43",
        "muted": "#486581",
        "border": "#CBD5E1",
        "accent": "#0F766E",
        "accent_text": "#F8FAFC",
        "danger": "#B91C1C",
    },
}


def apply_app_theme() -> None:
    """Apply the current theme and remove the default sidebar navigation."""

    palette = THEMES[get_theme_mode()]
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: {palette["background"]};
        }}

        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] p,
        [data-testid="stAppViewContainer"] li,
        [data-testid="stAppViewContainer"] label,
        [data-testid="stAppViewContainer"] span,
        [data-testid="stAppViewContainer"] div {{
            color: {palette["text"]};
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        [data-testid="stMetric"],
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stForm"] {{
            background: {palette["surface"]};
            border: 1px solid {palette["border"]};
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 16px;
        }}

        div.stButton > button,
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="radio"] label {{
            background: {palette["surface"]};
            color: {palette["text"]};
            border-color: {palette["border"]};
        }}

        div.stButton > button[kind="primary"] {{
            background: {palette["accent"]};
            color: {palette["accent_text"]};
            border-color: {palette["accent"]};
        }}

        div.stButton > button:hover {{
            border-color: {palette["accent"]};
            color: {palette["text"]};
        }}

        [data-testid="stCaptionContainer"] {{
            color: {palette["muted"]};
        }}

        .stAlert {{
            border-radius: 14px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_theme_toggle(*, key: str) -> None:
    """Render the light/dark toggle and persist the choice."""

    is_light_mode = st.toggle(
        "Modo claro",
        value=get_theme_mode() == "light",
        key=key,
    )
    target_mode = "light" if is_light_mode else "dark"
    if target_mode != get_theme_mode():
        set_theme_mode(target_mode)
        st.rerun()
