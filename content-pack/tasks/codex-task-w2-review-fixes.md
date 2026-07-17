# Wave 2 — Post-Review Fixes (W2T1/W2T2)

Code review findings on the Wave 2 CLI Labs changes. Fix all 5. Do NOT refactor the engine's internal mutation pattern — that is deferred to W2T3's state restructuring.

## 1. HIGH — dev-sw-act-06 uncompletable via advertised path
`frontend/src/features/cli-labs/data/lessons/learn-switching.json` (~line 628): the lab's scenario, objective label, and objective regex all tell the student `show interfaces status` OR `show interfaces` works, but `successCriteria.requiredCommands: ["show interfaces"]` uses exact matching (`objectiveTracker.js:commandRan`), so the `status` path never completes the lab.
Fix: remove `requiredCommands` from dev-sw-act-06's successCriteria — the `show-interfaces` objective regex already gates that a valid audit command ran. Keep `requiredState` untouched. Apply the same change to the backend copy.

## 2. MEDIUM — unbounded interface ranges
`frontend/src/features/cli-labs/engine/interfaceCommands.js:parseInterfaceRange`: `interface range g0/1 - 999999` creates 999999 interfaces and freezes the UI.
Fix: reject ranges where end > 48 (simulated 48-port switch) — return null so the caller emits the existing invalid-range error. No magic number inline: define `MAX_PORT = 48` constant.

## 3. MEDIUM — show mac address-table missing-arg success
`frontend/src/features/cli-labs/engine/commandEngine.js` (~line 474): `show mac address-table vlan` and `show mac address-table interface` with the arg missing still emit success events and canonical command log entries.
Fix: when the arg is missing, print `% Incomplete command.` and emit NO success event / command-log entry, matching how other incomplete commands behave in this engine.

## 4. MEDIUM — arp -a reads global MAC table
`frontend/src/features/cli-labs/engine/pcCommands.js` (~line 49): a PC's `arp -a` is derived from the switch-wide MAC table, so a PC shows entries for hosts it never talked to, even across VLANs.
Fix: track a per-PC ARP cache — populate it only when THAT PC pings (or is pinged, if the engine models that); `arp -a` renders only that PC's cache. Keep output format identical.

## 5. MEDIUM — sanity script has zero learn-switching coverage
`frontend/scripts/cli-engine-sanity.mjs` never loads `learn-switching.json`; W2T2 lesson-contract regressions pass silently.
Fix: add a completion drive for all learn-switching labs (same pattern as the existing foundations drive): load the pack, for each lab run the commands/PC actions that satisfy objectives + successCriteria, assert isLabComplete. Must cover dev-sw-act-06 via the `show interfaces status` path specifically (regression for fix #1).

## Files
- frontend/src/features/cli-labs/data/lessons/learn-switching.json
- backend/app/data/cli_labs/learn-switching.json (must stay byte-identical to frontend copy)
- frontend/src/features/cli-labs/engine/interfaceCommands.js
- frontend/src/features/cli-labs/engine/commandEngine.js
- frontend/src/features/cli-labs/engine/pcCommands.js
- frontend/scripts/cli-engine-sanity.mjs

## Acceptance
- `npm run cli:validate` passes
- `npm run cli:sanity` passes and now includes the learn-switching drive + dev-sw-act-06 status-path check
- `npm run build` passes (cd frontend)
- `cd backend && python -m pytest tests/ -q` passes
- Get-FileHash comparison: frontend and backend learn-switching.json identical
- Append summary to tasks/loop-log.md
