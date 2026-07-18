# Old Database Coverage Audit — 2026-07-18

## Scope and safety

This report was completed before any write to `backend/nexus.db`.

- Current database: `backend/nexus.db`
- Old database: `backend/nexus.db.pre24wk-2026-07-17`
- Comparison mode: SQLite URI `mode=ro`
- Current migration head: `b7c8d9e0f1a2`
- Old migration head: `d5e6f7a8b9c0`
- Full database replacement is prohibited.

Both databases return `ok` from `PRAGMA integrity_check`. They do not have the same migration lineage. The old database has pre-existing foreign-key violations in historical student rows, and the current database has five orphaned methodology-progress rows. These rows must not be copied by numeric ID.

## Classification rules

- **RESTORE** — still required, purpose is established, and a safe mapped import can be validated.
- **REPLACED** — represented or superseded by the 24-week curriculum.
- **HISTORICAL** — student activity that requires verified identity mapping.
- **OBSOLETE** — test, stale, or intentionally excluded material.
- **REVIEW** — purpose or safe mapping is unclear.

## Complete table comparison

Counts are physical row counts. “Old-only” and “current-only” use the natural identifier shown rather than surrogate integer IDs wherever possible.

| Table | Current | Old | Old-only | Current-only | Likely natural identifier | Foreign-key dependencies | Conflict assessment | Classification |
|---|---:|---:|---:|---:|---|---|---|---|
| `ai_rate_limits` | 5 | 0 | 0 | 5 | `(user_id, endpoint, window_start)` | None declared | Current runtime counters; preserve current | — |
| `ai_usage_logs` | 26 | 0 | 0 | 26 | `(created_at, feature, model)` | None | Current operational history; preserve current | — |
| `capstone_runs` | 0 | 0 | 0 | 0 | `id` plus student/template | `students`, `capstone_templates` | No records | — |
| `capstone_templates` | 3 | 0 | 0 | 3 | `title` | `roles` via `role_level` | New-build-only content | REPLACED |
| `cli_lab` | 48 | 48 | 0 | 0 | `id` | None | All 48 natural keys and common-column contents match | REPLACED (already represented) |
| `cli_lab_attempt` | 0 | 0 | 0 | 0 | UUID `id` | `students`, `cli_lab` | No records | — |
| `command_reference` | 50 | 50 | 0 | 0 | case-folded `command` | None | All 50 records match | REPLACED (already represented) |
| `comptia_objectives` | 4 | 4 | 0 | 0 | `(domain, objective_number)` | Referenced by `student_objective_progress` | All four records match | REPLACED (already represented) |
| `curriculum_videos` | 0 | 182 | 182 | 0 | unique `video_key` | Quiz association is logical through `quiz_title` | No current key collisions. Old `exam_code` column is absent from current schema and must be restored before import | RESTORE |
| `evidence_artifacts` | 0 | 0 | 0 | 0 | `checksum` or `storage_key` | `students`; logical submission reference | No records | — |
| `flashcard_reviews` | 0 | 0 | 0 | 0 | unique `(student_id, question_id)` | `students`, `questions` | No records | — |
| `incident_participants` | 0 | 0 | 0 | 0 | `(incident_id, student_id)` | `incidents`, `students` | No records | — |
| `incident_tickets` | 0 | 0 | 0 | 0 | unique `(incident_id, ticket_id)` | `incidents`, `tickets` | No records | — |
| `incidents` | 0 | 0 | 0 | 0 | `title` | `root_causes` | No records | — |
| `lab_runs` | 0 | 0 | 0 | 0 | `id` plus student/template | `students`, `lab_templates` | No records; old schema also had `vm_status` and `guac_url` | — |
| `lab_templates` | 5 | 0 | 0 | 5 | `title` | optional `lessons` | Nothing is missing from old; current has five new labs | REPLACED |
| `lessons` | 63 | 1 | 0 | 62 | `(module.code, lesson_order)`; title as secondary | `modules` | Old `MOD-000` lesson exactly matches current; 62 are new | REPLACED (already represented) |
| `login_streaks` | 1 | 5 | 4 | 0 by numeric key | `student_id` after verified identity mapping | `students` | Old IDs 1, 2, 4, and 7 reference deleted users; ID 12 was old Mentor. Numeric IDs collide with unrelated current users | HISTORICAL |
| `methodology_frameworks` | 1 | 1 | 0 | 0 | `name` | optional `roles` | `CompTIA 6-Step` matches | REPLACED (already represented) |
| `modules` | 25 | 1 | 0 | 24 | unique `code` | self-reference through prerequisite | Old `MOD-000` exactly matches; new build adds `MOD-001`–`MOD-024` | REPLACED (already represented) |
| `promotion_gates` | 24 | 3 | 3 | 24 | `(role name, requirement_type, normalized config)` | `roles` | Old five-role ladder was replaced by the six-role 24-week progression | REPLACED |
| `questions` | 189 | 778 | 778 | 189 | `(quiz title, normalized question_text)` | `quizzes` | Parent quiz titles are disjoint. Old schema includes F/G/H options absent from current; direct copying would corrupt some questions | RESTORE with schema compatibility |
| `quiz_attempts` | 0 | 0 | 0 | 0 | `id`, or `(student, quiz, completed_at)` | `students`, `quizzes` | No records | — |
| `quizzes` | 25 | 79 | 79 | 25 | normalized `title` | Logical `lesson_id`; child `questions` | Title sets are disjoint. Integer IDs overlap and must be regenerated. All old `lesson_id` values are null | RESTORE |
| `rca_submissions` | 0 | 0 | 0 | 0 | `(incident_id, student_id, submitted_at)` | `incidents`, `students` | No records | — |
| `resources` | 0 | 1 | 1 | 0 | normalized `url` | Logical optional `lesson_id` | Single ad-hoc record `Test Mine`; provenance and intended placement are unclear | REVIEW |
| `roles` | 6 | 5 | 5 | 6 | unique `name` and `rank_order` | Referenced by students, gates, capstones | Old role ladder was intentionally replaced | REPLACED |
| `root_causes` | 0 | 0 | 0 | 0 | normalized description/cause tuple | Referenced by incidents | No records | — |
| `squad_activity` | 0 | 15 | 15 | 0 | `(student identity, created_at, activity_type, title)` | `student_id` is logical but not declared | Most rows reference deleted users; titles refer to legacy quizzes/tickets | HISTORICAL |
| `student_domain_mastery` | 5 | 4 | 4 | 5 | `(verified student identity, domain_id)` | Student is logical but not declared | Old rows reference deleted user IDs 1, 2, 4, 7; IDs collide with current users | HISTORICAL |
| `student_lesson_notes` | 0 | 0 | 0 | 0 | unique `(student_id, lesson_id)` | `students`, `lessons` | No records | — |
| `student_methodology_progress` | 12 | 11 | identity-ambiguous | identity-ambiguous | `(verified student identity, framework name)` | `students`, `methodology_frameworks` | Old rows 1–10 are orphaned; current rows 8–12 are orphaned. Numeric overlap does not prove identity | HISTORICAL |
| `student_objective_progress` | 0 | 0 | 0 | 0 | `(student identity, objective natural key)` | `students`, `comptia_objectives` | No records | — |
| `student_roles` | 0 | 0 | 0 | 0 | `(student identity, role name, promoted_at)` | `students`, `roles` | No records | — |
| `students` | 7 | 6 | 6 old usernames | 7 current usernames | case-folded `username`/email | Parent of most activity tables | Accounts were recreated with different IDs, then renamed. Never copy old account rows or hashes | REPLACED; identity mapping REVIEW |
| `ticket_submissions` | 0 | 0 | 0 | 0 | `(student, ticket, submitted_at)` | `students`, `tickets` | No records | — |
| `tickets` | 48 | 4 | 4 | 48 | normalized `title` | Parent of submissions/incidents | Three old generic scenarios are superseded; one row is literally titled `test` | REPLACED / OBSOLETE |
| `video_watches` | 0 | 1 | 1 | 0 | unique `(verified student identity, video_key)` | `students`; logical curriculum key | The old row references deleted student ID 7, not current student ID 7 | HISTORICAL |
| `vm_assignments` | 0 | 0 | 0 | 0 | `vmid` or `(student, lab_run)` | `students`, `lab_runs` | No records | — |
| `weekly_domain_leads` | 0 | 8 | 8 | 0 | `(week_key, domain_id, verified student)` | Student is logical but not declared | All rows reference deleted user IDs; these are historical badge awards | HISTORICAL |
| `xp_ledger` | 0 | 0 | 0 | 0 | `(student, source_type, source_id, created_at)` | `students` | No records | — |

