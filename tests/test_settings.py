from modules.config.settings import AuthSettings


def _build_auth_settings(redirect_uri: str) -> AuthSettings:
    return AuthSettings(
        redirect_uri=redirect_uri,
        cookie_secret="cookie-secret",
        client_id="client-id",
        client_secret="client-secret",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    )


def test_runtime_redirect_status_flags_localhost_redirect_on_cloud_url() -> None:
    auth_settings = _build_auth_settings("http://localhost:8501/oauth2callback")

    status = auth_settings.runtime_redirect_status("https://glipmath.streamlit.app/")

    assert status.issue_code == "localhost_redirect"
    assert status.expected_redirect_uri == "https://glipmath.streamlit.app/oauth2callback"


def test_runtime_redirect_status_flags_host_mismatch_on_cloud_url() -> None:
    auth_settings = _build_auth_settings("https://other-app.streamlit.app/oauth2callback")

    status = auth_settings.runtime_redirect_status("https://glipmath.streamlit.app/")

    assert status.issue_code == "app_url_mismatch"
    assert status.expected_redirect_uri == "https://glipmath.streamlit.app/oauth2callback"


def test_runtime_redirect_status_accepts_matching_cloud_callback() -> None:
    auth_settings = _build_auth_settings("https://glipmath.streamlit.app/oauth2callback")

    status = auth_settings.runtime_redirect_status("https://glipmath.streamlit.app/")

    assert status.is_valid is True
    assert status.issue_code is None
