from __future__ import annotations

import streamlit as st

from app.components.auth_status import (
    render_access_message,
    render_auth_redirect_warning,
    render_auth_setup_warning,
)
from app.ui.template_renderer import asset_to_data_uri, render_template
from modules.auth.auth_service import trigger_login, trigger_logout
from modules.config.settings import AppSettings, AuthRedirectRuntimeStatus
from modules.utils.logging_utils import get_logger


logger = get_logger(__name__)


def render_login_page(settings: AppSettings) -> None:
    """Render the template-driven login page and handle login actions."""

    redirect_status = _get_auth_redirect_runtime_status(settings)
    login_is_enabled = settings.auth.is_configured and redirect_status.is_valid
    logger.debug(
        "Rendering login page | auth_configured=%s | login_enabled=%s | redirect_issue=%s | runtime_app_url=%s | current_redirect_uri=%s | expected_redirect_uri=%s | cookie_names=%s | query_keys=%s",
        settings.auth.is_configured,
        login_is_enabled,
        redirect_status.issue_code or "<none>",
        _get_runtime_app_url() or "<unknown>",
        redirect_status.current_redirect_uri or "<missing>",
        redirect_status.expected_redirect_uri or "<unknown>",
        _get_request_cookie_names(),
        sorted(str(key) for key in st.query_params.keys()),
    )
    login_html = render_template(
        "pages/auth_login.html",
        {
            "LOGO_DATA_URI": asset_to_data_uri("assets/brand/gliptec-logo.png"),
            "GOOGLE_G_DATA_URI": asset_to_data_uri("assets/icons/google-g-logo.svg"),
        },
    )
    st.html(login_html)
    login_clicked = st.button(
        "Continuar com Google",
        key="gm_login_google_button",
        type="secondary",
        use_container_width=True,
        disabled=not login_is_enabled,
    )
    if login_clicked:
        logger.info(
            "OAuth login button clicked | auth_configured=%s | redirect_issue=%s | runtime_app_url=%s | current_redirect_uri=%s | expected_redirect_uri=%s | cookie_names=%s | query_keys=%s",
            settings.auth.is_configured,
            redirect_status.issue_code or "<none>",
            _get_runtime_app_url() or "<unknown>",
            redirect_status.current_redirect_uri or "<missing>",
            redirect_status.expected_redirect_uri or "<unknown>",
            _get_request_cookie_names(),
            sorted(str(key) for key in st.query_params.keys()),
        )
        logger.info("Starting Streamlit OAuth login redirect | provider=default")
        trigger_login()
        st.stop()
    st.html(render_template("pages/auth_login_footnote.html", {}))
    if not settings.auth.is_configured:
        render_auth_setup_warning()
    elif not redirect_status.is_valid:
        render_auth_redirect_warning(
            current_redirect_uri=redirect_status.current_redirect_uri,
            expected_redirect_uri=redirect_status.expected_redirect_uri,
        )


def render_not_authorized_page(settings: AppSettings, email: str | None) -> None:
    """Render a minimal post-login access issue screen."""

    render_login_page(settings)
    render_access_message(email)
    if st.button("Sair da conta", type="secondary", use_container_width=True):
        trigger_logout()
        st.stop()


def _get_auth_redirect_runtime_status(settings: AppSettings) -> AuthRedirectRuntimeStatus:
    return settings.auth.runtime_redirect_status(_get_runtime_app_url())


def _get_runtime_app_url() -> str | None:
    context = getattr(st, "context", None)
    url = getattr(context, "url", None)
    if not url:
        return None
    return str(url).strip() or None


def _get_request_cookie_names() -> list[str]:
    context = getattr(st, "context", None)
    cookies = getattr(context, "cookies", None)
    keys = getattr(cookies, "keys", None)
    if not callable(keys):
        return []
    try:
        return sorted(str(key) for key in keys())
    except TypeError:
        return []
