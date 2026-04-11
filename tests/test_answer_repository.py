import pandas as pd

from modules.storage.answer_repository import AnswerRepository


class FakeBigQueryClient:
    def __init__(self, columns: tuple[str, ...]) -> None:
        self.columns = columns
        self.queries: list[str] = []
        self.parameters: list[object] = []
        self.insert_calls: list[tuple[str, list[dict[str, object]]]] = []

    def get_table_column_names(self, table_id: str) -> tuple[str, ...]:
        return self.columns

    def query_to_dataframe(self, sql: str, *, parameters=None) -> pd.DataFrame:
        self.queries.append(sql)
        self.parameters.append(parameters)
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
        user_access_table_id="project.dataset.user_access",
    )

    repository.load_user_frame("ana@example.com")

    assert fake_client.queries
    assert "CAST(NULL AS STRING) AS subject" in fake_client.queries[0]
    assert "CAST(NULL AS STRING) AS cohort_key" in fake_client.queries[0]
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
        user_access_table_id="project.dataset.user_access",
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
            "cohort_key": "ano_1",
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


def test_load_leaderboard_frame_scopes_students_to_one_cohort() -> None:
    fake_client = FakeBigQueryClient(tuple())
    repository = AnswerRepository(
        fake_client,
        answers_table_id="project.dataset.answers",
        user_access_table_id="project.dataset.user_access",
    )

    repository.load_leaderboard_frame(role="student", cohort_key="ano_2")

    assert "FROM `project.dataset.user_access`" in fake_client.queries[0]
    assert "LOWER(TRIM(answers.cohort_key)) = @cohort_key" in fake_client.queries[0]
    assert "access.role = 'student'" in fake_client.queries[0]
    parameters = fake_client.parameters[0]
    assert parameters is not None
    assert parameters[0].name == "cohort_key"
    assert parameters[0].to_api_repr()["parameterValue"]["value"] == "ano_2"


def test_load_leaderboard_frame_keeps_teacher_view_global() -> None:
    fake_client = FakeBigQueryClient(tuple())
    repository = AnswerRepository(
        fake_client,
        answers_table_id="project.dataset.answers",
        user_access_table_id="project.dataset.user_access",
    )

    repository.load_leaderboard_frame(role="teacher")

    assert "LOWER(TRIM(answers.cohort_key)) = @cohort_key" not in fake_client.queries[0]
    assert fake_client.parameters[0] is None


def test_load_user_leaderboard_position_frame_queries_only_one_user_rank() -> None:
    fake_client = FakeBigQueryClient(tuple())
    repository = AnswerRepository(
        fake_client,
        answers_table_id="project.dataset.answers",
        user_access_table_id="project.dataset.user_access",
    )

    repository.load_user_leaderboard_position_frame(
        user_email="Ana@example.com",
        role="teacher",
    )

    assert "LEFT JOIN ranked" in fake_client.queries[0]
    assert "totals.total_users" in fake_client.queries[0]
    parameters = fake_client.parameters[0]
    assert parameters is not None
    assert parameters[0].name == "user_email"
    assert parameters[0].to_api_repr()["parameterValue"]["value"] == "ana@example.com"


def test_load_user_leaderboard_position_frame_scopes_students_to_one_cohort() -> None:
    fake_client = FakeBigQueryClient(tuple())
    repository = AnswerRepository(
        fake_client,
        answers_table_id="project.dataset.answers",
        user_access_table_id="project.dataset.user_access",
    )

    repository.load_user_leaderboard_position_frame(
        user_email="ana@example.com",
        role="student",
        cohort_key="ano_2",
    )

    assert "LOWER(TRIM(answers.cohort_key)) = @cohort_key" in fake_client.queries[0]
    parameters = fake_client.parameters[0]
    assert parameters is not None
    assert [parameter.name for parameter in parameters] == ["user_email", "cohort_key"]


def test_load_user_progress_snapshot_frame_requests_compact_progress_fields() -> None:
    fake_client = FakeBigQueryClient(tuple())
    repository = AnswerRepository(
        fake_client,
        answers_table_id="project.dataset.answers",
        user_access_table_id="project.dataset.user_access",
    )

    repository.load_user_progress_snapshot_frame(
        user_email=" Ana@example.com ",
        timezone_name="America/Sao_Paulo",
    )

    assert "ARRAY(" in fake_client.queries[0]
    assert "AS answered_question_ids" in fake_client.queries[0]
    assert "AS activity_dates" in fake_client.queries[0]
    assert "AS question_streak" in fake_client.queries[0]
    parameters = fake_client.parameters[0]
    assert parameters is not None
    assert [parameter.name for parameter in parameters] == ["user_email", "timezone_name"]
    assert parameters[0].to_api_repr()["parameterValue"]["value"] == "ana@example.com"
    assert parameters[1].to_api_repr()["parameterValue"]["value"] == "America/Sao_Paulo"
