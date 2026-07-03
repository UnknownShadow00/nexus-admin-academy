# Wave 2 / Task 4 — Engine: STP / Rapid PVST+ and EtherChannel (LACP)

CONTEXT
Sections F and G of references/lesson-drafts/learn-switching.md teach spanning tree (loops, root election, PortFast, BPDU Guard) and EtherChannel (LACP, load sharing). READ both sections fully ("## Section F" through "## Section H") before implementing — mirror the exact commands, outputs, and failure behaviors the lessons teach. Follow the existing engine architecture: single-switch-pure engine modules (like trunking.js, networkSim.js), state on the switch state object, events registered in supportedEvents.js, multi-device awareness only via the context/deviceStates pattern established in W2T3.

SCOPE

1. STP (new engine module, e.g. engine/stpSim.js):
   - Commands (global config): `spanning-tree mode rapid-pvst` (and `pvst`), `spanning-tree vlan <id> priority <value>` (validate multiples of 4096, 0-61440), `spanning-tree vlan <id> root primary`
   - Interface config: `spanning-tree portfast`, `spanning-tree bpduguard enable`
   - `show spanning-tree` (and `show spanning-tree vlan <id>`): render root bridge ID (priority + MAC), local bridge ID, root/designated ports, port roles and states. Root election across a 2-switch topology: lowest (priority, MAC) wins; give each device a deterministic MAC derived from its id so lessons can predict the winner.
   - Port states: on a 2-switch loop (two parallel links), the non-root switch blocks one port (higher port number blocks). Lessons in Section F demonstrate a loop and how STP blocks it — match that narrative.
   - BPDU Guard: if a port has portfast + bpduguard and the topology delivers a BPDU (link to another switch), the port goes err-disabled; `show interfaces status` shows err-disabled; recover via `shutdown`/`no shutdown`.
   - Events per the existing naming scheme (config.stp-mode.set, config.stp-priority.set, config.portfast.set, config.bpduguard.set, cmd.show.spanning-tree, etc.) — register all in supportedEvents.js and validator.

2. EtherChannel (new engine module, e.g. engine/etherchannel.js):
   - Interface(-range) config: `channel-group <n> mode active|passive|on|desirable|auto`
   - Formation rules across a link pair: active/active, active/passive → LACP bundle; on/on → static bundle; on/active, active/auto etc. → no bundle (match IOS). Both physical links between the switches must be members for the lessons' 2-link bundles.
   - Creates logical `Po<n>` interface; `interface port-channel <n>` enters interface config for it; trunk/access config on the port-channel applies to members.
   - `show etherchannel summary`: flags (SU/SD, P for bundled ports), group listing.
   - STP interaction: a bundle counts as ONE STP port (no blocking between two switches connected only by one bundle).
   - Cross-switch ping (networkSim.js): a formed bundle whose port-channel (or members) is an operational trunk passes traffic like a trunk link; an unformed channel-group with mode mismatch leaves member links as individual links (STP blocks one).

3. Multi-switch plumbing: reuse W2T3's deviceStates/topology context. Reset reinitializes STP/EtherChannel state.

SANITY (cli-engine-sanity.mjs) — add:
- root election: lower priority wins; `root primary` takes over
- parallel links, no STP intervention config → one port blocking on non-root; show spanning-tree reflects it
- portfast+bpduguard on inter-switch link → err-disabled; shutdown/no shutdown recovers
- LACP: active/passive forms bundle (show etherchannel summary flags), active/auto does not; on/on forms
- bundle as trunk passes cross-switch ping; breaking the bundle (mode mismatch) falls back to individual links
- single-switch + existing multi-switch regressions unchanged

CONSTRAINTS
- No changes to existing lesson packs' behavior; all current sanity checks must keep passing.
- Immutability at the React boundary: LabRunner clones before engine mutation (existing pattern).
- Files stay under 800 lines — new modules rather than growing commandEngine.js; keep functions under 50 lines.
- No magic numbers: name constants (default priority 32768, priority step 4096, etc.).

ACCEPTANCE
- npm run cli:validate passes
- npm run cli:sanity passes including all new checks
- npm run build passes (frontend)
- cd backend && PYTHONPATH=. python -m pytest tests/ -q passes
- Append summary to tasks/loop-log.md, listing any spec deviations with reasons
