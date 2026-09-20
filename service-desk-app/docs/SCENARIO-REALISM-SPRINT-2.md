# Service Desk realism — remaining converted tickets

This extends [Sprint 1](SCENARIO-REALISM.md). Repository isolation and the
recoverable pilot/theme shelf are recorded in [the hygiene record](REALISM-SPRINT-2-HYGIENE.md).

## Foundation and authority

The four `realism-v1` fixtures remain byte-for-byte unchanged. Six additional
fixtures live in `packages/shared/src/service-desk-realism-v2.json`, with an
identical packaged backend copy. The frontend catalogue combines both files;
the seed selects v1 for the original four and v2 for the additional six.
The existing content-hash publisher creates a new immutable version when a
definition changes. No seed or migration was run against an operational DB.

Each attempt retains its published definition and its existing grading
semantics. Historical `process-v3` definitions keep their old objective and
escalation profiles; current v2 versions do not use those profiles. Historical
attempt rows and grades are not rewritten. The current browser catalogue has
no wizard. Rollout must finish or retire in-progress historical wizard
attempts before assigning current versions; this sprint does not migrate them
or promise browser replay of retired interactive controls.

The server replays immutable rules against its trusted, ordered event ledger.
Snapshots and client `realismEvidence` fields never become authority. Tool
commands are exact scoped identifiers, not host shell execution. Unknown
commands, arbitrary requester questions and unrelated asset/user targets fail
closed. New scenario state belongs to the assigned machine and attempt.

Existing primitives reused: machine `domainJoinState`, signed-in identity,
credential records, mapped drives, workstation snapshots, ordered evidence,
bounded note facts, hints, workflow phases, limited debrief and escalation
taxonomy. Added scoped state covers Office extensions, cross-port tests,
resource authorization, recurring lockout status and account compromise.
Credential staleness is metadata on the existing credential record, not a
separate client credential store. The simulator retains its diagnostic record
after invalidation; it does not store or expose actual passwords.

## Tools and requester communication

The unified workspace remains the entry point. Command Prompt `help` lists
available support syntax without prescribing an ordered solution. Settings
contains an Excel user-session test surface: original workbook, blank
workbook, Safe Mode, save, extension inspection and individual enable/disable.
These controls invoke the same state transitions as the terminal.

Company Chat has a scoped authored conversation for each new ticket. Questions
cover onset (2502), move context (2503), approval reference and urgency (2506),
timing/devices (2507), password/time/MFA exposure (2508), and another-device
sign-in (2510). Approval, exposure and other-device replies are required
evidence. The existing action transport carries known `Ask-Requester <id>`
commands with the assigned asset; arbitrary free text cannot manufacture a
reply or evidence. The UI displays replies only after asking. No LLM chat or
keyword-based positive confirmation is involved in these grades.

## Decision tables — author/reference material, not pre-completion coaching

