# Wave 2 / Task 5 — Convert Learn Switching Sections E–H (lessons 24–44)

CONTEXT
Final Wave 2 task. Convert sections E–H of references/lesson-drafts/learn-switching.md (lessons 24–44, 21 labs) into the learn-switching CLI lab pack, exactly like sections A–D were converted. READ the source sections fully. The engine already supports everything needed: multi-switch topologies + device tabs, 802.1Q trunking/DTP (W2T3), STP/Rapid PVST+/PortFast/BPDU Guard and EtherChannel LACP/PAgP (W2T4). If a lesson step needs a behavior the engine truly lacks, note it in your summary rather than faking it with an explanation step.

SCOPE
- Append the 21 labs to frontend/src/features/cli-labs/data/lessons/learn-switching.json following the existing lab schema (ids dev-sw-act-24 … dev-sw-act-44, topic sections matching the source: E = trunking, F = spanning tree, G = EtherChannel, H = final build/repair).
- Multi-switch lessons declare devices/links per the W2T3 topology schema; device-scoped objectives use the "device" field; PC lists may span both switches.
- Where a lesson requires the encapsulation command, set encapsulationRequired on the relevant startState interfaces.
- Exam/final labs (Section H and any lesson marked exam) get NO hints array.
- Every objective trigger must reference an event the engine emits (supportedEvents.js); every successCriteria must be reachable — verify with the completion drive.
- Copy the finished JSON byte-identically to backend/app/data/cli_labs/learn-switching.json.
- lessonCatalog.js: confirm the pack picks up the new labs (it loads the whole JSON — adjust section metadata if the catalog lists topics explicitly).

SANITY (cli-engine-sanity.mjs)
- Extend the learn-switching completion drive to run ALL new labs end-to-end: for each, execute the commands/PC actions that satisfy every objective and successCriteria, assert isLabComplete. Include at least one out-of-order-commands case and one repair-style lab driven only via its success path.

ACCEPTANCE
- npm run cli:validate passes and reports 69 lessons across 3 files
- npm run cli:sanity passes including the full E–H drive
- npm run build passes (frontend)
- cd backend && PYTHONPATH=. python -m pytest tests/ -q passes
- Get-FileHash: frontend and backend learn-switching.json identical
- Append summary to tasks/loop-log.md, listing any engine gaps encountered
