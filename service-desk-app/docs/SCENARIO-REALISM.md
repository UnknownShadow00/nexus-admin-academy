# Service Desk realism foundation — first four tickets

This document records Sprint 1. [Sprint 2](SCENARIO-REALISM-SPRINT-2.md)
replaces the remaining six converted workflows and extends this foundation;
its status and backlog supersede the historical deferrals below.

## Architecture and authority

The `realism-v1` catalog replaces the generic converted process for INC2501,
INC2504, INC2505 and INC2509. The other six conversions are unchanged.

`packages/shared/src/service-desk-realism-v1.json` declares each initial fault,
supported support-shell operations, observable outputs, guarded transitions,
evidence categories, final-state conditions, authored hints and completion
explanations. The identical packaged copy in `backend/app/data` allows a
backend-only container to seed without depending on the frontend checkout.
A regression test compares the copies. Changes to an already-published
fixture must introduce another catalog revision, not edit historical records.

The seed function embeds the complete fixture in a new immutable scenario
version, included in its content hash. It does not edit existing versions or
attempts. `process-v3` remains the historical grading catalog, including its
old converted rules. No migration or publication was run against a live DB.

The TypeScript interpreter renders local workstation operations. The Python
interpreter independently replays the same versioned fixture from successful
trusted ledger events before accepting a transition. The action endpoint
removes any browser-authored `realismEvidence` field and derives it itself.
Snapshots remain resume data, never grading evidence. Wrong-device commands,
unsupported targets and all five old `scenario.*` controls are rejected for
the new version. Ordinary navigation remains auditable without earning facts.

This is a bounded support-shell simulation, not a PowerShell runtime. `help`
lists available syntax. Commands never execute on the host. Printer properties
in Settings invoke the same commands as Terminal. Explorer reads the machine
filesystem, and storage figures in Settings and Explorer use the workstation
storage state. Services and terminal service inspection share service state.
Directory comparisons and approvals currently use the support shell; the
general Directory GUI is not a second source for this ticket's access grant.

Existing `machine.profileState` and filesystem `sizeBytes` are reused. Existing
domain trust state is untouched. The added fixture service facts cover printer
destination/queue, scoped directory membership/session access, profile recovery
protection, and capacity/configuration/history. There is no VM or separate
case-answer panel.

## Evidence and professional outcomes

The rubric remains Investigation 15, Diagnosis 25, Remediation 30,
Verification 20, Documentation 10. All five categories must be met for these
new versions. Observation evidence cannot be earned after the first repair;
verification requires a repair and must still agree with final machine state.
Repeating an observation after a guessed repair cannot backfill investigation.

Operations distinguish:

| Kind | Examples | State and grade |
| --- | --- | --- |
| Rejected | Wrong user/device, unapproved profile removal, Tier 1 retention change | No simulated mutation or trusted evidence |
| Ineffective success | Restart healthy spooler; clear Temp | Operation succeeds; root fault and missing repair evidence remain |
| Harmful success | Add All-Departments-RW | Fresh session can open the share; persistent policy breach prevents passing and becomes critical failure |

Profile removal is refused rather than simulating irreversible data loss.
Backup is checksum-verified before profile mapping reset. Broad membership is
a deliberately successful policy violation, not a failed network operation.

Each fixture defines small case-specific note fact groups. These check coverage
of values/paths, action and retest, with a few alternatives. They do not assess
negation or the overall meaning of prose, and are not a global regex grader.
Technical evidence is still mandatory even if a student copies a plausible note.

Full debriefs explain the decisive evidence, remedy, tempting wrong action and
authority boundary. Failed attempts with retries retain the existing limited
coaching policy: no full cause/remedy or correct destination is returned.

## INC2504 — printing from one computer

Before: healthy cloned workstation and five answer-shaped actions.
After: printer online at 10.26.19.94, local port at 10.26.19.80, spooler running,
driver present and jobs queued. Requester describes yesterday's working print
and today's stuck jobs without asserting peer results or a diagnosis.

| Opening hypothesis | Supporting or rejecting evidence |
| --- | --- |
| Spooler stopped | Services / `sc query` shows running; restart succeeds but jobs remain queued |
| Driver failure | Installed PCL6 driver is visible; changing only the destination restores printing |
| Printer offline | Old destination times out, but the asset's current address answers |
| Shared print service | Asset record identifies a direct TCP/IP connection |
| Stale local destination | Local port differs from the reachable current address; this explains all observations |

Student compares port and asset, tests both addresses, saves the current address,
then sends a test page. Post-change completion drains the queue. Restoring the
old destination invalidates final verification. Note covers both addresses,
port change and test-page result. No escalation is required.

## INC2505 — department access

Before: declared missing membership with a generic repair button.
After: a reachable Marketing share returns Access denied for Taylor Reed's
fresh session. Jamie Chen is an authorized peer. The recorded Marketing owner
approval names Marketing-Share-RW and permits Tier 1 to apply that membership.

