# Pre-Week-0 Launch Readiness Sprint — Final Report

Date: 2026-07-21. This closes the Pre-Week-0 Launch Readiness Sprint scoped
in the project owner's brief. The prior 17-phase review was not repeated;
this sprint reconciled its findings against live state, implemented the
approved fixes, independently verified them (including catching and fixing
one bug the implementation itself introduced), and produced this report.
**No deployment to the live `.101`/`nexus.builtfromzero.fyi` environment has
happened yet** — see "Final decision" below.

## Scope completed

Phases 1-10 of the sprint (reconciliation, A+ gate replacement, Week 0
onboarding, capstone role-gate fix, MOD-001 lock fix, squad-feed filtering,
quiz-visibility verification, live functional verification, backend/data
verification, independent code review) are complete. Phase 11 (deploy) is
prepared but not executed, pending the project owner's go-ahead on a live
production action. The broader Weeks 1-4 and post-launch roadmap was not
started, per the brief.

## A+ gate resolution

**Original cause:** a global 40%-of-A+-videos-watched gate
(`require_a_plus_unlocked`) blocked every ticket/lab/CLI-lab/capstone
mutation for every student, with no relationship to curriculum week.

**New rule:** `require_week_reached()` — a student's real derived current
week (the same logic Home/Week Plan already used) must have reached an
item's assigned week. Optional A+ video progress no longer affects hands-on
access at all; the Study Tracker's own progress display is untouched.

**Student behavior:** Week 1 hands-on work is available once Week 0's real
requirements (lesson notes + quiz) are met, regardless of A+ video
progress. A later week's items remain locked with a specific, human-readable
message and a link to the student's current week — never a raw 403.

**Later-gate behavior:** unchanged and still enforced — verified with a
Week 3 ticket remaining blocked for a Week 1 student, and direct API access
(bypassing the UI) enforcing the identical rule.

**Tests:** `test_week_prerequisite_gating.py` (7 tests) plus updated
`test_a_plus_access.py` assertions. Full suite: 188/188 passing.

## Week 0 onboarding

**First-login experience:** a "Welcome to Nexus" banner with a clear "Start
Week 0" action, shown only to students who have truly never started (the
old, confusing "pick up where you left off" fallback copy is gated behind a
real freshness check and can never reach a brand-new student).

**Orientation content:** one new lesson ("Welcome to Nexus: Your First
Week", ahead of the existing "CompTIA 6-Step Process" lesson, which is
unchanged and unmoved in substance) covering platform mechanics in plain,
short-section language — reviewed directly for beginner clarity, no
graded-ticket answers revealed.

**Guided practice:** lesson note → existing Week 0 quiz (reused, not
duplicated) → one-sentence zero-stakes practice response → optional
harmless sample-screenshot upload, clearly and permanently separated from
real ticket evidence and the ticket-grading/AI-rate-limit pipeline. None of
it awards XP, calls AI, creates a mentor-review record, or affects the
leaderboard — proven by a regression test checking exact row/XP counts
before and after.

