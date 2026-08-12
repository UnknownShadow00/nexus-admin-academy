# Service Desk Workstation Realism Audit

Date: 2026-08-12  
Branch baseline: `agent/student-experience-progression` at `a4dd42a784b48c250653131eb2f134192087acec`  
Implementation branch: `agent/service-desk-workstation-realism`

## Executive finding

The Service Desk is already a deterministic, server-graded simulator, not a set of static mockups. Its strongest foundations are immutable scenario versions, a trusted server event ledger, resumable snapshots, mode-aware hints, and a ticket process rubric. The realism gap is concentrated in the workstation layer: several apps display plausible information, but the information is not backed by one coherent machine model, and some high-value repairs are still one-click shortcuts.

The safe path is an in-place evolution. Preserve the attempt, event, snapshot, grading, progression, and ticket-shell contracts; replace the flat remote-desktop overlay with a versioned shared workstation state; route every app and command through deterministic selectors and mutations over that state; and split the oversized UI and reducer files into independently testable modules.

## Baseline and delivery constraints

- PR #15 is open, draft, green, and based on `main`; its head is the required release-candidate commit.
- This work is stacked from that exact commit and must target `agent/student-experience-progression`.
- Production, deployment configuration, and the parent branch are out of scope.
- Existing attempts, grades, assignments, snapshots, scenario versions, ticket history, and curriculum data must remain readable.
- Browser-provided events and snapshots are untrusted. Only server-reconstructed actions may become grading evidence.
- The five Phase 1 representative tickets are the real catalog entries, not new guessed scenarios:

| Workflow | Ticket | Stable key | Current primary surface |
|---|---|---|---|
| Locked account | INC2511 | `locked-user-account` | Directory |
| Password reset | INC2512 | `password-reset` | Directory |
| MFA reset | INC2513 | `mfa-reset` | Directory |
| File-share access | INC2405 | `inc2405` | Remote Desktop, Directory, Company Chat |
| VPN/network | INC2406 | `inc2406` | Remote Desktop |

## Current architecture

### Trusted attempt lifecycle

1. The browser starts an attempt pinned to a published scenario version.
2. The local simulation engine applies an action immediately for responsive interaction.
3. `TicketSessionProvider` queues the action plus a serialized resulting snapshot.
4. The server validates the action, reconstructs trusted objective events, and stores the browser snapshot only as resumable current state.
5. Closing a ticket asks the server to grade the trusted ledger; the browser's close payload is not accepted as resolution evidence.
6. Attempts, grades, event sequences, and version pins are retained for replay and audit.

This boundary is correct and must remain intact. A richer workstation does not justify trusting raw terminal text, UI flags, or snapshot fields.

### Main implementation pressure points

| Area | Current shape | Risk |
|---|---:|---|
| `RemoteDesktopTool.tsx` | 2,739 lines | Desktop shell, window chrome, every app, scenario controls, and learning UI are coupled. |
| `TicketSessionProvider.tsx` | 2,481 lines | Session orchestration, local reducer calls, persistence, API sync, and every tool command are coupled. |
| `remote-desktop-fixtures.ts` | 1,185 lines | Workstation facts, scenario descriptions, outputs, and presentation data are interleaved. |
| `simulation-engine/apply-action.ts` | 3,300 lines | Validation and mutation for all simulator domains share one switch. |
| `RemoteDesktopOverlay` | flat mutable fields | Apps cannot reliably observe the same network, filesystem, credential, service, and VPN facts. |

### Existing workstation capabilities worth preserving

- A Windows-inspired desktop, taskbar, start menu, login/connection states, desktop icons, focus, minimize, and close behavior.
- Scenario-specific workstations, services, drives, Explorer entries, terminal outputs, VPN logs, browser/chat/mail content, updates, and power/network controls.
- Guided, Practice, and Assessment selections with progressively reduced hints.
- Phase-aware workflows for several mature scenarios: investigate, diagnose, fix, verify, document, close.
- Per-workstation serialized state and backward-compatible snapshot deserialization.
- Deterministic terminal output rather than arbitrary shell execution.

