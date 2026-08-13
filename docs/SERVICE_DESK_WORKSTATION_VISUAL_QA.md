# Service Desk Workstation Visual QA

Date: 2026-08-13
Scope: Shared-state Windows-inspired workstation, representative support flows, grading, and narrow-screen fallback

## Acceptance result

PASS. The inspected states are legible, internally consistent, training-safe, and free of blocking page-level clipping. The 375 × 812 fallback presents one usable maximized application, hides Explorer's secondary navigation rail, preserves window controls, and produces no horizontal document overflow.

## Captures inspected

| Capture | Viewport | Evidence | Result |
| --- | --- | --- | --- |
| [`desktop-mapped-drive-dialog.png`](../service-desk-app/docs/visual-qa/service-desk-workstation/desktop-mapped-drive-dialog.png) | 1440 × 1000 | File Explorer, existing broken mapping, exact UNC entry, reconnect option, credential choice | PASS |
| [`desktop-vpn-terminal.png`](../service-desk-app/docs/visual-qa/service-desk-workstation/desktop-vpn-terminal.png) | 1440 × 1000 | Terminal output behind a focused connected VPN client, desktop/taskbar state | PASS |
| [`desktop-directory-password-reset.png`](../service-desk-app/docs/visual-qa/service-desk-workstation/desktop-directory-password-reset.png) | 1440 × 1000 | Identity evidence, focused reset dialog, require-change control, explicit no-secret handling | PASS |
| [`desktop-grading-complete.png`](../service-desk-app/docs/visual-qa/service-desk-workstation/desktop-grading-complete.png) | 1440 × 1000 | Reconnected share, completion panel, evidence list, score, feedback, and workstation state | PASS |
| [`mobile-file-explorer-375x812.png`](../service-desk-app/docs/visual-qa/service-desk-workstation/mobile-file-explorer-375x812.png) | 375 × 812 | Collapsed ticket workspace, maximized Explorer, full-width drive cards, taskbar, and window controls | PASS |

## Inspection notes

- Window focus is visually apparent, and the focused window is above sibling windows for pointer and keyboard interaction.
- The mapped-drive dialog exposes configuration choices rather than a one-click repair and displays no real credentials.
- The password reset flow states that a simulated credential is never generated, displayed, copied, or stored.
- Completion feedback remains visible alongside the repaired workstation state, so grading is tied to observable evidence.
- Mobile retains the workstation metaphor without shrinking a two-column Explorer below usability. The ticket workspace remains available through its collapsible control.
- The automated mobile check asserts an effective `window.innerWidth` of 375 pixels and `documentElement.scrollWidth <= window.innerWidth`.

## Deferred breadth

The audit and research documents define broader tablet, minimized/error/loading, BitLocker, onboarding, and future VM-adapter coverage. Those are deliberately outside this release candidate; no blocking defect was found in the required representative captures.
