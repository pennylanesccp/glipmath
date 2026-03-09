# MVP Scope

GlipMath MVP is intentionally small:

- Google OIDC login through Streamlit.
- Whitelist-based authorization from Google Sheets.
- One multiple-choice math question at a time.
- Append-only answer logging in the `answers` worksheet.
- Basic gamification indicators:
  - day streak
  - question streak
  - leaderboard position

Out of scope for this repository version:

- adaptive recommendation engines
- teacher dashboards
- admin CRUD pages
- rich analytics
- offline-first support
- non-Google identity providers
