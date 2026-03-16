from __future__ import annotations

import base64
import mimetypes

from html import escape
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "templates"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def asset_to_data_uri(relative_path: str) -> str:
    asset_path = TEMPLATES_DIR / relative_path

    if not asset_path.exists():
        raise FileNotFoundError(f"Asset not found: {asset_path}")

    mime_type, _ = mimetypes.guess_type(asset_path.name)
    mime_type = mime_type or "application/octet-stream"

    encoded = base64.b64encode(asset_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def render_template(
    template_relative_path: str
    , context: dict[str, str]
) -> str:
    template_path = TEMPLATES_DIR / template_relative_path

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    html = _read_text(template_path)

    for key, value in context.items():
        html = html.replace(f"{{{{{key}}}}}", escape(str(value), quote=True))

    return html