# Quiz Quality Audit

Audit date: 2026-07-19 UTC

## Executive finding

The 25 current seed quizzes are generally clear, workplace-oriented, lesson-aligned, and fully explained. The 79 imported quizzes contain useful material, but **none is safe to use as a required assessment without answer-key review**. All 778 imported questions lack explanations. The importer/browser path can fall back to A when it cannot detect a result, and the database proves a second failure mode: answers selected during import were sometimes combined with the real answer.

## Scoring rubric

Each row uses the requested 100-point rubric: technical correctness 30, job relevance 20, lesson alignment 15, clarity 10, answer quality 10, explanation quality 10, and appropriate difficulty 5. Scores evaluate the quiz *as stored today*, not its potential after repair.

## Corpus-level checks

- Questions inspected: **967** (all records, options A–H, primary and multi-answer keys, explanations, and quiz context).
- Missing explanations: **778**, exactly all imported questions. Seed questions missing explanations: **0**.
- Empty keyed options: **1 confirmed** (q649 includes nonexistent E); no primary `correct_answer` points to an empty option.
- Two-option True/False items: **90**. Empty C/D is intentional for those items, not by itself a defect.
- Questions with 5–8 populated options: **209**; the current schema/UI supports A–H.
- Multi-answer records: **278 total** (19 seed, 259 imported).
- High-confidence broken scoring keys: **120 questions across 25 imported quizzes**. Criteria were: a multi-key on a single-answer prompt, a Select-N count mismatch, every option keyed, or a key to an empty option.
- Imported primary answer A: **273/778 (35.1%)**. This is not proof that all 273 are wrong, but every one needs source-independent validation because both backend scraper fallbacks and bookmarklet fallbacks use A.
- Seed answer-position imbalance: B is the primary answer on **154/189 (81.5%)**. The answers are mostly technically defensible, but the pattern makes guessing easy and should be randomized or rebalanced.
- Exact duplicate questions: **0**. Near duplicates: **2 pairs**, neither heavy overlap.
- Duplicate answer-option sets and broken markup: **0 confirmed**. Four seed prompts use angle-bracket command placeholders such as `id <user>`; React renders them as text and they are not stored HTML.
- Question source at quiz level: **189 static-seed questions and 778 ExamCompass questions; 0 unknown**. The individual question rows have no source field, so attribution is inherited from the parent quiz.
- No evidence of questions copied into a completely unrelated quiz was found. The strongest content-placement problem is at quiz level: all 79 imports were packed into Weeks 1–9 by certification order.
- Certification/trivia tendency: **468/778** imports begin with definition/recognition constructions such as “Which,” “What,” or “A type”; only **214/778** contain scenario/action cues. Sixteen explicitly mention CompTIA/exam wording. These banks are useful for recall practice, not workplace promotion.
- Difficulty/placement: 17 quizzes are designated remediation because they are basic recall; 23 are optional practice and 29 have a best placement directly in the certification library. Current Week 1 mobile-device banks, Week 2 networking banks, and Week 9 operational-process banks are off-lesson, not merely too easy or hard.

## High-confidence key failures by quiz

These IDs are the minimum confirmed set; absence from this list does not validate the remaining imported keys.

| Quiz | Count | Question IDs |
|---:|---:|---|

