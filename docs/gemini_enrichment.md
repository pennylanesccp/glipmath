# Gemini Enrichment

## Purpose

Gemini is used only for offline/admin enrichment of question explanations.

This is intentionally not part of the student answer flow:

- the learner app reads explanations that already exist in BigQuery
- a missing explanation should not block question answering
- Gemini calls are reserved for manual enrichment and backfill workflows

## Why This Shape

This keeps costs and latency predictable:

- no per-answer model calls
- no runtime dependency for students
- BigQuery remains the source of truth after enrichment

The default strategy is free-tier-minded:

1. load or curate questions into `glipmath_core.question_bank`
2. find rows with missing explanations
3. enrich only those rows with Gemini
4. write the final nested explanations back to BigQuery

## Create Gemini API Keys

1. Open Google AI Studio:
   - `https://aistudio.google.com/apikey`
2. Create one or more API keys for the project you want to use.
3. Do not commit the keys to the repository.

Official references:

- Gemini API quickstart: `https://ai.google.dev/gemini-api/docs/quickstart`
- Python SDK docs: `https://googleapis.github.io/python-genai/`

## Secrets Configuration

Keep the Gemini model selection in `glipmath.toml` and put only the API keys in `.streamlit/secrets.toml` locally. If you want enrichment available in hosted environments, add the same API keys to Streamlit Community Cloud secrets as well.

```toml
[ai]
GEMINI_API_KEYS = [
  "REPLACE_WITH_GEMINI_API_KEY_1",
  "REPLACE_WITH_GEMINI_API_KEY_2",
]
```

Notes:

- `glipmath.toml` already defaults `ai.model` to `gemini-2.5-flash-lite`.
- if one key hits a rate/quota limit, the Gemini client retries the same request with the next configured key.
- the enrichment script reads secrets through the shared config loader
- student question answering does not require Gemini to be configured
- install the project before running enrichment:

  ```powershell
  python -m pip install -e .
  ```

## Enrichment Script

Dry run:

```powershell
python scripts/enrich_question_explanations.py --dry-run --limit 10
```

Write mode:

```powershell
python scripts/enrich_question_explanations.py --limit 50
```

Behavior:

- reads active questions that are missing one or more explanations
- builds a structured prompt per question
- asks Gemini for:
  - `correct_answer.explanation`
  - `wrong_answers[].explanation`
- validates that Gemini returned the expected alternatives
- preserves any explanation text that already exists
- writes the enriched nested answer structures back to BigQuery

## Safety Notes

- enrichment is row-by-row so one bad model response does not block the entire batch
- use `--dry-run` first whenever you change prompts or models
- if some questions fail validation, the script exits non-zero after processing so the run is visibly incomplete
