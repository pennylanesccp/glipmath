from __future__ import annotations

import streamlit as st


def render_auth_setup_warning() -> None:
    """Render a setup warning when auth configuration is missing."""

    st.warning(
        "A autenticacao Google ainda nao esta configurada. "
        "Preencha `.streamlit/secrets.toml` localmente ou configure os mesmos segredos no Streamlit Community Cloud."
    )


def render_access_message(email: str | None) -> None:
    """Render a generic access issue state."""

    st.error("Nao foi possivel concluir o acesso.")
    st.write(
        "O beta usa a configuracao do Google OAuth para controlar quem pode entrar. "
        "Se o login funcionou, mas o app nao conseguiu continuar, confirme se a conta devolveu um email valido."
    )
    if email:
        st.caption(f"Email detectado: {email}")
