# Student Experience Quality Audit — 2026-08-12

## Scope and method

This is the pre-change development audit for the student-quality release candidate. It was completed from the current `main` branch at `6e49db4` by tracing the Nexus and Service Desk routes, server progression services, immutable scenario versions, assignments, simulation fixtures, grading rules, seeds, curriculum mappings, labs, lessons, quizzes, progress views, and existing automated tests. Production systems and production data were not accessed or modified.

## Current student journey

- **Today:** The top card correctly points to the current week, but the actual next activity is reduced to a generic “Continue Training” action. Four statistics and Daily Review appear before any compact view of this week’s required path.
- **My Training / This Week:** The weekly page already separates required work from a collapsed optional section and uses Learn → Quiz → Practice → Review. In the global navigation, however, required training is nested under “Extra Practice,” which gives it the wrong importance. Locked weeks identify only the preceding week, not the specific remaining requirement.
- **Lessons:** Lesson pages preserve server-owned completion and notes. Early lesson source content is practical and technically accurate, but several entries put definitions, procedures, exercises, mistakes, and job relevance into one dense text field. The UI does not consistently turn that structure into scan-friendly sections.
- **Quizzes:** Answers are submitted once and the review screen correctly reveals correct answers only after submission. Existing explanations are displayed, but the feedback heading says “Why this is correct” even when discussing a wrong selection and does not explicitly frame the learner’s choice.
- **Labs:** Five published VM/local labs exist. The early hardware-identification and subnetting labs are primarily read/answer exercises. The network scenario and Windows command-line lab are closer to troubleshooting but rely on written descriptions or a student-owned machine rather than a controlled simulated state. The Week 15 AD break/fix lab has meaningful verification but currently exposes infrastructure-heavy setup instructions to the learner.
- **CLI labs:** The networking CLI engine and lab packs are substantial and should be preserved. In the Service Desk remote workstation, scenario-aware terminal support exists for a bounded command set including `ipconfig`, `ipconfig /all`, `ping`, `nslookup`, `hostname`, and other fixture-owned diagnostics. Arbitrary shell execution is intentionally not supported.
- **Progress:** The page uses honest completion counts and real quiz results. It does not invent skill percentages. Service Desk reporting is limited to completed count, achievements, XP, and recent activity; first-try versus revision counts and skill-group counts are not yet exposed.
- **Mobile:** Both apps contain responsive breakpoints and mobile tool navigation. The Service Desk queue is row-based rather than a card grid, but its two-column row collapses densely on small screens. Ticket actions stack correctly. Browser validation at 375×812 is required after the implementation changes.

## Current Service Desk behavior

- The active database contains 23 published scenario records.
- Five early prototype records (`locked-user-account`, `password-reset`, `mfa-reset`, `bitlocker-recovery`, and `new-employee-onboarding`) have no student assignments and do not contain the complete requester/device/tool definition required by the current workstation.
- Eighteen simulator-ready scenarios (`INC2401`–`INC2408`, `INC2501`–`INC2510`) have immutable published definitions, server-owned objectives, and corresponding workstation fixtures.
- The seed assigns all 18 simulator-ready scenarios to every non-mentor student.
- The assignments API returns every assignment without curriculum or completion filtering.
- The Service Desk client then starts from the entire fixture library and overlays assignment definitions. This means the full simulator-ready library appears even if assignments are removed or filtered elsewhere.
- Ticket attempts, events, idempotency, immutable scenario-version binding, server-authoritative transition validation, grading, and student ownership are already strong foundations.
- Starting an attempt currently proves assignment ownership but does not independently prove that the scenario is unlocked by curriculum progression.
- Completed scenarios remain replayable through the same assignment, but the queue has no explicit Assigned versus Practice model.
- The dashboard emphasizes practice points, rank, and accuracy above the work queue. These metrics compete with the “begin shift” task and do not explain what is newly assigned.
- The queue already uses realistic ticket rows with number, subject, requester, priority, status, SLA, and assignment state. Difficulty and case-pack context are missing.
- Ticket detail provides requester/device context, tools, notes, activity history, hints, and a resolve flow. The professional workflow is implicit rather than lightly cued.

## Scenario inventory and proposed learning packs

The pack proposal uses only the 18 scenarios that have complete simulator and grading support. The five unassigned prototypes remain preserved for historical/admin review but are not safe student queue content in this release candidate.

| Pack | Scenarios | Learning purpose |
|---|---|---|
| Starter Support | `INC2405`, `INC2404`, `INC2403`, `INC2502` | Narrow, observable shortcut, peripheral, PDF-export, and single-workbook symptoms; practice scoping before broad remediation. |
| Desktop Support | `INC2408`, `INC2501`, `INC2509`, `INC2504` | Windows service, profile, storage-growth, and local printer-port troubleshooting. |
| Accounts & Access | `INC2401`, `INC2505`, `INC2510`, `INC2507` | Profile/session access, least-privilege group access, device trust, and recurring credential lockout. |
| Networking | `INC2406`, `INC2407`, `INC2503`, `INC2402` | VPN, DNS, physical/VLAN, and managed wireless isolation. |
| Advanced Troubleshooting | `INC2506`, `INC2508` | Authorization boundaries and security containment/escalation. |

The starter selection deliberately does not use the four prototype account cases: their current published records are incomplete for the real simulator and have no server grading path. The selected four teach the same beginner habit—observe, narrow scope, make one safe change, verify—using cases that can be completed and graded honestly today.

## Curriculum mapping issues

The current required Service Desk mapping begins with advanced DNS troubleshooting in Week 1, before the curriculum teaches client networking, and then maps a moved-desk network/VLAN case to Week 2 hardware. This breaks the intended lesson → guided practice → independent practice → ticket sequence. Later mappings are more coherent (profile, disk, application, access, security, printer, domain trust).

