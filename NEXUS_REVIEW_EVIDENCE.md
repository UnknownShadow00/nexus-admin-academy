# Nexus — Review Evidence Log

**Date:** 2026-07-23 · Baseline `15a94103d5b951913875cc5a054fda7b70bede32` (`15a9410`, `main`).
No secrets/credentials appear in this file.

## Tooling & environment
- **Browser automation:** Playwright 1.61.1 + Chromium 1228 (`~/.cache/ms-playwright`), driven via
  Node scripts using `frontend/node_modules/playwright-core`. No Playwright MCP server; scripting
  achieved the same. **Verified end-to-end** (launch → navigate → screenshot) against production.
- **Production target:** `https://nexus.builtfromzero.fyi/` (HTTP 200; behind Cloudflare —
  non-browser requests get `403 error code 1010`, so all live checks used real Chromium).
- **Backend local:** `backend/.venv` (python3.11); seeded `nexus.db` mirrors production seeds.

## Commands run (representative)
- `git rev-parse HEAD`, `git status`, `git log` — baseline.
- `backend/.venv/bin/python -m pytest -q` → **238 passed (~45s)**.
- `pytest tests/test_security_hardening.py test_security_part9.py test_auth.py test_auth_jwt.py
  test_admin_session.py -q` → **45 passed**.
- `backend/.venv/bin/alembic heads` / `current` → `0035_service_desk_browser_mvp`.
- `python -m compileall app` → OK.
- SQLite read-only: `PRAGMA integrity_check` = ok; `foreign_key_check` = 0; table/FK/index census
  (55/55/121); lesson summary-length + outcomes census.
- `frontend`: `npm run build` (entry 1006 kB / 282 kB gzip; admin routes code-split);
  `npm audit --audit-level=high` → **0 vulnerabilities**.
- Live API pulls: `/api/admin/training/weeks` + `/validation` (25 weeks / 296 activities /
  137 mapped), practice inventories, quiz flow, IDOR probes, admin-guard probes, a11y DOM audit,
  perf request count, health check.

## Browser sizes used
- Desktop **1440×1000**, Mobile **375×812** (per plan). Week-page capture used 1440×1400 for full-page.

## Routes inspected (live, authenticated with temp accounts)
- **Student (all HTTP 200):** `/`, `/training`, `/training/content`, `/training/week/0`, `/progress`,
  `/quizzes`, `/tickets`, `/labs`, `/cli-labs`, `/cli-labs/dev-sw-act-01`, `/capstones`, `/commands`,
  `/terminal`, `/service-desk` (gated "unavailable"), `/lessons/{id}` (gated 403 for locked).
- **Admin (all HTTP 200, 0 console errors):** `/admin`, `/admin/students`, `/admin/modules`,
  `/admin/training`, `/admin/curriculum`, `/admin/curriculum-tags`, `/admin/bookmarklet`,
  `/admin/ticket-review`, `/admin/labs`, `/admin/capstones`, `/admin/ai-costs`.
- **Redirects verified:** `/learning-path→/training`, `/study-tracker→/training/content`,
  `/admin/review→/admin/ticket-review`.

## Security probes (live results)
- Pre-submit quiz answers exposed: **no**.
- IDOR quiz review `/review/1`: **403**; quiz submit `student_id:1`: **403**.
- Cross-student `/api/students/1[/progress]`: **404**; `?student_id=1` on quizzes/tickets: **403**.
- Student & unauth → `/api/admin/*`: **403**. Unauth `/auth/me`: **401** (expected).
- Live headers present: CSP (strict), HSTS (2y), `X-Content-Type-Options: nosniff`.
- `/docs`,`/openapi.json`,`/redoc`: return 489-byte SPA shell (backend Swagger not publicly routed).
- `/health`: **200** `{ok:true,…}`.

## Screenshots captured (session scratchpad — not committed; contain no secrets except transient
roster PII kept out of reports)
Login, admin dashboard, student home (desktop+mobile), My Training (desktop+mobile), All Course
Content, Progress, Week 0, a CLI networking lab, Terminal Practice, Networking Labs list,
Service Desk (student unavailable), admin Students / Weekly Training / Service Desk / Ticket Review.

## Temporary records created & removed (production)
- **Created:** throwaway student `zz_review_tmp_fb0dd9` (id **8**) via `POST /api/admin/students`;
  2 quiz attempts (quiz 42) + incidental login-streak rows.
- **Removed:** `DELETE /api/admin/students/8` → `{deleted:true}`; roster returned to the 7 real
  accounts (ids 1–7, untouched); deleted-student login now **401** (cascade confirmed); admin
  session logged out; scratchpad credential files scrubbed.
- **Admin credential** was read from local `backend/.env` in-memory only (user-authorized) — never
  printed, committed, or written to any report.

## Errors / warnings encountered
- **Cloudflare beacon CSP warning** on every authenticated page — **known-harmless** (strict CSP
  intentionally blocks the beacon; do not weaken).
- **`/service-desk` (student, gated):** 4× 404 console errors on the availability probe — real, to fix.
- Render **cold-start** (~up to 30s first load) noted on the login page.
- No other production-only errors observed.

## Areas that could NOT be validated (and why)
- **Student-side Service Desk experience** (Learning/Simulation modes, tools, KB, mobile, on-screen
  scoring) — **flag-gated OFF for normal students; toggling feature flags is prohibited by the
  review.** Reviewed via admin panel + scenario source only.
- **Production brute-force / rate-limit testing** — intrusive; not performed.
- **Backend Python dependency audit** (`pip-audit`/`safety`) — tool not installed in the review env;
  frontend `npm audit` is clean.
- **Formal color-contrast + screen-reader audit** — structural a11y checks only (no axe-core);
  recommend an axe/Lighthouse + manual SR pass in CI.
- **Exact deployed commit vs. baseline** — cannot read production's git SHA; behavior matched the
  `15a9410` source across all routes/nav/features. Docs describe self-host while prod appears to be
  Cloudflare/Render (unresolved from outside; flagged for owner reconciliation).
