# Phase 12 — Code Quality

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** Source inspection (28 routers / 30 models / 37 services / frontend) + grep-based smell
survey. Ruff not installed in the review env (backend lint **not run** — CI gap noted below).

## Overall health
Codebase is **clean and disciplined**: 238 backend tests pass, **0 TODO/FIXME/HACK markers**,
consistent `ok()`-wrapped responses, layered routers→services→models, strong typing on models,
39 unique constraints, all FKs with ON DELETE. This is not a codebase in distress — the refactors
below are consolidation/clarity, not rescue.

## Confirmed smells
- **Oversized modules:** `services/training_service.py` **870 LOC** (~20 functions, grab-bag),
  `features/cli-labs/engine/commandEngine.js` **930 LOC**; large routers `students.py` (719, **49
  `db.query` calls**) and `admin_content.py` (681).
- **N+1 queries:** loop-based per-item counts — clearest in the (dead) learning-path endpoint,
  which runs per-lesson quiz/ticket/note count queries inside a module→lesson loop. Similar
  patterns in `students.py`/`training_service.py`.
- **Duplicated business logic:**
  - Progress/XP/mastery spread across `progression_service`, `quiz_progression`, `xp_service` +
    `xp_calculator` + `xp_ledger`, `mastery_service`, and progress inside `training_service`.
  - **Two unlock systems:** module-unlock (lesson pages) vs week-gate (My Training).
  - Three admin content editors (Module Manager / Curriculum Editor / Weekly Training).
- **Dead code (narrow):** `GET /api/students/{id}/learning-path` (no frontend caller);
  `LessonPage` YouTube-embed branch (`video_url` null for all 64 lessons).
- **Dormant (NOT dead) — config/flag-gated:** `guacamole_service`, `proxmox_service`,
  `cve_service`, `discord_service` (used by `xp_service` milestones), `vm_assignment` +
  "Labs & VM Assignments". These are wired but inert without config/VM infra. Keep, but clearly
  flag as "not yet available" so they don't read as finished features.
- **Hidden-data bug:** lesson `outcomes` authored but never serialized/rendered (Phase 6).

## Ten highest-value refactors (value-ranked)

1. **Serialize + render lesson `outcomes`.** *Why:* objectives authored for 63/64 lessons are
   invisible. *Files:* `routers/lesson_notes.py`, `pages/LessonPage.jsx`. *Risk:* low. *Effort:* XS.
   *Test:* API returns outcomes; page shows them.
2. **Fix `/service-desk` unavailable-state 404s** (probe → 200 `{available:false}`). *Why:* console
   errors + noise. *Files:* `service_desk` router + frontend gate. *Risk:* low. *Effort:* S.
3. **Unify progress/XP/mastery into one service boundary.** *Why:* divergence/double-count risk
   across 5+ modules. *Files:* `progression_service`, `xp_*`, `mastery_service`, `quiz_progression`,
   `training_service`. *Risk:* med (touches scoring) — do behind tests. *Effort:* L. *Test:* golden
   progress/XP fixtures unchanged.
4. **Consolidate the two unlock systems** (module-unlock vs week-gate) to one source of truth.
   *Files:* `lesson_notes.py`, `training_service.py`, progression. *Risk:* med. *Effort:* M.
   *Test:* lesson access == week access for the same content.
5. **Remove the dead learning-path endpoint + its N+1.** *Files:* `students.py`. *Risk:* low
   (no caller). *Effort:* XS. *Test:* route gone; suite green.
6. **Fix remaining N+1 counts** with aggregate/join queries. *Files:* `students.py`,
   `training_service.py`. *Risk:* low. *Effort:* S–M. *Test:* query-count assertions.
7. **Split `training_service.py` (870)** into cohesive services (dashboard, week, progress,
   next-activity). *Risk:* med. *Effort:* M. *Test:* existing training tests green.
8. **Split `students.py` router (719)** — extract service functions; group endpoints. *Risk:* low.
   *Effort:* M. *Test:* suite green.
9. **Consolidate/relabel the 3 admin content editors.** *Why:* owner-operator confusion,
   inconsistent edits. *Files:* `ModuleManager`, `CurriculumEditorPage`, `AdminTrainingPage`.
   *Risk:* low–med. *Effort:* M. *Test:* content-validation unchanged.
10. **Split `commandEngine.js` (930)** into parser / state / renderer modules. *Files:*
    `features/cli-labs/engine/`. *Risk:* med (drives 48 labs). *Effort:* M. *Test:* `cli:validate`
    + `cli:sanity` + the CLI e2e spec.

*(Cross-listed from Phase 10, not counted above: login rate-limiting + admin audit log.)*

## Not recommended
- **No application rewrite.** The architecture is sound; incremental consolidation is the right path.
- Don't delete dormant deferred services — flag them "unavailable" instead (they're partially wired).

## CI / tooling gaps
- **Backend lint not enforced in the review env** (Ruff needs `requirements-dev`). Add
  `ruff check` + `pip-audit` to CI.
- Add DB **query-count** assertions to lock in N+1 fixes.

## Priorities
- P1: #1 (outcomes), #2 (SD 404s). P2: #3–#9 (consolidation) + CI lint/audit. P3: #10, dead-code
  removal.
