# Job-Ready Curriculum Blueprint (Phase 4A)

Status: Phase 4A — audit, classification, and blueprint. Structural (code-only)
changes implemented; full sequence reorder deferred pending authorization (see
"Structural constraint" below). Content authoring is Phase 4B/4C.

**Phase 4A.1 update (see the Phase 4A.1 report for full detail):** two things
in this document have since changed and should be read as historical
Phase 4A context, not current state:

1. §5/§6 originally left `stage.network_administration` positioned *before*
   Identity & Access (a structural relabel only, sequence unchanged).
   Phase 4A.1 corrected the Stage order itself to the target in that phase's
   prompt: Networking for Support → Identity & Access → Microsoft Workplace →
   **Network Administration & Infrastructure** → Systems & Server. The STAGES
   tuple in `curriculum_structure.py` now reflects this directly.
2. §0's "structural constraint" is still accurate for the Learning Path/Today
   system, but Phase 4A.1 discovered a **second**, independent, legacy
   week_number-indexed progression system
   (`progression_service.derive_current_week`/`MODULE_WEEKS`/`CLI_PACK_WEEKS`,
   and `service_desk_progression.SERVICE_DESK_PACKS`) that gates Service Desk
   packs, CLI packs, and legacy ticket/lab/capstone access independently of
   `TrainingWeek.display_order`. Phase 4A.1 deliberately did not reorder that
   system — see its report for the full analysis and the promotion-gate
   implications (`docs/PROGRESSION_CONTRACT.md` Gate 3/Gate 4).

The `TrainingWeek.display_order` code is now written and validated
(`training_curriculum_seed.sync_advanced_networking_resequence`, migration
`0056_advanced_networking_resequence`) but **not yet applied to production** —
that requires the explicit authorization described in the Phase 4A.1 report.

## 0. Structural constraint discovered during this phase

`curriculum_structure.py` (Stage/Module metadata) only controls how the
Learning Path **groups and labels** content
(`training_service._build_stage_path`). The actual **unlock/progression
sequence** a student experiences (what's next, what's locked, what "Today"
surfaces) is driven independently by `TrainingWeek.display_order` in the
database (`training_service._active_weeks`, `_build_state`). Today the two are
kept in lockstep (`module.source_week_number` order == `TrainingWeek.week_number`
order == Stage/Module display order), because Phase 3 built them that way.

Consequence: relabeling or regrouping Stage/Module metadata (safe, code-only)
does **not** move a module earlier or later in the student's actual required
path. Physically moving content (e.g. pushing deep Cisco networking after
Identity/M365, per the target order below) requires changing
`TrainingWeek.display_order` on production rows — a production database
mutation, which this phase's authorization explicitly excludes ("do not
mutate production database"). `week_number` (the stable mapping key) is
untouched by this, so the change is low-risk and reversible when authorized,
but it is a data change, not a code change, and needs its own explicit
per-turn authorization.

**What Phase 4A therefore implements:** structural relabeling that improves
clarity without changing sequence (see §6 "Structural changes implemented").
**What Phase 4A defers:** the physical reorder in §5 "Target order" that
requires moving weeks past each other. That is recommended as the very next
authorized action, before Phase 4B content is written into the M365 stage
slot, so 4B content lands in its permanent sequence position instead of being
moved twice.

## 1. Job-market conclusions

Repeated, cross-posting requirements for Twin Cities help desk / service desk
/ desktop support / junior sysadmin roles (per the priorities supplied and
cross-checked against the existing curriculum):

- **Very high / high**: troubleshooting methodology, customer communication,
  ticket documentation, Windows 10/11, desktop/laptop support, Microsoft 365,
  Outlook, Teams, Active Directory, Entra ID, MFA, account/access
  administration, TCP/IP, DNS, DHCP, Wi-Fi, VPN, printers/peripherals, remote
  support.
- **High / medium-high**: Intune, MDM, endpoint deployment/imaging,
  onboarding/offboarding, Exchange Online, OneDrive, SharePoint, Group
  Policy, BitLocker, endpoint security, mobile-device support.
- **Role-dependent / later**: PowerShell, Windows Server, Linux,
  Cisco/VLAN/routing, firewall administration, Azure infrastructure, backups,
  RMM/PSA, deeper infrastructure administration.

