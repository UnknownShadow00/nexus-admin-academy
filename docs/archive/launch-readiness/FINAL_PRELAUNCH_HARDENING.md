# Final Pre-Launch Hardening Report

Date: 2026-08-08  
Branch: `prelaunch/final-hardening`  
Verdict: **READY WITH KNOWN LIMITATIONS**

## Executive result

The launch-critical security and reliability findings discovered in this sprint
were fixed and covered by regression tests. The full backend, frontend, Service
Desk, and integrated launch-verification suites pass. No production deployment
or merge was performed.

The remaining limitations are non-blocking: Scenario Builder is an explicitly
labelled browser-local prototype rather than a publishing surface; 633 legacy
questions lack explanations; 71 active-but-unmapped quizzes require editorial
review before they are exposed; React Router has two moderate advisories whose
available automated remediation is a breaking v7 upgrade; and the legacy xterm
packages are deprecated.

## Security and authorization

Five P0 findings were confirmed and fixed:

1. Mentor/admin read access could flow through owner checks used by student
   mutation routes. Student quiz, lesson, ticket, check-in, and Service Desk
   writes are now owner-only; mentors retain the intended read/review paths.
2. The legacy Service Desk progress bridge accepted browser-selected event
   titles and could award repeat XP. It is now a compatibility no-op, and the
   summary is calculated from authoritative grades and XP ledger entries.
3. Uploaded evidence was exposed from a public static directory to anyone who
   knew its UUID URL. Evidence is now served by an authenticated, owner-or-mentor
   endpoint with safe path resolution.
4. Global credentialed CORS allowed unrelated ExamCompass origins. Credentialed
   application CORS now allows only configured Nexus origins; the one bookmarklet
   import route has a narrowly scoped, non-credentialed ExamCompass policy.
5. Production could start with a placeholder JWT secret. Production startup now
   rejects missing, short, or placeholder secrets and unsupported algorithms.

Service Desk snapshots remain untrusted (`trusted=false`). Snapshot/current
state is not consumed as grading evidence, cannot award XP or decide pass/fail,
cannot reopen completed attempts, and cannot mutate another student's attempt.
Failed attempts do not receive success XP, completion is idempotent, and raw
events cannot become trusted actions. Regression coverage also proves that a
mentor may inspect an attempt but receives 403 from event, snapshot, action,
hint, and completion mutations.

No hardcoded production secret, SQL string-concatenation vulnerability, upload
path traversal, client-selected XP value, or grading mass-assignment route was
found in the audited paths.

## Reliability and beginner experience

Four P1 findings were confirmed. Three were fully fixed and one was made honest
and recoverable:

- Corrupt Service Desk outbox data no longer disappears silently. Valid queued
  entries are retained in order, the original payload is backed up under a
  recovery key, and the UI receives a recoverable sync problem without crashing.
- Today no longer remains on an infinite skeleton when check-in or dashboard
  requests fail. Check-in is non-blocking and an actionable retry state is shown.
- Mentor use of the read-only student stats route no longer updates the student's
  login streak; presence state changes only through the owner-only check-in route.
- Scenario Builder still uses local storage and cannot safely publish the
  authoritative server schema. Its controls and notices now explicitly identify
  it as a local prototype and instruct the administrator to export before browser
  data is cleared. A schema-compatible publishing workflow remains post-launch.

Student primary navigation remains intentionally limited to Today, Service Desk,
and Progress, with Extra Practice for optional work. Today and weekly learning
already present the next Learn, Quiz, or Practice action; no old navigation
clutter was reintroduced. Evidence links now open through the authenticated API.

## Curriculum structure

Programmatic validation reports 25 contiguous weeks (0–24), 296 activities,
137/137 mapped videos, no missing or empty weeks, no duplicate activity IDs, no
broken references, no gating dead ends, and no ordering violations in a fresh
seed. The detailed audit is in `../reviews/NEXUS_CURRICULUM_AUDIT.md`.

