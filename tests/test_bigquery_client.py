import pytest

from modules.storage import bigquery_client as bigquery_client_module
from modules.storage.bigquery_client import BigQueryClient, BigQueryError


def test_bigquery_client_requires_explicit_credentials_when_adc_disabled(
    monkeypatch,
) -> None:
    def _unexpected_client(*args, **kwargs):
        raise AssertionError("bigquery.Client should not be constructed")

    monkeypatch.setattr(bigquery_client_module.bigquery, "Client", _unexpected_client)

    with pytest.raises(BigQueryError, match=r"\[gcp_service_account\]"):
        BigQueryClient(
            project_id="ide-math-app",
            location="southamerica-east1",
            allow_application_default_credentials=False,
        )


def test_bigquery_client_uses_streamlit_service_account(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_credentials = object()
    service_account_info = {
        "type": "service_account",
        "project_id": "ide-math-app",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
        "client_email": "glipmath@ide-math-app.iam.gserviceaccount.com",
        "client_id": "client-id",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    def _fake_from_service_account_info(info):
        captured["service_account_info"] = info
        return fake_credentials

    def _fake_client(*, project, location, credentials):
        captured["project"] = project
        captured["location"] = location
        captured["credentials"] = credentials
        return object()

    monkeypatch.setattr(
        bigquery_client_module.service_account.Credentials,
        "from_service_account_info",
        _fake_from_service_account_info,
    )
    monkeypatch.setattr(bigquery_client_module.bigquery, "Client", _fake_client)

    BigQueryClient(
        project_id="ide-math-app",
        location="southamerica-east1",
        service_account_info=service_account_info,
    )

    assert captured["service_account_info"] == service_account_info
    assert captured["project"] == "ide-math-app"
    assert captured["location"] == "southamerica-east1"
    assert captured["credentials"] is fake_credentials


def test_bigquery_client_allows_adc_by_default(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_client(*, project, location, credentials):
        captured["project"] = project
        captured["location"] = location
        captured["credentials"] = credentials
        return object()

    monkeypatch.setattr(bigquery_client_module.bigquery, "Client", _fake_client)

    BigQueryClient(
        project_id="ide-math-app",
        location="southamerica-east1",
    )

    assert captured["project"] == "ide-math-app"
    assert captured["location"] == "southamerica-east1"
    assert captured["credentials"] is None
