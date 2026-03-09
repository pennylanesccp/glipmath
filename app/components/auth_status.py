from __future__ import annotations

import streamlit as st


def render_auth_setup_warning() -> None:
    """Render a setup warning when auth secrets are missing."""

    st.warning(
        "A autenticacao Google ainda nao esta configurada. "
        "Preencha `.streamlit/secrets.toml` com os dados OIDC antes de usar o app."
    )


def render_unauthorized_message(email: str | None) -> None:
    """Render a friendly access-denied state."""

    st.error("Acesso nao autorizado.")
    st.write(
        "Sua conta Google foi autenticada, mas o seu email ainda nao esta liberado para usar o GlipMath."
    )
    if email:
        st.caption(f"Email detectado: {email}")
