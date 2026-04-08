import pandas as pd

from modules.storage.question_repository import QuestionRepository


class FakeBigQueryClient:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.parameters: list[object] = []

    def query_to_dataframe(self, sql: str, *, parameters=None) -> pd.DataFrame:
        self.queries.append(sql)
        self.parameters.append(parameters)
        return pd.DataFrame()

    def execute(self, sql: str, *, parameters=None) -> None:
        raise AssertionError("execute should not be called in these tests")


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


def test_load_active_project_frame_returns_distinct_non_blank_cohorts() -> None:
    fake_client = FakeBigQueryClient()
    repository = QuestionRepository(fake_client, "project.dataset.question_bank")

    repository.load_active_project_frame()

    assert "SELECT DISTINCT" in fake_client.queries[0]
    assert "cohort_key IS NOT NULL" in fake_client.queries[0]
    assert "TRIM(cohort_key) != ''" in fake_client.queries[0]
    assert fake_client.parameters[0] is None
