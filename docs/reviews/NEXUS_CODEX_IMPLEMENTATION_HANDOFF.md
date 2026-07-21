# Codex Implementation Handoff

Date: 2026-07-21. Phase 17. This document exists so that, once the project
owner approves the Prioritized Action Plan, each fix can be handed to Codex
as a self-contained task per this project's normal workflow. **Nothing in
this document has been implemented.** Task specs below follow the
project's required Codex format (what to build, files to edit, acceptance
criteria).

---

## Task 1 — Fix the A+ unlock gate blocking Week 1 (TICKET-001 / TECH-001, P0)

Two independent options; pick one after owner review:

**Option A (data-only, fastest):** Lower `a_plus_unlock_threshold_pct` via
`PATCH /api/admin/settings/a-plus-unlock` to a value appropriate for cohort
launch (e.g. 0-10%). No code change. Acceptance: a fresh student can submit
Ticket 1 immediately after login.

**Option B (product fix, more durable):** Add a visible, plain-language
explanation of the A+ unlock requirement before a student ever hits the
403 — e.g. a banner on the Tickets/Labs pages showing current progress
toward the threshold, and update the 403 error message to link directly to
the Study Tracker page.
Files: `frontend/src/pages/TicketsPage.jsx`, `LabsPage.jsx`,
`backend/app/services/a_plus_access.py` (for a richer error payload).
Acceptance: a locked student sees their current %, the target %, and a
direct link to make progress — not just a raw error string.

## Task 2 — Week 0 onboarding module (ONBOARD-001, NAV-001/002/003, P1)

Add a short, platform-specific orientation: what Nexus is, what a "week"
means, required vs. optional, XP vs. Role, how ticket grading + mentor
review works, where to get help.
Files: new lesson content in the curriculum source (`seed_phase_a.py` or
equivalent), `frontend/src/pages/StudentHome.jsx` (first-login banner),
`frontend/src/components/WeekPlanPanel.jsx` (Week 0 framing copy).
Acceptance: a fresh student's first Home-page view includes an explicit
welcome/orientation element; Week 0's panel explicitly states "this is all
of Week 0."

## Task 3 — Capstone role-gate data fix (CUR-002 / NAV-004, P1)

Set `role_level` on the 3 live `CapstoneTemplate` rows to the intended gate
tier (e.g. capstone 1 → Support Technician I, capstone 2 → Network Support
Technician, capstone 3 → Junior Systems Technician, adjust to the mentor's
actual intent).
Files: admin capstone-template edit UI, or a one-off data migration/admin
API call.
Acceptance: a fresh 0-XP student's `has_unlocked_capstones` returns `false`
and the Capstones nav item is hidden.

## Task 4 — Week 1 lesson (LESSON-001, P1) — SUPERSEDED, DO NOT RUN

Live verification during the Pre-Week-0 Launch Readiness Sprint (2026-07-21)
found this task's premise false: MOD-001's two existing lessons ("Anatomy of
a Good Ticket", "Meet the Command Line") were already served as Week 1
content. Writing a new lesson here would create duplicate/conflicting
curriculum. The real defect (a cosmetic-only Learning Path lock on MOD-001)
was fixed instead via `backend/alembic/versions/0030_week_gating_data_fixes.py`.
See `NEXUS_FINDINGS.csv` and `NEXUS_LESSON_REVIEW.md`.

## Task 5 — Lab XP/review parity (CUR-001 / ENGAGE-002 / LEARN-003, P2)

Add XP award (and/or a mentor-review gate matching the ticket flow) to lab
submission.
Files: `backend/app/routers/labs.py` (`submit_lab`), `XPLedger` write,
optionally an admin lab-review endpoint mirroring `verify-proof`/
`reject-proof`.
Acceptance: a submitted, verified lab visibly grants XP to the student, and
(if the review gate is added) an unverified lab shows the same "awaiting
instructor verification" pattern tickets already use.

## Task 6 — Terminal Practice / Command Library / Networking Labs
   consolidation (LAB-001 / NAV-007, P2)

Either wire `TerminalWidget` (`frontend/src/components/Terminal.jsx`) to the
existing CLI-lab simulator backend, or remove the `/terminal` nav item and
fold its command-search UI into Command Library.
Files: `frontend/src/App.jsx`, `frontend/src/pages/TerminalCommandsPage.jsx`,
`frontend/src/components/Terminal.jsx`.
Acceptance: no two nav items present functionally identical content; if
kept, the terminal widget executes real (simulated) commands.

## Task 7 — Screenshot evidence validation cleanup (LAB-002 / TECH-004, P2)

Either implement lightweight OCR-based text checking for
`artifact_type == "screenshot"` in `evidence_validator.py`, or remove
`must_contain_text` from screenshot-type `required_evidence` definitions in
the ticket/lab data so the schema stops promising an unimplemented check.
Files: `backend/app/services/evidence_validator.py`, ticket/lab seed data.
Acceptance: either a screenshot's required text is actually checked, or the
data no longer claims it will be.

## Task 8 — Quiz quality labeling (QUIZ-001, P2) — SUPERSEDED, not launch-relevant

Live student-account testing (Pre-Week-0 Launch Readiness Sprint,
2026-07-21) confirmed unvalidated quizzes are already invisible and
unattemptable to students (list, detail, and direct-submit all excluded/
404). No student-facing labeling fix is needed before launch. See
`NEXUS_FINDINGS.csv` and the addendum in `NEXUS_QUIZ_REVIEW.md`. The content-
quality corrections below remain a legitimate post-launch improvement:

Add a visible "practice — answers not yet verified" label to quizzes with
`answer_keys_validated: false`, or run the existing
`apply_quiz_answer_corrections.py --confirm` pass after owner review of its
dry-run output.
Files: frontend quiz list/detail components; existing script at
`backend/scripts/apply_quiz_answer_corrections.py`.
Acceptance: a student can visually distinguish a validated quiz from an
unvalidated one before attempting it.

## Task 9 — Ticket-list status glosses + rate-limit error message (NAV-005,
   TICKET-004/TECH-002, P2/P3)

Add a plain-language pill/tooltip next to raw status words on the Tickets
list; catch the rate-limit exception in `submit_ticket()` specifically and
return a proper `429` with friendly copy instead of a wrapped `500`.
Files: `frontend/src/pages/TicketsPage.jsx`, `backend/app/routers/
tickets.py`.
Acceptance: "needs_revision"/"pending" have a one-line explanation visible
on the list; hitting the daily AI-grading cap returns a clear 429, not a
500.

## Task 10 — Accessibility baseline (ACCESS-001/002/003/004, P2/P3)

Add a skip-to-content link, an app-wide focus-visible utility class, alt
text on the evidence-screenshot lightbox image, and labels on remaining
placeholder-only inputs.
Files: `frontend/src/App.jsx` (skip link), a shared Tailwind
focus-visible utility, `frontend/src/pages/TicketFeedback.jsx` (alt text),
and any component identified as unlabeled during implementation.
Acceptance: keyboard-only tab order includes a skip link; focus is visibly
indicated app-wide; the evidence image has descriptive alt text.

---

Each task above should go through the project's standard loop: Claude plans
→ Codex implements → `/review` → verify against acceptance criteria →
`tasks/loop-log.md` entry — **only after the project owner has approved
which tasks to run**, per this review's explicit constraint.
