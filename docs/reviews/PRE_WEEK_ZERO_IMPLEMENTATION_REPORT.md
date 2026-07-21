# Pre-Week-0 Launch Readiness Sprint — Implementation Report

Date: 2026-07-21. Scope: fix the confirmed pre-launch defects from the prior
17-phase review before the five real students begin Week 0. This sprint did
**not** repeat that review; it reconciled its findings against live
code/DB/API state, implemented the approved fixes, and independently
verified them. The broader Weeks 1-4 backlog was explicitly out of scope and
was not started.

---

## 1. Reconciliation corrections (Phase 1)

Two of the original review's findings were re-verified live this sprint and
found **not to hold as originally written**. Both are corrected in
`NEXUS_FINDINGS.csv` (marked SUPERSEDED, not deleted) and in the specific
detail docs that gave actionable instructions based on them
(`NEXUS_LESSON_REVIEW.md`, `NEXUS_QUIZ_REVIEW.md`,
`NEXUS_PRIORITIZED_ACTION_PLAN.md`, `NEXUS_CODEX_IMPLEMENTATION_HANDOFF.md`):

- **LESSON-001** ("Week 1 has zero lessons") was false. `MOD-001`'s two
  existing lessons were already served as Week 1 content by the live
  week-plan API; the "0 lessons" reading came from the curriculum-dump
  script's own ad-hoc week headers, not the platform's real week logic. The
  real defect in the same area — a cosmetic-only Learning Path lock on
  `MOD-001` caused by an unsatisfiable prerequisite on `MOD-000` (which has
  no lesson-linked quiz/ticket/lab, so its mastery is permanently 0%) — was
  fixed instead. No new lesson was written.
- **QUIZ-001** ("unvalidated quizzes are visible/attemptable") was false.
  Live student-account testing (list, direct detail GET, direct submit POST
  against a known `needs_edit` quiz) confirmed `student_visible_quiz_filters()`
  already excludes unvalidated quizzes uniformly across every student-facing
  route. See the addendum in `NEXUS_QUIZ_REVIEW.md` for the full inventory.

Finding-ID normalization (44 primary + 4 technical-alias rows,
`NEXUS_FINDINGS.csv`) and the account-count reconciliation (7 total accounts:
1 mentor + 6 students; no names/credentials exposed) were completed and are
unchanged from the earlier session note in `CLAUDE.md`.

## 2. A+ gate replacement (Phases 2, 4, 5)

**Root cause of the original P0 finding:** `require_a_plus_unlocked()`
gated every ticket/lab/CLI-lab/capstone mutation behind a global 40%-of-137-
A+-videos-watched threshold, with no relationship to curriculum week and no
in-app explanation.

**New rule:** `require_week_reached(db, student, required_week)` in
`backend/app/services/progression_service.py`, reusing the platform's
existing, correct `derive_current_week()` week-derivation logic (the same
logic that already drove Home/Week Plan). It replaces every
`require_a_plus_unlocked()` call site in `tickets.py`, `labs.py`,
`cli_labs.py`, `capstones.py`, and `evidence.py`. On failure it raises a
structured `403` (`code: "PREREQUISITE_NOT_MET"`, `error`, `data:
{required_week, current_week, next_action_route}`) instead of a raw message;
the frontend's new `PrerequisiteLock` component renders this as a
human-readable banner with a link to the student's actual current week.
Mentors always pass. The now-dead `require_a_plus_unlocked()` function and
its orphaned frontend counterpart (`APlusPreviewLock.jsx`) were removed; the
Study Tracker's own progress display (`get_a_plus_progress`,
`get/set_a_plus_unlock_threshold`) is unrelated and was kept — the A+
tracker itself is unaffected, only its former role as a hands-on-work gate
is gone.