## Scenario inventory

### Workstation scenarios

| Ticket | Stable key / profile | Primary diagnosis or workflow | Current maturity |
|---|---|---|---|
| INC2401 | `profile-storage` | Finance portal/profile storage | Generic scenario-step controls |
| INC2402 | `network-configuration` | Warehouse wireless/network config | Generic scenario-step controls |
| INC2403 | `pdf-export-update` | PDF export/update/disk condition | Generic scenario-step controls |
| INC2405 | `facilities-calendar-mapping` | Facilities access/share mapping | Explorer reconnect shortcut |
| INC2406 | `vpn-shared-drive` | VPN compliance/shared drive | VPN connect automatically restores drives |
| INC2407 | `dns-configuration-failure` | DNS configuration | Phase-aware, command-supported |
| INC2408 | `service-failure` | Print Spooler | Phase-aware, Services/terminal-supported |
| INC2501 | `temporary-windows-profile` | Temporary profile | Mixed app and scenario controls |
| INC2502 | `excel-add-in-isolation` | Excel add-in isolation | Generic scenario-step controls |
| INC2503 | `office-move-network` | Office move/network configuration | Generic scenario-step controls |
| INC2504 | `printer-dhcp-port` | Printer/DHCP port | Generic scenario-step controls |
| INC2505 | `department-share-least-privilege` | Share permissions/least privilege | Generic scenario-step controls |
| INC2506 | `restricted-folder-escalation` | Restricted folder/escalation | Generic scenario-step controls |
| INC2507 | `recurring-lockout-stale-mapping` | Stale mapping/recurring lockout | Generic scenario-step controls |
| INC2508 | `phishing-credential-containment` | Credential containment | Generic scenario-step controls |
| INC2509 | `recurring-disk-growth` | Recurring disk growth | Generic scenario-step controls |
| INC2510 | `domain-trust-repair` | Domain trust repair | Generic scenario-step controls |

### Non-workstation foundational and hardware scenarios

| Ticket | Stable key | Primary tool | Current maturity |
|---|---|---|---|
| INC2511 | `locked-user-account` | Directory | Server-sequenced identity/account workflow |
| INC2512 | `password-reset` | Directory | Server-sequenced identity/account workflow |
| INC2513 | `mfa-reset` | Directory | Server-sequenced identity/account workflow |
| INC2404 | `inc2404` | Asset Management | Guided hardware isolation controls |

BitLocker recovery and new-employee onboarding definitions exist as backend prototypes but are not complete browser-runtime cases. They belong after the five representative workflows and the shared architecture are proven.

## State-model audit

`RemoteDesktopOverlay` currently stores connection status, DNS servers, drive statuses, a current Explorer path/error, app focus/open/minimized lists, power/network flags, learning mode, progress flags, service rows, terminal history, update state, and VPN status/log/error. Static fixture objects separately own most machine, network, filesystem, VPN, and user facts.

The following required concepts are missing or fragmented:

- Machine identity: hostname, OS/build, domain/join state, signed-in user, profile type, compliance state.
- Network interfaces: IPv4/IPv6, prefix, gateway, DNS source, DHCP state/lease, media state, routes, and DNS cache.
- VPN profiles: gateway, tunnel type, authentication method, device-compliance prerequisites, routes, DNS changes, and connection failure reason.
- Filesystem tree: directories, files, UNC roots, permissions, availability, ownership, and stable identifiers.
- Mapped drives: letter, UNC path, reconnect-at-sign-in, credential target, current connection/error, and mapping provenance.
- Stored credentials: target, username, type, persistence, created time, and safe removal; never a stored plaintext secret.
- Application/window state: bounds, z-order, minimized/maximized state, taskbar activation, navigation history, dialog state, and keyboard-safe actions.
- Verification evidence: repeatable observations tied to the original symptom, requester confirmation, selected identity-verification method, and durable ticket notes.

