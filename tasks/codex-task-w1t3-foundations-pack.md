# Wave 1 / Task 3 — Learn Network Foundations Pack + Collapsible Topics UI

WHAT TO BUILD
Two deliverables:
A) Convert references/lesson-drafts/learn-network-foundations.md into a CLI Labs lesson pack (7 labs) using the new step schema.
B) Make the CLI Labs page group lessons into collapsible topic sections.

READ FIRST
- references/lesson-drafts/learn-network-foundations.md — the source content (7 labs: 6 lessons + 1 checkpoint)
- frontend/src/features/cli-labs/data/lessons/meet-the-cli.json — existing pack format
- frontend/src/features/cli-labs/components/StepPanel.jsx + steps/ — the step widgets (already built)
- frontend/scripts/validate-cli-labs.mjs — schema rules your JSON must pass
- frontend/src/features/cli-labs/engine/commandEngine.js — note the NEW events: pc.ping.success, pc.ping.failed, cmd.show.mac-address-table, config.mac-static.set (just added)

DELIVERABLE A — the pack
Create frontend/src/features/cli-labs/data/lessons/network-foundations.json:
- compartmentId: "network-foundations", compartmentTitle: "Learn Network Foundations", vendorId: "cisco-ios"
- sharedTopology: switch + PC-A (g0/1, vlan 10, ip 192.168.10.10) + PC-B (g0/2, vlan 10, ip 192.168.10.20); interfaces g0/1 and g0/2 up/access, vlan 10 named SALES. Lesson 6 and the checkpoint additionally need VLAN 20 named ENG with port g0/3 — use per-lesson startState for that (see meet-the-cli lesson 6 for the startState pattern).
- 7 lessons with ids EXACTLY as in the MD (dev-nf-encap-001, dev-nf-frame-001, dev-nf-mac-001, dev-nf-mac-static-001, dev-nf-arp-001, dev-nf-broadcast-001, dev-nf-checkpoint-001), chained via nextLabId in MD order.
- Per lesson: title, difficulty, estimatedMinutes, scenario (from MD Scenario section), hints (from MD Hints; checkpoint has NO hints — omit or empty array), objectives, steps.
- Objectives: convert the MD Objectives bullets into trigger-based objectives. Trigger mapping:
  * "enable"/privileged EXEC → mode.privileged.enter
  * "configure terminal" → mode.config.enter
  * "show interfaces status" → cmd.show.interfaces-status
  * "show mac address-table" → cmd.show.mac-address-table
  * "show vlan brief" → cmd.show.vlan-brief
  * PC ping → pc.ping.success
  * "mac address-table static ..." → config.mac-static.set with expectedArg "aaaa.bbbb.cccc"
  * "end" back to privileged → mode.privileged.enter
- Steps: convert every "Lesson Steps" entry in MD order. Types map 1:1 (explanation, multiple-choice, observe, forward-decision, hex-input, frame-builder).
  * multiple-choice / forward-decision: the MD gives question + correct-answer explanation but NO options. AUTHOR 4 plausible options per question (3 distractors + 1 correct, technically accurate, CCNA-level). correctIndex must match the explanation. Vary correctIndex position across questions.
  * hex-input: derive answer from explanation (e.g. EtherType IPv4 → answer "0800", accept ["0800","0x0800","800"]; binary 10101010 → "aa" accept ["aa","0xaa"]; broadcast MAC → "ffffffffffff" accept ["ffffffffffff","ffff.ffff.ffff","ff:ff:ff:ff:ff:ff"]).
  * frame-builder: fields ["Destination MAC","Source MAC","EtherType","Payload","FCS"], correctOrder [0,1,2,3,4].
  * observe: body = MD step text, objectiveIds = the lesson objectives that step exercises, explanation = MD Explanation.
- successCriteria per lesson: mirror the key proof (e.g. requiredCommands ["show mac address-table"] or requiredState for the static entry lesson if the engine exposes it; keep consistent with how objectiveTracker computes completion — all objectives met must remain the effective gate).
- Register in frontend/src/features/cli-labs/data/lessonCatalog.js (import + append to cliLabCompartments).
- Copy the pack to backend/app/data/cli_labs/network-foundations.json and wire it into the backend seed the same way meet-the-cli.json is wired (see backend/app/services/cli_lab_seed.py and backend/seed.py). Keep both JSON copies identical.

PC TERMINAL VISIBILITY (small LabRunner change)
LabRunner currently shows PcTerminal only when lesson.successCriteria.requiredPcAction exists. Extend: also show it when any lesson objective trigger starts with "pc." — foundations lessons need the PC terminal for ping.

DELIVERABLE B — collapsible topics on CliLabsPage
frontend/src/pages/CliLabsPage.jsx:
- Each compartment becomes a collapsible section: header row = chevron icon + compartment title + per-topic progress pill ("3/7 complete") — clicking toggles expand/collapse.
- ALL sections collapsed by default.
- Expanded section shows the existing lesson card grid unchanged.
- Keep overall completion counter in PageHeader. Tailwind only, dark-mode variants, match existing styles. Use lucide-react ChevronDown/ChevronRight.
- State: local useState set of expanded compartmentIds — no persistence needed.

CONSTRAINTS
- Do not modify meet-the-cli.json content (catalog import line changes only).
- Immutability patterns, files <400 lines (the JSON pack is exempt).
- No new npm dependencies. 

ACCEPTANCE
- npm run cli:validate passes (now 2 files, 25 lessons).
- npm run cli:sanity passes.
- npm run build passes (npm.cmd if npm.ps1 blocked).
- cd backend && python -m pytest tests/ -q passes (seed changes must not break tests; python -m py_compile on changed backend files).
- Every MD lesson step appears in the JSON in order; checkpoint lab has no hints.
- Append summary to tasks/loop-log.md.
