# Service Desk Lab Scenario Foundation

Status: Phase 1A browser MVP/private beta. The feature remains disabled by default and has no general rollout.

## What exists

The browser MVP provides five reviewed, browser-simulated scenarios: **Locked User Account**, **Password Reset**, **MFA Reset**, **BitLocker Recovery**, and **New Employee Onboarding**. It adds an explicit beta allow-list, assignments, a safe Knowledge Base, workspace/queue/performance APIs, and administrator review. It does not replace Support Tickets, add AI, provision VMs, make calls, or use voicemail.

## Feature gates

Both environment variables default to `false`:

| Variable | Effect |
|---|---|
| `SERVICE_DESK_LAB_ENABLED` | Enables student Service Desk APIs. Normal students receive a controlled `404 SERVICE_DESK_UNAVAILABLE` while false. |
| `SERVICE_DESK_LAB_ADMIN_ENABLED` | Enables administrator inspection/validation APIs for controlled testing. It does not enable student APIs. |

Normal students never receive a Service Desk navigation item. An explicitly enrolled student sees **Service Desk Lab** inside Practice Library only when the student flag is enabled. A direct `/service-desk` visit still calls server-side access checks and returns only a controlled unavailable state unless both controls permit access. Mentors have no implicit access. Administrators see `/admin/service-desk` under Assessments & Labs only when the separate admin flag is enabled.

## Phase 1A workspace and beta controls

The lazy `/service-desk` bundle has internal **Overview**, **Work Queue**, **Performance**, **Knowledge Base**, and Exit-to-Nexus navigation. The queue and overview make Learning and Simulation starts explicit. A ticket workspace exposes only pinned student-safe facts and contextual tools: Ticket/notes, Employee Directory, Identity & Access, BitLocker Recovery, Onboarding, and Learning Help. Contextual forms expose action field names but never accepted values, branch rules, credentials, recovery keys, or hidden rubrics; this lets a student make and learn from a wrong-account or wrong-device choice instead of merely clicking a pre-filled action.

Beta enrollment is an explicit database allow-list managed by administrator APIs. Enrollment/removal, assignment changes, knowledge edits, and resets create Service Desk audit records. Assignments target one student/scenario/mode with optional required status, due date, and simulation-attempt override. Learning Mode exposes versioned deterministic hints and remains unlimited; Simulation Mode has no hint action and defaults to three terminal attempts. Both use the same server-owned transition engine and deterministic grade.

Published Knowledge Base articles provide general process guidance. Opening/searching articles never exposes scenario-specific answers. Event payloads redact resolution text and never persist client password or recovery-key values. BitLocker key access is modeled as a state transition, not material returned to a browser or event log.

`service_desk_scenario` is a future My Training activity type. It references a published scenario stable key and completes only from a passed authoritative attempt. No seeded production week includes this type, and it remains distinct from `support_ticket`, so it cannot duplicate legacy ticket XP or completion credit.

## Scenario definition format

Definitions are reviewed JSON files in `backend/app/data/service_desk/`. JSON is loaded with the standard safe JSON parser and validated with strict Pydantic models; arbitrary executable code and unknown fields are rejected.

Each definition includes a stable key, integer version, public metadata, modes, objectives, skills, explicitly separated `student_facts` and `hidden_facts`, typed state schema/initial state, permitted actions, preconditions, declarative branches/mutations, success conditions, point values totaling 100, feedback, and a machine-executable `health_path`.

`student_facts` cannot contain known hidden keys such as `root_cause`, `correct_account_id`, instructor notes, answer metadata, or validation secrets. `critical_failure` cannot be marked student-visible. A health path must reference known actions, include resolution, and reach a valid pass.

## Publication and immutability

`ServiceDeskScenario` is a stable identity. `ServiceDeskScenarioVersion` stores an immutable canonical JSON definition and SHA-256 definition hash. A publishing operation is idempotent only when the stable key, version number, and hash match. Changing an existing published version raises an error; publish a new version number instead.

Existing attempts pin their `scenario_version_id`, so later scenario edits cannot change historical facts, rules, events, or grades. Published definitions may later be disabled for new starts, but their historical content remains available for replay and review.

