from __future__ import annotations

import streamlit as st


def render_auth_setup_warning() -> None:
    """Render a setup warning when auth configuration is missing."""

    st.warning(
        "A autenticacao Google ainda nao esta configurada. "
        "Preencha `.streamlit/secrets.toml` no ambiente local ou injete as variaveis de auth via Secret Manager no Cloud Run."
    )


def render_unauthorized_message(email: str | None) -> None:
    """Render a friendly access-denied state."""

    st.error("Acesso nao autorizado.")
    st.write(
        "Sua conta Google foi autenticada, mas este email ainda nao esta liberado para usar o GlipMath."
    )
    if email:
        st.caption(f"Email detectado: {email}")
