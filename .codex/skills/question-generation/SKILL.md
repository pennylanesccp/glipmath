---
name: question-generation
description: Generate high-quality GlipMath question-bank seed JSON payloads from course source files such as PDFs, slide decks, notes, Markdown, or pasted text. Use when Codex is asked to create, review, validate, or prepare one or more repository-compatible question-bank JSON seeds for BigQuery loading, especially course/aula batches under local/bq_seeds/source.
---

# GlipMath Question Generation

Use this skill to generate repository-compatible `question_bank` seed payloads from one or more course files. Do not invent a schema: use the existing nested `correct_answer` and `wrong_answers` model consumed by `scripts/apply_question_seed_jsons.py`.

## Required inputs

- Course subject exactly as provided by the user, for example `PHA3514 - Gestão de Recursos Hídricos`.
- One or more source files or pasted source texts.
- Aula boundaries, either explicit in the request or inferred from file names/content.
- Requested number of questions per aula, or a defensible count based on coverage.

## Optional inputs

- `cohort_key`; default to `engenharia_ambiental` for engineering/environmental course questions unless the user provides another value.
- Minimum difficulty; default to `4` unless the user explicitly requests easier questions.
- BigQuery load request; only write to BigQuery when explicitly requested.
- Course-specific ID prefix or existing seed files to extend.
- Source slug, year, or version suffix; default to the current course/aula/source naming style.

## Output format

Create one JSON seed payload per aula unless the user asks for a combined file. For engineering/environmental course batches, place operational seeds under:

```text
local/bq_seeds/source/poli/<source-file>.json
```

Use this payload shape:

```json
{
  "table_id": "ide-math-app.glipmath_core.question_bank",
  "delete": {
    "source": "<source>",
    "cohort_key": "engenharia_ambiental"
  },
  "defaults": {
    "subject": "<subject provided by user>",
    "topic": "aula 1",
    "source": "<source>",
    "cohort_key": "engenharia_ambiental",
    "is_active": true
  },
  "questions": [
    {
      "id_question": 351401101,
      "statement": "...",
      "correct_answer": {
        "alternative_text": "...",
        "explanation": "..."
      },
      "wrong_answers": [
        {
          "alternative_text": "...",
          "explanation": "..."
        },
        {
          "alternative_text": "...",
          "explanation": "..."
        },
        {
          "alternative_text": "...",
          "explanation": "..."
        }
      ],
      "difficulty": 4
    }
  ]
}
```

The loader materializes `created_at_utc` and `updated_at_utc`, normalizes taxonomy fields for storage, and accepts difficulty aliases, but generated JSON should use integer difficulty values for clarity.

## File naming convention

- Use lowercase ASCII slugs.
- Prefer one file per aula:
  - `pha3514_aula1_<short-topic-slug>_dificil.json`
  - `pha3514_aula2_<short-topic-slug>_dificil.json`
  - `pha3525_aula11_2_pof_dimensionamento_dificil.json`
- Use a matching `source` with a year/version suffix:
  - `pha3514_aula1_<short_topic_slug>_dificil_2026`
  - `pha3514_aula2_<short_topic_slug>_dificil_2026`
- Keep `delete.source` equal to `defaults.source`.
- Keep `delete.cohort_key` equal to `defaults.cohort_key`.

## ID generation convention

- First inspect nearby existing seeds for the course before assigning IDs.
- Preserve existing explicit IDs when editing a seed.
- For new PHA course/aula batches, prefer deterministic IDs in this pattern:
  - `<course_digits><aula_two_digits><block_digit><question_two_digits>`
  - Example: `PHA3514`, Aula 1, difficult block 1, question 1 -> `351401101`.
  - Example: `PHA3514`, Aula 11.2, question 1 -> `351411201`.
- Use a new block digit when adding a new independent batch for the same aula.
- If deterministic IDs would collide and no clean range is available, omit `id_question` and let `scripts/question_seed_ids.py` generate high-range IDs, then record that assumption in the summary.
- Always validate uniqueness within the new payload and against all local seed payloads being dry-run together.

## Topic naming convention

