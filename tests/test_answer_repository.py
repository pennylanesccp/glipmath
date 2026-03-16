import pandas as pd

from modules.storage.answer_repository import AnswerRepository


class FakeBigQueryClient:
    def __init__(self, columns: tuple[str, ...]) -> None:
        self.columns = columns
        self.queries: list[str] = []
        self.insert_calls: list[tuple[str, list[dict[str, object]]]] = []

    def get_table_column_names(self, table_id: str) -> tuple[str, ...]:
        return self.columns

    def query_to_dataframe(self, sql: str, *, parameters=None) -> pd.DataFrame:
        self.queries.append(sql)
        return pd.DataFrame()

    def insert_rows_json(self, table_id: str, rows: list[dict[str, object]]) -> None:
        self.insert_calls.append((table_id, rows))


def test_load_user_frame_falls_back_for_missing_optional_columns() -> None:
    fake_client = FakeBigQueryClient(
        (
            "id_answer",
            "id_question",
            "user_email",
            "selected_alternative_text",
            "correct_alternative_text",
            "is_correct",
            "answered_at_utc",
            "answered_at_local",
            "time_spent_seconds",
            "session_id",
            "topic",
            "difficulty",
            "source",
            "app_version",
        )
    )
    repository = AnswerRepository(
        fake_client,
        answers_table_id="project.dataset.answers",
        leaderboard_view_id="project.dataset.v_leaderboard",
    )

    repository.load_user_frame("ana@example.com")

    assert fake_client.queries
    assert "CAST(NULL AS STRING) AS subject" in fake_client.queries[0]
    assert "\n                topic" in fake_client.queries[0]


def test_append_answer_row_filters_unknown_columns_for_older_table_schema() -> None:
    fake_client = FakeBigQueryClient(
        (
            "id_answer",
            "id_question",
            "user_email",
            "selected_alternative_text",
            "correct_alternative_text",
            "is_correct",
            "answered_at_utc",
            "answered_at_local",
            "time_spent_seconds",
            "session_id",
        )
    )
    repository = AnswerRepository(
        fake_client,
        answers_table_id="project.dataset.answers",
        leaderboard_view_id="project.dataset.v_leaderboard",
    )

    repository.append_answer_row(
        {
            "id_answer": "a1",
            "id_question": 1,
            "user_email": "ana@example.com",
            "selected_alternative_text": "3",
            "correct_alternative_text": "4",
            "is_correct": False,
            "answered_at_utc": "2026-03-16T12:00:00Z",
            "answered_at_local": "2026-03-16 09:00:00",
            "time_spent_seconds": 4.0,
            "session_id": "session-1",
            "subject": "matematica",
        }
    )

    _, rows = fake_client.insert_calls[0]
    assert rows == [
        {
            "id_answer": "a1",
            "id_question": 1,
            "user_email": "ana@example.com",
            "selected_alternative_text": "3",
            "correct_alternative_text": "4",
            "is_correct": False,
            "answered_at_utc": "2026-03-16T12:00:00Z",
            "answered_at_local": "2026-03-16 09:00:00",
            "time_spent_seconds": 4.0,
            "session_id": "session-1",
        }
    ]
