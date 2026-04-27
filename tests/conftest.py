from __future__ import annotations

import hashlib
import re
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = REPO_ROOT / ".tmp" / "pytest_tmp"


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Iterator[Path]:
    """Provide a Windows-friendly temp path with readable local permissions."""

    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name).strip("_")[:64]
    digest = hashlib.sha1(request.node.nodeid.encode("utf-8")).hexdigest()[:10]
    path = TMP_ROOT / f"{slug}-{digest}"
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(mode=0o777, parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
