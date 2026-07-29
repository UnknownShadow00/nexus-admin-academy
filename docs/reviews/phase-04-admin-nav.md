# Phase 4 — Administrator Navigation & Workflow

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** LIVE, current admin account. Swept all 12 admin destinations at 1440×1000.
All returned HTTP 200 with **zero console errors**. (Real student PII seen in the roster is
deliberately kept out of this report.)

## Admin nav (as rendered) — matches intended IA
Dashboard · Learning Content ▾ (Modules/Lessons & Quizzes, Weekly Training, Study Curriculum,
Job Relevance Tags, ExamCompass Import) · Students · Assessments & Labs ▾ (Ticket Review,
Service Desk Lab, Labs & VM Assignments, Capstones) · System ▾ (AI Usage & Costs). Global
"Switch to Student View" and "Admin Sign Out" always present.

## Per-destination findings

| Destination | Purpose | State | Notes |
|---|---|---|---|
| Dashboard `/admin` | Ops home | ✅ | Submissions/Avg score/Completion tiles + **content-creation widgets** (Generate Quiz, Create Ticket, Add Resource, Bulk Create Tickets). Content-ops focused, **not** student-monitoring focused. |
| Students `/admin/students` | Roster | ⚠ | Flat table: Name/Email/Username/Notes/Mentor/XP/Quiz/Avg Quiz/Tickets/Avg Ticket + Edit/Delete + New Student. **No per-week progress, no current-week, no struggling/overdue signal, no drill-down.** |
| Modules/Lessons & Quizzes `/admin/modules` | Module Manager | ✅ | Rich editor (7.6k chars rendered). |
| Weekly Training `/admin/training` | Curriculum weeks | ✅✅ | "References valid" badge; "137/137 videos mapped (**5 exact**, 92 topic-group, 40 week fallback)"; per-week activity counts (W0:6, W1:10, W2:25, W3:26, W4:27, W5:18…); reorder + create. |
| Study Curriculum `/admin/curriculum` | Curriculum Editor | ✅ | Very large page (24k chars) — powerful but heavy. |
| Job Relevance Tags `/admin/curriculum-tags` | Tag mgmt | ✅ | Job-relevance tagging surface. |
| ExamCompass Import `/admin/bookmarklet` | Quiz import | ✅ | Bookmarklet workflow. |
| Ticket Review `/admin/ticket-review` | Grade queue | ✅ | Master-detail; clean "No graded submissions" empty state. |
| Labs & VM Assignments `/admin/labs` | Lab templates | ✅ | "Lab Templates" (note: **VM Assignments** references the deferred VM feature). |
| Capstones `/admin/capstones` | Capstone templates | ✅ | Template mgmt. |
| AI Usage & Costs `/admin/ai-costs` | AI cost dash | ✅ | Present though AI is "deferred" — tracks usage/budget. |

## Can an admin answer the plan's questions?

| Question | Answer | Evidence |
|---|---|---|
| What is each student supposed to do this week? | **Partially** — curriculum is visible in Weekly Training, but **not per-student**. |
| What has each student completed? | **Aggregate only** — Students table shows totals (XP, quiz count, tickets), not per-week/per-activity. |
| Where is each student struggling? | **No** — no per-topic scores, failed-attempt view, or drill-down. |
| What is overdue? | **No** — no due dates / overdue concept exists. |
| Which content is unpublished or broken? | **Yes** — Weekly Training "References valid", Curriculum Editor, published/draft states. |
| Which videos lack quizzes? | **Partially** — 137/137 mapped, but only 5 exact mappings (rest topic-group/fallback). |
| Which activities have no learning objective? | **Not surfaced** as a report. |
| Which scenarios are failing health checks? | **Yes** — Service Desk per-scenario Health (all Passing). |
| Which students have access to private-beta features? | **Yes** — Service Desk enrollment/Assignments. |
| Which actions were performed by administrators? | **No admin-audit view in the UI** (audit logging assessed in Phase 10). |

## Duplication / overlap (admin content editing)
Three overlapping content-editing surfaces: **Module Manager** (`/admin/modules`), **Curriculum
Editor** (`/admin/curriculum`, 24k chars), and **Weekly Training** (`/admin/training`). A small
owner-operated team editing content across three tools risks confusion and inconsistent edits.
Candidate consolidation → Phase 12.

## Dangerous-action protection
- Student **Delete** is a plain button in the roster with no visible confirm in the row (verify
  guard in Phase 10). Bulk ticket creation / "Publish All Tickets" are one-click.
- No roles/permissions UI — a **single shared admin** identity; all admin actions are
  indistinguishable by actor (relevant to audit-log finding above).

## Recommended simpler admin structure (for a 5-student program)
Keep the five workflow groups, but **rebalance toward student monitoring**:
1. **Dashboard** — add a compact cohort panel: each student's current week, % complete, last
   activity, and a "needs attention" flag (stalled / failing). This is the single highest-value
   admin improvement for five students.
2. **Students** — add a per-student drill-down (week-by-week completion, recent submissions,
   quiz scores by topic). Replace/augment the flat aggregate table.
3. **Learning Content** — consolidate the three overlapping editors (Modules / Curriculum /
   Weekly Training) or clearly delineate their roles; keep Job Relevance Tags + ExamCompass under it.
4. **Assessments & Labs** — keep as-is (Ticket Review, Service Desk, Labs, Capstones). Rename
   "Labs & VM Assignments" until VM ships.
5. **System** — add an **admin audit-log** view; keep AI Usage & Costs.

Avoid enterprise features (org hierarchy, SSO, RBAC roles) — unnecessary for five students.

## Strengths
Clean workflow IA; excellent content-integrity tooling (References valid, video mapping,
scenario health); solid Service Desk admin; zero console errors across all admin pages.

## Issues to carry forward
- **P1/UX (admin):** no per-student monitoring (current week / completion / struggling / overdue).
- P2: three overlapping content editors.
- P2/security: no admin audit-log view; single shared admin (→ Phase 10).
- Note: admin-created students auto-complete all methodology progress (Phase 0 finding) → verify effect in Phase 7.
