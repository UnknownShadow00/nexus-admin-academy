# Service Desk Workstation Realism Research

Date: 2026-08-12

## Decision summary

Build the domain model, app behavior, deterministic command interpreter, and desktop presentation as project-owned modules. Adopt one narrowly scoped window primitive only if its integration tests prove reliable: `react-rnd` is the leading candidate because it provides controlled bounds, drag handles, resize handles, and parent bounds without imposing a tiled-desktop or full operating-system architecture. Do not adopt a full web desktop, generic file uploader, old file-manager suite, or terminal emulator for Phase 1.

This simulator needs a constrained, auditable Windows training environment, not a general-purpose browser operating system. Every visible observation must be derived from one deterministic state, and every graded mutation must map to a server-validated action. That requirement dominates visual completeness and library convenience.

## Real Windows workflow references

### Network diagnosis

Microsoft documents `ipconfig` as the Windows TCP/IP configuration tool, including `/all`, DHCP release/renew, and DNS cache display/flush operations. The simulator should compute these outputs from interface, DHCP, DNS, and cache state rather than replay fixed strings. Source: [Microsoft Learn — ipconfig](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/ipconfig).

`ping` verifies IP reachability and can expose name-resolution problems, while `tracert` reveals the route toward a destination. `nslookup` queries configured or explicitly selected DNS servers. Their simulated results should share the same interface, route, DNS, VPN, and host registry facts. Sources: [Microsoft Learn — ping](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/ping), [Microsoft Learn — tracert](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/tracert), and [Microsoft Learn — nslookup](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/nslookup).

PowerShell's `Get-NetIPConfiguration` is a useful reference for the structured machine model even if the first terminal grammar remains Command Prompt-style: interface alias/index, profile, addresses, gateways, and DNS servers are first-class related values. Source: [Microsoft Learn — Get-NetIPConfiguration](https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-netipconfiguration?view=windowsserver2025-ps).

### Mapped drives and credentials

