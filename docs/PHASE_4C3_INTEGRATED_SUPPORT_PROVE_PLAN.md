# Phase 4C.3 — Integrated Support Prove

Status: implementation-ready design only. This document does not authorize deployment,
production migration, or Phase 4C.3 implementation.

## Decision

Proceed later with a deterministic, server-authoritative, three-incident final support
shift. Upgrade the existing Week 23 and Week 24 guided labs in place and add no curriculum
activities. The preferred delivery is Option D: convert the existing Week 24 `LabTemplate`
into a purpose-built multi-incident assessment while retaining its activity, template, and
historical run identities.

This is a bounded final assessment, not an early implementation of Persistent Company.

## Current-state audit

### Week 23 — Integrated Operations

The database title is currently **Integrated Operations**, rather than the older planning
label **Integrated Support Operations**. It is active, estimated at 240 minutes, and contains:

| Activity | Type | Required | Minutes | Current mechanics |
| --- | --- | ---: | ---: | --- |
| Working a Mixed Queue | Lesson 61 | No | 90 | Teaches domain/layer/owner separation, context switching, escalation, and a notes template. |
| Incident Communication and the Post-Incident Note | Lesson 62 | No | 75 | Teaches updates and post-incident documentation. |
| Incident Response | Video 174 | Yes | 6:43 | Required incident-response overview. |
| Incident Response Quiz | Quiz 48 | No | 15 | Optional check. |
| Integrated Operations Readiness | Quiz 25 | Yes | 15 | Required readiness check. |
| Work the Mixed Support Queue | Guided lab 21 | Yes | 25 | Three guided questions, structured-operations type, difficulty 1, default Practice role. |

The week has useful preparation content, but its only practical is a short, answer-led
exercise. It is appropriate as rehearsal, not as the graduation assessment.

### Week 24 — Final Support Shift

Week 24 is active and estimated at 300 minutes. It contains:

| Activity | Type | Required | Minutes | Current mechanics |
| --- | --- | ---: | ---: | --- |
| Capstone Briefing: Your First Week at Maple & Finch | Lesson 63 | No | 60 | Describes a four-stage, 20-hour persistent-company capstone and optional manual VM mode. |
| Environmental Social and Governance videos 171–173 | Videos | No | — | Stale fallback material that does not contribute to the final-shift goal. |
| Final Support Shift | Guided lab 22 | Yes | 35 | Seven structured questions and three exact command strings; default Practice role. |
| Take Over Maple & Finch Co. | Capstone 3 | No | 1,200 | Optional future-scope capstone. |

The current required lab has a sound mixed-domain intent and includes prioritization,
security escalation, and documentation questions. It is nevertheless too weak to prove
independent readiness:

- the UI exposes required commands as **Try** buttons;
- every correct answer in the current seven-question exercise is the first option;
- command completion trusts presence of exact strings in the browser-submitted transcript;
- there is no server-owned incident state, triage order, per-incident verification, user
  update, escalation artifact, or final handoff;
- grading is question-count percentage with a 70% threshold;
- the required activity is not a final-role promotion gate;
- a learner can pass by recognizing choices rather than investigating a support queue.

### Capstone inventory

| ID | Capstone | Week | Required | Duration | Infrastructure / mentor | Grading and graduation |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 1 | CompTIA A+ Module 1 Capstone: Hardware & Troubleshooting | 4 | No | 3 h | Written component guide, troubleshooting scenario, reflection; no infrastructure requirement | Submission writes a nominal score of 10 but does not pass the run; no review API or graduation gate. |
| 2 | CompTIA A+ Module 2 Capstone: Networking & OS | 8 | No | 4 h | Network diagram, troubleshooting exercise, command sheet; no infrastructure requirement | Same submission-only mechanics; no graduation gate. |
| 3 | Take Over Maple & Finch Co. | 24 | No | 20 h | Optional manual-VM/full-environment mode; mentor represents human roles; planned DC, client, Ubuntu, Headscale, backup, and persistent company state | No authoritative practical grading and no graduation gate. |
| 4 | Microsoft Workplace Support Shift | 29 | No | 2 h | Four Microsoft 365 process tickets; no mandatory infrastructure | Same submission-only mechanics; no graduation gate. |

Capstone access is based on the student's highest historical role, not only the current
role. Submission sets a run to submitted and gives it a nominal score, but does not set
`passed`. Training completion nevertheless treats a submitted capstone as complete. There
is no mentor/admin review endpoint despite score and pass fields on the model.

