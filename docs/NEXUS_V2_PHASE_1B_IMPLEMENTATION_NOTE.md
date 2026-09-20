# Nexus V2 — Phase 1B Implementation Note

Status: **implemented, not deployed.** Phase 1B delivers the *content +
assessment foundation*: V2 curriculum content and assessments become
data-driven (Markdown + YAML) instead of hardcoded Python, and the assessment
system gains deterministic-only grading structures for free-form questions.
No AI, no student migration, no production change.

Companions: `NEXUS_V2_PRD.md`, `CURRICULUM_CONTENT_STANDARD.md`,
`NEXUS_V2_MIGRATION_PLAN.md`, `NEXUS_V2_PHASE_1A_IMPLEMENTATION_NOTE.md`.

---

## 1. What shipped

### Data-driven content loaders (`backend/app/services/`)

| Module | Responsibility |
|---|---|
| `v2_lesson_loader.py` | Walk `content/curriculum/**/*.md`, parse YAML frontmatter + Markdown body, upsert one `lesson_v2_meta` row per `lesson_key`. Two-pass so `builds_on` / `review_of` edges resolve across files. `content_hash` (SHA-256 of body) drives change detection. Never writes the legacy `lessons` table (only sets the optional 1:1 `lesson_id` when frontmatter `legacy_lesson_id` is given). |
| `v2_content_loader.py` (extended) | `load_resources()` (learning resources + lesson/module links), `load_interview_prompts()` (Explain prompts + objective links), `_sync_module_assessments()` (module assessment rows referencing existing engines), `load_content()` orchestrator. All idempotent, keyed on stable natural keys. |
| `deterministic_grader.py` | Pure, no-DB, no-AI grading for `short_answer` / `free_response`. Returns `graded` **or** `needs_review` — never a confident pass/fail on prose it cannot judge. |
| `objective_coverage.py` | Per-version objective coverage report (DISTINCT mapped objectives; version-isolated). Backend only, no UI. |

### Fixture content (`backend/content/`)

- `curriculum/comptia-a-plus/220-1201/networking-fundamentals/tcp-udp-ports.md` — one real lesson (not a bulk migration).
- `resources/comptia-a-plus.yaml` — 2 resources (video + reference) with links.
- `interview-prompts/comptia-a-plus.yaml` — 1 Explain prompt with rubric.
- `certifications/comptia_aplus.yaml` — `assessments:` block added to the `networking_fundamentals` module (quick_check + module_quiz + explain).

### Extended question importer

`question_validation.py` and `question_importer.py` now accept
`short_answer` / `free_response` rows: options and correct-answer letters are
skipped; grading metadata (`acceptable_answers`, `expected_concepts`,
`rubric`, `rubric_version`, `answer_match_mode`, `min_concepts_for_pass`,
`partial_credit`) is parsed from JSON-or-pipe cells and written to
`question_v2_meta`. The legacy `questions` row stores the sentinel
`correct_answer = "-"` and `option_a = ""` to satisfy NOT NULL. All Phase 1A
behaviour (fingerprint dedup, preview/confirm, formula-injection guard,
editorial status, provenance, permission status, MCQ import) is unchanged.
The CSV template gains the 7 new columns and a `short_answer` example row.

---

## 2. Schema (migration `0063_v2_content_and_assessment`, additive)

`down_revision = 0062_v2_certification_foundation`. Full tested `downgrade`.
Legacy `lessons` / `questions` schemas are **not** touched — all V2 data is in
companion / new tables, per the approved Phase 1A architecture.

**`question_v2_meta`** — 8 columns added: `question_type`,
`acceptable_answers` (JSON), `answer_match_mode`, `expected_concepts` (JSON),
`rubric` (JSON), `rubric_version`, `min_concepts_for_pass`, `partial_credit`.

**`lesson_v2_meta`** reshaped (dropped + recreated by the migration; it held
no production rows): `lesson_id` is now **nullable** (a V2 lesson need not
bind to a legacy row); added `lesson_key` (unique), `title`, `summary`,
`content_path`, `content_body`, `content_hash`, `source_name`, `source_url`.

**`lesson_objectives`** / **`lesson_relationships`** — join keys moved from
`lesson_id` to `lesson_v2_meta_id` / `from_lesson_meta_id` +
`to_lesson_meta_id`. Self-edge CHECK and `(from,to,type)` uniqueness kept.

**New tables:**

