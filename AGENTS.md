# AGENTS.md - GlipMath repo instructions for Codex

Role: Senior Python, Streamlit, BigQuery, and Terraform engineer.

Mission: Maintain and evolve the GlipMath MVP with a simple learner UX, reliable BigQuery persistence, clean module boundaries, and a pragmatic Streamlit Community Cloud deployment path.

---

## Project overview

This repository is a Python project focused on a math-learning app with light gamification:

- `.streamlit/` - local and Streamlit Cloud secrets/config structure
- `app/` - Streamlit entrypoint, pages, components, and session state
- `modules/` - domain, service, storage, auth, config, and utility code
- `infrastructure/terraform/` - GCP data-layer IaC only
- `sql/` - BigQuery views plus seed assets
- `scripts/` - validation, load, and local/dev helper workflows
- `docs/` - architecture, auth, infra, deployment, and manual bootstrap docs
- `tests/` - deterministic unit tests without real GCP calls

Core flow:

1. Authenticate the learner with Google OIDC through Streamlit auth.
2. Load active questions from BigQuery.
3. Build randomized answer alternatives in memory from the nested question schema.
4. Append each submitted answer to BigQuery.
5. Compute day streak, question streak, and leaderboard position from persisted data.

---

## Non-negotiables

- BigQuery is the only durable application datastore in the MVP.
- Streamlit Community Cloud is the primary deployment target.
- Google OAuth app configuration and test users control beta access for now.
- `glipmath_core.question_bank` must keep the nested `correct_answer` / `wrong_answers` model unless an intentional schema migration is requested.
- `glipmath_events.answers` must remain append-only.
- Never commit secrets, `.streamlit/secrets.toml`, service account keys, OAuth credentials, or real private data.
- Keep user-facing UI text in Portuguese-BR unless explicitly asked to change product language.

---

## Architecture constraints

1. Keep `app/` thin. UI orchestration belongs there, not business logic.
2. Keep domain rules in `modules/services/`.
3. Keep BigQuery access and SQL execution in `modules/storage/`.
4. Keep `sql/views/` as the source for analytics view definitions used by Terraform.
5. Keep Terraform limited to resources the project actually uses.
6. Do not reintroduce Docker, Cloud Run, Artifact Registry, Secret Manager runtime dependencies, or in-app whitelist logic unless explicitly requested.

---

## Data and persistence rules

- `question_bank` rows must validate cleanly against the nested schema.
- Runtime answer randomization should be driven from canonical question data, not hardcoded UI labels.
- `answers` rows should use normalized `user_email` as the current identity field.
- Do not update historical answer rows in place.
- Prefer deterministic transforms and explicit schemas over ad-hoc data shaping.
- If schema assumptions change, update:
  - `docs/data_model.md`
  - `README.md`
  - Terraform schema JSON files
  - affected SQL views
  - seed assets
  - scripts
  - tests

---

## Environment and configuration

Required local conventions:

- Use the `venv` virtual environment.
- Use `.streamlit/secrets.toml` for local auth and BigQuery configuration.
- Keep `.streamlit/secrets.toml.example` safe and placeholder-only.

Expected secrets/config sections:

- `[app]`
- `[gcp]`
- `[bigquery]`
- `[auth]`
- `[gcp_service_account]`

Manual setup still exists outside the repo for:

- Google OAuth consent and client configuration
- runtime service account key creation
- Streamlit Community Cloud secret configuration

---

## Working rules

- Prefer small, focused diffs.
- Add or update tests when business logic changes.
- Use typed models and explicit imports.
- Keep repository and service boundaries clear.
- Avoid opportunistic refactors unless they unblock the requested work.
- If you touch deployment or bootstrap behavior, make sure the docs stay aligned with the real local and Streamlit Cloud flow.

---

## Git and completion requirement (MANDATORY)

When you finish any task, end your final message with a section titled exactly:

Commit message:

IMPORTANT formatting requirements:

- The entire commit message output must be in one fenced code block.
- That code block must be the last content in the final message.
- Use `-` for bullets.

Conventional Commits rules:

- Subject format: `type(scope): short imperative summary`
- Allowed types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf`
- Suggested scopes for this repo: `app`, `scripts`, `modules`, `road`, `multimodal`, `fuel`, `costs`, `infra`, `db`, `data`, `deps`, `docs`

Body format (required when files changed): 1 to 9 bullets summarizing changes

Output format:

If code/files changed, output inside a fenced block:

```text
{type}({scope}): {subject}

- {change bullets}
```

If code/files did not change, no commit message block is needed.
