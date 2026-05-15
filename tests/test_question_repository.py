import pandas as pd

from modules.storage.question_repository import QuestionRepository


class FakeBigQueryClient:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.parameters: list[object] = []
        self.inserted_rows: list[tuple[str, list[dict[str, object]]]] = []

    def query_to_dataframe(self, sql: str, *, parameters=None) -> pd.DataFrame:
        self.queries.append(sql)
        self.parameters.append(parameters)
        return pd.DataFrame()

    def execute(self, sql: str, *, parameters=None) -> None:
        raise AssertionError("execute should not be called in these tests")

    def get_table_column_names(self, table_id: str) -> tuple[str, ...]:
        return (
            "id_question",
            "statement",
            "correct_answer",
            "wrong_answers",
            "subject",
            "topic",
            "difficulty",
            "source",
            "cohort_key",
            "is_active",
            "created_at_utc",
            "updated_at_utc",
        )

    def insert_rows_json(self, table_id: str, rows: list[dict[str, object]]) -> None:
        self.inserted_rows.append((table_id, rows))


def test_load_active_index_frame_scopes_students_to_one_cohort() -> None:
    fake_client = FakeBigQueryClient()
    repository = QuestionRepository(fake_client, "project.dataset.question_bank")

    repository.load_active_index_frame(cohort_key="ano_1")

    assert "LOWER(TRIM(cohort_key)) = @cohort_key" in fake_client.queries[0]
    parameters = fake_client.parameters[0]
    assert parameters is not None
    assert parameters[0].name == "cohort_key"
    assert parameters[0].to_api_repr()["parameterValue"]["value"] == "ano_1"


def test_load_active_index_frame_keeps_teacher_scope_global() -> None:
    fake_client = FakeBigQueryClient()
    repository = QuestionRepository(fake_client, "project.dataset.question_bank")

    repository.load_active_index_frame()

    assert "LOWER(TRIM(cohort_key)) = @cohort_key" not in fake_client.queries[0]
    assert fake_client.parameters[0] is None


def test_load_question_frame_by_id_enforces_cohort_scope() -> None:
    fake_client = FakeBigQueryClient()
    repository = QuestionRepository(fake_client, "project.dataset.question_bank")

    repository.load_question_frame_by_id(42, cohort_key="ano_2")

    assert "AND id_question = @id_question" in fake_client.queries[0]
    assert "LOWER(TRIM(cohort_key)) = @cohort_key" in fake_client.queries[0]
    parameters = fake_client.parameters[0]
    assert parameters is not None
    assert {parameter.name for parameter in parameters} == {"id_question", "cohort_key"}


def test_load_question_frames_by_ids_preserves_requested_order_in_query() -> None:
    fake_client = FakeBigQueryClient()
    repository = QuestionRepository(fake_client, "project.dataset.question_bank")

    repository.load_question_frames_by_ids([42, 7, 42], cohort_key="ano_2")

    assert "FROM UNNEST(@id_question_ids) AS id_question WITH OFFSET AS requested_offset" in fake_client.queries[0]
    assert "INNER JOIN `project.dataset.question_bank` AS question_bank" in fake_client.queries[0]
    assert "ORDER BY requested_ids.requested_offset" in fake_client.queries[0]
    assert "LOWER(TRIM(cohort_key)) = @cohort_key" in fake_client.queries[0]
    parameters = fake_client.parameters[0]
    assert parameters is not None
    assert [parameter.name for parameter in parameters] == ["id_question_ids", "cohort_key"]
    assert parameters[0].to_api_repr()["parameterValue"]["arrayValues"] == [
        {"value": "42"},
        {"value": "7"},
    ]


def test_load_active_project_frame_returns_distinct_non_blank_cohorts() -> None:
    fake_client = FakeBigQueryClient()
    repository = QuestionRepository(fake_client, "project.dataset.question_bank")

    repository.load_active_project_frame()

    assert "SELECT DISTINCT" in fake_client.queries[0]
    assert "cohort_key IS NOT NULL" in fake_client.queries[0]
    assert "TRIM(cohort_key) != ''" in fake_client.queries[0]
    assert fake_client.parameters[0] is None


def test_append_question_row_filters_unknown_fields_before_insert() -> None:
    fake_client = FakeBigQueryClient()
    repository = QuestionRepository(fake_client, "project.dataset.question_bank")

    repository.append_question_row(
        {
            "id_question": 999,
            "statement": "Quanto é 2 + 2?",
            "correct_answer": {"alternative_text": "4", "explanation": "Porque 2 + 2 = 4."},
            "wrong_answers": [{"alternative_text": "3", "explanation": "Faltou 1."}],
            "subject": "Matemática",
            "topic": "aritmetica",
            "difficulty": "1_basico",
            "source": "manual",
            "cohort_key": "crescer_e_conectar",
            "is_active": True,
            "created_at_utc": "2026-04-09T12:00:00Z",
            "updated_at_utc": "2026-04-09T12:00:00Z",
            "ignored_field": "should_not_go",
        }
    )

    assert fake_client.inserted_rows == [
        (
            "project.dataset.question_bank",
            [
                {
                    "id_question": 999,
                    "statement": "Quanto é 2 + 2?",
                    "correct_answer": {"alternative_text": "4", "explanation": "Porque 2 + 2 = 4."},
                    "wrong_answers": [{"alternative_text": "3", "explanation": "Faltou 1."}],
                    "subject": "matematica",
                    "topic": "aritmetica",
                    "difficulty": 1,
                    "source": "manual",
                    "cohort_key": "crescer_e_conectar",
                    "is_active": True,
                    "created_at_utc": "2026-04-09T12:00:00Z",
                    "updated_at_utc": "2026-04-09T12:00:00Z",
                }
            ],
        )
    ]
