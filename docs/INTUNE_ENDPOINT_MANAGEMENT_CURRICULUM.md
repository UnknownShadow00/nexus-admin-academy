# Intune & Windows 11 Endpoint Management Curriculum (Phase 4B.2)

Status: Phase 4B.2 built on `feature/intune-endpoint-management`, not
merged, not deployed. Extends the existing `stage.microsoft_workplace`
Stage ("Microsoft 365, Entra & Endpoint Management") with the
Intune/Autopilot/device-lifecycle/MDM content that Phase 4B.1 explicitly
deferred. See `docs/MICROSOFT_WORKPLACE_CURRICULUM.md` for that earlier
slice.

## Scope

Five modules, new `week_number` 30-34 (existing 0-29 never renumbered):

1. **Intune & Managed Endpoint Foundations** (week 30) -- what Intune/MDM
   management means for a Windows device; Entra registered vs. joined vs.
   hybrid joined; reading a device record to determine join type,
   management state, and likely ownership before touching anything.
2. **Windows Enrollment & Autopilot** (week 31) -- automatic MDM enrollment
   and BYOD/Company Portal enrollment; Windows Autopilot vs. Autopilot
   Device Preparation; diagnosing a device that is Entra joined but not
   Intune managed.
3. **Policies, Compliance & Applications** (week 32) -- configuration
   policy vs. compliance policy; the device-state -> compliance ->
   Conditional Access -> access chain; diagnosing a failed application
   install using detection-rule evidence.
4. **Windows 11 Endpoint Troubleshooting & BitLocker** (week 33) -- Windows
   Update/driver/firmware triage; BitLocker recovery handled safely, with
   identity verification first; choosing the correctly-scoped device
   action for a given risk level. This module's quiz is the graduation
   gate quiz for this content slice.
5. **Device Lifecycle, Onboarding, Offboarding & Mobile** (week 34) --
   running a device through its full lifecycle; completing the device/M365
   side of a new-hire onboarding; offboarding a device safely without
   leaving open access; basic mobile MDM concepts and the safe
   retire-vs-wipe decision. Mobile stays folded in here rather than
   becoming a sixth module (see "Why five modules, not six" below).

## Why five modules, not six

