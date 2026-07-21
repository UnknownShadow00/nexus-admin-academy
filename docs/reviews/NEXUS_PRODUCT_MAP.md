# Nexus IT Academy — Product Map

Date: 2026-07-21. Phase 2 of the full platform review. Built from: Codex's
static system map (models/routers/services), a live API walkthrough against
`https://nexus.builtfromzero.fyi` using a disposable student account
(`nexus-review-student`) and the real admin credential, direct reads of
`frontend/src/App.jsx`, `StudentHome.jsx`, `WeekPlanPanel.jsx`, and a full read
of the seeded curriculum content (25 weeks, 63 lessons, 48 tickets, 5 lab
templates, 3 capstones, 104 quizzes) via `.tmp/review/curriculum_dump.md`.

Evidence labels used throughout this review series: **Observed live**,
**Confirmed in code**, **Both**, **Code-inferred only**, **Not testable**.

---

## 1. What Nexus actually is

A 24-week (Week 0–24) self-hosted training platform that walks a small,
named cohort of beginners from "what is a ticket" to a integrated capstone
simulating a junior infrastructure administrator's first week at a fictional
company ("Maple & Finch Co."). It is not a generic LMS — nearly every unit of
content is IT-support-specific and workplace-shaped: tickets are graded like
real tickets, labs are graded like real diagnostics, and the final capstone
is a four-stage simulated on-call week, not a written exam.

**Confirmed in code + Observed live.**

## 2. The core loop, as designed

```
Student logs in
  → Home shows XP / streak / quiz-done / tickets-passed + "This Week" panel
  → "This Week" panel lists this week's required quizzes / tickets / labs
  → Student opens a quiz → answers → immediate score + explanations
  → Student opens a ticket → reads scenario → runs (simulated) commands
      → submits plain-English explanation → AI grades against 5 anchors
      → mentor reviews AI's grade → verifies (grants XP) or requests revision
  → Student opens a lab → follows setup instructions → submits evidence
      (screenshots) → currently auto-scored, no mentor gate, no XP awarded
  → XP accumulates → level changes (Trainee → Help Desk I/II → Junior
    SysAdmin → SysAdmin) and, separately, Promotion Gates unlock formal
    Roles (Support Tech I/II → Network Support Tech → Junior Systems Tech →
    Junior Infrastructure Administrator) once lesson/mastery/ticket/CLI-lab/
    quiz thresholds are met for that gate
  → Capstones (3, one per curriculum third) become available — but
    currently unlock for everyone regardless of role or XP (see §6)
```

**Confirmed in code**, most steps also **Observed live** via the disposable
account's API responses.

## 3. Content inventory (live DB, confirmed)

| Item | Count |
|---|---|
| Modules | 25 (MOD-000 … MOD-024) |
| Lessons | 63 |
| Quizzes | 104 (967 questions) |
| — required + gate + cumulative (all validated, checklist-visible) | 25 |
| — practice / certification / remediation (many not answer-validated) | 79 |
| Tickets | 48 |
| Lab templates | 5 (all manual/browser-based; 0 with `proxmox_template_vmid`) |
| Capstone templates | 3 |
| Command-reference entries | 50 |
| Promotion gates | 29 (across 6 roles) |
| Curriculum videos | 182 |

Every one of the 25 weeks (0–24) has at least one required, validated,
checklist-visible quiz. Week 0 has no lessons and no tickets/labs — it is a
single methodology lesson plus one quiz (see the Week 0 review). Weeks 1–24
each carry 1–4 lessons, 1 ticket-writing-adjacent lesson block, 2-3 tickets on
average (48 across 24 content weeks), and a steady drip of CompTIA
certification-bank quizzes (examcompass-sourced) layered alongside the
original, workplace-scenario "required" quiz for that week.

**Confirmed in code, Observed live** (counts match both the DB dump and the
live `/api/study-tracker/curriculum` response).

## 4. The two parallel progression systems (important, easy to miss)

Nexus tracks **two separate ladders** that a beginner will not intuitively
distinguish:

1. **XP / Level** — a simple point total (`XPLedger`) driving a cosmetic
   level name (Trainee, Help Desk I/II, Junior SysAdmin, SysAdmin) and the
   leaderboard. Awarded on first quiz attempt and on mentor-verified tickets.
2. **Role / Promotion Gate** — a real credential-like progression
   (Support Technician I/II → Network Support Technician → Junior Systems
   Technician → Junior Infrastructure Administrator) gated by
   `min_completed_lessons`, `min_mastery_by_domain`, `min_verified_tickets_by_
   difficulty`, `practical_checkpoint` (a named Multi-Ticket Simulation ticket
   with a hint cap), `min_cli_labs`, and `no_unresolved_flags` — a real,
   multi-criterion gate, one per role, 29 individual requirement rows total.

Nothing in the UI (per the `StudentHome.jsx` / nav read) explains that these
are different things or how they relate. A student can plausibly ask "why do
I have a level but no role" or vice versa. **Confirmed in code.** Flagged as
`ONBOARD-` in the beginner-navigation review.

## 5. Data model shape (from Codex's static trace, confirmed against live
   API shapes)

