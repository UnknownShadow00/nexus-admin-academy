# Phase 9 — Support Tickets vs Service Desk

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** Support Tickets = source + live API. Service Desk = admin panel (LIVE) + scenario
definition source. **Student-side Service Desk could NOT be exercised live** — it is gated behind
a global student feature flag that is OFF for normal students, and the plan prohibits changing
feature flags. Student-side findings below are **admin-panel + source based** and labeled as such.

## What each system teaches

**Support Tickets (48).** Open-ended incident handling: the student writes an **ITIL-structured
write-up** (`_build_itil_writeup`) and is **AI-graded** (`ticket_grader.grade_ticket_submission`)
on `structure (0.3) · technical (0.5) · communication (0.2)` → 1–10, with a hint-penalty ladder
(−5/−10/−20/−35%, floor 40%), optional screenshot evidence, and team-collaboration multipliers.
Server keeps `scoring_anchors/root_cause/model_answer` hidden. **Skill: diagnosis + written
communication/documentation.** Fallback answer-key grading exists when AI is unavailable.

**Service Desk Lab (5 scenarios).** Guided **deterministic simulation**: the student drives a
tool-based workflow (open ticket → inspect requester → **verify identity** → find/inspect account
→ perform the safe change → document → resolve), scored deterministically against a rubric.
Immutable published versions, append-only events, `hidden_facts` server-side, health-path
validation. **Skill: correct, safe, procedural execution.**

## Overlap / difference / conflict
- **Different skills, minimal overlap:** Tickets teach *writing/communication under open-ended
  diagnosis*; Service Desk teaches *following a correct, safe procedure with identity
  verification*. They are complementary, not redundant.
- **No data/grading/XP conflict:** separate models (`TicketSubmission` vs
  `ServiceDeskAttempt/Event/Grade`), separate grading (AI vs deterministic), separate admin
  surfaces (Ticket Review queue vs Service Desk admin: scenarios/health/assignments/replay/grades).
- **Naming confusion (the real risk):** for a beginner, "Support Tickets" and "Service Desk Lab"
  sound like the same thing, and both live in Practice Library. This is the Phase 3 IA issue.

## The 5 scenarios (source review; all "Health: Passing" live in admin)

| Scenario | Core task | Identity verify | Critical-failure gating | Modes |
|---|---|---|---|---|
| Locked User Account | Unlock after failed logins | ✅ (weighted 25 pts) | Unlock before verify / wrong account → auto-fail | Learning + Simulation |
| Password Reset | Safe simulated reset | ✅ | wrong account, etc. | Learning + Simulation |
| MFA Reset | Reset factor after phone swap | ✅ | wrong account | Learning + Simulation |
| BitLocker Recovery | Verify requester **and device**, scoped key | ✅ (+device) | wrong device/key exposure | Learning + Simulation |
| New Employee Onboarding | Create account, assign group/device | ✅ (request validation) | wrong group/account | Learning + Simulation |

Each scenario has: 3 learning objectives, `student_facts` vs server-side `hidden_facts`
(root cause, correct IDs, recovery key, **critical_failure_definitions**), 8–10 tracked state
fields (with a visible subset), 8–9 actions incl. `request_hint`, success conditions, a scoring
rubric (`passing_score` 80), pass/fail/critical feedback, and a deterministic `health_path`.

**Assessment:** beginner-appropriate, realistic (the 5 most common tier-1 tasks), technically
correct process, **identity verification enforced in all five**, safe/recoverable-vs-critical
failure handling built in (e.g., "unlocking before identity verification" = critical fail).
This is a **strong Phase 1A foundation.**

## What could NOT be validated (flag-gated; labeled honestly)
Not exercised live from the student side: Learning-Mode step guidance UX, Simulation-Mode
difficulty, contextual browser tools behavior, Knowledge Base support, resolution-documentation
UX, on-screen scoring/feedback, and **mobile usability**. Verified only that admin reports all 5
as published + health-passing and that definitions are sound. **Before the temporary student
review of Service Desk, someone must enable the student flag in a controlled way and walk each
scenario end-to-end on desktop and mobile** — I did not do this (flag change prohibited here).

## Should both remain?
**Yes.** Keep Support Tickets (communication/writing) and Service Desk (procedure/safety) — they
train different competencies. Longer term, some *procedural* tickets (e.g., a scripted
password-reset ticket) are better expressed as deterministic Service Desk scenarios; keep genuinely
open-ended diagnosis as Support Tickets. **Authoritative split:** Service Desk = procedural,
safety-critical, deterministic tasks; Support Tickets = open-ended diagnosis + written comms.

## Recommended next Service Desk phase (do NOT implement now)
- **Must-fix in 1A before wider student use:**
  1. The student-side `/service-desk` **unavailable** state fires 404 console errors — make the
     availability probe return 200 `{available:false}` (Phase 3/13).
  2. Complete an **end-to-end student walkthrough** (desktop + mobile) of all 5 scenarios in both
     modes under a controlled flag enablement — this validation is currently missing.
  3. Clarify **Support Tickets vs Service Desk** naming/positioning in the IA (Phase 3).
- **Reasonable Phase 1B:** a couple more high-frequency scenarios (shared-drive access request,
  printer/email profile, VPN cert); richer per-step coaching in Learning Mode; a student-facing
  attempt history; surface Service Desk results in Progress.
- **Long-term (state prerequisite + value):** integrate Service Desk outcomes into My Training
  progression; instructor scenario authoring UI; analytics on common failure steps.
- **Not needed for Nexus:** real AD/Guacamole/VM/phone/voicemail integration, org-scale ticketing.

## Is Service Desk ready for its temporary student review?
**Foundation: yes. Student-facing sign-off: not yet** — the end-to-end flag-on walkthrough
(desktop + mobile, both modes, all 5 scenarios) has not been performed. Do that before exposing
it to students. **Phase 1B should not start until that walkthrough + the must-fix items are done.**

## Priorities
- P1: `/service-desk` unavailable-state 404 noise; missing end-to-end student walkthrough.
- P2: Tickets-vs-Service-Desk naming/IA; surface Service Desk in Progress.
- Future: 1B scenarios; My Training integration.
