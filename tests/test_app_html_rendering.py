from types import SimpleNamespace

from app.pages import login_page


def test_render_login_page_uses_streamlit_html(monkeypatch) -> None:
    html_calls: list[str] = []
    asset_paths: list[str] = []
    button_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        login_page,
        "_get_auth_redirect_runtime_status",
        lambda settings: SimpleNamespace(is_valid=True),
    )
    monkeypatch.setattr(
        login_page,
        "asset_to_data_uri",
        lambda relative_path: (asset_paths.append(relative_path) or "data:image/png;base64,abc"),
    )
    monkeypatch.setattr(login_page, "render_template", lambda template_path, context: "<section>login</section>")
    monkeypatch.setattr(login_page.st, "html", lambda html: html_calls.append(html))
    monkeypatch.setattr(
        login_page.st,
        "button",
        lambda label, **kwargs: (button_calls.append({"label": label, **kwargs}) or False),
    )
    monkeypatch.setattr(
        login_page.st,
        "markdown",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("st.markdown should not be used here")),
    )

    settings = SimpleNamespace(auth=SimpleNamespace(is_configured=True))

    login_page.render_login_page(settings)

    assert html_calls == ["<section>login</section>"]
    assert asset_paths[0] == "assets/brand/gliptec-logo.png"
    assert button_calls[0]["label"] == "Continuar com Google"


def test_render_login_page_click_starts_streamlit_login(monkeypatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(
        login_page,
        "_get_auth_redirect_runtime_status",
        lambda settings: SimpleNamespace(
            is_valid=True,
            issue_code=None,
            current_redirect_uri="https://glipmath.streamlit.app/oauth2callback",
            expected_redirect_uri="https://glipmath.streamlit.app/oauth2callback",
        ),
    )
    monkeypatch.setattr(login_page, "asset_to_data_uri", lambda relative_path: "data:image/png;base64,abc")
    monkeypatch.setattr(login_page, "render_template", lambda template_path, context: "<section>login</section>")
    monkeypatch.setattr(login_page.st, "html", lambda html: None)
    monkeypatch.setattr(login_page.st, "button", lambda label, **kwargs: True)
    monkeypatch.setattr(login_page, "trigger_login", lambda: events.append("login"))

    def stop() -> None:
        events.append("stop")
        raise RuntimeError("stop")

    monkeypatch.setattr(login_page.st, "stop", stop)

    settings = SimpleNamespace(auth=SimpleNamespace(is_configured=True))

    try:
        login_page.render_login_page(settings)
    except RuntimeError as error:
        assert str(error) == "stop"
    else:
        raise AssertionError("st.stop should interrupt the login flow")

    assert events == ["login", "stop"]
