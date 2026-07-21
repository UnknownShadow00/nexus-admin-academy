# Ticket System Review

Date: 2026-07-21. Phase 9. Evidence: **live testing** of tickets 1 and 2
against production using the disposable `nexus-review-student` account and
the real admin session, plus a full read of the 48-ticket catalog (titles,
sample checkpoints/evidence/scoring-anchor JSON for tickets 1-2), plus direct
reads of `backend/app/routers/tickets.py`, `admin_tickets.py`,
`a_plus_access.py`, `rate_limiter.py`, and `frontend/src/pages/
TicketFeedback.jsx`. The admin-only `a_plus_unlock_threshold_pct` setting was
temporarily lowered from its live production value (40%) to 0% to make live
ticket testing possible, and **was restored to 40% immediately after
testing** — confirmed via a final `GET /api/admin/settings/a-plus-unlock`
read showing `40`. No real student data was touched; all test submissions
were made and reviewed on the disposable account only.

---

## 1. Critical finding: the A+ unlock gate silently blocks Week 1's tickets

**Finding TICKET-001 (P0).** Every ticket-, lab-, capstone-, and CLI-lab-
related endpoint (`tickets.py`, `labs.py`, `capstones.py`, `cli_labs.py`,
`evidence.py` — confirmed by grep across all five routers) calls
`require_a_plus_unlocked()`, which blocks the action with a 403 until the
student has watched **40% of the 137 active CompTIA A+-tagged curriculum
videos** — **55 videos**, averaging roughly **9.3 hours of video** at their
recorded durations (summed directly from the live `curriculum_videos`
table). This was reproduced live: a brand-new disposable student at 0% got
`403 {"error": "Complete 40% of A+ Study Tracker to unlock hands-on work —
you're at 0%."}` on a first attempt to submit Ticket 1.

