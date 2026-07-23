# Phase 0 — Preconditions

**Date:** 2026-07-23
**Reviewer:** Claude Code (automated review)
**Review baseline commit:** `15a94103d5b951913875cc5a054fda7b70bede32` (branch `main`)

## Checklist results

| # | Precondition | Status | Evidence |
|---|---|---|---|
| 1 | Browser automation available + reaches production | ✅ PASS | Playwright 1.61.1 (frontend/node_modules), Chromium 1228 installed. Headless launch → `https://nexus.builtfromzero.fyi/` returned HTTP 200, redirected to `/login`, rendered real login page ("Nexus Admin Academy"). Screenshot captured in scratchpad. |
| 2 | Repo + git history read access | ✅ PASS | `git log`/`git rev-parse` working. HEAD = `15a9410`. |
| 3 | Temp accounts created | ✅ PASS (resolved) | User authorized using the current admin account (local `backend/.env`, in-memory only). Admin login via Playwright → `/admin`, `admin_session` set. Self-created throwaway **student** (id=8) via `POST /api/admin/students`; student login OK, fresh Week 0 home renders. |
| 4 | `docs/reviews/` exists | ✅ PASS | Created (was absent). Not gitignored. |
| 5 | Readiness reported before Phase 1 | ✅ (this file + chat) | |

## Tooling detail

- **Browser automation:** No Playwright MCP server is configured, but Playwright
  is drivable via Node script using `frontend/node_modules/playwright-core` +
  installed Chromium (`PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`). A reusable
  harness lives in the session scratchpad. End-to-end verified (launch → navigate →
  screenshot at 1440×1000). This is **genuine browser rendering**, not source-only.
- **Production:** HTTP 200. Login page shows student login + a separate "Admin Login".
  Login copy reads: *"First load can take up to 30 seconds while the backend wakes on
  Render."* — a possible discrepancy vs. the documented self-hosted systemd/nginx/SQLite
  deployment. Flagged for Phase 1/16.

## Account situation (the one blocker)

- **No student self-registration.** Frontend route table has no `/register` or
  `/signup`; login page offers no sign-up. Students are created only via the
  admin-only endpoint `admin_students.create_student` (`POST /api/admin/students`).
- **Admin auth** = single shared admin **username + password** sourced from env
  (`ADMIN_PASSWORD` / `ADMIN_SECRET_KEY`, `admin_auth.py`). No self-service admin
  bootstrap exists on production.
- **Consequence:** I can self-create the throwaway *student* per the plan — but only
  after I have *admin* access. Obtaining admin access on production requires the
  production admin credentials, which I do not have and cannot derive.

Per the plan's "Review inputs" section: when self-creation isn't possible due to no
bootstrap path, the reviewer must ask the user to provide temp credentials
out-of-band, and must never paste them into any committed/shared file, screenshot,
or transcript. No credentials will be written into any report.

## Readiness verdict

**Tooling: GREEN.** Browser automation, repo access, and report directory are all ready.

**Live authenticated review: GREEN (resolved).** User authorized use of the current
admin account. Admin credentials were read from local `backend/.env` in-memory only —
never printed, committed, or written to any report. Both roles verified against
production:

- **Admin:** current admin account. Login → `/admin`, dashboard renders with documented
  nav (Dashboard, Learning Content, Students, Assessments & Labs, System). Session state
  saved to scratchpad for reuse.
- **Student (throwaway, self-created):** username `zz_review_tmp_fb0dd9`, **student id 8**,
  fresh Week 0 state (0/5 required activities, 0 XP). Login OK; home renders. Session
  state saved to scratchpad.

### Cleanup obligation (Phase 16)
- Delete throwaway student **id 8** (`zz_review_tmp_fb0dd9`) via admin at end of review.
- Revoke admin session (logout). Scratchpad credential file is session-local, never committed.

### Notable observations captured during Phase 0 (to investigate in later phases)
- Production is fronted by **Cloudflare** (non-browser requests get `403 error code 1010`);
  login copy references **Render** as the backend host. Both differ from the documented
  self-hosted systemd/nginx/SQLite picture — reconcile in Phase 1/16.
- `admin_students.create_student` marks **all** `StudentMethodologyProgress` as
  `completed=True, practice_passed=True, quiz_score=100` for a new student. Admin-created
  students therefore differ from onboarding-seeded students — flag for Phase 4/7.
- Only console error on authenticated pages so far is the **Cloudflare beacon CSP** warning
  (plan already classifies this as known-harmless).

Everything is ready. Phases can proceed with genuine live navigation, not source-only.
