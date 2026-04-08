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
- Access control: Google OIDC for authentication plus BigQuery `user_access` for authorization

There is no Docker, Cloud Run, Artifact Registry, or Secret Manager runtime flow in the current MVP.

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
|- run_terraform.ps1
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
- `glipmath_core.user_access`
- `glipmath_events.answers`

Analytics views:

- `glipmath_analytics.v_user_totals`
- `glipmath_analytics.v_user_daily_activity`
- `glipmath_analytics.v_leaderboard`

`question_bank` uses a nested schema:

- `correct_answer` is a struct with `alternative_text` and `explanation`
- `wrong_answers` is a repeated struct array with the same shape
- `subject` stores the broad discipline so the same bank can hold math and non-math questions
- `cohort_key` stores which cohort or project owns the question, for example `etec`, `enem`, `ano_1`, `ano_2`, or `ano_3`

`user_access` resolves app access from authenticated email:

- `role` is `student` or `teacher`
- `cohort_key` is one specific cohort for students
- teachers use `cohort_key = all`
- the learner never chooses cohort manually in the UI

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

4. Review the public defaults in `glipmath.toml`.
   This file is versioned and holds non-sensitive app, GCP, BigQuery, and Gemini model settings.

5. Fill these sections in `.streamlit/secrets.toml`:
   - `[auth]` for Google OIDC
   - `[ai]` for the optional Gemini API key
   - `[gcp_service_account]` for the BigQuery runtime service account JSON fields
6. Apply Terraform for the GCP data layer.
   Recommended:

   ```powershell
   .\run_terraform.ps1 -Command plan
   .\run_terraform.ps1
   ```

7. Populate `glipmath_core.user_access` with one active row per authorized user.
   Students get one specific cohort, for example `ano_1`.
   Teachers get `role = teacher` and `cohort_key = all`.
8. Place supported raw question files under `data/`.
9. Validate and load the question bank:

   ```powershell
   python scripts/validate_question_bank.py --input-path data --cohort-key ano_1
   python scripts/load_question_bank_to_bigquery.py --input-path data --cohort-key ano_1
   ```

10. Run the app:

   ```powershell
   .\run_streamlit.ps1
   ```

## Streamlit Community Cloud Deployment

The production path is Streamlit Community Cloud.

1. Push the repository to GitHub.
2. Create the app in Streamlit Community Cloud.
3. Set the entrypoint to `app/streamlit_app.py`.
4. Paste the same secrets sections used locally into the Streamlit Cloud secrets editor, but change `auth.redirect_uri` to the deployed hostname instead of the local `localhost` callback.
5. For the published app, set `auth.redirect_uri` to `https://glipmath.streamlit.app/oauth2callback`.
6. Paste a valid `[gcp_service_account]` block into the Streamlit Cloud secrets editor as well.
7. Ensure the same redirect URI is registered in Google OAuth.
8. Redeploy and test login, question loading, answer inserts, and leaderboard reads.

`auth.redirect_uri`, `auth.client_id`, and `auth.server_metadata_url` are public values in practice, but Streamlit's built-in `st.login()` still requires them under `[auth]` in `secrets.toml`.
On Streamlit Community Cloud, BigQuery cannot rely on metadata-server Application Default Credentials, so the deployed app also needs explicit service-account credentials in secrets.

See `docs/deployment_streamlit_cloud.md`.

## Authentication and Access Control

Runtime flow:

1. `st.login()` starts Google OIDC.
2. Streamlit exposes the authenticated identity in `st.user`.
3. The app normalizes the email.
4. The app looks up the normalized email in BigQuery `glipmath_core.user_access`.
5. If there is no active row, the not-authorized page is shown.
6. If there is an active row, the app builds a user with explicit `role` and `cohort_key`.
7. `st.logout()` ends the session.

Question and leaderboard scope come from that access row:

- students only see active questions whose `question_bank.cohort_key` matches their `cohort_key`
- teachers can see all active questions
- students see leaderboard ranking only against students in the same `cohort_key`
- teachers keep the global leaderboard

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

The pipeline converts supported raw files into the canonical nested question-bank rows in memory, then validates and loads them. Both raw CSV and canonical JSONL may carry optional `cohort_key`, and the CLI can stamp a whole import batch with `--cohort-key`.

For the vestibulinho CSV pipeline, `id_question` is derived deterministically from `source`, `question_number`, and `cohort_key` when cohort scope is present.

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

To preview the static HTML screens without live actions:

```powershell
.\venv\Scripts\streamlit.exe run .\tests\preview_html_pages.py
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
- cohort-scoped question and leaderboard access

## Known Limitations

- Answer writes use BigQuery streaming inserts for MVP simplicity.
- Gemini enrichment is an offline/admin workflow, not part of the student answer path.
- Leaderboard membership is based on users who have at least one answer event.
- Question streak is computed in Python from user history, not in SQL.
- There is no admin UI for content management.
- Service account keys are not created by Terraform because that would put sensitive material in state.

## Next Steps

- Add richer explanation and remediation flows.
- Add a small admin workflow for question curation.
- Add CI for Terraform validation and tests.
- Add operational tooling to manage `user_access` rows safely.
