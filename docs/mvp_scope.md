# MVP Scope

## In Scope

- Streamlit app with two logical screens:
  - login
  - main app
- Google login through Streamlit auth
- BigQuery-backed question bank
- append-only BigQuery answer logging
- day streak
- question streak
- leaderboard position
- Terraform-managed GCP data layer
- practical question bank ingestion through JSONL
- deployment on Streamlit Community Cloud

## Deliberately Simplified for MVP

- beta access is controlled externally through Google OAuth app configuration and test users
- one global leaderboard based on total correct answers
- one question at a time
- no local persistence
- no admin UI

## Out of Scope

- Docker and Cloud Run deployment
- Artifact Registry
- Secret Manager runtime integration
- in-app whitelist or role management
- classroom management
- spaced repetition engine
- authoring questions inside the app
- multi-tenant concerns
