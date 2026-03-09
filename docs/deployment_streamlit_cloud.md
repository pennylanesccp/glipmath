# Deployment to Streamlit Community Cloud

## Prerequisites

Before deploying, make sure you already have:

- a GitHub repository with this code
- a private Google Sheet with the required worksheets
- a Google service account with editor access to the sheet
- Google OAuth / OIDC credentials configured for the final app URL
- Streamlit secrets ready to paste

## Deployment Steps

1. Push the repository to GitHub.
2. Sign in to Streamlit Community Cloud.
3. Create a new app.
4. Select the repository and branch.
5. Set the main file path to:

   ```text
   app/streamlit_app.py
   ```

6. Open the app's secrets manager.
7. Paste the contents of your completed `.streamlit/secrets.toml`.
8. Deploy the app.

## Post-Deploy Checks

After the first deployment, verify:

- the login screen loads
- Google sign-in redirects back correctly
- an authorized email reaches the main page
- a non-whitelisted email sees the access-denied screen
- question data loads
- submitting an answer appends a new row to `answers`

## Common Failure Modes

### Login fails or redirects incorrectly

Check:

- the redirect URI in Google Cloud
- the deployed app URL
- the `[auth]` section in Streamlit secrets

### Google Sheets access fails

Check:

- `spreadsheet_id` or `spreadsheet_url`
- service account fields in secrets
- that the sheet is shared with the service account email
- that the required APIs are enabled

### App loads but no user can enter

Check:

- `whitelist` worksheet exists
- emails are normalized correctly
- the user row is active

## Recommended Launch Checklist

- validate worksheet headers
- test one whitelisted account
- test one denied account
- verify answer timestamps and IDs
- verify leaderboard population rule matches expectations
