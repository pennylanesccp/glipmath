from __future__ import annotations

import streamlit as st


def render_header(*, app_name: str, user_name: str, user_email: str) -> bool:
    """Render the page header and return whether logout was requested."""

    title_column, user_column, action_column = st.columns([4, 3, 1])
    with title_column:
        st.title(app_name)
        st.caption("Pratique uma questao por vez e acompanhe sua evolucao.")
    with user_column:
        st.caption("Usuario logado")
        st.write(user_name)
        st.caption(user_email)
    with action_column:
        st.write("")
        st.write("")
        return st.button("Sair", type="secondary", use_container_width=True)
