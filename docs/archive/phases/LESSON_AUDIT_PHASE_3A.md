# Phase 3A Lesson Audit

Date: 2026-08-10

This audit reviewed all 64 current lesson records, their weekly
`TrainingWeekActivity` references, source summaries, outcomes, video links,
and student rendering. The live database has no lesson video URLs. A video is
not the only meaningful lesson format: 62 lessons contain 867–2,299 characters
of original instructional guidance, concrete diagnostics/safety rules, and a
specific lab, CLI, Service Desk, or evidence-practice connection.

| Classification | Count | Decision |
| --- | ---: | --- |
| KEEP | 62 | Substantive standalone instructional lessons. |
| MERGE / CONTENT ALREADY COVERED | 0 | No duplicate filler wrappers found. |
| REMOVE FROM LEARNING PATH | 1 | Retire the 51-character CompTIA wrapper; preserve its historical row and notes. |
| SPECIAL ORIENTATION | 1 | Keep the substantive Week 0 walkthrough with explicit completion. |

## KEEP — substantive lessons

| Module | Lessons |
| --- | --- |
| MOD-001 | Anatomy of a Good Ticket; Meet the Command Line |
| MOD-002 | Storage: Symptoms Before Specs; RAM, CPU, Power, and POST; BIOS/UEFI and Boot Order |
| MOD-003 | Accounts, Profiles, and Permissions; The Investigator's Toolkit; Command-Line Diagnostics; Windows Update and Defender Basics (optional in the weekly checklist) |
| MOD-004 | Priority, Impact, and Not Making It Worse; Talking to Humans |
| MOD-005 | Startup Failures and Recovery Options; Application Crashes and Hangs; Disk-Space Incidents |
| MOD-006 | Account Lifecycle Support; NTFS vs Share Permissions, For Real; Access Requests and the Escalation Rail |
| MOD-007 | Defender and the Windows Firewall; Malware Response and Phishing Triage; Remote Desktop and Remote Support |
| MOD-008 | The Client-Side Network Triage Tree; Network Printing Without Tears; Running a Real Queue |
| MOD-009 | IPv4 Addressing You Can Reason With; Practical Subnetting for Support; ARP, MAC Learning, and Packet Flow |
| MOD-010 | Cisco CLI Modes and Verification; VLANs and Access Ports; Interface Status and Basic Port Troubleshooting |
| MOD-011 | Trunks and the Native VLAN; Inter-VLAN Routing and Static Routes; DHCP Relay, NAT, Firewall, VPN, and Wireless — Awareness |
| MOD-012 | Secure Switch Administration; Structured Network Troubleshooting |
| MOD-013 | Windows Server and Server Manager; Active Directory: Domains, OUs, Users, and Groups; The Core AD Account Tickets |
| MOD-014 | Domain Joins and Computer Accounts; Group-Based File Access at Domain Scale |
| MOD-015 | Group Policy Fundamentals; Troubleshooting Group Policy with gpresult and RSoP |
| MOD-016 | DNS and DHCP Server Roles; PowerShell for Investigation and Administration |
| MOD-017 | Server Operations: Logs, Services, and Scheduled Tasks; Windows Server Backup and a Real Restore; Patching and PowerShell Remoting at Scale |
| MOD-018 | The Linux Filesystem and Navigation; Permissions, Users, Groups, and sudo; Packages and SSH |
| MOD-019 | systemd Services and journalctl; Linux Networking and DNS Troubleshooting; Scheduled Jobs with cron |
| MOD-020 | Web Server and Firewall Administration; Resource Triage, Backup, and Bash; Monitoring and Alert Triage |
| MOD-021 | Cloud Concepts That Matter on the Job; Entra ID: Cloud Identity Administration |
| MOD-022 | Azure VMs and Network Security Groups; Azure Storage and Cloud-vs-On-Prem Thinking |
| MOD-023 | Working a Mixed Queue; Incident Communication and the Post-Incident Note |
| MOD-024 | Capstone Briefing: Your First Week at Maple & Finch |

## SPECIAL ORIENTATION

**Welcome to Nexus: Your First Week** is a 2,700-character walkthrough of the
platform, required/optional work, evidence, progression, help channels, and
the Week 0 guided-practice sequence. It remains a real orientation lesson, but
notes are optional and an explicit server-stored completion is now required.

## REMOVE FROM LEARNING PATH

**CompTIA 6-Step Process** was a 51-character summary ("Define, theorize,
test, plan, verify, and document.") plus three outcomes, no video, no
interactive task, and no unique instructional content. Its troubleshooting
concept remains represented in the orientation, substantive diagnostic
lessons, and Service Desk work. The historical lesson row and student notes are
preserved, but the lesson is retired and its required Week 0 activity is
removed.

## Nearby student-facing pages

| Classification | Finding |
| --- | --- |
| KEEP | My Training, Week Plan, Service Desk, CLI labs, guided labs, and the remaining lesson pages all have a defined learning or practice action. |
| REMOVE | The obsolete Week 0 methodology wrapper from live learning surfaces. |
| MERGE | None required. |
| REVIEW LATER | Browser E2E remains a later dedicated-credentials phase; its static Week 0 expectation was updated for this flow. |
