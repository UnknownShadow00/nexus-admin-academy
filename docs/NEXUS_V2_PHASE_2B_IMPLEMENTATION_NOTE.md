# Nexus V2 Phase 2B — first student-facing V2 experience

Phase 2B turns the frozen reference module
`module.aplus.core1.ip_configuration` into a complete, data-driven student
flow. It does not add curriculum, change the legacy week path, deploy, or seed
production. Production remains feature-flagged off at migration `0064`.

## Routes and feature isolation

The development-only student routes are:

- `/learning-v2`
- `/learning-v2/modules/:moduleKey`
- `/learning-v2/modules/:moduleKey/lessons/:lessonKey`
- `/learning-v2/modules/:moduleKey/assessments/:assessmentKey`
- `/learning-v2/modules/:moduleKey/explain/:promptKey`
- `/learning-v2/modules/:moduleKey/practical/:assessmentKey`
- `/learning-v2/modules/:moduleKey/service-desk/:assessmentKey`

Both layers default off. The backend returns 404 unless
`V2_CURRICULUM_ENABLED=true`; the frontend omits the navigation item and route
definitions unless `VITE_V2_CURRICULUM_ENABLED=true`. This follows the existing
environment-settings convention and introduces no feature-flag framework.

## Backend presentation API

`app/services/v2_curriculum_service.py` is the thin presentation service. It
composes certification/version/domain, module purpose, ordered lessons,
objectives, resources, assessments, Explain prompts, the current student's
progress, and one derived next action. React never reconstructs these
relationships or contains curriculum identifiers.

`app/routers/v2_curriculum.py` exposes authenticated, student-scoped endpoints:

- `GET /api/v2/curriculum`
- `GET /api/v2/curriculum/modules/{module_key}`
- `GET /api/v2/curriculum/modules/{module_key}/lessons/{lesson_key}`
- `POST .../lessons/{lesson_key}/complete`
- `POST .../resources/{resource_key}/activity`
- `GET|POST .../assessments/{assessment_key}` and `.../submit`
- `GET|POST .../explain/{prompt_key}` and `.../submit`
- `POST .../service-desk/{assessment_key}/launch`

Question responses omit answer keys, acceptable-answer lists, rubrics, model
details, and grading internals. Answers and explanations are returned only
after submission. External resource URLs are accepted only when they are
absolute HTTP(S) URLs.

## Frontend architecture and V1 reuse

The new pages live under `frontend/src/pages/v2/`; small shared status,
breadcrumb, loading, and error components live under
`frontend/src/components/v2/`. They reuse the existing Nexus application
shell, authentication gate and student session, navigation, button/card/panel
styles, dark mode, responsive navigation, API request/error conventions,
icons, spinner, and existing `LabPage`. The Service Desk is launched as the
existing integrated application. No second quiz, lab, ticket, or visual design
system was created.

The existing generic quiz screen is deeply coupled to `QuizAssignment`,
`TrainingWeek`, XP, and the 40% gate. Phase 2B therefore reuses its interaction
pattern and the existing `Question` bank/deterministic grading services through
a small V2 assessment context rather than cloning or weakening that engine.
The shared V1 routes and behavior are unchanged.

All visible curriculum facts come from the API: titles, counts, resource URLs,
objective mappings, assessment keys, lab IDs, Service Desk scenario, and
Explain prompts. A unit test deliberately renders a made-up module key and
title supplied only by its mocked API response.

## Student experience

The entry page shows the current certification, exam version, current module,
lesson and assessment progress, and one prominent Continue action. The module
page presents the formula as five quiet sections: Learn, Check Your Knowledge,
Practice, Troubleshoot, and Explain. It uses plain-language statuses and
separate progress facts instead of a misleading overall percentage.

Lesson pages render the loaded Phase 2A Markdown with `react-markdown` (raw
HTML is not enabled), styled headings, lists, inline/code blocks, tables, and
links. External links open in a new tab with `noopener noreferrer` and an
assistive-text indication. Tables/code remain scrollable on narrow screens.
Navigation provides Back to module, Previous, Next, Mark complete, and
Continue controls.

Resources show Required or Optional, title, provider, type, open state, and
completion state. Opening records `opened_at` but never implies completion or
mastery. Students explicitly mark a resource complete, recording
`completed_at`. Missing links and mappings have non-interactive explanations.

Quick Checks and the Module Quiz draw 3–5/12 configured questions from the
existing bank. Supported choice and short-answer questions are graded by the
existing deterministic rules. The UI shows score, pass/not-yet-pass,
explanations, missed answers, retry, and persisted attempt history. They do not
write a legacy `QuizAttempt`, award XP, read a `TrainingWeek`, or touch the 40%
gate. Quick Checks are unlimited/formative; the Module Quiz uses its configured
70% threshold.

## Continue and completion rules

`resolve_continue()` derives one action; there is no student-position column.
The sequence is:

1. First lesson with an unfinished required resource
2. First unfinished lesson
3. That lesson's unfinished Quick Check
4. Module Quiz
5. Guided practical
6. Service Desk scenario
7. Each Explain prompt
8. Review the completed module

Optional resources never block Continue or completion. `module_complete` is
true only when every loaded lesson, every required resource, every Quick Check,
the 70% Module Quiz, mapped practical, mapped Service Desk activity, and every
active Explain prompt are complete/passed. A pending or mentor-review Explain
response is not complete. These rules contain no TrainingWeek, weekly
prerequisite, video-percentage gate, or legacy unlock check.

## Explain persistence and grading

