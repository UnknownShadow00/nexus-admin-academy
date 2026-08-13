# Service Desk Workstation Final Review

**Review baseline:** `a4dd42a784b48c250653131eb2f134192087acec..f95cdcb48ce169f0bb52f20bd05778538d325127`  
**Branch:** `agent/service-desk-workstation-realism`  
**Review status:** findings remediated and locally validated; stacked draft PR/CI confirmation follows the final push  
**Scope guard:** development only; PR #15 and PR #16 remain stacked, draft, and unmerged; no production access or deployment is part of this review.

## Review method and actual diff scope

The review used the complete 67-file PR #16 diff (6,896 insertions and 715 deletions), not the existing summary. It covered migration 0047, the Service Desk API and progression reads, the browser-to-Nexus event bridge, the complete workstation/simulation implementation, every changed unit and browser test, and the desktop/mobile QA artifacts.

The implementation is materially stronger than the pre-PR workstation. Server-authoritative grading, trusted action sequencing, exact account/file-share/VPN evidence, deterministic commands, cross-app state, and clean-browser restore are real. The remaining issues are boundary, semantics, information design, and maintainability issues rather than a reason to redo the workstation.

## Pre-change findings

### BLOCKER

1. **Server resume snapshots own cosmetic UI state and churn on UI-only actions.** The full `Attempt` is sent in every Nexus action snapshot. `WorkstationState.desktop`, Explorer navigation/history, terminal recall state, and duplicate legacy presentation fields are included. UI-only actions such as focus, minimize, move, maximize, Start menu, and app open/close can also enqueue snapshot writes. This makes the server responsible for window layout and produces unnecessary writes.
2. **Assessment replay can farm XP.** XP is awarded with `source_type="service_desk_attempt"` and `source_id=attempt.id`. A new passing Assessment attempt for the same scenario therefore has a new idempotency key and can award the full score again. The completion endpoint itself is idempotent per attempt, but mastery is not idempotent per student/scenario.
3. **Mode-mismatched attempt selection can attach an Assessment UI to a Guided attempt.** Assignment listing first searches for an in-progress attempt matching the current derived `experience_mode`, then falls back to the newest attempt in any mode. If curriculum timing changes while an earlier Guided attempt remains in progress, the row can advertise Assessment while returning the Guided attempt id. The browser may then sync Assessment-looking work to a non-mastery attempt.

### IMPORTANT

1. **Fresh snapshots copy all workstation fixtures eagerly.** `createAttempt()` creates a full v2 workstation, including immutable machine, host, filesystem, network, and service fixtures, for every workstation in the catalog before any workstation has been touched.
2. **Terminal and per-overlay event histories are unbounded.** Every command is copied into both `RemoteDesktopOverlay.terminalHistory` and `WorkstationState.terminal.history`; command recall is copied again. Remote Desktop action events also grow without a limit. A long session grows browser memory, local storage, outbox entries, and server snapshots.
3. **The server snapshot endpoint validates only the two-key wrapper shape.** It correctly treats the nested state as untrusted for grading, but it has no explicit serialized-size limit and accepts arbitrary nested payloads for persistence.
4. **Practice/mastery reads are inconsistent.** Pack unlocks, required weekly completion, and the main progression counts correctly require Assessment passes. However, the bridge progress summary builds `passed_scenarios`, first-try counts, skill counts, and “needs practice” from attempts in all modes. Guided or Practice passes can therefore appear as simulator completion/mastery in that summary. Dashboard/student counts also count passing Assessment attempts rather than distinct mastered scenarios, so Assessment replay inflates totals.
5. **Guided-to-Assessment language is incomplete.** Rows expose a mode badge only after opening a ticket. Guided completion does not clearly say that the case will return later for independent Assessment, and later Assessment does not say that prior Guided work was practice rather than forgotten completion.
6. **Queue labels do not fully answer “what should I do now?”** Assigned/Practice/More unlocked are structurally sound, but mode and weekly requirement are not visible in a restrained row-level presentation. “Completed” is used where “Assessments passed” is the actual metric.
7. **Directory remediation controls leak diagnosis.** Correct scenario-specific actions are visible from the start and disabled until the matching diagnosis is recorded. The disabled control name reveals the likely fix, while the simulator also rejects safe alternate account actions before diagnosis. This behaves like a scenario wizard rather than a generic technician console.
8. **Identity verification accepts every synthetic method for every starter account case.** The UI offers three safe methods, but the scenario has no concept of which approved evidence is actually available. Selecting any option succeeds, so the choice is mostly ceremonial.
9. **Assessment workflow presentation exposes grading progress.** The sidebar shows “Diagnosis evidence,” “Correct fix,” and “Post-fix verification” completion and gates closure on those booleans. It does not expose raw server answer keys, but it reveals the grading categories and confirms when the correct fix has been found. Assessment should permit an independent close attempt without acting as a live answer checklist.
10. **Terminal parsing is host-safe but incompletely bounded.** Metacharacters (`&`, pipes, redirects, semicolons, backticks, `$`, CR/LF) are rejected and no code path invokes a host shell. However, input has no length cap, extra switches are often ignored, quoting/Unicode/mixed-case coverage is thin, and command recall state exists in the model without a usable keyboard recall UX.
11. **`RemoteDesktopTool.tsx` remains a 2,701-line responsibility cluster.** The RC reduced it only from 2,739 lines at the PR base. It still owns ticket/session selection, connection/login, desktop shell, application dispatch, every workstation app, feedback, hints, completion, and scenario presentation. The natural low-risk extraction boundary is application rendering plus its app-specific panels.

