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
  - `https://glipmath.streamlit.app/oauth2callback`
  - if you deploy under another app slug, use that exact hostname instead

If the Streamlit Cloud URL changes, update the OAuth client accordingly.

## Streamlit Secrets Values

Put these values into `.streamlit/secrets.toml` locally and into the Streamlit Community Cloud secrets editor for deployment:

- `auth.redirect_uri`
- `auth.cookie_secret`
- `auth.client_id`
- `auth.client_secret`
- `auth.server_metadata_url`
- `auth.client_kwargs = { "scope" = "openid profile email", "prompt" = "select_account" }`

Even though `auth.redirect_uri`, `auth.client_id`, and `auth.server_metadata_url` are not confidential by themselves, Streamlit's built-in `st.login()` reads them from `[auth]` in `secrets.toml`, so they still need to stay there.

Google login needs the `email` scope for the app to receive `st.user.email`. Streamlit already defaults to `openid profile email`, but keeping the scope explicit in secrets avoids ambiguity when debugging authentication issues.

Important:

- local development should keep `auth.redirect_uri = http://localhost:8501/oauth2callback`
- Streamlit Community Cloud must use the deployed hostname, for example `https://glipmath.streamlit.app/oauth2callback`
- copying the local `localhost` value into Streamlit Cloud causes Google login to bounce back to `http://localhost:8501/oauth2callback`
- changing your local `.streamlit/secrets.toml` does not update the published app; you must edit the Streamlit Cloud secrets for the deployed environment

Recommended metadata URL for Google:

- `https://accounts.google.com/.well-known/openid-configuration`

## Beta Access Control

The MVP now resolves authorization from BigQuery `glipmath_core.user_access`.

The Google OAuth app still controls who can authenticate at all:

- OAuth app publishing status
- configured test users
- any domain or consent-screen restrictions you choose to apply

If the Google Auth app is still in `Testing`, every new learner or teacher email must also be added manually under `Google Auth Platform` > `Audience` > `Test users` before that person can log in.

After authentication, the app normalizes the email and looks up one active `user_access` row:

- students need `role = student` and one specific `cohort_key`
- teachers need `role = teacher` and `cohort_key = all`
- if there is no active row, the app shows the not-authorized screen

Important distinction:

- missing Google test-user access blocks login itself
- missing `user_access` rows blocks authorization after login
- missing `bigquery.tables.updateData` on `glipmath_core.user_access` blocks the in-app "Adicionar aluno" flow even when login is already working
