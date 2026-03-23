from __future__ import annotations

import streamlit as st


def apply_app_theme() -> None:
    """Hide Streamlit chrome and keep the app shell compact."""

    st.html(
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
        """
    )
