# Nexus V2 Phase 3A.1 — Editorial Review

## Scope and methodology

This gate reviewed the 15 Phase 3A lessons and all 75 bank questions as
teaching material for beginner support technicians. It did not add a module,
change TrainingWeek, alter legacy progression, or mutate production.

Each lesson was read end to end against the stored 220-1201/220-1202 objective
text. Each question received an individual disposition in
`NEXUS_V2_PHASE_3A1_QUESTION_AUDIT.csv`: technical answer, distractors,
wording, explanation, objective fit, A+ depth, job value, duplication, and
provenance were checked. Claims that needed an external check were compared
with current Microsoft, Intel, component-manufacturer, or vendor material.
The legacy Nexus and archived permitted-import banks were searched read-only;
an existing question replaced a new item only when it was stronger.

## Lesson findings

All 15 lessons were reviewed and remain five lessons per module. Their content
status moved from `draft` to `published` after review. Significant corrections:

- **PC Components, Power & Safe Upgrades:** separated case form factor from
  board-specific socket/RAM compatibility; made thermal-paste application
  manufacturer-directed; distinguished a physical PCIe x16 slot from its
  electrical lane count; removed beginner PSU probing/multimeter advice; and
  limited electrical checks to an approved tester and safe isolation.
- **Windows Support Tools & Client Configuration:** added the destination-device
  caveat to exFAT selection; explained that a failed ping can result from ICMP
  filtering; clarified that plain `chkdsk` reports status while repair switches
  can require elevation and scheduling; and clarified that WinHTTP proxy output
  is not every application's proxy configuration.
- **Windows Performance, Startup & Application Troubleshooting:** changed
  “faulting module” from proof of root cause to an investigation lead and kept
  the sequence at A+ client-support depth.

The lessons define terminology before action and retain the approved concise
structure, workplace examples, safe tools, interview examples, and formative
Quick Checks. No material was expanded into Network+, server administration,
or advanced Windows administration.

## Official-objective alignment

- **Hardware (220-1201):** 3.4 is substantively covered across motherboards,
  CPU/cooling, and expansion cards; 3.5 is substantively covered through power
  supplies, connectors, symptom isolation, and replacement safety. General
  upgrade workflow supports those objectives but is not used to claim an
  additional safety objective. CPU cooling is supporting coverage inside 3.4,
  not a claim that every possible cooling subtopic is exhausted.
- **Windows support tools (220-1202):** 1.1 covers client OS/filesystem support
  boundaries; 1.2 covers the taught Windows command-line tools; 1.6 covers
  workgroups/domains/shares and client network settings. Each mapping is based
  on a full lesson and assessment coverage, not a passing mention.
- **Windows troubleshooting (220-1202):** 3.1 is substantively covered through
  method, performance, startup/shutdown, application crashes, verification, and
  documentation. Verification practice supports professional process but does
  not claim a separate Core 2 objective.

The certification versions and Core assignments are correct for the objective
YAML stored in Nexus. The local YAML is a representative curriculum subset, so
these mappings do not imply full coverage of every bullet in CompTIA's broader
published objective document.

## Question findings

All 75 questions were individually reviewed. The original state was 75
draft/unreviewed bank questions. Final dispositions are:

| Module | Approved unchanged | Edited then approved | Replaced then approved | Removed | Still needs review |
| --- | ---: | ---: | ---: | ---: | ---: |
| PC Components, Power & Safe Upgrades | 10 | 15 | 0 | 0 | 0 |
| Windows Support Tools & Client Configuration | 17 | 8 | 0 | 0 | 0 |
| Windows Performance, Startup & Application Troubleshooting | 11 | 12 | 2 | 0 | 0 |
| **Total** | **38** | **35** | **2** | **0** | **0** |

Edits removed giveaway distractors, corrected ambiguous multi-select keys,
made scenarios supply enough context for “best” answers, strengthened teaching
explanations, corrected mappings/tags, and tightened free-response rubrics. The
two replaced troubleshooting items now use stronger validated Nexus scenarios:
recurring system-drive growth and an Event 1000 faulting add-in investigation.
The final total remains 25 per module because every item cleared the gate, not
because the number was forced.

### Sources and provenance

The Phase 3A starting report counted 14 reused and 61 newly authored. Two newly
authored items were replaced with better validated Nexus questions, producing
this final source breakdown:

| Module | Newly authored | Nexus reused | Permitted ExamCompass adaptation | Total |
| --- | ---: | ---: | ---: | ---: |
| Hardware | 19 | 0 | 6 | 25 |
| Windows support tools | 21 | 4 | 0 | 25 |
| Windows troubleshooting | 19 | 6 | 0 | 25 |
| **Total** | **59** | **10** | **6** | **75** |

