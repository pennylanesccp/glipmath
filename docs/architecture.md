# Architecture

GlipMath is a small but production-minded Streamlit application deployed on Streamlit Community Cloud and backed by BigQuery.

## Layers

- `app/`
  - Streamlit entrypoint, pages, components, and session-state helpers
  - Responsible for orchestration only
- `modules/domain/`
  - Typed app models
- `modules/ai/`
  - Offline/admin Gemini integration
  - Prompt building and structured explanation validation
- `modules/services/`
  - Pure or mostly pure business logic
  - Question parsing and selection
  - Answer evaluation
  - Streak calculations
  - Leaderboard logic
- `modules/storage/`
  - BigQuery client wrapper
  - Repositories for questions and answers
- `infrastructure/terraform/`
  - GCP data-layer resources only

## Runtime Flow

1. The user lands on the login page.
2. `st.login()` starts Google OIDC.
3. Streamlit exposes the authenticated identity in `st.user`.
4. The app normalizes the email and creates a lightweight current user object.
5. Repositories load:
   - active questions from `glipmath_core.question_bank`
   - current user answer history from `glipmath_events.answers`
   - leaderboard rows from `glipmath_analytics.v_leaderboard`
6. Services compute:
   - the next question
   - randomized display alternatives
   - day streak
   - question streak
   - leaderboard position
7. Submitting an answer appends one row to `glipmath_events.answers`.

## Offline Enrichment Flow

1. An admin script reads active questions missing explanations from `glipmath_core.question_bank`.
2. `modules/ai/explanation_service.py` builds a structured prompt for Gemini.
3. `modules/ai/gemini_client.py` calls Gemini with JSON output enabled.
4. The response is validated against the expected alternatives.
5. The script writes the enriched nested explanations back to BigQuery.

This flow is intentionally separate from the student request path.

## Question Model

The question bank uses a nested BigQuery schema:

- `correct_answer` is a struct
- `wrong_answers` is a repeated struct array

The app does not store `choice_a`-style columns anymore.

At runtime the app:

1. combines one correct answer with all wrong answers
2. randomizes the order in memory
3. renders only `alternative_text`
4. evaluates correctness from the runtime option structure and persists the canonical correct alternative text

This keeps the storage model simple while allowing per-render answer randomization.

## Authentication and Authorization

- Authentication is Google OIDC through Streamlit auth.
- Authorization is intentionally lightweight in the MVP.
- Beta access is controlled outside the app through Google OAuth app configuration and test users.
- There is no BigQuery whitelist dependency in the current version.

The authorization service remains as a boundary so internal allowlists or role checks can be added later without pushing business rules into the page code.

## Data Access Rules

- Page files do not execute BigQuery SQL directly.
- Repositories own all BigQuery reads and writes.
- Services operate on typed domain models instead of raw dataframes.
- Gemini access stays in `modules/ai/` and offline scripts, not in Streamlit page files.
- SQL used for analytics views lives under `sql/views/`.

## Deployment Model

- App hosting: Streamlit Community Cloud
- BigQuery access: service account JSON stored in Streamlit secrets
- Infrastructure: Terraform for BigQuery, IAM, and the runtime service account

There is no Docker, Cloud Run, Artifact Registry, or Secret Manager runtime dependency in the MVP.
