from __future__ import annotations

import asyncio
import json
import sys
from types import ModuleType, SimpleNamespace

from modules.auth.streamlit_joserfc_patch import (
    LOGIN_ERROR_QUERY_PARAM,
    LOGIN_ERROR_SESSION_EXPIRED,
    OAUTH_STATE_COOKIE_MAX_AGE_SECONDS,
    OAUTH_STATE_COOKIE_NAME,
    STREAMLIT_SESSION_COOKIE_NAME,
    STREAMLIT_TOKENS_COOKIE_NAME,
    STREAMLIT_USER_COOKIE_NAME,
    STREAMLIT_XSRF_COOKIE_NAME,
    _OAUTH_STATE_BROWSER_BINDINGS,
    build_client_oauth_cookie_cleanup_html,
    decode_provider_token,
    encode_provider_token,
    install_streamlit_joserfc_auth_patch,
)


class FakeRedirectResponse:
    def __init__(self, location: str) -> None:
        self.status_code = 302
        self.headers = {"location": location}
        self.cookies: list[dict[str, object]] = []
        self.deleted_cookies: list[dict[str, object]] = []

    def set_cookie(self, key: str, value: str, **kwargs: object) -> None:
        self.cookies.append({"key": key, "value": value, **kwargs})

    def delete_cookie(self, key: str, **kwargs: object) -> None:
        self.deleted_cookies.append({"key": key, **kwargs})


class FakeAuthCache:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get_dict(self) -> dict[str, object]:
        return dict(self.values)


def _deleted_cookie(cookie_name: str) -> dict[str, object]:
    return {
        "key": cookie_name,
        "path": "/",
        "secure": True,
        "httponly": True,
        "samesite": "none",
    }


def test_client_oauth_cookie_cleanup_html_targets_root_cross_site_cookies() -> None:
    html = build_client_oauth_cookie_cleanup_html()

    assert OAUTH_STATE_COOKIE_NAME in html
    assert STREAMLIT_SESSION_COOKIE_NAME in html
    assert "path=/" in html
    assert "SameSite=None" in html
    assert "Secure" in html


def test_install_streamlit_joserfc_auth_patch_replaces_loaded_helpers(
    monkeypatch,
) -> None:
    def old_encode_provider_token(provider: str) -> str:
        return provider

    def old_decode_provider_token(provider_token: str) -> dict[str, str]:
        return {"provider": provider_token}

    async def old_auth_callback(request: object, base_url: str) -> object:
        return SimpleNamespace(status_code=302)

    streamlit_module = ModuleType("streamlit")
    streamlit_module.__path__ = []
    auth_util_module = ModuleType("streamlit.auth_util")
    login_module = ModuleType("streamlit.commands.user_info")
    route_module = ModuleType("streamlit.web.server.starlette.starlette_auth_routes")

    auth_util_module.encode_provider_token = old_encode_provider_token
    auth_util_module.decode_provider_token = old_decode_provider_token
    login_module.encode_provider_token = old_encode_provider_token
    route_module.decode_provider_token = old_decode_provider_token
    route_module._auth_callback = old_auth_callback

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.auth_util", auth_util_module)
    monkeypatch.setitem(sys.modules, "streamlit.commands.user_info", login_module)
    monkeypatch.setitem(
        sys.modules,
        "streamlit.web.server.starlette.starlette_auth_routes",
        route_module,
    )

    install_streamlit_joserfc_auth_patch()

    assert auth_util_module.encode_provider_token is encode_provider_token
    assert auth_util_module.decode_provider_token is decode_provider_token
    assert login_module.encode_provider_token is encode_provider_token
    assert route_module.decode_provider_token is decode_provider_token
    assert route_module._auth_callback is not old_auth_callback

    request = SimpleNamespace(
        query_params={"state": "returned-state", "code": "oauth-code"},
        session={"_state": {"returned-state": {}}},
        cookies={"session": "cookie-value"},
        url=SimpleNamespace(path="/oauth2callback"),
    )
    response = asyncio.run(route_module._auth_callback(request, "/"))

    assert response.status_code == 302


