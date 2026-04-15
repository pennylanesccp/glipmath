from __future__ import annotations

import streamlit as st


def apply_app_theme() -> None:
    """Minimize Streamlit chrome while keeping navigation controls available."""

    st.html(
        """
        <style>
        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        [data-testid="stHeader"] {
            background: transparent !important;
            border-bottom: none !important;
            box-shadow: none !important;
        }

        [data-testid="stHeader"] [data-testid="stToolbarActions"],
        [data-testid="stHeader"] [data-testid="stToolbarActionButton"] {
            display: none !important;
        }

        [data-testid="stHeader"] a[href*="github.com"],
        [data-testid="stHeader"] a[href*="github.dev"],
        [data-testid="stHeader"] a[href*="codespaces"],
        [data-testid="stHeader"] a[href*="/fork"],
        [data-testid="stHeader"] a[title*="Fork" i],
        [data-testid="stHeader"] button[title*="Fork" i],
        [data-testid="stHeader"] [aria-label*="Fork" i],
        [data-testid="stHeader"] a[title*="Edit" i],
        [data-testid="stHeader"] button[title*="Edit" i],
        [data-testid="stHeader"] [aria-label*="Edit" i],
        [data-testid="stHeader"] a[title*="GitHub" i],
        [data-testid="stHeader"] button[title*="GitHub" i],
        [data-testid="stHeader"] [aria-label*="GitHub" i] {
            display: none !important;
        }

        .block-container {
            padding-top: 0.75rem;
            padding-bottom: 0.5rem;
        }
        </style>
        """
    )
