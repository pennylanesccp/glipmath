from __future__ import annotations

import streamlit as st

from modules.domain.models import AuthIdentity
from modules.utils.normalization import normalize_email


def get_authenticated_identity() -> AuthIdentity | None:
    """Return the current authenticated identity from Streamlit."""

    if not getattr(st.user, "is_logged_in", False):
        return None

    email = normalize_email(_user_attribute("email"))
    if not email:
        return None
    name = _user_attribute("name")
    return AuthIdentity(email=email, name=name)


def trigger_login() -> None:
    """Start the Streamlit login flow."""

    st.login()


def trigger_logout() -> None:
    """End the current Streamlit session."""

    st.logout()


def _user_attribute(attribute_name: str) -> str | None:
    value = getattr(st.user, attribute_name, None)
    if value:
        return str(value)

    getter = getattr(st.user, "get", None)
    if callable(getter):
        mapped_value = getter(attribute_name)
        if mapped_value:
            return str(mapped_value)

    if isinstance(st.user, dict):
        mapped_value = st.user.get(attribute_name)
        if mapped_value:
            return str(mapped_value)
    return None
