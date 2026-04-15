from tests.preview_html_pages import build_login_preview_html, build_question_preview_html


def test_login_preview_is_static_and_uses_portuguese_copy() -> None:
    html = build_login_preview_html(button_disabled=True)

    assert 'href="#preview-static"' in html
    assert "<form" not in html
    assert "Continuar com Google" in html
    assert "Este app pode conter erros." in html
    assert "felipeproenca97@gmail.com" in html
    assert "Continue with Google" not in html


def test_question_preview_can_open_subject_menu_without_live_links() -> None:
    html = build_question_preview_html(
        scenario="pending",
        subject_menu_open=True,
    )

    assert '<details class="gm-subject-menu" open>' in html
    assert 'href="#preview-static"' in html