All five reviewed JSON definitions and seven published Knowledge Base articles seed idempotently at application startup. Deployment still requires migration first and must keep both feature flags false until human rollout approval.

## Transition engine and events

`service_desk_engine.py` is the only state transition boundary. It loads the pinned definition, confirms feature availability and attempt ownership, validates the action/payload/preconditions, applies declarative state mutations, appends one event, recalculates the deterministic grade, and returns a safe projection.

Clients cannot send a final state, score, or completion flag. Each action includes an idempotency key and expected state version. A repeated key returns the existing result without creating another event. A stale state version is rejected with `409 STATE_CONFLICT`.

Events are append-only and unique by `(attempt_id, sequence_number)` and `(attempt_id, idempotency_key)`. Server timestamps and hashes support ordered replay. Resolution-note text is not retained in event payloads; only a presence/length marker is retained for deterministic documentation credit.

## Safe projection and scoring

Student APIs return only the ticket information intentionally provided, allowed action keys/tools and required field names, visible state fields, mode, status, student-safe feedback, and score/result. They never serialize accepted field values, `hidden_facts`, root causes, expected sequences, critical definitions, hidden rubrics, instructor notes, or validation metadata.

The Locked User Account scenario scores these server-recorded actions once each: open ticket (5), inspect requester (10), verify identity (25), search account (5), inspect account (10), unlock correct account (30), document (10), and resolve (5). A pass requires all technical success conditions, no critical error, and score at least 80. Unlocking before identity verification or unlocking a wrong account is a critical failure and cannot pass. Learning Mode allows unlimited retries and a deterministic hint; Simulation Mode allows three scored attempts. An administrator may release a completed simulation attempt from that cap through the reset endpoint; the original attempt, grade, and ordered event log remain intact.

## APIs

Student APIs, gated by `SERVICE_DESK_LAB_ENABLED` **and explicit beta enrollment**:

- `GET /api/service-desk/scenarios`
- `POST /api/service-desk/scenarios/{scenario_id}/attempts`
- `GET /api/service-desk/attempts/{attempt_id}`
- `POST /api/service-desk/attempts/{attempt_id}/actions`
- `GET /api/service-desk/attempts/{attempt_id}/result`
- `GET /api/service-desk/overview`, `/queue`, `/performance`
- `GET /api/service-desk/knowledge`

Admin APIs, protected by current admin authentication and `SERVICE_DESK_LAB_ADMIN_ENABLED`:

- `GET /api/admin/service-desk/scenarios`
- `GET /api/admin/service-desk/scenarios/{scenario_id}/versions`
- `POST /api/admin/service-desk/scenarios/validate`
- `POST /api/admin/service-desk/scenarios/publish`
- `GET /api/admin/service-desk/attempts/{attempt_id}/events`
- `POST /api/admin/service-desk/attempts/{attempt_id}/reset`
- assignments, beta enrollment/removal, Knowledge Base, attempt list, and five-scenario health status

Mentor APIs are intentionally absent until explicit mentor-to-student assignments exist.

## Health tests and next scenario

The health test executes the declared valid path and verifies state, ordered events, score/pass result, safe projection, replay, recovery, critical failure, idempotency, ownership, simulation limits, publication immutability, disabled behavior, and admin protection. Every published scenario must supply a valid `health_path` before it can be treated as healthy.

To add a scenario in a later approved phase:

1. Add a reviewed JSON definition with a new stable key/version and no hidden data in student facts.
2. Validate it through the admin validation API and automated tests.
3. Add a valid health path plus invalid/recoverable/critical-path tests.
4. Publish a new immutable version under administrator authorization.
5. Add a separate reviewed integration decision before connecting it to My Training, XP, mastery, or Support Ticket migration.

## Rollout and rollback

Deploy the additive `0035_service_desk_browser_mvp` migration with both flags false; verify normal student denial, then optionally enable admin review, then enroll specific approved students before enabling student access. Back up database/uploads and verify integrity before migration. Roll back code/flag activation for authorization, hidden-data, Support Ticket, or migration regressions; downgrade `0035` only after confirming no Phase 1A records must be retained. AI, Proxmox, Guacamole, Active Directory, calls, voicemail, and organization work remain intentionally deferred because deterministic browser simulation and safe replay are the Phase 1A boundary.