| Ticket  | Opening hypotheses                                                                                                         | Supporting / rejecting observations                                                                                                                                                             | Decisive evidence and professional outcome                                                                                                                                                                                   |
| ------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| INC2502 | Corrupt workbook; damaged Office; profile/startup settings; extension conflict                                             | Original workbook crashes; blank workbook opens; same original works in Safe Mode. Repair retains user extensions. Disabling PDF Export leaves the crash.                                       | Disable ReportLink, open original, re-enable ReportLink and reproduce the crash. Disable only ReportLink after isolation, then open/save original normally. A blank test or blanket extension disable is insufficient.       |
| INC2503 | NIC/configuration; cable; DHCP; wall connection; managed port/VLAN                                                         | Link is up but addressing is APIPA; replacement cable does not help; nearby device has normal addressing on B-18.                                                                               | NX-2503 works on B-18 AND NX-2503-peer fails on B-17. This proves port-side scope, not exact switch configuration. Network Support owns the next change. Escalate `other-team-owns-system`; do not claim restored service.   |
| INC2506 | Wrong path/unavailable share; missing membership; authorized request awaiting implementation; unapproved restricted access | Salary share exists/reachable but denies access. Identity/groups and HR Compensation ownership establish scope; requester offers urgency, not an approval reference.                            | Current approval lookup returns none and restricted-data policy requires recorded authorization. Leave access unchanged; Identity & Access obtains owner approval. Executive pressure is not an authorization source.        |
| INC2507 | Stale drive credential; scheduled task; old mobile credential; malicious attempts                                          | Events repeat every 15 minutes from NX-2507 to files.nexus.local; cmdkey entry predates rotation; P: reconnect uses that target. Task query and authored device context eliminate alternatives. | Correlate source/target/timing, invalidate the saved credential, unlock and observe a full interval. No lockout and a fresh successful access check demonstrate control of recurrence.                                       |
| INC2508 | Suspicious email with no exposure; password-only exposure; MFA/session compromise                                          | Requester confirms password AND MFA at 10:05; sign-in activity shows an unfamiliar session; session inspection is independently available.                                                      | Confirm exposure, immediately change credentials and revoke sessions. Old session/token rejection and fresh controlled sign-in verify containment, not complete incident remediation. Information Security owns the handoff. |
| INC2510 | Wrong/expired/locked password; DNS/network outage; local profile problem; computer trust mismatch                          | User works on loaner, account healthy, local support login works, addressing/DNS healthy; secure-channel test fails.                                                                            | Machine `domainJoinState` is trust-broken. Read scoped authorization EP-2510, repair only this secure channel, then test original user's domain sign-in on NX-2510. User password reset cannot repair the machine secret.    |

## Wrong-action semantics

- Rejected: unknown/wrong asset, user, question or command; unsupported domain
  removal/rejoin; invalid secure-channel authorization. No trusted state change.
- Ineffective: Office repair or wrong extension disable; indiscriminate
  extension disable (symptom may disappear but no targeted outcome); unlock or
  password reset with stale credential intact; user password reset for broken
  machine trust. Actions execute but cannot satisfy the required outcome.
- Incomplete containment: credential reset succeeds while old sessions remain
  active. Verification explicitly fails until sessions are revoked.
- Harmful/professionally wrong: restricted Salary grant actually opens access
  without approval and latches critical failure; an attempted switch write
  records an unauthorized operation (the managed device denies the write);
  leaving phishing sessions active through 30 simulated minutes introduces an
  unrecognized forwarding rule and latches the uncontained-exposure failure.
  This is bounded teaching state, not an attacker simulator.

Harmful state is attempt-local and is not erased by a subsequent technically
successful action. A clean retry begins with the immutable initial fixture.

## Time and verification

`Advance-Time 15` advances only this machine's scenario clock, capped at 240
minutes. No calendar, real timer, background worker or production clock exists.
Deterministic rules evaluate after each explicit advance. Lockout repeats if
the stale credential still exists; an unlock resets the observation window.
Phishing risk worsens if an old session remains active past the threshold.
The rule format is reusable for future INC2509 recurrence; the v1 disk case
is deliberately unchanged and still grades stabilization plus handoff.

## Grading and anti-gaming

Weights remain Investigation 15 / Diagnosis 25 / Remediation 30 /
Verification 20 / Documentation 10. There is no rubric change. INC2503 and
INC2506 normalize over the applicable 80 points and explicitly mark
Verification N/A. INC2508 has real containment verification and all five
categories apply. Every handoff requires trusted evidence, the student's
chosen route/reason and the note before it can be trusted.

Pre-change investigation/diagnosis cannot be filled retrospectively.
Post-change verification must occur after the final corrective event and
match current final conditions. Excel's reversible isolation is distinct from
its final targeted remediation; an uninformed initial disable marks an early
change and cannot become a retrospective investigation. Phishing requires
only the short exposure confirmation before containment, not a long sign-in
investigation; optional sign-in inspection may follow containment.

