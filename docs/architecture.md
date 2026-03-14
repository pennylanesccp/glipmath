# Architecture

## Overview

GlipMath is a small but production-minded Streamlit application deployed on Cloud Run and backed by BigQuery.

The architecture is intentionally split into five layers:

- UI: `app/`
- Domain models: `modules/domain/`
- Business services: `modules/services/`
- Storage adapters: `modules/storage/`
- Infrastructure: `infrastructure/terraform/`

## Runtime Flow

1. The user opens the Streamlit app.
2. Streamlit OIDC handles Google login.
3. The app normalizes the email and checks BigQuery `whitelist`.
4. Authorized users load active questions from `question_bank`.
5. The app loads the current user's answer history from `answers`.
6. The app loads leaderboard rows from `v_leaderboard`.
7. On submission, the app evaluates the answer and appends one event row to `answers`.

## Layer Responsibilities

### `app/`

- Page routing and orchestration
- Session state
- Streamlit components
- Portuguese-BR user-facing text

No BigQuery SQL or business rules should live here.

### `modules/domain/`

- `Question`
- `User`
- `AnswerAttempt`
- `LeaderboardEntry`

These are typed containers used across the app.

### `modules/services/`

- Question validation and selection
- Answer evaluation
- Day streak and question streak rules
- Leaderboard ranking logic
- Whitelist parsing and normalization

These modules are designed to stay deterministic and easy to test.

### `modules/storage/`

- BigQuery client wrapper
- Question repository
- Whitelist repository
- Answer repository

All BigQuery queries stay here so UI files remain thin.

### `infrastructure/terraform/`

- Project service enablement
- Service accounts
- BigQuery datasets, tables, and views
- Secret Manager placeholders
- Artifact Registry
- GCS bucket
- Cloud Run service

## Data Access Pattern

The app uses:

- table reads for `question_bank`
- table reads for `whitelist`
- user-scoped reads for `answers`
- streaming inserts for `answers`
- analytics view reads for `v_leaderboard`

This keeps the MVP simple while preserving a clean path to future optimization.

## Auth Design

Google OIDC is handled by Streamlit auth helpers:

- local runs read `.streamlit/secrets.toml`
- Cloud Run receives env vars from Secret Manager
- `scripts/bootstrap_streamlit_secrets.py` writes a runtime secrets file inside the container

Authorization is separate from authentication:

- authentication: Google identity
- authorization: active email match in BigQuery `whitelist`

## Deployment Design

- Local development: Streamlit + ADC + BigQuery
- Production deployment: Docker image on Cloud Run
- No local filesystem persistence
- Runtime identity: Cloud Run service account

## Design Tradeoffs

- BigQuery streaming inserts were chosen for MVP simplicity over more advanced write APIs.
- Current question streak is kept in Python because it is simpler and clearer than an MVP SQL implementation.
- Leaderboard aggregation is provisioned as a BigQuery view so app reads stay small.