Read-only legacy searching found useful Nexus command-line, slow-PC, PDF-crash,
and Windows deep-troubleshooting material. Candidate dispositions were USE/EDIT
for the 16 final reused items; the remainder were DUPLICATE, NOT RELEVANT, or
SOURCE/QUALITY UNCERTAIN because of incomplete multi-answer keys, weak
explanations, trivia, outdated assumptions, or a weaker scenario. In
particular, no archived ExamCompass item was imported just to increase reuse.

A material provenance defect was corrected: six hardware questions previously
described as Nexus-authored were traced to the permitted legacy ExamCompass
bank. They now retain the precise source URL and `permitted` status rather than
being represented as owned. The other 69 items remain `owned`.

### Distribution

Each module has 18 single-choice, 2 multi-select, 3 short-answer, and 2
free-response questions (54/6/9/6 across the batch).

| Module | Foundation | Scenario/application | Troubleshooting/reasoning |
| --- | ---: | ---: | ---: |
| Hardware | 8 | 10 | 7 |
| Windows support tools | 8 | 8 | 9 (7 troubleshooting, 2 reasoning) |
| Windows troubleshooting | 3 | 4 | 18 (15 troubleshooting, 3 reasoning) |

Importance is 14 Job Critical / 11 Working Knowledge for hardware; 15 / 9 / 1
Awareness for Windows tools; and 24 / 1 for Windows troubleshooting. Objective
counts are hardware 3.4=18 and 3.5=7; Windows tools 1.1=5, 1.2=10, 1.6=10; and
Windows troubleshooting 3.1=25. No mapped objective is obviously
underrepresented for the deliberately bounded module scope.

## Short answer, free response, and Explain

Short-answer matching remains normalized rather than punctuation/case exact.
Reasonable variants were added for `msinfo32.exe`, reordered `netstat -a -n -o`
switches, `perfmon.exe /rel`, Safe Mode variants, and `taskmgr.exe`. Tests cover
uppercase and representative variants without accepting technically different
commands.

The six bank free-response rubrics were made more granular, minimum-concept
thresholds were reviewed, and rubric versions were advanced. All six module
Explain prompts now use structured concepts with sensible aliases and new
rubric versions. Deterministic Explain grading now passes only when all required
concepts match; partially matching or differently worded ambiguous responses
go to the existing pending mentor workflow instead of receiving an
overconfident fail. Trivial clearly wrong responses can still fail
deterministically. The mentor UI was generalized to render structured concepts
instead of `[object Object]`.

## Quick Checks and Module Quizzes

The review found that same-objective Quick Checks could repeatedly draw the
first rows from a bank, including concepts taught in another lesson. All 15
Quick Checks now have lesson-aligned `tags_any` filters. Most display 4–5
questions; two display 3 because only three non-free-response items are both
strong and lesson-aligned. They remain unlimited-attempt formative work.

The prior 12-question Module Quiz draw mixed question types but did not protect
concept coverage. Each module now has a data-driven blueprint:

- hardware: platform/CPU/cooling 4, expansion 2, power 3, workflow/safety 3;
- Windows tools: objective 1.1=3, 1.2=5, 1.6=4;
- Windows troubleshooting: method 2, performance 3, startup 3, crash 2,
  verify/document 2.

The generic service balances available question types within each group. No
question IDs are hardcoded and no frontend module special case was added.

## Practical, Service Desk, and resource findings

- **Compatible PC upgrade plan — READY:** now requires comparing at least two
  candidates and rejecting one with a concrete compatibility reason. It tests
  selection, safety, installation planning, and verification rather than only
  worksheet recall.
- **Windows support snapshot — READY:** clearly requires real command output,
  safe redaction (including domains), a short interpretation, and an explicit
  elevation boundary for `chkdsk`/SFC.
- **Windows triage record — READY:** now requires two reproductions/runs so the
  student records a baseline, evidence, one controlled change, verification,
  and escalation/documentation.
- **INC2403 — suitable with a minor note:** it requires reproduction, a
  meaningful update/helper diagnosis, remediation, export retry, verification,
  and closure documentation. The diagnosis path is intentionally fairly
  scripted, so it is supplemental evidence and not a replacement for the
  broader triage practical. The Service Desk engine was unchanged.