| 26 | 3 | q569, q570, q573 |
| 27 | 0 |  |
| 28 | 3 | q584, q585, q587 |
| 29 | 0 |  |
| 30 | 2 | q599, q600 |
| 31 | 0 |  |
| 32 | 0 |  |
| 33 | 0 |  |
| 34 | 0 |  |
| 35 | 0 |  |
| 36 | 0 |  |
| 37 | 0 |  |
| 38 | 0 |  |
| 39 | 1 | q649 |
| 40 | 0 |  |
| 41 | 0 |  |
| 42 | 3 | q661, q662, q664 |
| 43 | 7 | q666, q668, q669, q671, q672, q673, q674 |
| 44 | 0 |  |
| 45 | 0 |  |
| 46 | 0 |  |
| 47 | 0 |  |
| 48 | 0 |  |
| 49 | 0 |  |
| 50 | 2 | q706, q707 |
| 51 | 0 |  |
| 52 | 0 |  |
| 53 | 0 |  |
| 54 | 0 |  |
| 55 | 11 | q748, q749, q753, q756, q758, q759, q760, q761, q764, q765, q766 |
| 56 | 13 | q767, q768, q769, q770, q772, q773, q774, q775, q776, q777, q778, q779, q781 |
| 57 | 0 |  |
| 58 | 10 | q785, q787, q788, q792, q793, q794, q795, q796, q799, q801 |
| 59 | 0 |  |
| 60 | 0 |  |
| 61 | 11 | q824, q825, q826, q827, q828, q829, q830, q831, q832, q835, q836 |
| 62 | 2 | q839, q846 |
| 63 | 4 | q847, q848, q850, q851 |
| 64 | 1 | q859 |
| 65 | 4 | q863, q864, q865, q871 |
| 66 | 0 |  |
| 67 | 5 | q908, q909, q911, q912, q913 |
| 68 | 0 |  |
| 69 | 0 |  |
| 70 | 0 |  |
| 71 | 1 | q968 |
| 72 | 0 |  |
| 73 | 5 | q982, q983, q986, q987, q988 |
| 74 | 0 |  |
| 75 | 0 |  |
| 76 | 0 |  |
| 77 | 8 | q1031, q1034, q1035, q1036, q1037, q1038, q1039, q1043 |
| 78 | 0 |  |
| 79 | 3 | q1075, q1085, q1087 |
| 80 | 0 |  |
| 81 | 5 | q1114, q1115, q1118, q1131, q1137 |
| 82 | 0 |  |
| 83 | 0 |  |
| 84 | 8 | q1177, q1178, q1179, q1180, q1181, q1182, q1184, q1185 |
| 85 | 0 |  |
| 86 | 0 |  |
| 87 | 0 |  |
| 88 | 0 |  |
| 89 | 2 | q1230, q1231 |
| 90 | 0 |  |
| 91 | 1 | q1244 |
| 92 | 5 | q1251, q1254, q1256, q1257, q1258 |
| 93 | 0 |  |
| 94 | 0 |  |
| 95 | 0 |  |
| 96 | 0 |  |
| 97 | 0 |  |
| 98 | 0 |  |
| 99 | 0 |  |
| 100 | 0 |  |
| 101 | 0 |  |
| 102 | 0 |  |
| 103 | 0 |  |
| 104 | 0 |  |

## Notable technical, clarity, and currency defects

| Question(s) | Finding | Required correction |
|---|---|---|
| q1919 | Screenshot and scope (`Is anyone else affected?`) are both defensible first questions. | Make the scenario constrain the goal or accept both. |
| q1925 | Read and Read & Execute are presented as jointly required; one may be sufficient depending on the object/action. | Ask about a specific file/executable and key the minimum right. |
| q1931 | “The first event matters most” is too absolute. | Teach first causal event as a strong starting hypothesis, then correlate. |
| q1984 | Key B and option C are simultaneously true. | Rewrite C or make the item multi-select. |
| q2039 | User Group Policy can refresh in the background/manually; next logon is not universally required. | Distinguish refreshable settings from logon-required settings. |
| q2042 | A DHCP reservation is preferred here, but an approved static address outside the pool is also valid. | State the organizational constraint that makes reservation best. |
| q649 | B and nonexistent E are keyed; Startup Repair is D. | Key D only. |
| q706–q707 | PII/PHI distinctions are blurred and multiple mutually exclusive answers are accepted. | Re-key and explain the scope of HIPAA/PHI. |
| q748, q761, q765–q766 | FTP, HTTPS, TCP, and UDP fundamentals have accepted wrong answers; both True and False are accepted on two items. | Re-key from protocol references and add explanations. |
| q767–q781 | Port bank accepts many wrong ports; q777 keys 135–139 for a three-answer NetBIOS question. | Re-key every item; teach 137/UDP, 138/UDP, 139/TCP and SMB 445 context. |
| q824–q836 | IP bank accepts mutually exclusive sizes/formats and often every option. | Re-key all affected items; merge only sound questions into Week 9. |
| q982–q988 | Power-supply bank accepts US and European voltage ranges together and extra rail answers. | Re-key and remove region ambiguity. |
| q1114 | Both True and False are accepted for advice to keep using and puncture a swollen battery. | Key False only; explicitly say stop use, isolate safely, and follow battery/e-waste procedure. |
| q1118 | Both True and False are accepted for routine full discharge of modern batteries. | Key False and explain modern lithium-ion practice. |
| q1177–q1185 | Common-OS bank frequently keys all operating systems for a one-best-answer prompt. | Re-key or retire until repaired. |
| q1217 / quiz 88 | “Premium editions” is not a precise Windows 10/11 edition label; Windows 10 general support ended 2025-10-14. | Reframe around currently supported Windows 11 editions and label historical certification facts. |
| q1244 | Device Manager and nonexistent E are accepted; Disk Management is D. | Key D only. |
| q1319 / quiz 100 | Voice-call MFA is taught as a static current pattern. As of 2026-07, Entra is moving users toward passkeys from 2026-09 and retiring Microsoft-provided SMS/voice in 2027-02. | Teach it as a legacy/transition method and prefer phishing-resistant authentication. |

