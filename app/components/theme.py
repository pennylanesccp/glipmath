from __future__ import annotations

import streamlit as st

from app.state.session_state import get_theme_mode, set_theme_mode
from app.ui.question_session import normalize_theme_mode


def apply_app_theme() -> None:
    """Sync the theme mode from the URL and hide Streamlit chrome."""

    requested_theme = _get_query_value("theme")
    if requested_theme is not None:
        normalized_requested_theme = normalize_theme_mode(requested_theme)
        if normalized_requested_theme != get_theme_mode():
            set_theme_mode(normalized_requested_theme)

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stToolbar"],
        [data-testid="stStatusWidget"],
        [data-testid="stHeader"] {
            display: none !important;
        }

        .block-container {
            padding-top: 0.75rem;
            padding-bottom: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _get_query_value(key: str) -> str | None:
    raw_value = st.query_params.get(key)
    if raw_value is None:
        return None
    if isinstance(raw_value, list):
        return str(raw_value[0]).strip() if raw_value else None
    text = str(raw_value).strip()
    return text or None
