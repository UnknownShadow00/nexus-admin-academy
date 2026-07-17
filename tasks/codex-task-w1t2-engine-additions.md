# Wave 1 / Task 2 — CLI Engine Additions: Ping, ARP, MAC Address Table

WHAT TO BUILD
Extend frontend/src/features/cli-labs/engine/commandEngine.js so the upcoming "Learn Network Foundations" lesson pack works. Three capabilities: PC ping with ARP transcript, switch MAC address table with dynamic learning, and static MAC entries.

CAPABILITY 1 — MAC address table state
- Add to baseState(): `macTable: []` — entries shaped `{ mac, vlan, port, type }` where type is "DYNAMIC" or "STATIC".
- Topology PCs already carry `ip` and `connectedTo` in lesson topology (see meet-the-cli.json sharedTopology). Assign each PC a deterministic fake MAC derived from its id (e.g. PC-A → "aaaa.aaaa.aa0a", PC-B → "bbbb.bbbb.bb0b" — any stable scheme is fine, document it in a comment).
- initialState(lesson) must read the lesson topology devices (lesson.topology or compartment sharedTopology passed on the lesson object) so ping can resolve PC IPs/ports/VLANs.

CAPABILITY 2 — PC ping command (runPcCommand)
- Support `ping <ip>` from the PC terminal.
- If the target ip matches another PC in the topology AND both PCs' switch interfaces are up (not shutdown) AND both are in the same VLAN: output a short transcript:
  1. ARP broadcast line: `ARP request: who has <ip>? tell <source ip> (broadcast ffff.ffff.ffff)`
  2. ARP reply line: `ARP reply: <ip> is at <target mac>`
  3. Four echo lines: `Reply from <ip>: bytes=32 time<1ms TTL=128`
  4. Summary line: `Ping statistics: 4 sent, 4 received, 0 lost`
  - On success: switch LEARNS both PC MACs — append DYNAMIC entries to state.macTable (mac, vlan of the access port, port from connectedTo) if not already present (no duplicates; a STATIC entry for the same mac is not overwritten).
  - Emit event `pc.ping.success` with eventArg = the raw command. Also emit `pc.ping.arp` is NOT needed — keep events minimal: `pc.ping.success` on success.
- If interfaces are down, different VLANs, or ip unknown: output `Request timed out.` x4 and summary `4 sent, 0 received, 4 lost`, emit event `pc.ping.failed`.
- Keep the existing ssh handling; unknown commands still return the existing error.

CAPABILITY 3 — Switch commands
- `show mac address-table` (privileged mode; also via `do` in config modes if the existing do-handling covers show commands generically): renders a table:
  ```
            Mac Address Table
  -------------------------------------------
  Vlan    Mac Address       Type        Ports
  ----    -----------       --------    -----
  10      aaaa.aaaa.aa0a    DYNAMIC     Gi0/1
  ```
  Sorted STATIC first then by vlan. Empty table renders header only. Event: `cmd.show.mac-address-table`. Support abbreviation via existing registry mechanics (canonical "show mac address-table", alias prefixes like "show mac"). 
- `mac address-table static <mac> vlan <id> interface <port>` (global config mode): validates mac format (xxxx.xxxx.xxxx hex groups) and that the interface exists in state.interfaces (accept g0/2 or gigabitethernet0/2 via existing normalizeIfName). Adds/replaces entry `{ mac, vlan, port, type: "STATIC" }`. Event: `config.mac-static.set`, eventArg = the mac. Invalid mac or unknown interface → IOS-style `% Invalid input detected` error output, no event.
- `no mac address-table static <mac> vlan <id> interface <port>`: removes the matching STATIC entry. Event: `config.mac-static.removed`. (Small addition, include it for completeness.)

FILES
- frontend/src/features/cli-labs/engine/commandEngine.js (main work — keep under 800 lines total; if it grows past that, extract a macTable helper module engine/macTable.js)
- frontend/scripts/cli-engine-sanity.mjs — add sanity assertions: ping success learns 2 DYNAMIC entries; ping to down interface fails; show mac address-table renders learned entries; static command adds STATIC entry visible in show output; static survives where dynamic would be absent before traffic.

CONSTRAINTS
- Follow existing engine idioms: registry entries with canonical/aliasPrefixes/validModes, makeEvent/normalizeResult, immutable-from-caller (caller clones state; in-engine mutation of the working copy matches existing style).
- No new npm dependencies. Frontend only — do not touch backend.
- Do NOT modify meet-the-cli.json or LabRunner.jsx.

ACCEPTANCE
- npm run cli:validate passes.
- npm run cli:sanity passes (including your new assertions).
- npm run build passes (npm.cmd on Windows if npm.ps1 blocked).
- Append summary to tasks/loop-log.md.
