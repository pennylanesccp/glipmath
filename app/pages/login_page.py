from __future__ import annotations

from urllib.parse import urlencode

import streamlit as st

from app.components.auth_status import render_access_message, render_auth_setup_warning
from app.ui.template_renderer import asset_to_data_uri, render_template
from modules.auth.auth_service import trigger_login, trigger_logout
from modules.config.settings import AppSettings


def render_login_page(settings: AppSettings) -> None:
    """Render the template-driven login page and handle login actions."""

    _consume_login_actions(settings)
    login_html = render_template(
        "pages/auth_login.html",
        {
            "LOGO_DATA_URI": asset_to_data_uri("assets/brand/ide-logo.png"),
            "GOOGLE_BUTTON_HREF": _build_login_href(action="login"),
            "GOOGLE_BUTTON_CLASS": "" if settings.auth.is_configured else " is-disabled",
        },
    )
    st.markdown(login_html, unsafe_allow_html=True)
    if not settings.auth.is_configured:
        render_auth_setup_warning()


def render_not_authorized_page(settings: AppSettings, email: str | None) -> None:
    """Render a minimal post-login access issue screen."""

    render_login_page(settings)
    render_access_message(email)
    if st.button("Sair da conta", type="secondary", use_container_width=True):
        trigger_logout()
        st.stop()


def _consume_login_actions(settings: AppSettings) -> None:
    action = (_get_query_value("action") or "").strip().lower()
    if action != "login":
        return

    st.query_params.clear()
    if not settings.auth.is_configured:
        st.rerun()

    trigger_login()
    st.stop()


def _build_login_href(*, action: str | None = None) -> str:
    params: dict[str, str] = {}
    if action:
        params["action"] = action
    return f"?{urlencode(params)}" if params else "?"


def _get_query_value(key: str) -> str | None:
    raw_value = st.query_params.get(key)
    if raw_value is None:
        return None
    if isinstance(raw_value, list):
        return str(raw_value[0]).strip() if raw_value else None
    text = str(raw_value).strip()
    return text or None