### NICE LATER

1. Delta-encoding every mutable workstation field against fixture defaults could reduce touched-workstation snapshots further, but sparse workstation creation plus UI stripping/history caps should be measured first.
2. The full browser bundle necessarily contains deterministic simulation rules needed to run the client. Separating presentation fixtures from mentor-only explanatory copy would improve defense in depth, but server grading already ignores client definitions and the API strips objective/explanation data.
3. BitLocker Recovery and New Employee Onboarding remain future work and are deliberately excluded from this pass.

## Workstation state boundary

The final contract should distinguish semantic persistence from wire representation. Immutable fixture data may be rehydrated rather than copied into every snapshot, but it still belongs to the simulation definition.

| `WorkstationState` field | Classification | Final persistence intent |
|---|---|---|
| `schemaVersion` | Simulation contract | Persist/validate |
| `machine.assetTag` | Simulation identity | Persist; used to rehydrate fixtures |
| `machine.hostname`, `operatingSystem`, `build`, `domain`, `model`, `location`, `lastLogon` | Immutable scenario fixture | Rehydrate; do not repeatedly copy when a sparse/delta representation is sufficient |
| `machine.domainJoinState`, `signedInUser`, `profileState`, `compliance` | Mutable/scenario-relevant machine state | Persist |
| `network.internetReachable`, `intranetReachable` | Simulation state | Persist |
| `network.interfaces` including address, gateway, status, and DNS | Simulation state | Persist mutable values; rehydrate immutable identifiers/labels where practical |
| `network.routes`, `dnsCache` | Troubleshooting simulation/evidence state | Persist with sensible bounds for cache entries |
| `network.knownHosts` | Immutable deterministic fixture | Rehydrate rather than duplicate |
| `network.vpn.profiles` | Immutable deterministic fixture/configuration | Rehydrate; persist only selected/connected/configuration mutations if profiles become editable |
| `network.vpn.selectedProfileId`, `connectedProfileId`, `status`, `error`, `log` | Simulation and troubleshooting state | Persist; cap log growth |
| `filesystem.nodes` | Simulated filesystem plus availability/access mutations | Persist mutations; rehydrate unchanged fixture nodes where possible |
| `filesystem.currentPath`, `history`, `historyIndex` | Explorer UI/session navigation | Local/session only |
| `filesystem.error`, `lastRefreshedAt` | Transient Explorer presentation | Local/session only; objective evidence lives in scenario progress/server events |
| `mappedDrives` | Simulated machine state | Persist |
| `credentials` | Safe credential metadata simulation state | Persist; never add password/secret values |
| `services` | Simulated machine state | Persist |
| `desktop.windows.*.open/minimized/maximized/bounds/restoreBounds/zIndex` | Desktop UI/session layout | Local/session only |
| `desktop.activeAppId`, `startMenuOpen`, `nextZIndex` | Desktop UI/session layout | Local/session only |
| `terminal.history` | Meaningful command/output evidence | Persist a bounded recent evidence window |
| `terminal.commandHistory`, `historyCursor` | Terminal recall/navigation UI | Local/session only and bounded |

Related legacy `RemoteDesktopOverlay` fields must follow the same rule: connection state, power/network state, repairs, scenario progress, notes, verification, VPN, mapped-drive/service state, and bounded terminal evidence persist; `focusedApp`, `openApps`, `minimizedApps`, Explorer visual navigation, and temporary errors remain local/session UI.

## Snapshot measurements at RC `f95cdcb`

Measurements use the production serializer and deterministic simulator actions. They are the raw nested `Attempt` JSON size before the Nexus wrapper and HTTP framing.

