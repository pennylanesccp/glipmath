import pandas as pd

from modules.auth.authorization_service import AuthorizationService


class FakeUserAccessRepository:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame
        self.requested_emails: list[str] = []

    def load_active_user_frame(self, user_email: str) -> pd.DataFrame:
        self.requested_emails.append(user_email)
        return self.frame


def test_authorization_succeeds_for_active_bigquery_access_row() -> None:
    repository = FakeUserAccessRepository(
        pd.DataFrame(
            [
                {
                    "user_email": " ANA@Example.com ",
                    "role": "student",
                    "cohort_key": "Ano_1",
                    "is_active": True,
                    "display_name": "Ana BigQuery",
                }
            ]
        )
    )

    user = AuthorizationService(repository).authorize(" ANA@Example.com ", fallback_name="Ana OAuth")

    assert user is not None
    assert user.email == "ana@example.com"
    assert user.display_name == "Ana BigQuery"
    assert user.role == "student"
    assert user.cohort_key == "ano_1"
    assert user.accessible_cohort_keys == ("ano_1",)
    assert repository.requested_emails == ["ana@example.com"]


def test_authorization_returns_none_when_user_access_row_is_missing() -> None:
    user = AuthorizationService(FakeUserAccessRepository(pd.DataFrame())).authorize("ana@example.com")

    assert user is None


def test_authorization_returns_none_for_inactive_access_row() -> None:
    repository = FakeUserAccessRepository(
        pd.DataFrame(
            [
                {
                    "user_email": "ana@example.com",
                    "role": "student",
                    "cohort_key": "ano_1",
                    "is_active": False,
                }
            ]
        )
    )

    user = AuthorizationService(repository).authorize("ana@example.com")

    assert user is None


def test_authorization_aggregates_multiple_teacher_projects() -> None:
    repository = FakeUserAccessRepository(
        pd.DataFrame(
            [
                {
                    "user_email": "prof@example.com",
                    "role": "teacher",
                    "cohort_key": "crescer_e_conectar",
                    "is_active": True,
                    "display_name": "Prof BigQuery",
                },
                {
                    "user_email": "prof@example.com",
                    "role": "teacher",
                    "cohort_key": "rumo_etec",
                    "is_active": True,
                    "display_name": "Prof BigQuery",
                },
            ]
        )
    )

    user = AuthorizationService(repository).authorize("prof@example.com")

    assert user is not None
    assert user.role == "teacher"
    assert user.accessible_cohort_keys == ("crescer_e_conectar", "rumo_etec")
    assert user.cohort_key == "crescer_e_conectar"
    assert user.can_access_professor_space is True


def test_authorization_prefers_admin_role_when_multiple_roles_exist() -> None:
    repository = FakeUserAccessRepository(
        pd.DataFrame(
            [
                {
                    "user_email": "admin@example.com",
                    "role": "teacher",
                    "cohort_key": "crescer_e_conectar",
                    "is_active": True,
                },
                {
                    "user_email": "admin@example.com",
                    "role": "admin",
                    "cohort_key": "all",
                    "is_active": True,
                },
            ]
        )
    )

    user = AuthorizationService(repository).authorize("admin@example.com")

    assert user is not None
    assert user.role == "admin"
    assert user.is_admin is True
    assert user.has_global_project_access is True
    assert user.accessible_cohort_keys == ()
