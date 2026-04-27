from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from google import genai
from google.genai import types

from modules.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GeminiConfigurationError(ValueError):
    """Raised when Gemini settings are missing or unusable."""


class GeminiGenerationError(RuntimeError):
    """Raised when Gemini does not return a usable structured response."""


class GeminiClient:
    """Thin wrapper around the official Google Gen AI SDK."""

    def __init__(
        self,
        *,
        api_keys: Sequence[str] | None = None,
        model: str | None,
        api_key: str | None = None,
    ) -> None:
        normalized_api_keys = _normalize_api_keys(api_keys=api_keys, api_key=api_key)
        if not normalized_api_keys:
            raise GeminiConfigurationError("GEMINI_API_KEYS is not configured.")
        if not model:
            raise GeminiConfigurationError("GEMINI_MODEL is not configured.")

        self._model = model
        self._api_keys = normalized_api_keys
        self._clients: dict[int, Any] = {}

    @property
    def model(self) -> str:
        """Return the configured Gemini model name."""

        return self._model

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Generate one structured JSON response."""

        response = None
        last_key_index = len(self._api_keys) - 1
        for key_index, _ in enumerate(self._api_keys):
            try:
                response = self._client_for_key(key_index).models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_json_schema=response_schema,
                    ),
                )
                break
            except Exception as exc:
                if key_index < last_key_index and _is_quota_exhausted_error(exc):
                    logger.warning(
                        "Gemini API key quota exhausted; retrying with next key | "
                        "model=%s key_index=%s",
                        self._model,
                        key_index,
                    )
                    continue

                logger.exception(
                    "Gemini request failed | model=%s key_index=%s",
                    self._model,
                    key_index,
                )
                raise GeminiGenerationError(f"Gemini request failed: {exc}") from exc

        if response is None:
            raise GeminiGenerationError("Gemini request failed.")

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, dict):
            return parsed

        response_text = getattr(response, "text", None)
        if isinstance(response_text, str) and response_text.strip():
            try:
                payload = json.loads(response_text)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                return payload

        raise GeminiGenerationError(
            "Gemini did not return a structured JSON object."
        )

    def _client_for_key(self, key_index: int) -> Any:
        client = self._clients.get(key_index)
        if client is None:
            client = genai.Client(api_key=self._api_keys[key_index])
            self._clients[key_index] = client
        return client


def _normalize_api_keys(
    *,
    api_keys: Sequence[str] | None,
    api_key: str | None,
) -> tuple[str, ...]:
    if api_keys is not None:
        if isinstance(api_keys, str):
            api_keys = api_keys.split(",")
        return tuple(
            text
            for item in api_keys
            if isinstance(item, str) and (text := item.strip())
        )
    if api_key is None:
        return ()
    text = api_key.strip()
    return (text,) if text else ()


def _is_quota_exhausted_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code == 429:
        return True

    status = str(getattr(exc, "status", "") or "").upper()
    message = f"{getattr(exc, 'message', '')} {exc}".upper()
    return any(
        marker in status or marker in message
        for marker in (
            "RESOURCE_EXHAUSTED",
            "RATE_LIMIT",
            "RATE LIMIT",
            "TOO MANY REQUESTS",
            "QUOTA EXCEEDED",
            "429",
        )
    )