Without those entities, one app can claim a repair while another still renders unrelated fixture data. That is the central realism defect.

## Interaction and workflow audit

### Window manager

Current windows open, focus, minimize, and close. They cannot be dragged, resized, maximized/restored, or reliably layered through a first-class z-order model. Desktop icons and the taskbar work, but the shell is visually and behaviorally shallower than a training workstation.

Required correction:

- Persist controlled bounds and window state per app.
- Support focus/z-order, minimize, maximize/restore, close/reopen, taskbar activation, start menu, and constrained movement.
- Make resizing progressive enhancement. Stable move/focus/maximize is higher priority than fragile resize behavior.
- Provide keyboard-accessible window controls and non-drag alternatives.

### File Explorer and mapped drives

Current Explorer renders fixture-derived drives and entries. A drive reconnect action accepts only a letter and flips its status to connected. It does not require or validate a UNC path, selected letter, reconnect preference, stored credential target, VPN reachability, DNS resolution, or permissions.

Required correction:

- Add a real Map Network Drive dialog with letter, UNC path, reconnect-at-sign-in, optional credential selection, validation, and actionable errors.
- Model navigation tree, address bar, back/forward/up, list/detail rows, status/loading/empty states, disconnected mappings, permission denied, path not found, and name-resolution failure.
- Make GUI mapping and `net use` mutate the same mapped-drive collection.

### VPN

Current VPN has statuses and logs, but clicking Connect can complete after a timer and, for INC2406, automatically marks all network drives connected. That is an explicit one-click magic path.

Required correction:

- Require a configured profile and model internet reachability, gateway resolution, device compliance, authentication, routes, and post-connect DNS state.
- Connect/disconnect must only change VPN/network state. A mapped drive reconnects only when its prerequisites are satisfied and the learner maps or reconnects it.
- Errors must be deterministic and explainable: no profile, offline, DNS failure, noncompliant device, authentication failure, unreachable gateway, or missing route.

### Terminal

The terminal parser currently supports a useful subset: `ipconfig`, `ping`, `nslookup`, `tracert`, `net use` listing, `whoami`, `hostname`, `gpupdate`, `systeminfo`, `tasklist`, `sc query`, `net start`, `net stop`, `cls`, and `help`. Outputs are deterministic and no real shell is invoked, which is a security strength.

Gaps:

- `net use` cannot map or delete drives and is not connected to Explorer state.
- `cmdkey` is absent, so Credential Manager cannot share state with the command line.
- Network command output is largely static rather than computed from interfaces, routes, cache, VPN, and host facts.
- Command history, editing, exact syntax errors, and scrollback need workstation-quality interaction.
- Commands must remain allowlisted and tokenized; no `eval`, `exec`, shell process, arbitrary filesystem access, or network requests.

### Credential Manager

There is no Credential Manager app or credential collection. Stale credential scenarios therefore depend on bespoke buttons rather than a reusable concept.

Required correction:

- Add Windows Credentials-style list/add/remove UI backed by safe metadata-only records.
- Share state with `cmdkey /list`, `cmdkey /add`, and `cmdkey /delete`.
- Never accept, persist, log, snapshot, or replay a real password. Scenario secrets are opaque fixture tokens and must be redacted from student-visible audit data.

### Services

The Services app and `sc query`/`net start`/`net stop` already share enough concepts to prove the pattern, but presentation and state belong in dedicated modules. Startup type, dependency failures, and service-specific verification should be state-derived, not hardcoded beside buttons.

### Directory versus workstation

Directory is correctly a separate administrative system. Account state must remain authoritative there. Workstation sign-in, profile, cached credentials, mapped-drive access, and user-visible symptoms should be projections of directory and workstation state, not a second writable copy of the account.

## Five representative workflow audit

### INC2511 — locked account

Strengths: requester inspection, identity verification, account lookup/inspection, diagnosis, safe unlock, notes, and server-enforced prerequisite order.

