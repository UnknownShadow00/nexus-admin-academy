# Nexus V2 Phase 3A — A+ Content Expansion Batch 1

Status: development only. Production deployment, migration, seeding, account
changes, and V2 enablement are outside this phase.

## Selection decision (recorded before implementation)

The batch uses only objective codes present in Nexus' stored representative
220-1201/220-1202 objective files.

| Module | Version | Official objectives | Why it matters for support work | Practical potential | Existing Nexus reuse candidates |
|---|---|---|---|---|---|
| PC Components, Power & Safe Upgrades | 220-1201 | 3.4, 3.5 | Desktop technicians must identify compatible motherboards, CPUs, expansion cards, power connectors, and an adequate replacement PSU without damaging equipment. | Guided, no-VM component/compatibility and PSU-sizing worksheet using a real or supplied machine specification. | Legacy Hardware lessons for motherboard form factors, expansion slots/connections/compatibility, CPU features, expansion cards, cooling, and computer power; Motherboard, CPU, Power Supply, and Core PC Hardware Troubleshooting quizzes. |
| Windows Support Tools & Client Configuration | 220-1202 | 1.1, 1.2, 1.6 | Entry-level technicians must recognise supported operating systems, collect evidence with safe Windows commands, and configure or diagnose ordinary client networking features. | Guided activity on any Windows 10/11 machine using `sfc /verifyonly`, `chkdsk` read-only inspection, `netstat`, `gpupdate`, and Windows network settings. | Legacy Windows Command-Line Diagnostics lab/questions; existing IP Configuration command lesson as review/deep-dive material; existing Windows environments. |
| Windows Performance, Startup & Application Troubleshooting | 220-1202 | 3.1 | Slow PCs, boot failures, crashes, shutdowns, and application failures are everyday service-desk work and require safe evidence-first triage. | Guided Windows triage practical using Task Manager, Reliability Monitor/Event Viewer, startup apps, disk space, and a verification record. | Existing slow-PC Service Desk scenario and PDF-editor crash ticket; legacy Core PC Hardware Troubleshooting and Windows diagnostic content; existing Windows lab infrastructure. |

The order is intentional: the existing IP Configuration module establishes
client-network evidence gathering; hardware follows with physical component
judgment; Windows support tools then reuses the command habit at Core 2 depth;
Windows troubleshooting applies those tools to common incidents.

## Existing-content audit

The audit classified relevant material before any new bank item was authored.
The final per-item manifest is maintained in the question-bank `audit_status`
and provenance fields where supported, with this summary as the human-readable
record.

| Existing material | Classification | Decision |
|---|---|---|
| Motherboard form-factor, expansion slot, connection, compatibility lessons | KEEP / EDIT | Reuse the linked Professor Messer sources and concepts; rewrite concise V2 Markdown around official 3.4 wording. |
| CPU Features and Expansion Cards lessons | KEEP / EDIT | Reuse concepts and links; combine into a logical beginner lesson instead of duplicating legacy lesson granularity. |
| Computer Power lesson and Power Supply Quiz | KEEP / EDIT | Reuse job-relevant wattage, connectors, modularity, input voltage, and safe replacement concepts for 3.5. |
| Storage/RAM lessons and quizzes | NOT RELEVANT for this batch | Good candidates for a later storage/memory module; not forced into objectives 3.4/3.5. |
| Core PC Hardware Troubleshooting Quiz | EDIT / DUPLICATE check | Retain only component/power symptoms directly supporting 3.4/3.5; defer general storage/display questions. |
| Windows Command-Line Diagnostics lab/questions | KEEP / EDIT | Reuse command intent and safe diagnostic workflow for 1202 objective 1.2, with explicit provenance. |
| IP Configuration Windows-command material | DUPLICATE / REVIEW | Do not reteach `ipconfig`, `ping`, and `nslookup`; label their Windows-tools appearance as review and add new `netstat`, `gpupdate`, `sfc`, and `chkdsk` depth. |
| Slow-PC/high-startup-CPU scenario | KEEP | Map the validated scenario to Windows troubleshooting 3.1 when its stable engine reference resolves. |
| PDF editor crash ticket | KEEP | Useful existing troubleshooting example; link to the authoritative Service Desk flow rather than recreating it. |
| USB headset and printer tickets | NOT RELEVANT | Useful future peripherals/printing content, but outside these selected objective mappings. |
| Unknown-source legacy questions | ARCHIVE CANDIDATE unless provenance can be confirmed | Never relabel as owned; exclude from this batch rather than silently importing. |