```
Module ──< Lesson                     (no week_number column on Lesson;
                                        week mapping goes through
                                        students.py: MODULE_WEEKS)
Quiz ──< Question ; Quiz >──< QuizAttempt   (mastery = best score;
                                              XP = first attempt only)
Ticket ──< TicketSubmission ──AI-graded──> mentor verify/reject
  (AI grading stores a `pending` score but does NOT grant XP;
   mentor `verify-proof` grants the stored XP and ticket mastery;
   mentor rejection sets `needs_revision`)
LabTemplate ──< LabRun ──< evidence
  (submission defaults an unset score to 10; current code does NOT
   award XP for labs at all)
CapstoneTemplate ──< CapstoneRun
  (availability requires `published` AND student role rank ≥ template's
   `role_level` — but all 3 live templates have role_level = NULL, so this
   gate is currently a no-op; every student sees Capstones as unlocked)
Role ──< PromotionGate ; Role ──< StudentRole
StudentMethodologyProgress   (a `can_access_tickets()` check exists in
                              methodology_enforcer.py but is not actually
                              called from tickets.py — not enforced)
XPLedger ──> total_xp ──> level name
```

**Confirmed in code.** The two parenthetical gaps (labs award no XP;
capstone role-gate is a no-op because every seeded template has
`role_level = NULL`) are structural findings carried into Phase 16 as
CUR-001 and CUR-002.

## 6. Navigation surface (frontend, confirmed in code + observed live)

Student nav — 9 items, identical desktop/mobile (`App.jsx` `studentNavItems`):
Home, Learning Path, Study Tracker, Tickets, Labs, Networking Labs, Capstones,
Command Library, Terminal Practice. Capstones is hidden only when
`has_unlocked_capstones === false` is *explicitly* returned by the API — and
for a brand-new disposable student at 0 XP, the live API returned
`has_unlocked_capstones: true` (because of the CUR-002 gap above), so
Capstones is visible to a student who has done nothing yet. This is examined
in depth in the beginner-navigation review.

Admin nav — 11 items, all gated by `AdminAccessGate` (a completely separate
session mechanism from student `RequireAuth`).

## 7. Essential vs. optional content, as designed

- **Essential per week**: exactly one required/validated/checklist quiz
  (every week 0–24), plus that week's tickets/labs where present.
  Progression math (`students.py`) only counts quizzes with both
  `is_required=true` and `show_in_weekly_checklist=true`.
- **Optional**: the large tail of certification-bank quizzes
  (practice/certification/remediation purpose) that mirror CompTIA A+/
  Network+ objective areas. These are scraped from ExamCompass, many have
  `answer_keys_validated=false` and visibly blank `explanation` fields (seen
  directly in Week 1's Mobile Device quizzes and confirmed system-wide via the
  admin editorial queue — 79 quizzes, many at `quality_score` 57-67 with
  several-of-N questions missing explanations). These are NOT required for
  progression and are NOT hidden — they sit in the same student-visible quiz
  browsing surface as required quizzes, distinguishable only by metadata a
  beginner never sees.

**Confirmed in code, Observed live.**

## 8. Duplicated / overlapping concepts an admin or student could confuse

- **Networking Labs vs. Terminal Practice vs. Command Library** — three
  separate nav items that all involve running commands in a simulated
  environment or looking commands up. Whether these should stay separate is
  examined in the Lab Review (Phase 10).
- **XP level vs. Role** — see §4.
- **Study Tracker vs. Learning Path** — Study Tracker exposes a
  certification-objective-driven catalog (`/api/study-tracker/curriculum`);
  Learning Path exposes the week-by-week module/lesson/video sequence. Both
  are legitimate but the naming does not make the distinction obvious to a
  first-time user (see Navigation Review).

## 9. Mentor-facing surface (admin panel)

11 admin sections covering student overview/roster, ticket submissions review
queue, quiz editorial queue, AI cost dashboard, promotion-gate config, lab/
capstone template CRUD, VM assignment table (currently always empty — no
automated VM activity exists), an ops summary, and a squad-activity feed.
Live admin data (Observed live, 2026-07-21) shows: all 6 real students at 0
XP / 0 quizzes / 0 tickets done (confirming "students have not officially
started"); the **Mentor's own account** shows 1 in-progress ticket
submission (`User cannot browse the internet`, submitted 2026-07-18) and 2
`lab_started` squad-activity entries from 2026-07-18 — most likely the
mentor's own dogfooding/testing of the platform, but this is visible to
students in the shared squad-activity feed and could read as "the mentor is
already ahead of us" or otherwise confuse a first-time cohort. Flagged as
ADMIN-### in Phase 14/16.

## 10. Confirmed platform-status facts vs. the user's original claims

| Claim in the review brief | Status |
|---|---|
| Manual-VM launch readiness | **Confirmed** — 0 of 5 lab templates have a `proxmox_template_vmid`; all labs are browser/evidence-based |
| Automated labs disabled | **Confirmed** — `admin_vm_assignments` live returns 0 rows; Proxmox/Guacamole env vars unset in production per prior security review |
| HTTPS redirect enabled | **Confirmed live** — `http://` now returns 301 to `https://` |
| Security hardening deployed | **Confirmed live** — CSP/HSTS/X-Content-Type-Options/Referrer-Policy/Permissions-Policy all present (still duplicated on proxied paths, a known cosmetic issue) |
| Tests/build/integrity recently passed | Re-verified independently in Phase 15 (Technical Review) |
| Unvalidated quizzes hidden | **Not accurate as stated** — unvalidated/`needs_edit` quizzes are not hidden from students; they are simply excluded from required-progression math. They remain visible and attemptable. See §7 and QUIZ review. |
| Email privacy on `GET /api/students` | **Confirmed** — live admin students-overview payload contains no email/private fields beyond what's expected for an admin-only endpoint |
| "Five real student accounts" | **Discrepancy** — live roster is 6 non-mentor students (Shak, Rakib, Ahmed, Emran, Walo, Hudayfa) + 1 Mentor = 7 total accounts. The brief's "five real students" does not match current production data. Recommend reconciling before finalizing cohort-size assumptions. |

This table is the authoritative fact-check referenced by every later phase —
later documents do not re-derive it.
