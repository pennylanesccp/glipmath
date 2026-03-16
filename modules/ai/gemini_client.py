from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types


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
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version="v1"),
        )

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
                    response_schema=response_schema,
                ),
            )
        except Exception as exc:
            raise GeminiGenerationError("Gemini request failed.") from exc

        parsed = getattr(response, "parsed", None)
        if not isinstance(parsed, dict):
            raise GeminiGenerationError(
                "Gemini did not return a structured JSON object."
            )
        return parsed
