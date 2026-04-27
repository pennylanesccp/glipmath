from pathlib import Path

from modules.config.settings import AuthSettings, load_settings


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


def test_load_settings_reads_public_repo_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GLIPMATH_APP_NAME", raising=False)
    monkeypatch.delenv("GLIPMATH_GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GLIPMATH_ANSWERS_TABLE", raising=False)
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    (tmp_path / "glipmath.toml").write_text(
        "\n".join(
            [
                "[app]",
                'app_name = "Repo Config"',
                "",
                "[gcp]",
                'project_id = "repo-project"',
                "",
                "[bigquery]",
                'answers_table = "repo_answers"',
                "",
                "[ai]",
                'model = "repo-model"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(secrets={}, base_dir=tmp_path)

    assert settings.app_name == "Repo Config"
    assert settings.gcp.project_id == "repo-project"
    assert settings.bigquery.answers_table == "repo_answers"
    assert settings.gemini.api_keys == ()
    assert settings.gemini.model == "repo-model"


def test_load_settings_prefers_secrets_over_public_repo_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("GLIPMATH_GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GLIPMATH_ANSWERS_TABLE", raising=False)
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    (tmp_path / "glipmath.toml").write_text(
        "\n".join(
            [
                "[gcp]",
                'project_id = "repo-project"',
                "",
                "[bigquery]",
                'answers_table = "repo_answers"',
                "",
                "[ai]",
                'model = "repo-model"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(
        secrets={
            "gcp": {"project_id": "secret-project"},
            "bigquery": {"answers_table": "secret_answers"},
            "ai": {
                "GEMINI_API_KEYS": ["first-key", "second-key"],
                "GEMINI_MODEL": "secret-model",
            },
        },
        base_dir=tmp_path,
    )

    assert settings.gcp.project_id == "secret-project"
    assert settings.bigquery.answers_table == "secret_answers"
    assert settings.gemini.api_keys == ("first-key", "second-key")
    assert settings.gemini.model == "secret-model"


def test_load_settings_reads_gemini_api_keys_from_comma_separated_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEYS", "first-key, second-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    settings = load_settings(secrets={}, base_dir=tmp_path)

    assert settings.gemini.api_keys == ("first-key", "second-key")
