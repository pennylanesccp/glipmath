# AGENTS

Future coding agents working in this repository should preserve these rules:

- Keep page files thin. UI orchestration belongs in `app/`, not business logic.
- Keep business rules inside `modules/services/`.
- Keep BigQuery access and SQL execution inside `modules/storage/`.
- Keep Terraform modular under `infrastructure/terraform/`.
- Prefer small cohesive modules over large files.
- Use explicit imports, type hints, and docstrings on public functions.
- Do not commit secrets or real credentials.
- Keep diffs focused and avoid opportunistic refactors unless they unblock the task.
- Add or update tests when core logic changes.
- Preserve the architecture boundary between UI, domain, services, storage, and infrastructure.
- Prefer deterministic pure functions for logic that can be tested without Streamlit or GCP.
- Do not scatter SQL or BigQuery client calls across page code.
- If you touch schema assumptions, update `docs/data_model.md`, `README.md`, Terraform schema files, and any affected CSV templates.