| Week | Required / total activities | Structural note |
|---:|---:|---|
| 0 | 5 / 6 | Beginner orientation; fresh seed orders learning before the quiz |
| 1 | 7 / 10 | Clear introductory support workflow |
| 2 | 10 / 25 | High optional density; required path remains bounded |
| 3 | 10 / 26 | High optional density; required path remains bounded |
| 4 | 10 / 27 | High optional density; required path remains bounded |
| 5 | 10 / 18 | Balanced required path |
| 6 | 6 / 8 | Balanced |
| 7 | 10 / 16 | Balanced |
| 8 | 10 / 20 | Balanced required path |
| 9 | 7 / 10 | Balanced |
| 10 | 7 / 21 | Optional practice-heavy; required path remains bounded |
| 11 | 8 / 12 | Balanced |
| 12 | 7 / 8 | Balanced |
| 13 | 6 / 6 | Focused required week |
| 14 | 4 / 4 | Light but coherent |
| 15 | 7 / 7 | Focused required week |
| 16 | 6 / 6 | Focused required week |
| 17 | 6 / 6 | Focused required week |
| 18 | 5 / 9 | Balanced |
| 19 | 5 / 6 | Balanced |
| 20 | 10 / 19 | Dense; required path remains bounded |
| 21 | 8 / 9 | Balanced |
| 22 | 4 / 5 | Light but coherent |
| 23 | 5 / 5 | Light, focused week |
| 24 | 3 / 7 | Short completion/review week |

The existing developer database has an older Week 0 ordering, while a clean
migration and seed produces the reviewed ordering. Production should be checked
against the documented migration/seed state rather than casually reseeded.

## Question bank

The complete bank was audited programmatically and the machine-readable report
was regenerated at `docs/question_bank_audit.json`.

- Questions: 966 (780 single-select, 186 multi-select)
- Structurally invalid: 0
- Exact normalized duplicates: 0
- Duplicate options: 0
- Invalid/empty correct-answer references: 0
- Select-N/multi-select mismatches: 0
- Malformed entities or imported numbering prefixes: 0
- Quizzes with zero questions: 0
- Questions disconnected from a quiz: 0
- Missing explanations: 633
- Active quizzes disconnected from curriculum: 71
- Objectively safe data fixes made: 0 (none were required)

Historical question 648 is not present in the current bank, and no current
Select-2 mismatch was found. No question answer requires human correctness review
based on structural evidence. Editorial review is still required for the 633
missing explanations and before exposing these currently unmapped quiz IDs:

`26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44, 46, 47, 49, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 96, 97, 98, 99, 100, 101, 102, 103, 104`.

## Service Desk, CLI, and administration

All 13 active Service Desk definitions were structurally reviewed, including the
8 assigned browser/runtime scenarios. They contain requester context, symptoms,
business impact, device context, progressive hints, tool use, verification,
documentation, and resolution objectives. No scenario content was changed: no
objectively weak launch blocker justified risking the server-authoritative
grading contracts.

CLI validation passes for 48 networking labs. The progression covers switching,
routing, ping, ARP, and SSH; Terminal Practice supplies beginner Windows/Linux
commands including `ipconfig`, `ping`, `nslookup`, `netstat`, `whoami`, and basic
filesystem/service commands. Unsupported commands were not added. Labs remain
discoverable through weekly learning and Extra Practice.

Admin navigation already groups Dashboard, Learning Content, Students,
Assessments & Labs, and System, with Service Desk review available. The only
confirmed misleading control was Scenario Builder's local-only save/publish
language, which was corrected.

## Release validation

| Validation | Result |
|---|---|
| Backend pytest | PASS — 329 passed, 9 warnings |
| Alembic head/current | PASS — `0032_service_desk_trusted_events (head)` |
| Python compile and Ruff | PASS |
| SQLite integrity/foreign keys | PASS — `ok`, no violations |
| Service Desk lint | PASS |
| Service Desk typecheck | PASS |
| Service Desk tests | PASS — shared 33, simulation 133, UI 29, web 51 |
| Service Desk build | PASS — Next 15.5.22 |
| Service Desk audit high | PASS — no known vulnerabilities |
| Frontend audit high | PASS with two MODERATE React Router advisories |
| Frontend build | PASS — Vite 1,992 modules |
| CLI validate | PASS — 48 lessons |
| CLI sanity | PASS |
| Integrated Playwright | PASS — 6/6 |

The React Router advisories affect `react-router-dom` 6.30.4. The available npm
remediation upgrades to v7 and is breaking. This client-only SPA does not use the
affected SSR/data-router hydration behavior, and its post-login path is locally
validated. The migration is therefore a dedicated post-launch task, not a rushed
release change. The Vite main bundle is about 1 MB, and legacy xterm packages are
deprecated; both are non-blocking technical debt.

