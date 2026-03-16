from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from modules.storage.schema_validation import prepare_dataframe, require_columns, worksheet_row_number
from modules.utils.normalization import clean_optional_text, coerce_bool

SUPPORTED_QUESTION_FILE_SUFFIXES = {".csv", ".jsonl"}
IGNORED_GENERATED_FILE_SUFFIXES = ("_failed_rows.csv",)
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


@dataclass(frozen=True, slots=True)
class ImportedQuestionRow:
    """One canonical question row plus the raw import context that produced it."""

    row: dict[str, Any]
    source_file: str
    source_path: Path
    row_number: int | None = None
    raw_row: dict[str, Any] | None = None
    raw_line: str | None = None


@dataclass(frozen=True, slots=True)
class QuestionImportFailure:
    """A question row that could not be imported safely."""

    source_file: str
    error: str
    source_path: Path
    row_number: int | None = None
    raw_row: dict[str, Any] | None = None
    raw_line: str | None = None


@dataclass(frozen=True, slots=True)
class StagedQuestionRoots:
    """Canonical staged raw-data roots."""

    new_root: Path
    processed_root: Path


def load_question_bank_rows(input_path: Path) -> list[dict[str, Any]]:
    """Load canonical question-bank rows from a directory, CSV file, or JSONL file."""

    imported_rows, failures = load_question_bank_import_rows(input_path)
    if failures:
        raise ValueError("\n".join(format_question_import_failure(failure) for failure in failures))
    return [item.row for item in imported_rows]


def load_question_bank_import_rows(
    input_path: Path,
) -> tuple[list[ImportedQuestionRow], list[QuestionImportFailure]]:
    """Load canonical question-bank rows and collect any row-level import failures."""

    if not input_path.exists():
        raise FileNotFoundError(f"Question input path not found: {input_path}")

    if input_path.is_dir():
        files = sorted(
            path
            for path in input_path.rglob("*")
            if path.is_file() and _is_supported_question_file(path)
        )
        if not files:
            raise ValueError(f"No supported question files found under '{input_path}'.")

        imported_rows: list[ImportedQuestionRow] = []
        failures: list[QuestionImportFailure] = []
        for file_path in files:
            file_rows, file_failures = load_question_bank_import_rows(file_path)
            imported_rows.extend(file_rows)
            failures.extend(file_failures)
        return imported_rows, failures

    suffix = input_path.suffix.lower()
    if suffix == ".jsonl":
        return _read_jsonl_rows(input_path)
    if suffix == ".csv":
        return _load_vestibulinho_csv_rows(input_path)
    raise ValueError(f"Unsupported question input file type: {input_path.suffix}")


def is_staged_question_root(input_path: Path) -> bool:
    """Return whether the path uses the `new/` and `processed/` staging layout."""

    return input_path.is_dir() and (input_path / "new").is_dir() and (input_path / "processed").is_dir()


def staged_question_roots(input_path: Path) -> StagedQuestionRoots:
    """Return the derived staged raw-data roots for a staged input directory."""

    return StagedQuestionRoots(
        new_root=input_path / "new",
        processed_root=input_path / "processed",
    )


def load_staged_question_bank_import_rows(
    input_path: Path,
) -> tuple[list[ImportedQuestionRow], list[QuestionImportFailure], StagedQuestionRoots]:
    """Load both staged folders while tolerating one side being temporarily empty."""

    roots = staged_question_roots(input_path)
    processed_rows, processed_failures = _load_optional_question_rows(roots.processed_root)
    new_rows, new_failures = _load_optional_question_rows(roots.new_root)
    combined_rows = [*processed_rows, *new_rows]
    combined_failures = [*processed_failures, *new_failures]
    if not combined_rows and not combined_failures:
        raise ValueError(f"No supported question files found under '{input_path}'.")
    return combined_rows, combined_failures, roots


def format_question_import_failure(failure: QuestionImportFailure) -> str:
    """Return a human-readable failure description."""

    location = failure.source_file
    if failure.row_number is not None:
        location = f"{location} row {failure.row_number}"
    return f"{location}: {failure.error}"


def write_question_import_failures_csv(
    failures: list[QuestionImportFailure],
    output_path: Path,
) -> None:
    """Write a CSV report with the failed raw rows and their error messages."""

    raw_columns = sorted(
        {
            key
            for failure in failures
            for key in (failure.raw_row or {}).keys()
        }
    )
    fieldnames = ["source_file", "row_number", "error", *raw_columns]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for failure in failures:
            row = {
                "source_file": failure.source_file,
                "row_number": failure.row_number or "",
                "error": failure.error,
            }
            for column in raw_columns:
                row[column] = _stringify_csv_value((failure.raw_row or {}).get(column, ""))
            writer.writerow(row)


