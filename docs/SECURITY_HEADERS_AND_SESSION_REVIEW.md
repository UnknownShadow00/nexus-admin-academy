# Cookie, CSRF, CORS, and Security-Header Review

Date: 2026-07-21. Covers Phases 3–6 of the security review triggered by an
external Deep Research report. All findings below were verified against the
current code and, where noted, the live `.101` deployment before any fix was
applied.

## Cookies (student + admin)

Both cookies (`student_session` in `app/routers/auth.py`, `admin_session` in
`app/routers/admin_session.py`) were already:

- `HttpOnly` — always.
- `Secure` — when `COOKIE_SECURE`/`is_production_environment()` resolves true
  (confirmed true in the live `.env`).
- Scoped to `path="/"` — broad, but required since the SPA and API share one
  origin behind the nginx proxy; narrowing it would not reduce real exposure
  here and would risk breaking routes.
- Expiring — student cookie 24h, admin cookie 12h (`ADMIN_SESSION_TTL_SECONDS`).
- Invalidated on logout — `/auth/logout` deletes the student cookie;
  `/api/admin/session/logout` calls `revoke_admin_session()` (server-side,
  removes the token from the in-process session store) *and* deletes the
  cookie. Verified by the existing `test_random_admin_session_roundtrip` test:
  a replayed cookie value fails after logout even though it was valid seconds
  earlier.
- Never stored in `localStorage` — `frontend/src/hooks/useAuth.js` keeps the
  in-memory JWT in a module-level variable and only ever *removes* a legacy
  `localStorage` key, never writes one.

**Found and fixed this review:** `SameSite` was `"none" if secure_cookie else
"lax"` — i.e. `None` in production. `None` is the correct choice only when a
cookie must ride along on genuine cross-site requests; it was not needed here.
Production is served same-origin (Cloudflare tunnel → nginx proxies `/api/`,
`/auth/`, `/uploads/` to the backend under one domain — see
`frontend/nginx.host.conf`), and the one cross-origin caller, the ExamCompass
bookmarklet (`frontend/src/pages/admin/BookmarkletPage.jsx`), authenticates
with an `X-Admin-Key` header and never sends `credentials: 'include'` — so no
legitimate flow depended on `SameSite=None`. All three cookie-setting call
sites now use `SameSite=Lax` unconditionally, which is strictly more
CSRF-resistant and has no functional cost. Regression tests:
`test_student_login_cookie_is_always_samesite_lax`,
`test_admin_login_cookie_is_always_samesite_lax` in
`backend/tests/test_security_hardening.py`.

## CSRF

Before this review, cookie-authenticated state-changing routes had no defense
beyond `SameSite`, which the report correctly flagged as insufficient on its
own. Fixed this review: `app/main.py` adds an Origin/Referer-validation
middleware (`csrf_origin_validation`) that:

- Only inspects `POST`/`PUT`/`PATCH`/`DELETE` requests.
- Only acts when a `student_session` or `admin_session` cookie is present —
  Bearer-token-only and `X-Admin-Key`-only requests (including the
  bookmarklet) are untouched.
- Requires `Origin` (falling back to `Referer`) to match a trusted-origin set
  built from the same `CORS_ORIGINS`/`FRONTEND_URL` configuration already used
  for CORS, explicitly excluding the two hardcoded ExamCompass origins (they
  should never be treated as a first-party session-cookie origin), plus the
  request's own `Host`-derived origin so same-origin calls always pass.
- Rejects with `403 {"code": "CSRF_REJECTED"}` when Origin/Referer is missing
  or doesn't match.

This is defense-in-depth on top of the `SameSite=Lax` fix, not a replacement
for it — either control alone would stop the classic form/fetch CSRF cases;
together they cover browsers with inconsistent `SameSite` support and any
future re-introduction of a cross-site flow. Tests:
`test_csrf_allows_trusted_student_origin_and_rejects_foreign_or_missing`,
`test_csrf_allows_trusted_admin_origin_and_skips_cookie_free_requests`,
`test_csrf_does_not_block_get_requests_with_session_cookie`.

## CORS

`app/main.py`'s `_cors_origins()` was already origin-allowlisted (never a
wildcard) with `allow_credentials=True`. One residual note, not fixed and not
blocking: the two ExamCompass origins are added unconditionally, in every
environment, so that a mentor can use the admin bookmarklet while browsing
ExamCompass. Verified that flow uses `X-Admin-Key` header auth with no
`credentials: 'include'` — so `allow_credentials=True` does not currently
grant ExamCompass cookie-based access in practice, and the CSRF middleware
above additionally ensures ExamCompass could never pass Origin validation to
ride a stolen/replayed cookie. This is an accepted, narrow tradeoff for a
mentor productivity tool against a fixed third-party origin the team doesn't
control — flagged for awareness, not required before launch.