Gaps: verification is a hardcoded “approved training check” button, the selected method is not learner-visible or auditable, Company Chat is not required, and completion relies on a generic Directory “verify access” action rather than a repeat test of the original sign-in symptom plus requester confirmation.

### INC2512 — password reset

Strengths: identity-before-reset and correct-account checks are server enforced; secrets are not entered in the current flow.

Gaps: no explicit method selection, temporary-password/next-sign-in semantics are not represented, the learner cannot distinguish reset from unlock based on evidence, and requester confirmation is absent.

### INC2513 — MFA reset

Strengths: identity-before-reset and account targeting are server enforced.

Gaps: no method inventory/removal/re-registration lifecycle, no session-revocation decision, no Company Chat confirmation, and no original MFA enrollment/sign-in retest.

### INC2405 — file-share access

The current ticket title mentions a facilities calendar while the workstation profile behaves as a mapped-drive repair. This content mismatch must be resolved in the next immutable scenario version. The present reconnect button is not a realistic mapping workflow and cannot prove path, reachability, permissions, or requester access.

### INC2406 — VPN/network

The current ticket device is described as macOS while the tool presents a Windows workstation. That mismatch must be resolved in the next immutable scenario version. Clicking VPN Connect currently restores the share implicitly. The corrected workflow must separate profile/connectivity diagnosis from share mapping and must verify both the VPN route and the original partner-workspace/share symptom.

## Learning-mode leakage audit

The remote desktop has Guided, Practice, and Assessment hint behavior, but the surrounding ticket workspace always shows the same “Suggested tools” card. Ticket fixtures and Remote Desktop can expose exact tool lists in every mode. Many less-mature scenarios also show direct `perform_scenario_step` buttons whose labels describe the expected action.

Required policy:

| Surface | Guided | Practice | Assessment |
|---|---|---|---|
| General process reminder | Visible | Visible, concise | Hidden |
| Suggested tool categories | Visible | Optional after request | Hidden |
| Exact app/command/step | Progressive hint only | Hint after request and penalized | Hidden |
| Objective/action keys | Never visible | Never visible | Never visible |
| Hidden root cause/facts | Never visible | Never visible | Never visible |
| Raw engine rejection | Translated teaching copy | Neutral safe copy | Neutral safe copy |

The mode must be attempt-level authoritative state, not a private preference inside only one workstation overlay. UI selectors across Ticket Workspace, tool catalog, Remote Desktop, and feedback must consume the same mode.

## Progression contradiction and resolution

Migration 0047 maps the foundational account scenarios to separate curriculum weeks:

- Week 1: `locked-user-account`
- Week 3: `password-reset`
- Week 4: `mfa-reset`

The progression service simultaneously unlocks all three in the Week 1 Starter Support pack. Both `_passed_scenario_keys` and training completion treat any passed attempt as mastery, regardless of mode or when it was attempted. Therefore, a guided starter pass can silently complete a later weekly requirement.

### Chosen model: guided onboarding does not count as curriculum mastery

- Starter Support may expose all four cases in Guided mode as low-pressure onboarding.
- A Guided pass records practice history and feedback but does not unlock packs, satisfy a weekly required activity, count as “passed first try,” award mastery XP, or satisfy assessment completion.
- Practice or Assessment passes are mastery-eligible. A later weekly requirement needs a mastery-eligible pass associated with that scenario at or after the week becomes available.
- Existing historical passes retain their prior meaning through an explicit backfill policy; no historical attempt is silently downgraded.
- Attempt purpose/mode and eligibility must be stored server-side and included in progression/training queries, API read models, replay, exports, and tests.

This resolves the contradiction without hiding starter cases and creates coherent Guided → Practice → Assessment semantics.

## Persistence, replay, and migration audit

Strengths:

- Snapshots have a schema wrapper and deserializer fallbacks.
- The server stores immutable scenario versions and ordered attempt events.
- Browser actions are synchronized through an outbox and server results can replace local state.
- Grades are recomputed from server-trusted events.

Risks and required controls:

