from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def test_streamlit_entrypoint_bootstraps_repo_root_for_file_execution() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    entrypoint_path = repo_root / "app" / "streamlit_app.py"
    original_sys_path = list(sys.path)

    try:
        sys.path = [
            path
            for path in sys.path
            if Path(path or ".").resolve() != repo_root
        ]

        spec = importlib.util.spec_from_file_location(
            "streamlit_app_bootstrap_test",
            entrypoint_path,
        )
        assert spec is not None
        assert spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        assert sys.path[0] == str(repo_root)
    finally:
        sys.path = original_sys_path
        sys.modules.pop("streamlit_app_bootstrap_test", None)
