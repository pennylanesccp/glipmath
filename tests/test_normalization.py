from pathlib import Path

import pytest

from modules.utils.normalization import normalize_taxonomy_value
from scripts.normalize_question_taxonomy import render_normalization_sql


def test_normalize_taxonomy_value_canonicalizes_accents_spacing_and_case() -> None:
    assert normalize_taxonomy_value(" Matemática ") == "matematica"
    assert normalize_taxonomy_value("RADICIAÇÃO") == "radiciacao"
    assert normalize_taxonomy_value("auto_loader") == "auto loader"
    assert normalize_taxonomy_value("delta-sharing") == "delta sharing"


def test_render_normalization_sql_replaces_table_placeholder() -> None:
    sql = render_normalization_sql(
        sql_path=Path("sql/maintenance/normalize_question_taxonomy.sql"),
        table_id="project.dataset.question_bank",
    )

    assert "{{QUESTION_TABLE_ID}}" not in sql
    assert "UPDATE `project.dataset.question_bank`" in sql


def test_render_normalization_sql_requires_placeholder() -> None:
    bogus_sql_path = Path("trash/test-normalization-missing-placeholder.sql")
    bogus_sql_path.parent.mkdir(parents=True, exist_ok=True)
    bogus_sql_path.write_text("SELECT 1;", encoding="utf-8")

    try:
        with pytest.raises(ValueError, match="missing the \\{\\{QUESTION_TABLE_ID\\}\\} placeholder"):
            render_normalization_sql(
                sql_path=bogus_sql_path,
                table_id="project.dataset.question_bank",
            )
    finally:
        bogus_sql_path.unlink(missing_ok=True)