`alembic_version` has one row in each database, but the values differ because the databases have different migration histories. It is configuration/schema state, not importable application data.

## Tracker restoration dataset

The confirmed tracker restoration consists only of:

1. All 182 `curriculum_videos` rows, preserving `active` state:
   - 63 active Core 1 (`220-1201`)
   - 45 inactive Core 1 historical rows
   - 74 active Core 2 (`220-1202`)
   - 137 rows will be visible through the active-only API
2. All 79 published legacy quizzes referenced by the curriculum.
3. All 778 child questions for those quizzes.

Validation facts:

- All 180 non-null curriculum `quiz_title` references resolve to an old quiz.
- The curriculum has 79 distinct referenced quiz titles.
- Old and current quiz title sets have zero overlap.
- Every old quiz’s `question_count` matches its actual child count.
- There are no duplicate `(quiz_id, question_text)` pairs.
- All old quiz `lesson_id` values are null, avoiding false links to current lessons.
- The old question schema has 83 populated `option_f`, 16 `option_g`, and 4 `option_h` values.
- Five questions use F and four use G as the primary answer; 45 multi-answer strings mention F, G, or H.
- Therefore F/G/H columns and API/UI handling must be added and staging-tested before quiz import.
- The old curriculum has `exam_code`, absent from the current schema. It must be preserved through a schema migration and model/API support.

