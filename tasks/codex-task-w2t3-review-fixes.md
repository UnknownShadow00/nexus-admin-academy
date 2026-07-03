# Wave 2 / Task 3 — Post-Review Fixes

Code review findings on the W2T3 multi-switch/trunking diff. Fix all 4 before the E–H lesson conversion, since those lessons depend on these behaviors.

## 1. HIGH — cross-switch ping ignores encapsulation requirement
`frontend/src/features/cli-labs/engine/networkSim.js:trunkPasses` never checks `trunkEncapsulation`; spec requires dot1q encapsulation to be honored where the lesson requires it.
Fix: support an `encapsulationRequired: true` flag on an interface's startState. In `trunkPasses`, if either end has `encapsulationRequired` and its `trunkEncapsulation !== "dot1q"`, the trunk does not pass traffic. Ends without the flag behave as today (2960-style dot1q default). Add the flag to validate-cli-labs.mjs's known startState interface keys.

## 2. MEDIUM — allowed-VLAN list parsing: no ranges, accepts garbage
`frontend/src/features/cli-labs/engine/trunking.js:normalizeAllowedVlans` stores `10-20` as the literal string (VLAN 10 then NOT allowed) and accepts non-numeric tokens like `10,abc`.
Fix: expand `a-b` ranges into individual VLAN ids (cap ids at 1–4094); reject any token that is not a number or valid range at the COMMAND level (`switchport trunk allowed vlan ...` prints `% Invalid input detected` and emits no event). `normalizeAllowedVlans` itself stays a pure normalizer but must expand ranges.

## 3. MEDIUM — nonegotiate ignored by trunk formation
`frontend/src/features/cli-labs/engine/trunking.js:isOperationalTrunk` ignores `nonegotiate`.
Fix (match IOS):
- `switchport nonegotiate` on a `dynamic auto`/`dynamic desirable` port → command rejected: `Command rejected: Conflict between 'nonegotiate' and 'dynamic' status.` (no state change, no event)
- A port with mode trunk + nonegotiate sends no DTP: peer in dynamic auto/desirable does NOT form a trunk; trunk/trunk still forms.

## 4. MEDIUM — malformed native VLAN arg error
`frontend/src/features/cli-labs/engine/commandEngine.js` (~line 450): `switchport trunk native vlan abc` returns `% Incomplete command.`
Fix: missing arg → `% Incomplete command.`; non-numeric or out-of-range (1–4094) arg → `% Invalid input detected`. No event on either.

## Sanity additions (cli-engine-sanity.mjs)
- encapsulationRequired end without dot1q → cross-switch ping fails; set encapsulation → succeeds
- `switchport trunk allowed vlan 10-20` allows VLAN 15; `10,abc` rejected with no event
- nonegotiate on dynamic port rejected; trunk+nonegotiate vs dynamic desirable → no operational trunk; trunk+nonegotiate vs trunk → trunk
- native vlan `abc` → invalid input, no event

## Files
- frontend/src/features/cli-labs/engine/networkSim.js
- frontend/src/features/cli-labs/engine/trunking.js
- frontend/src/features/cli-labs/engine/commandEngine.js
- frontend/scripts/validate-cli-labs.mjs
- frontend/scripts/cli-engine-sanity.mjs

## Acceptance
- `npm run cli:validate` passes
- `npm run cli:sanity` passes including all new checks above
- `npm run build` passes (frontend)
- `cd backend && python -m pytest tests/ -q` passes (run with PYTHONPATH=. if needed)
- Existing single-switch and multi-switch sanity checks unchanged and passing
- Append summary to tasks/loop-log.md
