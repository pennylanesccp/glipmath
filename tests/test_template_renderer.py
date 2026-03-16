from app.ui.template_renderer import raw_html, render_template


def test_render_template_escapes_plain_text_placeholders() -> None:
    html = render_template(
        "pages/question_session.html",
        {
            "THEME_NAME": "dark",
            "THEME_TOGGLE_HREF": "?theme=light",
            "THEME_TOGGLE_CLASS": "gm-theme-toggle--dark",
            "CURRENT_SUBJECT_LABEL": "<Matematica>",
            "SUBJECT_OPTIONS_HTML": raw_html("<a>Teste</a>"),
            "FIRE_ICON_DATA_URI": "data:image/svg+xml;base64,abc",
            "PODIUM_ICON_DATA_URI": "data:image/svg+xml;base64,xyz",
            "STREAK_TEXT": "1d / 2x",
            "RANK_TEXT": "#1 / 1",
            "TIMER_IFRAME_SRCDOC": "<html></html>",
            "LOGOUT_HREF": "?action=logout",
            "QUESTION_STATEMENT_HTML": raw_html("2 &lt; 3"),
            "ALTERNATIVES_HTML": raw_html("<div class='gm-option'>A</div>"),
            "BOTTOM_ACTION_HTML": raw_html("<div>Bottom</div>"),
        },
    )

    assert "&lt;Matematica&gt;" in html
    assert "<a>Teste</a>" in html
    assert "<div class='gm-option'>A</div>" in html


def test_render_template_preserves_raw_html_fragments() -> None:
    html = render_template(
        "pages/auth_login.html",
        {
            "THEME_NAME": "dark",
            "THEME_TOGGLE_HREF": "?theme=light",
            "THEME_TOGGLE_CLASS": "gm-theme-toggle--dark",
            "LOGO_DATA_URI": "data:image/png;base64,abc",
            "GOOGLE_BUTTON_HREF": "?action=login",
            "GOOGLE_BUTTON_CLASS": raw_html(" is-disabled"),
        },
    )

    assert 'class="gsi-material-button is-disabled"' in html
