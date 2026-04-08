from types import SimpleNamespace

from app.pages import login_page


def test_render_login_page_uses_streamlit_html(monkeypatch) -> None:
    html_calls: list[str] = []
    asset_paths: list[str] = []

    monkeypatch.setattr(login_page, "_consume_login_actions", lambda settings: None)
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
        "markdown",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("st.markdown should not be used here")),
    )

    settings = SimpleNamespace(auth=SimpleNamespace(is_configured=True))

    login_page.render_login_page(settings)

    assert html_calls == ["<section>login</section>"]
    assert asset_paths[0] == "assets/brand/gliptec-logo.png"
