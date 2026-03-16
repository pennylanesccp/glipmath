from __future__ import annotations

import streamlit as st

from app.components.auth_status import render_access_message, render_auth_setup_warning
from modules.auth.auth_service import trigger_login, trigger_logout
from modules.config.settings import AppSettings


def render_login_page(settings: AppSettings) -> None:
    """Render the unauthenticated login screen."""

    st.markdown(
        """
        <style>
        .st-key-glipmath_google_login button {
          -moz-user-select: none;
          -webkit-user-select: none;
          -ms-user-select: none;
          -webkit-appearance: none;
          background-color: #FFFFFF;
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23FFC107' d='M43.611 20.083H42V20H24v8h11.303C33.654 32.657 29.192 36 24 36c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.277 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z'/%3E%3Cpath fill='%23FF3D00' d='M6.306 14.691l6.571 4.819C14.655 16.108 18.961 13 24 13c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.277 4 24 4C16.318 4 9.656 8.337 6.306 14.691z'/%3E%3Cpath fill='%234CAF50' d='M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.153 35.091 26.715 36 24 36c-5.171 0-9.625-3.33-11.287-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z'/%3E%3Cpath fill='%231976D2' d='M43.611 20.083H42V20H24v8h11.303c-.793 2.237-2.231 4.166-4.084 5.571c.001-.001 6.19 5.238 6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z'/%3E%3C/svg%3E");
          background-position: 12px center;
          background-repeat: no-repeat;
          background-size: 20px 20px;
          border: 1px solid #747775;
          border-radius: 4px;
          box-sizing: border-box;
          color: #1f1f1f !important;
          cursor: pointer;
          font-family: 'Roboto', arial, sans-serif;
          font-size: 14px;
          font-weight: 500;
          height: 40px;
          letter-spacing: 0.25px;
          max-width: 400px;
          min-width: min-content;
          outline: none;
          overflow: hidden;
          padding: 0 16px 0 44px;
          text-align: center;
          transition: background-color .218s, border-color .218s, box-shadow .218s;
          vertical-align: middle;
          white-space: nowrap;
          width: 100%;
        }

        .st-key-glipmath_google_login button:hover {
          box-shadow: 0 1px 2px 0 rgba(60, 64, 67, .30), 0 1px 3px 1px rgba(60, 64, 67, .15);
        }

        .st-key-glipmath_google_login button:focus,
        .st-key-glipmath_google_login button:active {
          background-color: #F8F9FA;
          border-color: #5F6368;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<h1 style='text-align:center;'>Glipmath</h1>", unsafe_allow_html=True)
    if not settings.auth.is_configured:
        render_auth_setup_warning()
        return

    left, center, right = st.columns([1.4, 2.2, 1.4])
    with center:
        if st.button(
            "Entrar com Google",
            key="glipmath_google_login",
            type="secondary",
            use_container_width=True,
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
