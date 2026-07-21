# Pre-Week-0 Launch Readiness Sprint — Live Functional Verification

Date: 2026-07-21. Two live verification passes were run against the
implemented fixes, both using a disposable student account created via the
supported `POST /api/admin/students` endpoint and a disposable admin
session — never direct DB writes, never printed credentials. Both accounts
and all their owned rows were deleted before this document was written.

## Important limitation: no rendered browser was available

This environment has no working browser. Playwright is installed in
`backend/.venv` but its bundled Chromium does not support this sandbox's
Ubuntu version (`playwright install chromium` fails with "Playwright does
not support chromium on ubuntu26.04-x64"); no system Chrome/Chromium/Firefox
is installed; and the sandbox blocks binding to `localhost`, so neither
`uvicorn` nor a Vite dev server could even be served for a remote browser to
connect to. **No screenshots exist for this sprint.** Every checklist item
below marked NOT VERIFIED reflects this constraint honestly rather than
being reported as passed. Desktop/mobile visual review (button prominence,
text wrapping, overflow at ~375px, information density) was **not**
performed and should be done in a browser-capable environment before a
broader launch beyond the five-student cohort.

What **was** verified: real HTTP requests against the actual FastAPI
application object (via an in-process ASGI client, working against a copied
SQLite database — the real `backend/nexus.db` was never touched by either
verification pass), exercising the exact same routers, dependencies, and
business logic that runs in production. This confirms functional
correctness end-to-end; it does not confirm visual rendering.

## Round 1 (pre-fix)

Setup identical to Round 2 (below). Findings:

| # | Check | Result |
|---|---|---|
| 1 | Disposable student login | PASS — HTTP 200 |
| 2 | First-login Home banner | NOT VERIFIED (no browser); API confirmed `onboarding.is_fresh: true` + correct lesson route |
| 3 | Home/Week Plan point to same Week 0 lesson | PASS |
| 4 | Orientation lesson + guided-practice panel render | NOT VERIFIED (no browser); API returned correct lesson content |
| 5 | Lesson note save + reload persists | PASS |
| 6 | Ticketing Systems Quiz submission | PASS — 4/4 |
| 7 | Practice response save, zero-stakes messaging | PASS |
| 8 | Orientation sample upload, orientation-only labeling | PASS |
| 9 | Onboarding `is_complete` + Week 1 next action | PASS |
| 10 | Week 1 next action is a lesson, ordered before tickets/quiz | PASS |
| 11 | First Week 1 ticket accessible at 0% A+ video progress | **FAIL** — ticket detail loaded, but a hint/action request 403'd with "Complete Week 0's required lesson first," an unmentioned second Week 0 lesson requirement the completed walkthrough never surfaced |
| 12 | Later-week (Week 3) ticket shows a clear locked state on direct access | **FAIL** — direct ticket detail GET returned full content with no lock; the structured lock only appeared on a hint/submit attempt |
| 13 | Fresh student cannot open any capstone | PASS — empty list, `has_unlocked_capstones` false |
| 14 | Unvalidated quiz not visible/attemptable | PASS — 404 on list, detail, and direct submit |
| 15 | Mentor activity absent from student squad feed | PASS |
| 16 | Logout/login | PASS |
| 17 | Admin: onboarding progress inspectable | **FAIL** — not exposed on the existing admin student-activity view |
| 18 | Admin: ticket review / capstone mgmt / quiz editorial queue load | PASS |
| 19 | Admin: capstone role_level corrected, non-null | PASS (2, 3, 5) |

Two real defects (#11, #17) and one deferred, non-regression item (#12,
explained below) were found. See `PRE_WEEK_ZERO_IMPLEMENTATION_REPORT.md`
§3/§5 for the fixes applied to #11 and #17.

## Round 2 (post-fix, this sprint's final state)

Re-ran independently (not just re-trusting the fix's self-report) via the
full backend test suite plus a direct DB read confirming the live
`MOD-000` lesson set matches the fixture used in the new regression test
exactly (`Welcome to Nexus: Your First Week` id 64 order 1, `CompTIA
6-Step Process` id 1 order 2). The new regression test
`test_orientation_completion_reports_the_remaining_week_zero_lesson_until_week_one_unlocks`
reproduces the Round 1 #11 scenario exactly — lesson note + quiz + practice
done, `is_complete: true`, Week 1 ticket hint blocked with the structured
403 — and then proves the fix: saving a note on the second lesson flips
`week_one_unlocked` to `true` and the same ticket hint request immediately
succeeds. `test_admin_activity_includes_student_onboarding_progress`
confirms #17 is closed. Full suite: **188 passed, 0 failed**.

#12 was deliberately **not** fixed this round: tracing it confirmed ticket
detail (`GET`, read-only) has never been gated, in either the old A+ system
or the new week-based one — only mutating actions (hint reveal, submit)
were ever gated. A Week 3 ticket is also not visible in a Week 1 student's
default ticket list (which defaults to the current week) — reaching it
requires guessing or knowing a specific ID ahead of time. This is a minor,
pre-existing content-preview gap, not a hands-on-work bypass (no XP, no
grading, no credit is obtainable without a successful submit), and is
carried to the deferred-findings list rather than fixed in this sprint to
avoid scope creep into read-path gating that was never part of the original
A+-gate defect.

## What would still benefit from a real browser pass

Recommended before a wider-than-five-student launch, not blocking for the
five-student cohort given the API-level verification above: rendered
desktop and ~375px mobile screenshots of the Home welcome banner, Week Plan
panel, orientation practice panel, and locked-state banners, to check
wrapping, overflow, and button reachability — none of which could be
inspected in this environment.