The generic five `scenario.*` actions are rejected for all ten current
fixtures, and `convertedScenario()` is removed from frontend source. Neither
fabricated step IDs, submitted evidence fields, raw untrusted events nor
client snapshots can provide the server's observation evidence. Bounded note
checks require scenario facts but remain coverage checks, not semantic prose
grading. Limited debrief omits the solution, missing-step list, route and
stronger path while graded retries remain. Full debrief uses authored causes,
actions and explanations and distinguishes handoff from local resolution.

## Remaining realism debt

- No converted answer-button scenarios remain in the current catalogue.
- Office is an authored executable state model, not the real Excel binary.
  More workbook/profile controls and event-log detail could deepen isolation.
- Network tests prove the fault follows the port; actual switch config is
  intentionally inaccessible. Cabling topology and DHCP packet traces remain
  possible extensions, not required for the Tier 1 handoff.
- Directory/account, asset and SOP lookups are scoped support commands. The
  broad directory/admin GUIs are not yet fully coupled to every scoped record.
- Requester conversations are short authored choices; follow-up depth,
  notification acknowledgments and richer pressure branches remain backlog.
- Credential invalidation retains diagnostic metadata; future Credential
  Manager UX can distinguish removed records and fuller session refresh.
- Time is explicit, 15-minute and deterministic. INC2509 recurrence and more
  nuanced containment urgency could reuse it later.
- Documentation fact checks can recognize coverage, not negation, causal
  accuracy or useful prose. State/evidence still control the technical pass.
- Preserve historical attempt/version semantics during any later rollout;
  current UI does not resurrect retired wizard controls.
- Eventual shift/queue simulation and broader ticket catalogue are deferred.
- No curriculum YAML was loaded or rewritten; no new catalogue tickets added.

## VM recommendation

Simulation is sufficient for this sprint's judgment and hypothesis-isolation
goals. A future isolated Excel lab could improve binary/add-in fidelity.
INC2510 would materially benefit from a real disposable Windows/AD lab for
secure-channel credentials, restore behavior and sign-in mechanics, but is
not blocked on one. The other cases do not justify VMs at this stage. No VM
was provisioned or enabled.

## Verification record — Sprint 2 implementation before integration cleanup

- Full backend run: **1,013 passed**, 9 dependency/deprecation warnings,
  482.60 seconds. This run was collected before the final ten additional
  raw-event/pre-verification checks were added.
- Final focused backend Service Desk/attempts/escalation/retries/progression/
  workspace suites: **208 passed**, including all **42** new v2 tests and the
  final Excel refinement (blanket disabling permits technical save but does
  not earn targeted-remediation credit).
- Shared **37**, simulation-engine **266**, web **151**, UI **36**: **490
  passed**. The API JS package has no tests. New engine coverage: 44 tests.
- Lint, typecheck, all package builds, Ruff, compileall and diff checks passed.
  Next built 44 pages. No dependencies were changed.
- Dedicated realism browser run: **11 passed** (ten scenarios and authored
  requester-chat isolation). Full available local browser suite: **15 passed,
  7 failed**. The failures are legacy tests for INC2511–2513 and VPN/DNS/
  mapped-drive/spooler workflows: three seek the retired `Resolve / close`
  button, three seek `Student-authored internal note` in the desktop, and one
  asserts `border-sky-300` instead of `border-accent`. Baseline `7b12f94`
  already has the current Resolve label, workspace-only note surface and
  accent border; those UI surfaces were not changed here. The baseline suite
  was not separately executed. Updating those legacy E2E scripts is follow-up
  test debt, not a reason to restore obsolete UI controls.
- The visual tests regenerated four tracked screenshots; only those generated
  differences were restored to HEAD. No user/pilot work was discarded.
- Backend-integrated authenticated browser E2E was unavailable: no disposable
  credentials/configuration were provided. Local browser tests do not prove
  a live authenticated deployment; backend HTTP integration uses SQLite memory.
- JS audit found no known vulnerabilities. Python audit reports existing
  `pip 26.1.2`, `PYSEC-2026-3721`, fixed in 26.2; tooling remediation is separate.
