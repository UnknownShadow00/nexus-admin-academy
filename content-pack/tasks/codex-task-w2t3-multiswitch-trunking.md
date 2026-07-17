# Wave 2 / Task 3 — Engine + UI: Multi-Switch Topologies and 802.1Q Trunking

CONTEXT
Sections E–H of references/lesson-drafts/learn-switching.md require TWO student-configurable switches (SW1, SW2) joined on g0/24, with PCs hanging off each. Students run commands on both devices ("On SW2, type…"). READ sections E and the trunking lessons (from "## Section E" to "## Section F") before implementing — mirror the exact behaviors the lessons teach.

ARCHITECTURE (follow this shape; flag in your summary if you had strong reasons to deviate)

1. Multi-device state (LabRunner level, engine stays single-switch-pure):
   - Lesson topology may declare multiple switch devices: `devices: [{ id: "SW1", type: "switch", hostname: "SW1" }, { id: "SW2", ... }, PCs with `connectedTo` + `switch: "SW1"` ]` and a `links` array: `[{ a: "SW1:g0/24", b: "SW2:g0/24" }]`. Single-switch lessons keep today's shape — full backward compatibility, zero changes to existing packs.
   - LabRunner: when topology has 2+ switches, hold a state map `{ [deviceId]: switchState }` + per-device terminal lines; render device tabs above the terminal (Tailwind, dark-mode, active tab highlighted). Commands route to the active device's state via existing runCommand.
   - Events get tagged with the originating device: LabRunner wraps results, adding `device: activeDeviceId` to each event. objectiveTracker: objectives may declare optional `"device": "SW2"` — matchesTrigger then also requires event.device === objective.device. Objectives without device match any (backward compatible). Update validate-cli-labs.mjs: device value must exist in the lesson/shared topology when present.

2. Trunking commands (interface config mode, in engine):
   - `switchport mode trunk` → config.switchport-mode.set arg "trunk"
   - DTP negotiation (lesson dev-sw-act-25 step 4): `switchport mode dynamic desirable` and `switchport mode dynamic auto` → config.switchport-mode.set arg "dynamic desirable"/"dynamic auto"; `switchport nonegotiate` → config.nonegotiate.set. Trunk formation rule across a link: trunk/trunk, trunk/auto, desirable/desirable, desirable/auto → operational trunk; auto/auto or access on either end → no trunk. show interfaces switchport must show Administrative Mode (configured) vs Operational Mode (negotiated result); show interfaces trunk Mode column shows "on"/"desirable"/"auto" accordingly. The network evaluator must use the OPERATIONAL trunk state.
   - `switchport trunk encapsulation dot1q` → config.trunk-encapsulation.set
   - `switchport trunk allowed vlan <list>` (set) and `switchport trunk allowed vlan add <id>` → config.trunk-allowed.set / config.trunk-allowed.add; store allowedVlans (default "all")
   - `switchport trunk native vlan <id>` → config.trunk-native.set
   - `show interfaces trunk` → cmd.show.interfaces-trunk: renders Port/Mode/Encapsulation/Status/Native vlan + allowed vlans lines from state
   - `show interfaces switchport` already exists from W2T1 — extend to include trunk fields (admin mode, oper mode, encapsulation, native vlan, allowed list)

3. Neighbor discovery:
   - `show cdp neighbors` → cmd.show.cdp-neighbors; `show lldp neighbors` → cmd.show.lldp-neighbors. Render from topology links: neighbor device id, local/remote interface, capability S for switches. Works only on multi-switch lessons; on single-switch lessons renders an empty table.

4. Cross-switch ping (network evaluator — new engine module, e.g. engine/networkSim.js):
   - `evaluatePcPing(deviceStates, topology, sourcePcId, targetIp)`: succeeds when — target PC exists; both PCs' access interfaces up with matching VLIDs; if PCs are on different switches, every inter-switch link on the path must satisfy: both ends switchport mode trunk (with dot1q encapsulation configured where the lesson's startState requires it), VLAN allowed on both ends' allowed lists, AND for untagged/native traffic (PC VLAN == either side's native vlan) the native VLANs must MATCH on both ends (mismatch = fail — this is lesson dev-sw native-mismatch repair).
   - On success: BOTH switches learn MACs — local PC on its access port, remote PC on the trunk port (g0/24). This is what "trace a frame across two switches" inspects.
   - Cross-switch ping transcript (lesson dev-sw-ms-001 step 5 "step through the packet transcript"): when the path crosses a trunk, the ping output must narrate the path before the echo replies, e.g. lines: access ingress on SW1 g0/1 (VLAN 10, untagged) → 802.1Q tag added on SW1 g0/24 → crosses trunk → tag removed at SW2 g0/24 → access egress SW2 g0/1. Keep it to ~5 compact lines; same-switch pings keep the existing shorter transcript.
   - PC terminal: in multi-switch lessons the PC list may include PCs on both switches; PcTerminal gains a PC selector (tabs or dropdown) when more than one PC exists. Each PC's ping runs from that PC's identity. pc.ping.success events include device tag of the PC id (objectives can target specific PCs via expectedArg on the raw command instead — keep it simple: eventArg stays the raw command).

5. Reset/restart must reinitialize ALL device states.

SANITY (cli-engine-sanity.mjs) — add:
- two-switch lesson: access-only inter-switch link → cross-switch ping fails; configure trunk both ends → succeeds; MAC learned on trunk port of remote switch
- native vlan mismatch → vlan-1 PC ping fails; match natives → succeeds
- allowed-list pruning: remove VLAN from one end → that VLAN's ping fails; `allowed vlan add` restores
- device-scoped objective: event from SW1 does NOT complete an objective with device "SW2"
- single-switch lessons: unchanged behavior (run one meet-the-cli and one foundations completion as regression)

CONSTRAINTS
- Zero changes to existing lesson JSON files. Existing packs must behave identically.
- Files <400 lines each for new components; engine modules <800.
- Tailwind only, dark-mode variants. No new npm deps. Frontend only.

ACCEPTANCE
- npm run cli:validate, npm run cli:sanity, npm run build pass.
- Append entry to tasks/loop-log.md with a list of every new event id (needed for the section E–H conversion task).