## Implementation record

### Module content and mappings

| Module key | Lessons | Objective mapping | Bank | Quick Checks | Module Quiz | Explain |
|---|---:|---|---:|---|---|---:|
| `module.aplus.core1.hardware_support` | 5 | 220-1201 3.4, 3.5 | 25 | 5 × 4–5 | 12 displayed, 70% | 2 |
| `module.aplus.core2.windows_support_tools` | 5 | 220-1202 1.1, 1.2, 1.6 | 25 | 5 × 4–5 | 12 displayed, 70% | 2 |
| `module.aplus.core2.windows_troubleshooting` | 5 | 220-1202 3.1 | 25 | 5 × 4–5 | 12 displayed, 70% | 2 |

Every lesson is maintainable Markdown with the eight approved sections. Labels
are intentionally mixed: hardware platform/component knowledge includes
`working_knowledge`; OS/filesystem awareness is not overstated; safety,
evidence gathering, power, client configuration, and troubleshooting are
`job_critical`; IP tools are `review`, and safe upgrade/client settings/fix
verification are `deep_dive` where they build on earlier teaching.

### Resources

Nine new data-driven resource records supply required anchors for all 15
lessons. Hardware reuses the existing free Professor Messer 220-1201 course
anchors. Windows uses linked Microsoft lifecycle, Windows command, file-share,
network-settings, recovery, performance, and event-troubleshooting
documentation. Content is linked, never copied or rehosted. No URL was added
to React or Python application logic. Final link verification followed redirects
and returned HTTP 200 for every new anchor; two initially stale deep links were
replaced with stable official Microsoft pages before completion.

### Question sources and quality review

Each bank contains 20 single-choice scenario/knowledge questions, three short
answers, and two rubric-backed free responses. All 75 rows have objective,
module, importance, source, and permission metadata; all are draft and remain
invisible until editorial validation.

| Module | Existing Nexus items adapted with explicit provenance | Newly authored gap-fill | Final |
|---|---:|---:|---:|
| Hardware | 6 | 19 | 25 |
| Windows Support Tools | 4 | 21 | 25 |
| Windows Troubleshooting | 4 | 21 | 25 |
| **Total** | **14** | **61** | **75** |

Quality review checked answer defensibility, plausible alternatives, A+ depth,
objective fit, duplicate fingerprints, explanations, job relevance, and safe
tool use. Notable corrections made during review: physical fit is never
presented as complete platform compatibility; modular PSU cables are not
treated as interchangeable; ping is not described as proof of application
health; SFC and CHKDSK scopes remain distinct; firewall disablement and broad
share permissions are rejected as shortcuts; performance correlation is not
presented as proven cause. Unknown-source legacy questions were excluded.

### Practicals and Service Desk

- Hardware: guided/no-VM `A+ Practical — Plan a Compatible PC Upgrade`.
  Students cite a service manual and produce compatibility, ESD, rollback, and
  verification evidence. A VM would add no value.
- Windows Support Tools: guided existing-Windows activity `A+ Practical —
  Collect a Windows Support Snapshot`. It uses read-only evidence; repair
  switches are explicitly excluded.
- Windows Troubleshooting: guided existing-Windows activity `A+ Practical —
  Build a Windows Triage Record`. A healthy or mentor-prepared machine is
  sufficient; no artificial fault is required.
- Service Desk is not forced into hardware or tool-identification modules.
  Windows troubleshooting reuses validated `INC2403`, the PDF-editor crash
  investigation, and links to the authoritative Service Desk application.
  No scenario or ticket engine was created.

### Student and mentor scaling changes

The generic certification entry now lists all complete-formula modules with
`Not started`, `In progress`, or `Complete`, while keeping one primary
`Continue learning` action. Current is the first incomplete module in stable
Core 1 → Core 2/module order; when one module is complete, entry composition
derives the next incomplete module. Position is not stored.