**Data fixes** (`backend/alembic/versions/0030_week_gating_data_fixes.py`):
`MOD-001`'s unsatisfiable prerequisite on `MOD-000` was nulled (guarded to
only apply if it currently equals `MOD-000`'s id). The three live
`CapstoneTemplate` rows' `role_level` (previously all `NULL`, making
capstones accessible to every student from day one) were set by resolving
existing role name + rank_order — not assumed numeric IDs — to: Module 1
Capstone → Support Technician I (rank 2), Module 2 Capstone → Support
Technician II (rank 3), "Take Over Maple & Finch Co." → Junior Systems
Technician (rank 5).

**Verified student behavior:**
- Fresh student: Week 1 hands-on work is available once Week 0's real
  requirements (lesson notes + required quiz) are met — not gated by A+
  video progress at all.
- A student with 0% A+ video progress can submit Week 1 tickets/labs/CLI
  labs.
- A later-week item (e.g. Week 3) remains locked with a clear message
  ("You'll unlock this once you reach Week 3") and a link back to the
  current week.
- Direct API access (no UI involved) enforces the identical rule — proven
  by regression tests calling routes directly.
- Fresh trainee cannot open any capstone (`has_unlocked_capstones` is
  `false`, `GET /api/capstones` returns `[]`); a student holding the correct
  role sees exactly the 3 capstones as intended, verified via direct API
  call, not just UI hiding.

**Tests added:** `backend/tests/test_week_prerequisite_gating.py` (fresh
lock with exact structured-403 contract, direct-API-cannot-bypass, passing
Week 0 unlocks Week 1, later-week lock, A+ video progress never changes
hands-on access, `MOD-001` unlock-fix regression, capstone role-level
gating for both an ineligible and an eligible student). `test_a_plus_access.py`
was updated to assert the new, intended behavior (hands-on mutations no
longer blocked by A+ progress) rather than the old one.

## 3. Week 0 platform onboarding (Phase 3)

Added one new lesson, "Welcome to Nexus: Your First Week" (`MOD-000`,
`lesson_order=1`; the existing "CompTIA 6-Step Process" lesson moved to
`lesson_order=2`, content unchanged) — see
`backend/alembic/versions/0031_week0_orientation.py` for the exact prose,
reviewed by Claude directly for beginner clarity. It covers, in plain
language and short sections: what Nexus is and what a week means; the four
content types (lesson/quiz/lab/ticket); required vs. optional; evidence and
remediation; XP vs. Role; how AI grading + mentor review + "needs revision"
work; where to ask for help; the weekly routine; and a guided-practice
walkthrough. It does not reveal any graded-ticket answers.

**Guided practice** (`OrientationPracticePanel.jsx`, `onboarding.py` router,
`onboarding_service.py`, one new minimal model `StudentOnboardingPractice`):
save a lesson note → take the existing Week 0 "Ticketing Systems Quiz" (no
new quiz was created) → save a one-sentence zero-stakes practice response →
optionally upload a harmless sample screenshot via a new,
clearly-separate `POST /api/evidence/orientation-upload` endpoint
(`submission_type="orientation"`, never touches ticket evidence or the
ticket-grading/AI-rate-limit pipeline). None of this creates XP, an AI call,
a mentor-review record, a leaderboard event, or a promotion-gate record —
confirmed both by code comment and by a regression test asserting XP,
`AIRateLimit`, and `TicketSubmission` row counts are unchanged after
completing the practice step.

Home's first-login experience (`StudentHome.jsx`, `WeekPlanPanel.jsx`) now
shows a "Welcome to Nexus" banner with a clear "Start Week 0" action for a
fresh student, and the previous NAV-003 "pick up where you left off" default
copy is gated behind `!isFresh` so it can never be shown to a student who
has never started (verified directly: a fresh student's full stats payload
contains no such string).

Progress persists in the DB (`StudentLessonNote`, the quiz's own
`QuizAttempt`, `StudentOnboardingPractice`) — a student can leave and resume
at any point, and the orientation lesson remains open in the Learning Path
afterward (it is never hidden or force-repeated).

### Bug found and fixed during Phase 8 live verification

