# Nexus — Implementation Backlog

**Date:** 2026-07-23 · Baseline `15a9410` · Accepted findings → implementation-sized tasks.
Size: XS/S/M/L/XL. Each task lists priority, scope, likely files, dependencies, acceptance
criteria, tests, and risk.

---

## P1 — do first

### NB-1 · Surface lesson learning objectives (`outcomes`)
- **Size:** S · **Risk:** low
- **Scope:** Objectives are authored for 63/64 lessons but never sent/rendered.
- **Files:** `backend/app/routers/lesson_notes.py` (add `outcomes` to `get_lesson` payload);
  `frontend/src/pages/LessonPage.jsx` (render an "In this lesson you'll learn…" list).
- **Acceptance:** `GET /api/lessons/{id}` returns `outcomes`; lesson page shows objectives.
- **Tests:** backend serialization test; add a `lessons` test file (new coverage).
- **Deps:** none.

### NB-2 · Fix `/service-desk` unavailable-state 404 noise
- **Size:** S · **Risk:** low
- **Scope:** The availability probe 404s (4 console errors) when SD is flag-off.
- **Files:** `backend/app/routers/service_desk.py` (availability endpoint → 200 `{available:false}`);
  `frontend` Service Desk gate to read the flag cleanly.
- **Acceptance:** flag-off student sees "unavailable" with **no console errors**.
- **Tests:** endpoint returns 200 with `available:false`; e2e asserts no console errors.
- **Deps:** none.

### NB-3 · Admin cohort monitoring + per-student drill-down
- **Size:** L · **Risk:** med
- **Scope:** Admin can't see each student's current week, % complete, last-active, at-risk, or a
  per-student week/topic breakdown.
- **Files:** new admin endpoint(s) in `admin_students.py`/`admin_training.py` aggregating training
  progress; `AdminHome.jsx` cohort panel; `AdminStudentsPage.jsx` drill-down.
- **Acceptance:** dashboard lists each student's current week + % + last activity + at-risk flag;
  student page shows week-by-week completion and quiz scores by topic.
- **Tests:** aggregation query tests with fixtures; N+1 guard.
- **Deps:** progress data (reuse training_service).

### NB-4 · Add CI pipeline
- **Size:** M · **Risk:** low
- **Scope:** No `.github/workflows`; tests run manually.
- **Files:** `.github/workflows/ci.yml`.
- **Acceptance:** push/PR runs `pytest -q`, `alembic upgrade head` on a fresh DB,
  `npm ci && npm run build && npm run cli:validate && npm run cli:sanity && npm audit
  --audit-level=high`, `ruff check`, `pip-audit`. Nightly Playwright e2e.
- **Tests:** the pipeline itself.
- **Deps:** none.

### NB-5 · Service Desk end-to-end student walkthrough (validation, not code)
- **Size:** M · **Risk:** low (process)
- **Scope:** Student-side SD never validated live (flag-gated). Before student exposure, enable the
  flag in a controlled test, walk all 5 scenarios in both modes on desktop + mobile.
- **Files:** none (validation task); capture results.
- **Acceptance:** documented pass of all 5 scenarios (Learning + Simulation) desktop + mobile.
- **Deps:** controlled flag enablement. **Blocks Phase 1B.**

---

## P2 — next 30–60 days

### NB-6 · Login rate limiting / lockout
- **Size:** S · **Risk:** low · **Files:** `auth.py`, `admin_session.py`, reuse rate-limiter model.
- **Acceptance:** N failed logins → throttle/lock; test asserts 429/lock. **Deps:** none.

### NB-7 · Admin audit log
- **Size:** M · **Risk:** low · **Files:** new `admin_audit` model + write hooks on mutating admin
  routes + a System view. **Acceptance:** each mutating admin action writes actor/action/target/ts;
  visible under System. **Tests:** mutating call writes a row.

### NB-8 · Merge Command Library into Terminal Practice ("Command Line")
- **Size:** S · **Risk:** low · **Files:** `TerminalCommandsPage.jsx`, nav in `App.jsx`, redirect
  `/commands → /terminal`. **Acceptance:** one page with reference + sandbox; old route redirects.

