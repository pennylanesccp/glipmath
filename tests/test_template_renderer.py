from app.ui.template_renderer import raw_html, render_template


def test_render_template_escapes_plain_text_placeholders() -> None:
    html = render_template(
        "pages/question_session.html",
        {
            "CURRENT_SUBJECT_LABEL": "<Matematica>",
            "SUBJECT_OPTIONS_HTML": raw_html("<a>Teste</a>"),
            "FIRE_ICON_DATA_URI": "data:image/svg+xml;base64,abc",
            "PODIUM_ICON_DATA_URI": "data:image/svg+xml;base64,xyz",
            "STREAK_TEXT": "1d / 2x",
            "RANK_TEXT": "#1 / 1",
            "TIMER_HTML": raw_html("<div class='gm-inline-timer-chip'>00:10</div>"),
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
            "LOGO_DATA_URI": "data:image/png;base64,abc",
            "GOOGLE_G_DATA_URI": "data:image/svg+xml;base64,google",
        },
    )

    assert 'src="data:image/png;base64,abc"' in html
    assert 'url("data:image/svg+xml;base64,google")' in html
    assert "Continuar com Google" not in html
    assert "Este app pode conter erros." not in html

    footnote_html = render_template("pages/auth_login_footnote.html", {})

    assert "Este app pode conter erros." in footnote_html
    assert 'href="mailto:felipeproenca97@gmail.com"' in footnote_html