- The workstation state expansion needs a new snapshot schema version and an explicit v1-to-v2 upgrader.
- Old flat overlay fields must deserialize into the equivalent typed machine state without fabricating grading evidence.
- New actions require server validation and objective mappings before they can count.
- Replay must pin scenario definition, objective catalog, workstation fixture version, command grammar version, and snapshot version.
- Fixtures should contain safe synthetic values only; no production domains, tokens, credentials, or personal data.
- Migration upgrades and downgrades must be rehearsed against a copy of representative state, with row counts and checksums for immutable/history tables.

## Mobile, accessibility, and visual audit

The current UI is desktop-oriented and uses responsive outer layouts, but the simulated desktop itself needs an intentional narrow-viewport policy. A tiny scaled desktop is not usable training.

Required behavior:

- Desktop: movable/focusable windows with taskbar and start menu.
- Tablet: bounded windows with sensible defaults and optional maximize-first behavior.
- Mobile: one maximized app at a time, app switcher/taskbar, persistent access to ticket context, no horizontal page overflow, and dialogs that fit the viewport.
- All actions must be reachable without drag; window controls and app navigation need focus styles, labels, sensible order, and escape/close behavior.
- Status and error meaning must not rely on color alone.
- Visual QA must cover desktop and mobile for all five workflows, including error, loading, minimized, dialog, completion, resume, and assessment states.

## Recommended architecture

```text
Ticket attempt (server-pinned mode + scenario/workstation version)
        |
        v
TicketSession orchestration / sync outbox
        |
        v
Simulation engine domain dispatcher
        |
        +-- ticket / directory / asset reducers
        |
        `-- workstation reducer
              +-- machine + profile
              +-- network + VPN + DNS cache + routes
              +-- filesystem + shares + mapped drives
              +-- credentials
              +-- services
              +-- windows + application state
              `-- deterministic command interpreter
                         |
                         v
              trusted action/event projection
```

Proposed module boundaries:

- `packages/shared/src/workstation/`: versioned public types, fixture schema, safe constants.
- `packages/simulation-engine/src/workstation/`: initializer, reducer, selectors, invariants, migrations, and command interpreter.
- `apps/web/components/workstation/`: shell, window frame/manager, taskbar/start menu, and app registry.
- `apps/web/components/workstation/apps/`: Explorer, Terminal, VPN, Credential Manager, Services, Settings, System Information.
- `apps/web/lib/workstation/`: presentation selectors and learning-mode-safe feedback.
- Backend objective catalog: action-to-trusted-event rules for every graded workstation mutation and verification.

## Future real-VM seam

The browser simulator should depend on a small `WorkstationAdapter` contract rather than browser-only assumptions:

- read a versioned workstation snapshot;
- execute an allowlisted intent and return structured observations/events;
- subscribe to state changes;
- capture safe evidence with redaction metadata;
- report capabilities and connectivity;
- reset/restore an exercise checkpoint.

The deterministic browser adapter remains the default. A future VM adapter could translate the same intents to a brokered lab environment, but server grading must still consume normalized, signed observations rather than trusting arbitrary guest output. No VM runtime is part of this phase.

## Implementation order and gates

1. Lock contracts with reducer, serialization, command, and objective tests.
2. Introduce versioned shared workstation state and v1 snapshot migration.
3. Extract the workstation reducer and command interpreter from the global switch.
4. Extract the desktop shell/window manager and app registry from `RemoteDesktopTool.tsx`.
5. Build Explorer, VPN, Terminal, Credential Manager, Services, and Settings on shared state.
6. Convert INC2511, INC2512, INC2513, INC2405, and INC2406 end to end.
7. Make mode attempt-authoritative and implement non-mastery Guided semantics with historical compatibility.
8. Add unit, integration, API, migration, Playwright, accessibility, persistence, replay, and visual coverage.
9. Run full CI-equivalent validation, dependency/security audits, migration rehearsals, and predeployment checks.

No phase is complete if a one-click magic path can still satisfy the same trusted objective, if the original symptom cannot be re-tested, or if an old attempt cannot resume safely.