def test_streamlit_auth_login_patch_sets_signed_state_cookie(monkeypatch) -> None:
    def old_encode_provider_token(provider: str) -> str:
        return provider

    def old_decode_provider_token(provider_token: str) -> dict[str, str]:
        return {"provider": provider_token}

    async def old_auth_login(request: object, base_url: str) -> object:
        return FakeRedirectResponse(
            "https://accounts.google.com/o/oauth2/v2/auth"
            "?client_id=client&state=returned-state"
        )

    async def old_auth_callback(request: object, base_url: str) -> object:
        return FakeRedirectResponse("/")

    streamlit_module = ModuleType("streamlit")
    streamlit_module.__path__ = []
    auth_util_module = ModuleType("streamlit.auth_util")
    route_module = ModuleType("streamlit.web.server.starlette.starlette_auth_routes")

    auth_util_module.encode_provider_token = old_encode_provider_token
    auth_util_module.decode_provider_token = old_decode_provider_token
    route_module._auth_login = old_auth_login
    route_module._auth_callback = old_auth_callback
    route_module.create_signed_value = (
        lambda secret, name, value: f"signed:{name}:{value}".encode("utf-8")
    )
    route_module.get_cookie_secret = lambda: "cookie-secret"
    route_module._get_cookie_path = lambda: "/"

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.auth_util", auth_util_module)
    monkeypatch.setitem(
        sys.modules,
        "streamlit.web.server.starlette.starlette_auth_routes",
        route_module,
    )

    install_streamlit_joserfc_auth_patch()

    response = asyncio.run(route_module._auth_login(SimpleNamespace(), "/"))

    assert response.cookies == [
        {
            "key": OAUTH_STATE_COOKIE_NAME,
            "value": (
                f'signed:{OAUTH_STATE_COOKIE_NAME}:'
                '{"state":"returned-state"}'
            ),
            "max_age": OAUTH_STATE_COOKIE_MAX_AGE_SECONDS,
            "httponly": True,
            "secure": True,
            "samesite": "none",
            "path": "/",
        }
    ]
    assert _deleted_cookie(OAUTH_STATE_COOKIE_NAME) in response.deleted_cookies
    assert _deleted_cookie(STREAMLIT_SESSION_COOKIE_NAME) in response.deleted_cookies
    assert _deleted_cookie(STREAMLIT_USER_COOKIE_NAME) in response.deleted_cookies
    assert _deleted_cookie(STREAMLIT_TOKENS_COOKIE_NAME) in response.deleted_cookies


def test_streamlit_auth_cookie_patch_sets_streamlit_cookies_cross_site(
    monkeypatch,
) -> None:
    def old_encode_provider_token(provider: str) -> str:
        return provider

    def old_decode_provider_token(provider_token: str) -> dict[str, str]:
        return {"provider": provider_token}

    def old_set_single_cookie(
        response: FakeRedirectResponse,
        cookie_name: str,
        serialized_value: str,
    ) -> None:
        response.set_cookie(
            cookie_name,
            serialized_value,
            httponly=True,
            samesite="lax",
            path="/app",
        )

    async def old_auth_callback(request: object, base_url: str) -> object:
        return FakeRedirectResponse("/")

    streamlit_module = ModuleType("streamlit")
    streamlit_module.__path__ = []
    auth_util_module = ModuleType("streamlit.auth_util")
    route_module = ModuleType("streamlit.web.server.starlette.starlette_auth_routes")

    auth_util_module.encode_provider_token = old_encode_provider_token
    auth_util_module.decode_provider_token = old_decode_provider_token
    route_module._auth_callback = old_auth_callback
    route_module._set_single_cookie = old_set_single_cookie
    route_module.create_signed_value = (
        lambda secret, name, value: f"signed:{name}:{value}".encode("utf-8")
    )
    route_module.get_cookie_secret = lambda: "cookie-secret"

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.auth_util", auth_util_module)
    monkeypatch.setitem(
        sys.modules,
        "streamlit.web.server.starlette.starlette_auth_routes",
        route_module,
    )

    install_streamlit_joserfc_auth_patch()

    response = FakeRedirectResponse("/")
    route_module._set_single_cookie(response, STREAMLIT_USER_COOKIE_NAME, "{}")

    assert response.cookies == [
        {
            "key": STREAMLIT_USER_COOKIE_NAME,
            "value": f"signed:{STREAMLIT_USER_COOKIE_NAME}:{{}}",
            "httponly": True,
            "secure": True,
            "samesite": "none",
            "path": "/",
        }
    ]