| Opening hypothesis | Supporting or rejecting evidence |
| --- | --- |
| Bad path, unavailable share or network | The server and share exist; the result is Access denied, not path-not-found |
| Stale credentials/session | A new session alone still fails before membership changes |
| Missing departmental membership | Peer has Marketing-Share-RW; requester lacks it; owner approval confirms scope |
| Broader group would work | All-Departments-RW technically works, but covers unrelated resources and violates approval |

The decisive comparison includes requester groups, authorized peer groups,
approval and group scope. Correct remediation applies only Marketing-Share-RW;
a new requester session and share open are required. Overbroad access cannot
be converted into a pass by subsequently adding the correct group. Note names
Marketing, group/membership action and access retest.

## INC2501 — missing Desktop and Documents

Before: temporary-profile answer supplied by title and five controls.
After: Morgan's correct account is signed into C:\Users\TEMP. The original
profile at C:\Users\morgan.ellis contains Desktop and Documents data.

| Opening hypothesis | Supporting or rejecting evidence |
| --- | --- |
| Wrong signed-in account | `whoami` identifies Morgan |
| Actual deletion | Explorer and directory listings find original files in both folders |
| Redirected-folder/sync outage | Data remains local; profile path and profile-service event explain the empty current view |
| Temporary profile | USERPROFILE points at TEMP and event 1511 corroborates the profile-service failure |

The student must find both original data folders before creating a verified
recovery copy. Mapping reset requires that protection and profile evidence.
A new sign-in restores normal profile state and path; both original folders
must be checked afterwards. Destructive profile removal is outside the safe
procedure and is refused. The note covers TEMP, original location, preservation,
mapping/profile work, Desktop and Documents.

## INC2509 — recurring disk pressure

Before: declared runaway logs with Tier 1 silently changing retention.
After: a 256 GiB drive has 2 GiB free, Temp uses 2 GiB, Downloads 8 GiB and
NexusAgent logs 182 GiB. Historical samples show logs at 80, 140 and 182 GiB.

| Opening hypothesis | Supporting or rejecting evidence |
| --- | --- |
| Downloads | Moderate size, insufficient to explain the historical growth |
| Temp/update cache | Cleanup frees a small amount; application growth remains |
| Crash/sync storage | The size report locates the dominant application path |
| Application logging | Growth samples and debug/unbounded configuration identify the recurring source |

Tier 1 reviews policy, archives closed logs while retaining active data, verifies
headroom and escalates to Application Support using change-approval-required
or other-team-owns-system. A self-service close cannot pass. The note includes
capacity, NexusAgent/log path or source, archive and owning-team hand-off.

This verifies stabilization, not durable recurrence prevention. Simulated time
and an approved receiving-team retention change are deferred. No claim is made
that the application stops growing after the Tier 1 archive.

## Deliberate limits and remaining backlog

- INC2502: Office add-in reproduction, Safe Mode and controlled add-in isolation.
- INC2503: switch/VLAN evidence and Network Support escalation.
- INC2506: restricted data and realistic requester pressure.
- INC2507: recurring lockout and stale credential source.
- INC2508: actual phishing containment and security escalation.
- INC2510: domain trust evidence and approved computer-account recovery.
- Requester conversation depth: Company Chat currently uses generic keyword
  replies, including an unconditional fresh-session success message. It cannot
  prove a useful diagnostic exchange without a scenario/state-aware extension;
  these four do not grade those replies. No decorative chat requirement added.
- Simulated time: add bounded time advancement and growth/retention calculations
  before claiming durable disk verification.
- Note assessment: extend beyond fact coverage only with tested, bounded rules;
  copied facts and negated claims are not semantically evaluated today.
- Bridge the generic Directory and Asset Management panels to these scoped
  fixture facts; current authoritative investigation is available in Terminal
  and printer Settings, not a new standalone mini-app.
- Eventual shift/queue simulation with interruptions and competing priorities.
- Historical in-progress UI compatibility: grading remains tied to old versions;
  deployment planning must handle legacy active attempts before switching the
  browser fixture catalog. This sprint does not cut over or migrate them.

## VM assessment

Simulation is sufficient for the current reasoning targets of all four tickets.
A hybrid Windows environment could later improve printer-driver/property fidelity,
AD token refresh and profile event/registry realism. A real Windows VM is most
useful eventually for advanced profile recovery, not required for this sprint.
Disk growth/time can be added to the simulator without a VM.

## Verification record

Full backend: 1,010 passed, including Service Desk, grading and progression.
Focused final realism/workspace run: 40 passed, including 30 new realism tests.
Shared package: 37; simulation engine: 222; web: 151; UI: 36 — all 446 passed.
Four local Playwright scenarios passed through workstation commands and reload.
These browser checks use the local simulator, not an authenticated production
student or a backend-integrated browser session.

Lint, typecheck, all package builds, Ruff and compileall passed. npm audit found
no known vulnerabilities. The environment's pip 26.1.2 has PYSEC-2026-3721
(fixed in 26.2); no project dependency changed. Production deployment, DB writes,
migrations, student changes, V2 enablement and merging were not performed.
