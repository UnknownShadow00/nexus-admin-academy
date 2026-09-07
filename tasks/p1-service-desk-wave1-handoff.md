# Service Desk P1 Wave 1 — Persistent workspace

Completed: 2026-09-07. Branch: `feature/service-desk-p1-workspace`, based on P0 HEAD `bcc9957`.

## Scope and starting state

P0's launcher, assigned-device focus, server-owned outcomes, rejected-note retention, and grading protections were already present and were preserved. The working tree initially contained the prior Markdown-export task-log entry. That entry was preserved; the referenced architecture Markdown file was absent at the start of this implementation, so the review retained in the conversation and the explicit Wave 1 request supplied the design context.

No scenario definitions, authored evidence labels, per-ticket goals, tutorial/onboarding state, grading weights, evaluator, backend schema, mentor replay, or teaching debrief were changed.

## Workspace changes

- Compact case header: identity/title, requester/asset, priority, operational status, existing mode/attempt information, and module return.
- Six boxed stage explanations replaced by a compact status strip and one current-stage area using existing generic copy. Assessment explanation policy remains respected.
- Wide work area contains the tool switcher, reported-issue disclosure, active tool, and ticket actions.
- Evidence and notes are first-class rail content; hints are accessible through a disclosure. Evidence is still projected from the trusted server response.
- Case/device details and activity history are retained, collapsed by default.
- Global catalogue/navigation and the duplicate global module-return control are suppressed on ticket pages. Queue and standalone tool navigation remain available on their existing routes.

## Tools and continuity

The switcher shows at most four active/recent/guided-suggested tools and an **All tools** disclosure. The complete catalogue remains reachable, including safe but unhelpful choices. Practice/assessment do not receive guided suggestions.

Integrated Remote Desktop keeps P0's assigned-device focus and omits its duplicate case sidebar. Its viewport is bounded to keep the desktop icon list from making the mobile terminal excessively tall. Standalone selection remains available.

The existing `IntegratedToolContext` now exposes ticket/assignment/server-attempt identity and existing experience mode, with requester/asset retained on the ticket object. The existing provider supplies the server-issued attempt mapping; no second session store was added. Return paths use the existing validated return-target helper. Query hints cannot replace ticket or curriculum identity.

The pane owns one integrated Back control. Existing cross-tool links in deployment, shelf, server-room, and endpoint tools use the workspace selection callback when integrated and remain ordinary links when standalone.

## Mobile and accessibility

At 390px, Work / Evidence / Notes tabs replace a stack of all rail content. Panels remain mounted, preserving drafts while switching tabs/tools. Hints remain accessible above mobile work; details/history remain secondary disclosures.

The tool disclosure has explicit expanded/control semantics, native button keyboard operation, Escape dismissal, and focus return. Browser coverage selects Directory with Enter/Tab and checks focus after selection. Existing Radix tab behavior and focus styling remain in use. The integrated terminal fits the page width and has a bounded viewport; its output can scroll internally.

## Screenshots

All captures use generated fixture accounts on the disposable local stack—not production.

| View | Screenshot |
|---|---|
| Desktop before | [P0 initial workspace](p1-wave1-screenshots/desktop-before.png) |
| Desktop initial | [P1 initial workspace](p1-wave1-screenshots/desktop-initial.png) |
| Desktop tool open | [Remote Desktop in the shell](p1-wave1-screenshots/desktop-tool.png) |
| Desktop evidence/notes | [Retained evidence and note draft](p1-wave1-screenshots/desktop-evidence-notes.png) |
| Mobile initial | [390px workspace](p1-wave1-screenshots/mobile-initial.png) |
| Mobile tool open | [390px live terminal](p1-wave1-screenshots/mobile-tool.png) |

