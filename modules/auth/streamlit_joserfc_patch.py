from __future__ import annotations

import hashlib
import importlib
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, cast
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from modules.utils.logging_utils import APP_LOGGER_NAME


STARLETTE_AUTH_ROUTE_MODULE = "streamlit.web.server.starlette.starlette_auth_routes"
OAUTH_STATE_COOKIE_NAME = "_glipmath_oauth_state"
STREAMLIT_XSRF_COOKIE_NAME = "_streamlit_xsrf"
STREAMLIT_SESSION_COOKIE_NAME = "_streamlit_session"
STREAMLIT_USER_COOKIE_NAME = "_streamlit_user"
STREAMLIT_TOKENS_COOKIE_NAME = "_streamlit_user_tokens"
OAUTH_STATE_COOKIE_MAX_AGE_SECONDS = 10 * 60
AUTHLIB_STATE_SESSION_TTL_SECONDS = 60 * 60
OAUTH_STATE_BROWSER_BINDING_TTL_SECONDS = 10 * 60
OAUTH_COOKIE_PATH = "/"
OAUTH_COOKIE_SAMESITE = "none"
OAUTH_COOKIE_SECURE = True
LOGIN_ERROR_QUERY_PARAM = "auth_error"
LOGIN_ERROR_SESSION_EXPIRED = "login_session_expired"
_AUTH_COOKIE_CHUNK_DELETE_LIMIT = 8
_OAUTH_STATE_BROWSER_BINDINGS: dict[str, tuple[str, str, float]] = {}
_SERVER_CLEARED_COOKIE_NAMES = (
    OAUTH_STATE_COOKIE_NAME,
    STREAMLIT_SESSION_COOKIE_NAME,
    STREAMLIT_USER_COOKIE_NAME,
    STREAMLIT_TOKENS_COOKIE_NAME,
)
_CLIENT_CLEARED_COOKIE_PREFIXES = (
    f"{STREAMLIT_USER_COOKIE_NAME}_",
    f"{STREAMLIT_TOKENS_COOKIE_NAME}_",
)


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

    _patch_starlette_session_middleware()
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

    _patch_streamlit_auth_cookie_helpers(route_module)
    _patch_starlette_auth_login(route_module)
    _patch_starlette_auth_callback_logger(route_module)


def build_client_oauth_cookie_cleanup_html() -> str:
    """Return hidden HTML that clears client-readable stale OAuth cookies."""

    cookie_names = json.dumps(_SERVER_CLEARED_COOKIE_NAMES, ensure_ascii=True)
    cookie_prefixes = json.dumps(_CLIENT_CLEARED_COOKIE_PREFIXES, ensure_ascii=True)
    return f"""
<script>
(() => {{
  const baseNames = {cookie_names};
  const chunkPrefixes = {cookie_prefixes};
  const names = new Set(baseNames);
  for (const rawCookie of document.cookie.split(";")) {{
    const name = rawCookie.split("=")[0].trim();
    if (chunkPrefixes.some((prefix) => name.startsWith(prefix))) {{
      names.add(name);
    }}
  }}
  for (const name of names) {{
    document.cookie = `${{name}}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=None; Secure`;
  }}
}})();
</script>
""".strip()


def is_oauth_flow_cookie_name(cookie_name: str) -> bool:
    """Return whether a cookie is owned by Streamlit's OAuth flow."""

    return cookie_name in _SERVER_CLEARED_COOKIE_NAMES or any(
        cookie_name.startswith(prefix) for prefix in _CLIENT_CLEARED_COOKIE_PREFIXES
    )