def reconcile_staged_question_files(
    *,
    processed_root: Path,
    new_root: Path,
    imported_rows: Sequence[ImportedQuestionRow],
    failures: Sequence[QuestionImportFailure],
) -> None:
    """Rewrite staged raw files so valid rows live in processed and failures stay in new."""

    processed_root.mkdir(parents=True, exist_ok=True)
    new_root.mkdir(parents=True, exist_ok=True)

    relative_paths = {
        _resolve_relative_stage_path(item.source_path, processed_root, new_root)
        for item in imported_rows
    } | {
        _resolve_relative_stage_path(failure.source_path, processed_root, new_root)
        for failure in failures
    }

    for relative_path in sorted(relative_paths):
        processed_rows = [
            item
            for item in imported_rows
            if _resolve_relative_stage_path(item.source_path, processed_root, new_root)
            == relative_path
        ]
        failed_rows = [
            failure
            for failure in failures
            if _resolve_relative_stage_path(failure.source_path, processed_root, new_root)
            == relative_path
        ]

        _write_source_records(
            processed_root / relative_path,
            suffix=relative_path.suffix.lower(),
            rows=[_raw_record_from_imported_row(item) for item in processed_rows],
        )
        _write_source_records(
            new_root / relative_path,
            suffix=relative_path.suffix.lower(),
            rows=[_raw_record_from_failure(failure) for failure in failed_rows],
        )


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
        "subject": clean_optional_text(row.get("subject")),
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


def _load_vestibulinho_csv_rows(
    csv_path: Path,
) -> tuple[list[ImportedQuestionRow], list[QuestionImportFailure]]:
    dataframe = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    prepared = prepare_dataframe(dataframe)
    require_columns(prepared, RAW_VESTIBULINHO_REQUIRED_COLUMNS, csv_path.name)

    rows: list[ImportedQuestionRow] = []
    failures: list[QuestionImportFailure] = []
    for index, row in prepared.iterrows():
        row_number = worksheet_row_number(index)
        raw_row = row.to_dict()
        try:
            rows.append(
                ImportedQuestionRow(
                    row=build_question_row_from_vestibulinho_row(
                        raw_row,
                        default_source=csv_path.stem,
                    ),
                    source_file=csv_path.name,
                    source_path=csv_path,
                    row_number=row_number,
                    raw_row=raw_row,
                )
            )
        except ValueError as exc:
            failures.append(
                QuestionImportFailure(
                    source_file=csv_path.name,
                    source_path=csv_path,
                    row_number=row_number,
                    error=str(exc),
                    raw_row=raw_row,
                )
            )

    return rows, failures


def _read_jsonl_rows(
    jsonl_path: Path,
) -> tuple[list[ImportedQuestionRow], list[QuestionImportFailure]]:
    rows: list[ImportedQuestionRow] = []
    failures: list[QuestionImportFailure] = []
    with jsonl_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                failures.append(
                    QuestionImportFailure(
                        source_file=jsonl_path.name,
                        source_path=jsonl_path,
                        row_number=line_number,
                        error="invalid JSON object.",
                        raw_line=raw_line.rstrip("\r\n"),
                    )
                )
                continue
            if not isinstance(parsed, dict):
                failures.append(
                    QuestionImportFailure(
                        source_file=jsonl_path.name,
                        source_path=jsonl_path,
                        row_number=line_number,
                        error="expected a JSON object.",
                        raw_line=raw_line.rstrip("\r\n"),
                    )
                )
                continue
            rows.append(
                ImportedQuestionRow(
                    row=parsed,
                    source_file=jsonl_path.name,
                    source_path=jsonl_path,
                    row_number=line_number,
                    raw_row=parsed,
                    raw_line=raw_line.rstrip("\r\n"),
                )
            )
    return rows, failures


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


def _stringify_csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _is_supported_question_file(path: Path) -> bool:
    return (
        path.suffix.lower() in SUPPORTED_QUESTION_FILE_SUFFIXES
        and not path.name.lower().endswith(IGNORED_GENERATED_FILE_SUFFIXES)
    )


def _resolve_relative_stage_path(source_path: Path, processed_root: Path, new_root: Path) -> Path:
    try:
        return source_path.relative_to(processed_root)
    except ValueError:
        return source_path.relative_to(new_root)


def _raw_record_from_imported_row(item: ImportedQuestionRow) -> dict[str, Any] | str:
    if item.source_path.suffix.lower() == ".jsonl":
        return item.raw_line or json.dumps(item.raw_row or item.row, ensure_ascii=False)
    return dict(item.raw_row or {})


def _raw_record_from_failure(failure: QuestionImportFailure) -> dict[str, Any] | str:
    if failure.source_path.suffix.lower() == ".jsonl":
        if failure.raw_line is not None:
            return failure.raw_line
        return json.dumps(failure.raw_row or {}, ensure_ascii=False)
    return dict(failure.raw_row or {})


def _write_source_records(
    output_path: Path,
    *,
    suffix: str,
    rows: Sequence[dict[str, Any] | str],
) -> None:
    if not rows:
        if output_path.exists():
            output_path.unlink()
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".jsonl":
        with output_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                if isinstance(row, str):
                    handle.write(f"{row}\n")
                else:
                    handle.write(f"{json.dumps(row, ensure_ascii=False)}\n")
        return

    csv_rows = [row for row in rows if isinstance(row, dict)]
    fieldnames = _ordered_fieldnames(csv_rows)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _ordered_fieldnames(rows: Sequence[dict[str, Any]]) -> list[str]:
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def _load_optional_question_rows(
    input_path: Path,
) -> tuple[list[ImportedQuestionRow], list[QuestionImportFailure]]:
    try:
        return load_question_bank_import_rows(input_path)
    except ValueError as exc:
        if "No supported question files found under" in str(exc):
            return [], []
        raise