All nine required anchor resources returned HTTP 200 after redirects. Provider
and titles are correct, free/public, and lesson-aligned. The narrow client
TCP/IP page was replaced by Microsoft's current Windows network-settings guide;
the broad crash-support landing page was replaced by Microsoft's support and
diagnostic tools module. No paid notes were copied and no redundant resource
pile was added.

## Internal alignment audit

- **Hardware:** platform/CPU/cooling, expansion, power, and upgrade workflow
  each appear in lessons, tagged questions, the upgrade practical, and one of
  two Explain prompts. Service Desk is correctly absent.
- **Windows tools:** OS/filesystem boundaries, network review, system commands,
  shares/domains, and client settings each appear in lessons and question
  groups. The support snapshot exercises evidence collection, and two Explain
  prompts assess tool choice and support boundaries. Service Desk is correctly
  absent.
- **Windows troubleshooting:** method, performance, startup, crashes, and
  verify/document each have lesson, question, and quiz-blueprint coverage. The
  two-run triage practical, INC2403, and two Explain prompts provide application
  evidence. No significant lesson-assessment gap remains; INC2403's scripted
  diagnosis is the one minor limitation.

## Editorial state and tamper guard

The system-supported editorial state is on the quiz bank. An exact-byte
approval manifest records the reviewed filename, title, 25-question count, and
SHA-256. The loader promotes only those exact banks to `validated` with answer
keys validated and explanations complete. Any bank content or metadata change
resets the touched quiz to unreviewed; a hash mismatch blocks re-approval until
another human review updates the manifest. Student-delivery publication state
was not broadened by this editorial task.

Final approval hashes:

- hardware: `226daa2d9fec1fd1b1ca8f502eb947c0b5baed52550549d007680ec41f62520a`
- Windows tools: `3004146b1a9bb25985a858b4988a8810031031000efdfb5ddc874ed2c4651e4b`
- Windows troubleshooting: `41f31fb2bc12fd2eb21fe60481170b498d4fd4f963de8f1bde228d1403185ea1`

## Verification

- Backend: **729 passed**, 9 existing deprecation warnings (baseline 726; no
  regression). Tests include exact approval hashing/counts, provenance,
  objective validity, unique fingerprints, idempotency, Quick Check tag
  isolation, quiz-blueprint coverage, short-answer variants, Explain ambiguity,
  mentor composition, student rendering, and V1/legacy behavior.
- Frontend: **13 files / 39 tests passed**. Production build passed with the
  existing >500 kB chunk warning. `npm audit --audit-level=high` reports 0
  vulnerabilities. No lint or typecheck scripts exist.
- Browser: an isolated SQLite database migrated to development head 0066 and
  loaded V2 content. The student flow opened all Phase 3A modules, a reviewed
  hardware lesson/resource, Quick Check, Module Quiz, practical, Service Desk,
  Explain/pending grading, persistence, error state, and 390 px layout (1
  passed). The mentor flow switched modules, rendered weakness/misses, graded a
  pending Explain response with history, and passed tablet layout; student
  credentials received 403 from mentor data (2 passed). The first mentor setup
  attempt had an ambiguous disposable fixture label; the fixture was corrected
  and the complete rerun passed. The scratch stack and database were removed.
- Resources: all 9 anchor URLs returned HTTP 200.

## Production safety verification

Read-only checks at the end found the service active and `/health` HTTP 200.
Production remains `0064_v2_ai_grading_infrastructure`; the development 0065
and 0066 tables are absent. All V2 certification, objective, lesson/question
metadata, resource, assessment, and interview tables contain zero rows. Seven
students remain. The V2 route returns 404 because the feature is off. The
production database SHA-256 remained
`cb344b1bae6542f9aab26bd6b3284e1aa1897cb53bbc21005bcb2aee38ddf41b`.
No migration was created and nothing was deployed, seeded, migrated, or enabled
in production.

## Module verdicts and recommendation

- **PC Components, Power & Safe Upgrades — READY.** Safety and compatibility
  language is now defensible, practical work requires a real comparison, and
  the question bank has useful foundation/application/troubleshooting balance.
- **Windows Support Tools & Client Configuration — READY.** Command behavior,
  network boundaries, short-answer variants, and lesson-level assessment
  alignment are corrected.
- **Windows Performance, Startup & Application Troubleshooting — READY WITH
  MINOR NOTES.** The module is ready; INC2403 remains a deliberately scripted
  supplemental scenario rather than the sole proof of diagnosis skill.

Recommendation: **begin A+ Batch 2 only after owner approval**. Preserve this
manual per-question audit plus hash-bound approval gate. A second pass is not
required for these three modules, but future batches should avoid treating a
successful loader run as editorial approval.