The current UI renders `skills` and `items`, while Maple & Finch primarily stores `stages`
and `artifacts`. Its most important structure is therefore not presented reliably. Nested
rubric anchors are also not compatible with the generic renderer.

Valuable concepts to bring forward now are mixed-queue prioritization, safe fixes,
escalation, evidence, communication, post-incident notes, and handoff. Persistent company
state, a 60-person organization, a CMDB, live mentor-fed events, cloned servers and clients,
backup restoration, and a 20-hour operating week remain future scope.

## Competency coverage

### Must prove

- read imperfect requester language; establish scope, impact, owner, and priority;
- distinguish an active identity/security risk from a broad outage and from a lower-impact
  incident with a workaround;
- investigate Windows/identity access safely and distinguish AD, Entra, endpoint, and
  application evidence;
- use network, server, Linux, and cloud evidence to locate the failing layer;
- select a scoped remediation or a justified escalation without weakening security;
- verify the user's outcome and the relevant service/control state;
- record Issue, Evidence, Action, and Verification;
- provide a concise user update and a usable end-of-shift handoff.

### Should sample

- Windows services/processes/events and local storage/profile reasoning;
- account state, group/token/access reasoning, MFA and sign-in evidence;
- Microsoft 365 workload ownership and endpoint compliance as competing signals;
- IP, gateway, DNS, DHCP/VPN, client-versus-network, and basic segmentation awareness;
- Linux service, log, listener, disk, permissions, and network evidence;
- cloud control plane versus guest OS, network, and identity boundaries;
- server task/log/PowerShell inspection and owner-aware escalation.

### Optional advanced

- detailed Exchange, Teams, OneDrive, SharePoint, and Intune administration;
- BitLocker recovery and device lifecycle execution;
- complex VLAN design, cloud architecture changes, or domain-controller remediation;
- infrastructure provisioning, backup restoration, and multi-host incident command.

The final shift samples combinations of competencies; it should not attempt to retest every
tool or product taught across 35 modules.

## Assessment design

### Delivery choice

Use a small `FinalSupportShiftWorkbench` selected by the existing Week 24 `LabPage` for
`LabTemplate` 22. Reuse existing authentication, week gating, `LabRun`, evidence-panel,
terminal-profile, structured-note, and lab API patterns. Add only the endpoints and service
contract necessary for authoritative multi-incident state.

Why the alternatives are weaker:

- **Option A, one existing EvidenceCaseWorkbench:** its single complaint, evidence set,
  answer set, and notes model cannot cleanly own a queue or independent incident state.
- **Option B, parent controller over three curriculum activities:** increases orchestration
  and completion identities and conflicts with the zero-new-activity preference.
- **Option C, Service Desk pack plus evidence cases:** requires cross-application progress
  joins and new or directly reused scenarios; direct reuse over-rewards memorization.
- **Option D, in-place final lab:** preserves the exact required identity and offers one
  server-owned attempt, queue, rubric, result, and graduation gate.

### Incident 1 — Unrequested authentication prompts

Requester reports repeated MFA prompts and an unfamiliar sign-in notification. The initial
ticket must not label this a security incident or disclose the diagnosis.

Evidence may include Entra sign-in events, MFA method state, device/client context, account
state, recent changes, and one benign failed-sign-in distractor. The learner must verify
identity, recognize active account risk, contain or route the account through the approved
security action, avoid a routine password-only close, verify the resulting state, update the
user, and escalate the security event with the correct evidence.

Primary skills: priority judgment, identity/Entra/MFA, security containment, communication,
and escalation.

### Incident 2 — Finance share access after a role change

A finance team loses access to a shared location after a role move. Multiple staff are
affected and no workable alternative exists. Evidence combines AD group membership,
token/session state, share and NTFS effective access, a recent approved role change, and an
endpoint-compliance signal that is plausible but non-causal.

The learner must scope impact, distinguish identity/token/access layers, reject broad group
membership or permissive ACL changes, select the narrow correction or correct owner
escalation, refresh/verify effective access, and communicate restoration.

Primary skills: Windows/AD, access control, scoped remediation, business impact, and user
verification.

### Incident 3 — Internal knowledge base unavailable