At the same 1440×900 browser viewport, the initial full-page capture decreased from 2917px to 1397px in height. The six high-weight stage cards and always-expanded ten-tool catalogue no longer compete with the work area. Evidence and note entry are asserted to intersect the initial viewport. These are supporting layout observations, not a beginner-usability study. Only the desktop initial view has a captured P0 baseline.

## Validation

Final passing results, excluding earlier diagnostic runs:

| Suite | Result |
|---|---:|
| Backend P0 inventory/integrity/grading gate/onboarding/mapping/anti-gaming/publication | 41 passed; 2 dependency warnings |
| Service Desk shared | 37 passed |
| Service Desk simulation | 268 passed |
| Service Desk web | 176 passed |
| Service Desk UI | 36 passed |
| Service Desk package total | 517 passed |
| Frontend units | 53 passed |
| Standalone Service Desk browser suite | 27 passed |
| Authenticated integrated browser regressions | 14 passed |
| New P1 workspace browser tests | 2 passed |
| Authenticated P0 beginner curriculum flow | 1 passed |
| Browser total | 44 passed |

Service Desk production build, all-package typecheck, lint, frontend production build, CI YAML parsing, and whitespace checks passed. Unchanged package tasks may use Turbo cache. No Python or shell source changed.

P0 still rejects undeserved credit for immediate close, operational Resolved, generic notes, remediation without required investigation/verification, wrong targets, incorrect repair ordering, and forged evidence. The positive beginner path still yields a server PASS and reconciled V2 activity credit. Rubric weights remain 15/25/30/20/10.

### Diagnostic findings resolved

- New P1 tests failed on the P0 baseline as expected: expanded catalogue and old mobile tabs.
- Existing unit/browser assertions for full stage explanations, visible catalogue, the old Rail tab, and the old evidence heading were updated to the intended presentation—not satisfied by restoring old UI.
- A duplicate module-return control was caught by strict browser selectors and removed from the global ticket-page header.
- Running the P1 tests after the beginner test completed their shared assignment exposed a fixture-order requirement. CI explicitly runs the unfinished-workspace tests before the completing beginner path, on the fresh disposable stack.
- Screenshot review caught an over-tall mobile simulated desktop; the integrated viewport was bounded and a browser height assertion added.
- An initial new unit-test fixture failed typecheck; it now uses an existing real ticket fixture.
- Standalone screenshot tests refreshed five existing legacy PNGs. Those generated changes were restored to their known-clean starting versions; only the requested P1 evidence images are retained.

### Dependency audits

Audits were run before committing. pnpm reports no vulnerabilities. Frontend npm reports existing `browserslist` (high) and `postcss-selector-parser` (low) advisories. The installed backend environment reports a pip 26.1.2 installer advisory, `PYSEC-2026-3721`, with 26.2 listed as a fix. No dependency or lockfile was changed in this layout wave. These audit findings are follow-up items, not passing audit results.

## Reproduction

Start a fresh stack with `scripts/e2e/start_local_stack.sh`; source its generated `stack.env` without printing credentials. Run the integrated regression spec, then `p1-service-desk-workspace.spec.js`, then `p0-service-desk-beginner.spec.js`. Set `NEXUS_P1_SCREENSHOTS` to a disposable output directory to capture P1 views. Always stop that stack before the standalone build/browser run; both use the same local Next build directory.

The new P1 tests intentionally do not complete the assignment. The P0 beginner test performs the legitimate completion. Do not run these shared-fixture specs in arbitrary parallel order or against an already-completed fixture assignment.

## Remaining Wave 2

- Authored evidence labels.
- Stage-specific ticket goals.
- Evidence meaning after debrief.

## Production safety

Read-only checks confirmed production schema `0064_v2_ai_grading_infrastructure`; the production process and `.env` have no V2 enablement or pilot settings, and the access service defaults to V2 OFF with an empty pilot set. No deployment, production migration, production content load, production pilot enrollment, or merge to main occurred. Disposable test stacks were stopped. Existing P0 ancestry was preserved.
