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

        [data-testid="stHeader"] {
            background: rgba(248, 250, 252, 0.94) !important;
            backdrop-filter: blur(10px);
        }

        [data-testid="collapsedControl"] {
            display: flex !important;
            visibility: visible !important;
        }

        [data-testid="collapsedControl"] button {
            background: #ffffff !important;
            border: 1px solid #dbeafe !important;
            border-radius: 0.9rem !important;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08) !important;
            color: #1e3a8a !important;
        }

        [data-testid="collapsedControl"] button:hover {
            background: #eff6ff !important;
            border-color: #bfdbfe !important;
        }

        .block-container {
            padding-top: 0.75rem;
            padding-bottom: 0.5rem;
        }
        </style>
        """
    )
