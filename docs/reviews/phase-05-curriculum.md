# Phase 5 — My Training & Curriculum

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** LIVE. Pulled the full structure from production
(`/api/admin/training/weeks` + `/validation`) — **25 weeks, 296 activities** (not just counted:
every activity's type/ref/required/order analyzed). Rendered Week 0 as the temp student.

## Global composition (matches Progress page)
lesson **64** · video **137** · quiz **28** · support_ticket **48** · networking_lab **11** ·
guided_lab **5** · capstone **3** = **296**. Validation report: `valid:true`, 137/137 videos
mapped (**5 exact, 92 strong-topical, 40 week-level fallback**). Every week has learning goals;
only Week 0 skips the previous-week gate; no inactive weeks.

## Week-by-week (required-items / total activities / est. minutes)

| Wk | Title | Req | Total | Min | Sequence role |
|---|---|---|---|---|---|
| 0 | Welcome to Nexus | 5 | 6 | 60–93 | Orientation + 6-step process |
| 1 | IT Support and Ticket Basics | 7 | 10 | 227 | Support fundamentals |
| 2 | Computer Hardware | 10 | **25** | 300–354 | Hardware |
| 3 | Windows Fundamentals | 10 | **26** | 300 | OS |
| 4 | Working the Queue | 10 | **27** | 270 | Queue practice (+capstone) |
| 5 | Windows & Hardware Troubleshooting | 10 | 18 | 300 | Troubleshooting |
| 6 | Accounts and Permissions | 6 | 8 | 210 | Identity basics |
| 7 | Endpoint Security | 10 | 16 | 300 | Security |
| 8 | Client Networking | 10 | **20** | 300 | Networking (+capstone) |
| 9 | IP Addressing and Packet Flow | 7 | 10 | 240 | Networking |
| 10 | Switching and VLAN Basics | 7 | **21** | 300 | Networking (5 net-labs) |
| 11 | Routing and Network Services | 8 | 12 | 270 | Networking |
| 12 | Secure Network Administration | 7 | 8 | 240 | Network security |
| 13 | Active Directory Foundations | 6 | 6 | 240 | Identity/AD |
| 14 | Domain Operations and File Services | 4 | **4** | 210 | AD (lightest) |
| 15 | Group Policy | 7 | 7 | 210 | AD |
| 16 | Server Networking and PowerShell | 6 | 6 | 240 | Server |
| 17 | Server Operations and Recovery | 6 | 6 | 270 | Server |
| 18 | Linux Fundamentals | 5 | 9 | 240 | Linux |
| 19 | Linux Services and Troubleshooting | 5 | 6 | 240 | Linux |
| 20 | Linux Production and Security | 10 | **19** | 300 | Linux |
| 21 | Cloud Concepts and Identity | 8 | 9 | 210 | Cloud |
| 22 | Azure Infrastructure | 4 | 5 | 240 | Cloud |
| 23 | Integrated Operations | 5 | 5 | 240 | Integration |
| 24 | Capstone Readiness | 3 | 7 | 300 | Capstone (+capstone) |

## Sequence assessment (vs. the plan's ideal)
Progression is **logical and matches the target arc**: basics (W0–1) → hardware (W2) →
Windows/OS (W3) → troubleshooting (W5) → accounts/security (W6–7) → networking (W8–12) →
identity/AD/servers (W13–17) → Linux (W18–20) → cloud (W21–23) → capstone (W24). Capstones are
distributed (W4, W8, W24), giving mid-course milestones rather than a single end-load. **No
out-of-order topics** were found.

## Workload assessment
- **Required load is well-controlled** (mostly 5–10 items, ~210–300 min/week ≈ 3.5–5 hr). Good
  for part-time beginners.
- **Total activity count swings wildly (4 → 27)** because optional videos vary hugely: W2 (25),
  W3 (26), W4 (27), W10 (21), W8 (20), W20 (19) vs. W14 (4), W22/W23 (5). The required/optional
  split (UI shows "0 of N required") mitigates overwhelm, but **a beginner opening Week 2 still
  sees 25 cards** — the jump from W1's 10 to W2's 25 is visually jarring. Consider collapsing
  optional videos by default in dense weeks.
- **Hands-on is thin relative to watching:** 137 videos vs. only 5 guided labs + 11 networking
  labs. Support tickets (48) carry most of the practical load. For a job-oriented beginner
  program, more guided labs (or clearer "do this" tasks) would strengthen skill-building.

## Every activity answers the 5 questions?
- **What am I learning / why:** Week-level `learning_goals` (present for all 25 weeks) + lesson
  intros. Good at week level; not every individual video has its own objective (they inherit the
  week's).
- **What should I do / how do I know I'm done:** The week page's Learn/Practice layout with
  Required/Optional badges, time estimates, per-activity Start / Mark Watched / Take Quiz, and a
  progress bar makes "what to do" and "done" clear. **Strong.**
- **What next:** "Continue Next Activity" button + "Next: …" hint. **Strong.**

## Week 0 deep-dive (reviewed carefully per plan)
Welcoming and gentle (≈2 hr, 5 required). Goals: "Find your way around Nexus", "Use the six-step
troubleshooting process." Learn list: *Welcome to Nexus: Your First Week* (lesson) → *CompTIA
6-Step Process* (lesson) → *A+ Exams* (video, optional) → *Ticketing Systems* (video) →
*Ticketing Systems Quiz* → *Document Types* (video). First meaningful success (finish a lesson,
pass a short quiz) is reachable quickly. **First experience is welcoming, not overwhelming.**

Two concrete Week-0 issues:
1. **Content inconsistency (P3):** the first lesson body says *"Nexus is your **24-week** practice
   space"* while the program is **25 weeks** (W0–24). Same "24 vs 25" mismatch as README. Fix the
   lesson copy (and README) for consistency.
2. **Ordering (Future/low — this is the plan's known observation #1):** the **Document Types**
   video is ordered **after** the **Ticketing Systems Quiz**. Confirmed live. Impact is low (the
   quiz covers ticketing, not documents), but pedagogically the content-after-its-section reads
   slightly off. Safe to leave; if touched, place Document Types before the quiz.

## Other observations
- **Video mapping precision:** only **5 of 137** videos are *exact* quiz mappings; 92 are
  "strong topical" and 40 are "week fallback." Quizzes therefore assess topic areas, not specific
  videos — acceptable for a survey course but worth tightening for weeks with graded quizzes → Phase 7.
- **Known observation #2 (MOD-001 prerequisite repair on full seed):** deferred to Phase 11 (DB/seeds).
- No orphaned/duplicate activities or broken content refs surfaced (validation `valid:true`).

## Is the curriculum ready for the five students?
**Yes, with minor polish.** Sequence is sound, Week 0 is welcoming, required workload is
reasonable, and content validates. Recommended pre-cohort polish (all low-risk): fix "24 vs 25"
copy; consider collapsing optional videos in the 20+-activity weeks; add a couple more guided
labs in early weeks to balance watch-vs-do. None of these block launch.

## Priorities
- P3: "24-week" copy fix (lesson + README). P2/UX: dense-week optional-video presentation.
- P2/curriculum: watch-heavy vs. hands-on ratio (more guided labs early). Future: Document Types
  ordering; tighten exact video→quiz mappings.