def _patch_starlette_session_middleware() -> None:
    try:
        from starlette.middleware import sessions
    except (ImportError, ModuleNotFoundError):
        return

    session_middleware = getattr(sessions, "SessionMiddleware", None)
    if session_middleware is None or getattr(
        session_middleware,
        "_glipmath_cross_site_cookie",
        False,
    ):
        return

    original_init = session_middleware.__init__
    original_call = session_middleware.__call__

    @wraps(original_init)
    def init_with_cross_site_streamlit_session_cookie(
        self: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if kwargs.get("session_cookie") == STREAMLIT_SESSION_COOKIE_NAME:
            kwargs["same_site"] = OAUTH_COOKIE_SAMESITE
            kwargs["https_only"] = OAUTH_COOKIE_SECURE
            kwargs["path"] = OAUTH_COOKIE_PATH
        original_init(self, *args, **kwargs)
        if getattr(self, "session_cookie", None) == STREAMLIT_SESSION_COOKIE_NAME:
            _configure_streamlit_session_middleware_cookie(self)

    @wraps(original_call)
    async def call_with_cross_site_streamlit_session_cookie(
        self: Any,
        scope: Any,
        receive: Any,
        send: Any,
    ) -> Any:
        if getattr(self, "session_cookie", None) == STREAMLIT_SESSION_COOKIE_NAME:
            _configure_streamlit_session_middleware_cookie(self)
        return await original_call(self, scope, receive, send)

    session_middleware.__init__ = init_with_cross_site_streamlit_session_cookie
    session_middleware.__call__ = call_with_cross_site_streamlit_session_cookie
    session_middleware._glipmath_cross_site_cookie = True


def _configure_streamlit_session_middleware_cookie(session_middleware: Any) -> None:
    session_middleware.path = OAUTH_COOKIE_PATH
    session_middleware.security_flags = (
        f"httponly; samesite={OAUTH_COOKIE_SAMESITE}; secure"
    )


def _patch_streamlit_auth_cookie_helpers(route_module: Any) -> None:
    _patch_streamlit_auth_cookie_setter(route_module)
    _patch_streamlit_auth_cookie_clearer(route_module)


def _patch_streamlit_auth_cookie_setter(route_module: Any) -> None:
    set_single_cookie = getattr(route_module, "_set_single_cookie", None)
    if not callable(set_single_cookie) or getattr(
        set_single_cookie,
        "_glipmath_cross_site_cookie",
        False,
    ):
        return

    @wraps(set_single_cookie)
    def set_single_cookie_with_cross_site_attrs(
        response: Any,
        cookie_name: str,
        serialized_value: str,
    ) -> None:
        create_signed_value = getattr(route_module, "create_signed_value", None)
        get_cookie_secret = getattr(route_module, "get_cookie_secret", None)
        set_cookie = getattr(response, "set_cookie", None)
        if (
            not callable(create_signed_value)
            or not callable(get_cookie_secret)
            or not callable(set_cookie)
        ):
            set_single_cookie(response, cookie_name, serialized_value)
            return

        signed_value = create_signed_value(
            get_cookie_secret(),
            cookie_name,
            serialized_value,
        )
        if isinstance(signed_value, bytes):
            cookie_payload = signed_value.decode("utf-8")
        else:
            cookie_payload = str(signed_value)

        set_cookie(
            cookie_name,
            cookie_payload,
            httponly=True,
            secure=OAUTH_COOKIE_SECURE,
            samesite=OAUTH_COOKIE_SAMESITE,
            path=OAUTH_COOKIE_PATH,
        )

    set_single_cookie_with_cross_site_attrs._glipmath_cross_site_cookie = True
    route_module._set_single_cookie = set_single_cookie_with_cross_site_attrs


def _patch_streamlit_auth_cookie_clearer(route_module: Any) -> None:
    clear_auth_cookie = getattr(route_module, "_clear_auth_cookie", None)
    if not callable(clear_auth_cookie) or getattr(
        clear_auth_cookie,
        "_glipmath_cross_site_cookie",
        False,
    ):
        return

    @wraps(clear_auth_cookie)
    def clear_auth_cookie_with_cross_site_attrs(response: Any, request: Any) -> None:
        clear_auth_cookie(response, request)
        _clear_oauth_flow_cookies(response, route_module, request=request)

    clear_auth_cookie_with_cross_site_attrs._glipmath_cross_site_cookie = True
    route_module._clear_auth_cookie = clear_auth_cookie_with_cross_site_attrs


def _patch_starlette_auth_login(route_module: Any) -> None:
    auth_login = getattr(route_module, "_auth_login", None)
    if not callable(auth_login) or getattr(auth_login, "_glipmath_state_cookie", False):
        return

    @wraps(auth_login)
    async def auth_login_with_state_cookie(request: Any, base_url: str) -> Any:
        response = await auth_login(request, base_url)
        _clear_oauth_flow_cookies(response, route_module, request=request)
        state = _state_from_redirect_response(response)
        if state:
            _set_oauth_state_cookie(response, route_module, state)
            binding_cookie_name = _remember_oauth_state_browser_binding(
                request,
                state,
            )
            _logger().info(
                "Prepared OAuth login state fallback | state_fingerprint=%s | binding_cookie=%s",
                _fingerprint(state),
                binding_cookie_name or "<none>",
            )
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
                "Restored OAuth callback state session marker from fallback binding | details=%s",
                _json_for_log(_oauth_callback_snapshot(request, base_url=base_url)),
            )
        try:
            response = await auth_callback(request, base_url)
        except Exception as error:
            if _is_mismatching_state_error(error):
                logger.warning(
                    "OAuth callback rejected because the returned state did not match the browser session | details=%s",
                    _json_for_log(_oauth_callback_snapshot(request, base_url=base_url)),
                )
                _forget_oauth_state_browser_binding(_callback_state(request))
                redirect_response = await _redirect_to_login_retry(
                    route_module,
                    base_url,
                )
                if redirect_response is not None:
                    _clear_oauth_flow_cookies(
                        redirect_response,
                        route_module,
                        request=request,
                    )
                    return redirect_response
            else:
                logger.exception(
                    "OAuth callback failed inside Streamlit auth | details=%s",
                    _json_for_log(_oauth_callback_snapshot(request, base_url=base_url)),
                )
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
            _get_mapping_value(cookies, STREAMLIT_SESSION_COOKIE_NAME)
        ),
        "has_streamlit_xsrf_cookie": bool(
            _get_mapping_value(cookies, STREAMLIT_XSRF_COOKIE_NAME)
        ),
        "has_oauth_state_cookie": bool(
            _get_mapping_value(cookies, OAUTH_STATE_COOKIE_NAME)
        ),
        "has_oauth_state_browser_binding": bool(
            state and _oauth_state_browser_binding_exists(state)
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
        secure=OAUTH_COOKIE_SECURE,
        samesite=OAUTH_COOKIE_SAMESITE,
        path=OAUTH_COOKIE_PATH,
    )