### NB-9 · SQLite WAL + busy_timeout
- **Size:** XS · **Risk:** low · **Files:** `app/database.py` (connect PRAGMAs).
- **Acceptance:** `journal_mode=WAL`, `busy_timeout=5000`; concurrent-write test passes. **Deps:** none.

### NB-10 · Consolidate progress/XP/mastery into one service boundary
- **Size:** L · **Risk:** med · **Files:** `progression_service`, `xp_*`, `mastery_service`,
  `quiz_progression`, `training_service`. **Acceptance:** single source of truth; golden
  progress/XP fixtures unchanged. **Tests:** regression fixtures.

### NB-11 · Consolidate 3 admin content editors
- **Size:** M · **Risk:** low-med · **Files:** `ModuleManager.jsx`, `CurriculumEditorPage.jsx`,
  `AdminTrainingPage.jsx`. **Acceptance:** clear single editor or delineated roles; validation unchanged.

### NB-12 · Split frontend entry bundle
- **Size:** S · **Risk:** low · **Files:** `vite.config`, lazy heavier student pages.
- **Acceptance:** entry chunk < ~180 kB gzip; build passes.

### NB-13 · Distinguish "attempted" vs "passed"; fix "Great work!" on low scores; coverage vs mastery
- **Size:** S · **Risk:** low · **Files:** `quizzes.py` submit message, Progress UI labels.
- **Acceptance:** message reflects score; Progress separates coverage % from avg-score/mastery.

### NB-14 · Curriculum polish: author lesson 1; collapse optional videos in dense weeks; add early guided labs
- **Size:** M · **Risk:** low · **Files:** seed/content + week-page rendering.
- **Acceptance:** lesson 1 substantive; W2–W4 collapse optional videos; ≥2 new early-week labs.

### NB-15 · Central "My Notes" view
- **Size:** S · **Risk:** low · **Files:** notes list endpoint + a student page.
- **Acceptance:** student can browse all their notes in one place.

### NB-16 · Reconcile deployment docs with actual hosting
- **Size:** S · **Risk:** low · **Files:** `docs/DEPLOYMENT.md`, `CLAUDE.md`.
- **Acceptance:** docs describe the real (Cloudflare/Render or self-host) topology; backup/restore
  runbook verified against the live env.

### NB-17 · Mobile touch targets on All Course Content
- **Size:** S · **Risk:** low · **Files:** `StudyTrackerPage.jsx`/video-row component.
- **Acceptance:** watch toggles/chips ≥ 24×24 (ideally 44) at 375 px.

### NB-18 · Tests for uncovered endpoints (search + gating, flashcards, evidence validator)
- **Size:** M · **Risk:** low · **Files:** new `tests/test_search.py`, `test_flashcards.py`, extend
  evidence tests. **Acceptance:** search excludes gated lessons (regression for the leak); FSRS
  scheduling covered.

---

## P3 — useful improvements

- **NB-19** Fix "24-week" copy (lesson 1 + README). XS.
- **NB-20** Search respects lesson/week gating (also covered by NB-18 test). S.
- **NB-21** Add answer explanations to quiz review (data exists in reference content). S.
- **NB-22** Consolidate module-unlock vs week-gate to one system. M, risk med.
- **NB-23** Remove dead learning-path API + dead lesson `video_url` branch; fix its N+1. XS–S.
- **NB-24** `prefers-reduced-motion` global rule. XS.
- **NB-25** Magic-byte validation for image uploads; de-dup security headers. S.
- **NB-26** Week-0 Document Types ordering (place before quiz). XS.

---

## Future (state prerequisite + measurable value required)
- Service Desk Phase 1B scenarios (after NB-5). · My Training ↔ Service Desk progression
  integration. · More guided labs across all weeks. · PostgreSQL migration (only when SQLite
  triggers hit). · VM/Proxmox/Guacamole/AI expansion (deferred; needs infra, budget, eval controls).

## Suggested first sprint (order)
NB-1 → NB-2 → NB-9 → NB-13 → NB-4 → NB-3 → NB-5. (Quick wins first, then the two structural P1s.)
