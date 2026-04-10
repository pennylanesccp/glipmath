from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.config.settings import load_settings
from modules.storage.bigquery_client import BigQueryClient

DEFAULT_SQL_PATH = Path("sql/maintenance/normalize_question_taxonomy.sql")
TABLE_PLACEHOLDER = "{{QUESTION_TABLE_ID}}"


def render_normalization_sql(*, sql_path: Path, table_id: str) -> str:
    """Load the normalization SQL template and resolve the question-bank table."""

    try:
        sql_template = sql_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Normalization SQL not found: {sql_path}") from exc

    if TABLE_PLACEHOLDER not in sql_template:
        raise ValueError(
            f"Normalization SQL is missing the {TABLE_PLACEHOLDER} placeholder."
        )

    return sql_template.replace(TABLE_PLACEHOLDER, table_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize subject/topic taxonomy values inside the BigQuery question bank.",
    )
    parser.add_argument(
        "--sql-path",
        type=Path,
        default=DEFAULT_SQL_PATH,
        help=f"Path to the normalization SQL template. Defaults to {DEFAULT_SQL_PATH.as_posix()}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render the SQL and print it instead of executing it.",
    )
    args = parser.parse_args()

    settings = load_settings(base_dir=REPO_ROOT)
    question_table_id = settings.bigquery.question_bank_table_id(settings.gcp.project_id)
    sql = render_normalization_sql(
        sql_path=REPO_ROOT / args.sql_path,
        table_id=question_table_id,
    )

    if args.dry_run:
        print(sql)
        return

    bigquery_client = BigQueryClient(
        project_id=settings.gcp.project_id,
        location=settings.gcp.location,
        service_account_info=settings.service_account_info,
    )
    bigquery_client.execute(sql)
    print(f"Normalized question taxonomy fields in {question_table_id}.")


if __name__ == "__main__":
    main()