def _clear_oauth_state_cookie(response: Any, route_module: Any) -> None:
    _delete_cookie(response, OAUTH_STATE_COOKIE_NAME, route_module)


def _clear_oauth_flow_cookies(
    response: Any,
    route_module: Any,
    *,
    request: Any | None = None,
) -> None:
    for cookie_name in _oauth_flow_cookie_names_to_clear(request):
        _delete_cookie(response, cookie_name, route_module)


def _oauth_flow_cookie_names_to_clear(request: Any | None) -> list[str]:
    cookie_names = set(_SERVER_CLEARED_COOKIE_NAMES)
    for cookie_name in (STREAMLIT_USER_COOKIE_NAME, STREAMLIT_TOKENS_COOKIE_NAME):
        for chunk_index in range(1, _AUTH_COOKIE_CHUNK_DELETE_LIMIT + 1):
            cookie_names.add(f"{cookie_name}_{chunk_index}")

    cookies = getattr(request, "cookies", {}) if request is not None else {}
    for cookie_name in _keys(cookies or {}):
        text_name = str(cookie_name)
        if is_oauth_flow_cookie_name(text_name):
            cookie_names.add(text_name)

    return sorted(cookie_names)


def _delete_cookie(response: Any, cookie_name: str, route_module: Any) -> None:
    delete_cookie = getattr(response, "delete_cookie", None)
    if not callable(delete_cookie):
        return

    for cookie_path in _cookie_delete_paths(route_module):
        delete_cookie(
            cookie_name,
            path=cookie_path,
            secure=OAUTH_COOKIE_SECURE,
            httponly=True,
            samesite=OAUTH_COOKIE_SAMESITE,
        )


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
    if cookie_state != state and not _oauth_state_browser_binding_matches(
        request,
        state,
    ):
        return False

    session[state_key] = {"exp": time.time() + AUTHLIB_STATE_SESSION_TTL_SECONDS}
    _forget_oauth_state_browser_binding(state)
    return True


