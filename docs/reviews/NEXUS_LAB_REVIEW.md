# Lab, Evidence, and Practical-Work Review

Date: 2026-07-21. Phase 10. Evidence: full reads of `backend/app/routers/
labs.py`, `cli_labs.py`, `evidence.py`, `backend/app/services/
evidence_validator.py`, `frontend/src/pages/TerminalCommandsPage.jsx`,
`CliLabsPage.jsx`/`CliLabPage.jsx`, the live `admin_lab_templates`/
`admin_vm_assignments`/`admin_ops_summary` API responses, and the 5 lab
templates' full content from the curriculum dump.

---

## 1. Manual Windows/Linux VM labs — confirmed disabled

**Confirming the review brief's claim.** `admin_vm_assignments` returns 0
rows live; `admin_ops_summary` shows `lab_runs: 2` (both from the mentor's
own dogfooding, per the Product Map) and 0 incidents/capstone runs. None of
the 5 live `LabTemplate` rows has a `proxmox_template_vmid` set — confirmed
directly in the admin lab-templates payload and in the curriculum dump.
**Automated VM controls remain disabled, as required by the brief.**
**Confirmed in code + Observed live.**

## 2. What the 5 live labs actually are

All 5 are **browser-based, evidence/description-driven exercises**, not VM
labs: "Hardware Component Identification" (identify parts from photos/
descriptions), "IP Addressing & Subnetting Practice" (pen-and-paper
calculations), "Troubleshoot a Network Connectivity Scenario" (scenario
reasoning), "Windows Command-Line Diagnostics" (run the real toolkit on the
student's own PC, submit annotated output), and one more tied to Week 15's
domain file-services content. This is a small, thin surface relative to 48
tickets — 5 labs across 25 weeks. **Confirmed in code + Observed live.**

## 3. Networking Labs (CLI simulator)

The `cli_labs` system (`CliLabsPage`/`CliLabPage`) is the actual hands-on
command-practice surface referenced constantly in the lesson text (e.g.
"complete CLI labs 1-9 of the meet-the-cli pack," "the learn-switching CLI
pack drills exactly these modes and commands in a safe simulator"). This is
where students practice `show` commands, VLAN config, and trunk
verification against a simulated device — genuinely valuable, low-risk
practice for concepts (Cisco CLI modes, VLANs, trunking) that would
otherwise require real switch hardware. **Confirmed in code.**

## 4. Terminal Practice vs. Command Library — confirmed near-duplicate

**Finding LAB-001 (P2).** Direct comparison of the two components: **Command
Library** (`/commands`, `CommandReferencePage`) and **Terminal Practice**
(`/terminal`, `TerminalCommandsPage`) both do the same core thing — search/
browse the same `CommandReference` catalog (50 entries) grouped by category,
rendered as clickable cards with syntax/description/example. `Terminal
Practice`'s only addition is an embedded `TerminalWidget` (xterm.js). Per
prior repo history (CLAUDE.md: "Terminal component via xterm.js — component
exists — NOT connected to backend"), **this widget is decorative** — it is
not wired to any real shell, simulated or otherwise. A student opening
"Terminal Practice" expecting to practice typing real commands finds a
search-and-browse tool nearly identical to Command Library, plus a terminal
window that doesn't do anything. This is worse than simple duplication — it
actively risks teaching a wrong impression ("I practiced in a terminal")
when nothing was executed or checked. **Recommendation: either wire
`TerminalWidget` to the same CLI-lab simulator backing `Networking Labs` (so
"Terminal Practice" becomes genuinely interactive), or remove the nav item
and fold Command Library + Networking Labs' simulator into two clearly
distinct, functional surfaces (reference lookup vs. graded simulator
practice).** This is the same finding as NAV-007/24-Week's duplication note,
elevated here with the concrete "non-functional widget" evidence.

## 5. Evidence validation — real anti-cheat checks, with one meaningful gap

`evidence_validator.py` (read in full) performs genuinely useful checks on
every uploaded screenshot: SHA-256 checksum against all previously-uploaded
evidence (catches literal re-uploads of the same file), EXIF timestamp
staleness (flags a screenshot older than 7 days — catches reusing an old
screenshot for a new ticket), and EXIF software-tag detection for
Photoshop/GIMP/Paint.NET (flags likely-edited images). This is solid,
proportionate anti-cheat design for a beginner cohort.

**Finding LAB-002 (P2).** The `must_contain_text` validation rule —
present in ticket 1's own `required_evidence` JSON (`"must_contain_text":
["DNS"]` on a screenshot) — is **only implemented for `artifact_type ==
"log"`** (plain-text file content), never for `artifact_type ==
"screenshot"` (confirmed directly in `evidence_validator.py`: the
`must_contain` check block is nested under `if artifact_type == "log":`,
entirely separate from the screenshot metadata block above it). **No OCR or
image-content check exists.** In practice, this means a student can upload
any screenshot at all — a wallpaper, an unrelated image, last week's
homework — as "proof" of running `ipconfig /all`, and the platform will
accept it as long as it isn't a byte-for-byte duplicate of a prior upload.
Combined with the fact that ticket/lab submission does not actually require
evidence to be present at all (`evidence_complete` is recorded as a boolean
but never blocks submission — confirmed in `tickets.py`), **evidence is
currently closer to "recommended documentation" than "proof of completion"**
for both tickets and labs.

## 6. Do labs award XP? (Confirming CUR-001 from the Product Map with full
   code detail)

**No.** `submit_lab()` in `labs.py` sets `run.status = "submitted"`,
defaults `run.final_score` to 10 if unset, and calls `log_activity()` for the
squad feed — there is no XP-ledger write anywhere in this function, and no
mentor-review gate (unlike tickets, which route through `pending →
verify-proof/reject-proof`). A lab is "done" the instant it's submitted,
with a near-meaningless default score of 10/10 if the (currently unused)
scoring path isn't populated. **This is inconsistent with the ticket flow
in every respect** — no XP, no mentor gate, no real default-score
meaning — and a beginner has no way to know these two "hands-on work" types
behave so differently.

## 7. Fakeable completion — direct answer to the central Phase 10 question

**Yes, labs and, to a lesser extent, tickets are currently fakeable.** A
student could submit any lab with no real screenshot at all (evidence isn't
required) and receive a default score of 10/10 with no mentor ever reviewing
it. A student could submit a ticket with an unrelated screenshot and pass
the (non-existent) content check on it. This does not mean students *will*
game the system — the small, known, five/six-person cohort with an engaged
mentor is a real mitigating factor absent from a large anonymous platform —
but the technical guardrail against it is thinner than the review brief's
framing assumed ("evidence submission" reads as a real proof gate; today it
is closer to an honor-system attachment).

## 8. Command-failure guidance and error recovery

Within the CLI-lab simulator, hint content (confirmed in the curriculum
dump for multiple labs) provides some scaffolding ("Focus on form factor,"
"Broadcast is always the last address"), but whether the simulator gives
live, command-specific error feedback when a student types an incorrect
command (vs. only grading the final submitted state) could not be verified
without a live browser session — **Not testable** in this environment.

## 9. Should Networking Labs remain a separate nav item?

**Recommendation: yes, but rename and clarify.** Networking Labs (the CLI
device simulator) is functionally distinct from both Labs (evidence-based
scenario/identification exercises) and Command Library (a lookup
reference) — it is the only place students get graded, interactive command
practice against a simulated device. The problem is not that it's separate,
it's that its name ("Networking Labs") doesn't signal "interactive
simulator" any better than "Labs" signals "evidence-based exercises." A
rename to something like "CLI Simulator" or "Practice Labs" paired with
folding "Terminal Practice" into it (per §4) would resolve both the naming
and duplication problems in one change.

## 10. Missing labs / tickets needing labs

Given the Ticket Review's finding that Weeks 10, 12, 14, 16, 17, and 21 each
pair substantial lessons with thin ticket practice and **zero labs**, the
clearest lab-gap candidates are: a guided **subnetting worksheet lab**
(Week 10 — currently only a lesson + 1 ticket), a **GPO precedence
worked-example lab** (Week 16 — the hardest concept in the program with the
thinnest practice), and a **PowerShell discovery-pipeline lab** (Week 17 —
"find every locked account" as a hands-on exercise rather than only a
ticket).

## 11. Summary of Phase 10 findings

- **LAB-001 (P2):** Terminal Practice and Command Library are near-duplicate
  features; Terminal Practice's xterm.js widget is decorative/non-
  functional. Merge or wire it up.
- **LAB-002 (P2):** Screenshot evidence has no content-validation (OCR) even
  where `must_contain_text` rules are explicitly authored for it — currently
  a silent no-op for the screenshot type.
- **CUR-001 (P2, full technical detail restated here):** Labs award no XP and
  have no mentor-review gate, unlike tickets — inconsistent design a
  beginner cannot be expected to intuit. (Primary ID is CUR-001, from the
  Product Map; not a separate LAB-### finding — see `NEXUS_FINDINGS.csv`.)
- **LAB-003 (P3):** Evidence is not required to submit a ticket or lab —
  "evidence submission" functions as optional documentation, not a
  completion gate.
- **LAB-004 (P3):** Add labs for subnetting (Week 10), GPO precedence
  (Week 16), and PowerShell discovery pipelines (Week 17) to firm up the
  program's thinnest hands-on weeks.
- **Confirmed per the brief's requirement:** automated Proxmox/Guacamole VM
  controls remain fully disabled — 0 live VM assignments, 0 lab templates
  with a VMID configured.
