from __future__ import annotations

import streamlit as st

from app.components.auth_status import render_auth_setup_warning, render_unauthorized_message
from modules.auth.auth_service import trigger_login, trigger_logout
from modules.config.settings import AppSettings


def render_login_page(settings: AppSettings) -> None:
    """Render the unauthenticated login screen."""

    st.title(settings.app_name)
    st.write("Pratique questoes objetivas de matematica com acompanhamento simples de progresso.")
    st.info("O acesso e restrito a usuarios autenticados e previamente autorizados.")

    if not settings.auth.is_configured:
        render_auth_setup_warning()
        return

    if st.button("Entrar com Google", type="primary"):
        trigger_login()


def render_not_authorized_page(settings: AppSettings, email: str | None) -> None:
    """Render the post-login access denied screen."""

    st.title(settings.app_name)
    render_unauthorized_message(email)
    if st.button("Sair da conta", type="secondary"):
        trigger_logout()
        st.stop()
