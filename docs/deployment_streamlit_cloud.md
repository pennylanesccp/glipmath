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

## Secrets Structure

The secrets structure should match `.streamlit/secrets.toml.example`:

- `[app]`
- `[gcp]`
- `[bigquery]`
- `[auth]`
- `[gcp_service_account]`

## Runtime Notes

- the app starts with the normal Streamlit entrypoint
- no container startup script is required
- no local filesystem persistence is used
- BigQuery access uses the service account JSON stored in Streamlit secrets

## Verification Checklist

- login page loads
- Google login succeeds
- one question renders with randomized alternatives
- submitting an answer writes one row to `glipmath_events.answers`
- day streak, question streak, and leaderboard position render without errors
- cohort-scoped users only see their own question cohort
