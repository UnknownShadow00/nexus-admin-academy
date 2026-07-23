# Phase 10 — Security & Privacy (defensive, non-destructive)

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** Source review + LIVE authorization probes with the temp student/admin accounts only.
No exploitation, no auth bypass, no rate-limit testing against production.

## Strong controls (verified)

| Area | Status | Evidence |
|---|---|---|
| Password storage | ✅ | `passlib` **bcrypt** primary + `pbkdf2_sha256` (390k iters) fallback. |
| Session cookies | ✅ | Student JWT + admin session both `HttpOnly`, `Secure` (prod via `use_secure_cookies`), `SameSite=lax`, bounded `max_age`. |
| CSP | ✅ (strict) | `default-src 'self'; script-src 'self'` (no script unsafe-inline), `object-src 'none'`, `frame-ancestors 'self'`, `base-uri 'self'`, `form-action 'self'`, frame-src YouTube only. **Live-confirmed present.** |
| Other headers | ✅ | HSTS 2yr+includeSubDomains, `X-Content-Type-Options: nosniff`, Referrer-Policy, Permissions-Policy (geo/cam/mic off). Live-confirmed. |
| CSRF | ✅ | Origin-allowlist middleware (`_csrf_trusted_origins` from CORS origins + forwarded headers). |
| CORS | ✅ | Env-scoped (`CORS_ORIGINS`/`FRONTEND_URL`), no wildcard. |
| Admin auth | ✅ | Shared `ADMIN_USERNAME/PASSWORD` via env; `hmac.compare_digest` (timing-safe); random expiring server-side session. |
| Student→admin isolation | ✅ (live) | Student & unauth → `/api/admin/*` return **403**. |
| IDOR (quizzes) | ✅ (live) | `review/{other}` → 403; submit with `student_id:1` → 403; no pre-submit answers. |
| IDOR (students/tickets) | ✅ (live) | `/api/students/1[/progress]` → 404; `/api/quizzes?student_id=1`, `/api/tickets?student_id=1` → 403; `training/progress?student_id=1` ignores param, returns own data. |
| Hidden facts | ✅ | Ticket `scoring_anchors/root_cause/model_answer` and Service Desk `hidden_facts` (incl. BitLocker `recovery_key`, `critical_failure_definitions`) kept server-side. |
| File uploads | ✅ | Extension allowlist (jpg/jpeg/png/webp/txt/log) + MIME allowlist + 10 MB bounded read (`read(MAX+1)`), ownership-stamped. |
| Rate limiting (AI) | ✅ | `check_rate_limit(user,endpoint)` + pruning for AI usage. |
| Unauth `/auth/me` | ✅ | Returns **401** (expected behavior, not an error). |
| Dependency audit (frontend) | ✅ | `npm audit --audit-level=high` → **0 vulnerabilities**. |
| Security test suite | ✅ | 45 tests pass (hardening, part9, auth, JWT, admin session). |
| `/docs` exposure | ✅ non-issue | `/docs`, `/openapi.json`, `/redoc` return the 489-byte SPA shell publicly — the reverse proxy only routes `/api/*` and `/auth/*` to the backend, so Swagger is **not** reachable on the public domain. |
| Edge | ✅ | Cloudflare fronts prod (non-browser requests get 403 `1010`), adding bot/rate protection. |

## Findings (weaknesses)

**F1 — No app-level login rate limiting / lockout (P2).**
Neither `/auth/login` nor `/api/admin/session/login` throttles attempts or locks out after
failures. Realistic impact: online brute force of student/admin passwords. **Mitigated** by
Cloudflare in front and timing-safe admin compare, but there is no defense-in-depth at the app.
*Fix:* per-IP + per-username attempt counter with backoff/lockout (reuse the rate-limiter model).
*Regression test:* N failed logins → 429/lock. *Blocks student use?* No. *Blocks beta?* No.

**F2 — No admin audit log; single shared admin identity (P2).**
All admin actions (edit/delete student, publish content, reset attempts, beta enroll) run under
one shared credential and are **not recorded with actor/time**. Can't answer "which actions were
performed by administrators?" (Phase 4). *Fix:* append-only admin audit log (action, target,
timestamp) surfaced under System. *Regression test:* mutating admin call writes an audit row.

**F3 — Search bypasses lesson gating (Low).**
`/api/search/global` returns full summaries of lessons a student cannot open (lesson 22 → page
403 but present in search). Content isn't secret, but it defeats the progression gate.
*Fix:* filter search results by module/week unlock. *Regression test:* locked lesson absent from search.

**F4 — Upload validation is extension+MIME, not content/magic-byte (Low).**
A renamed file passing the extension+MIME check could be stored. Low risk: files are stored (not
executed) and served with `nosniff`; images are size-bounded. *Optional:* verify image magic bytes.

**F5 — Duplicate security headers (Info).**
CSP/HSTS appear twice (backend + edge both set them). Harmless; consolidate for tidiness.

## Privacy / data-handling
- Student endpoints never return other students' evidence, answer keys, scoring anchors, or hidden
  scenario facts (verified). Cross-student reads are 403/404.
- **Temp reviewer accounts:** admin credential used in-memory only (never written to any report);
  throwaway student id 8 is the only production write — **scheduled for deletion in Phase 16**.
- Backup/secret/`.env` permissions and recovery-key storage at rest → Phase 11/15.

## Not validated / out of scope here
- **No production brute-force / rate-limit testing** performed (would be intrusive; prohibited).
- **Backend Python dependency audit** (`pip-audit`/`safety`) not run (tool not installed in the
  review env) — recommend running it in CI. Frontend audit is clean.
- Production debug flag: `FastAPI()` has no explicit `debug=`; no debug leakage observed live.

## Verdict
Security posture is **strong for a small private program** — solid crypto, cookies, CSP, CSRF,
and airtight object-ownership/authorization (all IDOR probes blocked live). The two worthwhile
hardening items are **login rate limiting (F1)** and an **admin audit log (F2)**; neither blocks
student launch. No P0/P1 security defect found.

## Priorities
- P2: F1 login rate limiting; F2 admin audit log.
- P3/Low: F3 search-gating; F4 magic-byte upload check; F5 header de-dup.
- CI: add `pip-audit` for backend deps.