| Representative state | Serialized size before fixes |
|---|---:|
| Fresh workstation attempt | 285,769 bytes (279.1 KiB) |
| Midway through file-share work | 288,834 bytes (282.1 KiB) |
| VPN case after several commands | 293,601 bytes (286.7 KiB) |
| Account workflow after remediation | 288,060 bytes (281.3 KiB) |
| Long terminal session (500 commands) | 502,803 bytes (491.0 KiB) |

The 279 KiB fresh floor is not student work; it is mostly eagerly copied fixture state. The 500-command result demonstrates linear, duplicated history/event growth. Final before/after measurements will be appended after remediation.

## Mode semantics observed before fixes

- **Guided:** no pack/mastery counting and no XP in the main progression path; hints allowed without learning-mode penalties. The UI does not yet clearly explain later Assessment.
- **Practice:** derived only after an Assessment pass; it does not satisfy required weekly activity, pack mastery, or Assessment XP in the main completion endpoint. The bridge summary can still misclassify it because that read is not mode-filtered.
- **Assessment:** eligible for mastery, weekly completion, pack progression, and XP. Repeated Assessment passes currently award XP again and inflate attempt-based dashboard totals.

## Historical mode migration decision

The deterministic backfill is semantically supportable:

- The legacy database constraint permits only `learning` and `simulation`.
- Historical grading explicitly defined `learning` as penalty-free practice (“Learning Mode”) while leaving actual resolution checks intact.
- Seeded production assignments were `simulation`; the change that introduced Learning Mode documents that existing seeded rows were already simulation.
- Therefore `learning -> guided` and `simulation -> assessment` preserve the previous product meaning without student-specific heuristics.

Migration tests already cover one historical attempt of each legal legacy mode and the `0046 -> 0047 -> 0046 -> 0047` cycle. Final validation must add/retain explicit assertions for the complete legal mode domain, fresh upgrade, duplicate hashes/assignments, integrity, and foreign keys.

## Trust, grading, and symptom verification findings

- Browser `resulting_state`, local storage, raw `/events`, snapshot events, and close flags are untrusted for grading.
- Objective evidence can become trusted only through `/actions` and the server-owned scenario/action/order rules.
- Hints are rejected during Assessment.
- Locked Account, Password Reset, and MFA Reset require inspect, approved identity evidence, diagnosis, exact remediation, original sign-in-path verification, requester confirmation, note, and close.
- File share verification depends on the mapped resource opening; VPN verification depends on post-connection routing/resource reachability; service and DNS verification derive from shared machine state.
- The remaining trust concern is not forged state granting mastery; it is persistence size/shape and XP/mastery idempotency.

## GUI/CLI consistency findings

The RC uses one v2 workstation state for mapped drives, credentials, services, routes/DNS, and VPN. Existing tests confirm Explorer mapping is visible to `net use`, terminal deletion removes Explorer mapping, `cmdkey /list` reflects Credential Manager, and `sc query` reflects Services. Directory actions and synthetic sign-in checks use the same directory overlay. Additional final tests should make these exact bidirectional contracts explicit and retain them through serialization.

## Accessibility, mobile, and performance findings

- Window headers support pointer drag and `Alt+Arrow` keyboard movement; persistent labeled minimize/maximize/close controls are present.
- Desktop icons, taskbar apps, ticket navigation, and dialogs are real buttons/links. Dragging is not the only window-management path.
- Mobile uses an inset near-full-screen window fallback and the existing 375×812 screenshot shows no immediate trapped-screen defect.
- Gaps to retest/fix: Start-menu Escape/focus behavior, terminal Up/Down command recall, visible focus in extracted app components, mobile terminal keyboard/input reachability, and sidebar reopening.
- RC production bundle baseline: shared first-load JS **102 kB**; `/tools/[slug]` **251 kB** first load; main Service Desk `/` **211 kB** first load. The final build must not materially regress these values.

## Targeted remediation completed

1. Added a dedicated Nexus-resume serializer that strips UI/session fields, retains bounded troubleshooting evidence, and overlays same-attempt local UI after server restore.
2. Stopped Nexus writes for UI-only workstation actions and made untouched workstation overlays sparse/lazy.
3. Bounded input and histories and tightened deterministic command parsing.
4. Made mastery reads Assessment-only and XP idempotent per student/scenario, including a partial database uniqueness invariant for concurrent completions.
5. Prevented in-progress cross-mode fallback and added concise Guided/Practice/Assessment language.
6. Converted Directory actions into a generic safe console, allowed safe wrong actions, and graded them rather than revealing the right action through disabled controls.
7. Added scenario-supported, synthetic approved identity methods and enforced the selected evidence in browser and server transition rules.
8. Removed hints, suggested tools, and live grading-checklist labels from Assessment presentation and payloads.
9. Extracted application rendering from `RemoteDesktopTool.tsx` without changing the workstation state model.
10. Added/extended regression coverage for restore, state boundaries, cheats, history limits, modes, migration, keyboard operation, and exact target viewports.

