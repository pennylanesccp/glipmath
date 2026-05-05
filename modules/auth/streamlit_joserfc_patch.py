from __future__ import annotations

import sys
import hashlib
import importlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from modules.utils.logging_utils import APP_LOGGER_NAME


STARLETTE_AUTH_ROUTE_MODULE = "streamlit.web.server.starlette.starlette_auth_routes"
OAUTH_STATE_COOKIE_NAME = "_glipmath_oauth_state"
OAUTH_STATE_COOKIE_MAX_AGE_SECONDS = 10 * 60
AUTHLIB_STATE_SESSION_TTL_SECONDS = 60 * 60


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

    _patch_starlette_auth_routes()


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


def _patch_starlette_auth_routes() -> None:
    try:
        route_module = importlib.import_module(STARLETTE_AUTH_ROUTE_MODULE)
    except (ImportError, ModuleNotFoundError):
        return

    _patch_starlette_auth_login(route_module)
    _patch_starlette_auth_callback_logger(route_module)


def _patch_starlette_auth_login(route_module: Any) -> None:
    auth_login = getattr(route_module, "_auth_login", None)
    if not callable(auth_login) or getattr(auth_login, "_glipmath_state_cookie", False):
        return

    @wraps(auth_login)
    async def auth_login_with_state_cookie(request: Any, base_url: str) -> Any:
        response = await auth_login(request, base_url)
        state = _state_from_redirect_response(response)
        if state:
            _set_oauth_state_cookie(response, route_module, state)
        return response

    auth_login_with_state_cookie._glipmath_state_cookie = True
    route_module._auth_login = auth_login_with_state_cookie


def _patch_starlette_auth_callback_logger(route_module: Any) -> None:
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
        restored_state_session = _restore_oauth_state_session_marker(
            request,
            route_module,
        )
        if restored_state_session:
            logger.info(
                "Restored OAuth callback state session marker from fallback cookie | details=%s",
                _json_for_log(_oauth_callback_snapshot(request, base_url=base_url)),
            )
        try:
            response = await auth_callback(request, base_url)
        except Exception as error:
            logger.exception(
                "OAuth callback failed inside Streamlit auth | details=%s",
                _json_for_log(_oauth_callback_snapshot(request, base_url=base_url)),
            )
            if _is_mismatching_state_error(error):
                redirect_response = await _redirect_to_base(route_module, base_url)
                if redirect_response is not None:
                    _clear_oauth_state_cookie(redirect_response, route_module)
                    return redirect_response
            raise

        _clear_oauth_state_cookie(response, route_module)
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
        "session_keys": _safe_keys_for_log(session),
        "session_state_keys": _session_state_keys(session),
        "cookie_names": sorted(str(key) for key in _keys(cookies)),
        "has_streamlit_session_cookie": bool(
            _get_mapping_value(cookies, "_streamlit_session")
        ),
        "has_oauth_state_cookie": bool(
            _get_mapping_value(cookies, OAUTH_STATE_COOKIE_NAME)
        ),
    }


def _state_from_redirect_response(response: Any) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None

    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None

    location = getter("location") or getter("Location")
    if not location:
        return None

    parsed_location = urlparse(str(location))
    state_values = parse_qs(parsed_location.query).get("state")
    if not state_values:
        return None

    state = str(state_values[0]).strip()
    return state or None


def _set_oauth_state_cookie(
    response: Any,
    route_module: Any,
    state: str,
) -> None:
    set_cookie = getattr(response, "set_cookie", None)
    if not callable(set_cookie):
        return

    signed_state = _encode_signed_state_cookie(route_module, state)
    if signed_state is None:
        return

    set_cookie(
        OAUTH_STATE_COOKIE_NAME,
        signed_state,
        max_age=OAUTH_STATE_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        path=_cookie_path(route_module),
    )


def _clear_oauth_state_cookie(response: Any, route_module: Any) -> None:
    delete_cookie = getattr(response, "delete_cookie", None)
    if not callable(delete_cookie):
        return

    delete_cookie(OAUTH_STATE_COOKIE_NAME, path=_cookie_path(route_module))