The import must regenerate quiz/question primary keys, map questions through the newly assigned quiz IDs, use `video_key` and quiz title as idempotency keys, and execute inside one transaction.

## Exact old-only records left outside automatic restoration

### Tickets — REPLACED / OBSOLETE

- `Locked out user`
- `Password Reset Request for Company Email`
- `Unable to Connect to Office Wi-Fi`
- `test` — obsolete test data

The first three scenarios are covered by richer current tickets; none has a submission.

### Resource — REVIEW

- Title: `Test Mine`
- URL: `https://www.youtube.com/watch?v=PIuwTIaOGWk`
- Type: `Video`
- Week: `1`
- Category: `Chapter 1`

The title and lack of provider/license/lesson mapping make its intended production use unclear. It must remain only in the backup pending human review.

### Student activity — HISTORICAL

- `login_streaks`: 5 old rows
- `squad_activity`: 15 old rows
- `student_domain_mastery`: 4 old rows
- `student_methodology_progress`: 11 old rows, mostly already orphaned
- `video_watches`: 1 old row for deleted student ID 7
- `weekly_domain_leads`: 8 old badge rows

The old live accounts have IDs 12–17, while much of the activity references previously deleted IDs 1, 2, 4, and 7. The current accounts use IDs 1–7. Importing by ID would assign activity to the wrong people.

## Requested feature checks

- Study plans: no dedicated table exists; the current week plan is derived from curriculum/progression data.
- Bookmarks: no bookmark table exists.
- Achievements: no achievement table exists.
- Badges: no badge catalog exists; eight historical badge names are embedded in `weekly_domain_leads`.
- Configuration: no general configuration table exists. `alembic_version` is schema metadata; AI rate-limit rows are runtime counters.
- Attempts, submissions, evidence, XP history: both databases contain zero quiz attempts, ticket submissions, lab/capstone/CLI attempts, evidence artifacts, RCA submissions, and XP ledger rows.

## Pre-import decision

Approved for automatic staged restoration: `curriculum_videos`, `quizzes`, and `questions` only.

Everything else is either already represented, replaced, empty, historical, obsolete, or requires human review. No unrelated old-only table is approved for automatic import.

## Staging validation — completed before live import

Staging database: `.tmp/study-tracker-restore-stage-20260718/nexus-stage.db`, created with SQLite's online backup API from the current database.

