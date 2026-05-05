from __future__ import annotations

import sys
import hashlib
import importlib
import json
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, cast

from modules.utils.logging_utils import APP_LOGGER_NAME


STARLETTE_AUTH_ROUTE_MODULE = "streamlit.web.server.starlette.starlette_auth_routes"


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

    _patch_starlette_auth_callback_logger()


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


def _patch_starlette_auth_callback_logger() -> None:
    try:
        route_module = importlib.import_module(STARLETTE_AUTH_ROUTE_MODULE)
    except (ImportError, ModuleNotFoundError):
        return

    auth_callback = getattr(route_module, "_auth_callback", None)
    if not callable(auth_callback) or getattr(auth_callback, "_glipmath_logged", False):
        return

    @wraps(auth_callback)
    async def logged_auth_callback(request: Any, base_url: str) -> Any:
        logger = _logger()
        logger.info(
            "OAuth callback received | details=%s",
            _json_for_log(_oauth_callback_snapshot(request, base_url=base_url)),
        )
        try:
            response = await auth_callback(request, base_url)
        except Exception:
            logger.exception(
                "OAuth callback failed inside Streamlit auth | details=%s",
                _json_for_log(_oauth_callback_snapshot(request, base_url=base_url)),
            )
            raise

        logger.info(
            "OAuth callback completed | status_code=%s | details=%s",
            getattr(response, "status_code", "<unknown>"),
            _json_for_log(_oauth_callback_snapshot(request, base_url=base_url)),
        )
        return response

    logged_auth_callback._glipmath_logged = True
    route_module._auth_callback = logged_auth_callback


def _oauth_callback_snapshot(request: Any, *, base_url: str) -> dict[str, Any]:
    query_params = getattr(request, "query_params", {})
    query_keys = sorted(str(key) for key in _keys(query_params))
    state = _get_mapping_value(query_params, "state")
    code = _get_mapping_value(query_params, "code")
    error = _get_mapping_value(query_params, "error")
    error_description = _get_mapping_value(query_params, "error_description")
    session = getattr(request, "session", {}) or {}
    cookies = getattr(request, "cookies", {}) or {}

    return {
        "base_url": base_url,
        "path": _safe_request_path(request),
        "query_keys": query_keys,
        "has_code": bool(code),
        "has_state": bool(state),
        "state_len": len(state) if state else 0,
        "state_fingerprint": _fingerprint(state),
        "oauth_error": _short_text(error),
        "oauth_error_description": _short_text(error_description),
        "session_keys": sorted(str(key) for key in _keys(session)),
        "session_state_keys": _session_state_keys(session),
        "cookie_names": sorted(str(key) for key in _keys(cookies)),
    }


def _session_state_keys(session: Any) -> list[str]:
    if not isinstance(session, dict):
        return []
    state = session.get("_state")
    if not isinstance(state, dict):
        return []
    return sorted(str(key) for key in state.keys())


def _safe_request_path(request: Any) -> str:
    url = getattr(request, "url", None)
    path = getattr(url, "path", None)
    if path:
        return str(path)
    return str(getattr(request, "scope", {}).get("path", "<unknown>"))


def _get_mapping_value(mapping: Any, key: str) -> str | None:
    getter = getattr(mapping, "get", None)
    if callable(getter):
        value = getter(key)
    elif isinstance(mapping, dict):
        value = mapping.get(key)
    else:
        value = None
    if value is None:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    text = str(value)
    return text or None


def _keys(mapping: Any) -> list[Any]:
    keys = getattr(mapping, "keys", None)
    if not callable(keys):
        return []
    try:
        return list(keys())
    except TypeError:
        return []


def _fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _short_text(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("\n", " ").replace("\r", " ")[:160]


def _json_for_log(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)


def _logger() -> logging.Logger:
    return logging.getLogger(APP_LOGGER_NAME).getChild(__name__)
