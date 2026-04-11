from __future__ import annotations

import json
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

    def __init__(self, *, api_key: str | None, model: str | None) -> None:
        if not api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY is not configured.")
        if not model:
            raise GeminiConfigurationError("GEMINI_MODEL is not configured.")

        self._model = model
        self._client = genai.Client(api_key=api_key)

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

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_json_schema=response_schema,
                ),
            )
        except Exception as exc:
            logger.exception("Gemini request failed | model=%s", self._model)
            raise GeminiGenerationError(f"Gemini request failed: {exc}") from exc

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
