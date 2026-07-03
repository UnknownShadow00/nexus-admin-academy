# Wave 2 / Task 1 — Engine: Port Administration Commands (Switching Sections A–D)

CONTEXT
Next task converts references/lesson-drafts/learn-switching.md sections A–D (lessons 1–23, single-switch labs) into a lesson pack. This task adds every engine command those lessons need. READ sections A–D of the MD first (roughly lines 1–1600, through "EXAM: Exam 2: Access Ports") and extract the exact commands/outputs the lessons exercise — the list below is my inventory; trust the MD where it is more specific.

COMMANDS TO ADD to frontend/src/features/cli-labs/engine/commandEngine.js (extract helpers to new engine/ modules if the file would exceed 800 lines — e.g. engine/interfaceCommands.js, engine/showCommands.js):

Interface config mode:
- `description <text>` — store on the interface; shows in running-config and show interfaces status renders nothing special (keep simple). Event: config.description.set, eventArg = text.
- `switchport mode access` — event: config.switchport-mode.set, eventArg "access".
- `switchport access vlan <id>` — assigns accessVlan; if the VLAN does not exist in state.vlans, create it implicitly with name VLANxxxx (real IOS behavior prints "% Access VLAN does not exist. Creating vlan <id>"). Event: config.access-vlan.set, eventArg = id.
- `speed <10|100|1000|auto>` and `duplex <half|full|auto>` — store on interface. Events: config.speed.set / config.duplex.set. Only if sections A–D lessons use them (check lesson 6 "Link Settings Audit"); skip if unused.

Global config mode:
- `interface range g0/X - Y` (also accept `gigabitethernet0/X - Y`, spaces optional around dash) — enters a range-config mode where interface subcommands apply to ALL interfaces in the range. Prompt: `Switch(config-if-range)#`. Event: mode.interface-range.enter, eventArg = normalized range. Subcommands inside range emit their normal events ONCE (not per interface).
- VLAN mode `name <text>` — if not already supported, event config.vlan-name.set, eventArg = name.

Privileged/show commands (respect existing abbreviation + do-prefix mechanics):
- `show interfaces` — per-interface blocks: name, up/down, description if set, speed/duplex. Keep output compact (3-4 lines per interface). Event: cmd.show.interfaces.
- `show running-config interface <name>` — renders just that interface's config stanza. Event: cmd.show.running-config-interface.
- `show mac address-table dynamic` / `... vlan <id>` / `... interface <name>` — filtered views of the MAC table. Events: cmd.show.mac-address-table-dynamic / -vlan / -interface. Plain `show mac address-table` keeps its existing event.
- `show version` — short fake banner: model WS-C2960X, IOS 15.2, uptime, base MAC. Event: cmd.show.version.
- `show interfaces status` — extend existing renderer to include description column if any interface has one (keep column alignment).

STATE
- Interfaces gain optional fields: description, speed, duplex. renderRunningConfig must include description/speed/duplex/switchport lines when set.
- Implicit VLAN creation from switchport access vlan must integrate with existing vlans map (ports list updated).

SANITY (frontend/scripts/cli-engine-sanity.mjs) — add assertions:
- interface range applies shutdown/no-shutdown + access vlan to all members
- switchport access vlan on missing VLAN auto-creates it and prints the notice
- show mac address-table filters (dynamic/vlan/interface) filter correctly
- show running-config interface renders description and access vlan
- description text with spaces stored intact

CONSTRAINTS
- Follow existing registry/event idioms. No behavior change to existing commands/events (meet-the-cli + network-foundations must be unaffected).
- Frontend only. No new npm deps. Immutable-from-caller conventions unchanged.

ACCEPTANCE
- npm run cli:validate, npm run cli:sanity, npm run build all pass.
- Existing packs unaffected (25 lessons still validate).
- Append entry to tasks/loop-log.md.
