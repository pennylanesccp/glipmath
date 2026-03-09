# Architecture

## Design Goals

GlipMath is an MVP, but it is structured like a small maintainable Python application:

- typed modules
- small cohesive files
- explicit storage boundaries
- testable domain logic
- minimal logic inside Streamlit page files

## Layers

### `app/`

Contains Streamlit-specific composition:

- `streamlit_app.py`: entrypoint and routing
- `pages/`: logical page renderers
- `components/`: reusable UI fragments
- `state/`: session-state helpers for rerun-safe flows

### `modules/domain/`

Typed dataclasses representing app concepts:

- `Question`
- `AppUser`
- `AnswerRecord`
- `LeaderboardEntry`

### `modules/services/`

Pure business logic and data interpretation:

- question validation and selection
- answer parsing and evaluation
- streak calculations
- leaderboard calculations
- whitelist parsing and lookup

### `modules/auth/`

Authentication and authorization helpers:

- Streamlit OIDC integration wrappers
- whitelist-based authorization service

### `modules/storage/`

Persistence adapters:

- Google Sheets backend for production
- CSV backend for local storage workflows
- repositories for worksheet access
- schema validation helpers

### `modules/config/`

Settings loaded from Streamlit secrets with typed dataclasses.

## Runtime Flow

1. Streamlit starts `app/streamlit_app.py`.
2. Settings are loaded from `.streamlit/secrets.toml`.
3. If the user is not authenticated, the login page is rendered.
4. After authentication, the whitelist is loaded and matched by normalized email.
5. If authorized, the app loads:
   - question bank
   - whitelist users
   - answer history
6. Services compute:
   - valid questions
   - user history
   - day streak
   - question streak
   - leaderboard
7. The main page renders one question at a time.
8. On submission, one append-only answer row is written to `answers`.

## Data Integrity Strategy

The app is intentionally tolerant but not silent:

- missing required worksheet columns: blocking error
- duplicate IDs or duplicate normalized whitelist emails: blocking error
- malformed active question rows: skipped and surfaced in diagnostics
- malformed answer rows: skipped and surfaced in diagnostics
- empty `answers` worksheet: allowed

## Storage Strategy

Production target:

- private Google Sheet
- service account credentials in Streamlit secrets
- append-only answer logging

Development fallback:

- CSV files under `data/local_dev/`
- same worksheet naming convention as the production sheet

## UI Strategy

The UI is intentionally simple:

- login screen
- access denied screen
- one main authenticated screen
- top metrics
- compact leaderboard
- single question card
- answer feedback and next-question flow
