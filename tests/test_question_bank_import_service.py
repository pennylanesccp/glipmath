import csv
import json

from modules.services.question_bank_import_service import (
    build_question_row_from_vestibulinho_row,
    generate_question_id,
    load_question_bank_import_rows,
    load_question_bank_rows,
    reconcile_staged_question_files,
    write_question_import_failures_csv,
)


def test_build_question_row_from_vestibulinho_row_maps_correct_and_wrong_answers() -> None:
    row = build_question_row_from_vestibulinho_row(
        {
            "question_number": "7",
            "statement": "Quanto e 2 + 2?",
            "question_a": "3",
            "question_b": "4",
            "question_c": "5",
            "question_d": "6",
            "question_e": "",
            "subject": "matematica",
            "source": "Vestibulinho 1SEM2026",
            "answer": "B",
        }
    )

    assert row["statement"] == "Quanto e 2 + 2?"
    assert row["correct_answer"]["alternative_text"] == "4"
    assert [item["alternative_text"] for item in row["wrong_answers"]] == ["3", "5", "6"]
    assert row["subject"] == "matematica"
    assert row["source"] == "Vestibulinho 1SEM2026"
    assert row["is_active"] is True


def test_generate_question_id_is_stable_for_source_and_number() -> None:
    first = generate_question_id(source="Vestibulinho 1SEM2026", question_number=7)
    second = generate_question_id(source="Vestibulinho 1SEM2026", question_number=7)
    third = generate_question_id(source="Vestibulinho 2SEM2026", question_number=7)

    assert first == second
    assert first != third
    assert first > 0


def test_load_question_bank_rows_from_directory_supports_csv_and_jsonl(tmp_path) -> None:
    csv_path = tmp_path / "vestibulinho_questions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "question_number",
                "statement",
                "question_a",
                "question_b",
                "question_c",
                "question_d",
                "question_e",
                "subject",
                "source",
                "answer",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "question_number": "1",
                "statement": "Quanto e 1 + 1?",
                "question_a": "1",
                "question_b": "2",
                "question_c": "3",
                "question_d": "4",
                "question_e": "",
                "subject": "matematica",
                "source": "Vestibulinho 1SEM2025",
                "answer": "B",
            }
        )

    jsonl_path = tmp_path / "bonus_questions.jsonl"
    jsonl_path.write_text(
        json.dumps(
            {
                "id_question": 999,
                "statement": "Quanto e 3 + 3?",
                "correct_answer": {"alternative_text": "6", "explanation": None},
                "wrong_answers": [{"alternative_text": "5", "explanation": None}],
                "subject": "ciencias",
                "topic": None,
                "difficulty": None,
                "source": "jsonl",
                "is_active": True,
                "created_at_utc": None,
                "updated_at_utc": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_question_bank_rows(tmp_path)

    assert len(rows) == 2
    assert any(
        row["statement"] == "Quanto e 1 + 1?" and row["subject"] == "matematica"
        for row in rows
    )
    assert any(row["id_question"] == 999 and row["subject"] == "ciencias" for row in rows)


def test_load_question_bank_import_rows_collects_invalid_csv_rows(tmp_path) -> None:
    csv_path = tmp_path / "vestibulinho_questions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "question_number",
                "statement",
                "question_a",
                "question_b",
                "question_c",
                "question_d",
                "question_e",
                "source",
                "answer",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "question_number": "1",
                "statement": "Quanto e 1 + 1?",
                "question_a": "1",
                "question_b": "2",
                "question_c": "3",
                "question_d": "4",
                "question_e": "",
                "source": "Vestibulinho 1SEM2025",
                "answer": "B",
            }
        )
        writer.writerow(
            {
                "question_number": "2",
                "statement": "",
                "question_a": "1",
                "question_b": "",
                "question_c": "",
                "question_d": "",
                "question_e": "",
                "source": "Vestibulinho 1SEM2025",
                "answer": "A",
            }
        )

    imported_rows, failures = load_question_bank_import_rows(csv_path)

    assert len(imported_rows) == 1
    assert len(failures) == 1
    assert failures[0].source_file == "vestibulinho_questions.csv"
    assert failures[0].row_number == 3
    assert failures[0].error == "statement cannot be blank."


def test_write_question_import_failures_csv_persists_raw_row_context(tmp_path) -> None:
    csv_path = tmp_path / "vestibulinho_questions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "question_number",
                "statement",
                "question_a",
                "question_b",
                "question_c",
                "question_d",
                "question_e",
                "source",
                "answer",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "question_number": "2",
                "statement": "",
                "question_a": "1",
                "question_b": "",
                "question_c": "",
                "question_d": "",
                "question_e": "",
                "source": "Vestibulinho 1SEM2025",
                "answer": "A",
            }
        )

    _, failures = load_question_bank_import_rows(csv_path)
    output_path = tmp_path / "failed_rows.csv"

    write_question_import_failures_csv(failures, output_path)

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["source_file"] == "vestibulinho_questions.csv"
    assert rows[0]["row_number"] == "2"
    assert rows[0]["error"] == "statement cannot be blank."
    assert rows[0]["question_number"] == "2"


