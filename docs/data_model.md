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
- `topic STRING NULLABLE`
- `difficulty STRING NULLABLE`
- `source STRING NULLABLE`
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

Why nested?

- BigQuery stores the canonical correct answer and wrong answers cleanly
- the app can randomize answer order at runtime
- explanations can live beside each alternative

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
- `topic STRING NULLABLE`
- `difficulty STRING NULLABLE`
- `source STRING NULLABLE`
- `app_version STRING NULLABLE`

Usage notes:

- `answers` is append-only
- every answer submission inserts one row
- `answered_at_local` is stored as BigQuery `DATETIME`
- user identity is the normalized email for the MVP

The Terraform table definition partitions `answers` by `answered_at_utc` and clusters by `user_email` and `id_question`.

## Analytics Views

- `glipmath_analytics.v_user_totals`
- `glipmath_analytics.v_user_daily_activity`
- `glipmath_analytics.v_leaderboard`

Definitions:

- `v_user_totals`
  - aggregates `total_answers` and `total_correct` by normalized `user_email`
- `v_user_daily_activity`
  - aggregates per-user daily answer counts from `answered_at_local`
- `v_leaderboard`
  - ranks by:
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
  - rank in `v_leaderboard`
  - users with zero answers do not yet appear in the leaderboard view

## Input Formats

Canonical question-bank input:

- `sql/seeds/question_bank_template.jsonl`

Supported raw import input:

- `data/*.csv` in the vestibulinho flat-question format
  - `question_number`
  - `statement`
  - `question_a` to `question_e`
  - `source`
  - `answer`

The import pipeline converts the raw CSV rows into the nested BigQuery schema before validation and load.

For this raw CSV path, `id_question` is generated deterministically from `source` plus `question_number`.

Version-controlled schema files:

- `infrastructure/terraform/schemas/question_bank.json`
- `infrastructure/terraform/schemas/answers.json`
