# Data Model

## Datasets

- `glipmath_core`
- `glipmath_events`
- `glipmath_analytics`

## `glipmath_core.question_bank`

- `id_question INT64 REQUIRED`
- `statement STRING REQUIRED`
- `correct_answer RECORD REQUIRED`
  - `alternative_text STRING REQUIRED`
  - `explanation STRING NULLABLE`
- `wrong_answers RECORD REPEATED`
  - `alternative_text STRING REQUIRED`
  - `explanation STRING NULLABLE`
- `subject STRING NULLABLE`
- `topic STRING NULLABLE`
- `difficulty INT64 NULLABLE`
- `source STRING NULLABLE`
- `cohort_key STRING NULLABLE`
- `is_active BOOL REQUIRED`
- `created_at_utc TIMESTAMP NULLABLE`
- `updated_at_utc TIMESTAMP NULLABLE`

Validation rules:

- `id_question` must be unique
- `statement` must be present
- `correct_answer.alternative_text` must be present
- `wrong_answers` must contain at least one item for app validation
- alternative texts must be unique within a question
- inactive questions are ignored by the app
- `difficulty`, when present, must be an integer from 1 to 5

Why nested?

- BigQuery stores the canonical correct answer and wrong answers cleanly
- the app can randomize answer order at runtime
- explanations can live beside each alternative
- `subject` lets the same bank hold math and non-math content cleanly
- `cohort_key` lets the repository enforce project/class/year access before subject filtering

Difficulty scale:

- `1` básico
- `2` fácil
- `3` médio
- `4` difícil
- `5` avançado

`cohort_key` examples:

- `etec`
- `enem`
- `ano_1`
- `ano_2`
- `ano_3`

## `glipmath_core.user_access`

- `user_email STRING REQUIRED`
- `role STRING REQUIRED`
- `cohort_key STRING REQUIRED`
- `is_active BOOL REQUIRED`
- `display_name STRING NULLABLE`
- `created_at_utc TIMESTAMP NULLABLE`
- `updated_at_utc TIMESTAMP NULLABLE`

Rules:

- `user_email` is the normalized identity key used by the app
- `role` is explicit and must be `student` or `teacher`
- students must have exactly one cohort, for example `ano_2`
- teachers must use `cohort_key = all`
- if there is no active row for the authenticated email, the user is not authorized
- the learner never chooses cohort manually in the UI

## `glipmath_events.answers`

- `id_answer STRING REQUIRED`
- `id_question INT64 REQUIRED`
- `user_email STRING REQUIRED`
- `selected_alternative_text STRING REQUIRED`
- `correct_alternative_text STRING REQUIRED`
- `is_correct BOOL REQUIRED`
- `answered_at_utc TIMESTAMP REQUIRED`
- `answered_at_local DATETIME REQUIRED`
- `time_spent_seconds FLOAT64 REQUIRED`
- `session_id STRING REQUIRED`
- `subject STRING NULLABLE`
- `topic STRING NULLABLE`
- `difficulty STRING NULLABLE`
- `source STRING NULLABLE`
- `cohort_key STRING NULLABLE`
- `app_version STRING NULLABLE`

Usage notes:

- `answers` is append-only
- every answer submission inserts one row
- `answered_at_local` is stored as BigQuery `DATETIME`
- user identity is the normalized email for the MVP
- `cohort_key` stores the effective question cohort at submission time for future analytics and ranking
- `difficulty` is a textual answer-time snapshot; current submissions store the question's 1-5 difficulty as a string while historical rows remain append-only

The Terraform table definition partitions `answers` by `answered_at_utc` and clusters by `user_email` and `id_question`.

## Analytics Views

- `glipmath_analytics.v_user_totals`
- `glipmath_analytics.v_user_daily_activity`
- `glipmath_analytics.v_leaderboard`

Definitions:

- `v_user_totals`
  - aggregates `total_answers` and `total_correct` by normalized `user_email`
  - projects display name and access metadata from `user_access` when available
- `v_user_daily_activity`
  - aggregates per-user daily answer counts from `answered_at_local`
- `v_leaderboard`
  - remains a global leaderboard view and ranks by:
    1. `total_correct DESC`
    2. `total_answers DESC`
    3. `user_email ASC`

## Metric Definitions

- Day streak
  - consecutive calendar days with at least one answer
  - the streak can continue from today or yesterday
- Question streak
  - consecutive correct answers when scanning the current user history in reverse chronological order
- Leaderboard position
  - students see repository-query ranking only against active students in the same `cohort_key`
  - teachers see the global ranking
  - users with zero answers do not yet appear in the leaderboard result

## Input Formats

Canonical question-bank input:

- `sql/seeds/question_bank_template.jsonl`
- `local/bq_seeds/source/*.json` for local BigQuery seed payloads

Supported raw import input:

- `data/*.csv` in the vestibulinho flat-question format
  - `question_number`
  - `statement`
  - `question_a` to `question_e`
  - `subject` optional
  - `cohort_key` optional
  - `source`
  - `answer`

The import pipeline converts the raw CSV rows into the nested BigQuery schema before validation and load.
Legacy difficulty labels such as `easy`, `facil`, `3_medio`, `hard`, and `advanced` are normalized to the canonical integer scale during import.

For this raw CSV path, `id_question` is generated deterministically from `source`, `question_number`, and `cohort_key` when cohort scope is present. The loader CLI also accepts `--cohort-key` to stamp a whole batch without editing every row.

For local BigQuery seed payloads, `id_question` may be omitted or left blank. The seed scripts generate a high-range random integer ID before loading or rendering SQL, while preserving any explicit `id_question` values provided in the JSON.

Version-controlled schema files:

- `infrastructure/terraform/schemas/question_bank.json`
- `infrastructure/terraform/schemas/user_access.json`
- `infrastructure/terraform/schemas/answers.json`