- Upgraded from migration `b7c8d9e0f1a2` to `c8d9e0f1a2b3`.
- Dry run: 182 videos, 79 quizzes, and 778 questions would be inserted; transaction rolled back.
- First staged import: inserted exactly 182 videos, 79 quizzes, and 778 questions.
- Second staged import: inserted zero rows and skipped all 182 videos and 79 quizzes as exact matches, proving idempotency.
- Final staged totals: 182 curriculum videos, 104 quizzes, and 967 questions; 137 videos are active.
- Restored contents exactly match the old database by stable identifiers and non-surrogate fields.
- All quiz titles referenced by curriculum rows resolve; every quiz's declared question count matches its child rows.
- Preserved extended choices: 83 F options, 16 G options, 4 H options, five primary-F answers, and four primary-G answers.
- `PRAGMA integrity_check` returns `ok`.
- The foreign-key violation set remained at the same five pre-existing current-database rows before and after import.
- Every table other than `curriculum_videos`, `quizzes`, `questions`, and migration metadata retained the same row contents as the current database.
- Isolated API validation returned HTTP 200 for curriculum and an eight-option quiz, returned all 137 active videos, and exposed both exam codes (`220-1201`, `220-1202`).
- Backend test suite: 109 passed.
- Frontend production build: passed.

At completion of this section, `backend/nexus.db` had still not been modified.

## Live restoration result

The approved dataset was restored after the audit and staging gates passed.

- Pre-import online backup: `backend/nexus.db.pre-study-tracker-restore-20260718T015810Z` (`PRAGMA integrity_check = ok`; five pre-existing FK violations).
- Live migration: `b7c8d9e0f1a2` → `c8d9e0f1a2b3`.
- Live import: 182 curriculum videos, 79 quizzes, and 778 questions inserted in one transaction with remapped quiz IDs.
- Immediate second run: zero inserts; 182 video and 79 quiz exact-match skips.
- Post-import database totals: 182 curriculum videos, 104 quizzes, and 967 questions.
- Post-import validation: 137 active videos, zero unresolved curriculum quiz titles, zero quiz question-count mismatches, exact old-to-live restored row comparison, and `PRAGMA integrity_check = ok`.
- All non-target tables exactly match the pre-import backup by row contents. The five existing methodology-progress FK violations are unchanged.
- Authenticated live API checks: 137 active curriculum videos and 104 published quizzes returned with HTTP 200.
- Live page check: `https://nexus.builtfromzero.fyi/study-tracker` returns HTTP 200 at the same final URL and serves the SPA shell. Its deployed JavaScript contains the `/study-tracker`, `Study Tracker`, and `CompTIA A+ Study Tracker` markers; unauthenticated browser routing is handled by `RequireAuth`, not by a not-found route.
- No service or container was restarted, as required. The already-running backend and frontend remain on their pre-change process/bundle until an explicitly authorized deployment/restart activates the new F/G/H API/UI compatibility. The restored tracker itself is already live through the existing component and API; the nine legacy primary-F/G quiz answers require that activation before they are fully answerable in the browser.

## Route and source-history conclusion

Conclusion: **still present and linked**. The route was never deleted, renamed, or hidden.

- Frontend component: `frontend/src/pages/StudyTrackerPage.jsx`
- Route and navigation: `frontend/src/App.jsx` (`/study-tracker`, wrapped in `RequireAuth`)
- API client: `frontend/src/services/api.js`
- Backend router: `backend/app/routers/study_tracker.py`
- Model: `backend/app/models/curriculum_video.py`
- Original introduction: `0175cb8d6ffa0b964327f7b766018bbcc7767a92` (`V8`, 2026-03-01)
- The 24-week swap: `95f8ae09e435c4d0197f08f44e5d44740ef7da6d` explicitly says it used a fresh SQLite database and a swap rather than a merge. It retained the page and route but omitted tracker seeding, producing the empty current table.
- `cf0cf52c328871029bf85850f1fdff1ad786bf99` changed cohort-account/authentication files only and did not affect the tracker route, component, or dataset.
- Backup/current diff: `frontend/src/App.jsx` is byte-identical; `frontend/src/pages/StudyTrackerPage.jsx` is content-identical after ignoring CRLF/LF differences; the tracker backend router differs only by the newly added `exam_code` response field.
- Built frontend: the live bundle contains ten `/study-tracker` string occurrences and the page title. Tracker data was database-backed, so neither the old nor current bundle embeds the 182 URLs.