def test_streamlit_auth_callback_restores_missing_session_marker_from_state_cookie(
    monkeypatch,
) -> None:
    def old_encode_provider_token(provider: str) -> str:
        return provider

    def old_decode_provider_token(provider_token: str) -> dict[str, str]:
        return {"provider": provider_token}

    async def old_auth_callback(request: object, base_url: str) -> object:
        assert request.session["_state_default_returned-state"]["exp"] > 0
        return FakeRedirectResponse("/")

    def decode_signed_value(
        secret: str,
        name: str,
        value: str,
        max_age_days: float = 31,
    ) -> bytes | None:
        prefix = f"signed:{name}:"
        if not value.startswith(prefix):
            return None
        return value.removeprefix(prefix).encode("utf-8")

    streamlit_module = ModuleType("streamlit")
    streamlit_module.__path__ = []
    auth_util_module = ModuleType("streamlit.auth_util")
    route_module = ModuleType("streamlit.web.server.starlette.starlette_auth_routes")

    auth_util_module.encode_provider_token = old_encode_provider_token
    auth_util_module.decode_provider_token = old_decode_provider_token
    route_module._auth_callback = old_auth_callback
    route_module.decode_signed_value = decode_signed_value
    route_module.get_cookie_secret = lambda: "cookie-secret"
    route_module._get_cookie_path = lambda: "/"
    route_module._get_provider_by_state = (
        lambda state: "default" if state == "returned-state" else None
    )
    route_module._STARLETTE_AUTH_CACHE = FakeAuthCache(
        {"_state_default_returned-state": object()}
    )

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.auth_util", auth_util_module)
    monkeypatch.setitem(
        sys.modules,
        "streamlit.web.server.starlette.starlette_auth_routes",
        route_module,
    )

    install_streamlit_joserfc_auth_patch()

    state_payload = json.dumps(
        {"state": "returned-state"},
        ensure_ascii=True,
        separators=(",", ":"),
    )
    request = SimpleNamespace(
        query_params={"state": "returned-state", "code": "oauth-code"},
        session={},
        cookies={
            OAUTH_STATE_COOKIE_NAME: (
                f"signed:{OAUTH_STATE_COOKIE_NAME}:{state_payload}"
            )
        },
        url=SimpleNamespace(path="/oauth2callback"),
    )
    response = asyncio.run(route_module._auth_callback(request, "/"))

    assert response.status_code == 302
    assert response.deleted_cookies == [
        _deleted_cookie(OAUTH_STATE_COOKIE_NAME)
    ]


