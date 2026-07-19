# Quiz Curriculum Gaps

Audit date: 2026-07-19 UTC

## Gap rule

A “gap” below remains only after reusing, correcting, expanding, or merging the existing 104 quizzes. The plan does not propose a new quiz merely because an imported bank is imperfect. Scenario-based means learners must interpret symptoms/output, choose a safe next action, or produce a workplace decision—not recall a label.

## Genuine new-question gaps

| Week | Topic | Why existing questions are insufficient | Recommended questions | Form |
|---:|---|---|---:|---|
| 0 | Troubleshooting methodology | No quiz assesses the six-step process. Later seed items apply pieces of it but do not test hypothesis, controlled change, verification, and documentation as a sequence. | 8 | Scenario-based |
| 1 | CLI evidence and verification | #1 covers tickets; none of the 104 tests why command output is evidence, before/after verification, safe read-only discovery, or what belongs in a ticket from the CLI labs. | 6 | Scenario/output-based |
| 10 | Switch output interpretation | #12 is only seven questions and must serve the weekly assessment. No spare bank tests `show interfaces status`, VLAN membership, admin-down versus notconnect, and verify/save through realistic output. | 6 | Scenario/output-based |
| 19 | Linux services, logs, DNS, and cron practice | #21 is the only aligned quiz. #97/#98 cover basic Linux commands/features, not journal evidence, minimal cron environment, or Linux DNS triage. | 8 | Scenario/output-based |
| 20 | Monitoring evidence and alert triage | #22 covers the weekly concepts but there is no separate practice bank for baseline versus anomaly, alert noise, scope/impact, log growth, and alert-clear verification. | 6 | Scenario/chart/output-based |
| 21 | Microsoft 365 support operations | The curriculum covers Entra identity but no quiz covers Exchange/Outlook service health, license assignment, Teams/SharePoint access routing, OneDrive sync triage, or when to check Microsoft 365 service health. No existing quiz can be safely repurposed without losing its subject. | 10 | Mostly scenario-based |
| 22 | Azure evidence and monitoring | #24 tests VMs/NSGs/storage but no practice quiz tests Activity Log versus sign-in log, Resource Health, Azure Monitor evidence, or alert-based routing. | 6 | Scenario/output-based |
| 23 | Mixed-queue technical triage | #43 and #48 can provide asset/incident practice, but no existing quiz except #25 spans Windows/Linux/network/cloud in one queue. #25 is needed for the Week 24 cumulative gate. | 10 | Scenario-based |

New-question total if all are approved: **60**. These should be authored only after the placement/merge decisions are approved, because expansions below may reduce that number.

## Gaps closed by editing existing quizzes

| Week | Topic | Existing reuse recommendation | Question action |
|---:|---|---|---|
| 2 | Hardware troubleshooting | Make #78 the weekly assessment; use #79/#71/#73 for practice and #68/#69/#72 for remediation. | Curate #78 to 12 strong scenarios; re-key and explain all retained imports. |
| 4 | Ticket documentation, ITIL, communication, change | Expand #5; use #51 and #44 as practice. | Add 4 cross-week scenarios to #5; re-key/import explanations. |
| 5 | Windows recovery | Keep #6 and use #39/#86. | Correct q649 and add rationale. |
| 6/14 | NTFS/share and group access | Keep #7/#16; use #102 once at Week 6 as targeted practice with Week 14 prerequisite reuse by reference, not duplicate quiz rows. | Correct permission precedence/move/copy wording explanations. |
| 7 | Security escalation | Keep #8; use #32/#53 and merge #31/#41/#101 for remediation. | Remove certification-only phrasing and emphasize contain/preserve/escalate. |
| 8 | DNS/DHCP/network triage | Expand #9; use #64/#82; merge #59/#95 remediation. | Add Weeks 5–8 cumulative scenarios. |
| 9 | Subnetting/packet flow | Keep #10/#11; merge sound #61 items into remediation only after full re-key. | Correct q1984 and all affected imported keys. |
| 11 | Network services/ports | Keep #13; curate #58; use #56 only as remediation. | Convert port trivia into symptom/service decisions where possible. |
| 12 | Network cumulative/gate | Expand #14 and merge #57/#104 as optional awareness practice. | Add trunk/routing/DHCP relay/port-security output scenarios. |
| 13 | Active Directory basics | Keep #15 and repair #103 remediation. | Add explanations; avoid treating direct recall as promotion proof. |
| 15 | Group Policy | Keep #17 and rely on the VM break/fix lab for practical proof. | Correct q2039 refresh timing; no new quiz required unless a separate practice bank is desired. |
| 16 | DNS/DHCP/PowerShell cumulative | Expand #18 and use #52 remediation. | Add output/pipeline/-WhatIf scenarios to the existing assessment. |
| 17 | Backup and recovery | Expand #19 with sound concepts from #45. | Require restore verification and permission/version checks. |
| 18 | Linux fundamentals | Keep #20; use #97 and merge #85/#98 remediation. | Re-key and add command-output explanations. |
| 20 | Linux cumulative | Expand #22 across Weeks 18–20. | Add systemd/cron/permissions/backup transfer questions. |
| 24 | Integrated promotion gate | Move and expand #25. | Grow from 6 to 15–20 scenarios; preserve capstone as the authoritative practical assessment. |

## Topic coverage conclusion

- Ticket documentation: strong (#1, #5, tickets); only a CLI-evidence check is missing.
- Troubleshooting methodology: applied throughout, but Week 0 has no direct assessment.
- Windows administration / AD / PowerShell: strong core seed coverage; imported banks are support/remediation only.
- Linux: strong required seed coverage; Week 19–20 practice depth is missing.
- Networking / DNS / DHCP: strong after remapping; imported port/protocol banks must not become required.
- Security escalation: strong; imported physical/logical breadth belongs mostly in certification practice.
- Microsoft 365: genuine content and assessment gap beyond Entra identity.
- Azure fundamentals: required concepts exist; evidence/monitoring practice is thin.
- Backup/recovery: covered in Weeks 17 and 20; strengthen restore verification rather than create another definition quiz.
- Monitoring: Week 20 seed is good but has no practice bank.
- ITIL/service management and professional communication: #5, #44, #51, tickets, and incident lessons are sufficient after edits.

## Approval decisions before authoring

1. Confirm that #25 moves to Week 24 and that a new Week 23 mixed-queue quiz is acceptable.
2. Approve which imported banks become remediation versus certification-only.
3. Approve the 7–28 normal weekly question workload and conditional remediation model.
4. Decide whether the new-question gaps are in scope or should be met by expanding the named seed quizzes further.