Link counts need a terminology distinction: the tracker contains **182 Professor Messer video-page URLs**, not literal `youtube.com` or `youtu.be` URLs. Before restoration the current database had zero tracker URL rows and zero tracker quiz references. The old database/backup has 182 non-empty video URLs, zero literal YouTube-domain URLs, 180 quiz-title references, and 79 distinct referenced quizzes. After restoration the current database has those same counts. Generic source code contains YouTube embed/placeholder handling, but no hard-coded tracker catalog.

## Old Database Coverage

### Restored

- `curriculum_videos`: all 182 old rows (137 active and 45 intentionally inactive historical rows).
- `quizzes`: all 79 old tracker quizzes, alongside the 25 current 24-week quizzes.
- `questions`: all 778 old quiz questions, alongside the 189 current questions.
- Required metadata compatibility: `curriculum_videos.exam_code` and `questions.option_f`, `option_g`, and `option_h`.

### Already represented in the new build

- The one old module and lesson (`MOD-000` / `CompTIA 6-Step Process`).
- All 48 CLI labs, 50 command-reference rows, four CompTIA objectives, and the methodology framework.
- Current replacements for the role ladder, promotion gates, 24-week modules/lessons, five lab templates, 48 tickets, and 25 new-build quizzes.

### Intentionally left only in the backup

- Four old tickets: three superseded generic scenarios and one obsolete `test` row.
- One `resources` row (`Test Mine`, YouTube URL), classified REVIEW.
- Historical activity: five login streaks, 15 squad activities, four old mastery rows, 11 old methodology-progress rows, one video watch, and eight weekly-domain-lead/badge rows.
- Old student/account rows and password hashes.

### Requires human review

- Identity mapping for all historical activity because old numeric student IDs collide with unrelated current users and several old references were already orphaned.
- The purpose/licensing/placement of resource `Test Mine`.
- The five pre-existing current `student_methodology_progress` FK violations, which were preserved rather than altered during this restoration.

### Remaining old content status

- Lessons: none missing; the sole old lesson is already represented.
- Labs: none missing; the old database has no lab templates and the shared 48 CLI labs match.
- Quizzes: none missing; all 79 old quizzes and 778 questions were restored.
- Tickets: four remain intentionally backup-only (three replaced, one obsolete).
- Resources: one remains backup-only pending review.

## Final deployment verification

The compatibility code and frontend bundle were activated after the restoration audit.

- Backend: existing `nexus-admin-academy.service`, active on systemd with the updated model, API, and A–H submission validator.
- Frontend: existing `nexus-frontend` nginx container, serving `index-BfyqlHT9.js`.
- Fresh pre-verification online backup: `/home/nexus/backups/nexus-admin-academy/study-tracker-final-verification-20260718T022539Z`.
- Safe identity strategy: explicit student ID `900000001`, selected only after proving zero occurrences across 23 declared or logical student-reference columns. Cleanup targeted every scanned reference column by that exact ID.
- Authentication: public login and `/auth/me` passed without retaining or recording the temporary credential/token.
- Live route/API: `/study-tracker` HTTP 200 with the deployed bundle; 137 active tracker videos, 104 published quizzes, 25 modules, and 63 lessons.
- Live scoring: existing 24-week A–E quiz 8/8; restored primary-F quiz 9/9; restored primary-G quiz 19/19.
- Cleanup proof: all 42 application tables matched the fresh backup by schema, row count, and content hash; zero changed tables.
- Database invariants: 182 curriculum rows, 104 quizzes, 967 questions, zero quiz attempts, 12 methodology-progress rows, five unchanged known FK violations, and `PRAGMA integrity_check = ok`.
- Logs: no backend warnings/errors, API 4xx/5xx, authentication failures, migration failures, nginx errors, or frontend asset errors in the final verification window.
- Verification suites: 110 backend tests passed; frontend CLI sanity and 48-lab validation passed; production build passed. The frontend project has no configured lint or unit-test script.