This directly contradicts the curriculum's own design: **Week 1's content
(read in full for the Lesson/24-Week reviews) assigns two tickets** ("User
cannot browse the internet" and "User account locked out") **as Week 1
work**, and the promotion-gate for Support Technician I requires 4
difficulty-1 and 2 difficulty-2 verified tickets by the time Week 4's gate
quiz is reached. As shipped today, **no student can touch a single ticket,
lab, or capstone action until they have independently completed roughly 9
hours of unrelated video-watching on a different, confusingly-named part of
the platform (Study Tracker — see Navigation Review)** — a prerequisite that
is not mentioned anywhere in Week 0, Week 1, the Home page, or the nav.

This is not a hypothetical: it is the literal state of production right now
(confirmed threshold = 40% both before and after this review's testing
window). Since the review brief states the five/six real students have not
yet started, **this gate has not yet blocked anyone in practice, but it will
be the very first wall the first real student hits**, almost immediately,
with no explanation of what "A+ Study Tracker" means or how to make progress
against it. Recommended before Week 0 begins: either (a) lower the threshold
substantially (e.g. 0-10%) for the initial cohort and raise it later once
students understand the platform, or (b) keep 40% but add an explicit,
visible explanation of the gate on Home/Week 0/the Tickets page *before* a
student ever hits the 403. Given the brief's own "before Week 0" framing,
this is the review's single highest-priority production-behavior fix.

## 2. Live grading test results

Five submissions were made to two tickets with deliberately varied quality,
observing the real AI grader (`deepseek-r1:32b` via the local Ollama
service) end to end:

| Ticket | Submission style | AI score /10 | Elapsed | Grading verdict |
|---|---|---|---|---|
| 1 (DNS) | Strong — correct diagnosis, safe fix, explicit verification, plain-language user explanation | **8** | 23.4s | Accurately rewarded a complete, safe, well-communicated answer |
| 1 (DNS) | Weak — vague, no real diagnosis ("probably network issue"), no verification | **1** | 9.4s | Correctly penalized vagueness and missing verification |
| 1 (DNS) | Unsafe — disables firewall/antivirus to "rule it out," no re-test before closing | **1** | 10.7s | Correctly penalized the unsafe, unverified "fix" |
| 2 (Lockout) | Escalation-correct — explicit identity verification via callback, re-tested login live, checked for stale-credential device | **7** | 14.5s | Correctly rewarded the identity-verification safety rail the Week 7/14 lessons teach |
| 2 (Lockout) | Incomplete — one-line answers, no verification, "n/a" | **2** | 10.0s | Correctly penalized incompleteness |

**Verdict: the AI grader discriminates real quality differences correctly**
across this small but deliberately varied sample — strong answers score
high, vague/unsafe/incomplete answers score low, and the unsafe answer was
not rewarded despite superficially "resolving" the ticket. This is a
meaningfully positive finding for grading trustworthiness, consistent with
the prior security-review session's 5/5 calibration pass. **Observed live.**

## 3. Revision and mentor-review flow — tested end to end

Using the admin session: `PUT /api/admin/submissions/{id}/reject-proof`
correctly transitioned the DNS-ticket submission to `needs_revision`
(confirmed via response body and a subsequent student-facing `GET
/api/tickets` list showing `"status": "needs_revision"` on ticket 1).
`PUT /api/admin/submissions/{id}/verify-proof` correctly transitioned a
submission to `passed` and granted the stored XP (`xp_awarded_each: 10`,
matching `ai_score(1) × 10`).

**Frontend feedback page (`TicketFeedback.jsx`, read in full) is genuinely
good** — this corrects and narrows down the concern raised more broadly in
the Navigation Review (NAV-005): the per-submission feedback screen clearly
shows the AI score, an explicit **"Awaiting instructor verification. XP and
mastery update after proof is verified."** warning banner whenever
`xp_granted` is false, strengths/weaknesses lists, the mentor's own comment
when present, and a **"Resubmit"** button that only appears when status is
`needs_revision`. **This is one of the best-designed screens in the student
experience.** The residual gap is upstream of this screen: the bare
`status` string shown on the Tickets *list* (`pending`, `needs_revision`,
`passed`, `not_started`) is not glossed anywhere on that list view itself —
a student has to open the submission's feedback page to get the plain-
language explanation. Recommend a one-line status gloss directly on the
Tickets list (e.g. a small "waiting on your mentor" pill next to `pending`).
This is a much smaller, P2-level residual finding, not the P1 originally
suspected before this live test.

## 4. Resubmission model (confirmed in code)

`TicketSubmission` is one row per (student, ticket) pair, not one row per
attempt — resubmitting overwrites the writeup/scores/feedback of the
existing row unless its status is already `passed` (which is explicitly
blocked with a 400, "already been passed. Contact instructor for review").
This is the correct design for a ticket workflow (a ticket is worked to
resolution, not re-attempted for score-shopping like a quiz) but has one
side effect worth naming: **a mentor reviewing a resubmitted ticket cannot
see what the student's previous (rejected) attempt said** — only the latest
writeup persists. For a mentor trying to judge whether feedback was actually
incorporated, this is a minor loss of context. **Finding TICKET-002 (P3).**

## 5. Rate limits and the resubmission cost of AI grading

`grade_now` is accepted in the submit payload but **is not actually read
anywhere in `tickets.py`** — AI grading always runs synchronously on every
submit regardless of that flag (**Finding TICKET-003, P4, dead/unused
field**). More importantly: `ticket_grading` is rate-limited to **3 calls
per minute and 8 calls per day, per student** (confirmed in
`rate_limiter.py`). A student working through a normal week (2-4 tickets,
plus any resubmission after mentor feedback) will typically stay well under
8/day, but a student doing a Multi-Ticket Simulation (3, 6, or "the
infrastructure shift" scale) plus a same-day resubmission could plausibly
hit the daily cap. When the cap is hit, the failure mode observed live is a
**generic `500 {"error": "AI grading failed: 429: Rate limit: Max 3 calls
per minute"}`** — this is an internal rate-limit message leaking through as
a raw 500, not a friendly "you've used today's grading attempts, try again
tomorrow" message. **Finding TICKET-004 (P3).**

## 6. Ticket coverage against the requested real-world topic list

Checked against: password reset, lockout, Outlook, M365, printers, shared
drives, permissions, VPN, WiFi, DNS, DHCP, slow PCs, malware, ransomware
escalation, Linux services, backups, Azure, difficult users, professional
comms.

**Present and strong:** lockout (×3, including a repeat-lockout ticket),
printers (×2), shared-drive/permissions (×3, including a deliberately
sensitive "salary review folder" access trap), VPN (DNS-over-tunnel
ticket), WiFi, DNS (×2), DHCP (×2), slow PCs, malware/Defender, phishing
(the "Payroll update" credentials-entered scenario), Linux services (×4:
permission denied, SSH lockout, wiki down, cron job), backups (restore
ticket), Azure (×2: RDP-unreachable VM, expired SAS link), professional
comms (explicitly graded via the `communication` anchor on every ticket, plus
dedicated "write the email" lesson exercises in Week 5).

**Missing or only lesson-level, not ticket-level:** a dedicated **Outlook/
M365-branded** ticket (the closest is Week 4's generic "Email client cannot
send mail — SMTP authentication error," which is protocol-level, not an
M365/Outlook-specific scenario a real desk sees constantly — mailbox size
limits, shared mailbox permissions, Outlook profile corruption); an explicit
**ransomware-escalation** ticket (the malware/phishing tickets stop at
"contain and escalate," matching the curriculum's own stated scope rail, but
a ransomware-specific scenario — encrypted-files-discovered, immediate
isolation, and the specific communication challenge of that incident type —
does not appear as its own ticket); a **"difficult user"** ticket graded
specifically on de-escalation (Week 5's lesson has three ungraded "write the
email" practice prompts covering this exact skill, but no *ticket* exists
that scores a genuinely hostile/demanding user interaction as its own
scenario).

**Finding TICKET-005 (P3).** Recommend adding one Outlook/M365-specific
ticket and one explicit ransomware-discovery escalation ticket — both fit
naturally into the existing Week 4/Week 8 slots and would close the two most
concrete gaps against the requested coverage list. A dedicated
"difficult user" ticket is a nice-to-have (P4) given the skill is already
practiced, just not ticket-graded.

## 7. Summary of Phase 9 findings

- **TICKET-001 (P0):** A+ Study Tracker 40% unlock gate silently blocks all
  ticket/lab/capstone/CLI-lab work platform-wide, contradicting Week 1's
  designed ticket assignments. Fix before Week 0 begins.
- **TICKET-002 (P3):** Ticket resubmission overwrites prior writeup/feedback
  with no history retained for mentor comparison.
- **TICKET-003 (P4):** `grade_now` request field is accepted but unused —
  dead code, low risk, worth cleaning up.
- **TICKET-004 (P3):** Rate-limit rejections surface as raw internal 500
  messages instead of a friendly, actionable notice.
- **TICKET-005 (P3):** Add an Outlook/M365-specific ticket and a ransomware-
  escalation ticket to close the two clearest gaps in real-world coverage.
- **Positive finding, not a defect:** the AI grader itself, the mentor
  verify/reject workflow, and the `TicketFeedback.jsx` screen are all
  functioning well and are the strongest-tested part of the student
  experience in this review.
