import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.apply_question_seed_jsons import load_seed_batches, materialize_seed_payload


def test_materialize_seed_payload_merges_defaults_and_sets_timestamps() -> None:
    generated_at = datetime(2026, 4, 9, 15, 0, tzinfo=timezone.utc)
    batch = materialize_seed_payload(
        {
            "table_id": "project.dataset.question_bank",
            "delete": {
                "source": "seed_v1",
                "cohort_key": "certificacao",
            },
            "defaults": {
                "subject": "Databricks",
                "topic": "streaming",
                "source": "seed_v1",
                "cohort_key": "certificacao",
                "is_active": True,
            },
            "questions": [
                {
                    "id_question": 6200,
                    "statement": "Pergunta",
                    "difficulty": "easy",
                    "correct_answer": {
                        "alternative_text": "`STREAM`",
                        "explanation": "Resposta certa.",
                    },
                    "wrong_answers": [
                        {
                            "alternative_text": "`BATCH`",
                            "explanation": "Resposta errada.",
                        }
                    ],
                }
            ],
        },
        source_path=Path("local/bq_seeds/source/databricks/dbx_03_structured_streaming.json"),
        generated_at=generated_at,
    )

    assert batch.table_id == "project.dataset.question_bank"
    assert batch.delete_scope == {
        "source": "seed_v1",
        "cohort_key": "certificacao",
    }
    assert batch.rows == [
        {
            "id_question": 6200,
            "statement": "Pergunta",
            "correct_answer": {
                "alternative_text": "`STREAM`",
                "explanation": "Resposta certa.",
            },
            "wrong_answers": [
                {
                    "alternative_text": "`BATCH`",
                    "explanation": "Resposta errada.",
                }
            ],
            "subject": "Databricks",
            "topic": "streaming",
            "difficulty": "easy",
            "source": "seed_v1",
            "cohort_key": "certificacao",
            "is_active": True,
            "created_at_utc": "2026-04-09T15:00:00+00:00",
            "updated_at_utc": "2026-04-09T15:00:00+00:00",
        }
    ]


def test_load_seed_batches_rejects_duplicate_question_ids_across_files() -> None:
    root = Path("trash") / f"seed-apply-{uuid4().hex}"
    input_dir = root / "source"
    input_dir.mkdir(parents=True, exist_ok=True)

    seed_payload = {
        "table_id": "project.dataset.question_bank",
        "defaults": {
            "subject": "Databricks",
            "topic": "streaming",
            "source": "seed_v1",
            "cohort_key": "certificacao",
            "is_active": True,
        },
        "questions": [
            {
                "id_question": 6200,
                "statement": "Pergunta",
                "difficulty": "easy",
                "correct_answer": {
                    "alternative_text": "`STREAM`",
                    "explanation": None,
                },
                "wrong_answers": [
                    {
                        "alternative_text": "`BATCH`",
                        "explanation": None,
                    }
                ],
            }
        ],
    }

    try:
        (input_dir / "a.json").write_text(json.dumps(seed_payload), encoding="utf-8")
        (input_dir / "b.json").write_text(json.dumps(seed_payload), encoding="utf-8")

        with pytest.raises(ValueError, match="Duplicate id_question across seed batches"):
            load_seed_batches(input_dir)
    finally:
        shutil.rmtree(root, ignore_errors=True)