The internal knowledge base on an Azure-hosted Linux VM is unavailable, but staff have a
temporary documentation workaround. Azure resource health and power state are healthy, the
NSG permits the intended source, and the current VM IP is visible. Linux evidence shows the
application binding to an obsolete private address after a redeploy. Available tools include
resource/health/activity views and deterministic `ip`, `systemctl`, `journalctl`, `ss`, and
`curl` outputs, with unrelated disk and firewall evidence remaining healthy.

The learner must distinguish cloud control plane, network, and guest configuration; apply
or recommend the owner-scoped configuration correction; and verify the listener and
application path. This is a new variant of taught skill models, not a replay of Week 20 or
Week 22 answers.

Primary skills: Linux, networking, cloud responsibility boundary, service verification, and
handoff.

Three incidents are sufficient: they cover the mandatory combinations without turning the
assessment into a stamina test or Persistent Company simulation.

## State contract

Store server-owned state per attempt:

- attempt and rubric version, status, start/submission timestamps;
- submitted triage order, selected priority factors, and short rationale;
- per-incident status, evidence identifiers opened, decisions/actions attempted, accepted
  disposition, verification evidence, and completion state;
- structured Issue, Evidence, Action, Verification, user update, and escalation fields;
- rejected unsafe attempts and the reason code;
- final handoff entries and final submission/result.

The client may cache unsaved drafts, but reload/resume must reconstruct authoritative state
from the server. Incident state and evidence must be isolated within the authenticated
student's `LabRun`. Do not store a company model, employees, devices, economy, real-time
events, CMDB, or generated tickets.

## Prioritization

Present all three tickets simultaneously using timestamps, requester wording, scope,
security indicators, affected-user counts, business impact, and workaround availability.
Do not show P1/P2/P3 labels.

The deterministic expected order is:

1. unfamiliar sign-in/MFA activity because it is an active security risk;
2. the multi-user Finance access outage because it has broad impact and no workaround;
3. the knowledge-base incident because an adequate temporary workaround exists.

Grade both the order and the factors. A correct order with an empty rationale is incomplete;
free text is checked only for presence/length, never by AI or keyword guessing. The selected
structured factors provide the deterministic justification signal.

## Guidance and evidence

Initial content contains only the queue, symptoms, timestamps, requester wording, and known
impact. It must not contain a diagnosis, correct layer, explicit priority, or command list.
Evidence/tool categories can be available, but no tab or command is preselected. Titles and
buttons must describe the source (for example, **Entra sign-ins** or **Linux terminal**), not
the root cause.

The final Prove attempt has no hints. A generic help affordance may explain tool categories
and interaction mechanics, but must not reveal exact commands, evidence order, or diagnosis.
Week 23 is the supported Practice environment where learners receive guidance.

Terminal profiles remain deterministic and allowlisted. Unknown commands return scoped
unavailable feedback, never generic healthy output. Transcript text is evidence for the
learner, not proof of completion.

## Required professional outputs

Per incident:

- **Issue and scope:** affected user/service, impact, and responsible layer as concluded;
- **Evidence:** selected server-known evidence references plus concise interpretation;
- **Action or disposition:** the accepted scoped action, owner escalation, or containment;
- **Verification:** selected post-action evidence and the user-visible outcome;
- **User update:** status, impact, action/outcome, and next expectation;
- **Escalation:** destination, urgency, evidence, action already taken, and requested next
  step when escalation is appropriate.

At final submission:

- incident status and outcome;
- unresolved owner and next action;
- outstanding user promise;
- concise final-shift handoff summary.

Do not require the learner to repeat the same prose in several fields. Structured choices
carry facts; text fields test concise professional documentation.

## Server-authoritative grading

Reuse the established Service Desk process philosophy per incident:

| Category | Weight |
| --- | ---: |
| Investigation | 15% |
| Diagnosis | 25% |
| Remediation / disposition | 30% |
| Verification | 20% |
| Documentation / communication | 10% |

The shift score is 90% mean incident score plus 10% shift operations: 6% prioritization and
4% final handoff. All scoring inputs are accepted server events, server-known evidence,
structured selections, and required-field completeness. The browser never supplies scores
or completion claims.

Pass requirements:

- final score at least 80%;
- every incident score at least 70%;
- all incidents safely resolved, contained, or escalated;
- triage and final handoff complete;
- no critical unsafe action.

Unsafe actions must be rejected before state mutation and recorded by reason code. A
critical unsafe action fails that attempt rather than silently allowing trial-and-error.

## Retry and reset

