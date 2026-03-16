from __future__ import annotations

import streamlit as st

from app.components.auth_status import render_access_message, render_auth_setup_warning
from modules.auth.auth_service import trigger_login, trigger_logout
from modules.config.settings import AppSettings


def render_login_page(settings: AppSettings) -> None:
    """Render the unauthenticated login screen."""

    st.title(settings.app_name)
    with st.container(border=True):
        st.write("Pratique questoes objetivas de matematica com acompanhamento simples de progresso.")
        st.info("O beta usa login Google e controle de acesso configurado no proprio app OAuth.")

        if not settings.auth.is_configured:
            render_auth_setup_warning()
            return

        if st.button("Entrar com Google", type="primary", use_container_width=True):
            trigger_login()


def render_not_authorized_page(settings: AppSettings, email: str | None) -> None:
    """Render a generic post-login access issue screen."""

    st.title(settings.app_name)
    with st.container(border=True):
        render_access_message(email)
        if st.button("Sair da conta", type="secondary", use_container_width=True):
            trigger_logout()
            st.stop()