def test_streamlit_auth_callback_redirects_on_mismatching_state(monkeypatch) -> None:
    class MismatchingStateError(Exception):
        pass

    def old_encode_provider_token(provider: str) -> str:
        return provider

    def old_decode_provider_token(provider_token: str) -> dict[str, str]:
        return {"provider": provider_token}

    async def old_auth_callback(request: object, base_url: str) -> object:
        raise MismatchingStateError("mismatching_state")

    async def redirect_to_base(base_url: str) -> FakeRedirectResponse:
        return FakeRedirectResponse("/")

    streamlit_module = ModuleType("streamlit")
    streamlit_module.__path__ = []
    auth_util_module = ModuleType("streamlit.auth_util")
    route_module = ModuleType("streamlit.web.server.starlette.starlette_auth_routes")

    auth_util_module.encode_provider_token = old_encode_provider_token
    auth_util_module.decode_provider_token = old_decode_provider_token
    route_module._auth_callback = old_auth_callback
    route_module._redirect_to_base = redirect_to_base
    route_module._get_cookie_path = lambda: "/"

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.auth_util", auth_util_module)
    monkeypatch.setitem(
        sys.modules,
        "streamlit.web.server.starlette.starlette_auth_routes",
        route_module,
    )

    install_streamlit_joserfc_auth_patch()

    request = SimpleNamespace(
        query_params={"state": "returned-state", "code": "oauth-code"},
        session={},
        cookies={
            OAUTH_STATE_COOKIE_NAME: "stale",
            STREAMLIT_SESSION_COOKIE_NAME: "stale",
        },
        url=SimpleNamespace(path="/oauth2callback"),
    )
    response = asyncio.run(route_module._auth_callback(request, "/"))

    assert response.status_code == 302
    assert (
        response.headers["location"]
        == f"/?{LOGIN_ERROR_QUERY_PARAM}={LOGIN_ERROR_SESSION_EXPIRED}"
    )
    assert _deleted_cookie(OAUTH_STATE_COOKIE_NAME) in response.deleted_cookies
    assert _deleted_cookie(STREAMLIT_SESSION_COOKIE_NAME) in response.deleted_cookies


def test_streamlit_auth_callback_restores_missing_session_marker_from_xsrf_binding(
    monkeypatch,
) -> None:
    _OAUTH_STATE_BROWSER_BINDINGS.clear()

    def old_encode_provider_token(provider: str) -> str:
        return provider

    def old_decode_provider_token(provider_token: str) -> dict[str, str]:
        return {"provider": provider_token}

    async def old_auth_login(request: object, base_url: str) -> object:
        return FakeRedirectResponse(
            "https://accounts.google.com/o/oauth2/v2/auth"
            "?client_id=client&state=returned-state"
        )

    async def old_auth_callback(request: object, base_url: str) -> object:
        assert request.session["_state_default_returned-state"]["exp"] > 0
        return FakeRedirectResponse("/")

    streamlit_module = ModuleType("streamlit")
    streamlit_module.__path__ = []
    auth_util_module = ModuleType("streamlit.auth_util")
    route_module = ModuleType("streamlit.web.server.starlette.starlette_auth_routes")

    auth_util_module.encode_provider_token = old_encode_provider_token
    auth_util_module.decode_provider_token = old_decode_provider_token
    route_module._auth_login = old_auth_login
    route_module._auth_callback = old_auth_callback
    route_module.create_signed_value = (
        lambda secret, name, value: f"signed:{name}:{value}".encode("utf-8")
    )
    route_module.decode_signed_value = lambda *args, **kwargs: None
    route_module.get_cookie_secret = lambda: "cookie-secret"
    route_module._get_cookie_path = lambda: "/"
    route_module._get_provider_by_state = (
        lambda state: "default" if state == "returned-state" else None
    )
    route_module._STARLETTE_AUTH_CACHE = FakeAuthCache(
        {"_state_default_returned-state": object()}
    )

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.auth_util", auth_util_module)
    monkeypatch.setitem(
        sys.modules,
        "streamlit.web.server.starlette.starlette_auth_routes",
        route_module,
    )

    install_streamlit_joserfc_auth_patch()

    asyncio.run(
        route_module._auth_login(
            SimpleNamespace(cookies={STREAMLIT_XSRF_COOKIE_NAME: "xsrf-cookie"}),
            "/",
        )
    )
    request = SimpleNamespace(
        query_params={"state": "returned-state", "code": "oauth-code"},
        session={},
        cookies={STREAMLIT_XSRF_COOKIE_NAME: "xsrf-cookie"},
        url=SimpleNamespace(path="/oauth2callback"),
    )
    response = asyncio.run(route_module._auth_callback(request, "/"))

    assert response.status_code == 302
    assert "returned-state" not in _OAUTH_STATE_BROWSER_BINDINGS
