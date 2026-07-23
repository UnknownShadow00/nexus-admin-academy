# Service Desk Lab Architecture and Integration Plan

Status: planning blueprint for human review

Planning branch: `feature/service-desk-lab-planning`

Starting commit: `b47f9b1df1ebb811a79bfc14382d727dc20d1f57`

Scope: architecture and integration planning only; no Service Desk Lab implementation, migrations, routes, dependencies, infrastructure, or production changes are included.

## Planning baseline

- **Confirmed from code:** the branch was created from clean synchronized `main` at `b47f9b1df1ebb811a79bfc14382d727dc20d1f57`.
- **Confirmed from code:** My Training, persistent quiz mappings, weekly progression, Practice Library, Progress, admin weekly controls, and their automated tests are present.
- **Confirmed from code:** current Support Tickets routes, models, student pages, review workflow, tests, and My Training references remain present.
- **Confirmed from code:** a repository-wide search found no Service Desk Lab source, model, route, migration, dependency, or infrastructure implementation. Existing mentions in `TASKS.md` and `docs/MY_TRAINING.md` explicitly defer it.
- **Confirmed from documentation:** this task did not access or change production services or data. Only this plan and the required completion log are permitted to change.

## Evidence labels

- **Confirmed from code** means the behavior is implemented in the cited source, model, route, service, or test.
- **Confirmed from documentation** means the claim is operational or product guidance in a current repository document.
- **Strong recommendation** is the proposed implementation contract for Service Desk Lab.
- **Optional future enhancement** is deliberately outside the MVP.
- **Uncertain and requiring a decision** identifies a product, policy, capacity, or governance choice that cannot be proved from the repository.

## 1. Executive summary

**Strong recommendation:** build Service Desk Lab as a new, versioned scenario engine that reuses Nexus authentication, students, My Training, roles/ranks, progress conventions, uploads infrastructure, AI-cost accounting, and the low-level Proxmox/Guacamole clients. Do not expand `Ticket` and `TicketSubmission` into the new engine. Preserve those tables and routes as legacy history and progression inputs, then migrate selected ticket content through a compatibility adapter and explicit crosswalk.

The browser-first MVP should be available from **Practice Library → Service Desk Lab**, behind a feature flag, with a lazy-loaded workspace at `/service-desk`. Its first five scenarios should be Locked User Account, Password Reset, MFA Reset, BitLocker Recovery, and New Employee Onboarding. The first tools should be an Employee Directory, a combined Identity & Access console, BitLocker lookup, a searchable Knowledge Base, and ticket communication/resolution controls. All technical actions must be validated and recorded server-side.

Learning Mode and Simulation Mode must be two policies over the same immutable scenario version, state machine, attempts, events, skill tags, and grading contract. A scenario update creates a new version; it never changes a completed attempt. The browser receives only a safe state projection, never root causes, expected actions, hidden rubric rules, or instructor notes.

Proxmox/Guacamole belongs in a later phase after the browser engine is reliable. Existing clients are useful building blocks, but `VmAssignment` is coupled to `LabRun` and FastAPI `BackgroundTasks` is not a durable environment broker. AI belongs later still: deterministic actions and resulting state grade technical work; AI may grade communication and documentation only when grounded in the pinned scenario, event history, transcript, rubric version, and human-review controls.

## 2. Confirmed Nexus architecture

### 2.1 Application and deployment