The migration chain upgrades a clean database to the single current head. Seed
scripts completed on the throwaway launch database. SQLite integrity and foreign
keys pass. The repository provides SQLite online backup plus upload sync and a
PostgreSQL dump plus upload archive; both restore paths are documented in
`docs/DEPLOYMENT.md`.

## Exact human deployment checklist

1. Confirm the approved release SHA is on `prelaunch/final-hardening`, CI is green,
   the worktree is clean, and the SHA has received human review. Merge only through
   the organization's normal approved process.
2. Identify whether production uses SQLite or PostgreSQL. Record the current
   deployed SHA/image tags, environment configuration, nginx configuration,
   database revision, service versions, and upload path.
3. Schedule a maintenance window and pause writes. Run the matching sanctioned
   backup: `scripts/backup_sqlite.sh` for SQLite or `scripts/backup_db.sh` for the
   Docker/PostgreSQL stack. Back up uploads and nginx configuration with the same
   timestamp.
4. Verify the backup before changing production: decompress a SQLite copy and run
   `PRAGMA integrity_check` plus `PRAGMA foreign_key_check`, or list/restore the
   PostgreSQL archive into an isolated database. Confirm the upload archive is
   readable. Record exact backup paths.
5. Verify production environment values: `APP_ENV=production`; a unique JWT secret
   of at least 32 characters shared only where required; an allowed JWT algorithm;
   the exact production application origin(s) in CORS; secure cookies; production
   database URL; admin credentials/import key; durable upload, backup, and log
   paths; and no checked-in `.env` or placeholder secret.
6. Build immutable backend, frontend, and Service Desk artifacts from the approved
   SHA. Record artifact digests/tags. Do not copy local databases or build output.
7. With writes paused, run `alembic current` and `alembic heads`, then
   `alembic upgrade head`. Confirm the resulting revision is
   `0032_service_desk_trusted_events`. Do not run broad seed scripts against an
   existing production database unless the release procedure explicitly requires
   and has reviewed their data effects.
8. Start dependencies in order: database, backend, Service Desk, frontend/nginx.
   Confirm nginx routes `/api` and Service Desk to the intended upstreams and does
   not publish the evidence upload directory.
9. Run health and smoke checks: backend health, student login/logout, Today load,
   lesson and quiz submission, duplicate completion XP behavior, Service Desk
   launch/action/snapshot/complete, clean-browser resume, mentor read plus denied
   mentor mutation, owner-only evidence download, admin content review, and logout.
10. Resume writes only after smoke checks pass. Monitor 4xx/5xx rates, CORS/auth
    failures, migration errors, outbox recovery warnings, grading/XP anomalies,
    disk space, and backup logs throughout the maintenance observation window.

## Exact rollback checklist

1. Pause writes immediately, declare rollback, record the failed SHA/images and
   logs, and preserve a timestamped copy of the failed database and uploads for
   investigation.
2. Stop frontend/nginx, Service Desk, and backend writers. Do not run destructive
   Alembic downgrades; historical data migrations are not uniformly reversible.
3. Restore the previously recorded application images/SHA and nginx/environment
   configuration. This sprint adds no database migration, but if production data
   or schema changed during release, restore the verified pre-release database
   and matching uploads together using `docs/DEPLOYMENT.md`.
4. Start database, backend, Service Desk, then frontend/nginx. Run `alembic current`,
   database integrity/foreign-key checks, backend health, auth, ownership,
   evidence, quiz/XP, and Service Desk resume/grading smoke checks.
5. Resume writes only after the rollback smoke checks pass. Retain the failed-state
   copies and logs, confirm the next scheduled backup succeeds, and document the
   incident before attempting another release.

## Remaining work

There are no confirmed launch-blocking P0 or P1 defects after this patch. Planned
post-launch work is: implement a schema-compatible server publishing flow for
Scenario Builder; editorially review unmapped quizzes and add useful question
explanations; plan and test React Router v7 and maintained xterm migrations; add
`tracert`, `hostname`, and `systeminfo` only if future curriculum requires them;
and split/lazy-load the largest frontend bundle.

**NO MERGE PERFORMED.**  
**NO PRODUCTION DEPLOYMENT PERFORMED.**
