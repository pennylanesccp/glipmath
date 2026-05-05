from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from typing import Any, cast


def install_streamlit_joserfc_auth_patch() -> None:
    """Replace Streamlit's deprecated JOSE token helpers with joserfc."""

    try:
        import streamlit.auth_util as auth_util
    except (ImportError, ModuleNotFoundError):
        return

    original_encode = getattr(auth_util, "encode_provider_token", None)
    original_decode = getattr(auth_util, "decode_provider_token", None)

    auth_util.encode_provider_token = encode_provider_token
    auth_util.decode_provider_token = decode_provider_token

    for module in list(sys.modules.values()):
        module_name = getattr(module, "__name__", "")
        if not module_name.startswith("streamlit."):
            continue
        if getattr(module, "encode_provider_token", None) is original_encode:
            module.encode_provider_token = encode_provider_token
        if getattr(module, "decode_provider_token", None) is original_decode:
            module.decode_provider_token = decode_provider_token


def encode_provider_token(provider: str) -> str:
    """Return Streamlit's short-lived provider token with joserfc."""

    from joserfc import jwt

    header = {"alg": "HS256"}
    payload = {
        "provider": provider,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=2),
    }
    token = jwt.encode(header, payload, _signing_key(), algorithms=["HS256"])
    if isinstance(token, bytes):
        return token.decode("latin-1")
    return token


def decode_provider_token(provider_token: str) -> dict[str, Any]:
    """Decode Streamlit's short-lived provider token with joserfc."""

    from joserfc import jwt
    from joserfc.errors import JoseError
    from joserfc.jwt import JWTClaimsRegistry
    from streamlit.errors import StreamlitAuthError

    claims_registry = JWTClaimsRegistry(
        exp={"essential": True},
        provider={"essential": True},
    )
    try:
        token = jwt.decode(provider_token, _signing_key(), algorithms=["HS256"])
        claims_registry.validate(token.claims)
    except JoseError as error:
        raise StreamlitAuthError(f"Error decoding provider token: {error}") from None

    return cast("dict[str, Any]", token.claims)


def _signing_key() -> Any:
    from joserfc import jwk
    from streamlit.auth_util import get_signing_secret

    return jwk.import_key(get_signing_secret(), "oct")