The research checkpoint's draft module structure included a candidate
sixth Mobile/MDM module. The user's explicit approval decision rejected
this: the Minnesota job-market evidence supports mobile device support as
a real but secondary skill relative to Intune, Windows deployment,
policies, and device lifecycle -- not equal in weight to any of those.
Mobile/MDM content (concepts tour, lost/wiped-device decision) instead
sits at Recognize/light Working Knowledge depth inside Module 5 (week 34),
alongside offboarding, as one lesson ("Offboarding Safely, and Mobile
Device Basics") and one troubleshoot-role guided lab ("Lost Phone: Retire
or Wipe"). This keeps mobile coverage real without inflating it into a
standalone module the market evidence doesn't justify.

## Service Desk scenarios: why only two are live

The user's build authorization was explicit: only BitLocker recovery and
offboarding device reassignment should become live, server-graded Service
Desk tickets. Everything else in this phase is a guided/simulated
troubleshooting activity. This mirrors -- and is a direct continuation of
-- the same reasoning Phase 4B.1 already applied (see
`docs/MICROSOFT_WORKPLACE_CURRICULUM.md`'s "Why Level A stopped at two
tickets, not seven"): a Service Desk ticket should only be built as live
and server-graded when the grading engine can actually verify the
student's evidence, not merely accept a self-reported "success" flag.

Enrollment failures, Autopilot deployment problems, compliance/policy
propagation, application install failures, Windows Update/driver triage,
device lifecycle, onboarding, and mobile retire-vs-wipe decisions all
became `guided_lab` evidence-interpretation exercises (`practice`,
`troubleshoot`, or `prove` role per activity, matching the existing
Nexus pattern) instead of live tickets, because simulating and correctly
grading real Intune device state (enrollment status, policy propagation,
detection-rule evaluation, compliance timing) is a materially larger
platform-engineering problem than this phase's scope allowed.

BitLocker recovery and offboarding device reassignment were selected as
the two live scenarios because:

- Both map cleanly onto a small, closed set of verifiable facts (device
  identity, requester identity, a single diagnosis, a single high-impact
  action, a single post-action verification check) -- the same shape the
  existing `_account_process()` factory already grades successfully for
  `locked-user-account`/`password-reset`/`mfa-reset`.
- Both are genuinely safety-critical support tasks (disclosing a
  BitLocker recovery key, or reassigning/wiping a device, to the wrong
  person is a real-world incident), so grading identity-verification-first
  behavior has direct job-readiness value.
- Both appear as named, high-priority gaps in the original job-market
  research (BitLocker was previously only a one-line warning with no real
  coverage anywhere in the curriculum -- see the correction now recorded
  in `docs/JOB_READY_CURRICULUM_BLUEPRINT.md` section 10).

## Minimal grading vocabulary added -- explicitly not a simulator rewrite

The build authorization was explicit that Phase 4B.2 must **not** become a
general-purpose Intune simulator/grading engine rewrite, and must add only
the minimum trusted-event/evidence vocabulary the two approved live
scenarios need.

What was actually added, in full:

- A new `_device_process()` factory in
  `backend/app/services/service_desk_objectives.py` (`app/services/
  service_desk_objectives.py:795`), which produces the same five-category
  `ScenarioObjectiveDefinition` shape (investigation / diagnosis /
  remediation / verification / documentation) the existing
  `_account_process()` factory already uses. It reuses
  `chat.verify_identity`, `chat.request_resolution_confirmation`, and
  `ticket.add_note` verbatim -- no new chat/ticket vocabulary was needed.
- Three new generic device evidence actions: `device.inspect_record`,
  `device.record_diagnosis`, `device.verify_access`.
- One caller-supplied remediation `EvidenceRule` per scenario:
  `device.reveal_recovery_key` (BitLocker) and `device.reassign_device`
  (offboarding) -- the only scenario-specific vocabulary added.
- A `"device.": "device"` entry in `_EVENT_PREFIX_TOOLS` plus the shared
  `deviceId` boundary check, so malformed device events fail before they can
  enter the trusted transition graph.
- `"bitlocker-recovery"` and `"offboarding-device-reassignment"` added to
  the existing `ordered_workflows` set (`app/routers/service_desk.py:745`)
  -- this is a *generic* category-prerequisite-ordering mechanism already
  used by every other live scenario; adding these two keys required no new
  ordering logic.

No new grading primitives, no forbidden-action mechanism, no new
persistence model, and no changes to the trust/verification architecture
were introduced. This is deliberately the smallest change that lets these
two specific scenarios be graded honestly.

## Windows 10 policy

Windows 10 is treated as end-of-support hardware/software throughout this
phase's content, not as a currently-supported parallel OS. Lessons
reference Windows 11 as the baseline managed endpoint OS; Windows 10 is
mentioned only where relevant to the real support scenario of migrating a
still-in-service Windows 10 device onto Windows 11/Intune management, not
as an alternative platform to teach in parallel.

## Autopilot vs. Autopilot Device Preparation

Both are taught, deliberately, rather than covering only classic
Autopilot. Week 31's "Windows Autopilot vs Autopilot Device Preparation"
lesson and the guided lab "Autopilot Deployment Stuck" cover classic
Autopilot (profile-based, longer-established, still the dominant
enterprise deployment path documented in real job listings) alongside
Autopilot Device Preparation (Microsoft's newer, Entra-joined-first
provisioning flow) as two current options a technician needs to
recognize and distinguish, not as an Autopilot-only curriculum with
Device Preparation omitted.

## Microsoft source freshness

Verified: 2026-08-23. Researched via Microsoft Learn and current Intune/
Windows 11/Autopilot documentation as of the research checkpoint.

**Volatile areas flagged for re-verification on a future pass:**

- **Windows 10 end-of-support**: dates and any extended-support-program
  details should be re-confirmed if this content is reused significantly
  past its original authoring window.
- **Autopilot vs. Autopilot Device Preparation**: this is an actively
  evolving area of Microsoft's provisioning story; the relative
  positioning, feature parity, and Microsoft's own recommended default may
  shift. Re-check before treating either as the "recommended path" without
  re-verifying against current Learn docs.
- **Company Portal / Microsoft Intune app platform split**: Company Portal
  remains current across supported platforms, while some Android scenarios
  use the separate Microsoft Intune app. This is an area Microsoft continues
  to change;
  content here is intentionally kept at Recognize depth and phrased around
  concepts (device compliance, retire vs. wipe) rather than exact app
  names/UI paths, to reduce the blast radius of this kind of drift.
- **General click-paths**: as with Phase 4B.1, lesson content is written
  around what a technician is trying to determine and where the evidence
  lives, not click-by-click admin-center UI paths, so minor Microsoft UI
  changes should not by themselves invalidate this content.

## Depth classification

**MUST PERFORM**: read a device record and determine join type/management
state/ownership; diagnose a device that is Entra joined but not Intune
managed; distinguish configuration policy from compliance policy; trace
the device-state -> compliance -> Conditional Access -> access chain;
diagnose a failed application install from detection-rule evidence; triage
common Windows Update/driver problems; verify identity before any
BitLocker recovery-key disclosure; choose the correctly-scoped device
action for a given risk level; complete the device/M365 side of a new-hire
onboarding; offboard a device without leaving open access.

**WORKING KNOWLEDGE**: automatic vs. BYOD/Company Portal enrollment;
Windows Autopilot vs. Autopilot Device Preparation at a conceptual level;
the device lifecycle end to end.

**RECOGNIZE only, intentionally excluded from deeper depth**: mobile MDM
management beyond the retire-vs-wipe decision; advanced Intune scripting/
Graph automation; co-management with legacy Configuration Manager;
advanced compliance/eDiscovery on managed devices. None of these were
added -- this documents what was deliberately left out.

## Practical training strategy

- **Level A -- live Nexus simulation** (server-graded): the two device
  tickets, using the minimal `device.*` vocabulary described above and the
  focused Service Desk Device Management tool. The tool exposes only the
  evidence/actions those two tickets require; it is not an Intune tenant
  simulator or a general device-administration engine.
- **Level B -- guided evidence-interpretation exercises**: everything
  else -- enrollment/Autopilot diagnosis, policy/compliance/app-deployment
  tracing, Windows Update/driver triage, device lifecycle, onboarding, and
  the mobile retire-vs-wipe decision -- via the same question-based
  `guided_lab` mechanism already proven in Phase 4B.1, with an explicit
  `role` (`practice`, `troubleshoot`, or `prove`) per activity so labs are
  not uniformly labeled `troubleshoot` regardless of what they actually
  ask the student to do.
- **Level C -- real tenant exercises**: not built, same rationale as
  Phase 4B.1 (no live/licensed Microsoft 365 tenant assumed for this
  platform).

## Service Desk scenarios

| stable_key | Type | Week | Root skill |
|---|---|---|---|
| `bitlocker-recovery` | Live ticket | 33 | Verify requester identity before disclosing a BitLocker recovery key; never disclose first. |
| `offboarding-device-reassignment` | Live ticket | 34 | Confirm the correct device (a decoy device is present in the ticket data) and reassign/reset only after diagnosis and verification, not on request alone. |
| Diagnose Join, Management & Ownership | Guided lab (troubleshoot) | 30 | Read device-record evidence to determine why a device isn't managed as expected. |
| Autopilot Deployment Stuck | Guided lab (troubleshoot) | 31 | Distinguish an Autopilot profile problem from a Device Preparation problem. |
| The App That Says It Failed | Guided lab (troubleshoot) | 32 | Use detection-rule evidence to find the real cause of an app-install failure. |
| Blocked and Stuck: Compliance Meets a Pending Profile | Guided lab (troubleshoot) | 32 | Trace a Conditional Access block back through a pending compliance/configuration state. |
| Diagnose the Multi-Signal Ticket | Guided lab (prove) | 32 | Integrated policy/compliance/app diagnosis across multiple simultaneous signals. |
| Choose the Right Device Action | Guided lab (troubleshoot) | 33 | Weigh device-action risk (reboot/sync/retire/wipe/etc.) against the situation before acting. |
| Lost Phone: Retire or Wipe | Guided lab (troubleshoot) | 34 | Safe retire-vs-wipe decision for a lost/stolen mobile device. |

The `endpoint-management` `ServiceDeskPack` (`service_desk_progression.py`)
covers the two live tickets (`required_week=34`, `required_prior_passes=2`).
The week-33 BitLocker case unlocks one week earlier through its exact required
curriculum activity; the week-34 pack boundary prevents the offboarding case
from bypassing its own safety lesson.

## Safety and destructive-action model

- **BitLocker recovery**: the critical failure mode this scenario grades
  against is disclosing the recovery key *before* verifying the
  requester's identity. `_device_process()`'s category ordering
  (investigation -> diagnosis -> remediation -> verification ->
  documentation), enforced generically via `ordered_workflows`, makes an
  early `device.reveal_recovery_key` action rejected -- the same
  enforcement mechanism `locked-user-account`/`password-reset` already
  rely on, not new logic written for this scenario.
- **Offboarding device reassignment**: the ticket data includes a decoy
  device (a second, similarly-named device not belonging to the
  offboarding employee) specifically so that reassigning/resetting the
  wrong device is rejected. The diagnosis also records that authorization,
  access revocation, and data-reset handling have been established before
  reassignment -- tested directly by
  `test_endpoint_scenario_rejects_critical_action_against_decoy_device` in
  `backend/tests/test_phase4b2_endpoint_service_desk_scenarios.py`.
- **Guided-lab device actions**: "Choose the Right Device Action" (week 33)
  is built specifically to teach that not every device problem calls for
  the most drastic available action (e.g. a full wipe when a sync/restart
  would resolve it), reinforcing the same risk-weighing discipline the
  live tickets grade.

## Progression

**System A** (`TrainingWeek.display_order`): the five new weeks get
`display_order` 18-22, sitting immediately after the Phase 4B.1 M365
content (13-17). The 12 existing weeks previously at `display_order`
18-29 shift to 23-34 (`_INTUNE_DISPLAY_ORDER_SHIFT`); `week_number` is
never touched on any existing row.

**System B** (`progression_service.py` / `service_desk_progression.py`):

1. `MODULE_WEEKS` extended with `MOD-030`..`MOD-034` -> 30-34.
   `derive_current_week`'s dynamic `range(max(MODULE_WEEKS.values()) + 1)`
   (already generalized by Phase 4B.1) required no further change.
2. `PromotionGate` rows for the graduating role (`Junior Infrastructure
   Administrator`, rank 6) extended:
   - `min_completed_lessons.module_codes` += `MOD-030`..`MOD-034`.
   - a third `required_quiz` gate row, `{"week": 33}` (the Windows 11
     Endpoint Troubleshooting & BitLocker module's quiz), alongside the
     existing `{"week": 23}` and `{"week": 27}` rows.
   - a `min_service_desk_passes` gate row, `{"pack_key":
     "endpoint-management", "min_passed": 2}`.

   As with Phase 4B.1, this gate step is what actually prevents a student
   from graduating without touching this content -- the `MODULE_WEEKS`/
   range extension alone only makes the content reachable, it does not
   require it.

## Existing students

Same `StudentRole`-is-a-permanent-award-record reasoning as Phase 4B.1
applies unchanged:

- Students not yet graduated see the new weeks appear in their Learning
  Path at their System A position, and their System B sequential position
  naturally extends into weeks 30-34 once they clear the rest of the
  numbered curriculum -- no regression, no rollback.
- Already-graduated students' `StudentRole` grants are untouched; the new
  content appears in their Learning Path as optional refresher material,
  same as Phase 4B.1's M365 content does for them.

## Curriculum counts

| | Before (post-4B.1) | After (post-4B.2) |
|---|---|---|
| Total activities | 288 | 320 |
| Weeks | 30 | 35 |
| Modules | 30 | 35 |
| Lessons (new) | -- | 12 |
| Quizzes (new) | -- | 5 (23 questions) |
| Guided labs (new) | -- | 13 |
| Live Service Desk tickets (new) | -- | 2 |

Unlike Phase 4B.1, nothing existing is moved or relocated in this phase --
every new row is newly created content, since Weeks 30-34 did not exist
before.

## Migration and downgrade blast radius

Migration `0058_intune_endpoint_management` is schema-free and changes only
seeded curriculum/progression data. Upgrade creates weeks 30-34 and their 32
activities, five legacy modules and their lesson/quiz/lab records, the two
endpoint scenarios and published versions, three graduation-gate additions,
and shifts only `TrainingWeek.display_order` for the 12 later modules. Existing
`week_number` values 0-29 and existing student awards are not rewritten.

Downgrade removes those Phase 4B.2 rows, restores the 12 display orders and
the pre-Phase gate definitions, and returns the active curriculum to 30 weeks
and 288 activities. Because the two scenarios do not exist at revision 0057,
downgrade also deletes assignments, attempts, trusted/untrusted events, and
grades belonging specifically to `bitlocker-recovery` and
`offboarding-device-reassignment`, in foreign-key-safe order. It does not
delete other Service Desk history or any `StudentRole`/current-role award.
This deliberate data-loss boundary is covered by the downgrade/re-upgrade
regression test and must be called out before anyone authorizes a downgrade.

## Files changed

- `backend/app/services/curriculum_structure.py` -- 5 new
  `ModuleDefinition` rows under `stage.microsoft_workplace`; Stage
  description updated to remove the "planned for Phase 4B.2" placeholder.
- `backend/app/services/progression_service.py` -- `MODULE_WEEKS`
  extended with `MOD-030`..`MOD-034`.
- `backend/app/services/service_desk_progression.py` -- new
  `endpoint-management` `ServiceDeskPack`.
- `backend/app/services/service_desk_objectives.py` -- new
  `_device_process()` factory; two new `SCENARIO_OBJECTIVES` entries
  (`bitlocker-recovery`, `offboarding-device-reassignment`).
- `backend/app/routers/service_desk.py` -- `"device.": "device"` added to
  `_EVENT_PREFIX_TOOLS`; the two new stable_keys added to
  `ordered_workflows`.
- `backend/app/services/training_curriculum_seed.py` -- new
  `sync_intune_endpoint_management`, `_INTUNE_*` content constants.
- `backend/seed_curriculum.py` -- wires in the new sync call.
- `backend/alembic/versions/0058_intune_endpoint_management.py` -- new
  migration (schema-free; pure data), with a full downgrade.
- `backend/tests/test_service_desk_attempts.py` -- `_tool_for()` helper
  extended with a `"device."` branch.
- `backend/tests/test_phase4b2_endpoint_service_desk_scenarios.py` -- new
  API-driven grading, safety, isolation, replay, decoy-target, and boundary
  validation tests for the two live scenarios.
- `backend/tests/test_gate5_endpoint_management_bridge.py` -- verifies the
  future-graduation bridge and exact two-scenario endpoint pack.
- `backend/tests/test_training_service.py`,
  `backend/tests/test_orientation_seed.py` -- updated hardcoded
  curriculum-count assumptions (35 weeks, 320 activities); the two
  fresh-vs-upgraded-historical convergence regression tests were also
  updated to pin explicit migration revisions instead of the floating
  `head`, so they remain valid forever regardless of future migrations
  (see the in-file comments on `_POST_PHASE_4B1_COMMIT`).
- `docs/JOB_READY_CURRICULUM_BLUEPRINT.md` -- corrected the inaccurate
  claim that BitLocker coverage "already existed" in `endpoint_security`.
- `service-desk-app/` -- adds the narrow Device Management tool, two
  endpoint authorization contacts, trusted device-action synchronization,
  and focused unit coverage so both live cases are playable in the browser.
- `frontend/tests/e2e/service-desk-integration.spec.js` and
  `scripts/e2e/start_local_stack.sh` -- exercise both endpoint cases through
  the actual browser UI against an isolated disposable stack and assert the
  authoritative API returns 100/pass for each.
- `frontend/tests/e2e/my-training.spec.js` -- updates the curriculum-structure
  browser assertion from 30 to 35 storage weeks.
- `.github/workflows/ci.yml` -- updates the curriculum validation gate to the
  post-4B.2 totals.
- `docs/INTUNE_ENDPOINT_MANAGEMENT_CURRICULUM.md` -- this document.

## Technical debt / follow-ups

- Enrollment, Autopilot, policy/compliance, application deployment, and
  device lifecycle remain guided-lab reasoning exercises rather than live
  server-graded tickets. Making them live would require real Intune
  device-state simulation and grading -- deliberately out of scope for
  this phase (see "Service Desk scenarios: why only two are live" above).
- No real Microsoft Intune/tenant integration exists (Level C, deferred by
  design, same as Phase 4B.1).
- Mobile MDM coverage stays intentionally shallow (Recognize/light Working
  Knowledge) per the approved module-structure decision; if job-market
  evidence later shows mobile support growing in relative importance, a
  dedicated module would be the natural next step, not an expansion of
  Module 5 in place.