Currency references: [Microsoft Windows 10 lifecycle](https://learn.microsoft.com/en-us/lifecycle/announcements/windows-10-end-of-support) and [Microsoft Entra SMS/voice retirement](https://learn.microsoft.com/en-us/entra/identity/authentication/concept-sms-voice-retirement).

## Classification totals

- KEEP: **19**
- KEEP_WITH_EDITS: **24**
- MERGE: **15**
- OPTIONAL_PRACTICE: **23**
- REMEDIATION: **17**
- CUMULATIVE_REVIEW: **6**
- OWNER_REVIEW: **0**
- REMOVE_CANDIDATE: **0**


No quiz is a remove candidate solely because it is imported or lacks an explanation. No owner-review classification was needed for placement; uncertain answer keys are instead explicitly marked for edits. `REMOVE_CANDIDATE = 0` reflects the fact that even the weakest banks contain salvageable certification/remediation material.

## Per-quiz scorecard

Columns: TC technical correctness, JR job relevance, LA lesson alignment, CL clarity, AQ answer quality, EX explanation quality, DF difficulty fit.

| ID | Quiz | TC | JR | LA | CL | AQ | EX | DF | Total | Classification | Question-level finding |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|

| 1 | Ticket Writing Fundamentals | 28 | 20 | 15 | 9 | 9 | 10 | 5 | 96 | KEEP | All 8 explained; primary B 5/8. q1919 has two defensible first questions; q1925 treats Read and Read & Execute as jointly required rather than alternatives. |
| 2 | Windows Accounts and Permissions | 27 | 19 | 15 | 9 | 9 | 10 | 5 | 94 | KEEP | All 10 explained; primary B 6/10. No confirmed technical defect; rebalance answer positions. |
| 3 | The Investigator's Toolkit | 26 | 19 | 15 | 8 | 9 | 10 | 5 | 92 | KEEP | All 8 explained; primary B 4/8. q1931 overstates that the first event is always the root-cause event; soften to 'often the best starting point'. |
| 4 | Windows Command-Line Diagnostics | 28 | 20 | 15 | 9 | 9 | 10 | 5 | 96 | KEEP | All 6 explained; primary B 4/6. No confirmed technical defect; rebalance answer positions. |
| 5 | Help-Desk Operations | 28 | 20 | 15 | 9 | 9 | 10 | 5 | 96 | CUMULATIVE_REVIEW | All 6 explained; primary B 5/6. No confirmed technical defect; rebalance answer positions. |
| 6 | Windows Deep Troubleshooting | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 8 explained; primary B 6/8. No confirmed technical defect; rebalance answer positions. |
| 7 | Accounts and Permissions in Practice | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 9 explained; primary B 8/9. No confirmed technical defect; rebalance answer positions. |
| 8 | Endpoint Security and Remote Support | 28 | 20 | 15 | 9 | 9 | 10 | 5 | 96 | KEEP | All 8 explained; primary B 7/8. No confirmed technical defect; rebalance answer positions. |
| 9 | Client Network Triage | 28 | 20 | 15 | 9 | 9 | 10 | 5 | 96 | CUMULATIVE_REVIEW | All 8 explained; primary B 8/8. No confirmed technical defect; rebalance answer positions. |
| 10 | IPv4 Addressing and Subnetting | 25 | 20 | 15 | 8 | 9 | 10 | 5 | 92 | KEEP | All 8 explained; primary B 6/8. q1984 keys 'cannot reach the gateway' while option C ('local traffic only') is also true. |
| 11 | Packet Flow, ARP, and MAC Learning | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 6 explained; primary B 6/6. No confirmed technical defect; rebalance answer positions. |
| 12 | Cisco CLI, VLANs, and Interfaces | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 7 explained; primary B 7/7. No confirmed technical defect; rebalance answer positions. |
| 13 | Trunks, Routing, and Network Services | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 7 explained; primary B 7/7. No confirmed technical defect; rebalance answer positions. |
| 14 | Network Troubleshooting and Secure Admin | 28 | 20 | 15 | 9 | 9 | 10 | 5 | 96 | CUMULATIVE_REVIEW | All 7 explained; primary B 6/7. No confirmed technical defect; rebalance answer positions. |
| 15 | Active Directory Foundations | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 8 explained; primary B 6/8. No confirmed technical defect; rebalance answer positions. |
| 16 | Domain Joins and File Access | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 7 explained; primary B 6/7. No confirmed technical defect; rebalance answer positions. |
| 17 | Group Policy Troubleshooting | 23 | 19 | 15 | 8 | 9 | 9 | 5 | 88 | KEEP | All 7 explained; primary B 7/7. q2039 says user policy takes effect only at next logon; many settings also apply at background/manual refresh. |
| 18 | Server DNS/DHCP and PowerShell | 25 | 20 | 15 | 8 | 9 | 9 | 5 | 91 | CUMULATIVE_REVIEW | All 8 explained; primary B 7/8. q2042 presents DHCP reservation as the only right stable-address method; an approved static outside the pool can also be valid. |
| 19 | Server Operations, Backup, and Remoting | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 7 explained; primary B 7/7. No confirmed technical defect; rebalance answer positions. |
| 20 | Linux Fundamentals: Files, Permissions, SSH | 27 | 19 | 15 | 9 | 9 | 10 | 5 | 94 | KEEP | All 8 explained; primary B 6/8. No confirmed technical defect; rebalance answer positions. |
| 21 | Services, Logs, and Linux Networking | 27 | 19 | 15 | 9 | 9 | 9 | 5 | 93 | KEEP | All 8 explained; primary B 6/8. No confirmed technical defect; rebalance answer positions. |
| 22 | Linux in Production and Monitoring | 26 | 20 | 15 | 9 | 9 | 9 | 5 | 93 | CUMULATIVE_REVIEW | All 8 explained; primary B 6/8. No confirmed technical defect; rebalance answer positions. |
| 23 | Cloud Concepts and Entra ID | 27 | 20 | 15 | 9 | 9 | 10 | 5 | 95 | KEEP | All 8 explained; primary B 6/8. No confirmed technical defect; rebalance answer positions. |
| 24 | Azure VMs, NSGs, and Storage | 27 | 20 | 15 | 9 | 9 | 9 | 5 | 94 | KEEP | All 8 explained; primary B 7/8. No confirmed technical defect; rebalance answer positions. |
| 25 | Integrated Operations Readiness | 28 | 20 | 15 | 9 | 9 | 9 | 5 | 95 | CUMULATIVE_REVIEW | All 6 explained; primary B 5/6. No confirmed technical defect; rebalance answer positions. |
| 26 | Mobile Device Connection Methods Quiz | 13 | 13 | 5 | 7 | 2 | 0 | 4 | 44 | MERGE | 7 missing explanations; 3 confirmed key defects; primary A 4/7. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 27 | Mobile Device Hardware Servicing Quiz | 20 | 13 | 5 | 7 | 5 | 0 | 4 | 54 | MERGE | 9 missing explanations; 0 confirmed key defects; primary A 3/9. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 28 | Mobile Device Accessories Quiz | 13 | 13 | 5 | 7 | 2 | 0 | 4 | 44 | MERGE | 5 missing explanations; 3 confirmed key defects; primary A 3/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 29 | Mobile Device Network Connectivity Quiz | 24 | 13 | 9 | 7 | 5 | 0 | 4 | 62 | MERGE | 9 missing explanations; 0 confirmed key defects; primary A 3/9. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 30 | Mobile Device Application Support Quiz | 13 | 13 | 5 | 7 | 2 | 0 | 4 | 44 | MERGE | 6 missing explanations; 2 confirmed key defects; primary A 3/6. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 31 | Malware Quiz | 20 | 15 | 10 | 7 | 5 | 0 | 4 | 61 | REMEDIATION | 5 missing explanations; 0 confirmed key defects; primary A 3/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 32 | Social Engineering Quiz | 24 | 18 | 13 | 7 | 5 | 0 | 4 | 71 | KEEP_WITH_EDITS | 7 missing explanations; 0 confirmed key defects; primary A 2/7. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 33 | Threats & Vulnerabilities Quiz | 24 | 13 | 5 | 7 | 5 | 0 | 4 | 58 | MERGE | 4 missing explanations; 0 confirmed key defects; primary A 1/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 34 | Malware Removal Procedures Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 8 missing explanations; 0 confirmed key defects; primary A 2/8. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 35 | Mobile Device Security Quiz | 20 | 13 | 5 | 7 | 5 | 0 | 4 | 54 | MERGE | 5 missing explanations; 0 confirmed key defects; primary A 0/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 36 | Data Destruction & Disposal Methods Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 4 missing explanations; 0 confirmed key defects; primary A 2/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 37 | SOHO Network Security Quiz | 20 | 11 | 7 | 7 | 5 | 0 | 4 | 54 | OPTIONAL_PRACTICE | 6 missing explanations; 0 confirmed key defects; primary A 2/6. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 38 | Web Browser Security Quiz | 24 | 11 | 3 | 7 | 5 | 0 | 4 | 54 | OPTIONAL_PRACTICE | 4 missing explanations; 0 confirmed key defects; primary A 3/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 39 | Windows OS Troubleshooting Quiz | 13 | 18 | 13 | 7 | 2 | 0 | 4 | 57 | KEEP_WITH_EDITS | 5 missing explanations; 1 confirmed key defects; primary A 1/5. q649 keys B and nonexistent E; Startup Repair is option D. |
| 40 | Mobile OS and App Troubleshooting Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 5 missing explanations; 0 confirmed key defects; primary A 2/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 41 | Common PC Security Issues Troubleshooting Quiz | 24 | 15 | 10 | 7 | 5 | 0 | 4 | 65 | REMEDIATION | 4 missing explanations; 0 confirmed key defects; primary A 0/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 42 | Ticketing Systems Quiz | 13 | 13 | 9 | 7 | 2 | 0 | 4 | 48 | MERGE | 4 missing explanations; 3 confirmed key defects; primary A 1/4. q661 asks for three answers but keys four, including escalation level as initial intake data. |
| 43 | Asset Management Quiz | 13 | 18 | 13 | 7 | 2 | 0 | 4 | 57 | KEEP_WITH_EDITS | 10 missing explanations; 7 confirmed key defects; primary A 5/10. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 44 | Change Management Procedures Quiz | 24 | 18 | 13 | 7 | 5 | 0 | 4 | 71 | KEEP_WITH_EDITS | 5 missing explanations; 0 confirmed key defects; primary A 3/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 45 | Backup & Recovery Methods Quiz | 24 | 13 | 9 | 7 | 5 | 0 | 4 | 62 | MERGE | 4 missing explanations; 0 confirmed key defects; primary A 0/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 46 | Common Safety Procedures Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 5 missing explanations; 0 confirmed key defects; primary A 1/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 47 | Environmental Impacts & Controls Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 5 missing explanations; 0 confirmed key defects; primary A 0/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 48 | Incident Response Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 4 missing explanations; 0 confirmed key defects; primary A 0/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 49 | Software Licensing Concepts Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 6 missing explanations; 0 confirmed key defects; primary A 1/6. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 50 | Regulated Data Quiz | 13 | 11 | 3 | 7 | 2 | 0 | 4 | 40 | OPTIONAL_PRACTICE | 5 missing explanations; 2 confirmed key defects; primary A 2/5. q706 accepts PHI and PII although the general acronym requested is PII; q707 accepts PII and PHI for HIPAA. |
| 51 | Communication & Professionalism Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 14 missing explanations; 0 confirmed key defects; primary A 2/14. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 52 | Scripting Basics Quiz | 24 | 15 | 10 | 7 | 5 | 0 | 4 | 65 | REMEDIATION | 7 missing explanations; 0 confirmed key defects; primary A 1/7. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 53 | Remote Access Technologies Quiz | 24 | 18 | 13 | 7 | 5 | 0 | 4 | 71 | KEEP_WITH_EDITS | 14 missing explanations; 0 confirmed key defects; primary A 4/14. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 54 | Basic AI Concepts Quiz | 24 | 11 | 3 | 7 | 5 | 0 | 3 | 53 | OPTIONAL_PRACTICE | 4 missing explanations; 0 confirmed key defects; primary A 0/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 55 | Network Protocols Quiz | 13 | 13 | 9 | 6 | 2 | 0 | 4 | 47 | MERGE | 19 missing explanations; 11 confirmed key defects; primary A 10/19. q748 accepts directory access for FTP; q761 accepts SSH for HTTPS; q765/q766 key both True and False. |
| 56 | TCP & UDP Ports Quiz | 13 | 15 | 10 | 6 | 2 | 0 | 4 | 50 | REMEDIATION | 15 missing explanations; 13 confirmed key defects; primary A 7/15. Most port questions accept multiple wrong ports; q777 keys 135-139 although NetBIOS uses 137-139. |
| 57 | Wireless Networking Technologies Quiz | 20 | 13 | 9 | 7 | 5 | 0 | 3 | 57 | MERGE | 3 missing explanations; 0 confirmed key defects; primary A 2/3. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 58 | Network Services Quiz | 13 | 18 | 13 | 6 | 2 | 0 | 4 | 56 | KEEP_WITH_EDITS | 20 missing explanations; 10 confirmed key defects; primary A 7/20. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 59 | Network Configuration Concepts Quiz | 24 | 15 | 10 | 7 | 5 | 0 | 4 | 65 | REMEDIATION | 4 missing explanations; 0 confirmed key defects; primary A 0/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 60 | Common Networking Hardware Quiz | 20 | 15 | 10 | 7 | 5 | 0 | 4 | 61 | REMEDIATION | 15 missing explanations; 0 confirmed key defects; primary A 4/15. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 61 | IP Addressing Quiz | 13 | 13 | 9 | 6 | 2 | 0 | 4 | 47 | MERGE | 15 missing explanations; 11 confirmed key defects; primary A 14/15. Basic IP questions accept mutually exclusive bit lengths/number formats; several select-N items key every option. |
| 62 | Internet Connection Types Quiz | 13 | 11 | 3 | 7 | 2 | 0 | 4 | 40 | OPTIONAL_PRACTICE | 8 missing explanations; 2 confirmed key defects; primary A 2/8. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 63 | Network Types Quiz | 13 | 15 | 10 | 7 | 2 | 0 | 4 | 51 | REMEDIATION | 7 missing explanations; 4 confirmed key defects; primary A 4/7. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 64 | Networking Tools Quiz | 13 | 18 | 13 | 7 | 2 | 0 | 4 | 57 | KEEP_WITH_EDITS | 8 missing explanations; 1 confirmed key defects; primary A 2/8. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 65 | Display Devices Quiz | 13 | 11 | 3 | 7 | 2 | 0 | 4 | 40 | OPTIONAL_PRACTICE | 10 missing explanations; 4 confirmed key defects; primary A 6/10. Display-technology select-N keys are overinclusive; q868 correctly marks OLED-is-LCD false but the bank remains trivia-heavy. |
| 66 | Cabling Quiz | 20 | 11 | 3 | 6 | 5 | 0 | 4 | 49 | OPTIONAL_PRACTICE | 36 missing explanations; 0 confirmed key defects; primary A 11/36. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 67 | Connector Quiz | 13 | 13 | 5 | 7 | 2 | 0 | 4 | 44 | MERGE | 12 missing explanations; 5 confirmed key defects; primary A 5/12. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 68 | RAM Quiz | 20 | 15 | 10 | 7 | 5 | 0 | 4 | 61 | REMEDIATION | 17 missing explanations; 0 confirmed key defects; primary A 8/17. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 69 | Storage Devices Quiz | 20 | 15 | 10 | 7 | 5 | 0 | 4 | 61 | REMEDIATION | 7 missing explanations; 0 confirmed key defects; primary A 2/7. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 70 | Motherboard Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 20 missing explanations; 0 confirmed key defects; primary A 10/20. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 71 | BIOS Quiz | 13 | 18 | 13 | 7 | 2 | 0 | 4 | 57 | KEEP_WITH_EDITS | 7 missing explanations; 1 confirmed key defects; primary A 3/7. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 72 | CPU Quiz | 20 | 15 | 10 | 7 | 5 | 0 | 4 | 61 | REMEDIATION | 11 missing explanations; 0 confirmed key defects; primary A 4/11. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 73 | Power Supply Quiz | 13 | 18 | 13 | 7 | 2 | 0 | 4 | 57 | KEEP_WITH_EDITS | 12 missing explanations; 5 confirmed key defects; primary A 9/12. US/Europe voltage questions key both ranges; several rail questions accept extra components. |
| 74 | Multifunction Devices Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 8 missing explanations; 0 confirmed key defects; primary A 0/8. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 75 | Printer Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 21 missing explanations; 0 confirmed key defects; primary A 7/21. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 76 | Virtualization Concepts Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 6 missing explanations; 0 confirmed key defects; primary A 2/6. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 77 | Cloud Computing Concepts Quiz | 13 | 18 | 13 | 6 | 2 | 0 | 4 | 56 | KEEP_WITH_EDITS | 25 missing explanations; 8 confirmed key defects; primary A 10/25. Cloud service/deployment questions accept multiple mutually exclusive models. |
| 78 | Core PC Hardware Troubleshooting Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 19 missing explanations; 0 confirmed key defects; primary A 2/19. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 79 | Storage and RAID Troubleshooting Quiz | 13 | 18 | 13 | 7 | 2 | 0 | 4 | 57 | KEEP_WITH_EDITS | 18 missing explanations; 3 confirmed key defects; primary A 4/18. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 80 | Display Devices Troubleshooting Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 22 missing explanations; 0 confirmed key defects; primary A 4/22. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 81 | Mobile Devices Troubleshooting Quiz | 10 | 11 | 3 | 6 | 2 | 0 | 4 | 36 | OPTIONAL_PRACTICE | 30 missing explanations; 5 confirmed key defects; primary A 9/30. q1114 accepts a dangerous swollen-battery statement (including puncturing it); q1118 accepts obsolete full-discharge advice. Both True and False are keyed. |
| 82 | Network Troubleshooting Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 14 missing explanations; 0 confirmed key defects; primary A 2/14. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 83 | Printer Troubleshooting Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 20 missing explanations; 0 confirmed key defects; primary A 8/20. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 84 | Common OS Types Quiz | 13 | 11 | 3 | 6 | 2 | 0 | 4 | 39 | OPTIONAL_PRACTICE | 10 missing explanations; 8 confirmed key defects; primary A 7/10. Multiple OS questions key all offered operating systems despite asking for one best answer. |
| 85 | Filesystem Types Quiz | 20 | 15 | 10 | 7 | 5 | 0 | 4 | 61 | REMEDIATION | 8 missing explanations; 0 confirmed key defects; primary A 1/8. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 86 | OS Boot Methods Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 12 missing explanations; 0 confirmed key defects; primary A 2/12. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 87 | OS Installation Methods Quiz | 24 | 11 | 3 | 7 | 5 | 0 | 4 | 54 | OPTIONAL_PRACTICE | 8 missing explanations; 0 confirmed key defects; primary A 1/8. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 88 | Microsoft Windows Editions Quiz | 18 | 11 | 3 | 7 | 5 | 0 | 4 | 48 | OPTIONAL_PRACTICE | 14 missing explanations; 0 confirmed key defects; primary A 9/14. Windows 10 wording is lifecycle-stale after 2025-10-14; q1217 uses the nonexistent/ambiguous label 'Premium editions'. |
| 89 | MS Windows Basic Features Quiz | 13 | 15 | 10 | 7 | 2 | 0 | 4 | 51 | REMEDIATION | 8 missing explanations; 2 confirmed key defects; primary A 4/8. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 90 | Windows Task Manager Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 7 missing explanations; 0 confirmed key defects; primary A 4/7. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 91 | Windows MMC Snap-ins Quiz | 13 | 15 | 10 | 7 | 2 | 0 | 4 | 51 | REMEDIATION | 7 missing explanations; 1 confirmed key defects; primary A 2/7. q1244 accepts Device Manager and nonexistent E even though Disk Management (D) is correct. |
| 92 | Windows Additional Admin Tools Quiz | 13 | 18 | 13 | 7 | 2 | 0 | 4 | 57 | KEEP_WITH_EDITS | 8 missing explanations; 5 confirmed key defects; primary A 6/8. Five utility questions accept multiple mutually exclusive tools. |
| 93 | Microsoft Command-Line Tools Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 9 missing explanations; 0 confirmed key defects; primary A 3/9. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 94 | Microsoft Windows Settings Quiz | 20 | 15 | 10 | 7 | 5 | 0 | 4 | 61 | REMEDIATION | 6 missing explanations; 0 confirmed key defects; primary A 3/6. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 95 | Windows Networking Features Quiz | 20 | 13 | 9 | 7 | 5 | 0 | 4 | 58 | MERGE | 5 missing explanations; 0 confirmed key defects; primary A 2/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 96 | macOS Quiz | 24 | 11 | 3 | 7 | 5 | 0 | 4 | 54 | OPTIONAL_PRACTICE | 9 missing explanations; 0 confirmed key defects; primary A 3/9. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 97 | Linux Command Line Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 10 missing explanations; 0 confirmed key defects; primary A 2/10. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 98 | Linux OS Features & Tools Quiz | 24 | 15 | 10 | 7 | 5 | 0 | 4 | 65 | REMEDIATION | 5 missing explanations; 0 confirmed key defects; primary A 2/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 99 | Physical Security Concepts Quiz | 20 | 11 | 3 | 7 | 5 | 0 | 4 | 50 | OPTIONAL_PRACTICE | 8 missing explanations; 0 confirmed key defects; primary A 1/8. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 100 | Logical Security Concepts Quiz | 18 | 18 | 13 | 7 | 5 | 0 | 4 | 65 | KEEP_WITH_EDITS | 11 missing explanations; 0 confirmed key defects; primary A 2/11. q1319 teaches voice-call MFA without noting the 2026 passkey transition and 2027 Microsoft telecom retirement. |
| 101 | Windows OS Security Quiz | 20 | 15 | 10 | 7 | 5 | 0 | 4 | 61 | REMEDIATION | 4 missing explanations; 0 confirmed key defects; primary A 1/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 102 | NTFS & Share Permissions Quiz | 20 | 18 | 13 | 7 | 5 | 0 | 4 | 67 | KEEP_WITH_EDITS | 11 missing explanations; 0 confirmed key defects; primary A 6/11. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 103 | Active Directory Quiz | 24 | 15 | 10 | 7 | 5 | 0 | 4 | 65 | REMEDIATION | 5 missing explanations; 0 confirmed key defects; primary A 0/5. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |
| 104 | Wireless Security Quiz | 20 | 13 | 9 | 7 | 5 | 0 | 4 | 58 | MERGE | 4 missing explanations; 0 confirmed key defects; primary A 0/4. All answer keys require independent source/content review; certification wording is more factual than scenario-based. |

## Decision rule before release

1. Keep the 25 seed questions live only after correcting the six nuanced items above and removing the answer-position pattern.
2. Treat all 79 imported quizzes as quarantined editorial inventory even though their database status is currently `published`.
3. For any imported question retained: independently solve it, set the single/multi key, rewrite ambiguity, add a concise rationale, and verify current product/version facts.
4. Do not use certification banks to measure workplace promotion. Scenario/ticket/lab evidence should remain the gate authority.
