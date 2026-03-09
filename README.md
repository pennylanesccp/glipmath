# GlipMath

GlipMath is a Streamlit-based educational MVP for students solving multiple-choice math questions with a small layer of gamification.

The project is intentionally simple and production-minded:

- Google OIDC login through Streamlit
- whitelist-based authorization
- Google Sheets as the production persistence layer
- one question at a time
- append-only answer logging
- day streak, question streak, and leaderboard position

User-facing texts are in Portuguese-BR. Internal code and documentation are in English.

## MVP Scope

This repository covers:

- login screen for unauthenticated users
- friendly access-denied state for authenticated but non-whitelisted users
- main app screen for authorized users
- answer event logging to the `answers` worksheet
- streak and leaderboard calculations from historical answers
- local CSV development mode for storage-only workflows

Out of scope for this version:

- teacher/admin panels
- question authoring UI
- adaptive sequencing
- analytics dashboards
- non-Google authentication

See [docs/mvp_scope.md](docs/mvp_scope.md) for the compact scope summary.

## Architecture Summary

The repository follows a library-first structure:

- `app/`: Streamlit UI composition, logical pages, and session state
- `modules/`: domain models, services, auth, storage, config, and utilities
- `scripts/`: validation and local utility scripts
- `docs/`: setup, architecture, deployment, and data model documentation
- `tests/`: pure logic tests with no network calls
- `data/templates/`: worksheet templates and sample CSV artifacts

Core boundaries:

- page files orchestrate UI only
- services hold business rules
- storage modules handle Google Sheets and CSV I/O
- domain models define typed app data

See [docs/architecture.md](docs/architecture.md) for details.

## Repository Map

```text
glipmath/
|- .streamlit/
|- app/
|- modules/
|- data/
|- docs/
|- scripts/
|- tests/
|- AGENTS.md
|- README.md
|- pyproject.toml
|- requirements.txt
|- run_streamlit.ps1
```

## Data Model

The production spreadsheet must contain three worksheets:

- `question_bank`
- `whitelist`
- `answers`

Implemented rules:

- questions support 4 or 5 alternatives
- inactive questions are ignored
- malformed active question rows are skipped and surfaced as diagnostics
- duplicate IDs are treated as blocking validation errors
- authorization is based on normalized email from `whitelist`
- `answers` is append-only
- empty `answers` history is supported

Selection and ranking rules used by this MVP:

- question delivery: unseen active questions first, then random among all active valid questions
- leaderboard denominator: all active whitelisted users
- leaderboard ordering: `total_correct DESC`, `total_answers DESC`, `email ASC`
- day streak: consecutive local calendar days ending on today or yesterday
- question streak: current consecutive correct answers in reverse chronological order

See [docs/data_model.md](docs/data_model.md) for the full schema.

## Local Setup

1. Create a virtual environment with Python 3.11+.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy the example secrets file and fill it:

   ```powershell
   Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

4. Choose a storage mode in `.streamlit/secrets.toml`:
   - production-like: `storage_backend = "google_sheets"`
   - local storage-only development: `storage_backend = "csv"`

5. Optional: seed local CSV files for storage development mode:

   ```powershell
   python scripts/seed_local_csv_examples.py
   ```

6. Run the app:

   ```powershell
   .\run_streamlit.ps1
   ```

## Authentication

The app uses Streamlit OIDC authentication with the Google provider.

Expected runtime flow:

1. `st.login()` starts Google authentication.
2. `st.user` exposes the logged-in identity.
3. The email is normalized to lowercase and stripped.
4. The normalized email is matched against the `whitelist` worksheet.
5. Only active whitelist entries are allowed into the main page.
6. `st.logout()` ends the session.

Required OIDC values are documented in `.streamlit/secrets.toml.example`.

## Google Sheets Storage

Production persistence is intentionally simple:

- `question_bank` stores source questions
- `whitelist` stores authorized users
- `answers` stores append-only answer events

The app does not depend on SQLite for production. Google Sheets access is centralized under `modules/storage/`.

For local development without Sheets writes, a CSV storage backend is included. It mirrors worksheet names as:

- `data/local_dev/question_bank.csv`
- `data/local_dev/whitelist.csv`
- `data/local_dev/answers.csv`

## Validation and Utility Scripts

- `python scripts/validate_question_bank.py`
- `python scripts/seed_local_csv_examples.py`
- `python scripts/inspect_answers.py`

## Testing

Run focused unit tests with:

```powershell
python -m pytest
```

Tests cover:

- question validation and selection
- authorization via normalized email
- day streak and question streak calculations
- leaderboard ranking
- normalization helpers

## Deployment on Streamlit Community Cloud

High-level deployment flow:

1. Push this repository to GitHub.
2. Create the Google Sheet and service account.
3. Configure Google OAuth / OIDC.
4. Add secrets in Streamlit Community Cloud.
5. Deploy `app/streamlit_app.py`.

Detailed guides:

- [docs/google_setup_manual_steps.md](docs/google_setup_manual_steps.md)
- [docs/deployment_streamlit_cloud.md](docs/deployment_streamlit_cloud.md)

## Known Limitations

- Google Sheets is suitable for MVP scale, not heavy concurrency.
- `id_answer` is generated from the current max answer ID, which is acceptable for small-scale MVP traffic but not ideal for high write contention.
- The app intentionally has no admin panel for managing users or questions.
- The leaderboard is global across active whitelisted users and does not segment by class or cohort.

## Next Steps

- add an admin workflow for question curation
- add richer explanation and remediation content
- add spaced repetition or topic-based sequencing
- add analytics views for teachers or coordinators