Nexus's current curriculum already gets most of the *order* right by
accident of Phase 1-3 design (orientation → endpoint → Windows → networking →
identity → server → Linux → cloud → integrated). The two biggest misalignments
with the market data are: (a) deep Cisco-style networking (switching/VLANs,
trunking, routing) is bundled with entry-level client networking in one
block, ahead of Identity, when the market treats it as later/role-dependent;
and (b) Microsoft 365 / Entra / Intune — the single most repeated
requirement set — has no dedicated presence at all.

## 2. Module audit

Legend for "action": KEEP, KEEP+IMPROVE, MOVE (stage relabel now; physical
sequence move deferred), SPLIT, REDUCE, OPTIONAL/ADVANCED, MERGE, EXPAND,
REBUILD.

Depth: RECOGNIZE / WORKING KNOWLEDGE / MUST PERFORM.
Track: JOB-PRACTICAL / CERT-ALIGNED / BOTH.

| # | Module (week) | Stage (new) | Req/Opt | Learn/Check/Practice/Trbl/Prove | Action | Depth | Track | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | orientation.nexus (w0) | Orientation | 2/3 | 4/1/0/0/0 | KEEP+IMPROVE | RECOGNIZE | JOB-PRACTICAL | Add explicit troubleshooting-methodology + ticket-lifecycle framing so it fully covers Stage-0 topics, not just workflow tooling. |
| 2 | endpoint.support_workflow (w1) | Endpoint Foundations | 5/3 | 5/1/1/1/0 | KEEP | WORKING KNOWLEDGE | JOB-PRACTICAL | Already carries most of "ticket lifecycle/evidence/communication." Highest job-relevance module in the path. |
| 3 | endpoint.pc_hardware (w2) | Endpoint Foundations | 12/11 | 20/1/1/1/0 | REDUCE | RECOGNIZE→WORKING KNOWLEDGE | BOTH | 17 optional videos, 1 lab. Trim to core components/docks/monitors/peripherals; push deep component trivia to reference/optional. |
| 4 | windows.fundamentals (w3) | Windows Support | 4/18 | 18/3/1/0/0 | KEEP+IMPROVE | WORKING KNOWLEDGE | BOTH | Video-heavy (14 optional), thin practice. Needs more Check/Practice in 4C. |
| 5 | windows.queue_operations (w4) | Windows Support | 3/21 | 20/1/1/1/1 | KEEP+IMPROVE | MUST PERFORM | JOB-PRACTICAL | De facto "Service Desk Operations" teaching point (ticket ownership/impact/urgency). Cross-reference module 1 to avoid duplication. |
| 6 | windows.troubleshooting (w5) | Windows Support | 4/13 | 14/1/1/1/0 | KEEP+IMPROVE | MUST PERFORM | JOB-PRACTICAL | Name promises troubleshooting; only 1 troubleshoot activity today. Needs more scenarios (4C). |
| 7 | windows.accounts_permissions (w6) | Windows Support | 4/4 | 4/1/1/2/0 | KEEP | MUST PERFORM | JOB-PRACTICAL | Best-balanced module in the path. Anchor point for identity-verification security cross-cut. |
| 8 | windows.endpoint_security (w7) | Windows Support | 5/10 | 12/1/1/1/0 | KEEP+IMPROVE | WORKING KNOWLEDGE→MUST PERFORM | BOTH (SAFETY CRITICAL) | BitLocker/containment; video-heavy, thin practice. |
| 9 | networking.client_triage (w8) | **Networking for Support Technicians** (new) | 6/12 | 14/1/1/1/1 | MOVE (stage relabel) | MUST PERFORM | JOB-PRACTICAL | Exactly the entry-level networking the market wants (ping/ipconfig/DNS/local-vs-upstream). |
| 10 | networking.ip_addressing (w9) | **Networking for Support Technicians** (new) | 4/6 | 5/2/3/0/0 | MOVE (stage relabel) | WORKING KNOWLEDGE | BOTH | Good practice ratio via networking_lab. |
| 11 | networking.switching_vlans (w10) | **Network Administration & Infrastructure** (new) | 5/15 | 14/1/5/0/0 | MOVE (deferred physical move) | WORKING KNOWLEDGE | CERT-ALIGNED | Role-dependent per market data. Relabeled out of the entry-level networking stage now; recommend physically sequencing after Identity/M365 once authorized. |
| 12 | networking.routing_services (w11) | **Network Administration & Infrastructure** (new) | 5/5 | 6/1/3/0/0 | SPLIT (future) | WORKING KNOWLEDGE | CERT-ALIGNED/BOTH | Bundles high-priority DNS/DHCP service troubleshooting with lower-priority deep routing/trunk config. Recommend splitting DNS/DHCP-service-troubleshooting content into the support-networking stage in 4B; keep routing/trunk depth in this stage. |
| 13 | networking.secure_admin (w12) | **Network Administration & Infrastructure** (new) | 2/6 | 5/1/2/0/0 | MOVE (deferred physical move) | WORKING KNOWLEDGE | CERT-ALIGNED | Same as #11. |
| 14 | identity.active_directory (w13) | Identity & Access | 3/3 | 4/1/1/0/0 | KEEP+IMPROVE | MUST PERFORM | JOB-PRACTICAL | Zero troubleshoot activities despite AD/account work being a top market skill. Priority gap for 4C. |
| 15 | identity.domain_access (w14) | Identity & Access | 2/3 | 2/1/1/1/0 | KEEP | WORKING KNOWLEDGE | JOB-PRACTICAL | Has ticket-based troubleshoot coverage already. |
| 16 | identity.group_policy (w15) | Identity & Access | 2/4 | 4/1/1/0/0 | KEEP | WORKING KNOWLEDGE | BOTH | No troubleshoot activity; medium-high market priority. |
| 17 | server.powershell_services (w16) | Systems & Server Foundations | 4/2 | 4/1/1/0/0 | KEEP | WORKING KNOWLEDGE | BOTH | Positioning already reasonable (role-dependent, appropriately late). |
| 18 | server.operations_recovery (w17) | Systems & Server Foundations | 3/3 | 4/1/1/0/0 | KEEP | WORKING KNOWLEDGE | CERT-ALIGNED | Same. |
| 19 | linux.fundamentals (w18) | Linux Support | 5/3 | 6/1/1/0/0 | KEEP | WORKING KNOWLEDGE | CERT-ALIGNED | Role-dependent, valuable breadth. |
| 20 | linux.services (w19) | Linux Support | 2/3 | 3/1/1/0/0 | KEEP | WORKING KNOWLEDGE | CERT-ALIGNED | — |
| 21 | linux.production (w20) | Linux Support | 2/16 | 16/1/1/0/0 | REDUCE | WORKING KNOWLEDGE | CERT-ALIGNED | 13 optional videos; trim breadth, keep core log/security triage. |
| 22 | cloud.identity (w21) | Cloud & Infrastructure | 6/3 | 7/1/1/0/0 | KEEP | WORKING KNOWLEDGE | BOTH | Bridges naturally into future M365/Entra cloud-identity content. |
| 23 | cloud.azure_infrastructure (w22) | Cloud & Infrastructure | 2/2 | 2/1/1/0/0 | OPTIONAL/ADVANCED | RECOGNIZE→WORKING KNOWLEDGE | CERT-ALIGNED | Already appropriately light; do not expand ahead of M365 content per market priority. |
| 24 | integrated.operations (w23) | Integrated Support & Capstone | 3/3 | 3/2/1/0/0 | KEEP+IMPROVE | MUST PERFORM | JOB-PRACTICAL | Expand cross-domain ticket variety in 4C. |
| 25 | integrated.final_shift (w24) | Integrated Support & Capstone | 1/5 | 4/0/1/0/1 | KEEP | MUST PERFORM | JOB-PRACTICAL | Capstone Prove module. |

