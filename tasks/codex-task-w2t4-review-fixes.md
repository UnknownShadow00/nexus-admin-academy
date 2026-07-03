# Wave 2 / Task 4 — Post-Review Fixes

Review findings on the W2T4 STP/EtherChannel diff. Fix all before E–H lesson conversion.

## 1. CRITICAL — show spanning-tree crash without multi-switch context
`frontend/src/features/cli-labs/engine/stpSim.js:84` `annotateRoles` dereferences `root.deviceId` but `rootBridge()` returns undefined when `switchIds(context)` is empty (single-switch lesson / no context). `renderVlan` line 99 already guards with a fallback — apply the same fallback in `annotateRoles` (treat the local device as root when no peers exist).

## 2. HIGH — PortFast edge ports missing from show spanning-tree
`stpSim.js:69` `activeStpPorts` only walks `topology.links` (switch-to-switch). Section F lessons set `spanning-tree portfast` on PC-facing access ports and expect them visible as `P2p Edge`. Include up, non-err-disabled interfaces that have a connected PC (PC devices reference their port via `connectedTo`/`switch`) or explicit portfast config; role Desg/FWD, Type `P2p Edge` when portfast.

## 3. HIGH — missing Section G show commands and PAgP
`etherchannel.js`: implement `show etherchannel detail` (Protocol: LACP/PAgP, per-member flags), `show lacp neighbor` (partner device id = peer hostname, e.g. SW2), `show pagp neighbor`. PAgP modes `desirable`/`auto` already parse per W2T3 spec grammar — ensure formation matrix: desirable/desirable, desirable/auto bundle; auto/auto does not; LACP and PAgP never interoperate; `show etherchannel summary` Protocol column shows LACP or PAgP accordingly. Register events (cmd.show.etherchannel-detail, cmd.show.lacp-neighbor, cmd.show.pagp-neighbor) in supportedEvents.js + validator.

## 4. HIGH — no channel-group missing arg
`etherchannel.js:190` `no channel-group` with no number removes config; must return `% Incomplete command.` with no state change or event.

## 5. MEDIUM — arg validation sweep (match existing error-class conventions)
- `spanning-tree vlan 0|4095 ...` (priority or root primary) → `% Invalid input detected` (only 1-4094 valid) — stpSim.js:147
- Missing args → `% Incomplete command.`: `spanning-tree mode`, `spanning-tree vlan`, `spanning-tree vlan 1 priority` — stpSim.js:173
- Reject trailing extra tokens: `spanning-tree mode rapid-pvst extra`, `show spanning-tree extra`, `show spanning-tree vlan 1 extra`, `interface port-channel 1 extra`, `channel-group 1 mode active extra` → `% Invalid input detected`
- `interface port-channel x` (non-numeric) → `% Invalid input detected`, not incomplete — etherchannel.js:169

## 6. MEDIUM — port-channel shutdown ignored by summary
`interfaceCommands.js:239` after `interface port-channel 1` + `shutdown`, `show etherchannel summary` still shows `SU`/`(P)`. Shutdown Po → flags `SD`, members not `(P)` (use `(D)`), bundle passes no traffic in networkSim.

## Sanity additions (cli-engine-sanity.mjs)
- show spanning-tree on a single-switch lesson state (no multi-switch context) → renders without throwing (regression for #1)
- portfast access port appears as P2p Edge (regression for #2)
- desirable/desirable bundles with Protocol PAgP; desirable/auto bundles; auto/auto does not; LACP-vs-PAgP mix does not; show lacp neighbor lists peer hostname
- no channel-group without arg → incomplete, config intact
- shutdown Po1 → summary SD, cross-switch ping over that bundle fails; no shutdown restores

## Acceptance
- npm run cli:validate / cli:sanity / build pass; backend pytest (PYTHONPATH=.) passes
- All existing sanity checks unchanged and passing
- Append summary to tasks/loop-log.md
