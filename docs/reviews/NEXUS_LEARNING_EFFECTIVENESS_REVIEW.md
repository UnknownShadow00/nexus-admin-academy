# Learning Effectiveness Review

Date: 2026-07-21. Phase 11. Evidence: the full 63-lesson read (Lesson
Review), the full 48-ticket/5-lab title and sample-content read, the
promotion-gate requirement structure, and the AI-grading live test results
(Ticket Review).

---

## 1. Skill-area classification

| Skill area | Classification | Basis |
|---|---|---|
| Troubleshooting methodology (6-step) | Adequate | Taught once (Week 0), thin depth, but reinforced implicitly every week after via the same pattern |
| Ticket documentation / internal-vs-user-facing notes | **Strong** | Taught explicitly (Week 2), graded on every one of 48 tickets via the `communication` anchor |
| Hardware diagnostics (storage/RAM/CPU/POST/BIOS) | Strong | 3 dense lessons, 4+ tickets, explicit safety framing |
| Windows desktop administration (accounts/profiles/permissions/CLI tools) | Strong | 4 lessons, sustained ticket coverage weeks 4-8 |
| Prioritization & queue management | Strong | Explicit priority=impact×urgency framework, reinforced at increasing scale (Week 5 → Week 9 Multi-Ticket Sim → Week 24 mixed queue) |
| Professional/incident communication | Strong | Graded on every ticket via the `communication` anchor; dedicated lessons in Weeks 5 and 24; **too-cert-focused: no** — this is the most workplace-realistic skill area in the program |
| Security fundamentals (malware/phishing/endpoint) | Adequate | Good procedural teaching (Week 8); ticket coverage exists but is thinner than desktop/networking |
| Remote support (RDP/Quick Assist) | Adequate | One lesson, one ticket; etiquette content is strong but volume is thin |
| Client networking diagnostics (DNS/DHCP/gateway triage tree) | **Strong** | Arguably the single best-taught skill in the program (Week 9's triage tree), reinforced on Linux (Week 20) and Azure (Week 23) |
| IP addressing / subnetting | Adequate, under-practiced | Strong teaching approach ("answer real questions, not exam arithmetic") but only 1 ticket |
| Switching/VLANs/CLI verification discipline | Strong | 3 lessons, 3 tickets, explicit change→verify→save discipline |
| Inter-VLAN routing & network services (DHCP relay/NAT/firewall/VPN awareness) | Adequate, under-practiced | Appropriately scoped ("recognize, don't design") but only 1 ticket for a lot of new vocabulary |
| Secure network administration (SSH/port security/logging) | Adequate | Good content, thin standalone ticket practice (folded into the Week 13 synthesis) |
| Structured multi-layer network troubleshooting (L1-L4 method) | **Strong** | The clearest synthesis lesson in the program |
| Windows Server & Active Directory administration | Adequate, under-practiced | Strong conceptual teaching, thin ticket volume for how hard AD is for a true beginner |
| Group Policy reasoning (LSDOU/gpresult) | Weak-to-adequate | The hardest concept in the program with the thinnest practice (1 ticket) |
| PowerShell (investigation-first) | Adequate, under-practiced | Excellent pedagogical framing ("discover, don't guess") but only 1 ticket exercises it directly |
| Backup/restore discipline | Strong | The "restore and verify" lesson directly targets the single most common real-world failure (untested backups) |
| Linux administration (filesystem/permissions/services/networking/cron) | **Strong** | Deliberately mirrors the Windows arc 1:1 — the best-designed transfer-learning sequence in the curriculum |
| Linux production operations (web/firewall/monitoring) | Adequate, under-practiced | Strong content, thin standalone ticket practice |
| Cloud concepts & responsibility model (IaaS/PaaS/SaaS) | Adequate | Necessarily abstract; zero-cost design is a real strength; benefits from a non-text exercise |
| Entra ID / cloud identity | Strong | Directly ties to the AD skill area with clear "same ideas, new home" framing |
| Azure infrastructure (VMs/NSGs/storage) | Adequate | Good "outside-in" triage framing; appropriately scoped to support-level, not architecture-level |
| Incident response & blameless post-incident writing | **Strong** | The capstone-grade skill; genuinely advanced and realistic for a junior-level program |

No skill area classified as **Missing**, **Too-theoretical**, **Too-cert-
focused**, or **Repetitive-without-purpose**. The weakest classifications
are **Group Policy** (hardest concept, thinnest practice) and, to a lesser
extent, subnetting/PowerShell/AD — all "adequate teaching, under-practiced"
rather than poorly taught.

## 2. Answering the 9 core Phase 11 questions

**1. Can a student demonstrate competence without passing every quiz?**
Yes by design — progression math counts only required/validated/checklist
quizzes, and mastery/promotion depend more heavily on verified tickets and
practical checkpoints than on quiz volume. This is a genuine strength: quiz
performance is not the bottleneck the way ticket/practical performance is.

**2. Is demonstration (showing you can do the work) adequate?** Strong for
desktop/networking/Linux; weaker for AD/GPO/PowerShell purely on ticket
*volume*, not teaching quality.

**3. Is hands-on practice adequate?** Mixed — see the "under-practiced"
column above. The lab surface itself is thin (5 labs total) and, per the Lab
Review, currently not meaningfully gated (no XP, no mentor review, no
evidence-content check) — so "hands-on" work that does exist carries less
real accountability than tickets do.

**4. Is there spaced repetition?** Yes, and it's one of the program's best
features — account lifecycle management is taught 4 times at increasing
scope (desktop → desktop-in-practice → AD → Entra ID), and network
diagnostic triage is taught 3 times across different platforms (Windows →
switching → Linux → Azure), each time explicitly cross-referenced.

**5. Is difficulty gradual?** Mostly yes; Week 4 (24-Week Review) and the
Week 16 GPO jump are the two clearest exceptions to otherwise smooth pacing.

**6. Does this resemble real help-desk/sysadmin work?** Yes, more than
almost any comparable bootcamp curriculum reviewed against this brief — the
ticket-grading rubric (investigation/root_cause/safe_fix_or_escalation/
verification/communication) is itself a realistic model of how real
incident work is judged, and the capstone's "inherit an undocumented
environment" framing is a genuinely common first-90-days scenario for a
junior hire.

**7. Is the evidence students produce portfolio-worthy?** Partially. The
*content* students would produce (ticket write-ups, a runbook, a post-
incident note) is genuinely portfolio-quality if done well — but see the Lab
Review's finding that evidence isn't currently verified for authenticity, so
"portfolio-worthy" currently depends entirely on individual student
diligence rather than platform enforcement.

**8. What would an employer still need to teach a graduate?** Real
enterprise-scale tooling (a real ticketing system like ServiceNow/Freshdesk
rather than Nexus's own model, real Group Policy at scale with dozens of
GPOs, real change-management/CAB process, and vendor-specific tools the
program correctly scopes out) — but the *reasoning* patterns (triage,
escalation judgment, safe-fix discipline, documentation habits) transfer
directly and are the hardest things to teach on the job, which is exactly
what this curriculum concentrates on.

**9. What produces the most job-readiness?** The ticket-grading rubric
itself (investigation → root cause → safe fix/escalation → verification →
communication) is the single highest-leverage design element in the whole
platform — it is applied consistently across all 48 tickets and the entire
gate/capstone system, meaning a student who takes tickets seriously is
drilled on the actual shape of real support work 48+ times, independent of
which specific technology each ticket covers.

## 3. Summary findings

- **LEARN-001 (P3):** Group Policy (Week 16) is the clearest under-practiced/
  too-hard-for-its-practice-volume skill area — add a worked precedence
  example (already recommended in the Lesson and 24-Week reviews).
- **LEARN-002 (P3):** AD, subnetting, and PowerShell would each benefit from
  one additional ticket to match their conceptual difficulty.
- **LEARN-003 (P2, restates CUR-001/LAB-003):** because hands-on
  lab work carries no real accountability (no XP, no mentor gate, no
  evidence verification), the "hands-on adequacy" answer is weaker than the
  underlying lab *content* deserves — this is a platform-enforcement gap,
  not a curriculum-design gap.