Live API testing surfaced a real defect not caught by the original test
suite: completing the onboarding walkthrough (lesson note + quiz + practice)
reported `is_complete: true` and displayed a "Continue to Week 1" call to
action — but the platform's real prerequisite gate (`require_week_reached`)
still blocked Week 1 ticket actions, because `derive_current_week()`
requires a lesson note on **every** published lesson in Week 0's module, and
`MOD-000` now has two lessons (the new orientation lesson and the
pre-existing "CompTIA 6-Step Process"), while the onboarding walkthrough
only ever tracked the first one. Home was, in effect, recommending a task
the backend would reject — exactly the failure mode this sprint's own
Phase 2 spec called out to avoid.

**Fix:** `get_orientation_state()` now also reports `week_one_unlocked`
(`derive_current_week(...) >= 1`, reusing the real gate — no parallel logic)
and, when the walkthrough is done but the real gate isn't yet satisfied,
`week_one_remaining_lessons` naming the specific incomplete Week 0 lesson(s)
and their routes. `OrientationPracticePanel.jsx` only shows the "Continue to
Week 1" success state when both are true; otherwise it shows an honest
"one more required Week 0 step remains" message linking directly to the
named lesson. The CompTIA lesson's requirement itself was not weakened or
removed — it is legitimate curriculum. A new regression test
(`test_orientation_completion_reports_the_remaining_week_zero_lesson_until_week_one_unlocks`)
reproduces the exact live failure end-to-end and proves the fix: blocked
before the second lesson's note is saved, unlocked immediately after.

## 4. Squad activity feed (Phase 6)

`squad_dashboard()` in `students.py` now filters both its `members` roster
and its `activity_feed` query on `Student.is_mentor.is_(False)` — a
role-based filter, not a hardcoded username. The admin-only
`/api/admin/squad/activity` endpoint is unchanged and still shows mentor
activity for legitimate admin oversight. Verified via
`test_squad_dashboard.py`: student activity remains visible, mentor
activity/roster entries and private mentor-activity detail text are absent
from the student-facing feed, and the admin feed is unaffected.

## 5. Admin visibility addition (Phase 8 admin checklist)

`GET /api/admin/students/{id}/activity` now includes the student's
onboarding progress (`get_orientation_state()`, reused — not duplicated) so
a mentor/admin can inspect a student's Week 0 walkthrough status from an
existing admin view. Additive only; the endpoint's existing auth
(`verify_admin`, router-level dependency) and response fields are
unchanged. Verified via `test_admin_activity_includes_student_onboarding_progress`.

## 6. Verification performed

- `python -m py_compile` on every changed backend file: clean.
- `python -m pytest tests/ -q`: **188 passed, 0 failed** (up from 176 before
  this sprint; includes all new regression tests). One pre-existing
  regression was found and fixed during independent review: two tests in
  `test_security_hardening.py` referenced the now-removed
  `require_a_plus_unlocked` via `monkeypatch.setattr`, which raised
  `AttributeError` once the function was deleted — the monkeypatch lines
  were obsolete leftovers (the endpoint under test never called that
  function even before this sprint) and were removed.
- `alembic current`: `0031_week0_orientation (head)`.
- `PRAGMA integrity_check`: `ok`. `PRAGMA foreign_key_check`: 0 violations.
- `npm run build`: clean (pre-existing bundle-size warning only, unrelated
  to this sprint).
- `npm audit`: 0 vulnerabilities.
- Dead code removed as part of this sprint's own review (not a separate
  task): `require_a_plus_unlocked()` (backend/app/services/a_plus_access.py)
  and `APlusPreviewLock.jsx` (frontend), both fully orphaned after every
  call site was migrated to the new gate.

See `PRE_WEEK_ZERO_BROWSER_ACCEPTANCE.md` for the live functional
verification pass (desktop/API-level; no rendered-browser check was
possible in this environment) and `PRE_WEEK_ZERO_FINAL_READINESS.md` for
the overall launch recommendation.
