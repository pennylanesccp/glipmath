import pandas as pd

from modules.storage.user_access_repository import UserAccessRepository


class FakeBigQueryClient:
    def __init__(self, columns: tuple[str, ...]) -> None:
        self.columns = columns
        self.queries: list[str] = []
        self.parameters: list[object] = []
        self.execute_calls: list[tuple[str, object]] = []
        self.insert_calls: list[tuple[str, list[dict[str, object]]]] = []

    def get_table_column_names(self, table_id: str) -> tuple[str, ...]:
        return self.columns

    def query_to_dataframe(self, sql: str, *, parameters=None) -> pd.DataFrame:
        self.queries.append(sql)
        self.parameters.append(parameters)
        return pd.DataFrame()

    def insert_rows_json(self, table_id: str, rows: list[dict[str, object]]) -> None:
        self.insert_calls.append((table_id, rows))

    def execute(self, sql: str, *, parameters=None) -> int:
        self.execute_calls.append((sql, parameters))
        return 1


def test_append_access_row_filters_unknown_columns() -> None:
    fake_client = FakeBigQueryClient(
        (
            "user_email",
            "role",
            "cohort_key",
            "is_active",
            "created_at_utc",
            "updated_at_utc",
        )
    )
    repository = UserAccessRepository(fake_client, "project.dataset.user_access")

    repository.append_access_row(
        {
            "user_email": "aluno@example.com",
            "role": "student",
            "cohort_key": "rumo_etec",
            "is_active": True,
            "display_name": "Aluno",
            "created_at_utc": "2026-04-09T12:00:00+00:00",
            "updated_at_utc": "2026-04-09T12:00:00+00:00",
        }
    )

    assert fake_client.insert_calls == [
        (
            "project.dataset.user_access",
            [
                {
                    "user_email": "aluno@example.com",
                    "role": "student",
                    "cohort_key": "rumo_etec",
                    "is_active": True,
                    "created_at_utc": "2026-04-09T12:00:00+00:00",
                    "updated_at_utc": "2026-04-09T12:00:00+00:00",
                }
            ],
        )
    ]


def test_load_active_students_frame_filters_students_by_project() -> None:
    fake_client = FakeBigQueryClient(())
    repository = UserAccessRepository(fake_client, "project.dataset.user_access")

    repository.load_active_students_frame("rumo_etec")

    assert "FROM `project.dataset.user_access`" in fake_client.queries[0]
    assert "LOWER(TRIM(cohort_key)) = @cohort_key" in fake_client.queries[0]
    assert "LOWER(TRIM(role)) = 'student'" in fake_client.queries[0]
    assert "is_active = TRUE" in fake_client.queries[0]
    assert fake_client.parameters[0][0].name == "cohort_key"
    assert fake_client.parameters[0][0].value == "rumo_etec"


def test_deactivate_student_access_updates_active_student_rows() -> None:
    fake_client = FakeBigQueryClient(())
    repository = UserAccessRepository(fake_client, "project.dataset.user_access")

    affected_rows = repository.deactivate_student_access(
        user_email="aluno@example.com",
        cohort_key="rumo_etec",
    )

    assert affected_rows == 1
    sql, parameters = fake_client.execute_calls[0]
    assert "UPDATE `project.dataset.user_access`" in sql
    assert "is_active = FALSE" in sql
    assert "LOWER(TRIM(user_email)) = @user_email" in sql
    assert "LOWER(TRIM(cohort_key)) = @cohort_key" in sql
    assert "LOWER(TRIM(role)) = 'student'" in sql
    assert "is_active = TRUE" in sql
    assert parameters[0].name == "user_email"
    assert parameters[0].value == "aluno@example.com"
    assert parameters[1].name == "cohort_key"
    assert parameters[1].value == "rumo_etec"