def test_load_question_bank_rows_ignores_generated_failed_rows_reports(tmp_path) -> None:
    csv_path = tmp_path / "vestibulinho_questions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "question_number",
                "statement",
                "question_a",
                "question_b",
                "question_c",
                "question_d",
                "question_e",
                "source",
                "answer",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "question_number": "1",
                "statement": "Quanto e 1 + 1?",
                "question_a": "1",
                "question_b": "2",
                "question_c": "3",
                "question_d": "4",
                "question_e": "",
                "source": "Vestibulinho 1SEM2025",
                "answer": "B",
            }
        )

    failed_report_path = tmp_path / "question_bank_failed_rows.csv"
    failed_report_path.write_text(
        "source_file,row_number,error\nvestibulinho_questions.csv,3,statement cannot be blank.\n",
        encoding="utf-8",
    )

    rows = load_question_bank_rows(tmp_path)

    assert len(rows) == 1
    assert rows[0]["statement"] == "Quanto e 1 + 1?"


def test_reconcile_staged_question_files_keeps_failures_in_new_and_moves_valid_rows(tmp_path) -> None:
    new_root = tmp_path / "new"
    processed_root = tmp_path / "processed"
    new_root.mkdir()
    processed_root.mkdir()

    source_path = new_root / "vestibulinho_questions.csv"
    with source_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "question_number",
                "statement",
                "question_a",
                "question_b",
                "question_c",
                "question_d",
                "question_e",
                "source",
                "answer",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "question_number": "1",
                "statement": "Quanto e 1 + 1?",
                "question_a": "1",
                "question_b": "2",
                "question_c": "3",
                "question_d": "4",
                "question_e": "",
                "source": "Vestibulinho 1SEM2025",
                "answer": "B",
            }
        )
        writer.writerow(
            {
                "question_number": "2",
                "statement": "",
                "question_a": "1",
                "question_b": "",
                "question_c": "",
                "question_d": "",
                "question_e": "",
                "source": "Vestibulinho 1SEM2025",
                "answer": "A",
            }
        )

    imported_rows, failures = load_question_bank_import_rows(source_path)

    reconcile_staged_question_files(
        processed_root=processed_root,
        new_root=new_root,
        imported_rows=imported_rows,
        failures=failures,
    )

    with (processed_root / "vestibulinho_questions.csv").open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        processed_rows = list(csv.DictReader(handle))
    with (new_root / "vestibulinho_questions.csv").open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        new_rows = list(csv.DictReader(handle))

    assert len(processed_rows) == 1
    assert processed_rows[0]["question_number"] == "1"
    assert len(new_rows) == 1
    assert new_rows[0]["question_number"] == "2"
