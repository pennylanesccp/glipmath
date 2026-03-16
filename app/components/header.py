from __future__ import annotations

import streamlit as st

from app.components.theme import render_theme_toggle

def render_header(*, app_name: str, user_name: str, user_email: str) -> bool:
    """Render the page header and return whether logout was requested."""

    title_column, user_column, theme_column, action_column = st.columns([4, 3, 1.5, 1])
    with title_column:
        st.title(app_name)
        st.caption("Entre, responda ou pule a questao e siga em frente.")
    with user_column:
        st.caption("Usuario logado")
        st.write(user_name)
        st.caption(user_email)
    with theme_column:
        st.caption("Visual")
        render_theme_toggle(key="glipmath_theme_toggle_authenticated")
    with action_column:
        st.write("")
        st.write("")
        return st.button("Sair", type="secondary", use_container_width=True)