def _restore_oauth_state_session_marker(request: Any, route_module: Any) -> bool:
    query_params = getattr(request, "query_params", {})
    state = _get_mapping_value(query_params, "state")
    if not state:
        return False

    session = getattr(request, "session", None)
    if session is None:
        return False

    provider = _provider_for_state(route_module, state)
    if not provider:
        return False

    state_key = _authlib_state_key(provider, state)
    if state_key in session:
        return False

    if not _auth_cache_has_state(route_module, state_key):
        return False

    cookies = getattr(request, "cookies", {}) or {}
    cookie_state = _decode_signed_state_cookie(
        route_module,
        _get_mapping_value(cookies, OAUTH_STATE_COOKIE_NAME),
    )
    if cookie_state != state:
        return False

    session[state_key] = {"exp": time.time() + AUTHLIB_STATE_SESSION_TTL_SECONDS}
    return True


def _encode_signed_state_cookie(route_module: Any, state: str) -> str | None:
    create_signed_value = getattr(route_module, "create_signed_value", None)
    get_cookie_secret = getattr(route_module, "get_cookie_secret", None)
    if not callable(create_signed_value) or not callable(get_cookie_secret):
        return None

    payload = json.dumps(
        {"state": state},
        ensure_ascii=True,
        separators=(",", ":"),
    )
    signed_value = create_signed_value(
        get_cookie_secret(),
        OAUTH_STATE_COOKIE_NAME,
        payload,
    )
    if isinstance(signed_value, bytes):
        return signed_value.decode("utf-8")
    return str(signed_value)


def _decode_signed_state_cookie(route_module: Any, cookie_value: str | None) -> str | None:
    if not cookie_value:
        return None

    decode_signed_value = getattr(route_module, "decode_signed_value", None)
    get_cookie_secret = getattr(route_module, "get_cookie_secret", None)
    if not callable(decode_signed_value) or not callable(get_cookie_secret):
        return None

    decoded_value = decode_signed_value(
        get_cookie_secret(),
        OAUTH_STATE_COOKIE_NAME,
        cookie_value,
        max_age_days=OAUTH_STATE_COOKIE_MAX_AGE_SECONDS / 86400,
    )
    if isinstance(decoded_value, bytes):
        decoded_text = decoded_value.decode("utf-8")
    elif decoded_value is None:
        return None
    else:
        decoded_text = str(decoded_value)

    try:
        payload = json.loads(decoded_text)
    except json.JSONDecodeError:
        return None

    state = payload.get("state")
    if not state:
        return None
    return str(state)


def _provider_for_state(route_module: Any, state: str) -> str | None:
    provider_getter = getattr(route_module, "_get_provider_by_state", None)
    if not callable(provider_getter):
        return None

    provider = provider_getter(state)
    if not provider:
        return None
    return str(provider)


def _auth_cache_has_state(route_module: Any, state_key: str) -> bool:
    auth_cache = getattr(route_module, "_STARLETTE_AUTH_CACHE", None)
    get_dict = getattr(auth_cache, "get_dict", None)
    if not callable(get_dict):
        return False

    return state_key in get_dict()


def _authlib_state_key(provider: str, state: str) -> str:
    return f"_state_{provider}_{state}"


def _cookie_path(route_module: Any) -> str:
    cookie_path_getter = getattr(route_module, "_get_cookie_path", None)
    if callable(cookie_path_getter):
        return str(cookie_path_getter())
    return "/"


async def _redirect_to_base(route_module: Any, base_url: str) -> Any:
    redirect_to_base = getattr(route_module, "_redirect_to_base", None)
    if not callable(redirect_to_base):
        return None
    return await redirect_to_base(base_url)


def _is_mismatching_state_error(error: Exception) -> bool:
    return error.__class__.__name__ == "MismatchingStateError"


def _session_state_keys(session: Any) -> list[str]:
    if not isinstance(session, dict):
        return []
    state = session.get("_state")
    if not isinstance(state, dict):
        return []
    return _safe_keys_for_log(state)


def _safe_keys_for_log(mapping: Any) -> list[str]:
    return sorted(_safe_key_for_log(key) for key in _keys(mapping))


def _safe_key_for_log(key: Any) -> str:
    text = str(key)
    if not text.startswith("_state_"):
        return text

    parts = text.split("_", 3)
    if len(parts) == 4 and parts[2] and parts[3]:
        return f"_state_{parts[2]}_{_fingerprint(parts[3])}"
    return "_state_<redacted>"


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