Phase 1C had durable grading jobs but no durable original submission table for
InterviewPrompt answers. Migration `0066_v2_explain_submissions` therefore adds
the minimal `v2_explain_submissions` table: student, prompt, immutable submitted
answer, attempt number, and submission time. The answer is committed before
calling `submit_for_grading()`. Deterministic outcomes display their result;
ambiguous answers create the real Phase 1C pending job and display “Your
response was saved and is waiting to be graded.” No AI result is invented and
no provider, confidence, queue, GPU, or internal error is exposed. Submission
history persists and grading status remains student-scoped.

## Practical and Service Desk integration

The practical redirect resolves the mapped `lab_id` from module data and opens
the existing `LabPage` with a validated V2 module/assessment context. Small
changes hide week terminology, add a V2 back route and label the evidence
field. Existing start/submit handlers remain authoritative; only a correctly
mapped V2 assessment bypasses the legacy week context. Submission is reflected
into V2 progress on the next module read.

The Service Desk redirect requests a launch from the curriculum API. The API
validates the mapped existing scenario, creates/idempotently reuses an existing
`ServiceDeskAssignment`, records in-progress status, and sends the browser to
the existing ticket UI. Existing server-side Service Desk attempts and grading
remain authoritative and are synchronized into V2 progress. React StrictMode's
duplicate development request is handled by the existing unique constraint and
an idempotent retry.

## States, responsive behavior, and accessibility

All new surfaces provide loading and plain-language error states with retry,
plus explicit unavailable states for missing resources, practicals, and Service
Desk mappings. Unknown modules return a student-safe 404. Pending grading and
no-submission history have dedicated UI. There are no inert placeholder
buttons or raw backend errors.

The new pages use semantic links/buttons, fieldsets for choice questions,
labels for short-answer and Explain fields, headings in order, text labels in
addition to color, visible inherited focus rings, and accessible external-link
text. Buttons wrap into tap-friendly stacks on mobile. Browser checks at
1440×900 and 390×844 found no horizontal document overflow. Markdown, quiz
answers, progress cards, and the sticky lesson controls remained readable.

## Verification

- Frontend unit tests: **9 files, 31 tests passed**.
- Frontend production build: passed (existing large-chunk warning only).
- Frontend lint/typecheck: no scripts are defined; none were invented.
- Frontend dependency audit: `npm audit --audit-level=high`, **0 vulnerabilities**.
- Service Desk regression: **74 tests passed**, strict lint and typecheck passed.
- Targeted V2 API: **10 tests passed**, including a staged Continue/completion
  walk through every required activity with optional resources unfinished.
- Frozen Phase 1C/2A/2A.1 checks: **63 tests passed**.
- Full backend regression: **715 tests passed** (baseline 705 plus 10 Phase 2B
  API tests); Alembic guard, V1 quiz/week behavior, and Service Desk grading are
  included in that suite.
- Browser E2E: **1 full flow passed** in 12.0 seconds against a disposable
  migrated/loaded SQLite database and disposable students.
- Migration `0066`: scratch upgrade to head, downgrade to `0065`, re-upgrade to
  head passed; final scratch revision is `0066_v2_explain_submissions`.
- Screenshots were inspected at `/tmp/nexus-v2-entry-desktop.png`,
  `/tmp/nexus-v2-lesson-desktop.png`, and `/tmp/nexus-v2-module-mobile.png`;
  they are intentionally not committed.

The browser flow covered login, entry/module rendering, Lesson 1, explicit
resource and lesson completion, reload persistence, Quick Check, next/direct
lesson navigation, Module Quiz, existing guided Lab submission, existing
Service Desk launch, ambiguous Explain submission/pending state, cross-student
grading-job denial, progress roll-up, mobile overflow, and unknown module.

Visual review found the first entry and module layouts clear and the lesson
content readable. The practical initially carried legacy “Week” wording and
the evidence textarea lacked a useful label; both were corrected. A duplicate
Service Desk assignment race appeared under React StrictMode and was made
idempotent. No broader application redesign was needed.

## Production read-only verification

On 2026-08-29 UTC, read-only checks found:

- `nexus-admin-academy.service`: active/running
- `GET http://127.0.0.1:8000/health`: HTTP 200
- `GET /api/v2/curriculum`: HTTP 404 (production experience remains off)
- production `backend/nexus.db`: revision `0064_v2_ai_grading_infrastructure`
- `0065` and `0066` tables: not applied
- all production V2 curriculum/content/progress/grading tables: empty
- production student count: 7
- database SHA-256 remained
  `cb344b1bae6542f9aab26bd6b3284e1aa1897cb53bbc21005bcb2aee38ddf41b`
  across the verification; Git reports no database modification

No production migration, loader, seed, deployment, account creation, or
student migration was run.

## Deferrals and decision

The mentor UI was deferred: the Phase 2A mentor report/API already exists, and
adding an admin surface would expand risk after the complete student path.
Also deferred as required: APIPA VM, Windows terminal simulator, GPU/vLLM,
advanced mentor/cohort analytics, additional A+/Network+ curriculum,
gamification, and week-system cutover.

The Python dependency audit also reports `PYSEC-2026-3721` against the virtual
environment's `pip 26.1.2` tooling package (fixed by pip 26.2). It is not an
application runtime dependency introduced by Phase 2B; the environment was not
mutated during this phase.

The remaining rough edge is architectural: V2 assessment presentation is now
small and clean, but the legacy quiz page is still too week/XP/gate-coupled to
serve as a shared renderer without a larger V1 refactor. That refactor should
be considered only after this UI pattern is approved. The current production
bundle also retains its pre-existing large-chunk warning.

Recommendation: **approve this UI pattern and expand A+**, while keeping the
feature flag off until the development migrations and next module are approved.
