from modules.auth.authorization_service import AuthorizationService


def test_authorization_matches_normalized_email() -> None:
    user = AuthorizationService().authorize(" ANA@Example.com ", fallback_name="Ana")

    assert user is not None
    assert user.email == "ana@example.com"
    assert user.display_name == "Ana"


def test_authorization_returns_none_for_blank_email() -> None:
    user = AuthorizationService().authorize("   ")

    assert user is None
