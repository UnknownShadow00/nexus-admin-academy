# Deep Research Report Reconciliation

Date: 2026-07-21. The external Deep Research report (`deep-research-report.md`,
repo root) was explicitly written without ZIP access to this repository and
without authenticated live testing — it reasoned from older handoff documents
and a July 19 deployment artifact. This document classifies every major claim
in that report against the code and live deployment as of this review.

## Classification legend

- **Fixed before this review** — already resolved in the code prior to today,
  contradicting the report's older source material.
- **Fixed during this review** — confirmed present, then fixed today.
- **Still pending** — confirmed present, not fixed today.
- **Outdated** — the report's premise no longer matches reality (e.g. a doc
  drift that has since been corrected).
- **Not applicable** — describes a system/config that isn't in play here.
- **Requires automated-VM staging** — only matters once automated labs go live.

## Critical / high findings from the report

| Report claim | Classification | Evidence |
|---|---|---|
| Guacamole `get_token_url` authenticates as the admin user and embeds that token in the student-facing URL, letting a student reach the Guacamole admin UI | **Fixed before this review** | `backend/app/services/guacamole_service.py`: `create_scoped_access()` creates a per-assignment temporary Guacamole user, grants it `READ` on exactly one connection, and issues *that* user's own token for the student URL. The admin token (`_admin_token()`) is used only in server-side calls (`create_connection`, `delete_connection`, `delete_user`) and is never returned to any API response. |
| `allow_admin_or_student()` accepts any `Authorization: Bearer <anything>` string without verifying it | **Fixed before this review** | `backend/app/services/admin_auth.py` decodes and verifies the JWT (`decode_token`) before accepting a Bearer token; regression test `test_bearer_garbage_rejected` in `tests/test_security_part9.py` pins this. |
| Admin session token is `sha256(password)` — deterministic, non-expiring, non-constant-time compared | **Fixed before this review** | `backend/app/services/admin_auth.py`: `issue_admin_session()` uses `secrets.token_urlsafe(32)`, stored server-side with a TTL (`ADMIN_SESSION_TTL_SECONDS`, default 12h) and revoked on logout; credential comparisons use `hmac.compare_digest`. Regression tests `test_legacy_deterministic_admin_cookie_rejected`, `test_random_admin_session_roundtrip`. |

## Material medium findings from the report

| Report claim | Classification | Evidence |
|---|---|---|
| `AdminAccessGate.jsx` gates the admin UI on `localStorage.selected_profile.is_mentor` (client-only) | **Fixed before this review** | `frontend/src/components/AdminAccessGate.jsx` calls `adminSessionStatus()` (`GET /api/admin/session/status`, backed by `has_valid_admin_session(request)`) on mount and reacts to a `nexus:admin-session-invalid` event on any 401/403 — the gate is server-verified, not `localStorage`-derived. |
| `evidence.py` has no file-size cap and no ownership check | **Fixed before this review** | `backend/app/routers/evidence.py`: bounded read against `MAX_EVIDENCE_UPLOAD_BYTES` (10MB default), extension/MIME allowlist, and `EvidenceArtifact.student_id = current_student.id` set at creation. `tickets.py`'s submit flow additionally verifies referenced evidence IDs belong to the submitter. |
| SQLite foreign keys disabled / orphaned rows causing admin student-creation 500s | **Fixed before this review** | `backend/app/database.py` enables `PRAGMA foreign_keys=ON` on every SQLite connection via an SQLAlchemy `connect` event listener. `admin_students.py`'s `create_student()` catches `IntegrityError` → `409` rather than 500; student IDs are DB-autoincrement, no manual reuse. Live `PRAGMA foreign_key_check` returns zero violations (verified against the fresh backup taken for this review). |
| Documentation says production is PostgreSQL/Supabase/Railway while the deployment is actually SQLite | **Outdated** | `README.md` and `TASKS.md` both already state the deployment is self-hosted SQLite and that "Railway/Supabase plans are historical" — the drift the report flagged has already been corrected in-repo. |
| Evidence uploads may be lost on redeploy if `UPLOAD_DIR` sits on ephemeral storage | **Not applicable** | Active deployment is self-hosted on `.101` with `UPLOAD_DIR` on persistent local disk, covered by `scripts/backup_sqlite.sh`'s nightly `rsync` of the uploads directory — there is no Railway/ephemeral-storage deployment in play. |

## Reliability findings with security implications

