# Nexus V2 Phase 2C — Mentor View and Progress Intelligence

Phase 2C adds the smallest useful mentor-facing V2 experience for the frozen
reference module, `module.aplus.core1.ip_configuration`. It composes existing
Nexus records; it does not add a curriculum module, analytics warehouse,
student ranking, mastery model, or legacy progression dependency.

## Mentor routes and feature isolation

Frontend routes:

- `/admin/v2-progress` — cohort progress, review queue, weak areas, suggestions,
  student questions, filters, and Cohort Focus
- `/admin/v2-progress/students/:studentId` — one student's detailed module report
- `/admin/v2-grading/:pendingGradeId` — thin Phase 1C grading/override UI

Backend routes:

- `GET /api/admin/v2/mentor/cohort/{module_key}`
- `GET /api/admin/v2/mentor/module/{module_key}/student/{student_id}`
- `GET /api/admin/v2/mentor/cohort-focus`
- `PUT /api/admin/v2/mentor/cohort-focus`
- Existing Phase 1C `GET /api/admin/grading/queue`,
  `GET /api/admin/grading/{id}`, and `POST .../{id}/override`

Both the navigation/routes and mentor API reuse the existing V2 switch:
`VITE_V2_CURRICULUM_ENABLED` and `V2_CURRICULUM_ENABLED`. Both default off.
The backend responds with 404 while V2 is disabled. All mentor reads/writes
also use the existing `verify_admin` dependency. A student JWT receives 403 and
the React admin route redirects a non-admin session to `/admin-login`.

## Data composition

`app/services/v2_mentor_service.py` is a read model over existing sources:

- `Student` for cohort identity
- certification/version/module/lesson metadata for helpful labels
- `V2ModuleActivity.detail.attempts` for Nexus Quick Check and Module Quiz work
- `Question` and `QuestionV2Meta` for question text, retained answer, correct
  option text, explanation, objective, and topic tags
- `V2ExplainSubmission`, `PendingGrade`, AI attempt history, and append-only
  mentor overrides for Explain responses
- `StudentResourceActivity` for student notes and external-practice self-reports
- authoritative `LabRun` and `ServiceDeskAttempt`/`ServiceDeskAttemptGrade`
  records for practical and ticket results
- the existing student V2 `module_view()` and `resolve_continue()` path for
  current position

No duplicate analytics table or cached statistic was introduced. The report
does not read or write `TrainingWeek`, the legacy 40% gate, XP, or promotion.

## Student cohort view

The cohort table shows name, certification/module context, lessons completed,
Module Quiz status/score, practical status, Service Desk status, Explain review
state, weak-topic labels, and the derived current activity. It contains no
rank, peer comparison, leaderboard, or invented percentage.

The focused filter set is: all students, incomplete module, failed Module
Quiz, Explain needs review, and one selected weak topic. Loading, API error,
no-cohort-data, no-review-work, no-weakness, no-note, and no-filter-match states
are explicit.

## Student detail UX

The detailed report shows:

- lessons and required-resource completion
- Quick Check states/scores
- Module Quiz score, threshold context, and pass state
- module completion and derived current activity
- objective code plus official objective wording
- friendly weak topics and miss counts
- every retained missed question, latest student answer, correct option text,
  explanation, objective/topic, assessment source, and times missed
- every durable Explain submission, including deterministic-only submissions,
  pending/AI state, confidence/review signal when present, rubric/version,
  expected concepts, resolved result, and complete mentor override history
- practical and Service Desk summary plus links to the existing deep reviewers
- external-practice self-reports, clearly separated from Nexus results

Internal AI endpoint, provider, model, raw response, retry message, and
infrastructure error fields are removed from the mentor module report. The
existing protected grading detail remains the authoritative mentor-only audit
surface.

## Weakness and repeated-miss rules

The logic is intentionally transparent:

1. Read each stored Nexus Quick Check or Module Quiz attempt.
2. Count one miss when a result has `is_correct == false`.
3. Count repeated misses per question across attempts.
4. Sum those misses under the question's official certification objective.
5. Map the reference module's specific authored tags to a small friendly topic
   vocabulary. Specific signals such as DNS or APIPA take precedence over the
   generic `troubleshooting` tag.
6. For cohort aggregation, count each affected student once per topic, while
   retaining total misses and the number of students with repeated misses.
7. Sort by students affected, then total misses, then topic name.

The current friendly topics are DHCP and APIPA, DNS troubleshooting, Default
gateway, Subnet masks, IPv4 configuration, Troubleshooting methodology, and
Windows network commands. An unmapped question falls back to the official
objective wording. Phase 2A's older development-only `missed_question_ids`
payload remains readable; Phase 2B+ full attempts are authoritative.

External-practice completion, reported score, confusing topic, note, and
question are never inputs to the weakness totals, completion calculation, or
Nexus mastery.

## Cohort aggregation and office-hours suggestions

`weak_areas` reports the topic, students affected, cohort size, total actual
assessment misses, and students with repeated misses. `suggested_review_topics`
is the first five rows of that deterministic ordering, phrased as, for example,
“DHCP and APIPA — 4 students showing difficulty.” It is a teaching aid only;
it neither invokes AI nor changes curriculum.

## Explain grading queue and override workflow

The existing Phase 1C queue now includes unresolved pending/manual work and
retryable failures in addition to low-confidence/review-recommended and
terminal work. Priority remains deterministic:

1. low-confidence or AI-review-recommended result
2. exhausted retries
3. retryable/terminal grading failure
4. pending/manual review

The UI displays the prompt, original student answer, deterministic matched and
missing concepts, rubric version, score/pass controls, and a required mentor
reason. Submission calls the existing override API. It appends a
`MentorGradeOverride`; it never overwrites the original response, AI attempt,
deterministic finding, or prior override. Returned history is rendered
immediately.

## Student questions and external practice

Module-linked `StudentResourceActivity` records surface resource, completion,
reported score, student note, confusing topic, and question for mentor. Every
such item is labelled “Self-reported external practice,” and the UI states
that reported scores do not affect Nexus mastery or completion. Screenshots
are not required.

## Service Desk and practical integration

The report reuses the V2 engine synchronization used by the student Continue
view. A Service Desk attempt's authoritative score/pass and grade details are
used when present. The mentor-useful breakdown is derived from the existing
process rubric's `objective_checks` and weights for Investigation, Diagnosis,
Remediation, Verification, and Documentation. The page links to the existing
Service Desk Review instead of recreating it.

The practical uses the mapped authoritative `LabRun` status, score, feedback,
notes, and run id when available, then links to the existing Labs admin page.
No second lab reviewer was added.

## Cohort Focus

Cohort Focus reuses the existing `app_settings` table with key
`v2_cohort_focus`. The persisted value contains the module key and display
labels, for example “CompTIA A+ → IP Configuration & Basic Connectivity
Troubleshooting.” The update validates that the module exists. This is not a
progression gate and no migration was required.

## Tests and browser verification

Backend Phase 2C tests cover repeated misses, objective isolation, cohort
student counts, deterministic suggestions, exclusion of external scores,
student questions, deterministic and queued Explain submissions, complete
override history, feature flag and admin authorization, Cohort Focus,
current-position derivation, authoritative Service Desk breakdown, and no
legacy progression interaction.

Frontend tests cover flag default-off behavior, cohort/list rendering, useful
filters, weak areas, review work, student notes, detailed misses, Explain
pending state, mentor grading and returned history, Service Desk breakdown,
external practice, loading, errors, and empty states.

The Playwright run used an isolated SQLite database migrated through 0066 and
exactly five disposable students:

- Student A: passed Module Quiz with a DNS miss
- Student B: failed Module Quiz, repeated APIPA misses, pending Explain, and an
  external-practice question
- Student C: lessons incomplete
- Student D: weak Service Desk Verification and Documentation
- Student E: strong lesson/assessment/practical/Service Desk progress

The browser flow logged in as the disposable admin, viewed all students,
opened Student B, inspected the quiz/weak objective/missed question, opened the
pending Explain response, submitted a mentor override, confirmed history,
viewed cohort weakness and suggestions, updated Cohort Focus, verified a
student request receives 403, verified the admin route redirects to admin
login for the student session, and checked tablet overflow. An initial shared
header overflow at 768 px was corrected by keeping the existing mobile menu
through the `xl` breakpoint; the rerun passed.

Verification results:

- frontend: 12 files / 36 tests passed
- frontend production build: passed; existing >500 kB chunk warning remains
- frontend audit: `npm audit --audit-level=high`, 0 vulnerabilities
- frontend lint/typecheck: no scripts are defined
- targeted backend Phase 2C: 7 tests passed
- full backend: 722 tests passed
- Playwright: 2 tests passed
- migration: none for Phase 2C; scratch head remained 0066

## Development pip warning

The development virtual environment remains on pip 26.1.2. `pip-audit` reports
only `PYSEC-2026-3721`, fixed in pip 26.2. Pip is tooling rather than an
application lock dependency. It was not upgraded because the task was mapped
to the workspace-write sandbox profile and an installer/network mutation would
require the separate network profile. Production was not touched.

## Production read-only verification

Final read-only checks on 2026-08-29 UTC found:

- `nexus-admin-academy.service`: active
- `/health`: HTTP 200
- `/api/v2/curriculum`: HTTP 404 (production V2 remains off)
- production revision: `0064_v2_ai_grading_infrastructure`
- `v2_module_activity` (0065) and `v2_explain_submissions` (0066): absent
- no Phase 2C migration exists
- production certification/content/grading V2 tables: all empty
- production students: 7
- `backend/nexus.db` SHA-256 before and after:
  `cb344b1bae6542f9aab26bd6b3284e1aa1897cb53bbc21005bcb2aee38ddf41b`
- Git reports no production database modification

No production deploy, migration, loader, seed, account change, or student
migration was performed.

## Deferrals and remaining rough edges

No additional A+ module, student-facing cohort feature, peer ranking, trend,
AI suggestion, curriculum mutation, Service Desk reviewer, Lab reviewer,
local model, or analytics infrastructure was built. The cohort currently
means all non-mentor `Student` records because Nexus has no separate V2 cohort
membership model; this is appropriate for the current five-student operation
but should be revisited only if multiple simultaneous cohorts become real.
Topic labels are intentionally a small transparent vocabulary for the frozen
module, not a generalized mastery taxonomy. The inherited production bundle
warning and development pip advisory remain documented.

Recommendation: **approve the mentor pattern and expand A+**, while keeping
production V2 off and treating any next curriculum module as a separate phase.
