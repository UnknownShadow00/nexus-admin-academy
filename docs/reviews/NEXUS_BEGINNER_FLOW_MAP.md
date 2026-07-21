# Beginner Flow Map

Date: 2026-07-21. Phase 17. A single visual reference tracing a first-time
student from login through their first ticket, annotated with every finding
from this review that lands on that step.

```mermaid
flowchart TD
    A[Student logs in for the first time] --> B[Home page: name + 4 stat cards, all zero]
    B -->|NAV-001, NAV-002: no welcome message,\nfallback copy assumes a returning user| C["This Week" panel]
    C -->|NAV-003: collapses to one quiz line,\nno context this IS all of Week 0| D[Student takes the one Week 0 quiz]
    D -->|ONBOARD-002: quiz doesn't test\nthe lesson that was just read| E[Student sees Week 1: 2 tickets assigned, 0 lessons]
    E -->|LESSON-001: no lesson exists\nto teach this content| F[Student opens Ticket 1: DNS issue]
    F --> G[Student clicks Submit]
    G -->|"TICKET-001 / TECH-001 (P0): 403 blocked.\n'Complete 40% of A+ Study Tracker' —\na term never explained, requiring\n~9 hours of unrelated video-watching"| H{Student is stuck here\non Day 1 or 2}
    H -.->|If gate is fixed/lowered| I[Ticket submitted, AI grades it]
    I -->|Confirmed working well:\nstrengths/weaknesses/score shown,\n"awaiting instructor verification" banner| J[Mentor reviews: verify or reject]
    J -->|Confirmed working well:\nneeds_revision + Resubmit button| K[Student resubmits if needed]
    J -->|verify-proof| L[XP granted, ticket marked passed]
    L --> M[Student notices Capstones tab already unlocked]
    M -->|NAV-004 / CUR-002: capstone content\nfully visible/accessible at 0 XP\nbecause all templates have role_level=NULL| N[Confusion: "should I be doing this now?"]
```

## Reading the map

The two points where a real beginner is most likely to actually stop
making progress — not just feel confused, but be structurally blocked or
misdirected — are **G→H** (the A+ unlock gate, P0) and **B→C** (no
onboarding, P1). Every other annotated step is a clarity problem a student
would likely push through with mentor help, given this is a small,
closely-mentored cohort; **G→H is the one step that would generate a
support request or a stalled student even with a mentor present**, because
nothing in the product explains what happened or what to do about it.

The **M→N** branch (capstone visibility) is a lower-severity but earlier-
appearing confusion point — it can happen before a student has done any
real work at all, simply by looking at the nav bar.

## What "good" looks like after the Phase-16 fixes

With TICKET-001, ONBOARD-001, CUR-002, LESSON-001, and the NAV-001/002/003
copy fixes applied, the same flow becomes: login → oriented by a short
Week 0 welcome → takes an aligned Week 0 quiz → reads a real Week 1 lesson →
submits Ticket 1 successfully → sees clear AI + mentor feedback → resubmits
or moves on → Capstones tab stays hidden until genuinely earned. No
structural change to the ticket-grading engine, the mentor-review workflow,
or the curriculum sequencing is required to reach this state — every fix on
the critical path is small and well-understood.
