# Prioritized Action Plan

Date: 2026-07-21. Phase 17. Sourced from `NEXUS_FINDINGS.csv` (44 findings
across P0-P4). This plan sequences the same findings into a launch
timeline; it does not introduce new findings. **No fix in this plan has
been implemented — this is a plan for the project owner to approve before
any production code change is made.**

---

## Before Week 0 begins (blocking or near-blocking)

1. **TICKET-001 / TECH-001 (P0)** — Fix the A+ Study Tracker 40% unlock gate
   silently blocking all ticket/lab/capstone/CLI-lab work. Either lower the
   threshold for cohort launch or add visible in-app messaging before a
   student ever hits the 403. This is the one finding that turns "confusing"
   into "the platform doesn't work as designed" for a real beginner.
2. **ONBOARD-001 (P1)** — Add a short Week 0 platform-orientation
   module/panel (what Nexus is, what's required vs. optional, how XP/Role
   differ, how ticket grading + mentor review works, where to go if stuck).
3. **CUR-002 / NAV-004 (P1)** — Set `role_level` on the 3 live capstone
   templates so the existing "hide until unlocked" nav logic actually
   applies; stops day-one students from seeing graduation-level content.
4. **NAV-001 / NAV-003 (P1)** — Add first-login welcome copy and fix the
   "pick up where you left off" fallback text on Home; both are small copy/
   component changes bundled naturally with the Week 0 onboarding work.
5. **LESSON-001 (P1) — SUPERSEDED:** false premise, no lesson was missing
   (see `NEXUS_FINDINGS.csv` and `NEXUS_LESSON_REVIEW.md`). The real defect
   found in its place — a cosmetic-only Week 1 Learning Path lock — was
   fixed via migration `0030_week_gating_data_fixes.py` during the
   Pre-Week-0 Launch Readiness Sprint (2026-07-21).
6. **ADMIN-003 (P2)** — Clear the mentor's own dogfooding activity from the
   squad-activity feed (or confirm it's mentor-excluded from student view)
   before real students see it.

## During Weeks 1-4 (real but not launch-blocking)

7. **CUR-001 / ENGAGE-002 / LEARN-003 (P2)** — Give labs XP parity with
   tickets and/or a mentor-review gate.
8. **LAB-002 / TECH-004 (P2/P3)** — Decide whether to implement lightweight
   screenshot-content validation or simply drop `must_contain_text` from
   screenshot-type evidence definitions so the schema stops promising a
   check that doesn't run.
9. **LAB-001 / NAV-007 (P2)** — Resolve the Terminal Practice / Command
   Library / Networking Labs overlap (merge or clearly differentiate; wire
   up or remove the decorative terminal widget).
10. **QUIZ-001 (P2) — SUPERSEDED, not present:** live student-account testing
    (Pre-Week-0 Launch Readiness Sprint, 2026-07-21) confirmed unvalidated
    quizzes are not visible or attemptable by students at all — see
    `NEXUS_FINDINGS.csv` and the addendum in `NEXUS_QUIZ_REVIEW.md`. The
    remaining content-quality work (missing explanations, `needs_edit`
    status) is a legitimate post-launch improvement, not a launch blocker.
11. **NAV-005 (P2)** — Add a plain-language status gloss to the Tickets list
    view (the underlying feedback screen is already good — this is a small
    polish item, not a rebuild).
12. **NAV-006 / QUIZ-003 (P2/P3)** — Add a required/optional badge to quiz
    list items; spread Weeks 3/7's stacked optional quizzes more evenly.
13. **ACCESS-001 / ACCESS-002 (P2)** — Add a skip-to-content link and
    app-wide focus-visible styling.
14. **ENGAGE-003 (P2)** — Add a short in-app explanation of XP vs. Role
    (bundle with the Week 0 onboarding work).
15. **TICKET-004 / TECH-002 (P3)** — Return a proper 429 (not a wrapped 500)
    on rate-limit rejection.

## After the first cohort begins (informed by real usage)

16. **ADMIN-001 / ADMIN-002 / ADMIN-004 (P3)** — Add a stalled-student
    signal, surface failed-quiz detail directly, and consider routing a
    mentor digest through the existing Discord webhook — all most useful
    once there is real activity to summarize.
17. **ENGAGE-001 (P3)** — Revisit the leaderboard's framing once real
    engagement patterns among the 5-6 friends are observed.
18. **LESSON-003 / LEARN-001 / LEARN-002 / LAB-004 (P3)** — Add worked
    examples/labs/tickets for the program's thinnest-practiced hard topics
    (subnetting, GPO, AD, PowerShell) — best informed by watching where
    real students actually struggle.
19. **TICKET-005 (P3)** — Add the Outlook/M365 and ransomware-escalation
    tickets identified as coverage gaps.
20. **QUIZ-002 (P3)** — Run a scripted, full-104-quiz answer-bias/duplicate
    audit.
21. **ACCESS-003 / ACCESS-004 (P3)** — Add missing alt text and remaining
    input labels.
22. **TICKET-002 (P3)** — Decide whether ticket-resubmission history is
    worth storing for mentor context.

## Future work (explicitly deferred, includes automated VM)

23. **Automated Proxmox/Guacamole VM labs** — remains correctly disabled;
    no action recommended until a real start/connect/isolation/expiry/
    destroy smoke test passes against the configured infrastructure, per
    the existing go-live checklist.
24. **ACCESS-005** — a live browser/axe-core accessibility audit, once the
    cohort and/or platform scope grows beyond the current small, closely-
    mentored group.
25. **TECH-003** — clean up the dead `grade_now` field, or use it to support
    a genuine draft-save-without-grading flow.
26. **Bundle size** (978kB main chunk, from the Technical Review) — a
    code-splitting pass for admin routes, worthwhile but not urgent at
    current traffic levels.
27. **NAV-009** — the full nav consolidation from 9 to ~6 items is a larger
    UX project best sequenced after the smaller individual nav fixes above
    are already in place and observed with real students.
