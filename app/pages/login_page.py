from __future__ import annotations

import streamlit as st

from app.components.auth_status import render_access_message, render_auth_setup_warning
from app.components.navigation import build_query_link, clear_query_param, get_query_param
from app.components.template_assets import get_template_logo_data_uri
from app.components.theme import render_theme_toggle_markup
from modules.auth.auth_service import trigger_login, trigger_logout
from modules.config.settings import AppSettings

GOOGLE_ICON_MARKUP = """
<svg class="gm-google-icon" viewBox="0 0 18 18" aria-hidden="true">
    <path fill="#4285F4" d="M17.64 9.2045c0-.6382-.0573-1.2518-.1636-1.8409H9v3.4818h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2582h2.9086c1.7018-1.5668 2.6837-3.8741 2.6837-6.6155Z"/>
    <path fill="#34A853" d="M9 18c2.43 0 4.4673-.8059 5.9563-2.1791l-2.9086-2.2582c-.8059.54-1.8368.8591-3.0477.8591-2.3455 0-4.3282-1.5845-5.0364-3.7136H.9573v2.3318A8.9995 8.9995 0 0 0 9 18Z"/>
    <path fill="#FBBC05" d="M3.9636 10.7082A5.4104 5.4104 0 0 1 3.6818 9c0-.5932.1023-1.1686.2818-1.7082V4.9609H.9573A8.9995 8.9995 0 0 0 0 9c0 1.4523.3482 2.8277.9573 4.0391l3.0063-2.3309Z"/>
    <path fill="#EA4335" d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.3455l2.5809-2.5809C13.4632.8918 11.426.0 9 .0A8.9995 8.9995 0 0 0 .9573 4.9609l3.0063 2.3309C4.6718 5.1641 6.6545 3.5795 9 3.5795Z"/>
</svg>
"""


def render_login_page(settings: AppSettings) -> None:
    """Render the unauthenticated login screen."""

    pending_action = get_query_param("glipmath_action")
    if pending_action == "login" and settings.auth.is_configured:
        clear_query_param("glipmath_action")
        trigger_login()
        st.stop()

    logo_uri = get_template_logo_data_uri(str(settings.repository_root))
    login_href = build_query_link(glipmath_action="login") if settings.auth.is_configured else ""
    button_class = "gm-google-button"
    if not settings.auth.is_configured:
        button_class += " is-disabled"

    st.markdown(
        f"""
        <section class="gm-login-shell">
            {render_theme_toggle_markup()}
            <div class="gm-login-card">
                <img class="gm-logo" src="{logo_uri}" alt="Glipmath" />
                <a class="{button_class}" href="{login_href}">
                    {GOOGLE_ICON_MARKUP}
                    <span>Continuar com Google</span>
                </a>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if not settings.auth.is_configured:
        render_auth_setup_warning()


def render_not_authorized_page(settings: AppSettings, email: str | None) -> None:
    """Render a generic post-login access issue screen."""

    st.markdown(render_theme_toggle_markup(), unsafe_allow_html=True)
    st.title(settings.app_name)
    render_access_message(email)
    if st.button("Sair da conta", type="secondary", use_container_width=True):
        trigger_logout()
        st.stop()
