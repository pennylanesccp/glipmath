from __future__ import annotations

from types import SimpleNamespace

import pytest

from modules.ai import gemini_client


class FakeResponse:
    def __init__(self, *, parsed=None, text: str | None = None) -> None:
        self.parsed = parsed
        self.text = text


class FakeModels:
    def __init__(self, *, response: FakeResponse | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


class FakeSdkClient:
    def __init__(self, *, response: FakeResponse | None = None, error: Exception | None = None) -> None:
        self.models = FakeModels(response=response, error=error)


def test_gemini_client_requires_api_key_and_model() -> None:
    with pytest.raises(gemini_client.GeminiConfigurationError):
        gemini_client.GeminiClient(api_keys=(), model="gemini-test")

    with pytest.raises(gemini_client.GeminiConfigurationError):
        gemini_client.GeminiClient(api_keys=("secret",), model=None)


def test_gemini_client_uses_response_json_schema(monkeypatch) -> None:
    fake_sdk_client = FakeSdkClient(response=FakeResponse(parsed={"statement": "ok"}))
    captured_init_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        gemini_client.genai,
        "Client",
        lambda **kwargs: captured_init_kwargs.update(kwargs) or fake_sdk_client,
    )
    monkeypatch.setattr(
        gemini_client.types,
        "GenerateContentConfig",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    client = gemini_client.GeminiClient(api_keys=("secret",), model="gemini-test")
    payload = client.generate_json(
        prompt="hello",
        response_schema={"type": "object"},
        temperature=0.3,
    )

    assert payload == {"statement": "ok"}
    assert captured_init_kwargs == {"api_key": "secret"}
    config = fake_sdk_client.models.calls[0]["config"]
    assert getattr(config, "response_json_schema") == {"type": "object"}
    assert getattr(config, "response_mime_type") == "application/json"


def test_gemini_client_falls_back_to_json_text_when_parsed_is_missing(monkeypatch) -> None:
    fake_sdk_client = FakeSdkClient(
        response=FakeResponse(parsed=None, text='{"statement":"ok"}')
    )

    monkeypatch.setattr(
        gemini_client.genai,
        "Client",
        lambda **kwargs: fake_sdk_client,
    )
    monkeypatch.setattr(
        gemini_client.types,
        "GenerateContentConfig",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    client = gemini_client.GeminiClient(api_keys=("secret",), model="gemini-test")
    payload = client.generate_json(
        prompt="hello",
        response_schema={"type": "object"},
    )

    assert payload == {"statement": "ok"}


def test_gemini_client_retries_next_key_when_quota_is_exhausted(monkeypatch) -> None:
    class FakeQuotaError(RuntimeError):
        code = 429

    clients = {
        "spent": FakeSdkClient(error=FakeQuotaError("quota exceeded")),
        "fresh": FakeSdkClient(response=FakeResponse(parsed={"statement": "ok"})),
    }
    initialized_keys: list[str] = []

    def build_fake_client(**kwargs):
        api_key = str(kwargs["api_key"])
        initialized_keys.append(api_key)
        return clients[api_key]

    monkeypatch.setattr(gemini_client.genai, "Client", build_fake_client)
    monkeypatch.setattr(
        gemini_client.types,
        "GenerateContentConfig",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    client = gemini_client.GeminiClient(api_keys=("spent", "fresh"), model="gemini-test")
    payload = client.generate_json(
        prompt="hello",
        response_schema={"type": "object"},
    )

    assert payload == {"statement": "ok"}
    assert initialized_keys == ["spent", "fresh"]
    assert len(clients["spent"].models.calls) == 1
    assert len(clients["fresh"].models.calls) == 1


def test_gemini_client_surfaces_underlying_sdk_error(monkeypatch) -> None:
    fake_sdk_client = FakeSdkClient(error=RuntimeError("403 model not found"))

    monkeypatch.setattr(
        gemini_client.genai,
        "Client",
        lambda **kwargs: fake_sdk_client,
    )
    monkeypatch.setattr(
        gemini_client.types,
        "GenerateContentConfig",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    client = gemini_client.GeminiClient(api_keys=("secret",), model="gemini-test")

    with pytest.raises(gemini_client.GeminiGenerationError) as exc_info:
        client.generate_json(
            prompt="hello",
            response_schema={"type": "object"},
        )

    assert "403 model not found" in str(exc_info.value)