- Allow up to three self-service attempts.
- Submitted attempts are immutable; a retry creates a new attempt/run state.
- Failed attempts do not award completion or satisfy progression.
- There is no Learning Mode or hint ladder inside the final Prove; Week 23 provides Practice.
- Do not apply XP penalties. A pass can use the existing lab XP policy.
- A mentor reset is for abandoned/corrupt attempts, not for editing a submitted score. The
  reset must be audited and must never transfer state between students.

## Graduation integration

The final-role promotion gate currently checks a required Week 23 quiz, module completion,
advanced troubleshooting and Microsoft/endpoint packs, and later quizzes. It does not check
the Week 24 lab or any capstone.

Add a future progression evaluator for one exact required practical. The gate payload should
pin at least:

```json
{
  "gate_type": "required_lab",
  "lab_template_id": 22,
  "activity_stable_id": "week-24-guided_lab-22",
  "minimum_score": 80,
  "rubric_version": "integrated-support-v1"
}
```

Eligibility must require a run owned by the same student, for exact template 22, submitted
or verified under the pinned rubric, with authoritative structured feedback and a passing
score. Failed, incomplete, pre-rubric, unrelated, or other-student runs must not count.

`StudentRole` awards are append-only. Do not revoke or demote existing graduates. Learners
who already hold the final role remain grandfathered; the new gate applies only when an
unawarded learner seeks that role.

## Service Desk relationship

Use the Service Desk grading concepts and event-trust boundary, but do not directly reuse
existing tickets. Current packs already teach locked accounts, MFA, desktop, access,
networking, advanced troubleshooting, Microsoft 365, and endpoint cases. Direct reuse would
reward remembered answers and complicate cross-application completion.

Build the three final incidents as workbench-owned variants of the same skill models. Do not
add Phase 4C.3 Service Desk scenarios. The Service Desk application and its authoritative
grading remain unchanged.

## UI flow

1. The existing Week 24 required activity opens on `LabPage` with **Begin Final Shift**.
2. The learner sees the three-ticket queue and submits an initial triage order/reasoning.
3. Selecting a ticket opens its evidence/tools and structured working notes.
4. Returning to the queue preserves server state and displays status without diagnosis hints.
5. After all safe dispositions and verification gates, the learner completes the handoff.
6. Final submission locks the attempt and displays category scores and remediation guidance.

Week 23 lab 21 should be upgraded in place into a light, guided queue rehearsal using the
same conceptual fields. It stays Practice. Week 24 lab 22 becomes Prove.

### Mobile contract (375×812)

- use a single-column queue and full-width controls;
- replace wide tab bars with an incident selector or accessible accordion;
- bound terminal height near 280 px and allow internal scrolling;
- stack evidence, notes, and actions rather than preserving a desktop split pane;
- preserve drafts before navigation and expose clear saved state;
- avoid sticky regions that obscure the current field or submit control;
- assert no horizontal document overflow and visible keyboard focus.

## Proposed migration 0061 (do not create yet)

Suggested revision: `0061_integrated_support_prove`, down-revision
`0060_network_linux_cloud_practical_upgrade`.

Before mutation, validate the complete target set in one preflight:

- exact Week 23 and Week 24 `TrainingWeek` rows;
- exact activities `week-23-guided_lab-21` and `week-24-guided_lab-22`;
- exact `LabTemplate` IDs 21 and 22;
- exact final-role promotion gate row and its expected 0060 payload.

Upgrade in place:

- update lab 21 to the guided mixed-queue Practice contract;
- update lab 22 to the versioned final-shift contract and appropriate duration (target 90
  minutes after usability validation);
- set only the Week 24 activity learning role to `prove`; retain Week 23 as `practice`;
- add the exact versioned required-lab condition to the final-role gate;
- create no curriculum activities and delete no historical rows.

Historical `LabRun` rows remain attached to template 22, but runs without the new rubric
version and authoritative assessment payload cannot satisfy the new gate.

Downgrade must restore the exact frozen 0060 lab/activity/gate definitions and remove only
the gate condition owned by 0061. It must preserve lab IDs, activity IDs/stable IDs, LabRuns,
scores, roles, XP, and all unrelated gate conditions. Freeze the 0061 data definitions in
the migration or a migration-owned immutable module; do not let downgrade behavior drift
with mutable application constants.

## Expected implementation scope

Expected curriculum delta after a future implementation:

- modules: 35 (no change);
- activities: 320 (no change);
- required: 141 (no change);
- optional: 179 (no change);
- Week 23 existing lab remains Practice;
- Week 24 existing lab changes from Practice to Prove, producing expected role totals Learn
  216, Check 38, Practice 22, Troubleshoot 36, and Prove 8.

Likely files:

- `backend/alembic/versions/0061_integrated_support_prove.py`
- `backend/app/services/integrated_support_prove.py`
- `backend/app/routers/labs.py`
- `backend/app/schemas/lab.py`
- `backend/app/services/progression_service.py`
- `backend/app/services/training_curriculum_seed.py`
- `backend/seed.py`
- `backend/seed_curriculum.py`
- `backend/tests/test_phase4c3_integrated_support.py`
- `backend/tests/test_phase4c3_migration.py`
- `backend/tests/test_phase4c3_progression.py`
- `frontend/src/components/FinalSupportShiftWorkbench.jsx`
- `frontend/src/pages/LabPage.jsx`
- `frontend/src/services/api.js`
- `frontend/tests/e2e/phase4c3-integrated-support.spec.js`

No model/schema migration should be added unless implementation proves existing `LabRun`
JSON/text storage cannot provide a safe, queryable versioned contract. Prefer a schema-free
data migration, but do not sacrifice server authority or isolation merely to avoid a table.

## Test matrix

### Backend contract and grading

- correct and incorrect triage orders and required structured factors;
- incidents remain independent and cannot consume each other's evidence/actions;
- evidence must be opened/accepted server-side before dependent decisions count;
- critical unsafe actions are rejected before mutation and fail the attempt;
- scoped actions, escalation, post-action verification, user update, and handoff gates;
- category math, per-incident floor, overall 80% floor, and deterministic reason codes;
- client-supplied transcript, score, status, or evidence IDs cannot forge completion;
- reload/resume returns exact authoritative state;
- submitted attempts are immutable and retries are isolated;
- student A cannot read, mutate, submit, or graduate from student B's attempt;
- exact template/activity/rubric gate passes; failed, incomplete, old-rubric, unrelated, and
  cross-student completions fail;
- historical final-role awards remain valid and are never removed.

### Migration and seed

- pinned 0060 → 0061 → 0060 → 0061 cycle;
- complete preflight fails before any mutation when a target is missing;
- activity/template IDs, stable IDs, LabRuns, XP, quiz/video history, and StudentRole rows
  survive upgrade/downgrade;
- fresh-head install and historical upgrade converge to the same 4C.3 definitions;
- current application code against a 0060 database cannot inject 0061 definitions;
- repeated seed is idempotent and does not reset attempts.

### Frontend and regressions

- desktop and 375×812 queue, incident navigation, evidence, terminal, notes, handoff, failure,
  retry, and reload/resume;
- no diagnosis leaks in title/button/help text and no correct-answer position pattern;
- keyboard focus, labels, saved-state announcement, and no horizontal overflow;
- Phase 4C.1 Windows/AD practical regression;
- Phase 4C.2 network/Linux/cloud practical regression;
- Phase 4B.2 endpoint/Intune progression regression;
- existing Service Desk trusted grading remains unchanged.

## Risks and controls

- **Client trust:** score only accepted server events and server-known state.
- **Memorization:** use new incident variants and rotate answer ordering where choices remain.
- **Overbuilding:** keep one queue, three fixed incidents, and no persistent company model.
- **Historical identity:** mutate templates/activities in place; version new grading payloads.
- **Promotion regression:** add an exact evaluator and grandfather existing awarded roles.
- **Seed divergence:** carry the version gate forward at the future head and keep a permanent
  fresh-versus-historical convergence test.
- **Mobile overload:** design single-column flow before implementing the desktop split view.

## Explicitly deferred

- Persistent Company and the full Maple & Finch implementation;
- multi-VM or automated Proxmox/Guacamole topology;
- dynamic/random ticket generation and background company events;
- real SLA clocks, company economy, CMDB, and asset inventory;
- AI callers, AI grading, and voice simulation;
- backup/domain-controller labs and long-running company state;
- a general certification or orchestration engine.

## Recommendation

**GO to implement Phase 4C.3 later**, after Phase 4C.2 is merged through the normal review
process. Implementation must start from this bounded contract, preserve historical
identities, and pass the migration/seed/graduation trust tests above. Do not implement it as
part of the Phase 4C.2 branch review.
