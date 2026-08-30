# Nexus V2 — Phase 1A Implementation Note

Status: **implemented, not deployed.** Additive foundation only. No production
deploy, no student migration, no change to current curriculum behaviour, the
legacy `TrainingWeek` system, or the 40% A+ unlock gate.

Companion docs: `NEXUS_V2_PRD.md`, `CURRICULUM_CONTENT_STANDARD.md`,
`NEXUS_V2_MIGRATION_PLAN.md`.

---

## What Phase 1A introduced

### 1. V2 certification hierarchy (new tables, empty in production)

`certifications → certification_versions → certification_domains /
certification_modules / certification_objectives`

- Certification **versions are data**, carrying their `exam_codes` as a JSON
  list on the row. No progression code branches on a hardcoded exam-code
  constant. (The legacy `a_plus_access.A_PLUS_EXAM_CODES` constant is
  untouched and still drives the unchanged 40% gate — its removal is a later
  phase.)
- `certification_versions.version_key` is globally unique **and** unique per
  certification. `certification_objectives` is unique on
  `(certification_version_id, objective_code)`, so 220-1201 and 220-1202 both
  carry an objective `"1.1"` independently.
- `certification_modules.legacy_training_week_id` / `legacy_module_code` are
  nullable, read-only migration bridges — they never make a V2 module
  participate in week gating.

### 2. Lesson & question mapping via **companion tables** (not new columns)

- `lesson_v2_meta` (1:1 with `lessons`): `lesson_key`, `certification_version_id`,
  `certification_module_id`, `domain_key`, `importance`,
  `learning_relationship`, `content_path`.
- `question_v2_meta` (1:1 with `questions`): `certification`,
  `certification_version` (+ resolved `certification_version_id`), `domain`,
  `module`, `objective_code`, `importance`, `source_name`, `source_url`,
  `permission_status` (NOT NULL, default `unknown`).
- `lesson_objectives` (M:N lesson ↔ objective).
- `lesson_relationships` (directed edges, `builds_on` / `review_of`, unique
  per `(from, to, type)`, self-edge rejected) — a lesson can relate to
  **multiple** earlier lessons.
- `Lesson.v2_meta` / `Question.v2_meta` relationships added for ergonomics;
  they add no columns and are lazy.