## Final results

### Persisted simulation state

Nexus resume snapshots own machine identity and mutable machine state, network interfaces/routes/DNS/VPN configuration and connection state, mapped drives, credential metadata, services, filesystem nodes/availability, scenario progress, remediation and verification state, notes, bounded event evidence, and the most recent 50 terminal command/output evidence records. Immutable fixtures are created lazily: an untouched attempt no longer carries every workstation fixture.

### Local/session UI state

The local attempt cache, not Nexus, owns open/minimized/focused apps, window bounds/restore bounds/maximized state/z-index, Start-menu state, Explorer current path/history/cursor/transient errors/refresh timestamp, terminal recall history/cursor, and other cosmetic session presentation. Server restore merges these fields back only from a local cache with the same attempt id. UI-only actions do not enqueue server snapshots.

### Snapshot size and growth

Sizes are raw serialized attempt JSON. “Local” retains session UI; “Nexus” uses the resume boundary.

| Representative state | RC before | Final local | Final Nexus resume |
|---|---:|---:|---:|
| Fresh attempt | 279.1 KiB | 1.7 KiB | 1.7 KiB |
| Mid file-share case | 282.1 KiB | 11.3 KiB | 10.9 KiB |
| VPN case after commands | 286.7 KiB | 16.3 KiB | 16.1 KiB |
| Account workflow | 281.3 KiB | 4.0 KiB | 4.0 KiB |
| 500-command stress session | 491.0 KiB | 87.3 KiB | 77.7 KiB |

The server additionally rejects resume snapshots above 512 KiB. No evidence required for grading was removed; grading still uses the separate trusted server event ledger.

### History and input limits

- Terminal rendered/local evidence: 100 entries.
- Terminal Nexus-persisted evidence: 50 entries.
- Terminal command recall: 100 commands; recall cursor remains local.
- Remote Desktop overlay events: 250.
- Explorer navigation history: 50 and local-only.
- VPN log: 50.
- Terminal input: 512 characters.

### Workstation architecture

`RemoteDesktopTool.tsx` fell from 2,701 lines at the RC to 1,329 lines. The extracted `WorkstationApplications.tsx` (1,447 lines) owns application dispatch and the cohesive set of app panels; `RemoteDesktopTool` retains session selection, ticket workspace, connection/login, desktop/taskbar, feedback, hints, and closure orchestration. The existing `WindowFrame` and app registry remain reusable boundaries. A dynamic-import experiment did not improve the measured route bundle and was not retained.

### Final mode and progression semantics

- **Guided:** supported learning attempt; can use hints; a pass is shown as guided practice complete and may be referenced by a later Assessment. It grants no mastery, pack pass, required-week completion, achievement progress, or XP.
- **Practice:** independent repetition after mastery without curriculum stakes. It grants no mastery, pack pass, required-week completion, achievement progress, or XP.
- **Assessment:** independent mastery attempt. A passing Assessment may satisfy the required week and pack progression and may grant XP once per student/scenario.
- Replay of Guided or Practice never grants XP. Repeated Assessment attempts cannot add another mastery row or XP award. Dashboard/progress counts use distinct Assessment-mastered scenarios rather than passing attempt totals.
- The queue keeps current assigned work dominant, shows a restrained mode label, identifies required-this-week work, calls the count “Assessments passed,” and explains a later Assessment as independent demonstration after earlier Guided practice.

### Migration 0047

The historical mapping remains `learning -> guided` and `simulation -> assessment`. This follows the only legal legacy values and their documented behavior: Learning Mode was penalty-free supported practice, while seeded/graded Simulation Mode represented the independent attempt. Tests cover both values, the constraint domain, fresh base-to-0047, production-like 0046-to-0047, and 0046-to-0047-to-0046-to-0047. They preserve attempts/events/grades/hashes, prohibit duplicate assignments/version hashes, enforce the mastery-XP uniqueness index, report `PRAGMA integrity_check = ok`, and report zero FK errors.

### Leakage, Directory, identity, and verification

