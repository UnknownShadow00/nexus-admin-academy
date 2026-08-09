# Nexus — Curriculum Audit

**Updated:** 2026-08-08 · Final hardening audit against the branch database and
`backend/scripts/validate_training_curriculum.py`: **25 contiguous weeks (0–24), 296 activities,
137/137 videos mapped, validation `valid:true`, no broken references or gating issues.**
Composition: lesson 64 · video 137 · quiz 28 · support_ticket 48 · networking_lab 11 ·
guided_lab 5 · capstone 3. Fresh-seed idempotency and the same totals are covered by automated tests.

## Sequence assessment
The program follows the intended skill arc and **no out-of-order topics were found**:
basics (W0–1) → hardware (W2) → Windows/OS (W3) → troubleshooting (W5) → accounts & security
(W6–7) → networking (W8–12) → identity/AD/servers (W13–17) → Linux (W18–20) → cloud (W21–23) →
capstone readiness (W24). Capstones are distributed (W4, W8, W24) as mid-course milestones.

## Week-by-week (required / total activities / est. minutes)
| Wk | Title | Req | Total | Min | Notes |
|---|---|---|---|---|---|
| 0 | Welcome to Nexus | 5 | 6 | ~93 | Gentle orientation + 6-step process. Fresh seeds place both required videos before the quiz; the checked branch DB retains an older video-after-quiz order. |
| 1 | IT Support and Ticket Basics | 7 | 10 | 227 | Good on-ramp to ticket work. |
| 2 | Computer Hardware | 10 | **25** | ~354 | **Dense** (15 optional videos) — jarring jump from W1. Collapse optional videos. |
| 3 | Windows Fundamentals | 10 | **26** | 300 | Dense. |
| 4 | Working the Queue | 10 | **27** | 270 | Dense; includes a capstone. |
| 5 | Windows & Hardware Troubleshooting | 10 | 18 | 300 | Core troubleshooting. |
| 6 | Accounts and Permissions | 6 | 8 | 210 | Identity basics. |
| 7 | Endpoint Security | 10 | 16 | 300 | Security. |
| 8 | Client Networking | 10 | **20** | 300 | Networking begins; capstone. |
| 9 | IP Addressing and Packet Flow | 7 | 10 | 240 | + networking labs. |
| 10 | Switching and VLAN Basics | 7 | **21** | 300 | 5 networking labs. |
| 11 | Routing and Network Services | 8 | 12 | 270 | — |
| 12 | Secure Network Administration | 7 | 8 | 240 | — |
| 13 | Active Directory Foundations | 6 | 6 | 240 | — |
| 14 | Domain Operations and File Services | 4 | **4** | 210 | **Lightest** week. |
| 15 | Group Policy | 7 | 7 | 210 | — |
| 16 | Server Networking and PowerShell | 6 | 6 | 240 | — |
| 17 | Server Operations and Recovery | 6 | 6 | 270 | — |
| 18 | Linux Fundamentals | 5 | 9 | 240 | — |
| 19 | Linux Services and Troubleshooting | 5 | 6 | 240 | — |
| 20 | Linux Production and Security | 10 | **19** | 300 | Dense. |
| 21 | Cloud Concepts and Identity | 8 | 9 | 210 | — |
| 22 | Azure Infrastructure | 4 | 5 | 240 | Light. |
| 23 | Integrated Operations | 5 | 5 | 240 | Light. |
| 24 | Capstone Readiness | 3 | 7 | 300 | Capstone close. |

## Workload concerns
- **Required load is well-balanced** (5–10 items, ~210–300 min/week ≈ 3.5–5 hr) — appropriate for
  part-time beginners.
- **Total activity count swings 4→27** because optional videos vary. The required/optional split
  (UI shows "0 of N required") mitigates this, but **dense weeks (W2/W3/W4 = 25–27 cards) still
  look overwhelming**. Recommend collapsing optional videos by default in 15+-activity weeks.

## Sequence / prerequisite problems
- **None structural** — every week has learning goals, `requires_previous_week` set (except W0),
  no orphaned/duplicate activities, no broken refs (`valid:true`).
- **Known observation #1 (low):** in the checked branch database, the **Document Types** video is
  ordered **after** the **Ticketing Systems Quiz**. Fresh seeds already place it before the quiz.
  Do not hand-edit production; apply the reviewed idempotent curriculum seed only as an intentional
  release content step after backup.
- **Known observation #2 (benign):** running the full seed reconciles a missing MOD-001
  prerequisite (self-heal). Not a defect.

## Duplicate / repeated material
- **Weekly Roadmap** repeats across Home / My Training / Progress (navigation dedupe, not curriculum).
- **All Course Content** re-presents the same 137 videos the Weekly Plan sequences — intentional
  "browse vs guided" split; acceptable.

## Video → quiz mapping quality
- 137/137 mapped, but only **5 exact**, 92 strong-topical, 40 week-fallback. Quizzes assess topic
  areas, not specific videos. Fine for formative use; **tighten exact mappings for graded weeks**.

## Lesson quality (from Phase 6)
- 64 lessons, all published, median summary 1532 chars — **good**. **One stub:** lesson 1
  "CompTIA 6-Step Process" (51 chars) — a required 45-min Week 0 lesson that needs real authoring.
- **Authored learning objectives (`outcomes`) exist for 63/64 lessons but are never shown** (API
  omits the field; page doesn't render it). High-value fix.

## Practical / hands-on balance
- 137 videos vs **only 5 guided labs** + 11 networking labs; 48 tickets carry most hands-on load.
  For a job-oriented program, **add a few early-week guided labs** to balance watch-vs-do.

## Does every activity answer the 5 questions?
- *What am I learning / why:* week `learning_goals` (all present) + lesson intros — good at week level.
- *What to do / how do I know I'm done:* week page Learn/Practice layout, Required/Optional badges,
  time estimates, Start/Mark Watched/Take Quiz, progress bar — **clear**.
- *What next:* "Continue Next Activity" + "Next: …" — **clear**.
- Gap: individual videos inherit the week's objective rather than each having its own.

## Recommended standard lesson template (practical to maintain)
Backed by existing model fields (`outcomes`, `summary`, `required_notes_template`):
Objective (surface `outcomes`) → Why it matters → Key terms → Main explanation → Worked example →
Common mistakes → Practice task (link ticket/lab) → Quick knowledge check (link quiz) → Related
video/quiz/lab → Notes prompt.

## Is the curriculum ready for the five students?
**Yes — with minor, low-risk polish** (none blocking):
1. Author lesson 1 (CompTIA 6-Step stub).
2. Surface lesson objectives (`outcomes`).
3. Collapse optional videos in dense weeks (W2–W4).
4. Add a couple of early-week guided labs.
Optional/low: Week-0 Document Types ordering; tighten exact video→quiz maps.

## Priorities
- P1: surface `outcomes`. P2: author lesson 1; dense-week presentation; more early labs.
- P3: exact quiz mappings; reconcile the older checked-DB Week 0 order through the reviewed seed process.
