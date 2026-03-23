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
