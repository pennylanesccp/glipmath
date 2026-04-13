from __future__ import annotations

import streamlit as st


def apply_app_theme() -> None:
    """Minimize Streamlit chrome while keeping navigation controls available."""

    st.html(
        """
        <style>
        [data-testid="stToolbar"],
        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        .block-container {
            padding-top: 0.75rem;
            padding-bottom: 0.5rem;
        }
        </style>
        """
    )
