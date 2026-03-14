# Google Auth Setup

## What Terraform Does Not Fully Automate

This repository does not attempt to fully automate Google OAuth consent and OIDC client configuration.

You still need to configure:

- OAuth consent screen
- OAuth client ID and secret
- authorized redirect URIs

## Recommended OAuth Client

Create a Web application OAuth client in the same GCP project:

- project: `ide-math-app`

## Redirect URIs

Recommended URIs:

- local: `http://localhost:8501/oauth2callback`
- Cloud Run: `https://<your-cloud-run-url>/oauth2callback`

If the Cloud Run URL changes, update the OAuth client and the corresponding Secret Manager value.

## Required OIDC Values

The app expects:

- `redirect_uri`
- `cookie_secret`
- `client_id`
- `client_secret`
- `server_metadata_url`

For Google, the metadata URL is:

`https://accounts.google.com/.well-known/openid-configuration`

## Where Values Go

### Local development

Put them in `.streamlit/secrets.toml` using `.streamlit/secrets.toml.example` as the template.

### Cloud Run

Populate Secret Manager secrets created by Terraform:

- `glipmath-auth-cookie-secret`
- `glipmath-auth-client-id`
- `glipmath-auth-client-secret`
- `glipmath-auth-redirect-uri`
- `glipmath-auth-server-metadata-url`

Cloud Run injects them as env vars and the bootstrap script converts them into a Streamlit secrets file at container start.

## Cookie Secret Guidance

Use a long random value. Treat it as sensitive.

Do not commit it to the repository.