**Why companion tables instead of columns on `lessons` / `questions`**
(deviation from the Phase 0 migration plan, which said "add columns to
`questions`"): several historical-lineage tests build a DB with an old
backend checkout, then run data-only migrations (e.g. `0057`, which
`INSERT`s questions) using the *current* ORM. New nullable columns on
`questions` / `lessons` make the current ORM emit `SELECT`/`INSERT` naming
columns the not-yet-upgraded schema lacks → `OperationalError`. A side table
keeps the legacy `lessons` and `questions` schemas **byte-for-byte
unchanged**, so every existing migration/seed/test path is unaffected. The
trade-off (an extra join later) is acceptable for an additive foundation; a
later phase may still choose to inline once the week system is gone.

### 3. Importance & Learning-Relationship vocabularies

- Importance: `job_critical | working_knowledge | awareness`, with `know_it`
  accepted as a legacy alias of `working_knowledge` (matches the existing
  `curriculum_videos.job_relevance` values so they can converge later).
- Learning Relationship: `new | review | deep_dive`.
- Helpers in `app/models/certification.py`: `normalize_importance`,
  `normalize_permission_status`, `is_publishable_permission`,
  `question_permission_status`.

### 4. Objective data loader

- `app/services/v2_content_loader.py` — idempotent upserts from YAML:
  - `load_certifications(path)` — cert + versions + domains + modules.
  - `load_objectives(path)` — objectives for the version the file names;
    raises if that version is not loaded first.
  - `load_all()` — every cert file, then every referenced objective file.
  - `backfill_examcompass_permission()` — owner decision: existing ExamCompass
    questions may be reused; marks them `permitted` in `question_v2_meta`
    **without ever rewriting the legacy `questions.source` text**. Idempotent.
- Data files (maintainable, not Python constants):
  - `backend/content/certifications/comptia_aplus.yaml`
  - `backend/content/objectives/comptia-a-plus-220-1201.yaml`
  - `backend/content/objectives/comptia-a-plus-220-1202.yaml`
- Every objective row records `source_name` + `source_url` provenance
  (defaulted from the file header, overridable per objective).
- `backend/seed_v2_foundation.py` — opt-in runner. **Not** wired into
  `seed.py` / `seed_curriculum.py` / CI. Run by hand:
  `./.venv/bin/python seed_v2_foundation.py`.

Only A+ (220-1201 / 220-1202) is seeded, with a **representative subset** of
objectives (enough to prove uniqueness + version coexistence). The other six
roadmap certifications are not seeded.

### 5. CSV/XLSX importer — extended, not replaced

`app/services/question_importer.py` + `app/routers/admin_question_import.py`:

- New optional template columns: `certification`, `certification_version`,
  `domain`, `module`, `objective_code`, `importance`, `source_name`,
  `source_url`, `permission_status`.
- Writes a `question_v2_meta` row per imported/updated question; resolves
  `certification_version_id` when the `version_key` matches a loaded version
  (unknown/blank key → string kept, FK left NULL, non-fatal).
- `permission_status` blank → `unknown`; `importance` `know_it` → normalised
  to `working_knowledge`.
- New validation in `app/services/question_validation.py` (only fires when the
  key is present): invalid `permission_status` or `importance` makes the row
  **invalid** in preview and **skipped** in confirm.
- **Preserved exactly:** fingerprint dedup, preview/confirm two-phase
  transaction, formula-injection sanitisation, editorial-status gating
  (imports still land draft / unreviewed / student-invisible), and all
  existing question history. A legacy CSV with the old 17 columns imports
  unchanged (its `question_v2_meta` row is created with safe defaults).

### 6. Migration

`backend/alembic/versions/0062_v2_certification_foundation.py`
(`down_revision = 0061_integrated_support_prove`).

- Creates the 9 tables above. Adds **no columns** to any existing table.
- Full, tested `downgrade` (drops the 9 tables). Verified
  `upgrade head → downgrade 0061 → upgrade head` on a fresh SQLite DB.
- SQLite/PostgreSQL-portable (`sa.JSON()`, plain types, `CURRENT_TIMESTAMP`
  server defaults).

---

## Deferred to Phase 1B (documented deferrals)

| Item | Why deferred |
|---|---|
| `short_answer` / `free_response` question types | Needs `acceptable_answers` / `expected_concepts` storage, a rubric model, and grading-path changes. Out of scope for "safe architecture". The validator still accepts only `single` / `multi` / `true_false`. |
| Any AI / rubric / free-response grading | Explicitly excluded from Phase 1A. `pending_grades` / `ai_grades` tables not created. |
| Inlining V2 metadata as real columns on `lessons` / `questions` | Companion tables chosen for safety (see above). Revisit after the week system is retired. |
| Lesson Markdown content loader + resource / interview-prompt loaders | Only the objective loader was needed for the A+ proof-of-concept. Directory convention is sketched in the content standard; loaders come with MVP content. |
| Admin UI for the V2 hierarchy / objective coverage report | No student- or admin-facing surface changed in Phase 1A. |
| `module_assessments` table / assessment-role wiring | Belongs with MVP module build, not the foundation. |
| Publish-time enforcement of `owned` / `permitted` only | Phase 1A records `permission_status`; it does not yet block publishing on it. |
| Backfilling `certification_modules.legacy_training_week_id` from `curriculum_structure` | Bridge columns exist; population is a later migration step. |

---

## Verification performed

| Check | Result |
|---|---|
| New suite `tests/test_v2_certification_foundation.py` | **29 passed** |
| Full backend suite (`pytest -q`) | **584 passed**, exit 0 (no regressions) |
| `ruff check` on all new/changed files | clean |
| `python -m compileall` app / tests / migration | clean |
| Fresh DB `alembic upgrade head` | clean to `0062` |
| `alembic downgrade 0061` then `upgrade head` | clean, tables round-trip |
| Legacy-lineage migration tests (`0057`–`0061` data migrations, historical seed convergence, downgrade/reupgrade) | pass — `lessons` / `questions` schemas untouched |
| `seed_v2_foundation.py` run twice | idempotent (2nd run: 0 created / 0 updated / 40 unchanged) |
| `Lesson` / `Question` / `TrainingWeek` `__table__` column sets | unchanged (guard tests) |
| `a_plus_access.DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT` | still `40`; `A_PLUS_EXAM_CODES` unchanged |
| V2 load + import create zero `training_weeks` / `training_week_activities` rows | asserted |

### Explicit confirmations

- Legacy week system behaves exactly as before — no model, route, seed, or
  gate for `training_weeks` changed.
- The 40% A+ video-watch gate (`a_plus_access.py`) is unchanged and still
  active.
- No student rows were created, migrated, or modified.
- No existing progress, quiz attempts, questions, lab runs, ticket
  submissions, or Service Desk data were deleted or altered.
- No production deployment occurred.
- V2 tables are empty until `seed_v2_foundation.py` is run explicitly; V2 and
  V1 data coexist.

---

## Test-file changes outside the new suite

`tests/test_phase4c3_final_shift.py`: two migration-cycle tests used
`alembic upgrade "head"` and then asserted `alembic_version == "0061..."`.
That conflates "head" with "the revision this phase added". Both were pinned
to `REVISION_0061` (their actual intent), so later additive migrations don't
perturb them. No assertion values changed; the `0060 ↔ 0061` boundary they
exercise is identical.
