# GlipMath

GlipMath is a Streamlit-based math learning MVP with a light gamification loop:

- Google login
- one question at a time
- append-only answer logging in BigQuery
- day streak
- question streak
- leaderboard position

The current deployment target is Streamlit Community Cloud. GCP is used for the data layer only.

## MVP Direction

- App deployment: Streamlit Community Cloud
- Primary data store: BigQuery
- Infrastructure as code: Terraform for BigQuery, IAM, and the runtime service account
- Runtime secrets: Streamlit secrets locally and in Streamlit Community Cloud
- Beta access control: externalized through Google OAuth app configuration and test users

There is no Docker, Cloud Run, Artifact Registry, Secret Manager runtime flow, or in-app whitelist table in the current MVP.

## Repository Map

```text
glipmath/
|- .streamlit/
|- app/
|- data/
|- modules/
|- infrastructure/terraform/
|- sql/
|- scripts/
|- docs/
|- tests/
|- README.md
|- requirements.txt
|- pyproject.toml
|- run_streamlit.ps1
```

## Architecture Summary

- `app/` keeps Streamlit pages, components, and session state thin.
- `modules/ai/` owns offline Gemini integration for question-bank enrichment only.
- `modules/services/` owns question selection, answer evaluation, streaks, and leaderboard logic.
- `modules/storage/` is the only place that talks to BigQuery.
- `modules/domain/` defines typed app models.
- `infrastructure/terraform/` manages the GCP data layer only.
- `sql/views/` contains the analytics SQL used by Terraform.
- `scripts/` handles question validation, question loading, and optional local/dev answer backfill.

More detail:

- `docs/architecture.md`
- `docs/data_model.md`
- `docs/mvp_scope.md`

## BigQuery Data Model

Datasets:

- `glipmath_core`
- `glipmath_events`
- `glipmath_analytics`

Primary tables:

- `glipmath_core.question_bank`
- `glipmath_events.answers`

Analytics views:

- `glipmath_analytics.v_user_totals`
- `glipmath_analytics.v_user_daily_activity`
- `glipmath_analytics.v_leaderboard`

`question_bank` uses a nested schema:

- `correct_answer` is a struct with `alternative_text` and `explanation`
- `wrong_answers` is a repeated struct array with the same shape
- `subject` stores the broad discipline so the same bank can hold math and non-math questions

The app combines the correct answer and wrong answers in memory, assigns stable runtime option IDs, randomizes display order, and persists both the selected alternative text and the canonical correct alternative text.

## Local Setup

1. Create a Python 3.11+ virtual environment.
2. Install dependencies:

   ```powershell
   python -m pip install -e .
   ```

   Optional extras:

   ```powershell
   python -m pip install -e .[dev]
   python -m pip install -e .[admin]
   ```

3. Copy the example secrets file:

   ```powershell
   Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

4. Fill these sections in `.streamlit/secrets.toml`:
   - `[auth]` for Google OIDC
   - `[gcp]` for project/location
   - `[bigquery]` for dataset/table/view names
   - `[ai]` for optional Gemini enrichment scripts
   - `[gcp_service_account]` for the BigQuery runtime service account JSON fields
5. Apply Terraform for the GCP data layer.
6. Place supported raw question files under `data/`.
7. Validate and load the question bank:

   ```powershell
   python scripts/validate_question_bank.py --input-path data
   python scripts/load_question_bank_to_bigquery.py --input-path data
   ```

8. Run the app:

   ```powershell
   .\run_streamlit.ps1
   ```

## Streamlit Community Cloud Deployment

The production path is Streamlit Community Cloud.

1. Push the repository to GitHub.
2. Create the app in Streamlit Community Cloud.
3. Set the entrypoint to `app/streamlit_app.py`.
4. Paste the same secrets structure used locally into the Streamlit Cloud secrets editor.
5. Ensure the OAuth redirect URI for the Streamlit Cloud hostname is registered in Google OAuth.
6. Redeploy and test login, question loading, answer inserts, and leaderboard reads.

See `docs/deployment_streamlit_cloud.md`.

## Authentication and Access Control

Runtime flow:

1. `st.login()` starts Google OIDC.
2. Streamlit exposes the authenticated identity in `st.user`.
3. The app normalizes the email.
4. A lightweight authorization abstraction converts the identity into the current app user.
5. Beta access is controlled outside the app through Google OAuth configuration and test users.
6. `st.logout()` ends the session.

There is no BigQuery-backed whitelist in the MVP. The abstraction remains in place so internal authorization rules can be reintroduced later without rewriting the UI.

See `docs/google_auth_setup.md`.

## Seed and Admin Flow

There is no admin UI in the MVP.

Use:

- `python scripts/validate_question_bank.py --input-path data`
- `python scripts/load_question_bank_to_bigquery.py --input-path data`
- `python scripts/enrich_question_explanations.py --dry-run --limit 10`
- `python scripts/backfill_local_dev_data.py --user-email ana@example.com`

Supported question inputs:

- `data/*.csv` in the vestibulinho flat-question format
- `sql/seeds/question_bank_template.jsonl`

The pipeline converts supported raw files into the canonical nested question-bank rows in memory, then validates and loads them.

For the current vestibulinho CSV pipeline, `id_question` is derived deterministically from `source` plus `question_number`.

The load script skips invalid rows, writes them to `trash/question_bank_failed_rows.csv` by default, and still loads the valid subset into BigQuery. Use `--failed-rows-output` to override that path.

The question bank loader replaces the current contents of `glipmath_core.question_bank`.

## Gemini Enrichment

Gemini is used only for offline/admin enrichment of question explanations.

- The student-facing app reads explanations from BigQuery and does not call Gemini per answer.
- Missing explanations do not block the learner flow.
- Gemini credentials live in Streamlit secrets under `[ai]`, not in code.
- The recommended workflow is to enrich only rows with missing explanations and run that as a manual backfill step.

Useful command:

```powershell
python -m pip install -e .[admin]
python scripts/enrich_question_explanations.py --dry-run --limit 10
```

See `docs/gemini_enrichment.md`.

## Terraform Summary

Terraform manages only the GCP resources still needed:

- required Google APIs for BigQuery and IAM
- one service account for Streamlit runtime access to BigQuery
- BigQuery datasets
- BigQuery tables
- BigQuery analytics views
- least-privilege IAM bindings

See:

- `docs/terraform_infra.md`
- `docs/manual_bootstrap_steps.md`

## Testing

Run unit tests with:

```powershell
python -m pip install -e .[dev]
python -m pytest
```

The test suite avoids real GCP calls and covers:

- raw question import from the `data/` pipeline
- nested question parsing and validation
- Gemini prompt building and explanation response parsing
- alternative randomization
- answer correctness evaluation
- day streak
- question streak
- leaderboard ranking
- email normalization and authorization entry

## Known Limitations

- Answer writes use BigQuery streaming inserts for MVP simplicity.
- Gemini enrichment is an offline/admin workflow, not part of the student answer path.
- Leaderboard membership is based on users who have at least one answer event.
- Question streak is computed in Python from user history, not in SQL.
- The app assumes a single global leaderboard.
- There is no admin UI for content management.
- Service account keys are not created by Terraform because that would put sensitive material in state.

## Next Steps

- Add richer explanation and remediation flows.
- Add cohort/class filtering for the leaderboard.
- Add a small admin workflow for question curation.
- Add CI for Terraform validation and tests.
- Reintroduce in-app authorization only when beta access needs move beyond Google OAuth test users.
