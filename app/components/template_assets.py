from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=None)
def get_template_asset_data_uri(base_dir: str, asset_name: str) -> str:
    """Return a template asset as a base64 data URI."""

    asset_path = Path(base_dir) / "templates" / asset_name
    mime_type, _ = mimetypes.guess_type(asset_path.name)
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:{mime_type or 'application/octet-stream'};base64,{encoded}"


@lru_cache(maxsize=None)
def get_template_logo_data_uri(base_dir: str) -> str:
    """Return the best available template logo/image asset as a data URI."""

    templates_dir = Path(base_dir) / "templates"
    candidate_paths = sorted(templates_dir.glob("*.png"))
    if not candidate_paths:
        raise FileNotFoundError("No PNG logo/image asset was found inside templates/.")

    preferred = next(
        (path for path in candidate_paths if "logo" in path.stem.lower()),
        candidate_paths[0],
    )
    mime_type, _ = mimetypes.guess_type(preferred.name)
    encoded = base64.b64encode(preferred.read_bytes()).decode("ascii")
    return f"data:{mime_type or 'image/png'};base64,{encoded}"