def _remember_oauth_state_browser_binding(request: Any, state: str) -> str | None:
    binding = _request_browser_binding(request)
    if binding is None:
        return None

    cookie_name, cookie_fingerprint = binding
    _evict_expired_oauth_state_browser_bindings()
    _OAUTH_STATE_BROWSER_BINDINGS[state] = (
        cookie_name,
        cookie_fingerprint,
        time.time() + OAUTH_STATE_BROWSER_BINDING_TTL_SECONDS,
    )
    return cookie_name


def _oauth_state_browser_binding_matches(request: Any, state: str) -> bool:
    _evict_expired_oauth_state_browser_bindings()
    stored_binding = _OAUTH_STATE_BROWSER_BINDINGS.get(state)
    request_binding = _request_browser_binding(request)
    if stored_binding is None or request_binding is None:
        return False

    stored_cookie_name, stored_fingerprint, _ = stored_binding
    request_cookie_name, request_fingerprint = request_binding
    return (
        request_cookie_name == stored_cookie_name
        and request_fingerprint == stored_fingerprint
    )


def _oauth_state_browser_binding_exists(state: str) -> bool:
    _evict_expired_oauth_state_browser_bindings()
    return state in _OAUTH_STATE_BROWSER_BINDINGS


def _forget_oauth_state_browser_binding(state: str | None) -> None:
    if not state:
        return
    _OAUTH_STATE_BROWSER_BINDINGS.pop(state, None)


def _evict_expired_oauth_state_browser_bindings() -> None:
    now = time.time()
    for state, (_, _, expires_at) in list(_OAUTH_STATE_BROWSER_BINDINGS.items()):
        if expires_at <= now:
            _OAUTH_STATE_BROWSER_BINDINGS.pop(state, None)


def _request_browser_binding(request: Any) -> tuple[str, str] | None:
    cookies = getattr(request, "cookies", {}) or {}
    xsrf_cookie = _get_mapping_value(cookies, STREAMLIT_XSRF_COOKIE_NAME)
    xsrf_fingerprint = _fingerprint(xsrf_cookie)
    if xsrf_fingerprint is None:
        return None
    return STREAMLIT_XSRF_COOKIE_NAME, xsrf_fingerprint


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


def _cookie_delete_paths(route_module: Any) -> tuple[str, ...]:
    configured_path = _cookie_path(route_module)
    if configured_path == OAUTH_COOKIE_PATH:
        return (OAUTH_COOKIE_PATH,)
    return (OAUTH_COOKIE_PATH, configured_path)


async def _redirect_to_base(route_module: Any, base_url: str) -> Any:
    redirect_to_base = getattr(route_module, "_redirect_to_base", None)
    if not callable(redirect_to_base):
        return None
    return await redirect_to_base(base_url)


async def _redirect_to_login_retry(route_module: Any, base_url: str) -> Any:
    response = await _redirect_to_base(route_module, base_url)
    if response is None:
        return None

    headers = getattr(response, "headers", None)
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return response

    location = getter("location") or getter("Location")
    if not location:
        return response

    headers["location"] = _url_with_query_param(
        str(location),
        LOGIN_ERROR_QUERY_PARAM,
        LOGIN_ERROR_SESSION_EXPIRED,
    )
    return response


def _url_with_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    query_values = dict(parse_qs(parsed.query, keep_blank_values=True))
    query_values[key] = [value]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query_values, doseq=True),
            parsed.fragment,
        )
    )


def _is_mismatching_state_error(error: Exception) -> bool:
    return error.__class__.__name__ == "MismatchingStateError"


def _callback_state(request: Any) -> str | None:
    return _get_mapping_value(getattr(request, "query_params", {}), "state")


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