- Assessment API responses omit hints and suggested-tool lists. The workstation does not render a correct-fix checklist or objective-completion labels in Assessment. Browser simulation definitions remain available because the deterministic machine runs client-side, but private grading objectives and trust decisions remain server-only.
- Directory offers natural account and authentication actions after inspection/identity authorization. Safe wrong actions are possible and incur a grading penalty; destructive enable/disable actions are not added to starter cases. The right action is no longer exposed as a scenario-specific disabled answer button.
- Identity verification offers multiple safe synthetic methods where the scenario supports them: employee-ID/directory match, manager confirmation, or callback through a known company contact. Unsupported methods are rejected; no knowledge-based questions or real PII are used.
- Original-symptom verification remains state-derived: account sign-in/temporary credential/MFA readiness, mapped resource opening, and VPN route/DNS/internal-resource reachability. A forged Verify event or result snapshot cannot satisfy server objectives.

### Cross-app and terminal results

Mapped-drive changes remain bidirectional between Explorer and `net use`; Credential Manager and `cmdkey /list` share one state; Services and `sc query` share one state; VPN affects routes, DNS, and internal reachability; Directory remediation affects simulated sign-in. Restore tests confirm the same shared state in a clean browser.

Terminal execution remains purely simulated. Mixed case and whitespace work where legitimate. Malformed quoting, controls, Unicode edge input, extra/unsupported switches, pipes, redirects, `&&`, `||`, semicolons, substitutions, traversal strings, and overlength input return deterministic simulated errors and never reach a host executor.

### UI, accessibility, and performance

- Actual Playwright screenshots were inspected at 1440×1000 and 375×812. Desktop layout, ticket workspace, taskbar, overlapping Terminal, window controls, and closure UI remain usable.
- The first mobile capture exposed inline desktop geometry overriding the small-screen window inset. Important responsive classes now override the inline bounds; the retest keeps minimize/maximize/close on-screen, Terminal input and taskbar reachable, Back to Nexus visible, and horizontal overflow absent.
- A keyboard-only test opens/closes the ticket workspace, opens Start, launches Terminal, submits and recalls a command, minimizes and refocuses the window, and reaches Back to Nexus. Window title bars also retain `Alt+Arrow` movement and labeled focus/minimize/maximize/close controls.
- Final Service Desk build: shared 102 kB (no change), `/tools/[slug]` 252 kB (+1 kB), `/` 213 kB (+2 kB), ticket page 216 kB. The increase is small and justified by hardening/semantics; no build-system rewrite was warranted.

### Cheat and regression results

Tests reject or fail to trust direct remediation before prerequisites, forged `resulting_state`, raw event posting, local snapshot edits, fake confirmation, missing identity verification, missing documentation, wrong account/method/action, wrong asset/path/drive, and premature closure. Replays across all three modes do not create undeserved mastery. Student isolation and mentor read-only boundaries remain intact.

PR #15 progression behavior was rerun through the complete integrated suite: Week 0, Starter Support, Assigned/Practice/more-unlocked queues, current-week and instructor assignment, Home/My Training, lesson/quiz/lab/Progress behavior, Back to Nexus, role gates, and student isolation all passed.

### Validation record

- Backend: `pip check` pass; CI-scope Ruff pass; compile pass; focused Service Desk/migration suite 109 passed; full pytest 410 passed (9 deprecation warnings); `pip-audit` no known vulnerabilities.
- Service Desk: lint pass; typecheck pass; 305 package tests pass (36 shared, 175 simulator, 29 UI, 65 web); production build pass; `pnpm audit` no known vulnerabilities.
- Nexus frontend: `npm audit` zero vulnerabilities; production build pass; CLI validation 48 lessons pass; CLI sanity pass.
- Playwright: 28/28 pass from a fresh disposable base-to-0047 database, including desktop/mobile Daily Review, parent progression, account workflows, shared-state/offline restore, trusted grading/XP/replay, converted workstation cases, exact viewports, and keyboard operation.
- Disposable stacks were stopped and removed after each run. Production was not read from, written to, migrated, deployed, or otherwise modified.

### Remaining classification

- **BLOCKER:** none after remediation and local validation.
- **IMPORTANT:** the client necessarily carries deterministic simulation definitions; private grading remains server-side. `WorkstationApplications.tsx` is cohesive but large and can be split by app family only when future changes justify it.
- **NICE LATER:** delta-encode touched workstations further if real telemetry justifies it; improve Start-menu focus trapping/Escape polish; address unrelated repository-wide legacy Ruff debt outside the CI scope; BitLocker and New Employee Onboarding remain explicitly future work.

The final commit SHA, draft PR state, predeploy result, and required CI status are reported after the final push. Neither PR is to be merged and production remains untouched.
