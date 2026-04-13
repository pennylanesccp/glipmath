from __future__ import annotations

from app.components import theme


def test_apply_app_theme_keeps_sidebar_navigation_available(monkeypatch) -> None:
    rendered_html: list[str] = []

    monkeypatch.setattr(theme.st, "html", lambda html: rendered_html.append(html))

    theme.apply_app_theme()

    assert len(rendered_html) == 1
    stylesheet = rendered_html[0]
    assert '[data-testid="stToolbar"]' in stylesheet
    assert '[data-testid="stStatusWidget"]' in stylesheet
    assert '[data-testid="stSidebar"]' not in stylesheet
    assert '[data-testid="collapsedControl"]' not in stylesheet
    assert '[data-testid="stHeader"]' not in stylesheet