| Report claim | Classification | Evidence |
|---|---|---|
| Synchronous VM provisioning blocks the worker 60–120s against a 30s frontend timeout | **Fixed before this review** | `backend/app/routers/labs.py`: `start_lab` persists a `VmAssignment` and returns `202` immediately; provisioning runs in a background task (`_provision_vm_task`) with its own DB session; the frontend polls `GET /{lab_id}/vm-status`. |
| Page refresh loses the in-memory Guacamole URL | **Fixed before this review** | `VmAssignment` state (status, IP, connection ID, guac URL, error, expiry) is persisted and re-served by `GET /api/labs/{lab_id}`; `LabPage.jsx` resumes polling instead of re-provisioning. |
| No live isolated automated-VM lifecycle test performed | **Requires automated-VM staging** | Confirmed still true and intentionally so: `PROXMOX_HOST`, `PROXMOX_TOKEN_ID`, `GUACAMOLE_URL`, `GUACAMOLE_ADMIN_USERNAME` are all unset in the live `.env`, and 0 of the 5 manual lab templates have a `proxmox_template_vmid` configured — the automated code path is present but functionally inert in production. Manual-VM labs remain the launch default. |

## Requested-but-unverifiable-by-the-report items — verified this review

| Item | Result |
|---|---|
| `/login`, `/admin-login` reachability | Confirmed live: both flows return 200 on a fresh smoke check; see final report. |
| TLS/HTTPS | Confirmed live via `curl -I https://nexus.builtfromzero.fyi/`: HTTP/2, valid Cloudflare-issued TLS, `alt-svc: h3` (QUIC available). **New finding this review**: plain `http://` is served `200 OK` with no redirect to HTTPS — see `docs/SECURITY_HEADERS_AND_SESSION_REVIEW.md`. Still pending; requires a Cloudflare dashboard change ("Always Use HTTPS"), not a code fix. |
| Response headers | Confirmed live: no security headers present before this review. **Fixed during this review** at the code level (FastAPI middleware + both nginx configs) — not yet deployed to `.101`. |
| `robots.txt` / `sitemap.xml` | Confirmed live: `robots.txt` exists and is a real, intentional AI-crawler-consent policy file, not a stray default. `sitemap.xml` has no dedicated route and falls through to the SPA's `index.html` (cosmetic — a 200 with HTML instead of a 404/real sitemap; not a security issue, not fixed, not blocking). |

## New findings from this review (not in the original report)

| Finding | Classification | Action |
|---|---|---|
| `POST /api/tickets/uploads` read the entire multipart body into memory before checking the 5MB per-file cap, with no aggregate cap across multiple files in one request — inconsistent with the already-hardened `evidence.py` bounded-read pattern | **Fixed during this review** | Bounded read (`file.read(MAX_FILE_SIZE + 1)`) plus a new 20MB aggregate cap across all files in one request. Tests: `test_ticket_upload_is_bounded_and_valid_upload_still_succeeds`, `test_ticket_upload_rejects_combined_size_and_invalid_mime`. |
| `SameSite=None` used for all cookies in production despite the app being served same-origin, weakening CSRF posture beyond what the deployment topology requires | **Fixed during this review** | All three cookie-setting call sites now use `SameSite=Lax` unconditionally. See `docs/SECURITY_HEADERS_AND_SESSION_REVIEW.md`. |
| No CSRF-specific defense beyond `SameSite` | **Fixed during this review** | Origin/Referer-validation middleware added, scoped to cookie-authenticated state-changing requests only. |
| No security response headers (HSTS, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) anywhere in the stack | **Fixed during this review** | See above; code-complete, not yet deployed. |
| Plain HTTP not redirected to HTTPS at the Cloudflare edge | **Still pending** | Dashboard-only fix, out of this repo's control. |
| `GET /api/students` returns every student's email to any authenticated student (not just mentors), combined with `GET /api/leaderboard` exposing XP/level for all students | **Fixed during this review** | `backend/app/routers/students.py`'s `get_students()` now returns only `id`/`name` — the only fields the frontend's ticket-collaborator picker (`TicketSubmit.jsx`) actually reads. Admins retain email access via the already-existing, `verify_admin`-gated `GET /api/admin/students/overview`. Tests: `test_student_roster_leaks_no_email_or_private_fields`, `test_admin_overview_still_returns_email_for_account_management` in `backend/tests/test_security_hardening.py`. `GET /api/leaderboard` was already email-free. |
| `admin_session.py`'s `/student-token` route guards itself with a manual `has_valid_admin_session` check instead of `Depends(verify_admin)` (functionally correct, inconsistent) | **Still pending — cosmetic** | Not a bypass; consistency cleanup only. |
| `admin_tickets.py`'s `verify_proof` hardcodes `submission.verified_by = 0` — no real admin-identity attribution | **Still pending — audit-trail only** | Not an authorization gap in a single-shared-admin-credential deployment. |
| `/uploads/screenshots` is a public `StaticFiles` mount with no per-request auth check (relies on unguessable UUID filenames) | **Still pending — accepted tradeoff** | Documented in `docs/SECURITY_ROUTE_AUTHORIZATION_AUDIT.md`; not launch-blocking. |
| A leftover uncommitted change adds a temporary "Claude" student account (live in the DB, id 8) and references a "Codex administrator" review account, with credentials in `backend/.env`, apparently created for this review and not yet cleaned up | **Fixed** | Fully resolved 2026-07-21. Fresh verified backup taken first (`~/backups/nexus-security-review/20260721T022432Z/`). Inspected the live "Claude" row (id 8): zero owned rows in any other table. `ADMIN_USERNAME` was found to literally equal the temporary value `codex` (confirmed via a live `.env` mtime match to the review-account creation timestamp, and a boolean-only comparison — no secret value was ever printed); the operator replaced it with the real mentor credentials directly. The "Claude" account was removed via the supported `DELETE /api/admin/students/{id}` workflow; `SEED_PASSWORD_CLAUDE` was removed from `.env`; the temporary `ACCOUNTS` entry in `seed_users.py` was reverted. Post-cleanup: 7 real cohort accounts remain, zero orphan rows, integrity `ok`, zero FK violations, `test_username_case.py` passes, and a live admin-login round-trip with the new credentials succeeds (old `codex` username now rejected). |