**Counts**: KEEP 10, KEEP+IMPROVE 7, MOVE 4, SPLIT 1, REDUCE 2,
OPTIONAL/ADVANCED 1, MERGE 0, EXPAND 0, REBUILD 0. No module needed a full
rebuild or merge — the Phase 3 structure is fundamentally sound; the work is
rebalancing depth/practice, not replacing content.

## 3. Activity-mix gap summary (roles: Learn/Check/Practice/Troubleshoot/Prove)

Stage-level totals (required + optional activities):

| Stage | Learn | Check | Practice | Troubleshoot | Prove |
|---|---|---|---|---|---|
| Orientation | 4 | 1 | 0 | 0 | 0 |
| Endpoint Foundations | 25 | 2 | 2 | 2 | 0 |
| Windows Support | 68 | 7 | 5 | 5 | 1 |
| Networking (both new stages) | 44 | 6 | 14 | 1 | 1 |
| Identity & Access | 10 | 3 | 3 | 1 | 0 |
| Systems & Server | 8 | 2 | 2 | 0 | 0 |
| Linux Support | 25 | 3 | 3 | 0 | 0 |
| Cloud & Infrastructure | 9 | 2 | 2 | 0 | 0 |
| Integrated & Capstone | 7 | 2 | 2 | 0 | 1 |
| **Total** | **200** | **28** | **33** | **9** | **3** |