The Windows mapping flow asks for a drive letter and folder path and can reconnect the mapping at sign-in. The simulator should reproduce those decision points, validation states, and visible results rather than a “Reconnect” success button. Source: [Microsoft Support — Map a network drive in Windows](https://support.microsoft.com/en-au/windows/map-a-network-drive-in-windows-29ce55d1-34e3-a7e2-4801-131475f9557d).

`net use` can list connections, connect a device name to a share, set persistence, supply a user context, and delete a connection. GUI and terminal operations therefore belong on the same mapped-drive collection. Source: [Microsoft Learn — net use](https://learn.microsoft.com/en-gb/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/gg651155(v=ws.11)).

`cmdkey` lists, creates, and deletes stored credential targets. The simulator should retain safe target/username/type metadata and use an opaque scenario credential reference; it must never store or echo a real password. Source: [Microsoft Learn — cmdkey](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmdkey).

### VPN

Windows requires a VPN profile before connection. Users select a named profile through Network & internet > VPN or the taskbar network surface, then connect and observe status. This supports modeling profile configuration separately from connection state. Source: [Microsoft Support — Connect to a VPN in Windows](https://support.microsoft.com/en-us/windows/experience/connectivity-networking/connect-to-a-vpn-in-windows).

Microsoft's VPN profile documentation treats routes, split versus forced tunneling, authentication, name resolution, and traffic filters as profile behavior. A deterministic training VPN should therefore mutate routes and DNS policy explicitly; it should not silently repair an unrelated mapped drive. Source: [Microsoft Learn — VPN profile options](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/vpn/vpn-profile-options).

### Windows services

`sc query` reports service state and can target a specific service. The current simulator already has the right safety pattern—structured state and allowlisted commands—but should derive both the Services app and terminal output from one service entity. Source: [Microsoft Learn — sc query](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-query).

Microsoft's Print Spooler troubleshooting guidance includes validating the spooler service and its dependencies before retesting printing. INC2408 should preserve this evidence-led sequence rather than treating “Running” as proof that the original print symptom is fixed. Source: [Microsoft Learn — Print Spooler service isn't running](https://learn.microsoft.com/en-us/troubleshoot/windows-server/printing/print-spooler-service-not-running).

### Account recovery and identity verification

`Unlock-ADAccount` is a distinct administrative action against a locked account; it is not equivalent to a password reset. That distinction should be visible in diagnosis, permissions, evidence, and audit events. Source: [Microsoft Learn — Unlock-ADAccount](https://learn.microsoft.com/en-us/powershell/module/activedirectory/unlock-adaccount?view=windowsserver2025-ps).

Microsoft's password reset flow supports a temporary password with a requirement to change it at the next sign-in. The browser simulation should represent that lifecycle without ever rendering or persisting an actual secret. Source: [Microsoft Learn — reset a user's password](https://learn.microsoft.com/en-us/entra/fundamentals/users-reset-password-azure-portal).

For MFA recovery, requiring re-registration removes registered methods and prompts registration at a later sign-in; revoking sessions is a separate control. These should be explicit, scenario-appropriate actions rather than a generic “Reset MFA” flag. Source: [Microsoft Learn — manage user authentication methods for Microsoft Entra multifactor authentication](https://learn.microsoft.com/en-gb/entra/identity/authentication/howto-mfa-userdevicesettings).

NIST's digital identity guidance rejects knowledge-based authentication/security questions as acceptable authentication evidence. The simulator should use a documented synthetic verification policy—such as a callback to a directory-listed contact plus a training-only employee identifier—not teach weak security questions as a normal reset workflow. Source: [NIST SP 800-63 FAQ](https://pages.nist.gov/800-63-FAQ/).

Microsoft also provides account-lockout diagnostic tooling and guidance, reinforcing that repeated lockouts should be investigated for their source rather than repeatedly unlocked. This is directly relevant to the stale-mapping scenario. Source: [Microsoft Learn — Account Lockout and Management Tools](https://learn.microsoft.com/en-us/troubleshoot/windows-server/windows-security/account-lockout-and-management-tool).

## Dependency comparison

Package metadata below was checked against the package registry on 2026-08-12. Repository links are the upstream project sources.

### Window managers and layout primitives

| Option | Fit | Maintenance / size signal | License | Decision |
|---|---|---|---|---|
| [`react-rnd`](https://github.com/bokuweb/react-rnd) | Controlled free-floating position/size, drag handles, resize handles, bounds | v10.5.3; about 87 KB unpacked; small dependency chain | MIT | Conditional adopt. Best fit for window movement and optional resize; wrap it behind project-owned window state and keyboard controls. |
| [`react-mosaic-component`](https://github.com/nomcopter/react-mosaic) | Tiled panes | v7.0.0; about 401 KB unpacked; drag/drop and utility dependencies | Apache-2.0 | Reject. A tiling manager does not reproduce overlapping Windows app behavior. |
| [`flexlayout-react`](https://github.com/caplin/FlexLayout) | Docking/tabbed layout | v0.10.5; about 1.6 MB unpacked | MIT | Reject. Good IDE layout, wrong desktop interaction model and larger surface. |
| Project-owned pointer implementation | Exact control | No dependency; highest maintenance and browser edge-case burden | Project license | Fallback only. Use if `react-rnd` fails React 19, accessibility, mobile, or persistence tests. |

`react-rnd` supports controlled `position` and `size`, stop callbacks, bounds, drag handles, and resize controls in its upstream documentation. Those map cleanly to a serializable window entity. It does not solve z-order, taskbar behavior, maximize/restore, app lifecycle, keyboard access, or responsive policy; those remain project responsibilities.

### Terminal libraries

| Option | Fit | Maintenance / size signal | License | Decision |
|---|---|---|---|---|
| [`@xterm/xterm`](https://github.com/xtermjs/xterm.js) | Full terminal rendering and input model | v6.0.0; about 5.9 MB unpacked before addons | MIT | Reject for Phase 1. Excellent for a PTY, but this is a small deterministic command grammar and does not need terminal emulation. |
| Project-owned command UI | Exact allowlisted commands, structured errors, simple history | Small and directly testable | Project license | Adopt. Keep parser and state mutations outside React; UI only handles input/history/scrollback. |

The safety boundary is more important than terminal fidelity: input is parsed into known command intents; no input reaches a shell, `eval`, dynamic import, arbitrary URL, or host filesystem.

### File Explorer libraries

| Option | Fit | Maintenance / size signal | License | Decision |
|---|---|---|---|---|
| [Chonky](https://github.com/TimboKZ/Chonky) | File-browser components | v2.3.2; last registry update in 2022; roughly 1.9 MB and older Material UI/Redux stack | MIT | Reject. Stale integration profile and unnecessary state architecture. |
| [`@files-ui/react`](https://github.com/files-ui/react) | File upload/drop-zone components | Current, roughly 938 KB unpacked | MIT | Reject. It is an uploader library, not a Windows Explorer/navigation model. |
| Project-owned Explorer | Address bar, navigation tree, mapped drives, deterministic errors | Uses the same domain state and existing design system | Project license | Adopt. The required behavior is narrow and scenario-specific. |

A general file manager still would not model Windows drive letters, UNC paths, reconnect-at-sign-in, VPN route dependencies, stored credential targets, or server grading evidence. Those are the bulk of the work, so a presentation library offers limited leverage.

### Browser operating-system projects

| Project | Useful patterns | License / scope | Decision |
|---|---|---|---|
| [daedalOS](https://github.com/DustinBrett/daedalOS) | Process/window contexts, taskbar, persistent window state, File Explorer patterns | MIT; complete browser desktop with many unrelated apps | Reference only. Do not copy its architecture or assets wholesale. |
| [OS.js](https://github.com/os-js/OS.js) | Modular desktop, application lifecycle, virtual filesystem | BSD-2-Clause; full client/server web-desktop platform | Reject. Too broad and imposes a second platform inside the simulator. |
| [Puter](https://github.com/HeyPuter/puter) | Large-scale browser OS and filesystem | AGPL-3.0; very large full-stack product | Reject on scope and license compatibility risk. |
| [98.js](https://github.com/1j01/98) | Desktop interaction and BrowserFS examples | Mixed project/assets context; Windows 98 recreation | Reference only. Wrong era and heightened asset/trademark concerns. |

The transferable lesson from these projects is separation: application registry, process/window state, filesystem abstraction, and shell presentation should be distinct. Their visual assets, bundled applications, general-purpose filesystem, authentication, and server layers are not appropriate dependencies.

## Build-versus-adopt conclusion

Adopt `react-rnd` only behind a `WindowFrame` adapter and only after a focused proof passes:

- React 19 rendering and hydration;
- controlled bounds surviving serialize/resume;
- focus and z-order on pointer and keyboard activation;
- title-bar-only drag without stealing controls or text selection;
- parent bounds at desktop/tablet sizes;
- maximize/restore and taskbar minimize independent of the library;
- usable non-drag controls on touch/mobile;
- no high-severity audit findings and an acceptable bundle delta.

If any of those fail, ship movement with a small project-owned pointer implementation and defer resize. The user-facing requirement explicitly values reliable move/focus/maximize over brittle resizing.

Everything else should be built in-repo because it encodes the simulator's trusted domain:

- versioned workstation state and migration;
- app registry and shell lifecycle;
- deterministic command grammar;
- filesystem/share/mapping rules;
- VPN/network/DNS behavior;
- credential metadata and redaction;
- service state;
- verification evidence;
- learning-mode presentation rules;
- action-to-objective projection.

## Proposed deterministic command grammar

The first complete grammar should be deliberately small:

- `ipconfig`, `ipconfig /all`, `/release`, `/renew`, `/displaydns`, `/flushdns`
- `ping <known-host-or-ip>` with a bounded count
- `nslookup <known-host> [known-dns-server]`
- `tracert <known-host-or-ip>`
- `net use`
- `net use <letter>: <unc> [/persistent:yes|no]`
- `net use <letter>: /delete`
- `cmdkey /list`
- `cmdkey /add:<known-target> /user:<synthetic-user>` using an opaque scenario credential flow rather than a password token
- `cmdkey /delete:<known-target>`
- `sc query [known-service]`
- `net start <known-service>` and `net stop <known-service>`
- `whoami`, `hostname`, `systeminfo`, `tasklist`, `gpupdate /force`, `cls`, `help`

Parsing rules:

- Tokenize quotes and whitespace with a finite parser; reject unsupported switches and trailing input.
- Normalize command names and safe identifiers, but preserve paths and display values for output.
- Resolve only fixture-known hosts, services, shares, users, and credential targets.
- Return structured output lines and typed mutations, not HTML.
- Escape all rendered text and cap history/output lengths.
- Record only normalized command intent and redacted arguments in trusted events.

## Identity-verification design

Each account ticket should publish an allowed synthetic verification policy. A learner selects and completes one permitted method, and the trusted event records the method ID, policy version, synthetic target, outcome, and timestamp—never a real identifier or secret.

Recommended training methods:

- callback to the phone number already held in the synthetic directory, with a displayed simulated callback outcome;
- manager confirmation already attached to the synthetic ticket when appropriate;
- training-only employee identifier matched against a synthetic record, paired with a second approved factor.

Disallowed teaching patterns:

- security questions or knowledge-based trivia;
- accepting a new phone/email supplied only in the same request;
- asking for or displaying a current password;
- treating Company Chat from an unverified session as identity proof by itself;
- a generic button with no method, target, outcome, or audit detail.

Company Chat remains useful for controlled callback coordination and post-repair confirmation. Its message thread should become deterministic evidence linked to the ticket and requester, but it must not independently satisfy identity verification unless the scenario policy explicitly establishes a trusted out-of-band channel.

## Later-phase scenario plans

### BitLocker recovery

Build only after identity-verification policies and secret-redaction controls are proven. The workflow should verify requester/device ownership, inspect the recovery-key escrow record, distinguish recovery from bypass, reveal a one-time synthetic key through an audited safe display, require post-boot verification, and ensure the key never enters notes, snapshots, logs, chat, analytics, or replay exports. Wrong-device/key disclosure is a critical failure.

### New employee onboarding

Build only after reusable identity, group, device, filesystem, and verification primitives exist. The workflow should validate the approved request, create/select the correct synthetic account, apply least-privilege group membership, assign the correct device, establish first-sign-in/MFA enrollment state, verify only authorized shares/apps, and document handoff. It must resist premature account creation, wrong-user assignment, excess group access, and secret leakage.

## Verification implications

The selected architecture requires tests at four layers:

1. Pure domain tests for state invariants, commands, migrations, redaction, and cross-app consistency.
2. Server tests for action authorization, objective projection, mode/mastery eligibility, grade replay, and malicious snapshot/event rejection.
3. Component/integration tests for window lifecycle, app interactions, keyboard access, dialogs, and state-derived errors.
4. Playwright workflows for all five representative tickets across Guided, Practice, Assessment, resume/reload, desktop/mobile, and deliberate failure paths.

Visual similarity is not sufficient evidence. A workflow passes only if another app/command observes the same mutation, the original symptom can be re-tested, the requester can confirm where required, and the server grade is reproducible from trusted events.

