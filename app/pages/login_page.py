from __future__ import annotations

import streamlit as st

from app.components.auth_status import render_access_message, render_auth_setup_warning
from app.state.session_state import get_theme_mode
from modules.auth.auth_service import trigger_login, trigger_logout
from modules.config.settings import AppSettings


def render_login_page(settings: AppSettings) -> None:
    """Render the unauthenticated login screen."""

    is_light_mode = get_theme_mode() == "light"
    button_background = "#FFFFFF" if is_light_mode else "#131314"
    button_text = "#1f1f1f" if is_light_mode else "#e3e3e3"
    button_border = "#747775" if is_light_mode else "#8e918f"
    button_disabled_background = "#ffffff61" if is_light_mode else "#13131461"
    button_disabled_border = "#1f1f1f1f" if is_light_mode else "#8e918f1f"
    button_state_color = "#303030" if is_light_mode else "white"

    button_css = """
        <style>
        .st-key-glipmath_google_login {
          display: flex;
          justify-content: center;
        }

        .st-key-glipmath_google_login button {
          -moz-user-select: none;
          -webkit-user-select: none;
          -ms-user-select: none;
          -webkit-appearance: none;
          appearance: none;
          align-items: center;
          background-color: __BUTTON_BACKGROUND__;
          background-image: none;
          border: 1px solid __BUTTON_BORDER__;
          border-radius: 4px;
          box-sizing: border-box;
          color: __BUTTON_TEXT__;
          cursor: pointer;
          display: flex;
          font-family: 'Roboto', arial, sans-serif;
          font-size: 14px;
          font-weight: 500;
          height: 40px;
          letter-spacing: 0.25px;
          max-width: 400px;
          min-width: min-content;
          outline: none;
          overflow: hidden;
          padding: 0 12px;
          position: relative;
          text-align: left;
          transition: background-color .218s, border-color .218s, box-shadow .218s;
          vertical-align: middle;
          white-space: nowrap;
          width: auto;
        }

        .st-key-glipmath_google_login button::before {
          content: "";
          background-image: url("data:image/svg+xml,%3Csvg version='1.1' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23EA4335' d='M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0C14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z'/%3E%3Cpath fill='%234285F4' d='M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z'/%3E%3Cpath fill='%23FBBC05' d='M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z'/%3E%3Cpath fill='%2334A853' d='M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3c-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z'/%3E%3Cpath fill='none' d='M0 0h48v48H0z'/%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-size: 20px 20px;
          display: block;
          flex: 0 0 20px;
          height: 20px;
          margin-right: 10px;
          min-width: 20px;
          position: relative;
          width: 20px;
        }

        .st-key-glipmath_google_login button::after {
          background-color: __BUTTON_STATE_COLOR__;
          bottom: 0;
          content: "";
          left: 0;
          opacity: 0;
          pointer-events: none;
          position: absolute;
          right: 0;
          top: 0;
          transition: opacity .218s;
        }

        .st-key-glipmath_google_login button > div {
          align-items: center;
          display: flex;
          flex-direction: row;
          flex-wrap: nowrap;
          height: 100%;
          justify-content: space-between;
          position: relative;
          width: 100%;
        }

        .st-key-glipmath_google_login button p {
          color: __BUTTON_TEXT__;
          flex-grow: 1;
          font-family: 'Roboto', arial, sans-serif;
          font-size: 14px;
          font-weight: 500;
          line-height: 20px;
          margin: 0;
          overflow: hidden;
          text-align: left;
          text-overflow: ellipsis;
          vertical-align: top;
        }

        .st-key-glipmath_google_login button:disabled {
          background-color: __BUTTON_DISABLED_BACKGROUND__;
          border-color: __BUTTON_DISABLED_BORDER__;
          cursor: default;
        }

        .st-key-glipmath_google_login button:disabled::before,
        .st-key-glipmath_google_login button:disabled p {
          opacity: 38%;
        }

        .st-key-glipmath_google_login button:not(:disabled):active::after,
        .st-key-glipmath_google_login button:not(:disabled):focus::after {
          opacity: 12%;
        }

        .st-key-glipmath_google_login button:not(:disabled):hover {
          box-shadow: 0 1px 2px 0 rgba(60, 64, 67, .30), 0 1px 3px 1px rgba(60, 64, 67, .15);
        }

        .st-key-glipmath_google_login button:not(:disabled):hover::after {
          opacity: 8%;
        }
        </style>
        """
    button_css = (
        button_css
        .replace("__BUTTON_BACKGROUND__", button_background)
        .replace("__BUTTON_BORDER__", button_border)
        .replace("__BUTTON_TEXT__", button_text)
        .replace("__BUTTON_DISABLED_BACKGROUND__", button_disabled_background)
        .replace("__BUTTON_DISABLED_BORDER__", button_disabled_border)
        .replace("__BUTTON_STATE_COLOR__", button_state_color)
    )

    st.markdown(
        button_css,
        unsafe_allow_html=True,
    )

    st.markdown("<h1 style='text-align:center;'>Glipmath</h1>", unsafe_allow_html=True)
    if not settings.auth.is_configured:
        render_auth_setup_warning()
        return

    if st.button(
        "Continuar com Google",
        key="glipmath_google_login",
        type="secondary",
        use_container_width=False,
    ):
        trigger_login()


def render_not_authorized_page(settings: AppSettings, email: str | None) -> None:
    """Render a generic post-login access issue screen."""

    st.title(settings.app_name)
    with st.container(border=True):
        render_access_message(email)
        if st.button("Sair da conta", type="secondary", use_container_width=True):
            trigger_logout()
            st.stop()
