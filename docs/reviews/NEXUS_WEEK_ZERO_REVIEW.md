# Week 0 Onboarding Review

Date: 2026-07-21. Phase 5. Evidence: full read of Week 0's live curriculum
content (`.tmp/review/curriculum_dump.md` lines 37–156), the live
`week_plan`/`dashboard` API responses for a fresh disposable student, and
`StudentHome.jsx`/`WeekPlanPanel.jsx`.

---

## 1. What Week 0 actually contains (Confirmed in code + Observed live)

- **1 module** (`MOD-000` — Troubleshooting Methodology)
- **1 lesson** ("CompTIA 6-Step Process," 45 min, teaching text: *"Define,
  theorize, test, plan, verify, and document"* — three outcome bullets)
- **1 required quiz** ("Ticketing Systems Quiz," 4 questions, ExamCompass-
  sourced, about ticket-system data fields — not actually about the 6-step
  method taught in the one lesson)
- **0 tickets, 0 labs, 0 capstones**

## 2. Does Week 0 teach the ~17 named onboarding skills a beginner needs?

The requested onboarding skillset (navigating the platform, understanding
XP, understanding required vs. optional, understanding tickets/labs/
evidence vocabulary, submitting work, reading feedback, finding the next
task, etc.) is **not taught anywhere in Week 0's content**, and is not taught
anywhere else in the platform either (no dedicated onboarding module exists
in the 25-module catalog). Week 0's single lesson teaches troubleshooting
methodology — a real, useful, on-topic skill for the *curriculum*, but it is
not platform onboarding. **Finding ONBOARD-001 (P1).**

## 3. The lesson/quiz mismatch

**Finding ONBOARD-002 (P2).** The one lesson teaches the CompTIA 6-step
troubleshooting method (define/theorize/test/plan/verify/document). The one
required quiz tests ticketing-system data-entry fields (category, escalation
level, progress notes) — a related but different topic, sourced from a
different ExamCompass page than the lesson. A student who read the lesson
carefully and then takes the quiz will find none of the lesson's content
tested, and none of the quiz's content taught by the lesson. This is a
"taught before tested" gap on the very first assessment a student ever
takes — a bad first impression for the assessment system's credibility.

## 4. Should Week 0 include a guided practice task?

**Yes — recommended.** Every other week in the 24-week body has at least one
ticket or lab giving the student a concrete, gradable, "try it yourself"
moment (confirmed in the week-by-week structural index). Week 0 currently has
none. Given Week 0 is every student's literal first experience with the
platform, the absence of a guided practice task (a sample lesson-note
exercise, a harmless practice screenshot upload, a one-question practice
quiz with immediate feedback walking through the UI, or a 2-minute "submit a
comment on this ticket, see how grading feedback looks" dry run) means the
first time a student encounters ticket submission, evidence upload, or AI
grading is Week 1+ — with real grading consequences and no rehearsal. A
zero-stakes walkthrough belongs here.

## 5. Recommended Week 0 additions (product judgment, not yet built)

1. A short, platform-specific "how Nexus works" orientation — 5 minutes,
   explaining: what a week is, what's required vs. optional, what XP is
   vs. Role, how ticket grading + mentor review works end-to-end, and where
   to go if stuck (the mentor's Discord). This directly fixes ONBOARD-001
   and overlaps with NAV-001/002/005 from the Navigation Review — one
   implementation fixes multiple findings.
2. Either replace the Ticketing Systems Quiz with one aligned to the 6-step
   lesson, or add a second, aligned quiz — fixes ONBOARD-002.
3. Add one ungraded or low-stakes practice ticket/evidence-upload flow so
   "submit → AI grade → mentor verify" is rehearsed once before it counts.

## 6. Net Week 0 verdict

Content quality (the one lesson that exists) is good — consistent with the
strong writing quality found across the whole curriculum (see Lesson
Review). The problem is not quality, it is completeness: Week 0 is not
currently doing the job "Week 0" needs to do for total beginners, which is
platform orientation, not curriculum content. This is the most consequential
and least expensive fix in the entire review — see Final Response's
recommended first implementation phase.