- No deploy, production DB write/migration, V2 enablement, production student
  change, service restart, VM provisioning or merge occurred.

## Integration cleanup — 2026-09-05

The seven previously failing browser tests were classified before their tests
were changed:

| Test                           | Previous expectation                                                        | Current behavior and cause                                                                     | Classification / cleanup                                                                                         |
| ------------------------------ | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| INC2511 account locked         | Button named `Resolve / close`                                              | Unified OutcomeBar names the action `Resolve`; the dialog remains `Resolve or close ticket`    | Obsolete accessible-name selector; use the current button role/name                                              |
| INC2512 password expired       | Same                                                                        | Same                                                                                           | Obsolete accessible-name selector; use the current button role/name                                              |
| INC2513 MFA factor unavailable | Same                                                                        | Same                                                                                           | Obsolete accessible-name selector; use the current button role/name                                              |
| INC2406 VPN/shared drive       | Focused window has `border-sky-300`, then desktop-owned note/close controls | Focus token is `border-accent`; documentation and Resolve live in the unified ticket workspace | Obsolete style selector plus obsolete UI contract; assert visible/interactable window and current workspace flow |
| INC2405 Facilities mapping     | Desktop-owned note textarea and `Close ticket`                              | One editable `ResolutionNotePanel`; Resolve reads it without a textarea                        | Obsolete UI contract; exercise the one-note workspace flow                                                       |
| INC2407 DNS                    | Same                                                                        | Same                                                                                           | Obsolete UI contract; exercise the one-note workspace flow                                                       |
| INC2408 Print Spooler          | Same                                                                        | Same                                                                                           | Obsolete UI contract; exercise the one-note workspace flow                                                       |

Running those corrected flows exposed one genuine integration regression hidden
behind the stale selectors: when no backend workspace view was present, local
fixture mode defaulted every note to `ticket.add_note`. Remote workflows grade
`remote_desktop.add_internal_note`, so Resolve correctly rejected the visible
note. `documentationTargetForTicket` now uses the server target whenever one is
present and otherwise derives remote-desktop scope from the current immutable
scenario workflow. Account tickets continue to use ticket notes. Unit and
browser coverage lock this boundary.

The current Resolve dialog has zero editable textboxes and shows the saved note
read-only. It has no client-side score/pass prediction. The browser tests use
roles, labels and dialog names rather than CSS token assertions.

At realism integration cleanup, theme behavior was inspected without applying
the preserved theme stash: explicit saved choices worked but OS fallback was
still deferred. The later pilot-readiness integration manually adopted only
that small current-compatible fallback: explicit choice, then OS preference,
then dark if preference detection is unavailable.

### Final cleanup verification

- The seven corrected legacy flows pass: **7 passed, 0 failed**.
- The complete local browser suite passes: **23 passed, 0 failed**, including
  the current default-dark and saved-light theme contract. The dedicated
  ten-scenario/requester-isolation browser suite passes: **11 passed, 0
  failed**. A single Connect timeout occurred only while that suite was run
  concurrently with a Next build; its clean serial rerun passed all 11 and is
  classified as environmental, not an unexplained product failure.
- The compact backend catalogue smoke starts each of INC2501–INC2510, confirms
  all five retired `scenario.*` actions are rejected, executes its trusted
  scenario trace, and reaches the intended close or escalation outcome.
- Final focused Service Desk, grading, attempts, escalation, retry, workspace
  and V1 progression suites: **238 passed**. Full backend: **1,033 passed**
  with nine existing dependency/deprecation warnings.
- Shared **37**, simulation-engine **266**, web **152**, and UI **36**:
  **491 passed**. Lint, typecheck, package builds, Ruff, compileall, formatting
  and diff checks passed.
- Browser checks use the local fixture environment. Authenticated browser E2E
  was unavailable because no disposable authenticated credentials were
  configured; no live or production system was contacted.
