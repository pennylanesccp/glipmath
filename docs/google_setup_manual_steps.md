# Google Setup Manual Steps

This repository cannot finish the external Google setup automatically. A human must complete the steps below.

## 1. Create the Google Sheet

1. Create a new private Google Sheet.
2. Create exactly these worksheets:
   - `question_bank`
   - `whitelist`
   - `answers`
3. Copy the header rows from:
   - `data/templates/question_bank_template.csv`
   - `data/templates/whitelist_template.csv`
   - `data/templates/answers_template.csv`
4. Add your real question and whitelist data.

## 2. Create a Google Cloud Project

1. Open Google Cloud Console.
2. Create a dedicated project for GlipMath.
3. Enable billing only if your organization requires it for API usage.

## 3. Enable Required APIs

Enable at least:

- Google Sheets API
- Google Drive API

The Drive API is useful because service-account access to the spreadsheet depends on Drive permissions.

## 4. Create a Service Account

1. In the Google Cloud project, create a service account for the app.
2. Generate a JSON key.
3. Keep that JSON private.
4. Copy the JSON fields into the `[gcp_service_account]` section of `.streamlit/secrets.toml`.

## 5. Share the Sheet with the Service Account

1. Copy the service account email address from the JSON key.
2. Open the Google Sheet.
3. Share the sheet with that service account email.
4. Grant editor access so the app can append answer rows.

Without this step, reads and writes will fail even if the credentials are otherwise valid.

## 6. Configure Google OAuth / OIDC for Streamlit Login

1. In Google Cloud Console, configure the OAuth consent screen.
2. Create OAuth client credentials for a web application.
3. Add redirect URIs for:
   - local development, for example `http://localhost:8501/oauth2callback`
   - your Streamlit Community Cloud deployed URL, for example `https://YOUR-APP.streamlit.app/oauth2callback`
4. Copy the client ID and client secret.
5. Put them into the `[auth]` section of `.streamlit/secrets.toml`.
6. Keep `server_metadata_url` pointed at Google's OpenID configuration:
   - `https://accounts.google.com/.well-known/openid-configuration`

## 7. Fill Streamlit Secrets

Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example` and fill:

- `[app]`
- `[google_sheet]`
- `[worksheets]`
- `[auth]`
- `[gcp_service_account]`

Minimum fields to review carefully:

- `storage_backend`
- `spreadsheet_id` or `spreadsheet_url`
- `timezone`
- `cookie_secret`
- `client_id`
- `client_secret`
- all service account fields

## 8. Validate Locally

1. Install dependencies.
2. Run `python scripts/validate_question_bank.py`.
3. Run the app with `.\run_streamlit.ps1`.
4. Confirm:
   - login works
   - a whitelisted account is authorized
   - a non-whitelisted account is denied
   - answers append to the `answers` worksheet

## 9. Deploy the App

1. Push the repository to GitHub.
2. Create the app in Streamlit Community Cloud.
3. Set the entrypoint to `app/streamlit_app.py`.
4. Add the same secrets in the Streamlit Cloud secrets manager.
5. Redeploy after setting the production redirect URI in Google Cloud.
