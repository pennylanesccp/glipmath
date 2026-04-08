from pathlib import Path
from uuid import uuid4

import pytest

from scripts.render_question_seed_sql import load_seed_payload, render_seed_sql


def test_render_seed_sql_uses_defaults_and_nested_structs() -> None:
    sql = render_seed_sql(
        {
            "table_id": "project.dataset.question_bank",
            "delete": {
                "source": "seed_v1",
                "cohort_key": "ano_1",
            },
            "defaults": {
                "subject": "Matematica",
                "topic": "divisao",
                "source": "seed_v1",
                "cohort_key": "ano_1",
                "is_active": True,
            },
            "questions": [
                {
                    "id_question": 3001,
                    "statement": "Quanto e 12 dividido por 3?",
                    "difficulty": "facil",
                    "correct_answer": {
                        "alternative_text": "4",
                        "explanation": "12 dividido por 3 e igual a 4.",
                    },
                    "wrong_answers": [
                        {
                            "alternative_text": "3",
                            "explanation": "3 x 3 = 9.",
                        },
                        {
                            "alternative_text": "5",
                            "explanation": "5 x 3 = 15.",
                        },
                    ],
                }
            ],
        },
        source_path=Path("local/bq_seeds/divisao.json"),
    )

    assert "-- Generated from local/bq_seeds/divisao.json." in sql
    assert "DELETE FROM `project.dataset.question_bank`" in sql
    assert "source = 'seed_v1'" in sql
    assert "STRUCT(" in sql
    assert "AS correct_answer" in sql
    assert "AS wrong_answers" in sql
    assert "CURRENT_TIMESTAMP() AS created_at_utc" in sql
    assert "CURRENT_TIMESTAMP() AS updated_at_utc" in sql


def test_render_seed_sql_allows_table_id_override() -> None:
    sql = render_seed_sql(
        {
            "table_id": "project.dataset.question_bank",
            "defaults": {
                "subject": "Matematica",
                "topic": "divisao",
                "source": "seed_v1",
                "cohort_key": "ano_1",
                "is_active": True,
            },
            "questions": [
                {
                    "id_question": 1,
                    "statement": "Pergunta",
                    "difficulty": "facil",
                    "correct_answer": {
                        "alternative_text": "1",
                        "explanation": None,
                    },
                    "wrong_answers": [
                        {
                            "alternative_text": "2",
                            "explanation": None,
                        }
                    ],
                }
            ],
        },
        table_id_override="override.dataset.question_bank",
    )

    assert "INSERT INTO `override.dataset.question_bank`" in sql
    assert "INSERT INTO `project.dataset.question_bank`" not in sql


def test_load_seed_payload_rejects_invalid_json() -> None:
    input_path = Path("trash") / f"invalid-seed-{uuid4().hex}.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text("{ invalid", encoding="utf-8")

    try:
        with pytest.raises(ValueError, match="Seed JSON is invalid"):
            load_seed_payload(input_path)
    finally:
        input_path.unlink(missing_ok=True)
