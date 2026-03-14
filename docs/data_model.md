# Data Model

## Datasets

GlipMath uses three datasets by default:

- `glipmath_core`
- `glipmath_events`
- `glipmath_analytics`

## Core Tables

### `glipmath_core.question_bank`

Purpose: curated source of active and inactive multiple-choice questions.

Key columns:

- `id_question INT64 REQUIRED`
- `source STRING REQUIRED`
- `statement STRING REQUIRED`
- `choice_a STRING REQUIRED`
- `choice_b STRING REQUIRED`
- `choice_c STRING REQUIRED`
- `choice_d STRING REQUIRED`
- `choice_e STRING NULLABLE`
- `correct_choice STRING REQUIRED`
- `is_active BOOL REQUIRED`
- `topic STRING NULLABLE`
- `difficulty STRING NULLABLE`
- `explanation STRING NULLABLE`
- `created_at_utc TIMESTAMP NULLABLE`
- `updated_at_utc TIMESTAMP NULLABLE`

Business rules:

- `id_question` must be unique
- active rows must have valid choices
- `correct_choice` must reference a populated choice
- inactive rows remain stored but are ignored by the app

### `glipmath_core.whitelist`

Purpose: authorized users allowed to enter the app.

Key columns:

- `id_user INT64 REQUIRED`
- `email STRING REQUIRED`
- `name STRING NULLABLE`
- `is_active BOOL REQUIRED`
- `created_at_utc TIMESTAMP NULLABLE`
- `updated_at_utc TIMESTAMP NULLABLE`

Business rules:

- `id_user` must be unique
- `email` is matched after lowercase + trim normalization
- only active users are authorized

### `glipmath_events.answers`

Purpose: append-only answer event log.

Key columns:

- `id_answer STRING REQUIRED`
- `id_user INT64 REQUIRED`
- `email STRING REQUIRED`
- `id_question INT64 REQUIRED`
- `selected_choice STRING REQUIRED`
- `correct_choice STRING REQUIRED`
- `is_correct BOOL REQUIRED`
- `answered_at_utc TIMESTAMP REQUIRED`
- `answered_at_local DATETIME REQUIRED`
- `time_spent_seconds FLOAT64 REQUIRED`
- `session_id STRING REQUIRED`
- `source STRING NULLABLE`
- `topic STRING NULLABLE`
- `app_version STRING NULLABLE`

Design decisions:

- `id_answer` is a UUID-like string to avoid write contention
- `answered_at_utc` is the canonical event timestamp
- `answered_at_local` stores the app-local wall clock in `America/Sao_Paulo` by default
- rows are append-only and never updated

## Analytics Views

### `glipmath_analytics.v_user_totals`

Purpose:

- total answers per active user
- total correct answers per active user
- zero-filled rows for active users with no history

### `glipmath_analytics.v_user_daily_activity`

Purpose:

- daily activity grain by user
- supports streak-oriented analysis and future dashboards

### `glipmath_analytics.v_leaderboard`

Purpose:

- global leaderboard ordered by `total_correct DESC`, `total_answers DESC`, `email ASC`

## Metric Definitions

### Day streak

Consecutive local calendar days with at least one answered question, ending on:

- today, or
- yesterday

If the last activity is older than yesterday, streak is `0`.

### Question streak

Current consecutive correct-answer streak when reading the user's history in reverse chronological order.

### Leaderboard position

Rank within active whitelisted users using:

1. `total_correct DESC`
2. `total_answers DESC`
3. `email ASC`

## Source of Truth

Schema JSON files live in:

- [question_bank.json](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/infrastructure/terraform/schemas/question_bank.json)
- [whitelist.json](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/infrastructure/terraform/schemas/whitelist.json)
- [answers.json](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/infrastructure/terraform/schemas/answers.json)
