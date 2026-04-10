from __future__ import annotations

import streamlit as st


def render_auth_setup_warning() -> None:
    """Render a setup warning when auth configuration is missing."""

    st.warning(
        "A autenticação Google ainda não está configurada. "
        "Preencha `.streamlit/secrets.toml` com a seção `[auth]` localmente "
        "ou configure a mesma seção de segredos no Streamlit Community Cloud."
    )


def render_auth_redirect_warning(
    *,
    current_redirect_uri: str | None,
    expected_redirect_uri: str | None,
) -> None:
    """Render a warning when the deployed app points OAuth back to the wrong host."""

    st.error("O login Google está apontando para um callback diferente da URL publicada do app.")
    st.write(
        "No Streamlit Community Cloud, `auth.redirect_uri` precisa usar o domínio atual do app "
        "e terminar com `/oauth2callback`."
    )
    if current_redirect_uri:
        st.caption(f"redirect_uri atual: {current_redirect_uri}")
    if expected_redirect_uri:
        st.caption(f"redirect_uri esperado aqui: {expected_redirect_uri}")
    st.write(
        "Esse valor vem da seção `[auth]` nas secrets do ambiente ativo. "
        "Trocar o arquivo local não altera o app publicado: atualize os segredos do Streamlit Cloud "
        "e confirme a mesma URL em `Authorized redirect URIs` no cliente OAuth do Google."
    )


def render_access_message(email: str | None) -> None:
    """Render a generic access issue state."""

    st.error("Não foi possível concluir o acesso.")
    if email:
        st.write(
            "O beta usa a configuração do Google OAuth para controlar quem pode entrar. "
            "Se o login funcionou, mas o app não conseguiu continuar, confirme se existe "
            "uma linha ativa para esse e-mail em `glipmath_core.user_access`."
        )
        st.caption(f"E-mail detectado: {email}")
        return

    st.write(
        "O login aconteceu, mas o provedor não devolveu um e-mail utilizável para o app. "
        "Confirme se o OAuth está pedindo os escopos `openid profile email` e, se o app "
        "ainda estiver em modo de teste, adicione a conta em `Audience` > `Test users` "
        "no Google Auth Platform."
    )
