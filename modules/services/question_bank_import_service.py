from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from modules.storage.schema_validation import prepare_dataframe, require_columns, worksheet_row_number
from modules.utils.normalization import clean_optional_text, coerce_bool

SUPPORTED_QUESTION_FILE_SUFFIXES = {".csv", ".jsonl"}
RAW_VESTIBULINHO_REQUIRED_COLUMNS = [
    "question_number",
    "statement",
    "question_a",
    "question_b",
    "question_c",
    "question_d",
    "source",
    "answer",
]
ALTERNATIVE_COLUMN_BY_LABEL = {
    "A": "question_a",
    "B": "question_b",
    "C": "question_c",
    "D": "question_d",
    "E": "question_e",
}


def load_question_bank_rows(input_path: Path) -> list[dict[str, Any]]:
    """Load canonical question-bank rows from a directory, CSV file, or JSONL file."""

    if not input_path.exists():
        raise FileNotFoundError(f"Question input path not found: {input_path}")

    if input_path.is_dir():
        files = sorted(
            path
            for path in input_path.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_QUESTION_FILE_SUFFIXES
        )
        if not files:
            raise ValueError(f"No supported question files found under '{input_path}'.")

        rows: list[dict[str, Any]] = []
        for file_path in files:
            rows.extend(load_question_bank_rows(file_path))
        return rows

    suffix = input_path.suffix.lower()
    if suffix == ".jsonl":
        return _read_jsonl_rows(input_path)
    if suffix == ".csv":
        return _load_vestibulinho_csv_rows(input_path)
    raise ValueError(f"Unsupported question input file type: {input_path.suffix}")


def build_question_row_from_vestibulinho_row(
    row: dict[str, object],
    *,
    default_source: str | None = None,
) -> dict[str, Any]:
    """Convert one vestibulinho CSV row into the canonical nested BigQuery row shape."""

    question_number = _parse_positive_int(row.get("question_number"), "question_number")
    statement = _parse_required_text(row.get("statement"), "statement")
    source = clean_optional_text(row.get("source")) or clean_optional_text(default_source)
    if not source:
        raise ValueError("source cannot be blank.")

    answer_label = _parse_answer_label(row.get("answer"))
    alternatives = _extract_alternatives(row)
    if len(alternatives) < 2:
        raise ValueError("at least two alternatives must be present.")
    if answer_label not in alternatives:
        raise ValueError("answer must reference a populated alternative.")

    correct_alternative = alternatives[answer_label]
    wrong_alternatives = [
        alternative
        for label, alternative in alternatives.items()
        if label != answer_label
    ]

    return {
        "id_question": generate_question_id(source=source, question_number=question_number),
        "statement": statement,
        "correct_answer": correct_alternative,
        "wrong_answers": wrong_alternatives,
        "topic": clean_optional_text(row.get("topic")),
        "difficulty": clean_optional_text(row.get("difficulty")),
        "source": source,
        "is_active": coerce_bool(row.get("is_active"), default=True),
        "created_at_utc": clean_optional_text(row.get("created_at_utc")),
        "updated_at_utc": clean_optional_text(row.get("updated_at_utc")),
    }


def generate_question_id(*, source: str, question_number: int) -> int:
    """Generate a stable positive INT64-compatible question ID."""

    normalized_source = " ".join(source.strip().lower().split())
    payload = f"{normalized_source}:{question_number}"
    digest = hashlib.sha1(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


def _load_vestibulinho_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    dataframe = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    prepared = prepare_dataframe(dataframe)
    require_columns(prepared, RAW_VESTIBULINHO_REQUIRED_COLUMNS, csv_path.name)

    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    for index, row in prepared.iterrows():
        row_number = worksheet_row_number(index)
        try:
            rows.append(
                build_question_row_from_vestibulinho_row(
                    row.to_dict(),
                    default_source=csv_path.stem,
                )
            )
        except ValueError as exc:
            issues.append(f"{csv_path.name} row {row_number}: {exc}")

    if issues:
        raise ValueError("\n".join(issues))
    return rows


def _read_jsonl_rows(jsonl_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of '{jsonl_path}'."
                ) from exc
            if not isinstance(parsed, dict):
                raise ValueError(
                    f"Expected a JSON object on line {line_number} of '{jsonl_path}'."
                )
            rows.append(parsed)
    return rows


def _extract_alternatives(row: dict[str, object]) -> dict[str, dict[str, Any]]:
    alternatives: dict[str, dict[str, Any]] = {}
    for label, column_name in ALTERNATIVE_COLUMN_BY_LABEL.items():
        alternative_text = clean_optional_text(row.get(column_name))
        if not alternative_text:
            continue

        explanation = clean_optional_text(row.get(f"{column_name}_explanation"))
        alternatives[label] = {
            "alternative_text": alternative_text,
            "explanation": explanation,
        }
    return alternatives


def _parse_positive_int(value: object, field_name: str) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid integer.") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return parsed


def _parse_required_text(value: object, field_name: str) -> str:
    text = clean_optional_text(value)
    if not text:
        raise ValueError(f"{field_name} cannot be blank.")
    return text


def _parse_answer_label(value: object) -> str:
    label = clean_optional_text(value)
    if not label:
        raise ValueError("answer cannot be blank.")
    normalized = label.upper()
    if normalized not in ALTERNATIVE_COLUMN_BY_LABEL:
        raise ValueError("answer must be one of A, B, C, D, or E.")
    return normalized