Service Desk remains optional at module level, so a pedagogically inappropriate
ticket is not required merely to make a module appear. Quick Check, Module
Quiz, practical, and Explain remain the core formula for these job-critical
modules. Module completion is still independent per module.

The mentor cohort response now advertises all loaded lesson-bearing modules.
The existing cohort page has one module selector and preserves the selected
module in student-detail links. The same report, miss aggregation, objective
wording, grading queue, practical, Service Desk, notes, and Explain components
render every module; there are no module-specific mentor pages.

Browser testing exposed a generic concurrency edge: React's duplicate
development requests could both try to materialize the same authoritative
Service Desk progress row. `record_activity` now contains the unique insert in
a savepoint and reuses the winning row. This is a generic idempotency fix, not
module-specific behavior.

### Objective coverage

Reference-module coverage is 220-1201 **2.5, 5.1, 5.7**. New coverage is:

- Hardware: 220-1201 **3.4, 3.5**
- Windows Support Tools: 220-1202 **1.1, 1.2, 1.6**
- Windows Troubleshooting: 220-1202 **3.1**

Across the selected four student modules this is 9 of the 26 representative
stored A+ objectives (34.6%). Nexus also already has a pre-existing foundation
lesson mapped to 220-1201 2.1, so the loader's total objective-coverage report
moves from 4/26 (15.4%) before Batch 1 to 10/26 (38.5%) after Batch 1.

Remaining stored representative objectives:

- 220-1201: 1.1, 1.2, 1.3, 2.2, 3.1, 4.1, 4.2
- 220-1202: 2.1, 2.4, 2.7, 3.2, 3.4, 4.1, 4.2, 4.7

These are planning inputs, not a reason to manufacture lessons. Storage/RAM,
peripherals, and additional hardware-troubleshooting material found in the
legacy audit remain candidates for later approved A+ batches.

### Verification

- Backend: 726 tests passed after the final generic concurrency fix (baseline
  722 plus four Phase 3A tests). Tests cover idempotency, valid objectives,
  duplicate keys/fingerprints, bank provenance/mix, four-module entry/Continue,
  independent progress, coverage, mentor composition, no TrainingWeek writes,
  and existing legacy behavior.
- Frontend: 39 tests passed (baseline 36 plus multi-module student and mentor
  coverage, including a Core 2 label regression); production build passed. No lint/typecheck script exists. The
  previously documented >500 kB bundle warning remains and was not allowed to
  derail curriculum work. `npm audit` reports 0 vulnerabilities.
- Browser: disposable schema-0066 scratch database only. The student flow
  loaded all four modules, opened a new hardware lesson/resource, exercised the
  reference lesson, Quick Check, Module Quiz, practical, Service Desk, Explain,
  persistence, unknown-module state, and 390 px mobile layout. The mentor flow
  saw exactly five disposable students, switched reference → hardware →
  reference, preserved module context in detail, reviewed misses/weaknesses,
  graded Explain with history, and passed 768 px tablet overflow sanity. A
  student bearer token received 403 from mentor data. Final reruns: student 1
  passed; mentor/security 2 passed.
- Scratch teardown removed the temporary database and processes. No production
  account was used.

### Production read-only verification

The service is active and `/health` returned 200. Production remains
`0064_v2_ai_grading_infrastructure`; 0065/0066 are absent; V2 certification,
lesson metadata, question metadata, and module-assessment tables contain zero
rows; 0065/0066 activity/submission tables are absent; seven students remain.
`backend/nexus.db` SHA-256 is unchanged at
`cb344b1bae6542f9aab26bd6b3284e1aa1897cb53bbc21005bcb2aee38ddf41b`.

No migration was created. Nothing was deployed, seeded, migrated, or enabled
in production. The development-only pip 26.1.2 advisory was left documented;
changing packages was outside this workspace-write curriculum task.

### Deferrals and recommendation

The only known rough edges are the existing bundle-size warning, the separate
development pip advisory, and the intentionally representative (not complete)
stored objective YAML. Deeper hardware Service Desk work awaits a naturally
server-verifiable scenario; no fake ticket was added.

Recommendation: **continue A+ Batch 2** after owner review of these three
modules and editorial validation/publication of the draft banks. The generic
module pattern scaled cleanly; no architecture revision is indicated.
