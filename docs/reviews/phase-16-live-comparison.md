# Phase 16 — Live Production Comparison & Cleanup

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** LIVE via temp accounts only, against `https://nexus.builtfromzero.fyi/`.

## Routes & navigation match the baseline source
- **All expected student routes exist and return 200** (12 destinations swept in Phase 3) and the
  primary nav renders exactly the 4 intended items (Home, My Training, Practice Library, Progress),
  matching `App.jsx` at `15a9410`.
- **All expected admin routes exist and return 200** (12 destinations swept in Phase 4) with the 5
  intended workflow groups — matching the source nav config.
- **Retired routes redirect** as coded: `/learning-path → /training`, `/study-tracker →
  /training/content`, `/admin/review → /admin/ticket-review`.
- **No stale/unexpected routes** and **no production-only errors** surfaced beyond the known,
  harmless Cloudflare beacon CSP warning.

## Feature flags behave as designed
- **Service Desk Lab** is correctly **gated off for a normal student** (route shows "unavailable",
  hidden from nav) while **enabled and healthy in the admin panel** (5 published scenarios, health
  passing). The per-student beta-enrollment + global-flag model behaves as documented. *(I did not
  toggle any flag — student-side SD remained untested per the restriction; see Phase 9.)*

## Isolation verified (live)
- Student → `/api/admin/*` and unauthenticated → `/api/admin/*` both return **403**.
- Cross-student reads (`/api/students/1…`, `?student_id=1` on quizzes/tickets) return **404/403**;
  IDOR on quiz review/submit returns **403**. Student and admin experiences are correctly isolated.

## Deployment reality vs. documentation (finding to reconcile)
Evidence indicates production runs **behind Cloudflare with the backend on Render**: the login page
states "first load can take up to 30 seconds while the backend wakes on Render," non-browser
requests receive Cloudflare `403 error code 1010`, and there is an observable cold-start. However,
`docs/DEPLOYMENT.md` and `CLAUDE.md` describe an **active self-hosted systemd + nginx + SQLite**
deployment. **These diverge.** This matters operationally: the documented SQLite backup/restore and
systemd restart procedures assume direct file/host access that a Render deployment may not provide.
*Action for owner:* reconcile the docs with the actual hosting (or document both, clearly labeling
which is live), and confirm the backup/restore runbook works against the real environment.

## Temporary changes made under review accounts — and their cleanup

**Created (production writes):**
- One throwaway student: `zz_review_tmp_fb0dd9` (id **8**), via `POST /api/admin/students`.
- Two quiz attempts by that student on quiz 42 (Week 0 Ticketing Systems Quiz) — from the Phase 7
  submit/retake test. Plus the incidental login-streak/activity rows that a login creates.

**Removed / restored (verified):**
- `DELETE /api/admin/students/8` → `{deleted:true}` (HTTP 200).
- Roster before: ids `[1,2,3,4,5,6,7,8]`; after: `[1,2,3,4,5,6,7]` — **the 7 real accounts remain
  untouched; only the temp student was removed.**
- Deleted student's dependent rows (quiz attempts, streak) cascade-deleted via the FKs (all FKs
  carry ON DELETE, Phase 11). Confirmed by **deleted-student login now returning 401**.
- Admin session logged out (`/api/admin/session/logout` → 200).
- Scratchpad credential files scrubbed (`review_student.json`, saved session states deleted).

**No real students, real curriculum, or production content were modified.** No feature flags were
toggled. No deploy, merge, push, migration, or production seed was run.

## Verdict
The live production app **corresponds to the reviewed baseline** in routes, navigation, gating, and
isolation, with no stale deployment or production-only defects. The one item to reconcile is the
**docs-vs-hosting** discrepancy (self-host docs vs. Cloudflare/Render reality). All temporary review
artifacts have been cleaned up and verified removed.

## Priorities
- P2: reconcile deployment docs with actual hosting; verify backup/restore against the real env.
- (Cross-ref) P1: `/service-desk` unavailable-state 404 noise; student-side SD walkthrough still owed.