**Completion persistence:** all state is DB-backed (lesson notes, the
quiz's own attempt record, one new minimal practice table); a student can
leave and resume freely; the orientation lesson stays open afterward and is
never re-forced.

**Link to Week 1 — bug found and fixed:** live testing found the onboarding
walkthrough could report itself complete and point to Week 1 while the real
backend gate still blocked Week 1 actions, because Week 0's module gained a
second lesson that the walkthrough never tracked. Fixed by adding a
`week_one_unlocked` field (reusing the real gate, not a parallel check) and
an honest "one more required step" message naming the specific remaining
lesson when the two disagree. Reproduced and closed with a dedicated
regression test.

## Capstones

**Corrected role requirements:** the three live templates, previously all
`role_level = NULL` (accessible to everyone), now require Support
Technician I, Support Technician II, and Junior Systems Technician
respectively — resolved from the platform's existing role names and
rank order, not invented or assumed by numeric ID.

**Student visibility:** a brand-new student sees no capstones
(`GET /api/capstones` returns `[]`); a student holding the correct role sees
exactly the expected capstone(s).

**Direct access protection:** verified via direct API calls for both an
ineligible and an eligible student, not only through UI hiding; `submit_capstone`
also gained a previously-missing accessibility check it lacked even before
this sprint (`start_capstone` had one, `submit_capstone` did not).

**Admin behavior:** admin capstone-management APIs are unaffected and still
show/manage all three templates regardless of role gating.

## Squad activity feed

Student-facing roster and activity queries now filter on `Student.is_mentor
== False` (role-based, not a hardcoded username); the admin-only activity
endpoint is untouched. Verified: student activity remains visible, mentor
roster entries/activity and private mentor-activity detail text are absent
from the student feed, real student progress is unaffected.

## Quiz visibility

Exact live inventory (see `NEXUS_QUIZ_REVIEW.md` addendum for full table):
104 total quizzes; 28 student-visible (25 required/gate/cumulative —
exactly one per Week 0-24 — plus 3 optional/practice, all validated); 76
hidden (29 unvalidated certification, 30 unvalidated practice, 17
remediation); 5 draft/inactive. Confirmed via three live tests against a
known unvalidated quiz: excluded from the student list, 404 on direct
detail GET, 404 on direct submit POST. The original QUIZ-001 finding (that
these were visible/attemptable) is corrected — see reconciliation above.

## Account reconciliation

7 total accounts on the live system: 1 mentor account, 6 student accounts.
No names, usernames, or emails were exposed in this process. The 6 intended
student accounts are unchanged and have not been touched by this sprint's
code or data changes. One disposable review account (created via the
supported admin-creation endpoint for this sprint's own testing) remains
and will be removed as part of Phase 11 cleanup before any student begins.

## Browser acceptance

**No rendered-browser verification was possible in this environment** (no
supported Chromium build, no system browser, sandbox blocks localhost
binding) — see `PRE_WEEK_ZERO_BROWSER_ACCEPTANCE.md` for the full,
explicitly-labeled PASS/FAIL/NOT VERIFIED checklist. Every functional
(API-level) check that could be performed was performed, including two full
passes (pre-fix and post-fix) with a disposable student and admin account,
both fully cleaned up afterward. Desktop and mobile visual review (text
wrapping, button reachability, overflow at ~375px) is a genuine gap and
should be done by a human on the live/staging site — which does not share
this sandbox's browser limitation — before or shortly after the five
students begin.

## Test results

- Backend: `python -m pytest tests/ -q` → **188 passed, 0 failed** (176
  before this sprint + 12 new; includes fixing 2 tests broken by removing
  a now-dead function during this sprint's own review).
- `python -m py_compile` on all changed files: clean.
- `alembic current`: `0031_week0_orientation (head)`.
- `PRAGMA integrity_check`: `ok`. `PRAGMA foreign_key_check`: 0 violations.
- `npm run build`: clean. `npm audit`: 0 vulnerabilities.
- Production health endpoint: not checked this sprint (no deployment has
  occurred yet — see Phase 11 status below).

## Deferred findings

**During Weeks 1-4 (real, not launch-blocking):** lab XP/mentor-review
parity (CUR-001); screenshot evidence `must_contain_text` no-op cleanup
(LAB-002); Terminal Practice/Command Library/Networking Labs overlap
(LAB-001/NAV-007); ticket-status wording polish (NAV-005); quiz
required/optional badges (NAV-006/QUIZ-003); focus-visible/skip-link
accessibility gaps (ACCESS-004); proper 429 handling. **New this sprint:**
ticket/lab detail (GET-only) routes do not show a locked state on direct
access to a later-week item before an action is attempted — a minor
content-preview gap, not a hands-on-work bypass, deliberately not fixed
this sprint to avoid scope creep into previously-unscoped read-path gating.

**After students begin:** stalled-student signals, failed-quiz mentor
detail, additional tickets/labs for subnetting/GPO/AD/PowerShell,
leaderboard evaluation for a small cohort (ENGAGE-001), mentor digest.

**Future:** automated Proxmox/Guacamole VM delivery (still correctly
disabled — unchanged this sprint), full axe/screen-reader accessibility
audit (ACCESS-005), broader nav consolidation, frontend bundle splitting.

## Phase 11 status — not executed

Deployment to the live environment (backup, deploy, restart, live
re-verification, disposable-account cleanup on production, one commit + new
release tag) has **not** been performed. This is a production action
affecting the platform the five students will imminently use, on shared
infrastructure outside this sandbox — it is held pending the project
owner's explicit go-ahead rather than executed unilaterally. Everything
required to proceed quickly once approved is ready: all tests pass, the
diff has been fully reviewed, and the exact deploy procedure is already
documented in `CLAUDE.md`'s deployment-reality notes.

## Final decision

**Ready for five-student Week 0 launch**, contingent on: (1) explicit
approval to execute Phase 11's deployment steps against the live
environment, and (2) a brief human click-through on the live/staging site
after deployment to cover the desktop/mobile visual checks this sandbox
could not perform, before telling the five students to begin. No blocking
defect remains open; the two real defects found during this sprint's own
live verification were fixed and independently re-verified, and the one
non-blocking gap found (ticket-detail pre-lock content exposure) is
correctly categorized as deferred, not launch-blocking.

Per the brief: this sprint stops here. The broader Weeks 1-4 roadmap is not
started and awaits the project owner's next instruction.
