from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    """Copy worksheet templates into the local CSV development directory."""

    base_dir = Path(__file__).resolve().parents[1]
    templates_dir = base_dir / "data" / "templates"
    target_dir = base_dir / "data" / "local_dev"
    target_dir.mkdir(parents=True, exist_ok=True)

    mapping = {
        "question_bank_template.csv": "question_bank.csv",
        "whitelist_template.csv": "whitelist.csv",
        "answers_template.csv": "answers.csv",
    }
    for source_name, target_name in mapping.items():
        shutil.copyfile(templates_dir / source_name, target_dir / target_name)

    print(f"Seeded local CSV examples into {target_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
