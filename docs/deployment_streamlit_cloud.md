# Deployment on Streamlit Community Cloud

## Deployment Target

The primary deployment target for the MVP is Streamlit Community Cloud.

## Prerequisites

- the GCP data layer has been applied with Terraform
- the runtime service account exists and you have created a JSON key for it manually
- Google OAuth is configured with the Streamlit Cloud redirect URI
- the question bank has been loaded into BigQuery
- `glipmath_core.user_access` has active rows for the users who should be allowed in

## Streamlit Community Cloud Steps

1. Push the repository to GitHub.
2. Create a new app in Streamlit Community Cloud.
3. Point the app to `app/streamlit_app.py`.
4. Set Python version compatibility if needed through the repo metadata.
5. Paste the secrets payload into the Streamlit Cloud secrets editor.
6. Set `auth.redirect_uri` to the deployed hostname callback, for example `https://glipmath.streamlit.app/oauth2callback`, instead of the local `localhost` value.
7. Confirm the same published callback URL is registered in the Google OAuth client's `Authorized redirect URIs`.
8. Remember that editing the local `.streamlit/secrets.toml` file does not change the deployed app; the Streamlit Cloud secrets editor is a separate environment.

## Secrets Structure

The checked-in public defaults live in `glipmath.toml`.
The secrets payload should match `.streamlit/secrets.toml.example`:

- `[auth]`
- `[ai]`
- `[gcp_service_account]`

The values are not identical across environments:

- local development should keep `auth.redirect_uri = http://localhost:8501/oauth2callback`
- Streamlit Community Cloud must use the deployed app URL, for example `https://glipmath.streamlit.app/oauth2callback`
- `auth.redirect_uri`, `auth.client_id`, and `auth.server_metadata_url` are public in practice, but Streamlit auth still requires them under `[auth]` in secrets

## Runtime Notes

- the app starts with the normal Streamlit entrypoint
- `app/streamlit_app.py` bootstraps the repository root on `sys.path` so absolute imports like `app.*` and `modules.*` work in Streamlit Community Cloud
- no container startup script is required
- no local filesystem persistence is used
- BigQuery access uses the service account JSON stored in Streamlit secrets
- when `[gcp_service_account]` is missing, the app now fails fast with a configuration error instead of falling back to metadata-based ADC lookup

## Verification Checklist

- login page loads
- Google login succeeds
- one question renders with randomized alternatives
- submitting an answer writes one row to `glipmath_events.answers`
- day streak, question streak, and leaderboard position render without errors
- cohort-scoped users only see their own question cohort
