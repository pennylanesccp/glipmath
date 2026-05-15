from __future__ import annotations

import tomllib
from pathlib import Path

from app.components import theme


def test_apply_app_theme_keeps_sidebar_navigation_available(monkeypatch) -> None:
    rendered_html: list[str] = []

    monkeypatch.setattr(theme.st, "html", lambda html: rendered_html.append(html))

    theme.apply_app_theme()

    assert len(rendered_html) == 1
    stylesheet = rendered_html[0]
    assert '[data-testid="stStatusWidget"]' in stylesheet
    assert '[data-testid="stSidebar"]' not in stylesheet
    assert '[data-testid="stToolbar"] {' not in stylesheet
    assert '[data-testid="collapsedControl"]' not in stylesheet
    assert '[data-testid="stHeader"]' in stylesheet
    assert "background: transparent !important;" in stylesheet
    assert ".stToolbarActions" in stylesheet
    assert ".stToolbarActionButton" in stylesheet
    assert '[data-testid="stToolbarActions"]' in stylesheet
    assert '[data-testid="stToolbarActionButton"]' in stylesheet
    assert '[data-testid="stAppDeployButton"]' in stylesheet
    assert 'a[href*="github.com"]' in stylesheet
    assert '[aria-label*="Fork" i]' in stylesheet
    assert '[aria-label*="GitHub" i]' in stylesheet


def test_streamlit_config_hides_cloud_top_bar() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((repo_root / ".streamlit" / "config.toml").read_text())

    assert config["client"]["toolbarMode"] == "minimal"
    assert config["ui"]["hideTopBar"] is True
