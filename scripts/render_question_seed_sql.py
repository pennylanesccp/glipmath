from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.services.difficulty_service import require_difficulty_value
from modules.utils.normalization import normalize_taxonomy_value
from scripts.question_seed_ids import resolve_seed_question_id

DEFAULT_INPUT_DIR = Path("local/bq_seeds/source")
DEFAULT_OUTPUT_DIR = Path("local/bq_seeds/sql")


def load_seed_payload(input_path: Path) -> dict[str, Any]:
    """Load one JSON seed payload from disk."""

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Seed JSON not found: {input_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Seed JSON is invalid: {input_path}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Seed JSON root must be an object.")
    return payload


def render_seed_sql(
    payload: Mapping[str, Any],
    *,
    source_path: Path | None = None,
    table_id_override: str | None = None,
) -> str:
    """Render a BigQuery DELETE + INSERT seed statement from one JSON payload."""

    table_id = _require_string(table_id_override or payload.get("table_id"), "table_id")
    delete_scope = _require_mapping(payload.get("delete") or {}, "delete")
    defaults = _require_mapping(payload.get("defaults") or {}, "defaults")
    questions_raw = payload.get("questions")
    if not isinstance(questions_raw, list) or not questions_raw:
        raise ValueError("questions must be a non-empty array.")

    rendered_selects = []
    seen_question_ids: set[int] = set()
    for index, question_raw in enumerate(questions_raw, start=1):
        question = _require_mapping(question_raw, f"questions[{index - 1}]")
        merged_question = dict(defaults)
        merged_question.update(question)
        id_question = resolve_seed_question_id(
            merged_question.get("id_question"),
            field_name=f"questions[{index - 1}].id_question",
            seen_question_ids=seen_question_ids,
        )
        merged_question["id_question"] = id_question
        rendered_selects.append(_render_question_select(merged_question, row_label=f"questions[{index - 1}]"))

    delete_lines = []
    if delete_scope:
        delete_lines.extend(
            [
                f"DELETE FROM `{table_id}`",
                "WHERE " + "\n  AND ".join(
                    f"{column_name} = {_sql_literal(value)}"
                    for column_name, value in delete_scope.items()
                )
                + ";",
                "",
            ]
        )

    header_lines = []
    if source_path is not None:
        header_lines.append(f"-- Generated from {source_path.as_posix()}.")

    return "\n".join(
        [
            *header_lines,
            *delete_lines,
            f"INSERT INTO `{table_id}`",
            "(",
            "  id_question,",
            "  statement,",
            "  correct_answer,",
            "  wrong_answers,",
            "  subject,",
            "  topic,",
            "  difficulty,",
            "  source,",
            "  cohort_key,",
            "  is_active,",
            "  created_at_utc,",
            "  updated_at_utc",
            ")",
            "WITH source_rows AS (",
            _join_union_all(rendered_selects),
            ")",
            "SELECT",
            "  id_question,",
            "  statement,",
            "  correct_answer,",
            "  wrong_answers,",
            "  subject,",
            "  topic,",
            "  difficulty,",
            "  source,",
            "  cohort_key,",
            "  is_active,",
            "  CURRENT_TIMESTAMP() AS created_at_utc,",
            "  CURRENT_TIMESTAMP() AS updated_at_utc",
            "FROM source_rows;",
        ]
    ).strip() + "\n"


def write_seed_sql(
    payload: Mapping[str, Any],
    *,
    input_path: Path,
    output_path: Path,
    table_id_override: str | None = None,
) -> None:
    """Render and write one SQL seed file to disk."""

    sql = render_seed_sql(
        payload,
        source_path=input_path,
        table_id_override=table_id_override,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(sql, encoding="utf-8")


def render_seed_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    table_id_override: str | None = None,
) -> list[Path]:
    """Render one SQL file per JSON payload under the input directory."""

    if not input_dir.exists():
        raise ValueError(f"Seed JSON directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise ValueError(f"Seed JSON input must be a directory: {input_dir}")

    input_paths = sorted(
        path
        for path in input_dir.rglob("*.json")
        if path.is_file()
    )
    if not input_paths:
        raise ValueError(f"No seed JSON files were found under: {input_dir}")

    output_paths: list[Path] = []
    for input_path in input_paths:
        payload = load_seed_payload(input_path)
        output_path = output_dir / input_path.relative_to(input_dir).with_suffix(".sql")
        write_seed_sql(
            payload,
            input_path=input_path,
            output_path=output_path,
            table_id_override=table_id_override,
        )
        output_paths.append(output_path)
    return output_paths


def _render_question_select(question: Mapping[str, Any], *, row_label: str) -> str:
    correct_answer = _require_mapping(question.get("correct_answer"), f"{row_label}.correct_answer")
    wrong_answers_raw = question.get("wrong_answers")
    if not isinstance(wrong_answers_raw, list) or not wrong_answers_raw:
        raise ValueError(f"{row_label}.wrong_answers must be a non-empty array.")

    wrong_answers = [
        _render_alternative_struct(
            _require_mapping(wrong_answer, f"{row_label}.wrong_answers[{index}]"),
            field_name=f"{row_label}.wrong_answers[{index}]",
            indent="      ",
        )
        for index, wrong_answer in enumerate(wrong_answers_raw)
    ]

    return "\n".join(
        [
            "  SELECT",
            f"    {int(question['id_question'])} AS id_question,",
            f"    {_sql_literal(_require_string(question.get('statement'), f'{row_label}.statement'))} AS statement,",
            "    STRUCT(",
            _render_alternative_fields(correct_answer, field_name=f"{row_label}.correct_answer", indent="      "),
            "    ) AS correct_answer,",
            "    [",
            ",\n".join(wrong_answers),
            "    ] AS wrong_answers,",
            f"    {_sql_literal(_require_taxonomy_string(question.get('subject'), f'{row_label}.subject'))} AS subject,",
            f"    {_sql_literal(_require_taxonomy_string(question.get('topic'), f'{row_label}.topic'))} AS topic,",
            f"    {require_difficulty_value(question.get('difficulty'), f'{row_label}.difficulty')} AS difficulty,",
            f"    {_sql_literal(_require_string(question.get('source'), f'{row_label}.source'))} AS source,",
            f"    {_sql_literal(_require_string(question.get('cohort_key'), f'{row_label}.cohort_key'))} AS cohort_key,",
            f"    {_sql_bool(_require_bool(question.get('is_active'), f'{row_label}.is_active'))} AS is_active",
        ]
    )


def _render_alternative_struct(
    alternative: Mapping[str, Any],
    *,
    field_name: str,
    indent: str,
) -> str:
    return "\n".join(
        [
            f"{indent}STRUCT(",
            _render_alternative_fields(alternative, field_name=field_name, indent=indent + "  "),
            f"{indent})",
        ]
    )


def _render_alternative_fields(
    alternative: Mapping[str, Any],
    *,
    field_name: str,
    indent: str,
) -> str:
    return "\n".join(
        [
            f"{indent}{_sql_literal(_require_string(alternative.get('alternative_text'), f'{field_name}.alternative_text'))} AS alternative_text,",
            f"{indent}{_sql_literal(_optional_string(alternative.get('explanation')))} AS explanation",
        ]
    )


def _join_union_all(rendered_selects: list[str]) -> str:
    return "\n  UNION ALL\n".join(rendered_selects)


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return _sql_bool(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _sql_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object.")
    return value


def _require_string(value: Any, field_name: str) -> str:
    text = _optional_string(value)
    if text is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return text


def _require_taxonomy_string(value: Any, field_name: str) -> str:
    text = normalize_taxonomy_value(value)
    if text is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return text


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _require_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be a boolean.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render BigQuery seed SQL files from local JSON payloads.",
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input-json",
        type=Path,
        help="Path to one local JSON seed payload.",
    )
    input_group.add_argument(
        "--input-dir",
        type=Path,
        help=f"Path to a directory of JSON payloads. Defaults to {DEFAULT_INPUT_DIR.as_posix()}.",
    )
    parser.add_argument(
        "--output-sql",
        type=Path,
        help="Optional output path for one generated SQL file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=f"Optional output directory for generated SQL files. Defaults to {DEFAULT_OUTPUT_DIR.as_posix()}.",
    )
    parser.add_argument(
        "--table-id",
        help="Optional override for payload.table_id.",
    )
    args = parser.parse_args()

    if args.input_json is not None:
        payload = load_seed_payload(args.input_json)
        if args.output_dir is not None and args.output_sql is not None:
            raise ValueError("Use only one of --output-sql or --output-dir in file mode.")

        output_sql = args.output_sql or _resolve_output_sql_path(
            input_json=args.input_json,
            output_dir=args.output_dir or DEFAULT_OUTPUT_DIR,
        )
        write_seed_sql(
            payload,
            input_path=args.input_json,
            output_path=output_sql,
            table_id_override=args.table_id,
        )
        print(f"Generated SQL seed: {output_sql}")
        return

    if args.output_sql is not None:
        raise ValueError("--output-sql is only valid together with --input-json.")

    input_dir = args.input_dir or DEFAULT_INPUT_DIR
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR
    output_paths = render_seed_directory(
        input_dir,
        output_dir,
        table_id_override=args.table_id,
    )
    for output_path in output_paths:
        print(f"Generated SQL seed: {output_path}")


def _resolve_output_sql_path(*, input_json: Path, output_dir: Path) -> Path:
    if input_json.is_relative_to(DEFAULT_INPUT_DIR):
        relative_path = input_json.relative_to(DEFAULT_INPUT_DIR).with_suffix(".sql")
        return output_dir / relative_path
    return output_dir / input_json.with_suffix(".sql").name


if __name__ == "__main__":
    main()
