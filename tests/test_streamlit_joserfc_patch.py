from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace

from modules.auth.streamlit_joserfc_patch import (
    decode_provider_token,
    encode_provider_token,
    install_streamlit_joserfc_auth_patch,
)


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
