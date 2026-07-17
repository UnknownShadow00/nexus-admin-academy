# Wave 2 / Task 2 — Learn Switching Pack, Sections A–D (labs 1–23)

WHAT TO BUILD
Convert sections A–D of references/lesson-drafts/learn-switching.md (lessons 1–16 + Exam 1 + lessons 18–22 + Exam 2 + lesson 23 if present — everything BEFORE "## Section E") into a new pack. Sections E–H come in a later task and will be APPENDED to the same pack file — structure the JSON so appending lessons is trivial.

READ FIRST
- references/lesson-drafts/learn-switching.md sections A–D (through "EXAM: Exam 2: Access Ports")
- frontend/src/features/cli-labs/data/lessons/network-foundations.json — the reference conversion (format, steps, objectives style)
- frontend/src/features/cli-labs/engine/commandEngine.js — the port-admin events just added (config.description.set, mode.interface-range.enter, config.access-vlan.set, cmd.show.interfaces, cmd.show.version, cmd.show.mac-address-table-dynamic/-vlan/-interface, cmd.show.running-config-interface, config.vlan-name.set, etc.)

PACK
Create frontend/src/features/cli-labs/data/lessons/learn-switching.json:
- compartmentId: "learn-switching", compartmentTitle: "Learn Switching", vendorId: "cisco-ios"
- sharedTopology: single switch + PCs per the MD's dominant setup (PC-A g0/1 192.168.10.10, PC-B g0/2 192.168.10.20, vlan 10; adjust per MD). Lessons with different device/VLAN/interface needs use per-lesson startState/topology overrides — mirror each lesson's Scenario exactly (IPs, ports, VLAN names SALES/ENG/HR/IT, pre-broken states for repair lessons).
- Lesson ids EXACTLY the MD Lab IDs (dev-sw-act-01 … dev-sw-act-23), chained nextLabId in MD order.
- sectionTitle field on each lesson: "Section A — Port Basics" etc. (derive names from MD section content; keep short). The UI does not render it yet — it is forward-looking metadata.

CONVERSION RULES (same as network-foundations, plus lessons learned)
1. DO NOT convert the MD's first summary Objectives bullet into an objective — it duplicates the actionable bullets. Objectives = actionable command bullets only. NO consecutive duplicate triggers (tracker completes one objective per command).
2. Steps: every "Lesson Steps" entry, in order, types map 1:1. MCQ/forward-decision: author 4 technically accurate options (3 distractors + correct), correctIndex varies, consistent with the step's Explanation. hex-input: derive answer + accept variants. frame-builder: fields + correctOrder from the step content. observe: body from MD, objectiveIds referencing this lesson's objectives, explanation from MD.
3. Exams (dev-sw-act-17, dev-sw-act-23): hints omitted/empty, steps still converted.
4. Repair/broken-state lessons (e.g. "Restore the Silent Port", "Repair the VLAN Database", "Wrong Desk, Wrong VLAN"): encode the broken state in startState so the student experiences the fault (shutdown ports, wrong accessVlan, missing VLANs).
5. successCriteria per lesson: requiredState/requiredCommands mirroring the lesson's proof, consistent with objectives as the effective gate. For repair lessons, use requiredState so completion reflects the FIXED state (check SUPPORTED_REQUIRED_STATE_KEYS in objectiveTracker.js; if a lesson needs a state key that is not supported, add it to stateMatchesValue + the frozen list — e.g. interface descriptions or accessVlan checks).
6. If a lesson requires an engine command/event that does NOT exist, STOP converting that lesson, implement the missing command in the engine following existing idioms, add a sanity assertion, then continue. List every engine addition you made in your final summary.
7. PC ping targets must match per-lesson topology IPs.

REGISTER + SEED
- Import + append the compartment in frontend/src/features/cli-labs/data/lessonCatalog.js.
- Copy identical JSON to backend/app/data/cli_labs/learn-switching.json, wire into backend seed exactly like network-foundations (cli_lab_seed.py glob/registry — check whether it auto-discovers *.json or needs an explicit entry).

ACCEPTANCE
- npm run cli:validate passes (3 files, 48 lessons).
- npm run cli:sanity passes.
- npm run build passes.
- Runtime completion check: script-drive all 23 new labs to completion via their objective commands (include at least one out-of-order variation); report any lab that cannot complete.
- cd backend && python -m pytest tests/ -q passes; py_compile changed backend files.
- Frontend/backend JSON copies hash-identical.
- Append entry to tasks/loop-log.md.
