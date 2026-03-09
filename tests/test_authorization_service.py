import pandas as pd

from modules.auth.authorization_service import AuthorizationService


class FakeWhitelistRepository:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def load_frame(self) -> pd.DataFrame:
        return self._frame


def test_authorization_matches_normalized_email() -> None:
    frame = pd.DataFrame(
        [
            {"id_user": "1", "email": " ANA@Example.com ", "name": "Ana", "is_active": "true"},
        ]
    )
    service = AuthorizationService(FakeWhitelistRepository(frame))

    user = service.authorize("ana@example.com")

    assert user is not None
    assert user.id_user == 1
    assert user.email == "ana@example.com"


def test_authorization_denies_inactive_user() -> None:
    frame = pd.DataFrame(
        [
            {"id_user": "1", "email": "ana@example.com", "name": "Ana", "is_active": "false"},
        ]
    )
    service = AuthorizationService(FakeWhitelistRepository(frame))

    user = service.authorize("ana@example.com")

    assert user is None