- Default to one simple aula topic per seed: `aula 1`, `aula 2`, `aula 11.1`, `aula 11.2`.
- Do not use verbose topic titles unless the user explicitly requests them.
- Use the same topic for every question in one aula payload through `defaults.topic`.
- The loader normalizes taxonomy values for storage; keep generated defaults simple and lower-case to match persisted values.
- Preserve the subject string in the JSON exactly as the user provided it, even though storage normalizes taxonomy for filtering.

## Question quality rubric

Generate questions that test reasoning, interpretation, application, comparison, diagnosis, or design judgment. Prefer prompts such as:

- "Qual decisão é mais adequada..."
- "Por que esta interpretação é tecnicamente frágil..."
- "Qual consequência operacional decorre..."
- "Como diferenciar..."
- "Qual diagnóstico explica..."

Quality requirements:

- Difficulty must be `4` or `5` when the minimum difficulty is 4.
- Cover all major concepts from each aula, not just slide titles or the easiest points.
- Use source-supported concepts only; do not hallucinate topics absent from the files.
- Avoid pure memorization of numbers, table values, law numbers, resolution numbers, acronym expansions, exact document names, or case names unless the fact is genuinely central to the learning objective.
- Do not write trick questions. Ambiguity should not be the source of difficulty.
- Keep explanations concise and instructional; they should state why the correct answer works and why the distractors are insufficient.
- Keep alternatives similar in tone, length, specificity, and polish.
- When the source is ambiguous, put assumptions in the generation summary, not in the JSON.

## Distractor quality rubric

Every question should have exactly three wrong answers unless the repository schema is intentionally changed.

Good distractors:

- Are plausible to a student with partial understanding.
- Reflect common misconceptions, incomplete reasoning, wrong transfer of a concept, or misuse of an operational criterion.
- Include at least one genuinely tempting misconception or incomplete-reasoning option per question.
- Are not absurd, jokey, or eliminable without knowing the content.
- Avoid giveaway absolute words such as `always`, `never`, `only`, `must`, `cannot`, `automatically`, `completely`, `exclusively`, `sempre`, `nunca`, `apenas`, `somente`, `obrigatoriamente`, or `automaticamente`, unless the absolute wording is justified and similarly plausible alternatives also use firm wording.
- Do not make the correct answer systematically longer or more complete than the distractors.

## Coverage checklist

Before writing final JSON, build a short coverage map for each aula:

- Main concepts and subtopics in the source.
- Practical decisions or diagnoses students should be able to make.
- Comparisons or distinctions emphasized by the material.
- Any formulas, flows, or design constraints that are conceptually important.
- Major risks, assumptions, limitations, or operational consequences.
- Minimum number of questions needed so each major topic is represented.

If a source file covers multiple aulas, split the coverage map and output one payload per aula.

## Validation checklist

Perform these checks before finalizing:

- Validate JSON syntax.
- Confirm payload follows the seed format used by `scripts/apply_question_seed_jsons.py`.
- Confirm `table_id` is `ide-math-app.glipmath_core.question_bank` unless the user provides another target.
- Confirm `cohort_key` is not a placeholder.
- Confirm all generated questions are active through `defaults.is_active: true` or explicit question override.
- Confirm all IDs are unique.
- Confirm every question has exactly one correct answer and three distractors.
- Confirm all alternatives are unique within each question.
- Confirm there are no duplicate statements.
- Confirm every difficulty is `4` or `5` when minimum difficulty is 4.
- Confirm every requested aula/source topic has adequate coverage.
- Confirm correct alternatives are not systematically longer than wrong alternatives.
- Confirm there is no heavy reliance on absolute giveaway words.
- Confirm no question depends on memorizing exact law numbers, class numbers, table numbers, acronym expansions, or exact document/case names unless pedagogically necessary.
- Run the repository's seed tests when reasonably fast.

Recommended commands:

```powershell
$env:PYTHONUTF8='1'
.\venv\Scripts\python.exe -m pytest tests\test_apply_question_seed_jsons.py tests\test_render_question_seed_sql.py -q
```

For one payload, validate materialization with:

```powershell
$env:PYTHONUTF8='1'
@'
from pathlib import Path
from scripts.apply_question_seed_jsons import materialize_seed_payload
from scripts.render_question_seed_sql import load_seed_payload

path = Path(r"local/bq_seeds/source/poli/<file>.json")
batch = materialize_seed_payload(load_seed_payload(path), source_path=path)
rows = batch.rows
assert rows
assert all(row["cohort_key"] == "engenharia_ambiental" for row in rows)
assert all(row["is_active"] is True for row in rows)
assert all(row["difficulty"] in (4, 5) for row in rows)
assert len({row["id_question"] for row in rows}) == len(rows)
assert len({row["statement"] for row in rows}) == len(rows)
for row in rows:
    texts = [row["correct_answer"]["alternative_text"], *[a["alternative_text"] for a in row["wrong_answers"]]]
    assert len(row["wrong_answers"]) == 3
    assert len(set(texts)) == 4
print(f"{path}: {len(rows)} rows OK")
'@ | .\venv\Scripts\python.exe -
```

If the user asked to load into BigQuery, also preflight source/cohort scope and ID collisions, then use `scripts.apply_question_seed_jsons.apply_seed_batches` or the CLI. Verify row counts, active flags, topic, difficulty distribution, and duplicate IDs after load.

## Example prompt

```text
Use $question-generation to generate questions for `PHA3514 - Gestão de Recursos Hídricos` from the attached Aula 1 and Aula 2 slides. Use minimum difficulty 4. Cover every relevant topic per class. Create one JSON seed payload per aula. Do not load to BigQuery yet.
```

## Example JSON payload

This is a schema example only; do not treat it as generated course content.

```json
{
  "table_id": "ide-math-app.glipmath_core.question_bank",
  "delete": {
    "source": "pha0000_aula1_exemplo_dificil_2026",
    "cohort_key": "engenharia_ambiental"
  },
  "defaults": {
    "subject": "PHA0000 - Curso Exemplo",
    "topic": "aula 1",
    "source": "pha0000_aula1_exemplo_dificil_2026",
    "cohort_key": "engenharia_ambiental",
    "is_active": true
  },
  "questions": [
    {
      "id_question": 1101,
      "statement": "Uma equipe precisa escolher entre duas alternativas de gestão com riscos e custos diferentes. Qual critério de decisão é mais defensável?",
      "correct_answer": {
        "alternative_text": "Comparar as alternativas pela relação entre objetivo, risco controlado, viabilidade operacional e evidência disponível.",
        "explanation": "A decisão deve conectar finalidade, risco, operação e evidência, não apenas um indicador isolado."
      },
      "wrong_answers": [
        {
          "alternative_text": "Escolher a alternativa com menor custo inicial, mantendo a análise de risco para depois da implantação.",
          "explanation": "Custo inicial é relevante, mas não substitui a avaliação prévia de risco e viabilidade."
        },
        {
          "alternative_text": "Escolher a alternativa com maior complexidade técnica, pois complexidade indica desempenho superior.",
          "explanation": "Complexidade pode aumentar custo e falhas se não estiver ligada ao objetivo do sistema."
        },
        {
          "alternative_text": "Escolher a alternativa mais parecida com um exemplo citado em aula, sem verificar as condições locais.",
          "explanation": "Exemplos ajudam, mas a aplicação depende das premissas e do contexto real."
        }
      ],
      "difficulty": 4
    }
  ]
}
```

## Common mistakes to avoid

- Generating one combined file when the user asked for one payload per aula.
- Leaving `cohort_key` as a placeholder or using `pha3525` instead of `engenharia_ambiental` for engineering/environmental course questions.
- Using verbose topics such as full lecture titles when the requested taxonomy should be `aula N`.
- Asking students to memorize law numbers, resolution numbers, table numbers, acronyms, case names, or slide titles instead of applying concepts.
- Creating correct answers that are visibly longer and more careful than all distractors.
- Writing distractors with obvious giveaway absolutes.
- Reusing the same misconception in every distractor.
- Duplicating statements or alternatives across questions.
- Adding unsupported topics because they are common in the broader discipline.
- Forgetting that `local/bq_seeds/` is ignored by Git; only repository skill/docs changes will be committed unless a tracked seed location is explicitly chosen.

## Final response pattern for a generation task

When the user asks for actual question generation, finish with a concise summary:

- Files created or updated.
- Topics covered.
- Number of questions per aula.
- Difficulty range.
- Validation performed.
- Assumptions made.
- BigQuery load status, if loading was requested.
