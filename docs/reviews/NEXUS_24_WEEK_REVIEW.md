# Week 0–24 Curriculum Review

Date: 2026-07-21. Phase 6. Evidence: full read of every lesson's teaching
text across all 25 weeks, the full ticket/lab/quiz title index, and lab/
ticket sample content, all from the live-DB curriculum dump
(`.tmp/review/curriculum_dump.md`, 25,436 lines). Difficulty is rated
1 (gentle) – 5 (steep) relative to a complete beginner's position at that
point in the program, not in absolute IT terms.

| Week | Main goal | Lessons | Required work | Hands-on work | Difficulty | Main strength | Main weakness | Recommended change |
|---|---|---|---|---|---|---|---|---|
| 0 | Learn the 6-step troubleshooting method | 1 | 1 quiz | none | 1 | Clean, memorable framework | No platform onboarding; quiz doesn't test the lesson (see Week 0 Review) | Add onboarding + align quiz to lesson |
| 1 | Write tickets a stranger can act on | 0 (module-less) | 1 quiz + 4 optional certs | 2 tickets (DNS, lockout), 1 lab (hardware ID) | 2 | Sharp internal-vs-user-facing-notes framing, directly job-relevant | "0 lessons" is a real content gap — the required quiz and 2 tickets have no matching lesson to teach from first | Write a short Week 1 lesson (ticket-writing has none; Week 2's lesson 1 partially covers it one week late) |
| 2 | Ticket anatomy + first CLI exposure | 2 | 1 quiz + 7 optional certs | 3 tickets, 1 lab | 2 | "Guided practice: rewrite these bad notes" is genuinely active learning | Heaviest optional-quiz load in the early curriculum (7) right when a beginner is most fragile | Defer 2-3 of the 7 optional quizzes to a later week |
| 3 | Hardware symptom→cause reasoning | 3 | 1 quiz + 13 optional certs | 4 tickets, 1 lab | 3 | Excellent safety framing ("never chkdsk /f on a clicking drive") | 13 optional quizzes is the single largest per-week pile in the whole program — overload risk | Spread the mobile/hardware cert-bank quizzes across weeks 3-6 instead of stacking in week 3 |
| 4 | Windows 11 investigation toolkit | 4 | 1 quiz + 2 optional | 4 tickets, 2 labs, capstone 1 | 3 | Four dense, well-sequenced lessons (accounts→tools→CLI→update/defender); first capstone lands here | 4 lessons + 4 tickets + capstone in one week is the heaviest single week in the program | Consider splitting into two weeks or moving the capstone to a review week |
| 5 | Prioritization + communication | 2 | 1 quiz + 5 optional | 3 tickets | 2 | "Write the email" practice is a rare explicit communication exercise | No lab this week breaks the lesson→ticket→lab rhythm | None needed — soft week is appropriate after Week 4's load |
| 6 | Deep Windows troubleshooting | 3 | 1 quiz + 5 optional | 3 tickets | 3 | Crash/hang/won't-start triage is genuinely advanced-beginner content, well explained | No lab | Add a short lab pairing with the disk-space lesson |
| 7 | Accounts/profiles/permissions in practice | 3 | 1 quiz + 12 optional | 3 tickets | 3 | The escalation-rail lesson (grantable vs. escalate-only) is one of the best in the program | 12 optional quizzes again stacked in one week | Spread security-domain cert quizzes across 7-8 |
| 8 | Endpoint security + remote support | 3 | 1 quiz + 6 optional | 4 tickets, 1 lab | 3 | Malware response procedure is safety-first and realistic | Introduces "credentials entered" incident response without a prior security-fundamentals week | Acceptable as-is; strong week |
| 9 | Client networking + workplace simulation | 3 | 1 quiz + 9 optional | 1 ticket, Multi-Ticket Sim 1, Gate 1 checkpoint | 3 | The 4-step "no internet" triage tree is the best single diagnostic framework in the curriculum | Only 1 standalone ticket beyond the simulation — thin standalone practice | Fine given the Gate 1 practical checkpoint carries the week |
| 10 | IPv4 addressing | 3 | 1 quiz, 0 optional | 1 ticket | 3 | Subnetting taught as "answer real questions," not exam arithmetic | Only 1 ticket for a historically hard topic (subnetting) | Add a second ticket applying subnetting to a real scenario |
| 11 | Switching, VLANs, CLI | 3 | 1 quiz + 6 optional | 3 tickets | 3 | CLI-modes lesson prevents the classic beginner mistake (wrong-mode config) | None significant | None |
| 12 | Trunks, routing, network services | 3 | 1 quiz, 0 optional | 1 ticket | 4 | Honest scope discipline ("dynamic routing is CCNA, not Nexus") | Only 1 ticket for three dense lessons (trunks, inter-VLAN routing, DHCP relay/NAT/firewall/VPN/wireless awareness) | Add a trunk-mismatch or DHCP-relay ticket |
| 13 | Secure switch admin + structured troubleshooting | 2 | 1 quiz + 2 optional | 1 ticket | 3 | The L1-L4 bottom-up method is the capstone of the whole networking arc | Thin standalone tickets relative to how much this week ties together | Acceptable — it's a synthesis week |
| 14 | Windows Server + AD foundations | 3 | 1 quiz, 0 optional | 1 ticket | 4 | AD hierarchy explained with direct ties back to Weeks 6-7's permission lessons | Big conceptual jump (desktop → server/domain) with only 1 ticket | Add a second AD-account ticket alongside the one existing |
| 15 | Domain ops + file services at scale | 2 | 1 quiz, 0 optional | 1 ticket, 1 lab | 3 | A-G-DL-P access pattern taught concretely, not abstractly | Only 1 ticket for a genuinely hard access-model topic | Add a group-nesting or GPO-drive-mapping ticket |
| 16 | Group Policy | 2 | 1 quiz + 1 optional | 1 ticket | 4 | gpresult/RSoP troubleshooting lesson is excellent and realistic | GPO precedence (LSDOU) is one of the hardest concepts in the whole program, taught in 2 lessons with 1 ticket | Add a worked precedence example as a guided lab |
| 17 | Server networking + PowerShell | 2 | 1 quiz + 1 optional | 1 ticket | 4 | PowerShell taught as investigation-first ("discover, don't guess") is the right pedagogical move | 1 ticket for two dense, high-value lessons (DNS/DHCP server + PowerShell) | Add a PowerShell-only ticket (e.g. "find every locked account") |
| 18 | Server ops, backup, PowerShell at scale | 3 | 1 quiz + 3 optional | 2 tickets | 3 | The "restore and verify" backup lesson explicitly targets the most common failure mode (untested backups) | None significant | None |
| 19 | Linux survival | 3 | 1 quiz, 0 optional | 2 tickets | 3 | Filesystem/permissions/SSH sequence mirrors the Windows arc's structure — good for transfer learning | None significant | None |
| 20 | Linux services, logs, cron | 3 | 1 quiz, 0 optional | 2 tickets | 3 | systemd/journalctl failed-service investigation is a direct Linux mirror of Week 6's Windows method | None significant | None |
| 21 | Linux in production | 3 | 1 quiz + 2 optional | 1 ticket | 4 | Ties nginx/ufw/monitoring together into one operational picture | Only 1 standalone ticket for three lessons covering web server, resource triage/backup/bash, and monitoring | Add a resource-triage ticket (disk-full or CPU-hog scenario) |
| 22 | Cloud concepts + Entra ID | 2 | 1 quiz, 0 optional | 2 tickets | 3 | Explicit zero-cost design (no student ever needs to spend money) is a real strength for a beginner cohort | Cloud responsibility-model (IaaS/PaaS/SaaS) is abstract for hands-first learners | Consider a guided diagram/matching exercise before the lesson text |
| 23 | Azure infrastructure | 2 | 1 quiz + 1 optional | 2 tickets | 4 | NSG/VM triage taught as "outside-in," directly transferable from Week 7/20 firewall lessons | Azure-specific content this late risks feeling bolted-on if Weeks 22-23 are rushed | Ensure adequate calendar time (not compressed) given this is Month 6 content |
| 24 | Integrated operations + capstone | 3 | 1 quiz, 0 optional | 1 ticket, Multi-Ticket Sim 3, capstone (4-stage) | 5 | The "mixed queue, transferable method" framing is the strongest single synthesis message in the program | None significant (an earlier pass suspected a duplicate lesson-numbering bug here; re-verified directly against the live DB in the Technical Review — Week 24 correctly spans two distinct modules, MOD-023 and MOD-024, each with its own valid Lesson 1; the apparent duplicate was only a content-dump grouping artifact, not a data bug) | None needed — this is the strongest closing week in the curriculum |

## Strongest 5 weeks

**Week 9** (client-network triage tree), **Week 13** (L1-L4 synthesis method),
**Week 19/20** (Linux mirrors the Windows method 1:1, reinforcing transfer
learning), **Week 24** (mixed-queue + capstone). These weeks share one trait:
they explicitly connect back to 2-4 prior weeks' skills rather than
introducing isolated new facts — the strongest pedagogical pattern in the
whole curriculum.

## Weakest 5 weeks

**Week 1** (0 lessons for 2 tickets + a required quiz — a genuine content
gap), **Week 10 and 12** (subnetting and routing/services are historically
the hardest topics for beginners, each backed by only 1 ticket), **Week 16**
(GPO precedence, one of the hardest concepts taught, gets thin practice),
**Week 21** (three substantial lessons, one ticket).

## Overloaded weeks

**Week 3** (13 optional quizzes) and **Week 7** (12 optional quizzes) are the
clearest overload risks — not because the required work is too heavy, but
because a motivated beginner who tries to "do everything visible" will hit a
wall of ExamCompass certification quizzes with no signal that they're
optional. **Week 4** is the heaviest *required* week (4 lessons + 4 tickets +
2 labs + Capstone 1 in a single week).

## Underdeveloped weeks

Weeks 10, 12, 14, 15, 16, 17, and 21 each pair 2-3 substantial lessons with
only 1 ticket — thin hands-on reinforcement for some of the program's
conceptually hardest material (subnetting, inter-VLAN routing, AD, GPO
precedence, PowerShell).

## Reorder candidates

None of the 25 weeks are out of pedagogical order — the sequence (hardware →
Windows desktop → queue/communication → client networking → switching/VLANs
→ routing → secure administration → Windows Server/AD → GPO → PowerShell →
Linux → cloud → integration) is coherent and each week's lessons explicitly
reference prior weeks by number. No reordering is recommended.

## Weeks that may be too advanced for their position

Weeks 16 (Group Policy precedence) and 21 (Linux production stack) ask a
beginner to reason about multi-factor precedence rules and multi-service
correlation respectively with less practice ticket volume than earlier,
easier weeks received. This is a pacing risk more than a sequencing error —
the fix is more practice at the same position, not moving the content.

## Weeks that under-prepare for the next stage

None outright fail to prepare for what follows — every lesson set explicitly
ties forward ("this pays off in Week X"). The closest candidate is Week 15
(domain-scale file access), which under-practices the A-G-DL-P pattern that
Week 16's GPO-deployed-drive-mapping content assumes fluency with.
