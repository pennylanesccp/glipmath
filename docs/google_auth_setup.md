# Google Auth Setup

GlipMath uses Google OIDC through Streamlit auth.

## What Terraform Does Not Create

Terraform does not create the Google OAuth consent screen or OAuth client. Those still need to be configured manually in Google Cloud Console.

## Recommended Setup

1. Configure the OAuth consent screen for the project.
2. Create a Web application OAuth client.
3. Add redirect URIs for each environment.
4. Add beta users as OAuth test users if the app is still in testing mode.

## Redirect URIs

- Local:
  - `http://localhost:8501/oauth2callback`
- Streamlit Community Cloud:
  - `https://<your-streamlit-app-name>.streamlit.app/oauth2callback`

If the Streamlit Cloud URL changes, update the OAuth client accordingly.

## Streamlit Secrets Values

Put these values into `.streamlit/secrets.toml` locally and into the Streamlit Community Cloud secrets editor for deployment:

- `auth.redirect_uri`
- `auth.cookie_secret`
- `auth.client_id`
- `auth.client_secret`
- `auth.server_metadata_url`

Recommended metadata URL for Google:

- `https://accounts.google.com/.well-known/openid-configuration`

## Beta Access Control

The MVP now resolves authorization from BigQuery `glipmath_core.user_access`.

The Google OAuth app still controls who can authenticate at all:

- OAuth app publishing status
- configured test users
- any domain or consent-screen restrictions you choose to apply

After authentication, the app normalizes the email and looks up one active `user_access` row:

- students need `role = student` and one specific `cohort_key`
- teachers need `role = teacher` and `cohort_key = all`
- if there is no active row, the app shows the not-authorized screen
