from __future__ import annotations

import streamlit as st


def render_header(*, app_name: str, user_name: str, user_email: str) -> bool:
    """Render the page header and return whether logout was requested."""

    title_column, user_column, action_column = st.columns([3, 2, 1])
    with title_column:
        st.title(app_name)
    with user_column:
        st.caption("Aluno conectado")
        st.write(user_name)
        st.caption(user_email)
    with action_column:
        st.write("")
        return st.button("Sair", type="secondary", use_container_width=True)
