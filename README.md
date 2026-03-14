# GlipMath

GlipMath is a Streamlit-based math learning MVP with a light Duolingo-like loop:

- Google login
- whitelist-based authorization
- one question at a time
- append-only answer logging
- day streak
- question streak
- leaderboard position

This repository is GCP-first from day one:

- Python 3.11+
- Streamlit
- BigQuery for persistence
- Cloud Run for deployment
- Secret Manager for auth/runtime secrets
- Terraform for infrastructure

The UI is intentionally simple and user-facing text is in Portuguese-BR. Code, SQL, and docs stay in English.

## MVP Scope

The MVP has only two logical screens:

1. Login
2. Main app

The main page shows:

- app title
- logged-in user
- logout button
- day streak
- question streak
- leaderboard position
- one question card
- answer submission
- result feedback
- next question button

More detail is in [docs/mvp_scope.md](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/docs/mvp_scope.md).

## Repository Map

```text
glipmath/
|- .streamlit/
|- app/
|- modules/
|- infrastructure/terraform/
|- sql/
|- scripts/
|- docs/
|- tests/
|- Dockerfile
|- README.md
|- requirements.txt
|- pyproject.toml
```

## Architecture Summary

- `app/` keeps Streamlit pages, components, and session state thin.
- `modules/services/` owns deterministic business rules.
- `modules/storage/` centralizes BigQuery access.
- `modules/domain/` defines typed domain models.
- `infrastructure/terraform/` provisions GCP resources with reusable modules.
- `sql/views/` defines analytics views used by Terraform.
- `scripts/` handles CSV validation and BigQuery seed flows.

See [docs/architecture.md](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/docs/architecture.md).

## BigQuery Data Model

Datasets:

- `glipmath_core`
- `glipmath_events`
- `glipmath_analytics`

Main business tables:

- `glipmath_core.question_bank`
- `glipmath_core.whitelist`
- `glipmath_events.answers`

Analytics views:

- `glipmath_analytics.v_user_totals`
- `glipmath_analytics.v_user_daily_activity`
- `glipmath_analytics.v_leaderboard`

See [docs/data_model.md](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/docs/data_model.md).

## Local Setup

1. Create a Python 3.11+ virtual environment.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy the example secrets file:

   ```powershell
   Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

4. Fill the Google OIDC values in `.streamlit/secrets.toml`.
5. Authenticate locally for BigQuery access:

   ```powershell
   gcloud auth application-default login
   ```

6. Create the BigQuery datasets and tables with Terraform.
7. Load seed CSVs into BigQuery with the scripts in `scripts/`.
8. Run the app:

   ```powershell
   .\run_streamlit.ps1
   ```

## GCP Setup Summary

- Project ID: `ide-math-app`
- Recommended default region: `southamerica-east1`
- Terraform provisions BigQuery, Secret Manager, Artifact Registry, Cloud Run, service accounts, and a GCS bucket.
- OAuth consent and Google OIDC client creation still require manual setup.
- Secret values must be inserted manually before the final Cloud Run apply.

See:

- [docs/terraform_infra.md](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/docs/terraform_infra.md)
- [docs/google_auth_setup.md](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/docs/google_auth_setup.md)
- [docs/manual_bootstrap_steps.md](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/docs/manual_bootstrap_steps.md)

## Terraform Summary

Terraform is organized as:

- reusable modules under `infrastructure/terraform/modules/`
- a `dev` environment under `infrastructure/terraform/environments/dev/`
- version-controlled BigQuery schemas under `infrastructure/terraform/schemas/`

The recommended flow is two-stage:

1. Apply infra with `deploy_cloud_run = false`
2. Populate Secret Manager values, build and push the image, then set `deploy_cloud_run = true`

## Cloud Run Deployment Flow

1. Build the Docker image.
2. Push it to Artifact Registry.
3. Ensure auth secrets exist and contain real values.
4. Update `container_image` in `terraform.tfvars`.
5. Apply Terraform with `deploy_cloud_run = true`.
6. Verify `/oauth2callback` is registered in the Google OAuth client.

See [docs/deployment_cloud_run.md](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/docs/deployment_cloud_run.md).

## Auth Flow

Runtime flow:

1. `st.login()` starts Google OIDC.
2. Streamlit exposes the authenticated identity in `st.user`.
3. Email is normalized with lowercase and trim.
4. Authorization checks BigQuery `whitelist`.
5. Only active whitelisted users can access the main page.
6. Non-whitelisted users see a friendly denial state.
7. `st.logout()` ends the session.

Cloud Run receives auth config through Secret Manager-backed environment variables. A bootstrap script writes `.streamlit/secrets.toml` inside the container so Streamlit auth can initialize normally.

## Seed and Admin Flow

There is no admin UI in the MVP.

Use:

- `python scripts/validate_question_bank.py`
- `python scripts/load_question_bank_to_bigquery.py`
- `python scripts/load_whitelist_to_bigquery.py`
- `python scripts/backfill_local_dev_data.py`

Source CSV templates live in:

- [sql/seeds/question_bank_template.csv](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/sql/seeds/question_bank_template.csv)
- [sql/seeds/whitelist_template.csv](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/sql/seeds/whitelist_template.csv)

## Testing

Run unit tests with:

```powershell
python -m pytest
```

The test suite avoids real GCP calls and covers:

- question validation
- authorization by normalized email
- day streak
- question streak
- leaderboard ranking
- normalization helpers

## Known Limitations

- Answer writes use BigQuery streaming inserts for simplicity.
- Question streak is computed in Python from the current user history, not in SQL.
- The app assumes a single global leaderboard.
- There is no admin UI for editing questions or whitelist data.
- Terraform creates Secret Manager placeholders, but secret values must still be added manually.

## Next Steps

- Add a small admin workflow for question curation.
- Add richer analytics beyond total-correct ranking.
- Cache leaderboard/user history reads if traffic grows.
- Add cohort or class segmentation.
- Add richer explanation content and remediation flows.