| Area | Finding and evidence | Classification | Service Desk consequence |
|---|---|---|---|
| Frontend | React 18, Vite, React Router, and Tailwind are declared in `frontend/package.json`; `frontend/src/main.jsx` installs `BrowserRouter`, `ErrorBoundary`, and the toaster. Shared primitives such as `.panel`, `.btn-primary`, `.btn-secondary`, and `.input-field` live in `frontend/src/styles.css`. | Confirmed from code | Reuse the visual language and router. Lazy-load the whole workspace and each large tool. |
| Frontend routing | `frontend/src/App.jsx` contains the student/admin information architecture and all SPA routes. Admin pages are already loaded with `React.lazy`; student pages are currently eager. | Confirmed from code | Add one lazy student shell and one lazy admin shell during implementation; do not add simulated tools to global navigation. |
| Backend | `backend/app/main.py:create_app` creates FastAPI, includes routers, defines error envelopes and `/health`; SQLAlchemy 2 models and Alembic migrations back the API. | Confirmed from code | Follow the existing router/service/model split and `{success, data}` response envelope from `backend/app/utils/responses.py:ok`. |
| Database | `backend/app/database.py` defaults to SQLite, enables SQLite foreign keys, and supports PostgreSQL/JSONB variants. `docker-compose.yml` is the PostgreSQL deployment alternative. | Confirmed from code | MVP can support the current five-student SQLite deployment, but event/queue concurrency and scale testing should define the PostgreSQL readiness threshold. |
| Production | `docs/DEPLOYMENT.md` documents the active systemd backend on port 8000, nginx frontend container, Cloudflare HTTPS, persistent SQLite database/uploads, backups, health checks, and rollback. | Confirmed from documentation | Deploy later through the existing process; do not create a parallel Service Desk deployment. |
| Background work | `backend/app/routers/labs.py:_provision_vm_task` uses FastAPI `BackgroundTasks`; no Celery, RQ, durable scheduler, or queue dependency exists. Backups use cron. | Confirmed from code | Browser MVP needs no queue. VM allocation and AI batch work require a durable job abstraction before launch. FastAPI itself recommends a larger queue tool for heavy multi-process work ([FastAPI Background Tasks caveat](https://fastapi.tiangolo.com/tutorial/background-tasks/#caveat)). |
| Bundle | `frontend/vite.config.js` has no manual chunk strategy; the checked build artifact `frontend/dist/assets/index-HCDR1Dj7.js` is about 1.0 MB. | Confirmed from code | Route-level and tool-level splitting is an MVP acceptance criterion. Do not import all tools into the main bundle. |

### 2.2 Authentication and authorization

- **Confirmed from code:** `backend/app/services/auth_service.py:create_access_token`, `decode_token`, and `get_current_student` implement JWT student authentication through a bearer token or the HTTP-only `student_session` cookie. `ensure_student_access` permits self-access or a student with `is_mentor=True`.
- **Confirmed from code:** `backend/app/models/student.py:Student` has `is_mentor`; there is no mentor capability table or assigned-student/cohort relation.
- **Confirmed from code:** administrator authentication is separate. `backend/app/services/admin_auth.py` validates environment-backed credentials/API keys and an expiring in-memory `admin_session`; `backend/app/routers/admin_session.py` manages login/logout and mentor impersonation.
- **Confirmed from code:** `backend/tests/test_admin_session.py`, `test_security_hardening.py`, and `test_security_part9.py` cover student/admin separation, session behavior, and object ownership.
- **Strong recommendation:** retain current student and admin authentication, but introduce explicit Service Desk capabilities. `is_mentor` may identify the principal, but must not implicitly grant scenario publishing, organization reports, grade override, AI-cost, or environment administration.
- **Uncertain and requiring a decision:** Nexus has no authoritative mentor-to-student assignment. Before mentor APIs ship, decide whether mentors see all five students or only explicitly assigned students; the safer default is explicit assignments.

### 2.3 Security and storage baseline

- **Confirmed from code:** `backend/app/main.py` applies origin/referer CSRF checks to cookie-authenticated writes, CORS allowlists, HSTS behind HTTPS, `nosniff`, strict referrer policy, no-store API caching, and a same-origin CSP. Its current `Permissions-Policy` disables camera, microphone, and geolocation.
- **Confirmed from code:** `backend/app/models/evidence.py:EvidenceArtifact`, `backend/app/routers/evidence.py`, `tickets.py`, and `labs.py` provide bounded upload metadata, checksums, ownership checks, and validation status. Files are mounted under `/uploads/screenshots` by `backend/app/main.py`.
- **Strong recommendation:** reuse the storage and validation implementation, not the weak polymorphic link (`submission_type` plus unvalidated `submission_id`). Add an explicit Service Desk attempt-artifact join and an authorized download path. Scenario evidence, transcripts, and identity facts must not be exposed through guessable static URLs.

### 2.4 Learning, practice, progression, and administration

| System | Confirmed implementation | Service Desk implication |
|---|---|---|
| My Training | `TrainingWeek` and `TrainingWeekActivity` in `backend/app/models/training.py`; APIs in `backend/app/routers/training.py`; canonical state in `backend/app/services/training_service.py`; admin controls in `backend/app/routers/admin_training.py` and `frontend/src/pages/admin/AdminTrainingPage.jsx`. | Add one future `service_desk_scenario` activity type, never overload `support_ticket`. Completion must query a valid server-side attempt pinned to the assigned scenario version. |
| Weekly progression | `_TrainingContext.progress`, `_build_state`, `build_training_overview`, and `validate_training_curriculum` calculate completion, locking, next activity, and reference health. Tests are in `backend/tests/test_training_service.py`, `test_training_api.py`, and `test_admin_training_api.py`. | Extend the canonical service and validator so Home, My Training, and Progress continue to agree. |
| Progress math | `build_training_progress` counts required activity rows while content metrics deduplicate by `(activity_type, content_ref)`; video, quiz, practice, rank, and training measures are separate. | A scenario attempt counts once for the canonical assignment/activity, even if surfaced in several recommendations. Rank and training progress remain distinct. |
| Modules/lessons | `Module` and `Lesson` are in `backend/app/models/learning.py`; lesson completion uses `StudentLessonNote`. | Scenario prerequisites/remediation should reference stable existing lesson IDs. |
| Videos/quizzes | `CurriculumVideo`/`VideoWatch`; `Quiz`, `Question`, `QuizAttempt`, and `QuizAssignment` in `backend/app/models/quiz.py`; quiz APIs protect answers until submission. | Reference IDs only. Reuse quiz pass/attempt facts; never copy answers into a scenario payload. |
| Guided labs | `LabTemplate`/`LabRun` in `backend/app/models/lab.py`; lifecycle in `backend/app/routers/labs.py`. | Reuse links, evidence patterns, and low-level VM services; do not treat a submitted lab note as proof of a Service Desk state change. |
| Networking/terminal practice | `CliLab`/`CliLabAttempt` and `backend/app/routers/cli_labs.py`; frontend CLI/terminal pages. | Reuse terminal presentation and command-redaction patterns. The existing client-supplied command log is not authoritative enough for Service Desk grading. |
| Support Tickets | `Ticket`/`TicketSubmission`, student APIs, admin review, AI grading, evidence, XP, mastery. | Preserve and adapt; see Section 3. |
| Capstones | `CapstoneTemplate`/`CapstoneRun`; rank-filtered APIs in `backend/app/routers/capstones.py`; tests in `test_capstones.py` and `test_week_prerequisite_gating.py`. | Reuse gating concepts and history. Service Desk simulated shifts may later become capstone inputs, not bypass capstone rules. |
| Ranks/gates | `Role`, `PromotionGate`, and `StudentRole`; `backend/app/services/progression_service.py` checks quizzes, verified tickets, mastery, practical checkpoints, lessons, CLI labs, and flags. | Create an explicit compatibility adapter before Service Desk outcomes affect ticket-count gates or mastery. Avoid double credit. |
| Assignments | `QuizAssignment`, weekly activities, and `VmAssignment` are purpose-specific; no generic student assignment exists. | Add a dedicated Service Desk assignment model rather than stretching `QuizAssignment`. |
| Admin review | `frontend/src/pages/admin/AdminTicketReviewPage.jsx` plus `backend/app/routers/admin_tickets.py` supports review, revision, proof verification, override, flags, and XP. | Reuse review interaction patterns and audit every override; the new event replay needs a new detail view. |
| Incidents | `RootCause`, `Incident`, `IncidentTicket`, `IncidentParticipant`, and `RCASubmission` exist in `backend/app/models/incident.py`; admin-only CRUD/summary exists in `admin_content.py`. | Retain for legacy incident exercises. It lacks scenario state/version/events and is not the engine foundation. |

### 2.5 Integrations and operations

- **Confirmed from code:** `backend/app/services/ai_service.py` supports an OpenAI-compatible endpoint, budget checks, rate limits, structured JSON extraction, and `AIUsageLog`; `backend/app/models/ai_usage_log.py` records feature/model/tokens/cost/metadata. `frontend/src/pages/admin/AICostDashboard.jsx` and `/api/admin/ai-usage` report cost.
- **Confirmed from code:** `backend/app/services/ticket_grader.py` grounds a rubric and labels student text untrusted. However, `tickets.py:submit_ticket` invokes grading before committing the submission and converts grader failure into an HTTP 500, while `docs/MENTOR_GUIDE.md` says submissions remain available for manual grading. This is a current behavior/documentation discrepancy; it is not changed in this planning task.
- **Confirmed from code:** `backend/app/services/discord_service.py` sends XP milestone webhooks only. There is no general notification inbox/model.
- **Confirmed from code:** `backend/app/services/proxmox_service.py` allocates VMIDs, selects linked/full clones by storage capability, starts/destroys VMs, and finds guest IPs. `backend/app/services/guacamole_service.py` creates one RDP connection and a short-lived user with READ permission to that one connection.
- **Confirmed from code:** `VmAssignment` in `backend/app/models/vm_assignment.py` is uniquely tied to one `LabRun`; `backend/tests/test_labs.py`, `test_proxmox_service.py`, and `test_guacamole_service.py` cover lifecycle, isolation, clone selection, expiration, cleanup, and scoped Guacamole access.
- **Confirmed from documentation:** `README.md`, `docs/DEPLOYMENT.md`, `docs/MENTOR_GUIDE.md`, and `docs/AUTHORING_CONFIG_SECURITY.md` say automated Proxmox/Guacamole remains opt-in pending real staging acceptance; manual VM delivery is the safe fallback.
- **Strong recommendation:** extend `AIUsageLog` later with attempt/scenario/rubric/model identifiers. Reuse the Proxmox/Guacamole client functions behind a new broker, after staging validation. Do not reuse `VmAssignment` for Service Desk.

### 2.6 Migrations, seeds, and tests

- **Confirmed from code:** Alembic history is additive from `backend/alembic/versions/0001_...` through `0033_finalize_training_quiz_mappings.py`. My Training is created in `0032_my_training.py`; mapping finalization is `0033_...`. Historical migrations must remain unchanged.
- **Confirmed from code:** `backend/seed.py`, phase seed modules, `seed_curriculum.py`, and CLI lab JSON seed current content. Application lifespan only refreshes CLI labs and weekly domain leads.
- **Strong recommendation:** scenario definitions should not be silently published by application startup. Publication is an explicit validated operation with a checksum and immutable version.
- **Confirmed from code:** the backend suite covers authentication, security, tickets, hints/parameters, quizzes, progression gates, labs, Guacamole, Proxmox, capstones, My Training, and content validation. `frontend/tests/e2e/my-training.spec.js` and `frontend/playwright.config.js` provide Chromium browser coverage for student/admin navigation, direct routes, mobile width, quiz mappings, progression persistence, permissions, console/network failures, and disposable-record cleanup. No separate frontend component/unit suite was found.

## 3. Existing Support Tickets audit

### 3.1 Current student workflow

**Confirmed from code:** `frontend/src/pages/TicketsPage.jsx` lists tickets with week, status, and difficulty filters. `TicketPage.jsx` presents the prompt, checkpoints, and hints. `frontend/src/components/TicketSubmit.jsx` collects symptom, root cause, resolution, verification, commands, evidence, collaborators, and client-reported duration, with a local draft. `TicketFeedback.jsx` shows the result.

There is no explicit student ticket-assignment or claim record: eligible tickets are listed from current content/week state, and one current submission supplies the per-student status. `Ticket` itself is the reusable content/template record. Category is a string, difficulty is constrained to 1–5, and week access is enforced by `require_week_reached`. The admin workflow can create/publish ticket content and review submissions, but it is not a scenario versioning or queue administration system.

Student APIs in `backend/app/routers/tickets.py` are:

- `GET /api/tickets`: own (or mentor-selected) list with one current submission status per ticket.
- `GET /api/tickets/{ticket_id}`: deterministic per-student parameters and public ticket fields; hidden root cause/model answer/scoring anchors are withheld.
- `POST /api/tickets/{ticket_id}/hint`: creates or updates an in-progress submission, persists hint count, and reduces potential XP.
- `POST /api/tickets/{ticket_id}/submit`: validates ownership, collaborators, evidence, and week access; grades; writes the submission; and sets it pending.
- `POST /api/tickets/uploads`: legacy ticket evidence upload.

**Confirmed from code:** `backend/app/services/ticket_params.py` selects deterministic per-student parameter values. It personalizes facts but does not create an isolated mutable system state.

### 3.2 Data and workflow limitations

| Concern | Evidence | Consequence |
|---|---|---|
| Content model | `Ticket` stores prompt, week/category/difficulty, lesson/objectives, hidden answer, checkpoints, evidence, rubric, hints, and parameters. | Useful authored content and taxonomy can be imported, but it lacks explicit requester/device/account/environment state and tools. |
| Submission model | `TicketSubmission` stores one evolving write-up, scores, hints, evidence, XP, review, and override fields. | It is a graded document, not an immutable multi-attempt simulation. Application logic updates the same row for a retake until pass. |
| Status | In practice: not started → in progress (hint) → pending after submit → in review/passed or needs revision through admin review. | Reuse status vocabulary selectively, but define an explicit attempt state machine. |
| Grading | `ticket_grader.py` grades five anchors; admin can override, verify proof, request revision, flag, and resolve through `admin_tickets.py`. | Reuse rubric ideas and review workflow, not AI-only technical grading. Technical outcomes need deterministic state evidence. |
| Completion | My Training treats a graded pending/in-review/passed ticket as complete; progression ticket gates rely on passed/verified tickets. | Migration must preserve both interpretations and prevent double credit. |
| History | Ticket links, submissions, mentor comments, overrides, evidence, XP, and gate counts are production dependencies. | Never delete/rewrite. Keep legacy detail/history accessible after any label change. |
| Queue/tools/events | No claim/assignment queue, SLA/priority, tool state, action event log, replay, scenario version, or mode. | Requires a new engine, not columns added indefinitely to `tickets`. |

### 3.3 Current feature disposition

| Existing feature | Keep | Extend | Merge | Replace later | Remove later | Evidence |
|---|---:|---:|---:|---:|---:|---|
| Ticket content and current routes | ✓ |  |  |  |  | `Ticket`; `/api/tickets`; `/tickets`; production links and curriculum references. |
| Ticket submissions/history | ✓ |  |  |  |  | `TicketSubmission`, evidence, XP, mentor review, overrides. |
| Five-anchor rubric concepts | ✓ | ✓ |  |  |  | `ticket_grader.py`; Student and Mentor Guides. Add identity, process, escalation, and outcome dimensions. |
| Student ticket list/detail UI | ✓ |  |  | ✓ |  | Preserve for history/current curriculum; new workspace replaces only migrated scenario entry. |
| Admin ticket review patterns | ✓ | ✓ | ✓ |  |  | `AdminTicketReviewPage.jsx`, `admin_tickets.py`; reuse interaction conventions in attempt review. |
| Ticket AI technical grading | ✓ |  |  | ✓ |  | Existing tickets keep it; deterministic engine becomes authoritative for Service Desk technical score. |
| Hint/XP ladder | ✓ | ✓ | ✓ |  |  | `tickets.py:hint_multiplier`; model hint reveals as events and scenario-version policy. |
| Deterministic parameter substitution | ✓ | ✓ | ✓ |  |  | `ticket_params.py`; reuse the concept with facts frozen in an attempt snapshot. |
| One-row evolving submission attempt | ✓ |  |  | ✓ |  | Keep legacy history; new attempts are immutable/version-pinned records. |
| Static upload delivery | ✓ |  |  | ✓ |  | Existing artifact routes; new sensitive artifacts need authorized access. |
| Support Tickets navigation label | ✓ |  | ✓ |  | ✓ | `frontend/src/App.jsx`; rename only after migration gates in Section 22 are met. |
| Incident/RCA exercises | ✓ |  |  | ✓ |  | Separate admin content models have no student scenario runtime; retain and consider a later adapter. |
| Ticket-specific and generic upload paths | ✓ |  | ✓ | ✓ |  | `tickets.py`, `evidence.py`, and `labs.py` overlap; use one secured Service Desk artifact contract without changing legacy endpoints. |

### 3.4 Recommendation

**Strong recommendation:** choose a combination of options 2, 3, and 4: Support Tickets is a legacy system migrated gradually; its content/review/progression concepts are reusable; and Service Desk receives a new frontend plus a new backend scenario service. Do not make `Ticket`/`TicketSubmission` the direct data foundation. Use a crosswalk such as `LegacyTicketScenarioLink(ticket_id, scenario_id, migration_status)` or validated import metadata, preserve legacy records indefinitely, and credit either the legacy submission or the Service Desk attempt—not both—for the same curriculum requirement.

## 4. Reuse map

### Reuse decisions

| Existing component or service | Location | Reuse decision | Required changes | Risk |
|---|---|---|---|---|
| Student authentication | `services/auth_service.py` | Reuse unchanged | Apply ownership-filtered queries; never accept student identity as authority from payload. | Low |
| Admin authentication | `services/admin_auth.py` | Reuse for current single-node deployment | Add Service Desk permissions at endpoint/service boundaries; plan shared session storage before multi-worker scale. | Medium |
| Mentor identity | `Student.is_mentor` | Extend | Add scoped capabilities and assigned-student relation/policy. | High |
| Student/profile records | `models/student.py` | Reuse unchanged | Reference by FK; avoid copying profile PII into scenario definitions. | Low |
| Roles/ranks | `models/progression.py`, `progression_service.py` | Reuse and extend by adapter | Add Service Desk gate checks only after credit semantics are approved. | Medium |
| My Training | `models/training.py`, `training_service.py` | Extend | Add `service_desk_scenario`, validator, destination, completion lookup, and dedup rules. | Medium |
| Weekly next activity | `training_service.py` | Reuse canonical calculation | Resolve assigned/published scenario and safe route. | Medium |
| Quiz scoring | `models/quiz.py`, `routers/quizzes.py` | Reuse unchanged | Reference attempts for prerequisites/remediation. | Low |
| Ticket content | `models/ticket.py` | Wrap/migrate gradually | Import selected facts/rubrics into reviewed scenario drafts with crosswalk. | Medium |
| Ticket submissions/reviews | `TicketSubmission`, `admin_tickets.py` | Retain legacy; reuse patterns | Read-only history adapter; explicit one-source progression credit. | High |
| Guided labs | `models/lab.py`, `routers/labs.py` | Reuse links/patterns | Do not reuse weak completion as Service Desk state proof. | Medium |
| Networking/terminal | `models/cli_lab.py`, CLI frontend | Reuse UX/parser concepts | Server executes/validates simulated commands; no client-authored completion. | High |
| Capstones | `models/capstone.py`, `routers/capstones.py` | Reuse gating/history | Later Service Desk shift can contribute through explicit gate config. | Medium |
| Proxmox client | `services/proxmox_service.py` | Wrap in new broker later | Durable jobs, leases, quotas, networks, reconciliation, secrets, validation. | Very high |
| Guacamole client | `services/guacamole_service.py` | Wrap in new broker later | Short-lived brokered sessions, vault, exact CSP origin, cleanup/revocation. | Very high |
| AI service/cost logs | `services/ai_service.py`, `AIUsageLog` | Extend later | Attach scenario/attempt/rubric/model/prompt version; privacy and fallback. | High |
| Admin AI reports | `/api/admin/ai-usage`, `AICostDashboard.jsx` | Extend later | Filter Service Desk roleplay/evaluation usage and budgets. | Medium |
| Evidence/upload validation | `EvidenceArtifact`, evidence validator | Reuse storage/validation, extend relation | Explicit attempt-artifact relation, private retrieval, malware/retention policy. | High |
| Discord milestone webhook | `discord_service.py` | Reuse only for non-sensitive milestones | Never send ticket facts, transcripts, or identity data. | Medium |
| App settings | `models/app_setting.py:AppSetting` | Reuse for server flag | Typed accessor for `service_desk_enabled` and cohort allowlist; audit changes. | Medium |
| Audit/activity feed | `SquadActivity` and app logs | Do not reuse as attempt log | Create append-only event model with typed payloads. | High |
| Incident/RCA tables | `models/incident.py` | Retain legacy; optional later adapter | Do not use as scenario engine. | Medium |

## 5. Student information architecture

**Strong recommendation:** keep Nexus global navigation unchanged—Home, My Training, Practice Library, Progress. Add one Practice Library destination, **Service Desk Lab**, which opens a dedicated, route-lazy workspace. Internal navigation is Overview, Work Queue, Training Paths, Performance, Knowledge Base, and Exit to Nexus. Contextual tools appear only inside an attempt.

| Workspace page | Purpose and information | Main actions | Empty/loading/error | Mobile | Permission/API | Reuse and MVP |
|---|---|---|---|---|---|---|
| Overview | Current attempt, assignments, recommended next scenario, path status, recent result, score dimensions, skill gaps. | Continue, start recommended, review result. | Friendly “No assignments yet”; skeleton cards; retryable error with correlation ID. | Single column; sticky Continue action; no dense charts. | Own data only; `GET /api/service-desk/overview`. | Reuse My Training hero/status cards; **MVP**. |
| Work Queue | Published/assigned/available tickets with priority, impact, urgency, status, category, difficulty, and mode. Hidden facts excluded. | Filter, inspect, start/claim, continue, review. | Explain whether prerequisites, assignments, or feature flag cause an empty queue. | Cards instead of wide table; filter sheet; 44px targets. | Own eligibility; `GET /queue`, `POST /attempts`. | Reuse ticket filters/status chips; **MVP**. |
| Training Paths | Curated scenario sequences with prerequisites, estimated effort, completion, and related My Training content. | Open path, start next, review completed. | “Paths are being prepared”; preserve direct assignments. | Vertical roadmap, collapsible completed items. | Public published path structure + own progress. | Reuse weekly roadmap; read-only **MVP if content exists**, authoring later. |
| Performance | Technical accuracy, process, communication, documentation, identity verification, escalation, time, hints, skills, and attempts. | Review attempt/replay/feedback, open remediation. | Explain scores appear after first completed attempt. | Summary cards then accessible tables; no hover-only detail. | Own attempts only; mentor/admin variants separate. | Reuse Progress measures/status labels; summary **MVP**, trends later. |
| Knowledge Base | Search scenario-safe articles by symptom, task, category, and skill without exposing roots/expected actions. | Search, filter, open article, return to ticket. Article openings become events during attempts. | Suggested beginner articles; skeleton; recoverable search error. | Full-page outside an attempt; bottom sheet/full screen inside. | Authenticated students; only published student articles. | New content model/search; minimal **MVP**. |
| Exit to Nexus | Explicit return to Practice Library or prior Nexus route without ending the attempt. | Exit, optionally keep attempt running. | Not applicable. | Always reachable in workspace menu/header. | Authenticated. | React Router navigation; **MVP**. |

### Navigation and route contract

| Current route | Current purpose | Proposed destination | Compatibility plan |
|---|---|---|---|
| `/` | Student Home | Unchanged; may show assigned Service Desk recommendation from canonical training/overview data. | No redirect. |
| `/training`, `/training/week/:weekId` | Weekly plan and week | Unchanged; future scenario activity links to a pinned/eligible Service Desk entry. | Existing bookmarks unchanged. |
| `/tickets` | Support Ticket list | Legacy Support Tickets until migration gates pass. | Keep route and history permanently; later new starts may redirect through crosswalk. |
| `/tickets/:ticketId` | Legacy ticket work | Legacy ticket detail | Keep while active references exist; after migration show history or explicit migrated-scenario action. |
| `/tickets/:submissionId/feedback` | Legacy feedback | Legacy feedback | Retain, no destructive redirect. |
| `/service-desk` | Not present | Lazy Service Desk Overview | New MVP route behind flag. |
| `/service-desk/queue` | Not present | Work Queue | New MVP route. |
| `/service-desk/paths` | Not present | Training Paths | MVP read-only or Phase 2 depending authored content. |
| `/service-desk/performance` | Not present | Own Performance | New MVP summary route. |
| `/service-desk/knowledge` | Not present | Knowledge Base | New MVP route. |
| `/service-desk/attempts/:attemptId` | Not present | Ticket workspace | New MVP route with server ownership check and safe projection. |
| `/service-desk/attempts/:attemptId/review` | Not present | Result, event replay, feedback | New MVP route. |
| `/admin/ticket-review` | Legacy ticket review | Unchanged | Keep legacy reviews/history. |
| `/admin/service-desk` | Not present | Admin Service Desk Dashboard | New under Assessments & Labs; not global top level. |
| `/admin/service-desk/scenarios/:id` | Not present | Scenario/version detail | Read-only/validate in foundation, editing later. |
| `/admin/service-desk/attempts/:id` | Not present | Attempt review/replay | MVP. |

## 6. Ticket workspace design

### Desktop (approximately 1440px)

Use a resilient three-region layout rather than global tool tabs:

1. **Ticket/context rail (300–340px):** number, title, status, priority inputs, requester, department/location, device/asset, verification status, description, conversation history, prerequisites, and mode.
2. **Main tool canvas (flexible, minimum 560px):** the currently selected contextual tool, its state, validation feedback, and an accessible local tab strip for only the tools allowed by this scenario.
3. **Action rail (320–360px):** activity timeline, hints, escalation, resolution notes, closure checklist, and submit/close. It may collapse to a drawer on smaller laptops.

The header always shows the scenario/mode, elapsed or SLA time where configured, connection state, and **Exit to Nexus**. A stale-state banner must stop writes until the server projection refreshes.

### Mobile (approximately 375px)

Use one region at a time: **Ticket**, **Tool**, and **Notes** as a local segmented control, not global navigation. Preserve state when switching. Put Continue/Save/Resolve in a sticky bottom action area that does not cover inputs. Conversation and event history are collapsible. Tables become labeled cards. Real remote-desktop work is not an MVP mobile requirement; when later available, explain that a keyboard/desktop is recommended rather than presenting an unusable canvas.

### Contextual surface rules

| Surface | Use |
|---|---|
| Main-canvas local tab | Directory, Account, MFA, BitLocker, Assets, Printer, Email, Terminal—only when permitted by the pinned scenario. Lazy-load on first open. |
| Drawer/split panel | Knowledge article, action timeline, requester conversation, non-destructive reference details. |
| Modal | Destructive or high-risk confirmation such as password reset, account disable, device restart, or final closure; focus-trapped and keyboard operable. |
| Action rail | Resolution notes, escalation, verification checklist, submit/close, rubric-visible student expectations. |
| Full workspace route | Attempt review/replay and, later, Guacamole. Avoid embedding a complex VM beneath multiple nested panels. |
| Guacamole session | Phase 4 full canvas/new workspace route with a persistent Nexus session banner and explicit disconnect/return. |

Loading states preserve layout, tool failures do not erase ticket notes, and all actions announce results through accessible live regions. Buttons use explicit verbs, visible focus, sufficient contrast, and disabled reasons.

## 7. Learning Mode

**Strong recommendation:** Learning Mode is a policy attached to a scenario version, not a second scenario implementation. It is untimed by default, allows retry/reset lineage, displays learning objectives and recommended tools, provides progressive hints, explains rejected actions without revealing the complete solution, and generates an after-action explanation. It can link directly to existing My Training lessons/quizzes before or after the attempt.

Learning Mode may:

- highlight the next process category (“Verify identity before changing access”), but not silently perform the action;
- reveal scenario-authored hints in sequence and log each reveal;
- allow recoverable mistakes and show why the state did not change;
- offer a clean retry as a new child attempt, preserving the original event history;
- score the same dimensions as Simulation Mode while labeling the result “practice” and applying a different timing/hint policy;
- recommend remediation using explicit skill-to-content mappings, never title similarity alone.

## 8. Simulation Mode

Simulation Mode uses the same scenario version, state machine, tools, events, skills, and grade schema, with a stricter policy: limited or no tool recommendations, timed SLA where meaningful, reduced hints, incomplete requester information, recoverable ambiguity, multiple contributing causes, and stronger documentation/escalation requirements. A later shift may group several scenario attempts under one `ShiftRun`, but that is not an MVP entity.

Technical outcome is deterministic. Communication, documentation, identity verification, escalation judgment, hint usage, and resolution time are separate dimensions. Closing an unresolved ticket must not produce a technical pass merely because the final note sounds plausible.

## 9. Scenario engine

### 9.1 Runtime contract

**Strong recommendation:** implement a deterministic state-transition service:

`(immutable scenario version, attempt state, validated command, actor, policy) → (new state, append-only events, safe projection, grading evidence)`

The service owns all transitions inside one database transaction. The client sends an allowlisted command and an idempotency key, never a completion flag or authoritative resulting state. The attempt has an optimistic `state_version`; a stale command receives `409 STATE_CONFLICT` with a fresh safe projection.

A scenario definition contains:

- stable scenario UUID/slug and immutable integer version;
- title, category, difficulty, supported modes, objectives, skill tags, prerequisites, required rank, estimated time;
- ticket/requester/account/device/environment facts split into **student-visible** and **hidden** data;
- initial state, root cause, tool allowlist, required/alternate/recoverable/critical actions;
- success/failure/escalation conditions, hint sequence, explanation, scoring rubric, reset policy;
- browser/VM/AI requirements and instructor notes.

### 9.2 Authoring option comparison

| Option | Strength | Weakness | Decision |
|---|---|---|---|
| Database-only | Easy admin edits | Hard to review/diff/test; draft mistakes can reach runtime | Reject as sole source. |
| JSON | Machine-friendly | Comments/author readability weaker | Accept as canonical serialized form. |
| YAML | Author-friendly and reviewable | Parser/schema pitfalls require strict validation | Use as optional reviewed source format. |
| Typed Python/code | Strong types | Content changes require deploy and invite unsafe executable logic | Use for engine/action definitions, not scenario facts. |
| Full admin builder | Accessible to instructors | Large, risky product; validation/version UX is substantial | Later phase. |
| Hybrid config + DB publication | Reviewable source, strict schema, immutable runtime snapshot | Requires publish pipeline and provenance | **Recommended.** |

For MVP, reviewed YAML or JSON is validated by Pydantic, normalized to canonical JSON, hashed, and explicitly published into an immutable `ScenarioVersion`. Drafts may be cloned; published rows cannot be edited. The admin UI first lists, previews, validates, and publishes—not a free-form builder. Automated health tests execute at least one valid path for every publishable version.

## 10. Scenario versioning

Scenario identity and scenario version are separate. Lifecycle:

1. Create/clone a draft version.
2. Validate schema, references, hidden-data projection, prerequisite cycles, tool/action compatibility, and at least one success path.
3. Preview as a student in both supported modes.
4. Publish once, assigning version number, checksum, publisher, and timestamp.
5. Pin every assignment (optionally) and every attempt (always) to that version.
6. Disable/retire the version for new starts without deleting it or breaking results.
7. Any update clones a new draft and publishes a new version.

**Strong recommendation:** completed attempts retain the pinned version FK plus frozen per-attempt randomized facts and rubric version. Historical replay loads that immutable snapshot. A scenario can be marked broken for new starts while old attempts remain reviewable. Deleting published versions is prohibited at the application and FK level.

## 11. Universal action and event-log architecture

### 11.1 Event contract

Every meaningful attempt change produces an append-only server event. Examples include attempt/ticket start and claim, tool open, employee/account lookup, password reset, unlock, group/MFA/BitLocker/asset action, command, printer/email/service/device change, article/hint use, message/caller response, escalation, resolution, closure, grade, override, reset, VM allocation, and environment validation.

| Field | Contract |
|---|---|
| `id` | Server-generated UUID; not sequentially guessable. |
| `attempt_id` | FK to the owned attempt; every read is ownership/capability scoped. |
| `sequence_number` | Monotonic within attempt; unique `(attempt_id, sequence_number)` for deterministic replay. |
| `scenario_version_id` | Denormalized/pinned consistency check; must match attempt. |
| `actor_type` / `actor_id` | Student, mentor, administrator, system, environment, or AI; system actors have no fake student ID. |
| `occurred_at` / `received_at` | Server timestamps; client timestamp may be metadata only. |
| `tool_key` / `event_type` | Validated enums/registry keys, not arbitrary client strings. |
| `command_id` | Unique idempotency key per attempt/actor; repeated requests return the prior result. |
| `payload` | Schema-versioned, allowlisted, redacted structured facts needed for replay/evidence. |
| `previous_state_hash` / `resulting_state_hash` | Integrity and replay diagnostics; do not duplicate all sensitive state in every row. |
| `outcome` | accepted, rejected, failed, no-op, or system error, with a safe reason code. |
| `visibility` | Student-visible, instructor-only, security-only, or system-only. |
| `correlation_id` | Links API request, broker job, AI call, and operational logs. |

**Strong recommendation:** never store passwords, session tokens, API keys, BitLocker recovery values, raw hidden answers, or full sensitive WebSocket payloads in events. Use stable redacted references and one-way fingerprints where comparison is necessary. OWASP recommends object-level authorization even for unguessable identifiers ([IDOR prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)) and separating purpose-specific audit/transaction logs from general security logs ([Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)).

### 11.2 Uses

- **Grading:** deterministic rules query accepted/rejected actions and final state; AI never invents technical evidence.
- **Feedback:** link each rubric dimension to supporting events and recommended remediation.
- **Review/appeal:** replay ordered facts, show overrides as new events, and retain the original grade.
- **Debugging:** reproduce transition failures from scenario version + initial snapshot + commands.
- **Analytics:** aggregate skill failure, hint, abandonment, time, alternate paths, and scenario health from privacy-safe projections.
- **Broken-scenario detection:** alert on impossible transitions, abnormal rejection clusters, and environment failures.
- **AI evaluation:** provide a bounded, redacted event projection, transcript, and pinned rubric.
- **Portfolio evidence:** publish only approved summaries; never raw employee/account facts or internal rubric.

### 11.3 Retention

**Strong recommendation:** retain canonical grade/action evidence with the academic record; retain verbose operational telemetry for a shorter configurable window; retain AI/audio transcripts only as long as approved for review and appeals, then delete or anonymize them. Legal/educational policy must set exact durations. Event deletion must not make a grade unverifiable; use a minimized canonical record after verbose data expires.

**Uncertain and requiring a decision:** approve concrete retention periods, transcript consent, student export/deletion handling, and whether tamper-evident hash chaining is required. A hash chain is defense-in-depth, not a substitute for DB permissions, backups, and an audit policy.

**Optional future enhancement:** after ordinary replay and audit controls are proven, add signed portfolio summaries or tamper-evident event-chain verification for selected capstone evidence. Do not expose the raw attempt log publicly.

## 12. Database proposal

**Strong recommendation:** do not extend `tickets`, `ticket_submissions`, `lab_runs`, or `vm_assignments` into a polymorphic Service Desk engine. The first implementation migration should be additive and create scenario identity/version, assignment, attempt, event, grade, and skill-link foundations. Knowledge and environment tables can follow when their features enter scope.

### Proposed data model

| Entity | Purpose | Existing reuse | MVP/later | Risk |
|---|---|---|---|---|
| `ServiceDeskScenario` | Stable identity: UUID, slug, title/category, lifecycle, current published version, created/updated actor/times. Unique slug; index status/category. | None; optional legacy ticket crosswalk. | MVP | Medium |
| `ServiceDeskScenarioVersion` | Immutable normalized definition, schema version, version number, checksum, status, source/provenance, publish metadata. Unique `(scenario_id, version_number)` and checksum policy. | JSON/JSONB conventions from current models. | MVP | High |
| `ServiceDeskScenarioSkill` | Version-to-skill mapping with weight/required flag. Unique version+skill. | Existing domains/objective IDs may seed taxonomy, not replace it. | MVP | Medium |
| `ServiceDeskSkill` | Stable skill taxonomy and optional My Training remediation references. | Module domain/objective concepts. | MVP minimal | Medium |
| `ServiceDeskAssignment` | Assign a published scenario/version or path to a student, mode, availability/due dates, required/optional, creator. Index student/status/due. | Student FK; no generic assignment fits. | MVP | Medium |
| `StudentScenarioAttempt` | Student, pinned version/assignment, mode, status, state revision, safe runtime state, randomized facts, start/end/timing, reset lineage. Unique idempotent-start key; indexes student/status/version. | Student; status patterns only. | MVP | High |
| `ServiceDeskAttemptEvent` | Append-only command/outcome log with sequence, actor, typed/redacted payload, hashes, idempotency/correlation. Unique `(attempt_id, sequence)` and `(attempt_id, actor_key, command_id)`. | No current equivalent. | MVP | Very high |
| `ServiceDeskAttemptGrade` | Rubric version, dimension scores, total/outcome, evidence event IDs, deterministic/AI/human contributions, calculation metadata. Grade changes create revisions. | Ticket rubric/override concepts. | MVP | High |
| `ServiceDeskAttemptFeedback` | Mentor/admin feedback, visibility, author/time, linked grade/events, resolution. | Ticket admin comment/flags patterns. | MVP | Medium |
| `ServiceDeskLegacyTicketLink` | Crosswalk between legacy ticket and scenario/version; migration/credit state. Unique ticket and scenario policy. | `Ticket` FK. | MVP migration support | Medium |
| `ServiceDeskTrainingPath` / item | Ordered published scenarios, prerequisites, audience/rank, enabled state. | TrainingWeek ordering pattern. | Phase 2 (or seed-only MVP) | Medium |
| `ServiceDeskKnowledgeArticle` / revision | Published student-safe articles, search metadata, body revision, audience, skill tags, leakage review. | Resource records are links only, insufficient. | MVP minimal | High |
| `ServiceDeskAttemptArtifact` | Explicit attempt/event/artifact link and purpose/visibility. | `EvidenceArtifact` storage and validation. | MVP if uploads needed | High |
| `ServiceDeskAttemptStateCheckpoint` | Periodic replay snapshot for long attempts; event sequence and state hash. | Attempt state JSON can serve MVP. | Later | Medium |
| `ScenarioEmployee`, `Account`, `Device`, `TicketFact` tables | Reusable normalized fictional world entities. | Ticket parameters. | Later; keep facts inside immutable version/attempt snapshot in MVP. | High |
| `SimulatedMessage` | Queryable conversation items linked to attempts/events. | None. | Phase 2/3; events can serve MVP scripted messages. | Medium |
| `SimulatedCall` / `CallTranscript` | Call session, consent, transcript segments, provider/model, retention. | AI usage metadata. | Phase 3 | Very high |
| `LabEnvironmentTemplate` | Versioned environment topology/templates, validation/reset policy, quotas. | `LabTemplate.proxmox_template_vmid` informs design. | Phase 4 | Very high |
| `LabSession` / operation | Lease, resources, job status, Guacamole connection refs, expiry, cleanup/reconciliation. | Low-level clients; not `VmAssignment`. | Phase 4 | Very high |

### Entity lifecycle and integrity contracts

| Entity | Important fields and relationships | Indexes/uniqueness | Versioning and retention |
|---|---|---|---|
| `ServiceDeskScenario` | UUID, slug, display metadata, lifecycle, current published-version FK, authorship timestamps; has many versions and legacy links. | Unique slug/UUID; status/category indexes. | Identity survives all versions; archive rather than delete once referenced. |
| `ServiceDeskScenarioVersion` | Scenario FK, integer version, schema version, normalized definition JSON, checksum, mode/requirement summary, status, publisher/time. | Unique scenario+version; checksum and status indexes. | Draft may be replaced only before publication under optimistic revision; published immutable and retained while any attempt/grade exists. |
| `ScenarioTicket` | **Not a separate MVP table.** Ticket/requester facts live in pinned definition/snapshot. Normalize later only for a persistent shared simulated world. | If later added: unique version+ticket key. | Pinned with scenario version; never reference mutable legacy `Ticket` facts at runtime. |
| `ScenarioEmployee` | **Not a separate MVP table.** Fictional employee facts are definition/snapshot data; must not point at real `Student` records. | If later added: unique fictional directory ID within world/version. | Versioned/pinned; minimize and retire with academic retention. |
| `ScenarioAccount` | **Not a separate MVP table.** Simulated account state belongs to attempt state and version facts. | If later added: unique world+account key. | Attempt state is retained through canonical events/grade evidence; secrets are never retained. |
| `ScenarioDevice` | **Not a separate MVP table.** Simulated device/asset facts live in version/snapshot for MVP. | If later added: unique fictional asset tag within world/version. | Pinned; no real device identifier unless an approved hybrid environment mapping is separately protected. |
| `ScenarioTool` | Tool registry is typed code plus a definition allowlist; scenario version stores allowed tool keys/config, not arbitrary executable code. | Unique tool key+handler version in registry validation. | Handler changes require backward-compatibility tests or a new handler version retained for old replay. |
| `ServiceDeskTrainingPath` | Stable path identity, title/description/rank/status; has ordered path-item rows pointing to published scenario policies. | Unique slug; unique path+display order; status/rank indexes. | Published path revisions should be copied/versioned before assignments depend on them; retain assigned revision. |
| `ServiceDeskAssignment` | Student FK (future cohort FK), scenario/version or path revision, mode, required flag, availability/due, status, creator. | Student/status/due indexes; uniqueness/idempotency key prevents duplicate active assignment. | Preserve completed/revoked assignments; revocation blocks new start but not history. |
| `StudentScenarioAttempt` | UUID, student/assignment/pinned-version FKs, mode/status, state JSON, state revision, facts snapshot, timing, reset-parent FK, start idempotency. | Student/status/version/start indexes; one active policy enforced transactionally/partial unique where supported. | Never repoint to a newer scenario version; retain canonical academic attempt and retry lineage. |
| `AttemptEvent` | Attempt/version FKs, sequence, actor, server times, tool/type, command/correlation IDs, redacted payload, state hashes, outcome/visibility. | Unique attempt+sequence and attempt+actor+command; time/type indexes for review/health. | Append-only; canonical evidence retained with attempt, verbose payload minimized by approved retention policy. |
| `AttemptState` | Use `StudentScenarioAttempt.state_json` and revision in MVP; later checkpoint has attempt+sequence+state hash/snapshot. | Unique attempt+checkpoint sequence. | Projection is rebuildable from retained canonical events; checkpoints may expire after integrity verification. |
| `AttemptGrade` | Attempt FK, revision, rubric ID/version, dimension JSON, total/outcome, evidence event refs, source mix, calculator/model metadata, actor/time. | Unique attempt+revision; attempt/outcome indexes. | Append revisions; original grade never overwritten; retain with academic record. |
| `AttemptFeedback` | Attempt/grade/event refs, author principal, visibility, body, created/resolved times. | Attempt/time and author indexes. | Append/edit policy must preserve revision/audit; retain with attempt unless policy removes private drafts. |
| `ScenarioHint` | Keep ordered hints inside immutable version in MVP; hint reveals are events. Normalize only if cross-version authored hint analytics require it. | Definition validation enforces unique order/key. | Text changes require a new scenario version. |
| `ScenarioSkill` | Stable skill code/name/taxonomy plus version join weight/required and explicit remediation content refs. | Unique skill code; unique version+skill. | Taxonomy labels may evolve, but historical version joins/grade evidence retain original code/version. |
| `KnowledgeArticle` | Stable article identity plus revision rows: title/body/search terms/audience/skills/status/reviewer/leakage check. Attempt events reference revision. | Unique slug+revision; published/status/search indexes. | Published revision immutable; old opened revisions retained for replay, while student search shows current allowed revision. |
| `SimulatedMessage` | Later normalized attempt conversation: sender role, channel, body/content type, event FK, server time, visibility. | Attempt/time/channel indexes; unique generating event. | MVP may render scripted messages from events; normalized messages follow transcript privacy retention. |
| `SimulatedCall` / `CallTranscript` | Call attempt/session, consent, provider/model, start/end/status; segments with speaker/time/redacted text and storage policy. | Attempt/status/time; segment call+sequence unique. | Phase 3 only; immutable evaluation source, with approved redaction/deletion and a minimized grade record. |
| `LabEnvironmentTemplate` | Stable identity + immutable topology version, Proxmox templates, network, readiness/validation/reset policy, resource estimate. | Unique slug+version/checksum; status/capability indexes. | Published template version pinned to session; retain metadata after underlying image retirement. |
| `LabSession` | Attempt/template-version FKs, lease/status, resource IDs, broker operation, scoped Guacamole refs, heartbeat/expiry/cleanup, validation result. | Attempt/status/expiry/resource unique indexes. | Operational secrets are not retained; lifecycle/audit metadata retained with attempt, verbose broker logs shorter. |

### First migration contract

The first implementation migration should create only:

1. `service_desk_scenarios`
2. `service_desk_scenario_versions`
3. `service_desk_skills` and version-skill join
4. `service_desk_assignments`
5. `service_desk_attempts`
6. `service_desk_attempt_events`
7. `service_desk_attempt_grades`
8. `service_desk_attempt_feedback`

It should add no destructive changes, seed no production scenario assignments, and downgrade only these empty/new tables after a dependency check. Use foreign keys with restrictive deletion for published versions and attempts. Do not cascade-delete academic evidence. `AppSetting` can hold the disabled-by-default feature flag without a new table.

**Uncertain and requiring a decision:** whether SQLite remains the production engine through Phase 2. Benchmark event writes, replay, concurrent attempts, and report queries first; PostgreSQL is strongly preferred before multi-ticket shifts, high-volume transcripts, or VM job workers.

## 13. API proposal

All APIs follow Nexus's `/api` convention, `{success, data}` envelope, Pydantic validation, cookie/bearer authentication, same-origin CSRF protection, stable error codes, and no-store responses. Student endpoints derive identity from the authenticated principal. Public response models are explicit safe projections and must never serialize the raw scenario definition.

### Proposed APIs

| API group | Users | Purpose | MVP/later | Security notes |
|---|---|---|---|---|
| `/api/service-desk/overview`, `/queue`, `/scenarios/{slug}` | Student | Safe catalog, assignments, current work, prerequisites. | MVP | Own eligibility; no hidden facts/rubrics; rate-limit search/list abuse. |
| `POST /api/service-desk/attempts` | Student | Idempotently start a published eligible scenario and pin version/facts. | **First API / MVP** | Ignore payload student ID; assignment/rank/prerequisite check; idempotency key. |
| `GET /api/service-desk/attempts/{id}` | Student | Safe attempt projection, tools, conversation, next allowed UI state. | MVP | Ownership every request; `404` for foreign IDs. |
| `POST /api/service-desk/attempts/{id}/actions` | Student | Canonical typed command/state transition/event append. | MVP | Action schema per tool; expected state revision; idempotency; rate limits; server timestamp. |
| `POST .../{id}/resolve`, `/escalate`, `/hints` | Student | Semantic commands routed through the same engine. | MVP | Cannot bypass engine/grader; hint sequence server-owned. |
| `/api/service-desk/performance` | Student | Own attempt/skill/score summaries and remediation. | MVP summary | Distinct attempts; no peer data. |
| `/api/service-desk/knowledge` | Student | Search published safe articles; log use during attempt. | MVP | Sanitize content/search; scenario-specific access does not reveal answers. |
| `/api/mentor/service-desk/students/{id}/attempts` | Mentor | Assigned-student attempts, event replay, feedback. | MVP after scope model | Mentor capability + assigned relation; sensitive transcript policy. |
| `/api/mentor/service-desk/attempts/{id}/feedback` | Mentor | Add non-destructive feedback. | MVP | Append-only audit; no default override/publish. |
| `/api/admin/service-desk/scenarios` | Admin | List/create draft metadata, preview, validate, clone, publish, disable. | Foundation/MVP read-only+publish | Admin auth, audit every publication; optimistic draft revision. |
| `/api/admin/service-desk/assignments` | Admin | Assign published versions/modes/dates. | MVP | Validate rank/prerequisites; audit and idempotency. |
| `/api/admin/service-desk/attempts` and `/{id}` | Admin | Search/review/replay attempts and system evidence. | MVP | PII-aware filters; paginate; separate security-only payloads. |
| `POST .../{id}/grade-overrides`, `/reset` | Admin (mentor only if granted) | Revisioned override/reset with reason. | MVP | Never mutate original grade/events; step-up or reauth desirable for high-risk action. |
| `/api/admin/service-desk/reports` | Admin | Aggregated scenario/skill/failure trends. | Phase 2 | Minimum group-size/privacy rules; no raw secret payloads. |
| `/api/internal/service-desk/grade` | Internal worker/service | Deterministic grade/regrade from pinned data. | MVP in-process initially | Not browser reachable; service identity if split later. |
| `/api/internal/service-desk/environments/...` | Broker/validator | Allocate, heartbeat, validate, reset, destroy. | Phase 4 | mTLS/service auth, signed jobs, network allowlist, idempotency. |
| `/api/internal/service-desk/ai/...` | AI worker | Roleplay/evaluation jobs. | Phase 3 | Redacted bounded context, prompt/rubric/model version, budget and audit. |

### Request, response, and failure rules

- `POST /attempts`: `{scenario_id, mode, assignment_id?, idempotency_key}` → `201` safe attempt projection; `409 ACTIVE_ATTEMPT_EXISTS` may return the existing attempt.
- `POST /actions`: `{command_id, expected_state_version, tool, action, parameters}` → accepted/rejected event summary and fresh safe projection. Parameters use a discriminated union per action.
- Validation failures use `400`; unauthenticated `401`; unauthorized object access returns non-enumerating `404`; locked prerequisite `403` with a safe reason; stale state/idempotency conflict `409`; rate limit `429`; unavailable environment `503` with retry metadata.
- Reads paginate and filter explicitly. Writes have bounded payloads and per-student/per-attempt limits. Searches have normalized length/result caps.
- Audit publication, assignment, reset, grade override, environment, transcript export, and settings changes.
- Hidden-data contract tests recursively reject keys such as root cause, expected actions, answer keys, rubric thresholds, instructor notes, secrets, and other students' identifiers.

## 14. Browser-tool framework

### Shared framework

**Strong recommendation:** create a registry-based tool framework instead of unrelated components. Each tool definition has a stable key/version, lazy frontend loader, public state schema, command discriminated union, backend handler, scenario capability requirements, authorization rule, event types, accessibility metadata, and health tests. The engine resolves available tools from the pinned scenario; the browser cannot enable one itself.

Every tool reads a server-safe projection and mutates state only through `/actions`. Confirmation is required for destructive changes. Tool actions are deterministic and support explicit failure codes such as identity-not-verified, stale-state, policy-denied, dependency-unavailable, invalid-input, rate-limited, and already-complete.

### Tool evaluation

| Tool | MVP capabilities and state/actions | Validation and common failures | Accessibility/mobile/reuse | Phase |
|---|---|---|---|---|
| Employee Directory | Search fictional employee; view approved department/location/contact/status/device refs. | Query bounds; ambiguous/no match; identity mismatch; never return hidden security answers. | Labeled results/cards; keyboard search; reuse student-search visual pattern only, not real student roster. | MVP |
| Identity & Access Console | Inspect account; reset password, unlock, expire sessions, view/change approved groups, reset MFA. | Identity verification, least privilege, policy/temporary-password rules, locked dependency, risky group confirmation. | Generic enterprise UI, not Microsoft clone; stacked mobile forms; focus to result. | MVP (groups limited) |
| BitLocker Recovery | Search asset; verify requester/device; reveal/use simulated recovery key. | Key is masked and never event-logged; denied without identity/device match; track disclosure. | Copy control with accessible confirmation; full-screen mobile; original generic UI. | MVP |
| Knowledge Base | Search/open published article, related skills, return to attempt. | Leakage review, article version, no hidden scenario mapping; log usage. | Drawer/route; headings/landmarks; reuse Resource styling. | MVP |
| Ticket conversation/notes | Scripted requester messages; student replies; internal/resolution notes; escalate/close. | Required fields, channel/visibility, PII warnings, closure checks. | Persistent drafts, labeled channels, mobile composer. | MVP |
| Asset Registry | Device/owner/status/warranty/location; assign/return device. | Asset availability/ownership; duplicate assignment; onboarding/offboarding policy. | Card/table alternatives; generic inventory UI. | Phase 2 (minimal read-only may support onboarding MVP) |
| Printer Settings | Queue/device/status/default/driver; clear/restart/configure. | Wrong printer, permissions, offline/dependency, unsafe broad change. | Form controls, status text not color-only. | Phase 2 |
| Email Client | Account/connectivity/sync state; repair profile/settings, send test. | Wrong recipient, unsafe credential handling, service outage. | Generic mail UI; no Outlook branding/layout copy. | Phase 2 |
| Teams-style Chat | Scripted or later AI text conversation. | Disclosure/identity/abuse rules; message bounds. | Generic chat; screen-reader message announcements; no vendor clone. | Phase 2/3 |
| Terminal | Curated commands against simulated state; output, history, errors. | Allowlisted parser; no shell execution in API process; redact secrets; command limits. | Reuse current terminal UX concepts; accessible transcript; mobile command chips. | Phase 2 |
| VPN Settings | Profile, auth, network, routes, DNS; reconnect/repair. | Prerequisite network, credentials, route conflict. | Generic settings; compact mobile sections. | Phase 2 |
| Windows Update | Scan/status/pending reboot/service state; retry/restart service. | Dependency, disk, policy, reboot side effects. | Generic OS updater, not exact Windows UI. | Phase 2 |
| Driver Status | Device/driver/version/error; rollback/update/enable. | Compatibility, restart, wrong device. | Semantic device tree alternative to tiny icons. | Phase 2 |
| Basic Remote Desktop | Open later real/simulated device session. | Session allocation, expiry, disconnect, network and credential failures. | Desktop recommended; Guacamole supports touch/text input but do not promise advanced mobile usability ([Guacamole UI manual](https://guacamole.apache.org/doc/gug/using-guacamole.html)). | Phase 4 |
| Software Installation | Catalog/status/policy; install/uninstall/repair. | License/approval/dependency/disk/restart. | Progress announcements and cancel rules. | Phase 2/4 |
| Deployment/task sequence | Deployment progress/logs/retry. | Step failure, network, image, policy. | Readable step list; mobile monitoring only. | Phase 4 |

## 15. Browser, hybrid, and VM classification

| Class | Use when | Initial examples | Acceptance boundary |
|---|---|---|---|
| Browser-only | The learning value is process, policy, state reasoning, communication, and documentation; deterministic simulation is sufficient. | Password/unlock/MFA, BitLocker, asset checkout, ticket documentation, basic printer/email/VPN settings, command interpretation. | Default for MVP. Fast reset, accessible, repeatable, no external dependency. |
| Hybrid | Nexus owns ticket/state/grade, but one meaningful step needs a real isolated system. | Domain join, file-share repair, DNS record correction, service restart, Group Policy verification. | Only after broker health, automatic validation, isolation, and rollback are proven. |
| Full VM | Persistent multi-system state and authentic administrative tooling are central to the objective. | AD/DNS/DHCP, GPO, Windows Server roles, PowerShell across hosts, server recovery, deployment, patch failure. | Advanced Phase 4; never required for ordinary beginner tickets. |

## 16. Proxmox and Guacamole architecture

### Current reuse boundary

**Confirmed from code:** the low-level Proxmox and Guacamole clients already implement important pieces: token-based API access, clone selection, VM start/destroy/IP discovery, one-connection Guacamole users, and cleanup. The test suite mocks these contracts. **Confirmed from documentation:** real staging isolation and lifecycle have not been accepted.

**Strong recommendation:** retain those client modules behind interfaces, but create a new environment broker rather than extending `VmAssignment`. The broker owns templates, leases, operations, quotas, retries, reconciliation, validation, and cleanup. FastAPI request-process background tasks are not durable enough for long clone/reset workflows.

### Future advanced flow

1. Student starts an eligible advanced attempt.
2. Nexus atomically creates a `LabSession` lease and idempotent allocation job after quota checks.
3. A durable worker selects a compatible environment template/pool, reserves VMIDs/resources, and clones or leases a warm environment.
4. Network policy isolates the student environment from production, other students, Proxmox management, and unauthorized internet destinations.
5. Guest readiness/health checks complete before Guacamole is exposed.
6. The broker creates a one-session Guacamole connection and time-limited principal; Nexus returns a scoped launch reference, not admin credentials.
7. Student work produces Nexus events; an environment validator reads system state through a least-privilege channel and submits signed facts.
8. The engine grades from validated facts plus Nexus events.
9. On close, expiry, admin reset, or failure, the broker revokes Guacamole, captures allowed diagnostics, destroys/reverts resources, and releases quota.
10. Reconciliation finds orphaned leases/connections/VMs after crashes.

### Operational design

- Version environment templates and validation/reset contracts; attempts pin the template version.
- Prefer linked clones where supported and isolation/reset behavior is verified; use full clones when storage or security requires independence. Proxmox documents template-linked versus full clone behavior in [`qm`](https://pve.proxmox.com/pve-docs/qm.1.html) and its [VM Templates and Clones guide](https://pve.proxmox.com/wiki/VM_Templates_and_Clones).
- Use least-privilege Proxmox API tokens scoped to the pool/storage/node operations required by the broker; never a root user token. Keep tokens in the existing secret mechanism initially, then a dedicated vault before scale.
- Use per-student isolated networks/VLAN/SDN segments. Shared classroom domains are allowed only as explicitly designed tenants with per-student objects and tested cross-student boundaries.
- Store no temporary password/token in Nexus events or URLs under application logs. Guacamole supports vault-backed injection of connection secrets ([Guacamole vault documentation](https://guacamole.apache.org/doc/gug/vault.html)); evaluate it before Phase 4.
- Define idle timeout, hard maximum duration, one active environment per student by default, per-template quotas, retry ceilings, capacity reservation, and instructor emergency termination.
- Capacity planning uses peak concurrent sessions × template vCPU/RAM/disk plus clone IOPS and at least one failure/recovery reserve. Measure, do not invent fixed student ratios.
- Observe queue time, clone time, readiness, validation, active leases, failures, orphans, cleanup latency, and resource saturation.
- If Guacamole is framed from another origin, add only the exact approved origin to CSP after security review. Microphone remains disabled until an approved call feature requires it.

## 17. AI architecture

AI is not in the MVP. The existing OpenAI-compatible service and usage log can be extended without choosing a new provider in this plan.

### Roleplay AI (Phase 3)

Roleplay covers caller/requester/chat/interviewer/manager personas. It receives only the pinned persona facts, allowed knowledge, disclosure rules, current public state, conversation history within a bounded window, identity-verification policy, and emotional state. It must refuse to disclose hidden root causes, expected actions, credentials, rubric thresholds, or instructor notes. Student text and retrieved KB content are untrusted input, not instructions.

### Evaluation AI (Phase 3)

Evaluation may score communication, documentation, transcript behavior, de-escalation, and explanation quality. Input must include scenario/version/checksum, canonical visible and hidden facts as appropriate, deterministic event/state evidence, transcript, final notes, structured rubric and rubric version. It must not grade technical success from the final narrative alone. Deterministic technical grade remains authoritative; human review can override with an append-only reason.

### Controls

- Separate system instructions, scenario facts, student content, and retrieved content with explicit trust labels and schemas.
- Test prompt injection, answer extraction, persona escape, fabricated tool actions, identity-verification bypass, and hostile KB/upload content.
- Track provider/model/version, prompt template version, rubric version, retries, latency, tokens, cost, fallback, and reviewer outcome in `AIUsageLog` metadata or later typed columns.
- Apply per-student/per-attempt and global budgets, circuit breakers, bounded retries, deterministic scripted fallback, and manual review.
- Store transcripts separately with consent, encryption/access controls, redaction, retention, export/deletion policy, and transcript-view audit.
- Do not let an AI call mutate attempt state directly. It proposes a message/evaluation; a server policy validates and records it.

## 18. Admin workspace

Place **Service Desk Lab** under the existing **Assessments & Labs** admin group. The shell route is `/admin/service-desk`; do not create a new top-level admin navigation category.

| Area | Purpose/actions/data | Permissions/audit | Reuse | Phase |
|---|---|---|---|---|
| Dashboard | Health, active attempts, assignments, completion, broken versions, environment/AI status. | Admin; every operational action audited. | Admin cards, training validation patterns. | MVP summary |
| Scenarios | List draft/published/disabled versions; inspect IDs/checksum/tools/prereqs; clone, validate, preview, publish, disable, mark broken. | Author/publisher capabilities separated; publication audited. | Admin Training ordering/validation UX. | Foundation read-only+validate; editing later |
| Assignments | Assign published versions/modes/dates, required/optional, student; revoke future starts. | Admin; mentor limited to assigned students only if granted. | Quiz/weekly assignment concepts. | MVP |
| Students | Per-student current work, eligibility, progress, remediation; no raw hidden facts by default. | Assigned mentor or admin. | Admin Students patterns. | MVP |
| Attempts | Search, replay events/state, inspect grade/evidence, add feedback, reset, override with reason. | Mentor assigned scope; override default admin only. | Ticket Review patterns. | MVP |
| Reports | Scenario/skill failure trends, hints, time, alternate paths, fairness/health. | Admin/org reports; privacy thresholds. | AI cost/report cards. | Phase 2 |
| Environment | Templates, leases, capacity, health, reset/terminate/reconcile. | Environment-admin only; high-risk audit. | Admin Labs lifecycle patterns. | Phase 4 |
| Settings | Feature/cohort flags, limits, retention, mode defaults, AI/VM policies. | Global admin only; configuration audit. | Typed `AppSetting` accessors. | Foundation minimal, later expanded |

The full drag-and-drop scenario builder is Phase 5. MVP authoring uses reviewed config plus preview/validation/publication so an attractive editor cannot publish an invalid or leaky scenario.

**Optional future enhancement:** organization-specific scenario packs and delegated instructor authoring can follow only after tenant boundaries, publication review, and backward-compatible import/export are defined.

## 19. Permission matrix

**Strong recommendation:** model explicit capabilities even if initial enforcement maps them to current admin/student/mentor principals. “Mentor” must not mean “administrator.” Default-deny any capability not listed.

### Permission matrix

| Capability | Student | Mentor | Administrator |
|---|---:|---:|---:|
| View assigned scenarios | Own | Assigned students | All |
| View available published scenarios | Eligible own | Published catalog | All/drafts |
| Start/use attempt | Own | No (preview separately) | Preview only |
| View assigned students | No | Yes, explicit scope | Yes |
| View all students | No | No | Yes |
| Assign scenarios | No | Assigned students, published only if granted | Yes |
| View attempts | Own | Assigned students | All |
| View event log | Own student-visible events | Assigned attempts, instructor-visible | All including security view by capability |
| View transcripts | Own where policy allows | Assigned + consent/policy | Yes, policy/audit required |
| Add feedback | No | Assigned attempts | Yes |
| Override grades | No | No by default | Yes, reason + revision |
| Reset attempts | Own retry only when scenario permits | Request/limited if granted | Yes |
| Create scenario draft | No | No by default | Yes, author capability |
| Edit/clone draft | No | No by default | Yes, author capability |
| Preview/test scenario | Own published only | Optional reviewer capability | Yes |
| Publish/disable/mark broken | No | No | Yes, publisher capability |
| Manage VM environments | No | Observe assigned session only | Environment-admin only |
| View AI costs | Own usage not cost detail | No | Yes |
| Edit global settings | No | No | Yes |
| View organization reports | Own performance only | Assigned-student aggregate | Yes |
| Export raw events/transcripts | Own approved export | No by default | Privileged audited export |

## 20. My Training integration

**Strong recommendation:** add a future `service_desk_scenario` value to `TRAINING_ACTIVITY_TYPES` and the database check constraint through an additive migration. `content_ref` should identify the stable scenario plus an explicit published-version policy; metadata can carry assignment/mode/prerequisite presentation, but the server resolves and validates the actual version.

Completion contract:

- Required weekly activity completes only when the student's canonical assigned attempt for the resolved scenario/version reaches an accepted terminal outcome under its completion policy.
- Learning-mode practice may require “completed” while a graded weekly assessment may require “passed”; the activity config states which.
- A retry does not create multiple credits. The canonical best/accepted attempt is selected server-side.
- Service Desk attempt completion contributes once to practice and overall required training. It does not also count as a legacy support ticket unless an explicit migration crosswalk grants one compatibility credit.
- Rank progress remains separate. Only a configured promotion gate adapter may translate a verified Service Desk outcome into mastery/ticket-equivalent credit.
- Capstone readiness can require named scenario skills/outcomes without granting capstone access or bypassing `capstones.py` rank checks.

Prerequisite/remediation flow:

- Scenario definitions reference exact existing video/quiz/lesson/training activity IDs and required rank; curriculum validation rejects missing/disabled/inaccessible references.
- Weekly progression may hard-gate a required assigned scenario. Practice Library normally uses soft recommendations and explains them, preserving ordinary practice access.
- A failed skill maps to reviewed remedial content IDs. Example: a DNS scenario failure can recommend the exact DNS lesson and quiz; no title matching at runtime.
- `training_service.py` remains the single source for Home/Continue Training and week unlocking. Service Desk does not compute a competing “overall training percent.”

**Uncertain and requiring a decision:** decide whether first Service Desk attempts award XP directly, inherit legacy ticket XP through the crosswalk, or defer XP until mentor verification. The MVP should not introduce a second award path before this is approved.

## 21. Initial scenario pack

The pack intentionally begins with browser-only identity and access work. It teaches identity verification, safe change, validation, documentation, and communication before adding network/OS environments. “Frustrated user” should first be a persona variant on a real technical scenario, not a standalone root cause.

### Proposed scenarios

| Scenario | Difficulty | Prerequisites | Tools | Browser/hybrid/VM | Skills | MVP priority |
|---|---|---|---|---|---|---|
| Locked User Account | Beginner | Account-security lesson + quiz | Directory, Identity Console, KB, notes | Browser | identity verification, lockout diagnosis, unlock, verify, communicate | P0—first five |
| Password Reset | Beginner | Password/security lesson + quiz | Directory, Identity Console, KB, notes | Browser | verification, password policy, temporary credential, secure communication | P0—first five |
| MFA Reset | Beginner | MFA/security lesson + quiz | Directory, Identity Console, KB, notes | Browser | verification, factor reset, re-enrollment, escalation | P0—first five |
| BitLocker Recovery | Beginner/Intermediate | Encryption/device-security content | Directory, BitLocker, read-only Assets, KB, notes | Browser | device match, recovery disclosure, privacy, verification | P0—first five |
| New Employee Onboarding | Intermediate | Accounts, hardware, onboarding content | Directory, Identity Console, read-only Assets, KB, notes | Browser | checklist, least privilege, asset/account coordination, documentation | P0—first five |
| Outlook Not Syncing | Beginner | Email/connectivity lesson + quiz | Email, KB, notes | Browser | scope, connectivity, cache/profile reasoning, test | P1 |
| Network Printer Unavailable | Beginner/Intermediate | Printer/network basics | Printer, Directory, KB, notes | Browser | impact, queue/network checks, safe restart, verification | P1 |
| DNS Resolution Failure | Intermediate | DNS lesson + quiz | Terminal, network settings, KB | Browser first; hybrid later | name resolution, isolate layer, cache/config, verify | P1 |
| VPN Connection Problem | Intermediate | VPN/network/security content | VPN, Terminal, Directory, KB | Browser first; hybrid later | auth vs network, profile, logs, safe repair | P1 |
| Slow Computer | Intermediate | Hardware/Windows troubleshooting | Assets, Task/OS simulator, KB | Browser; hybrid later | baseline, bottleneck evidence, change control, verify | P2 |
| Windows Update Failure | Intermediate | Windows/update content | Update, services, terminal, KB | Browser; hybrid later | error interpretation, prerequisites, service/reboot, verify | P2 |
| Driver Issue | Intermediate | Hardware/driver content | Driver, Assets, KB | Browser; hybrid later | identify device, compatibility, rollback/update, verify | P2 |
| Employee Offboarding | Intermediate/Advanced | Identity, security, asset process | Directory, Identity Console, Assets, KB | Browser | authorization, disable/revoke, preserve data, chain of custody | P1 |
| Shared-Drive Access | Intermediate | Permissions/shares content | Directory, Access Console, KB | Browser; hybrid later | least privilege, groups, effective access, verification | P1 |
| Frustrated User + Access Problem | Intermediate | Communication plus one identity scenario | Conversation, Directory, Identity Console, KB | Browser; AI roleplay later | de-escalation, empathy, verification, technical resolution | P2 persona variant |

### Scenario behavior details

| Scenario | Learning Mode | Simulation Mode | Initial state and success | Common mistakes | Estimated time |
|---|---|---|---|---|---|
| Locked User Account | Recommends identity and account-status checks; explains lockout cause and safe unlock. | Sparse requester details, repeated lockout clue, light SLA. | Correct fictional user locked by stale credential; verify identity, identify condition, unlock safely, confirm sign-in, document. | Unlocking wrong user, skipping verification, resetting password unnecessarily, no verification. | 10–15 min |
| Password Reset | Shows password-policy article and secure temporary-password flow. | Ambiguous same-name employee; fewer hints. | Approved user needs reset; verify identity, reset under policy, require change/revoke sessions as configured, confirm, communicate securely. | Sending password in notes, wrong user, weak password, skipping session/policy step. | 10–15 min |
| MFA Reset | Explains lost-device vs service-outage distinction and enrollment. | Incomplete device facts and time pressure. | User lost factor; verify through approved channel, revoke old factor, issue enrollment, confirm. | Reset before verification, leaving old factor active, exposing enrollment secret. | 12–18 min |
| BitLocker Recovery | Guides device/asset matching and key disclosure policy. | Several devices/requesters; no recommended tool. | Approved user/device match; verify, retrieve/reveal simulated key once, record safe disclosure, confirm boot. | Wrong asset, logging key, disclosing without identity, treating recovery as root-cause fix. | 10–15 min |
| New Employee Onboarding | Checklist and rationale for least privilege; allows correction. | Missing manager detail requires clarification/escalation. | Approved hire facts; create/enable approved account/groups, assign available device, document handoff, verify access. | Excess groups, unapproved account, duplicate asset, skipping verification/handoff. | 20–30 min |
| Outlook Not Syncing | Guided scope and generic mail diagnostics. | Ambiguous local/profile vs service symptom. | Stale local sync state; check service/connectivity, repair minimal state, send test, document. | Recreate profile first, delete data, ignore outage, no test. | 15–20 min |
| Network Printer | Guided queue/network/driver sequence. | Several affected users changes impact/priority. | Offline/stuck queue or configuration fact; isolate, change minimally, print test. | Delete queue/driver prematurely, wrong printer, no test. | 15–20 min |
| DNS Failure | Explains IP vs name test and resolver chain. | Misleading “internet down” description. | Network works but resolver/cache/config does not; collect evidence, correct allowed cause, resolve and verify. | Random reboot, change many settings, flush cache without finding cause. | 20–25 min |
| VPN Problem | Guides local network, credentials, profile, MFA, route checks. | Partial error and SLA. | One pinned auth/profile/network cause; diagnose, correct or escalate, verify protected resource. | Reset unrelated password, disable security, no internal-resource test. | 20–25 min |
| Slow Computer | Shows baseline and evidence categories. | User reports vague slowness with competing signals. | Pinned resource/startup/disk condition; gather evidence, correct safely, compare result. | “Clean everything,” unapproved uninstall, no before/after evidence. | 20–30 min |
| Windows Update | Guides error/dependency/reboot sequence. | Multiple possible symptoms but one pinned state. | Update blocked by defined dependency/state; correct, retry, validate version/status. | Repeated retries, unsafe deletion, forced reboot without notice. | 20–30 min |
| Driver Issue | Guides device ID/status/version and rollback decision. | Time pressure with a plausible wrong driver. | Pinned incompatible/disabled driver; select safe repair and verify device. | Random download, unsigned driver, wrong device, no rollback plan. | 20–30 min |
| Offboarding | Explains authorization and ordered revocation. | Urgent manager request contains missing approval. | Approved departure; disable access/session/factors, groups/asset handoff, preserve required data, document. | Delete data/account, act without approval, miss factor/session/asset. | 20–30 min |
| Shared Drive | Guides identity/group/effective permissions and least privilege. | Similar groups/users and incomplete request. | Approved access via correct group/path; validate effective access and avoid excess. | Direct broad permission, wrong group, privilege escalation, no verification. | 15–25 min |
| Frustrated User | Provides optional communication prompts and pause/reframe hints. | Persona escalates based on student tone; technical facts remain deterministic. | Resolve the underlying pinned access problem and meet communication/verification rubric. | Arguing, promising unsupported outcome, skipping identity due pressure. | 15–25 min |

## 22. Support Tickets migration strategy

### Staged rollout

1. **Preserve current system:** keep Support Tickets label/routes/data and all My Training references while Service Desk foundation is behind a disabled flag.
2. **Side-by-side beta:** show Service Desk Lab only to administrators and explicitly allowlisted disposable/test students. Support Tickets remains the normal destination.
3. **Selected content migration:** import a small set into reviewed scenario drafts; record a legacy crosswalk; compare facts, prerequisites, completion, score, XP/mastery, review, and links. Do not background-convert historical submissions into fake event logs.
4. **Cohort rollout:** assign published scenarios to a small cohort; validate completion, mentor review, reports, rollback, and no double credit. Keep legacy history read/write as needed.
5. **Navigation rename:** change Practice Library **Support Tickets** to **Service Desk Lab** only after the MVP is stable, active weekly references have a migration/compatibility decision, production history is accessible, progression parity tests pass, and rollback is rehearsed.
6. **Compatibility:** preserve `/tickets/:id` and feedback links. The legacy list can become “Support Ticket History”; migrated new-start links may redirect through the crosswalk to `/service-desk`, never blindly by numeric ID.
7. **Retirement:** disable legacy authoring/new assignment only after no active curriculum requires it. Retain tables and read-only history for academic/audit purposes. Remove UI/code only in a separate approved migration project, never as part of MVP.

### Rollback

The feature flag removes Service Desk navigation and prevents new starts while retaining attempt data. Existing Support Tickets immediately remains available. No rollback deletes scenario/attempt rows. A failed migrated training activity can be reverted to its prior `support_ticket` reference in a reviewed curriculum change because the old record/history remains.

## 23. Testing strategy

### Automated layers

| Layer | Required coverage |
|---|---|
| Schema/version | Valid/invalid config, canonical hash, draft clone, immutable publication, disable without history breakage, reference validation, no hidden-data projection. |
| State engine | Initial state, every allowed action, alternate solutions, recoverable/critical mistakes, invalid transitions, optimistic conflict, idempotent replay, success/failure/escalation, reset lineage. |
| Scenario health | For every publishable version, execute at least one machine-readable valid completion path; assert no impossible prerequisites, missing tool handlers, unreachable success, or secret projection. |
| Attempts/events | Ownership, isolation, monotonic sequence, immutable events, state replay equals stored projection, grade evidence exists, event payload redaction, concurrent commands. |
| Grading | Dimension math, deterministic outcome, hint/timing policy, AI absent/failure fallback, grade revisions/override audit, historical rubric/version. |
| Permissions | Student A cannot read/write Student B; mentor only assigned scope; student cannot admin/mentor; publisher/environment/AI-cost capabilities separated. |
| Tools | Component/unit contract plus API transition for search/reset/unlock/MFA/BitLocker/KB/notes; keyboard/focus and mobile component checks. |
| My Training | Scenario reference health, required/optional completion, next activity, no duplicate credit, rank/capstone preserved, legacy crosswalk exclusivity. |
| Migration | Old routes/history/reviews/XP/progress unchanged; selected links map; feature flag rollback; disabled version history. |
| Browser | Playwright/Chromium at 1440×1000 and 375×812: login, navigation, start, action, refresh, back/forward, reconnect, complete, review, admin assignment/replay, console/network/a11y/overflow. |
| VM (Phase 4) | Quota, idempotent allocation, isolation, Guacamole scope, timeout, refresh recovery, validation, cleanup, orphan reconciliation, broker restart, resource exhaustion. |
| AI (Phase 3) | Grounding, injection/leakage, persona rules, identity verification, transcript retention, deterministic fallback, human override, model/rubric version and cost limits. |

### Manual acceptance

- Learning Mode beginner can identify the next action without an instructor.
- Simulation Mode does not expose recommended tools/answers unintentionally.
- Student can recover after refresh/logout/login without losing server state.
- A mentor can explain a grade from events; an administrator can replay and diagnose it.
- Mobile has no horizontal overflow/clipped controls and preserves notes/tool state.
- Every direct route refreshes through nginx SPA fallback and returns safe errors.
- Browser console/network have no persistent release-caused errors.
- Two-student IDOR tests modify IDs on every read/write/export endpoint.

## 24. Security review

### Highest risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Forged client actions/completion | High | Critical | Server state machine, typed commands, transactional event/state update, idempotency, authoritative validator/grade; never accept resulting state/completed flag. |
| Cross-student IDOR | Medium | Critical | Principal-derived queries, object-level checks on every read/write/export, non-enumerating 404, two-account automated matrix. |
| Hidden root/rubric/answer leakage | High | High | Separate raw definition from explicit public projection; recursive forbidden-field tests; no raw JSON in frontend/admin student preview. |
| VM lateral movement/production reach | Medium in Phase 4 | Critical | Separate networks/pools, deny-by-default egress, management isolation, least-privilege tokens, per-student leases, penetration/staging tests. |
| Guacamole/Proxmox credential exposure | Medium | Critical | Server-only clients, secret manager/vault, short-lived scoped users, no secrets in URL/log/event where avoidable, rotation/revocation. |
| Event payload PII/secrets growth | High | High | Typed/redacted payloads, visibility tiers, encryption/access, retention, export audit, do-not-log list. |
| Scenario version/history corruption | Medium | High | Immutable published rows, restrictive FKs, checksum, backups, replay tests, revisioned grades. |
| Mentor over-privilege | High with current boolean | High | Explicit capabilities and assigned-student scope; admin-only defaults for publish/override/env/settings/costs. |
| AI prompt injection/answer leakage | High in Phase 3 | High | Trust-separated bounded prompts, tool isolation, leakage tests, deterministic state authority, human review/fallback. |
| Upload malware/data exposure | Medium | High | MIME/signature/size checks, private retrieval, quarantine/scanning, attempt ownership, retention, no executable rendering. |
| WebSocket session abuse | Medium if added | High | Same-origin handshake, re-auth/authorization per message, size/rate/backpressure, idle/absolute timeout, sanitized logs. OWASP calls for origin/auth checks, limits, heartbeats, and avoiding sensitive message logs ([WebSocket Security](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)). |
| Grade override abuse | Low/Medium | High | Dedicated capability, mandatory reason, append-only original/revision, actor/time audit, periodic report. |
| Denial of service/cost exhaustion | Medium | High | Per-user/action/AI/environment limits, quotas, budgets, circuit breakers, queue backpressure, admin kill switch. |

### Additional controls

- Maintain student/admin/mentor route and service separation; frontend hiding is never authorization.
- Keep CSP same-origin. Add exact Guacamole/AI media origins only when required and reviewed; no wildcards.
- File and transcript access uses authenticated APIs, not static predictable paths.
- Validate and encode all simulated email/chat/KB/user content; never interpret it as HTML or executable commands.
- If real-time transport is unnecessary, use normal HTTP polling initially. Add WebSockets only for proven chat/session needs.
- Define incident response: disable feature/new starts, revoke environment/AI credentials, preserve audit evidence, notify affected users, restore verified backups, and document re-enable criteria.
- Back up scenario versions, attempts/events/grades, KB revisions, assignments, and broker metadata with existing DB procedures; test restoration and replay.

## 25. Performance and operations

- **Frontend:** lazy-load `/service-desk`, `/admin/service-desk`, and each tool; keep scenario schemas/data server-side; prefetch only the next likely small tool; establish chunk budgets and fail CI on major unexpected growth. Do not fix the existing Vite warning in this planning task.
- **API/state:** return safe projections/deltas, paginate queue/events/attempts, index student/status/version/sequence/time, and avoid replaying all events on every request. Add periodic state checkpoints only when profiling proves needed.
- **Database:** monitor SQLite write lock latency, event volume, replay/report cost, and backup duration. Define a tested PostgreSQL migration before higher concurrency, transcripts, or durable workers.
- **Real time:** prefer HTTP commands plus polling/SSE for simple updates. Add WebSockets only for interactive chat/remote session signals, with the controls in Section 24.
- **Jobs:** browser MVP grades synchronously when cheap. AI and VM workflows use durable queued jobs with idempotency, retries, dead-letter/reconciliation, and admin visibility.
- **Observability:** correlation IDs from request → event → grade → AI/broker job; metrics for starts, completion, rejected actions, state conflicts, latency, errors, hint use, broken versions, cost, queue time, environment orphans, and cleanup.
- **Feature flags/rollout:** disabled default; admin/test allowlist; one cohort; percentage/cohort expansion; kill new starts independently from read-only history.
- **Backup/restore:** use `docs/DEPLOYMENT.md` procedures; add scenario/event replay and history checks to restore drills. Never publish or seed content automatically during production startup.

## 26. Phased roadmap

### Implementation phases

| Phase | Features | Dependencies | Database changes | Relative effort | Risk | Completion criteria |
|---|---|---|---|---|---|---|
| 0: Foundation | Flag, lazy route shell, capability policy, schema/validator, immutable versions, attempts/events/grade foundation, deterministic engine, admin read-only list/validation, one test fixture. | Approved schema, permission/retention/XP decisions; current auth/My Training conventions. | First additive foundation migration in Section 12. | Medium | High | Hidden-data tests pass; one version publishes and replays; Student A/B isolation; no nav for unflagged users; rollback disables starts. |
| 1: Browser MVP | Overview, queue, ticket workspace, Learning/Simulation policy, Directory, Identity/MFA, BitLocker, KB, notes/hints/escalation/resolve, assignments, review/replay, first five scenarios, My Training activity. | Phase 0; reviewed content/KB; mentor-scope decision. | Knowledge, artifact link, legacy crosswalk if not in foundation. | Large | High | Five health-tested scenarios; end-to-end browser/mobile/a11y; deterministic grades; progression no double credit; cohort beta passes. |
| 2: Troubleshooting tools | Assets, printer, email, terminal, DNS/VPN/slow-PC/update/driver, paths, expanded reports. | Stable tool registry/action engine; content authors. | Training paths/items, normalized messages if required, report indexes/checkpoints. | Large | Medium/High | New tools share framework; valid paths and alternate solutions; bundle budgets; reports match raw events. |
| 3: Communication | Scripted text maturity, voicemail, AI caller/chat, transcripts, communication evaluator, de-escalation variants, cost controls. | Approved provider/privacy/consent/retention; AI calibration and human review. | Calls/transcripts/evaluation metadata; AI usage links. | Very large | High | No answer leakage/injection escapes; deterministic technical score unaffected; budgets/fallback/human review; transcript privacy tests. |
| 4: Advanced environments | Durable broker, templates, Proxmox/Guacamole, AD/DNS/DHCP/GPO/file-share/PowerShell environments, validation/reset. | Staging infrastructure acceptance; queue, vault, network isolation, capacity. | Environment templates/sessions/operations/validation. | Very large | Very high | Isolation/red-team tests; crash/orphan recovery; scoped sessions; automatic validation/reset; quota/rollback; manual fallback. |
| 5: Instructor/organization | Full scenario builder, custom packs, advanced analytics, portfolio evidence, LMS/org controls. | Mature schema/version/editor governance and usage evidence. | Organizations/content ownership/export/integration tables as approved. | Very large | Medium/High | Draft/test/publish safety; tenancy/privacy; audit; backward-compatible imports/exports. |

## 27. Risks and mitigations

### Major risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Engine becomes a pile of tool-specific conditionals | Medium | High | Typed tool registry, common command/result/event contract, pure transition tests, architectural review at Phase 0. |
| Simulations feel like form filling rather than troubleshooting | High | High | Begin with observable state, alternate actions, feedback, communication, and user tests with the five beginners; do not over-script the happy path. |
| Existing ticket/history/progression breaks | Medium | Critical | Side-by-side flag, explicit crosswalk, no table deletion, compatibility routes, one-source credit tests, rollback to legacy. |
| Content authoring outruns validation | High | High | Hybrid reviewed source, strict schema/reference/leakage checks, executable health paths, immutable publish. |
| Mentor model is too broad | High | High | Capability/assignment layer before mentor endpoints; admin-only high-risk defaults. |
| SQLite/event volume contention | Medium | High | Benchmarks and indexes; small cohort rollout; PostgreSQL readiness gate before scale. |
| Frontend bundle becomes worse | High | Medium | Route/tool lazy loading, chunk budgets, no vendor UI frameworks for each simulator. |
| Technical grading relies on AI prose | Medium | Critical | Deterministic state/event grade is authoritative; AI limited to later qualitative dimensions. |
| VM automation is unreliable or unsafe | High before staging | Critical | Defer to Phase 4; new durable broker; isolation/quotas/reconciliation; manual fallback. |
| Students learn the UI rather than transferable process | High | High | Generic original tools, variable facts/alternate paths, explicit skill rubric, explanation tied to reasoning. |
| MVP is too broad | High | High | Five scenarios/five shared tools, browser-only, no calls/VM/full builder/shifts. |

## 28. Open decisions

The following require human approval before or during Phase 0:

1. **Mentor scope:** all current students or explicit mentor-student assignments? Recommended: explicit assignments.
2. **MVP XP/mastery:** direct award, legacy-equivalent adapter, or mentor-verified award? Recommended: no new direct XP until one-source credit is specified.
3. **Attempt policy:** concurrent attempts per scenario/mode, retry limits, best/latest/verified result. Recommended: one active attempt per scenario+mode; unlimited Learning retries; configured Simulation retries.
4. **Completion threshold:** “completed” versus “passed” for weekly required activities. Recommended: configured per activity, default pass for assessment and complete for practice.
5. **Retention/privacy:** canonical event, verbose telemetry, upload, transcript, and portfolio periods plus consent/export/deletion policy.
6. **Scenario publisher roles:** which administrators may author versus publish; whether two-person review is required for high-risk scenarios.
7. **Knowledge content ownership:** who reviews articles for accuracy and answer leakage.
8. **Production database threshold:** measurable point to migrate SQLite to PostgreSQL.
9. **Feature flag granularity:** admin/test allowlist, cohort model, and emergency read-only behavior.
10. **Accessibility target:** recommended WCAG 2.2 AA acceptance and documented desktop-first exception for later full VM control.
11. **AI provider/model:** deferred until Phase 3; no choice is required for MVP.
12. **VM topology/capacity/network:** deferred until Phase 4 staging discovery.

## 29. Clear MVP recommendation

The MVP is a browser-only, feature-flagged Service Desk workspace using Nexus login and current navigation. It includes Overview, Work Queue, ticket workspace, a small Performance summary, searchable Knowledge Base, admin assignments, scenario validation/publication, attempt review/replay, Learning and Simulation policies, deterministic grading, and five identity/onboarding scenarios. It uses Directory, Identity & Access/MFA, BitLocker, Knowledge Base, and ticket conversation/resolution tools.

Do **not** include Proxmox, Guacamole, real AD, AI callers/evaluators, voicemail, multi-ticket shifts, a full visual scenario builder, organization/LMS features, vendor-exact interfaces, broad analytics, or all 15 scenarios in the MVP.

Success is not “the pages exist.” Success is: a beginner can start a valid assigned scenario, act through server-validated tools, recover after refresh, finish through at least one valid path, receive an explainable grade tied to immutable events, and have the result flow once into My Training without exposing answers or another student's data.

## 30. Clear first implementation task and final answers

### First implementation task

Deliver a disabled-by-default **Scenario Foundation vertical slice**:

1. additive foundation migration from Section 12;
2. Pydantic scenario schema and canonical validator;
3. immutable draft/publish/version service;
4. attempt start and one generic server action/event transition with optimistic concurrency and idempotency;
5. explicit safe student projection and hidden-field tests;
6. read-only admin scenario/version/validation API;
7. lazy `/service-desk` route shell showing “not enabled” or one test assignment;
8. one reviewed Locked User Account test fixture and machine-executed valid path;
9. Student A/B IDOR, replay, downgrade/upgrade, and feature-flag rollback tests.

This is an implementation-phase task, not work performed by this plan.

### Required final recommendations

1. **Should Support Tickets be reused, wrapped, migrated, or replaced?** Preserve it unchanged for active/history use, wrap it with adapters, and migrate selected content gradually into a new engine. Replace only its future simulation experience; never rewrite historical submissions.
2. **What should the first MVP contain?** The browser-only scope in Section 29 with immutable versions, server actions/events, deterministic grading, five scenarios, assignments, review, KB, and My Training integration.
3. **Which five scenarios first?** Locked User Account, Password Reset, MFA Reset, BitLocker Recovery, and New Employee Onboarding.
4. **Which browser tools first?** Employee Directory; combined Identity & Access/MFA Console; BitLocker Recovery; Knowledge Base; ticket conversation, notes, escalation, and resolution controls.
5. **What should not be built in MVP?** AI/voice, Proxmox/Guacamole/real systems, multi-ticket shifts, full builder, vendor UI copies, LMS/org tenancy, and the full scenario pack.
6. **Which Nexus systems are reused unchanged?** Student/admin authentication, student identities, quiz/lesson/video history, current Support Ticket data/routes/history, capstone authorization, deployment/backups, and the global Home/My Training/Practice Library/Progress structure.
7. **Which systems need extension?** Mentor capabilities/scope, Training activity types/completion/validation, Progress/adapters, uploads authorization/linkage, AI cost metadata later, admin review/report patterns, and low-level VM clients behind a later broker.
8. **What database migration first?** The additive scenario/version/skill/assignment/attempt/event/grade/feedback foundation described in Section 12, with no content assignment or legacy-table mutation.
9. **What API first?** `POST /api/service-desk/attempts`, because it establishes eligibility, immutable version pinning, frozen facts, idempotency, ownership, and the safe projection used by every later tool.
10. **What frontend route first?** Lazy-loaded `/service-desk` Overview shell behind the disabled-by-default feature flag.
11. **When rename Support Tickets?** Only after selected-cohort MVP acceptance, history/progression parity, migrated weekly references, compatibility links, and rollback pass; then retain a Support Ticket History route.
12. **When introduce Proxmox?** Phase 4, after browser/hybrid demand is proved and a durable broker, staging isolation, quotas, validation, cleanup, and secret controls pass.
13. **When introduce AI?** Phase 3, after deterministic scenarios/events/grades and transcript/privacy/human-review controls are stable.
14. **Highest technical risk?** Creating a secure, deterministic, replayable server state/event engine that preserves version history and cannot be forged or leak hidden facts.
15. **Highest product risk?** Building an elaborate ticket UI that teaches button memorization instead of transferable troubleshooting, communication, and judgment.
16. **Is the plan ready for implementation?** Yes, for human review and Phase 0 after the open policy decisions in Section 28 are resolved or explicitly deferred with the recommended defaults.

## Appendix A: Repository evidence inspected

The audit read relevant implementations rather than inferring from filenames. Material evidence included:

- Frontend: `frontend/package.json`, `vite.config.js`, `src/main.jsx`, `src/App.jsx`, `src/styles.css`, student Home/My Training/Progress/Study Tracker/Quiz/Tickets/Labs/CLI/Capstone/Command/Terminal pages and components, admin Training/Ticket Review/Labs/Capstones/AI cost pages, `src/api.js`, and nginx configuration.
- Backend application: `backend/app/main.py`, `database.py`, `config.py`, `utils/responses.py`, router registration, error/security middleware, and health/upload mounting.
- Models: student, app setting, training, study tracker/video, learning, quiz, ticket, lab, CLI lab, VM assignment, capstone, progression, evidence, incident/RCA, AI usage/rate limit, squad/activity, and resources.
- Student/admin APIs: auth/session, students, training/admin training, tickets/admin tickets, quizzes, labs/admin VM lifecycle, CLI labs, capstones, evidence, submissions, onboarding, study tracker, search/resources, admin content/curriculum/students.
- Services: auth/admin auth, training, progression, onboarding, ticket parameters/grader/mastery, evidence validation, AI, Discord, Proxmox, Guacamole, CLI seed, curriculum seed/validation.
- Migrations/seeds: the full Alembic version list through `0033`, My Training migrations, `seed.py`, phase seeds, curriculum seed/reference data, and CLI lab content.
- Tests: all files under `backend/tests`, with focused reading of auth/security, tickets/hints/parameters, progression gates, training/admin training, labs, Proxmox, Guacamole, capstones, quizzes, and data-integrity tests.
- Operations/docs: `README.md`, `docs/DEPLOYMENT.md`, `AUTHORING_CONFIG_SECURITY.md`, `MENTOR_GUIDE.md`, `STUDENT_GUIDE.md`, `MY_TRAINING.md`, `MY_TRAINING_QUIZ_MAPPING.md`, backup/deployment scripts, Compose/systemd/nginx configuration, environment examples, and dependency manifests.

## Appendix B: External primary references

These references support future infrastructure/security design; repository evidence remains authoritative for current Nexus behavior:

- [Proxmox VE `qm` documentation](https://pve.proxmox.com/pve-docs/qm.1.html)
- [Proxmox VE API](https://pve.proxmox.com/wiki/Proxmox_VE_API)
- [Proxmox VM Templates and Clones](https://pve.proxmox.com/wiki/VM_Templates_and_Clones)
- [Apache Guacamole configuration](https://guacamole.apache.org/doc/gug/configuring-guacamole.html)
- [Apache Guacamole UI/mobile behavior](https://guacamole.apache.org/doc/gug/using-guacamole.html)
- [Apache Guacamole vault integration](https://guacamole.apache.org/doc/gug/vault.html)
- [OWASP IDOR Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
- [FastAPI Background Tasks caveat](https://fastapi.tiangolo.com/tutorial/background-tasks/#caveat)