The path is overwhelmingly Learn-weighted (video-driven). Troubleshoot and
Prove are structurally scarce everywhere except the two networking stages
(which get Practice from the CLI simulator) and the handful of Service Desk
scenario modules. This is the single clearest, most actionable gap: **Windows,
Identity, Systems/Server, Linux, and Cloud stages need materially more
Troubleshoot-role activities**, not more Learn content. Phase 4C should target
this directly rather than adding more videos.

## 4. Certification vs. job-practical balance

Roughly even split by module count (13 JOB-PRACTICAL/BOTH-leaning modules
carrying the entry-level day-one skills vs. 12 CERT-ALIGNED/BOTH modules
covering broader infrastructure). The certification material (hardware
trivia, deep Linux/server, deep networking) is not being deleted — it's
being deprioritized in *sequence and prominence*, not removed. Nexus should
keep both: cert-aligned breadth as reference/foundation, job-practical depth
as the thing students are actually assessed and drilled on.

## 5. Target order (recommended; §0 explains what's implemented vs. deferred)

```
Stage 0  Technician Orientation                      (unchanged position)
Stage 1  Endpoint Foundations                         (unchanged position)
Stage 2  Windows Support                              (unchanged position)
Stage 3  Networking for Support Technicians            (relabeled now; same weeks 8-9)
Stage 4  Network Administration & Infrastructure       (relabeled now; same weeks 10-12 —
                                                         target: physically move after Stage 6)
Stage 5  Identity & Access                             (unchanged position)
Stage 6  Microsoft 365, Entra & Endpoint Management     (NEW empty placeholder — Phase 4B content)
Stage 7  Systems & Server Foundations                  (unchanged position)
Stage 8  Linux Support                                 (unchanged position)
Stage 9  Cloud & Infrastructure Foundations             (unchanged position)
Stage 10 Integrated Support & Capstone                  (unchanged position)
```

The one deferred physical move: Stage 4 (deep switching/VLAN/routing/secure
admin, weeks 10-12) should eventually sit *after* Stage 6 (M365), not before
Identity. That requires the authorized `TrainingWeek.display_order` change
described in §0. Until then it stays where it physically is today (right
after support-level networking, before Identity) — correctly labeled as
"later/role-dependent" but not yet resequenced.

## 6. Structural changes implemented in this phase (code-only, `curriculum_structure.py`)

- Split `stage.networking_foundations` into `stage.networking_support`
  (client triage + IP addressing, weeks 8-9) and
  `stage.network_administration` (switching/VLANs, routing/services, secure
  admin, weeks 10-12). No module's `source_week_number` or relative order
  changed — this is a pure relabel/regroup, zero sequence risk.