The first-pass curriculum correction should map early required tickets to cases appropriate to the week while leaving historical attempts and scenario versions untouched.

## Highest-priority problems

1. All simulator cases are effectively exposed at once; new learners have no controlled starting queue.
2. There is no server-authoritative pack unlock check at attempt start.
3. The client reconstructs fixtures that are not present in the student’s assignment response.
4. Assigned work and replay practice are not distinguished.
5. Future work dominates the queue instead of appearing as one compact next-pack preview.
6. Required training is mislabeled as “Extra Practice” in navigation.
7. The Week 1/2 Service Desk curriculum mappings are pedagogically out of order.
8. Difficulty is stored but not shown in the Service Desk worklist.
9. Locked-week explanations do not name the remaining required work.
10. Several useful P1/P2 improvements (lab restructuring, lesson presentation, richer progress skill evidence) are larger than the P0 progression boundary and must not weaken P0 delivery.

## Release boundary

This PR should implement the progression/read-model/UI changes without replacing the simulation engine or changing authentication/grading architecture. Major VM lab redesign, arbitrary Service Desk shell support, and trustworthy cross-domain skill scoring belong in a future phase.

## Implemented release-candidate decisions

- **Foundational account cases:** `locked-user-account`, `password-reset`, and `mfa-reset` previously had only sparse prototype records: no complete employee/device definition, scenario-specific Directory state, investigation sequence, safe remediation state, process-aware server objectives, verification action, or immutable current simulator version. They now render as `INC2511`–`INC2513` while retaining their stable scenario keys. Each requires account inspection, the approved simulated identity check, a supported diagnosis, the correct safe action, post-fix verification, a meaningful note, and closure. MFA also requires separating successful primary authentication from the unavailable second factor. Server authorization rejects objective actions submitted out of sequence.
- **Final packs:** Starter Support contains Locked Account, Password Reset, MFA Reset, and `INC2404` USB headset troubleshooting. Desktop Support contains `INC2408`, `INC2501`, `INC2403`, `INC2502`, and `INC2509`. Accounts & Access contains `INC2401`, `INC2405`, `INC2505`, and `INC2507`. Networking contains `INC2406`, `INC2407`, `INC2503`, and `INC2402`. Advanced Troubleshooting contains `INC2504`, `INC2506`, `INC2508`, and `INC2510`. The headset is the fourth starter case because it has a deterministic isolate/replace/verify path without requiring application or infrastructure diagnosis.
- **Pack gates:** Starter Support requires completion of Week 0 (server-derived current week 1). Desktop Support requires Week 3 and two unique Starter passes. Accounts & Access requires Week 6 and two unique Desktop passes. Networking requires Week 8 and two unique Accounts & Access passes. Advanced Troubleshooting requires Week 10 and three unique Networking passes. Packs unlock sequentially; XP and repeated passes of one scenario are not authorities, and every case in a pack is not required.
- **Assigned, Practice, and secondary work:** Assigned contains unpassed cases from the active pack (normally capped at four), in-progress work, and exact instructor assignments. Practice contains only scenarios already passed and replayable. Other unlocked unfinished scenarios remain available in the collapsed **More unlocked cases** section rather than flooding the shift queue. Passing an instructor-assigned future case moves it to Practice without unlocking that future pack.
- **Curriculum alignment:** Required Service Desk activities now use Locked Account (Week 1), `INC2404` headset troubleshooting (Week 2), Password Reset (Week 3), MFA Reset (Week 4), `INC2502` Excel troubleshooting (Week 5), `INC2505` least-privilege share access (Week 6), `INC2508` phishing containment (Week 7), `INC2407` DNS troubleshooting (Week 8), and `INC2510` domain trust (Week 14). A server-derived current-week mapping grants access to that exact required case without unlocking its future pack; after the week, an unfinished mapped case remains secondary and accessible. This keeps Endpoint Security paired with phishing triage while preventing dead-end weekly assignments or broad pack bypasses.
- **Assignment generation:** New and existing non-mentor students receive the managed 21-scenario simulator-ready inventory, while the progression service decides which subset is visible and startable. Existing assignments, attempts, grades, and legacy records remain intact. Instructor ownership overrides grant access only to the exact assigned scenario.
- **Content versions:** The three completed account scenarios and four previously revised solution-revealing scenarios (`INC2405`, `INC2406`, `INC2501`, and `INC2504`) receive new immutable published versions. Historical prototype and attempt-pinned versions are not edited.
- **Labs and lessons:** The network-diagnosis lab is now an independent DNS evidence exercise, and the Windows CLI lab is a guided evidence routine using `hostname`, `whoami`, `ipconfig /all`, `ping`, `nslookup`, and `tracert`. Existing early lessons are rendered into scan-friendly headings, bullets, code, and short paragraphs without changing their technical source meaning.

## FUTURE PHASE

- Build controlled simulator state for more guided and independent VM labs; do not claim verification from a written answer alone.
- Redesign the hardware-identification and subnetting labs around observable work and evidence.
- Hide infrastructure-heavy AD lab setup behind instructor/automation tooling while preserving the learner's break/fix and verification work.
- Expand only scenario-owned CLI commands where a deterministic output and grading objective exist; arbitrary shell execution remains out of scope.
- Add trustworthy cross-domain skill scoring only after the event model can support it. This release uses honest completed-case counts and needs-practice evidence instead of invented percentages.
- Complete `bitlocker-recovery` and `new-employee-onboarding` only after each has scenario-specific workstation state, safe process objectives, verification, and immutable simulator-ready content. They remain preserved, excluded prototypes in this release candidate.