## Deployment record (2026-07-21)

- Pre-cleanup backup: `~/backups/nexus-security-review/20260721T022432Z/` (application.tar.gz, nexus.db.gz, uploads.tar.gz) — integrity `ok`, zero FK violations, verified before any change.
- Temporary-account cleanup: "Claude" student (id 8, zero owned rows) removed via `DELETE /api/admin/students/8`; `SEED_PASSWORD_CLAUDE` removed from `.env`; temporary `ACCOUNTS` entry reverted in `seed_users.py`; real `ADMIN_USERNAME`/`ADMIN_PASSWORD` restored by the operator directly in `.env` (values never viewed or printed by the assistant).
- Backend deploy: `nexus-admin-academy.service` restarted (via `kill -KILL $MAINPID`, since interactive `sudo` is unavailable in this environment and `Restart=on-failure` is configured — documented practice, see `CLAUDE.md`'s "Deployment reality note"). Clean startup, no import/middleware errors, `/health` returned 200 before and after.
- Frontend deploy: `npm run build` → `docker cp dist/. nexus-frontend:/usr/share/nginx/html/` + updated `nginx.host.conf` → `docker exec nexus-frontend nginx -s reload`. `nginx -t` passed before reload.
- Live smoke test: 41/41 checks passed (authentication, CSRF, email privacy, uploads, security headers, core workflows, ticket submission + live Ollama grading) using disposable accounts, all removed afterward with zero orphan rows.
- Final verification: 176 backend tests passed, `alembic current` → `0029 (head)`, SQLite integrity `ok` / zero FK violations, `npm audit` 0 vulnerabilities, `npm run build` clean.
- Cloudflare "Always Use HTTPS": **not enabled** as of this deployment — confirmed via a live `curl` showing plain `http://nexus.builtfromzero.fyi/` still returns `200` with no redirect. This remains a pending operator action in the Cloudflare dashboard; no code lever exists for it in this repo.
- Minor finding (not blocking): the new nginx security headers are set at the `server` block level in both `nginx.conf`/`nginx.host.conf`, so proxied backend paths (`/api/`, `/auth/`, `/health`) receive the same headers twice — once from nginx, once from the FastAPI middleware — since both layers add them. Values are identical in every case, so this has no security effect (confirmed live), but it's untidy and worth a follow-up cleanup (scope `add_header` to just the `location /` and `location /assets/` blocks).

## Not applicable

- Railway/Supabase-specific persistence risks — no such deployment exists.
- Any finding predicated on the ZIP-inspection or authenticated-live-testing
  the report says it could not perform — superseded by this review's direct
  code and live-deployment checks.