`allow_methods=["*"]` / `allow_headers=["*"]` remain broad; left as-is since
tightening them would be a larger, riskier change for marginal benefit given
the origin allowlist and the new CSRF layer already constrain the actual
attack surface.

## HTTPS and security headers

**Before this review (live, verified via `curl -I` against
`https://nexus.builtfromzero.fyi`):** no `Strict-Transport-Security`, no
`Content-Security-Policy`, no `X-Content-Type-Options`, no `Referrer-Policy`,
no `Permissions-Policy` on any response — from Cloudflare, nginx, or the
FastAPI backend. Also confirmed: plain `http://nexus.builtfromzero.fyi/`
returns `200 OK` directly (no redirect to HTTPS) — the Cloudflare tunnel
(`ingress: service: http://localhost:80` in `/home/nexus/.cloudflared/config.yml`)
forwards to nginx over plain HTTP regardless of how the client reached the
edge, and neither nginx nor the tunnel config enforces an upgrade.

**Fixed this review (code-level, not yet deployed):**
- FastAPI (`app/main.py`, applies to all `/api/`, `/auth/` JSON responses):
  `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(),
  camera=(), microphone=()`, a CSP scoped to this app's actual needs
  (`script-src 'self'`; `frame-src` allowlists only the two YouTube embed
  origins used by `LearningPath.jsx`; `frame-ancestors 'self'`; `object-src
  'none'`), and `Cache-Control: no-store` on every `/api/`/`/auth/` response
  so authenticated JSON is never cached. `Strict-Transport-Security` is only
  emitted when the request arrived over HTTPS (checked via
  `X-Forwarded-Proto`/`request.url.scheme`), so local `http://localhost` dev
  is unaffected.
- Nginx (`frontend/nginx.conf` and `frontend/nginx.host.conf`, both kept
  consistent): the same five headers added via `add_header ... always;` on
  the SPA and static-asset locations. HSTS is added unconditionally here —
  safe because browsers only ever honor an HSTS header on a response actually
  received over HTTPS (i.e. the real end-user connection via Cloudflare's
  edge TLS); sending it on the plaintext tunnel hop to origin is inert, not
  harmful.

**Not fixed by this review — requires a Cloudflare dashacard action, not a
code change:** the missing HTTP→HTTPS redirect. `HSTS` only protects a client
that has already completed one HTTPS visit; a user who types the bare
`http://` domain, or follows an old `http://` link, still gets served over
plaintext today. The correct fix is enabling **"Always Use HTTPS"** (or an
equivalent edge redirect rule) on the `builtfromzero.fyi` zone in the
Cloudflare dashboard — this repo and this tunnel config have no lever for it.
**Recommend doing this before/at launch** since it's a two-click dashboard
change, not a deploy.

**Deployed 2026-07-21:** all of the above header/CSP/cookie/CSRF code changes
are live — backend restarted, frontend rebuilt and redeployed into the
`nexus-frontend` container. Live `curl -I https://nexus.builtfromzero.fyi/`
confirms CSP, HSTS, X-Content-Type-Options, Referrer-Policy, and
Permissions-Policy all present; `/auth/me` confirms `Cache-Control: no-store`
on authenticated API responses. 41/41 live smoke-test checks passed (see
`docs/DEEP_RESEARCH_FINDINGS_RECONCILIATION.md`'s deployment record).

**Known minor issue found post-deploy:** nginx's `add_header` directives are
set at the `server` block level, so proxied backend paths (`/api/`, `/auth/`,
`/health`) get the same headers twice — once from nginx, once from the
FastAPI middleware. Values are identical (confirmed live), so there's no
security impact, but it should be cleaned up by scoping nginx's `add_header`
to just `location /` and `location /assets/`.

**Cloudflare "Always Use HTTPS":** still not enabled as of this deploy — a
live check of `http://nexus.builtfromzero.fyi/` still returns `200` with no
redirect. This is a dashboard-only setting; no code lever exists for it here.

## Frame-related notes

- `frame-ancestors 'self'` in the new CSP controls who may embed *this* app in
  an iframe — there's no current reason for Nexus to be framed by anyone, so
  this is safe and was not set to `X-Frame-Options: DENY` (which would be
  redundant with a modern CSP and more brittle).
- `frame-src` (what Nexus itself may embed) currently only needs YouTube for
  lesson videos (`LearningPath.jsx`). Automated VM labs are not live (Proxmox/
  Guacamole env vars are unset in production — see the reconciliation report),
  so no Guacamole origin is allowlisted yet. **Follow-up required**: add the
  configured `GUACAMOLE_URL` origin to `frame-src` in `app/main.py`'s
  `_SECURITY_CSP` before automated VM labs ever go live, or the Guacamole
  iframe in `LabPage.jsx` will be silently blocked by CSP.