| Table | Purpose | Key relationships |
|---|---|---|
| `v2_resources` | Learning resource (video/article/documentation/external_practice/reference) with provider, URL, provenance, `permission_status`, `active`. | → `certification_versions` (SET NULL) |
| `v2_resource_links` | Resource ↔ lesson and/or module, `is_required`, `display_order`. CHECK: at least one of lesson/module set. | → `v2_resources` (CASCADE), `lesson_v2_meta` (SET NULL), `certification_modules` (SET NULL). Unique `(resource, lesson_meta, module)`. |
| `v2_student_resource_activity` | Per-student external-practice tracking: `opened_at`, `completed`, `completed_at`, `reported_score`, `student_note`, `confusing_topic`, `question_for_mentor`. **A reported score is never mastery — no gate evaluator reads this table.** | → `students` (CASCADE), `v2_resources` (CASCADE). Unique `(student, resource)`. |
| `module_assessments` | A module's assessment slots by `assessment_role` (quick_check / module_quiz / practical / service_desk / explain). **References** existing engines by nullable FK — `quiz_id`, `lab_template_id`, `service_desk_scenario_id` — it does not reimplement them. `displayed_count`, `pass_percent`, `config` (JSON). | → `certification_modules` (CASCADE), `lesson_v2_meta` (SET NULL), `quizzes` / `lab_templates` / `service_desk_scenarios` (SET NULL) |
| `interview_prompts` | Data-driven Explain/interview prompts: `prompt`, `expected_concepts` (JSON), `rubric` (JSON), `rubric_version`, `importance`, `model_answer_outline`, provenance, `active`. | → `certification_versions` / `certification_modules` (SET NULL) |
| `interview_prompt_objectives` | Prompt ↔ objective. | → `interview_prompts` / `certification_objectives` (CASCADE) |

---

## 3. Deterministic grading contract

`grade_short_answer(response, acceptable_answers, *, match_mode)` and
`grade_free_response(response, expected_concepts, *, rubric, rubric_version,
min_concepts_for_pass, partial_credit)` return:

```
{status: "graded"|"needs_review", score: float, passed: bool|None,
 method: str, matched: [...], missing: [...], rubric_version, detail}
```

Rules that keep it honest:

- **short_answer**: normalized equality or a curated answer appearing as a
  whole phrase inside a *short* (≤12-token) response → `graded` pass. Short
  response, no match → `graded` fail (confident). Long/rambling response →
  `needs_review` (do not guess). No key configured → `needs_review`.
- **free_response**: concept matched if its term or an alias appears as a
  whole phrase. All concepts (≥ threshold) → `graded` pass. Some matched,
  `partial_credit` on → `graded` partial (score = fraction, `passed=False`).
  **Zero concepts matched but the response is non-trivial → `needs_review`,
  `passed=None`** — the matcher may simply not recognise the phrasing; a
  later AI/mentor pass decides. Trivial/empty response → `graded` 0.

No model is ever called; output is a pure function of the inputs.

---

## 4. Objective coverage

`certification_version_coverage(db, version)` → `total_objectives`,
`covered_objectives` (DISTINCT objectives with ≥1 `lesson_objectives` row),
`uncovered_objectives`, `coverage_percent`, `question_covered_objectives`
(extra signal from `question_v2_meta.objective_code`), `uncovered` / `covered`
detail lists, and `by_domain` breakdown. Two lessons mapping the same
objective count once. Objectives, lessons and questions are all filtered to
the version, so versions never bleed into each other's score.

---

## 5. Verification performed

- `backend`: `pytest -q` → **618 passed**, 0 failed (includes the historical
  data-migration lineage tests — companion-table compatibility holds).
- New `tests/test_v2_content_and_assessment.py` → 34 passed. Updated
  `tests/test_v2_certification_foundation.py` (companion-table shapes) → 29
  passed.
- `alembic upgrade head` → `downgrade 0061` → `upgrade head` clean.
- Model ↔ migration-head parity: identical table set, identical columns on
  all 10 V2 tables.
- `compileall` + `ruff check` clean on every new/changed file.
- V1 guards asserted by tests: `DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT == 40`
  unchanged; V2 content load creates **zero** `training_weeks` rows; legacy
  `questions` table has none of the V2 columns.

## 6. Deferred to Phase 1C (structures ready, not blocking)

Local GPU/LLM service; AI grade tables / pending-grade worker / retry queue;
confidence scoring; AI explanations; mentor AI-review UI; any student-facing
UI for resources, external-practice self-report, or the coverage report.
`needs_review` is the hand-off point those systems consume.
