# AGENTS

Future coding agents working in this repository should preserve these rules:

- Keep page files thin. UI orchestration belongs in `app/`, not business logic.
- Keep business rules inside `modules/services/`.
- Keep Google Sheets and CSV I/O inside `modules/storage/`.
- Prefer small cohesive modules over large files.
- Use explicit imports, type hints, and docstrings on public functions.
- Do not commit secrets or real credentials.
- Keep diffs focused and avoid opportunistic refactors unless they unblock the task.
- Add or update tests when core logic changes.
- Preserve the architecture boundary between UI, domain, services, and storage.
- Prefer deterministic pure functions for logic that can be tested without Streamlit.
- If you touch schema assumptions, update `docs/data_model.md`, `README.md`, and any affected CSV templates.
