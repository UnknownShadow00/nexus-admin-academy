# Nexus Learning — Full Project Review Plan

This document is the single source of truth for the review. Do not re-paste
phases into chat — read this file directly.

**Execution model:** One phase per session/turn. After completing a phase,
write its report file, update the Progress Tracker below, then **stop and
summarize findings in chat** before starting the next phase. Do not
auto-continue through multiple phases unless explicitly told to batch them.

---

## Progress Tracker

Update this table after every phase. Do not skip updating it.

| Phase | Name | Status | Report File | Date | Notes |
|---|---|---|---|---|---|
| 0 | Preconditions | Complete — all GREEN | `docs/reviews/phase-00-preconditions.md` | 2026-07-23 | Browser automation verified against prod (real login/admin/student renders). Baseline 15a9410. Admin = current account (in-memory from .env, authorized). Throwaway student id=8 created (delete in Phase 16). Cloudflare/Render vs. documented self-host discrepancy noted. |
| 1 | Baseline | Complete | `docs/reviews/phase-01-baseline.md` | 2026-07-23 | Baseline=HEAD 15a9410 (no separate baseline supplied). 47 migrations, head 0035. 238 backend tests pass. No secrets tracked. Deferred Guacamole/Proxmox code present. README "24wk" vs plan "25wk" + Cloudflare/Render vs self-host to reconcile. |
| 2 | Architecture map | Complete | `docs/reviews/phase-02-architecture.md` | 2026-07-23 | React SPA + FastAPI/SQLite. 28 routers (all mounted), 30 models, 37 services. Split auth (student JWT cookie / admin server session). Key overlaps: Training vs legacy curriculum, Support Tickets vs Service Desk, multiple XP/progress calculators. Oversized: training_service.py 870, commandEngine.js 930. Deferred code present (guacamole/proxmox/vm/ai). |
| 3 | Student navigation/IA | Complete (LIVE) | `docs/reviews/phase-03-student-nav.md` | 2026-07-23 | Swept all 12 dests desktop+mobile as temp student. Clean 4-item nav; My Training excellent; strong "next step" cues; graceful states; search has no stale Learning Path. Issues: Practice Library breadth + confusable CLI-trio names; Weekly Roadmap duplicated Home/Training/Progress; /service-desk 404 console errors in gated state. |
| 4 | Admin navigation/workflow | Complete (LIVE) | `docs/reviews/phase-04-admin-nav.md` | 2026-07-23 | Swept all 12 admin dests (200, 0 errors). Strong content tooling (References valid, 137/137 mapped but only 5 exact; Service Desk health Passing). Key gap: NO per-student monitoring (current week/completion/struggling/overdue). 3 overlapping content editors. No admin audit-log view; single shared admin. |
| 5 | My Training / curriculum | Complete (LIVE) | `docs/reviews/phase-05-curriculum.md` | 2026-07-23 | Pulled all 25 weeks/296 activities live. Sequence sound, Week 0 welcoming, required workload OK (5-10/wk). Issues: dense weeks (25-27 activities) visually jarring; watch-heavy vs 5 guided labs; "24-week" copy bug vs 25 weeks; Document Types after Ticketing quiz (known obs #1, low). Curriculum READY for 5 students w/ minor polish. |
| 6 | Lessons / content authoring | Complete (LIVE+source) | `docs/reviews/phase-06-lessons.md` | 2026-07-23 | 64 lessons, all published, good content (median 1532 chars, only 1 stub=lesson 1). Safe sanitization (plain text). KEY: authored `outcomes` never serialized/rendered (objectives hidden). Dual gating (module vs week). Search leaks gated lesson summaries. Dead learning-path API + null video_url branch. No central notes view. |
| 7 | Assessment / progress | Complete (LIVE) | `docs/reviews/phase-07-assessment.md` | 2026-07-23 | Assessment layer SAFE (verified live): no pre-submit answers, IDOR review+submit blocked (403), no XP double-award on retake, mastery=best, speed-flag anti-cheat. Nuance: quiz completion=attempted (0-score counts done, "Great work!" misleading); coverage% ≠ mastery. No answer explanations. No admin audit log. |
| 8 | Practice Library / labs | Complete (LIVE) | `docs/reviews/phase-08-practice.md` | 2026-07-23 | 5 guided labs, 48 networking (Cisco IOS sim — standout, ready), 50 command refs, terminal sandbox (no completion), 48 tickets (week-gated), 3 capstones (gated). Issues: CLI-trio overlap/naming (Terminal+Command Library duplicate); dual-surfaced tickets/labs; sandbox-vs-graded unclear. Don't add enterprise catalog. |
| 9 | Support Tickets vs Service Desk | Complete (admin LIVE + source; student-side flag-gated, NOT live) | `docs/reviews/phase-09-servicedesk.md` | 2026-07-23 | Tickets=AI-graded ITIL writeups (comms skill); Service Desk=deterministic procedural sim (safety skill). Distinct, no data conflict. All 5 scenarios well-designed (identity verify enforced, critical-failure gating, health passing). Student-side SD NOT tested live (global flag off, prohibited to change). 1B should wait for end-to-end flag-on walkthrough + must-fixes. |
| 10 | Security & privacy | Complete (LIVE probes) | `docs/reviews/phase-10-security.md` | 2026-07-23 | Strong: bcrypt, HttpOnly/Secure/lax cookies, strict CSP+HSTS (live), CSRF origin, all IDOR blocked live (403/404), admin authz 403 for students/unauth, hidden facts server-side, uploads bounded, npm 0 vulns, 45 sec tests pass. Findings: P2 no login rate-limit (Cloudflare mitigates); P2 no admin audit log; Low search-gating bypass. No P0/P1. |
| 11 | Database / migrations / seeds | Complete | `docs/reviews/phase-11-database.md` | 2026-07-23 | Excellent schema (55 tables, all FKs have ON DELETE, integrity ok, 0 violations, 121 idx, 39 unique). 47 migrations reversible except 5 stub downgrades. Seeds idempotent; MOD-001 self-heal benign. SD versions immutable. Finding: no WAL/busy_timeout (P2 easy win). Postgres trigger: multi-worker/>20-50 concurrent/locked errors. No P0/P1. |
| 12 | Code quality | Complete | `docs/reviews/phase-12-code-quality.md` | 2026-07-23 | Clean codebase (238 tests pass, 0 TODO markers). Smells: oversized training_service.py 870/commandEngine.js 930/students.py 719; N+1 in learning-path; duplicated progress/XP/mastery + dual gating + 3 content editors. Dead: learning-path API, video_url branch. Deferred services dormant not dead. Top-10 refactors listed; no rewrite. Lint not run (CI gap). |
| 13 | Performance & reliability | Complete (LIVE) | `docs/reviews/phase-13-performance.md` | 2026-07-23 | Home load lean: 5 API calls, 788ms, 0 duplicates. Code splitting (17 lazy), ErrorBoundary, loading states. /health 200. Issues: 1MB main bundle (282kB gzip) split it; Render cold-start 30s first load (infra, contradicts self-host docs); /service-desk 404 noise. Cloudflare beacon CSP warning harmless (don't weaken CSP). |
| 14 | Accessibility & responsive | Complete (LIVE) | `docs/reviews/phase-14-accessibility.md` | 2026-07-23 | Strong: 0 horizontal overflow at 375px, all inputs labeled, all controls named, 1 h1/page, visible focus rings (keyboard verified), full dark mode, status not color-only. Findings: A1 small touch targets on All Course Content mobile (P2); A2 no reduced-motion (P3); A3 contrast not formally measured. Good shape for launch. |
| 15 | Testing & release process | Complete | `docs/reviews/phase-15-testing.md` | 2026-07-23 | 228 tests + 6 real-journey e2e; strong security/gating/service-desk/seed-idempotency coverage. Gaps: no tests for search(has bug)/flashcards/evidence/resources/commands; migrations not tested both ways. BIG gap: NO CI (.github/workflows absent) — all manual. DEPLOYMENT.md thorough. Docs say self-host but prod on Render. |
| 16 | Live production comparison | Complete (LIVE + CLEANUP DONE) | `docs/reviews/phase-16-live-comparison.md` | 2026-07-23 | Routes/nav/gating/isolation all match baseline; no stale deploy or prod-only errors. Docs-vs-hosting discrepancy (self-host docs vs Cloudflare/Render). CLEANUP: temp student id 8 + attempts DELETED (verified login 401), 7 real accounts intact, admin logged out, creds scrubbed. No flags toggled, no real data modified. |
| 17 | Feature decision matrix | Complete | `NEXUS_FEATURE_DECISION_MATRIX.md` | 2026-07-23 | Full matrix: student/admin/platform/deferred features classified (Keep/Improve/Merge/Rename/Postpone) with quality, value, overlap, priority, effort. Top actions: surface lesson outcomes, fix SD 404, admin monitoring, add CI, merge CLI trio. |
| 18 | Prioritized findings | Complete (folded into full review) | `NEXUS_FULL_PROJECT_REVIEW.md` | 2026-07-23 | 0 P0, 5 P1, 16 P2, 9 P3, 6 Future. |
| 19 | Roadmap | Complete (folded into full review) | `NEXUS_FULL_PROJECT_REVIEW.md` | 2026-07-23 | Immediate→30→60→90→long-term roadmap. |
| Final | Synthesis of all deliverables | Complete | see Required Deliverables | 2026-07-23 | 6 deliverables written. |

---

## Project purpose

Nexus Learning is a private IT-training platform intended primarily for five
beginner IT students. The platform should guide students through a structured
training program while also allowing controlled access to quizzes, labs,
simulated support work, progress tracking, capstones, and administrative
oversight.

The product should feel:

- Simple for complete beginners
- Structured rather than overwhelming
- Practical and job-oriented
- Easy to navigate
- Consistent across desktop and mobile
- Safe for real student data
- Maintainable by a small owner-operated team
- Expandable without becoming cluttered

---

## Review inputs

Repository location: `[INSERT LOCAL REPOSITORY PATH]`

Review baseline commit: `[INSERT FINAL REVIEW-BASELINE COMMIT]`

Production website: `https://nexus.builtfromzero.fyi/`

Temporary student account and temporary administrator account:
**Claude Code should create these itself** (throwaway username/password,
student and admin role) rather than being handed pre-existing credentials,
so credentials never need to be typed into chat or written into any report.
If self-creation isn't possible (e.g., no admin bootstrap path), ask the user
to provide temp credentials out-of-band — do not paste them into any file,
screenshot, or terminal transcript that gets committed or shared.

Use only these temporary review accounts. Do not attempt to access other
users' private data. Do not attempt to bypass authentication, permissions,
server restrictions, rate limits, security controls, or feature flags.

---

## Current known product state

Use the source and live application as the source of truth, but begin with
this context:

- Backend is Python/FastAPI. Frontend is React/Vite.
- Production uses systemd, nginx/reverse proxy, and SQLite.
- The student-facing Learning Path page was retired. `/learning-path`
  redirects to `/training`. My Training is now the authoritative guided
  learning experience.
- Production curriculum currently has: 25 weeks, 296 activities, 137/137
  videos mapped.
- Current primary student navigation is intended to center on: Home, My
  Training, Practice Library, Progress.
- Direct lesson pages and notes remain supported. Quiz Library remains
  available. Guided Labs, Networking Labs, Command Library, Terminal
  Practice, Support Tickets, and Capstones remain available.
- Legacy Support Tickets remain separate from the new Service Desk Lab.
- Service Desk Phase 1A includes: five deterministic scenarios, Learning
  Mode, Simulation Mode, contextual browser tools, Knowledge Base,
  Performance, Assignments, Beta enrollment, admin scenario details, event
  replay, grade details, attempt reset. Controlled through feature flags and
  audited beta enrollment. Phase 1B has not started.
- AI, Proxmox, Guacamole, real Active Directory integration, calls,
  voicemail, and advanced organization features are intentionally deferred.
- The obsolete frontend Learning Path page is removed, but the old backend
  learning-path API may still exist.
- Two known observations have intentionally **not** been changed — do not
  automatically classify these as defects; investigate actual impact first:
  1. Fresh synchronization ordering differs between Document Types and the
     Ticketing Systems Quiz.
  2. Running the full application seed may repair a missing MOD-001
     prerequisite.

---

## Main objective

Determine: what Nexus does well; what is confusing, broken, incomplete,
duplicated, risky, or unnecessary; what should be removed, merged, renamed,
or kept separate; what should be improved now vs. postponed; what students
need for a clearer learning journey; what admins need to run the program;
the most dangerous technical debt; and a roadmap that adds value without
overcomplicating the platform.

Do not make assumptions based only on documentation. Inspect the code,
database models, migrations, seeds, tests, routes, API responses, browser
interface, and actual live behavior.

---

## Phase 0: Preconditions (run once, before Phase 1)

1. Confirm browser-automation tooling (e.g., a Playwright MCP) is available
   and can reach `https://nexus.builtfromzero.fyi/`. If it is **not**
   available, stop and report this clearly — do not proceed with a
   source-only review while implying navigation was tested. A source-only
   review must be explicitly labeled as such everywhere it appears.
2. Confirm read access to the repository and its Git history.
3. Confirm whether temp accounts need to be created (see Review Inputs) and
   create them if possible.
4. Confirm `docs/reviews/` exists in the repo (create it if not) — this is
   where all phase reports and final deliverables are written.
5. Report readiness before starting Phase 1.

---

## Phase 1: Establish the baseline

1. Confirm the current Git branch and commit.
2. Confirm the worktree is clean.
3. Compare local HEAD with the supplied review-baseline commit.
4. Identify the frontend and backend start commands.
5. Identify dependency and lock files.
6. Identify environment-variable templates.
7. Identify migration state and migration history.
8. Identify seed scripts and their responsibilities.
9. Identify production deployment documentation.
10. Identify test suites and browser tests.
11. Identify major architectural directories.
12. Identify dead, duplicate, generated, temporary, or suspicious files.
13. Confirm whether secrets or credentials appear in tracked files.
14. Record any inability to run a required part of the system.

Do not modify repository state merely to make the review easier.

---

## Phase 2: Architecture map

Explain the current architecture in plain language. Map: frontend pages,
frontend routing, student navigation, admin navigation, shared frontend
components, API service layer, authentication and sessions, authorization
and roles, backend routers, services and business logic, database models,
migrations, seeds, curriculum definitions, quiz system, lesson system,
notes, progress calculation, labs, Support Tickets, Service Desk scenarios,
Service Desk attempts/events/grades, admin tools, file uploads, background
tasks (if any), logging, testing, deployment.

Identify duplicated business logic between: frontend and backend; routes and
services; seeds and migrations; My Training and old curriculum systems;
Support Tickets and Service Desk; admin pages; student progress systems.

Highlight modules that are too large, overly coupled, difficult to test, or
likely to break unrelated functionality.

---

## Phase 3: Student navigation and information architecture review

Review the student experience using the temporary student account on desktop
(1440×1000) and mobile (375×812).

For every visible student destination, explain: what it currently does;
whether students need it; whether it overlaps another destination; whether
the name is understandable to a beginner; whether it belongs in primary
navigation; whether it should be a subsection/filter/card/direct link
instead; whether it should be kept, merged, renamed, hidden, or removed.

Cover specifically: Home, My Training, Weekly Training, All Course Content,
Lessons, Quiz Library, Practice Library, Guided Labs, Networking Labs,
Command Library, Terminal Practice, Support Tickets, Service Desk Lab,
Progress, Capstones, Search, Orientation, Profile/account controls.

Answer:
1. Does every primary nav item have a distinct purpose?
2. Is the difference between My Training and Practice Library obvious?
3. Is the difference between Support Tickets and Service Desk Lab obvious?
4. Are there too many secondary destinations?
5. Are students repeatedly shown the same content through different pages?
6. Can a beginner tell exactly what to do next after logging in?
7. Does Home act as a useful dashboard or merely duplicate other pages?
8. Does Progress explain meaningful learning progress?
9. Are locked activities understandable?
10. Do Back, refresh, direct links, and mobile navigation behave consistently?
11. Are there dead links, empty states, misleading cards, or unreachable routes?
12. Are retired features still referenced in search, breadcrumbs, metadata,
    or backend-generated URLs?

Produce a proposed student navigation structure: current structure,
recommended structure, what moves, what disappears, what's renamed, and why
each change improves beginner usability. Do not recommend a separate tab for
every feature.

---

## Phase 4: Administrator navigation and workflow review

Use the temporary administrator account.

For every admin destination, explain: purpose; who needs it; whether it's
complete; whether it duplicates another area; whether important actions are
missing; whether dangerous actions are adequately protected; whether it
should remain, move, merge, or be renamed.

Cover: Dashboard, Student management, Learning Content, Weekly Training,
Lessons, Quizzes, Labs, Support Tickets and reviews, Service Desk
administration, Scenarios, Knowledge Base, Assignments, Beta enrollment,
Attempts, Replay, Grades, Attempt reset, Capstones, System/configuration
areas, Roles and permissions.

Check whether an admin can answer: What is each student supposed to do this
week? What has each student completed? Where is each student struggling?
What is overdue? Which content is unpublished or broken? Which videos lack
quizzes? Which activities have no learning objective? Which scenarios are
failing health checks? Which students have access to private-beta features?
Which actions were performed by administrators?

Recommend a simpler admin structure appropriate for a small five-student
program. Avoid designing enterprise features Nexus doesn't need.

---

## Phase 5: My Training and curriculum review

Inspect all 25 weeks and all 296 activities — do not only count records.

Evaluate: week titles/descriptions, learning objectives, activity order,
prerequisites, required vs. optional content, workload per week, video
duration where available, lesson quality, quiz placement/difficulty, labs,
tickets, Service Desk scenarios, capstones, repetition, missing
reinforcement, sudden difficulty jumps, orphaned/duplicate content,
incorrect mappings, broken links, activities misaligned with the week's
objective, content too advanced or too basic for its placement, weeks too
full or too empty.

Assess whether the program develops skills in a logical sequence: computer
basics → operating systems → hardware → troubleshooting → networking →
identity and access → ticketing → security → command line → support
communication → documentation → practical labs → capstone readiness.

Check whether every activity answers: What am I learning? Why does it
matter? What should I do? How do I know I completed it? What should I do
next?

Review Week 0 carefully: Orientation, CompTIA troubleshooting process,
initial expectations, first meaningful success, whether the first experience
is welcoming rather than overwhelming.

Produce a week-by-week assessment: current purpose, strong points, problems,
missing prerequisites, duplicated material, recommended ordering changes,
recommended additions/removals, priority. Do not rewrite curriculum content
during this review.

---

## Phase 6: Lessons and content-authoring review

Review the lesson system independently from the retired Learning Path UI.
Check: direct lesson routes, lesson content, notes, completion tracking,
video fields, quiz relationships, admin editing, published/draft state,
ordering, search, metadata, mobile rendering, accessibility, broken
markdown/HTML, content sanitization, data validation.

Determine: Are lessons useful or mostly placeholders? Should lessons be
short reading companions to videos? Should each video have a lesson
summary? Should lessons include objectives, vocabulary, examples, review
checks? Are notes useful and easy to find later? Is content duplicated
between lessons and videos? Does the admin editor support reliable content
creation? Are there unreachable lessons, or activities referencing
missing/incorrect lessons? Is the remaining backend learning-path API now
dead code?

Recommend one standard, practical-to-maintain lesson template (objective,
why it matters, key terms, main explanation, worked example, common
mistakes, practice task, quick knowledge check, related video/quiz/lab,
notes prompt).

---

## Phase 7: Assessment and progress review

Review: quizzes, attempts, pass thresholds, retakes, review pages,
correct-answer exposure, progress calculation, best vs. latest score,
completion rules, XP, mastery terminology, capstone gating, rank
restrictions, manual overrides, mentor/admin reviews.

Determine: Can students understand why something is complete/incomplete?
Are progress percentages accurate? Can completion be accidentally
duplicated? Can XP be awarded twice? Are quiz mappings sensible? Do quiz
questions test understanding rather than memorization? Do students get
useful explanations? Do failed attempts teach improvement? Does progress
survive refresh and direct navigation? Are admin overrides transparent and
auditable?

Identify misleading metrics. Recommend which metrics belong on Home, My
Training, Progress, and the admin dashboard. Avoid analytics that won't help
five students.

---

## Phase 8: Practice Library and labs review

For each practice type — Guided Labs, Networking Labs, Command Library,
Terminal Practice, Support Tickets, Service Desk Lab, Capstones — determine:
what skill it teaches; whether it works; whether it's beginner appropriate;
whether instructions are clear; whether completion is authoritative;
whether progress is recorded; whether feedback is useful; whether it
duplicates another practice type; whether it belongs in My Training vs.
Practice Library; whether it's ready for students.

Determine whether students need: categories, difficulty filters,
recommended practice, assigned practice, recently used, completed, search,
skill tags. Do not turn Practice Library into a large marketplace or
enterprise LMS catalog.

---

## Phase 9: Support Tickets versus Service Desk review

Explain: what Support Tickets currently teach; what Service Desk Lab
currently teaches; where they overlap/differ; whether students understand
the difference; whether their data, grading, XP, and admin workflows
conflict; whether both should remain; whether Support Tickets should
eventually simplify; whether some Support Tickets should migrate into
deterministic Service Desk scenarios; which system is authoritative for
which activity type.

Review the five Service Desk scenarios (Locked User Account, Password
Reset, MFA Reset, BitLocker Recovery, New Employee Onboarding) for:
beginner clarity, realism, correct technical process, identity-verification
requirements, safe failure handling, recoverable vs. critical mistakes,
Learning Mode guidance, Simulation Mode difficulty, tool behavior,
resolution documentation, scoring, feedback, Knowledge Base support, mobile
usability.

Recommend the next Service Desk phase without implementing it. Separate:
must-fix Phase 1A defects; reasonable Phase 1B work; long-term ideas;
features Nexus does not need.

---

## Phase 10: Security and privacy review

Perform a **defensive, non-destructive** audit of: authentication, session
handling, password storage, cookies, CSRF, CORS, CSP, input validation,
output encoding, HTML sanitization, file uploads, object ownership,
student-to-student isolation, student-to-admin isolation, admin
authorization, rank/role checks, feature flags, beta enrollment, direct URL
access, IDOR risks, hidden scenario facts, mass assignment, rate limiting,
audit logs, sensitive logging, recovery-key handling, temp reviewer
accounts, environment configuration, secrets, backup permissions, dependency
vulnerabilities, production debug behavior.

Do not exploit production. Validate authorization only through normal
temporary-account behavior.

For each finding: severity, evidence, affected route/file, realistic
impact, recommended correction, regression test needed. Do not exaggerate
theoretical findings without evidence.

---

## Phase 11: Database, migrations, and seed review

Review: schema design, foreign keys, indexes, uniqueness constraints,
nullability, cascades, immutable scenario versions, append-only events,
audit logs, SQLite concurrency risks, migration ordering, downgrades, seed
ownership, idempotency, fresh-install behavior, production-upgrade
behavior, duplicate-content protection, production reseeding risks,
backup/restore process.

Pay particular attention to: logic split between migrations and `seed.py`;
curriculum synchronization; orientation lesson creation; lesson title/order
identity; MOD-000; MOD-001; training activity order; scenario hashes;
published immutable versions; attempt/event/grade consistency.

Assess when SQLite becomes a practical limitation — explain the exact usage
threshold or feature that should trigger a PostgreSQL migration, rather than
recommending it immediately.

---

## Phase 12: Code-quality review

Inspect for: large files/functions, repeated conditionals, duplicated
authorization, duplicated API calls, weak type guarantees, inconsistent
response formats, missing error handling, silent failures, race conditions,
stale state, unnecessary global state, inefficient rendering, N+1 queries,
missing indexes, dead code, deprecated routes, unused dependencies, weak
names, mixed responsibilities, hard-coded values, magic strings, time-zone
bugs, incomplete tests, tests coupled to implementation details, flaky
browser tests, unsafe test fixtures.

Identify the **ten highest-value refactors**: why it matters, files
involved, risk, effort, recommended sequence, how to test it. Do not
recommend rewriting the application.

---

## Phase 13: Performance and reliability review

Review: initial frontend bundle, lazy loading, route-level code splitting,
API request volume, duplicate requests, database query performance, image
and video loading, cache behavior, error boundaries, loading states, retry
behavior, health endpoints, logging, startup, deployment, backup
verification, rollback, systemd behavior, nginx behavior, browser-console
warnings, Cloudflare beacon CSP warning, expected unauthenticated `/auth/me`
behavior.

Distinguish harmless warnings from real defects. Do not recommend weakening
CSP merely to permit analytics.

---

## Phase 14: Accessibility and responsive design review

Render at minimum 1440×1000 (desktop) and 375×812 (mobile).

Review: keyboard navigation, focus indicators, tab order, Enter/Space
activation, Escape behavior, modal focus containment, drawer focus
restoration, screen-reader names, heading order, form labels, error
announcements, color contrast, status not conveyed by color alone, touch
targets, horizontal overflow, clipped controls, dense tables, mobile
navigation, reduced motion, zoom behavior where practical.

Capture screenshots of meaningful issues only — do not fill the report with
cosmetic preferences that don't affect usability.

---

## Phase 15: Testing and release-process review

Determine: what's well covered vs. superficially covered; what critical
paths lack tests; what tests are flaky; what fixtures differ from
production; whether fresh installs match production; whether browser tests
validate real user journeys; whether security regressions are covered;
whether migrations are tested both directions; whether seeds are tested
twice; whether production smoke tests are repeatable; whether cleanup is
reliable.

Review the release workflow: branching, commits, merge process, backups,
migration, frontend build, backend restart, health checks, feature flags,
production smoke testing, rollback, deployment records.

Recommend a simpler, repeatable release checklist.

---

## Phase 16: Live production comparison

Using only the temporary accounts, confirm: expected routes exist; expected
navigation matches; frontend/backend correspond to the baseline; no stale
deployment; no production-only errors; feature flags behave as expected;
student and admin experiences are isolated correctly.

Do not modify real curriculum or real students. Record any temporary
changes made under the review accounts and clean them up when practical —
list what was created and what was removed in this phase's report.

---

## Phase 17: Feature-by-feature decision matrix

One decision table for every major feature, classified as: Keep / Improve /
Merge / Rename / Hide / Remove later / Postpone / Needs investigation.

Columns: Feature, Current purpose, Current quality, Student value, Admin
value, Overlap, Recommendation, Reason, Priority, Estimated effort,
Dependencies.

Write directly to `NEXUS_FEATURE_DECISION_MATRIX.md` (this is also one of
the six required deliverables — no need to duplicate it elsewhere).

---

## Phase 18 + 19: Prioritized findings and roadmap

**Findings** — classify every finding once (avoid restating the same
finding in different words) as:
- P0: Immediate security/data-loss/production failure risk
- P1: Serious bug or major student/admin blocker
- P2: Important usability, maintainability, or curriculum weakness
- P3: Useful improvement
- Future: Valuable but not appropriate yet

Each finding needs: title, priority, evidence, affected route/component/
API/model/file, user impact, technical impact, recommended fix, estimated
effort, risk of fixing, required tests, whether it blocks student use,
whether it blocks private beta, whether it blocks Phase 1B.

**Roadmap** — realistic, for a small private program:
- Immediate stabilization (before more students/features)
- Next 30 days (reduce confusion/risk)
- Next 60 days (curriculum, practice, admin improvements)
- Next 90 days (carefully selected expansion)
- Long term (additional Service Desk scenarios, My Training/Service Desk
  integration, better reporting, more labs, optional VM integration,
  optional AI assistance, PostgreSQL migration, content-authoring
  improvements) — do not recommend AI, VMs, Guacamole, calls, or advanced
  enterprise features merely because they sound impressive; state the
  prerequisite and measurable value for each.

These two phases feed directly into the full review's "Prioritized
findings" and "Roadmap" sections — no separate standalone file needed.

---

## Required deliverables (final synthesis pass)

Once all phase reports exist in `docs/reviews/`, read all of them and
produce these six files:

1. **`NEXUS_FULL_PROJECT_REVIEW.md`** — Executive summary, architecture map,
   product strengths, major risks, student UX review, admin UX review,
   navigation review, curriculum review, lesson review, practice/lab
   review, Support Tickets vs. Service Desk, security, database/seeds/
   migrations, code quality, performance, accessibility, testing,
   deployment, prioritized findings, roadmap, final recommendation.

2. **`NEXUS_FEATURE_DECISION_MATRIX.md`** — from Phase 17 (already written).

3. **`NEXUS_IMPLEMENTATION_BACKLOG.md`** — accepted findings converted to
   implementation-sized tasks: priority, scope, files likely involved,
   dependencies, acceptance criteria, tests, risk, size (XS/S/M/L/XL).

4. **`NEXUS_CURRICULUM_AUDIT.md`** — week-by-week assessment, sequence
   problems, missing prerequisites, duplicate content, workload concerns,
   recommended content moves, lesson-template recommendation, quiz/lab/
   ticket alignment.

5. **`NEXUS_NAVIGATION_PROPOSAL.md`** — current/recommended student nav,
   current/recommended admin nav, route migration recommendations,
   redirects needed, mobile considerations, features to remove from primary
   navigation.

6. **`NEXUS_REVIEW_EVIDENCE.md`** — commands run, tests run, browser sizes,
   routes inspected, temporary records created/removed, screenshots, errors
   encountered, areas that could not be validated.

Do not include passwords or secrets in any of these files.

---

## Final response (chat, after all deliverables are written)

Keep this **short — this is the only thing that goes in the main chat
reply**; everything else lives in the files above. Include exactly:

1. Baseline commit reviewed
2. Tests and validation performed
3. Count of P0 / P1 / P2 / P3 / Future findings
4. The five most important findings
5. Recommended student navigation (one line each)
6. Recommended admin navigation (one line each)
7. Whether curriculum is ready for the five students
8. Whether Service Desk is ready for its temporary student review
9. Whether Phase 1B should start
10. The first five implementation tasks
11. Files created
12. Anything that couldn't be verified
13. Confirmation that no production deployment, merge, push, feature-flag
    change, or real-student modification occurred

---

## Strict restrictions

Do not: push or merge; deploy; enable/disable feature flags; create
migrations; run production seeds; modify real students; modify real
curriculum; delete production data; start Phase 1B; add AI; add VM
integration; add Guacamole; add calls or voicemail; rewrite the
application; expose credentials; claim a feature was tested when it wasn't;
treat documentation as proof that runtime behavior works.

This is primarily a review and planning task. You may create temporary
local files, databases, test accounts, browser traces, screenshots, and
review reports — clean up temporary resources when finished. Do not expose
credentials in Git, screenshots, reports, terminal transcripts, or
application logs.

Review first. Provide evidence. Recommend changes in a prioritized,
practical way.
