# Mentor / Admin Panel Review

Date: 2026-07-21. Phase 14. Evidence: a full live admin-session walkthrough
(11 admin API surfaces) against production using the real admin credential,
plus live testing of the review/reject/verify workflow performed during
Phase 9's ticket testing (this session actually rejected and then verified
a real submission end to end, not merely read the endpoints).

---

## 1. Can one mentor triage the whole cohort in under a minute?

**Currently yes, trivially — but only because there is nothing to triage
yet.** Live data: all 6 real students at 0 XP / 0 quizzes / 0 tickets;
`admin_review_queue` returns 0 rows; `admin_submissions` shows exactly 1 row
system-wide (the mentor's own dogfooding ticket). This is expected pre-
launch state, not a finding about the admin UI's real capacity. The
meaningful question is whether the *structure* supports fast triage once
real activity exists, which the next sections address.

## 2. Structural triage capability (evaluated from the API/data shape)

- **Overdue work visibility:** `admin_students_overview` returns per-student
  `quiz_done/quiz_total`, `ticket_done/ticket_total`, and averages — this
  supports "who's behind" at a glance, but it does not appear to expose a
  time-based "hasn't logged in for N days" or "started but stalled" signal
  directly in this payload (the `SquadActivity` feed is the closer fit for
  that, examined below). **Finding ADMIN-001 (P3):** a stalled-student flag
  (e.g. "no activity in 7+ days") would materially speed up triage for one
  mentor watching 6 people.
- **Failed-quiz visibility:** not directly exposed in the students-overview
  payload (only aggregate `avg_quiz`); a mentor would need to open the
  editorial/review surfaces or per-student detail to see a specific failed
  attempt. **Finding ADMIN-002 (P3).**
- **Pending-ticket visibility:** `admin_review_queue` and `admin_
  submissions` both exist and, per this session's live test, correctly
  reflect a submission's real-time status (`pending` → `needs_revision` →
  `passed`, confirmed by directly driving that transition this session).
  This surface works as designed.
- **Buried actions / duplicate admin pages:** 11 admin nav sections is a
  reasonable number for the described scope (student mgmt, quiz editor,
  curriculum editor, lab/capstone template CRUD, AI cost dashboard, ticket
  review, VM assignments, ops summary, squad activity) — no clear duplicate
  section was identified in this pass, though `admin_vm_assignments`
  currently shows a whole section that is permanently empty pre-launch
  (0 rows, automated VM disabled) — not wrong, but worth mentally filtering
  out as "not yet relevant."

## 3. Confirmed working end-to-end (this session performed the actual
   actions, not just a read)

- **Reject → needs_revision:** `PUT /api/admin/submissions/{id}/reject-
  proof` with a comment correctly set status to `needs_revision`, which the
  student's Tickets list and TicketFeedback screen both reflected
  immediately (cross-referenced in the Ticket Review).
- **Verify → XP granted:** `PUT /api/admin/submissions/{id}/verify-proof`
  correctly set status to `passed` and returned `xp_awarded_each: 10`,
  matching the stored `ai_score × 10` formula.
- **AI cost dashboard:** live data shows total AI spend of **$0.043** across
  34 ticket-grading calls to date — the local Ollama deployment keeps real
  cost negligible, and the dashboard correctly breaks down cost by feature
  and lists recent calls with token counts and timestamps. This is a
  well-built, currently-low-risk surface.
- **Promotion gates admin view:** the full 29-row gate configuration is
  readable via `admin_promotion_gates`, matching the curriculum-dump gate
  data exactly — no drift between the admin-editable config and what the
  curriculum documents.

## 4. A finding specific to mentor workload: the mentor's own account has
   live activity mixed into the shared feed

**Finding ADMIN-003 (P2).** `admin_squad_activity` (the feed presumably
visible to students, per its name) shows 2 `lab_started` entries from the
**Mentor's own account**, dated 2026-07-18 — almost certainly the mentor's
own dogfooding/testing of the lab flow before real students start. This is
not a bug, but if the squad-activity feed is student-visible, a student
seeing "Mentor started a lab" in their shared activity feed on day one, with
no context, is a small but real confusion risk given the review brief's
own framing that no one has started yet. **Recommend the mentor either
clear this test activity or confirm the squad feed correctly excludes
mentor accounts from student view before Week 0 begins.**

## 5. Manual score correction and AI-grading review

`PUT /api/admin/submissions/{id}/override` (manual score override) and `PUT
/api/admin/review/{id}` (manual review) both exist as separate endpoints
from verify-proof/reject-proof — giving the mentor three related but
distinct actions (override score, manual review, verify/reject). This is
reasonable flexibility but was not live-tested in this pass beyond
confirming the endpoints exist and are correctly gated behind
`verify_admin` (all `/api/admin/*` routes share one dependency, confirmed in
`admin_content.py`'s router definition). **Not a finding — noted for
completeness.**

## 6. Reporting and unnecessary mentor work

No dedicated weekly-digest or "what changed since I last checked" report
endpoint was found among the reviewed admin surfaces — a mentor currently
has to actively check the review queue, submissions list, and squad
activity separately rather than receiving one consolidated view. Given the
existing Discord webhook integration (`discord_service.py`, confirmed in the
Product Map's service inventory) already supports passive notifications,
**Finding ADMIN-004 (P3):** consider routing a daily/weekly digest (new
submissions pending review, stalled students, failed required quizzes) to
the mentor's Discord rather than requiring active dashboard-checking — this
would meaningfully reduce mentor workload for a single person managing 6
students alongside their own job.

## 7. Admin UI safety

All destructive-sounding admin actions reviewed (reject-proof, override,
bulk-generate tickets) are scoped to a single submission/ticket by ID in
the API design, reducing blast radius of an accidental click; no bulk
"delete all" or similarly broad destructive action was found in the
reviewed admin router set. This is a reasonable safety posture for a
low-traffic, single-mentor admin panel.

## 8. Summary findings

- **ADMIN-001 (P3):** No stalled-student ("no activity in N days") signal
  in the students-overview data.
- **ADMIN-002 (P3):** Failed-quiz detail not surfaced directly in the
  overview payload — requires drilling into per-student detail.
- **ADMIN-003 (P2):** Mentor's own dogfooding activity is currently mixed
  into the (likely student-visible) squad-activity feed — clear or verify
  exclusion before Week 0.
- **ADMIN-004 (P3):** No consolidated daily/weekly mentor digest; consider
  routing one through the existing Discord webhook integration.
- **Positive finding:** the core review/reject/verify workflow, the AI cost
  dashboard, and the promotion-gate config surface all work correctly and
  match their documented behavior exactly, confirmed via live testing this
  session rather than static reading alone.
