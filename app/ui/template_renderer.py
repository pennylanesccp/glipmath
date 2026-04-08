from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Mapping


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "templates"


@dataclass(frozen=True, slots=True)
class RawHtml:
    """Wrapper for already-sanitized HTML fragments injected into templates."""

    value: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def asset_to_data_uri(relative_path: str) -> str:
    asset_path = TEMPLATES_DIR / relative_path

    if not asset_path.exists():
        raise FileNotFoundError(f"Asset not found: {asset_path}")

    mime_type, _ = mimetypes.guess_type(asset_path.name)
    mime_type = mime_type or "application/octet-stream"

    encoded = base64.b64encode(asset_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def raw_html(value: str) -> RawHtml:
    """Mark a string as safe pre-rendered HTML for template injection."""

    return RawHtml(value)


def render_template(
    template_relative_path: str,
    context: Mapping[str, str | RawHtml],
) -> str:
    template_path = TEMPLATES_DIR / template_relative_path

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    html = _read_text(template_path)

    for key, value in context.items():
        rendered_value = value.value if isinstance(value, RawHtml) else escape(str(value), quote=True)
        html = html.replace(f"{{{{{key}}}}}", rendered_value)

    return html
