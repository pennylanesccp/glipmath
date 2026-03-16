from __future__ import annotations

import streamlit as st

from app.ui.template_renderer import asset_to_data_uri, render_template


def render_login_page(
    google_login_url: str | None = None
    , is_dark_mode: bool = True
) -> None:
    logo_data_uri = asset_to_data_uri("assets/brand/ide-logo.png")

    button_href = google_login_url or "#"
    button_class = "" if google_login_url else " is-disabled"

    theme_name = "dark" if is_dark_mode else "light"
    next_theme = "light" if is_dark_mode else "dark"
    theme_toggle_href = f"?theme={next_theme}"
    theme_toggle_class = "gm-theme-toggle--dark" if is_dark_mode else "gm-theme-toggle--light"

    login_html = render_template(
        "pages/auth_login.html"
        , {
            "LOGO_DATA_URI": logo_data_uri
            , "GOOGLE_BUTTON_HREF": button_href
            , "GOOGLE_BUTTON_CLASS": button_class
            , "THEME_NAME": theme_name
            , "THEME_TOGGLE_HREF": theme_toggle_href
            , "THEME_TOGGLE_CLASS": theme_toggle_class
        }
    )

    st.markdown(login_html, unsafe_allow_html=True)