- Added an empty placeholder stage `stage.microsoft_workplace` ("Microsoft
  365, Entra & Endpoint Management") positioned after Identity & Access. It
  has zero modules today, so `_build_stage_path` skips it entirely (no
  visible effect on the current Learning Path) until Phase 4B adds modules.
- Documented the display-order/gating decoupling directly in the module
  docstring so future editors don't assume relabeling reorders progression.

**Not implemented** (requires DB authorization, see §0): physically moving
weeks 10-12 later; splitting `routing_services` content; any change to
`TrainingWeek` rows.

## 7. Service Desk cross-cutting distribution

Current `service_desk_scenario` presence by stage (from live data):

| Stage | Weeks with a ticket scenario |
|---|---|
| Endpoint Foundations | w1, w2 |
| Windows Support | w4, w5, w6 (x2), w7 |
| Networking for Support Technicians | w8 |
| Identity & Access | w14 |
| Systems/Server, Linux, Cloud, Integrated | **none today** |

Tickets are already reasonably threaded through Orientation → Endpoint →
Windows → early Networking → Identity. The gap is Systems/Server, Linux,
Cloud, and Integrated, which have zero ticket-type activities despite being
exactly where "mixed queue" and cross-domain tickets belong per the target
design. Phase 4C should add scenarios there, plus M365-flavored tickets
(Outlook/Teams/MFA) once Phase 4B content exists.

## 8. Security cross-cutting distribution

| Job-practical anchor | Security concept | Current coverage |
|---|---|---|
| Password reset (w6) | Identity verification | Present (accounts_permissions) |
| MFA reset (future M365) | Account-takeover risk | **Gap — Phase 4B** |
| Email (future M365) | Phishing | **Gap — Phase 4B** |
| Endpoint (w7) | Malware/isolation | Present, thin practice |
| Permissions (w6, w13-15) | Least privilege | Present |
| PowerShell (w16) | Safe change practices | Present, thin |
| Network (w10-12) | Firewall/exposure | Present, cert-leaning |
| Server (w17) | Patching/backup/recovery | Present |
| Cloud (w21-22) | Shared responsibility | Present |

No new security content added in this phase per scope; table records where it
already lives and where 4B/4C must add it (MFA/phishing, both tied to the
missing M365 stage).

## 9. Microsoft 365 / Entra / Intune blueprint (Phase 4B target — not authored here)

All proposed as modules inside `stage.microsoft_workplace`, in learning order:

| Module | Why it matters | Depth | Prerequisite | Learn | Check | Practice | Troubleshoot | Prove | Tenant/lab needed? |
|---|---|---|---|---|---|---|---|---|---|
| M365 Support Foundations | Single most-repeated market requirement; students need the M365 admin center mental model | WORKING KNOWLEDGE | Windows Support, Identity & Access | Video/lesson tour of M365 admin center, licensing basics | Quiz on admin roles/license types | Guided walkthrough of a tenant | Simulated "can't access X app" ticket | — | Simulated first; real/dev tenant later |
| Entra ID & Authentication | Cloud identity is now the primary identity plane employers ask about | MUST PERFORM | M365 Support Foundations | Entra concepts vs on-prem AD | Quiz: hybrid identity, sync basics | Guided Entra user/group walkthrough | Sign-in failure / conditional-access ticket | Prove: resolve an identity-lockout ticket end to end | Simulated first |
| Outlook / Exchange Online | Outlook is a named top-priority tool | MUST PERFORM | M365 Support Foundations | Exchange Online admin basics | Quiz on mailbox/distribution concepts | Guided mailbox/permission walkthrough | Outlook connectivity/profile ticket | — | Simulated |
| Teams / OneDrive / SharePoint | Named top/high priority collaboration stack | WORKING KNOWLEDGE | Outlook/Exchange module | Teams/OneDrive/SharePoint admin tour | Quiz on sharing/permissions model | Guided sharing-config walkthrough | "Can't access shared file" ticket | — | Simulated |
| MFA & Identity Troubleshooting | Named top priority; ties directly to account-takeover security cross-cut | MUST PERFORM (SAFETY CRITICAL) | Entra ID & Authentication | MFA methods, risk concepts | Quiz on verification requirements | Guided MFA reset walkthrough with identity verification | MFA lockout / suspicious sign-in ticket | Prove: MFA reset following verification policy | Simulated |
| Intune & Endpoint Management | High/medium-high priority, direct extension of endpoint-security module | WORKING KNOWLEDGE | Windows Support, M365 Support Foundations | Intune console tour, MDM concepts | Quiz on enrollment/compliance concepts | Guided policy walkthrough | Non-compliant-device ticket | — | Simulated first; real tenant valuable later |
| Device Enrollment & Compliance | Extension of Intune; frequently paired with onboarding | WORKING KNOWLEDGE | Intune & Endpoint Management | Enrollment methods (Autopilot concepts) | Quiz | Guided enrollment walkthrough | Failed-enrollment ticket | — | Simulated |
| Employee Onboarding | Named recurring MSP/help-desk task | MUST PERFORM | Entra ID, Intune modules | Onboarding checklist walkthrough | Quiz | Guided new-hire setup exercise | — | Prove: complete an onboarding ticket end to end | Simulated |
| Employee Offboarding | Same, paired with security (account/access removal) | MUST PERFORM (SAFETY CRITICAL) | Employee Onboarding | Offboarding checklist walkthrough | Quiz | Guided deprovisioning exercise | Offboarding-with-open-access-risk ticket | Prove: complete offboarding correctly (access fully removed) | Simulated |
| Mobile Device Support | High/medium-high priority | RECOGNIZE→WORKING KNOWLEDGE | Intune & Endpoint Management | Mobile MDM concepts tour | Quiz | — | Lost/wiped-device ticket | — | Simulated |

Recommend: all ten initially simulated (matches existing Nexus pattern of
guided labs + service-desk-scenario simulation); a real/dev M365 tenant is a
later enhancement, not a Phase 4B blocker.

## 10. Endpoint support gap blueprint

Not currently modeled as distinct activities; recommended placement:

| Topic | Placement | Depth |
|---|---|---|
| Laptop/dock setup, multi-monitor | Endpoint Foundations (expand pc_hardware) | WORKING KNOWLEDGE |
| Printers/peripherals | Windows Support (queue_operations already touches this — confirm scope in 4C) | WORKING KNOWLEDGE |
| Webcams/headsets, Teams Rooms basics | Microsoft Workplace stage (paired with Teams module) | RECOGNIZE |
| Mobile devices | Microsoft Workplace stage (Mobile Device Support module) | RECOGNIZE |
| Wi-Fi, VPN | Networking for Support Technicians (client_triage already partially covers; confirm/expand in 4C) | WORKING KNOWLEDGE |
| Browser problems, Office apps | Windows Support (windows.fundamentals) | WORKING KNOWLEDGE |
| Windows Update, drivers | Windows Support (windows.troubleshooting) | WORKING KNOWLEDGE |
| BitLocker | Windows Support (endpoint_security, already present) | WORKING KNOWLEDGE |
| Imaging/deployment concepts | Microsoft Workplace stage (Device Enrollment module, Autopilot-adjacent) | RECOGNIZE |
| Hardware replacement, asset handling | Endpoint Foundations (pc_hardware) | RECOGNIZE |

## 11. MSP workflow gap blueprint

No commercial product integration. Recommend a lightweight "MSP context"
thread inside Integrated Support & Capstone (not a new stage): PSA/RMM
concepts, multiple-customer context switching, SLA/priority concepts, client
documentation habits, recurring-issue pattern recognition. This is a
workflow-literacy addition, not new tooling — matches scope rule (no real
commercial products).

## 12. Content to defer (explicitly out of scope for 4A and 4B)

Persistent fictional company, competency/challenge-out engine, real M365
tenant automation, Proxmox/Guacamole/Cisco/Ubiquiti hardware integration,
portfolio/career features. Unchanged from the standing scope rules.

## 13. Phase 4B implementation list

1. Author the 10 Microsoft Workplace modules above (content, quizzes, guided
   labs, service-desk scenarios) into `stage.microsoft_workplace`.
2. Get authorization and execute the deferred `TrainingWeek.display_order`
   move for weeks 10-12 (Network Administration) so it sequences after the
   new M365 stage, matching the label already applied in this phase.
3. Expand `pc_hardware`, `windows.fundamentals`, and `linux.production` per
   the REDUCE findings (trim optional video sprawl, keep core).
4. Split `routing_services` DNS/DHCP-troubleshooting content into the
   support-networking stage per the SPLIT finding.

## 14. Phase 4C practical reinforcement list

1. Add Troubleshoot-role activities (service_desk_scenario or equivalent) to
   every stage currently at zero: Systems/Server, Linux, Cloud, Integrated.
2. Add troubleshoot coverage to `identity.active_directory` (currently zero
   despite being a top market skill) and `identity.group_policy`.
3. Expand `integrated.operations` ticket variety to include mixed-domain and
   (once 4B lands) M365-flavored tickets.
4. Add MFA-reset and offboarding Prove-level scenarios once 4B modules exist.

## Self-review

Checked for and did not find: overengineering (no new competency engine, no
new dataclass fields beyond what already existed), certification-order bias
driving the target sequence, advanced networking left too early (relabeled
out of the entry-level stage), Linux/server/cloud crowding out support skills
(their stage positions are unchanged and already appropriately late), missing
M365 placement (now has a reserved, empty, structurally safe slot), progress
regression (validated — see Tests), hidden week-number assumptions (documented
explicitly in the module docstring), duplicate curriculum source of truth
(none introduced; `curriculum_structure.py` remains sole authority for
Stage/Module display).

One thing deliberately *not* fixed in this phase: insufficient practical
troubleshooting/ticket work is the single largest gap (§3), but fixing it
means authoring dozens of new scenarios — explicitly Phase 4B/4C scope, not
4A.

## Recommendation

**GO** to merge Phase 4A: the audit, classification, and blueprint are
complete; the only code change (`curriculum_structure.py` stage split +
placeholder) is validated as zero-risk (0 issues, 273/273 still mapped,
counts unchanged).

**Before Phase 4B**, recommend a short, explicitly-authorized micro-task to
execute the deferred `TrainingWeek.display_order` move for weeks 10-12 (§0,
§5, §13.2), so Phase 4B content is written directly into its permanent
sequence position instead of being authored once and resequenced later.
