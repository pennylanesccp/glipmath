import pandas as pd

from modules.storage.user_access_repository import UserAccessRepository


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
