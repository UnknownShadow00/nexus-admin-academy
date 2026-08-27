# Nexus Admin Academy — Full Fresh Code Review

**Date:** 2026-08-27 · **Reviewer:** Claude Code (Sonnet)
**Repo:** `UnknownShadow00/nexus-admin-academy` (public)
**Deployed commit observed at review start:** `8ea625a` (detached) — **advanced to `44b7723` mid-review by host automation** (see P1-1)
**Prior review:** `NEXUS_FULL_PROJECT_REVIEW.md` (2026-07-23, baseline `15a9410`) — treated as historical only.

**Method actually performed**

| Check | How | Result |
|---|---|---|
| Git history forensics (leaked evidence) | `git log --all --full-history` over every flagged path + blob scan of all revs | Clean — nothing to rewrite |
| Production topology | `systemctl cat/status`, `ss -tlnp`, `docker ps`, `docker inspect`, `docker exec` on nginx/SD containers, live `curl` | Self-hosted systemd + SQLite + Cloudflare tunnel confirmed |
| Backend test suite | clean venv, in-memory SQLite, `pytest -q` | **555 passed**, 142 s, exit 0 |
| Migrations from empty | isolated clone, temp SQLite, `alembic upgrade head` | Clean → head `0061`, 57 tables, `integrity_check ok`, 0 FK violations |
| Seed idempotency | isolated clone, temp DB, `seed.py` + `seed_curriculum.py` run **twice** | No duplicate keys/titles/weeks created on 2nd run |
| service-desk-app gate | **fresh `pnpm install --frozen-lockfile`** in isolated clone, then `lint && typecheck && test && build` | All pass — lint 5/5, typecheck 10/10, **test 322**, build 5/5 (21 static pages) |
| `pnpm audit --prod` | isolated clone, **real registry** (first successful run in project history) | **No known vulnerabilities found** |
| Nexus JWT integration | source diff of both codebases + live container env + live edge routing | Contract aligned and wired; full authenticated click-through **not** performed (no browser tooling) |
| Live security headers / auth probes | `curl` against `https://nexus.builtfromzero.fyi` | HSTS + strict CSP + nosniff present; login has no app-layer rate limit |

**Not done (be explicit):** no authenticated browser click-through with screenshots (no Playwright/Chromium
available in this environment and it would require production student credentials); no local build of the
main Vite frontend (host disk at 94%); no `alembic downgrade` walk. NB-5 is therefore **still not closed
end-to-end** — see P1-4.

---

# Priority 0 — the three gating investigations

## P0.1 — Leaked-credential claim: **NOT reproducible in this repo. No history rewrite required.**

`service-desk-app/docs/ARCHITECTURE.md` §6 documents a prior audit of a *different* working tree
(paths are all `../website-capture/…`, `../artifacts/…`, and "the root `.gitignore` (`Nexus dupe/.gitignore`)")
that found ~118 live bearer tokens and a real tester email inside mislabeled-"sanitized" evidence files.

Evidence those files never entered **this** repository's history:

| Probe | Command | Result |
|---|---|---|
| HAR files ever | `git log --all --full-history -- '*.har' '*session.sanitized.har'` | empty |
| "sanitized" / "firestore" named files ever | `git log --all --full-history -- '*sanitized*' '*firestore*'` | empty |
| capture infra ever | `git log --all --full-history -- '*website-capture*' '*crawlee*' '*browsertrix*' '*.auth*'` | empty |
| `service-desk-app/artifacts/*` ever | `git log --all --full-history -- 'service-desk-app/artifacts/*'` | empty |
| tracked today | `git ls-files \| grep -iE 'artifact\|capture\|\.har\|firestore\|evidence'` | only 3 deployment screenshots under `Nexus dupe/artifacts/` + backend evidence *code* |
| on disk today | `find … -type f` | `service-desk-app/artifacts/` and `service-desk-app/website-capture/` do not exist |
| blob scan for the Firebase key across every rev | `git rev-list --all \| xargs -n1 git grep -l 'AIzaSy…'` | only `service-desk-app/docs/ARCHITECTURE.md` itself, which quotes it as a "by-design-public client identifier" |

The service-desk-app was consolidated into this repo as source + docs only (snapshot `6aa2ae1`
"Nightly snapshot 2026-08-03", then `feature/merge-service-desk-into-nexus`); the evidence/capture
folders were left behind in the original tree.

**`.gitignore` coverage (the doc's fallback ask):** `service-desk-app/.gitignore` blanket-ignores
`artifacts/`, `website-capture/`, and `playwright/` — broader than the specific
`website-capture/browsertrix/crawls/profiles/` and `…/**/profile/` the doc wanted, so it is covered.
Residual gap → **P3-1**: the *root* `.gitignore` ignores only `artifacts/e2e-launch-verification/`, not
a blanket `artifacts/` or `website-capture/`; if either capture tree is ever recreated at repo root it
would not be ignored.

**Action:** none for git history. Close the ARCHITECTURE.md §6 action item as "N/A — files never migrated";
optionally harden the root `.gitignore` (P3-1).

## P0.2 — Production reality: **self-hosted systemd + SQLite + Cloudflare tunnel. Not Render.**

| Layer | Reality (evidence) |
|---|---|
| Backend process mgr | `systemd` unit `nexus-admin-academy.service`, `Type=simple`, `ExecStart=…/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000`, `WorkingDirectory=…/projects/nexus-admin-academy/backend` — **this checkout is production**. Active 23 h+ at review start. (`systemctl cat/status`) |
| Database | **SQLite** `backend/nexus.db` (3.0 MB, 7 students, `alembic_version = 0061`). `app/database.py` default `sqlite:///./nexus.db`; prod `backend/.env` `DATABASE_URL` set (value not displayed). No Postgres in the production path. |
| Frontend | Docker container `nexus-frontend` (`nginx:alpine`) publishing `0.0.0.0:80`, serving the Vite build and proxying `/api /auth /uploads /health` to `backend-host:8000` and `/service-desk*` to `nexus-service-desk:3000`. |
| Service Desk | Docker container `nexus-service-desk` (`Up 3 days (healthy)`, `127.0.0.1:13000->3000`). |
| Edge / TLS | `cloudflared.service` tunnel, up 1 month (`/etc/cloudflared/config.yml`). Live responses carry `server: cloudflare`, `cf-ray`. Domain `nexus.builtfromzero.fyi` → `/health` returns `200 {"success":true,…}`. |
| Also on the host (not prod) | a `nexus-staging-*` compose stack (backend + SD web + **postgres:16** + frontend) up for weeks on ports 18000/18081, and a legacy `nexus-service-desk:331efc…` image. |

**Docs to correct (docs-vs-reality):**

| Doc | Stale claim | Correct |
|---|---|---|
| `NEXUS_FULL_PROJECT_REVIEW.md` §2, §4.5, §18 | "backend apparently on **Render**", "Render cold-start" | self-hosted systemd; no cold start |
| `docs/PRODUCTION_STATE_2026-07-25_schema_ahead_of_code.md` | live doc describing an unmerged-branch state | resolved — should be archived (see P0.3) |
| `tasks/loop-log.md` (Apr 2026 entries) | "hardened … for Render/Supabase deployment", "Set production env vars on Render/Vercel" | historical; leave but do not treat as current |
| `README.md` | already fixed — "Railway/Supabase plans are historical" | ✅ accurate |
| `docs/DEPLOYMENT.md`, `docs/AUTHORING_CONFIG_SECURITY.md` | — | ✅ already describe systemd + SQLite + Cloudflare + nginx accurately |

## P0.3 — Schema-ahead-of-code: **RESOLVED. The doc is now stale and should be archived.**

`docs/PRODUCTION_STATE_2026-07-25_schema_ahead_of_code.md` recorded that migrations `274729e5d444` and
`6736e5d5172a` from the then-unmerged `fix/question-bank-integrity-and-import` had been applied to prod
while the service ran older code, with the explicit exit condition "deploy this branch's code … then this
file can be archived."

That happened:

| Check | Result |
|---|---|
| Branch merged | `c904be2 Merge pull request #4 from …/fix/question-bank-integrity-and-import` is in `main` history |
| Prod DB revision | `SELECT version_num FROM alembic_version` → `0061_integrated_support_prove` (the migrations were renumbered into the sequential `00xx_` chain; the doc's `6736e5d5172a` is an ancestor) |
| `questions` columns live | `difficulty, tags, source, fingerprint, imported_at, import_filename, flagged_for_review, flag_reason` **all present**, plus `seed_key` |
| Code ↔ schema | `alembic current` (against prod DB) = `0061 (head)`; tree has a **single** head `0061`; fresh empty→head applies clean. No orphaned columns, no migration without model support found. |

**Status: code and schema are in sync.** Residual items:
- **P3-2:** delete/relocate `docs/PRODUCTION_STATE_2026-07-25_schema_ahead_of_code.md` (move to `docs/reviews/` or an `archive/`); as written it reads as a current warning.
- **P3-3 (dev ergonomics):** `alembic heads` / `alembic upgrade` fail without `PYTHONPATH=.` because
  `alembic/versions/0043_retire_legacy_tickets.py` does `from app.services.service_desk_objectives import …`
  at import time. `alembic current` works. Add `prepend_sys_path = .` to `alembic.ini` or stop importing
  app code from migrations.

**Priority-0 verdict:** all three gating investigations come back **clean or already-resolved**. Nothing in
Priority 0 blocks the follow-on plan. The only Priority-0-adjacent live risk is operational, not code —
see **P1-1**.

---

# Executive summary

Nexus remains a **coherent, well-tested, self-hosted IT-training platform**. Fresh runs confirm the
substance of the project's self-reported status rather than contradicting it: the backend suite is
**555 green** (up from 283), the service-desk-app monorepo passes its full production gate with **322
green tests** and — verified for the first time against a real registry — **zero dependency
vulnerabilities**, migrations apply cleanly from an empty database to head `0061`, and seeds create no
duplicates on re-run. Live production is exactly what `docs/DEPLOYMENT.md` describes (systemd + SQLite +
nginx container + Cloudflare tunnel); the "Render" language survives only in the *prior review* and old
loop-log entries.

The Service Desk / Nexus JWT integration that was flag-gated and unverified in July is now **wired in
production infrastructure**: shared `JWT_SECRET_KEY`/HS256, matching token claims on both sides, nginx
`auth_request` gating, `NEXUS_INTEGRATION=1` on the container, and `/service-desk/api/health` answering
`200` at the edge. What this review could **not** do is the authenticated student click-through with
screenshots — so NB-5 is *closer* but not formally closed.

The findings that matter are **operational, not defects in the code**:

1. **Host automation is committing snapshot commits and checking out feature branches directly in the
   live production working directory** — the exact thing `DEPLOYMENT.md`'s "hard invariant" forbids. The
   deployed `HEAD` moved from `8ea625a` to `44b7723` *during this review*, and nginx was reloaded
   mid-review (its CSP gained the Sentry origin). (P1-1)
2. **The production host root filesystem is at 94% (3.8 GB free)** while carrying the live SQLite writer,
   Docker, a second staging stack, and local backups. (P2-1)

Everything the prior review flagged as P1 that was a *product* gap (admin monitoring, CI, Service Desk
end-to-end) is either done (CI is green on `main`) or unchanged (admin monitoring). **No P0. Two P1s,
both operational.**

---

# Architecture map (current — verified 2026-08-27)

React 18 + Vite SPA (`frontend/`) ↔ FastAPI + SQLAlchemy + Alembic (`backend/`) over JSON, **SQLite** in
prod. Split auth: student signed-JWT `student_session` HttpOnly cookie (claims `sub`, `name`, `email`,
`is_mentor`, `exp`); admin separate expiring random server-side session (`verify_admin` /
`has_valid_admin_session`).

| Item | Prior (2026-07-23) | Now (2026-08-27) | Source |
|---|---|---|---|
| Routers | 28 | **30** (all mounted in `app/main.py`) | `ls app/routers/*.py` |
| Models | 30 | **30** | `ls app/models/*.py` |
| Services | 37 | **48** | `ls app/services/*.py` |
| Alembic migration files | 47 | **77** | `ls alembic/versions/*.py` |
| Alembic head | `0035` | **`0061_integrated_support_prove`** (single head) | `alembic current` |
| DB tables | 55 | **57** (fresh build) / same live | `sqlite_master` |
| Backend tests | 238 + 45 sec | **555** total | `pytest -q` |
| service-desk-app tests | n/a | **322** (shared 37 / sim-engine 182 / ui 29 / web 74) | `pnpm -r test` |
| Curriculum (canonical) | 25 wk / 296 act | **35 weeks (0–34) / 320 activities** (141 required, 179 optional); 35 modules, 79 lessons, 38 quizzes, 259 questions, 48 legacy tickets, 25 SD scenarios, 137 videos, 4 capstones, 38 guided labs, 11 networking labs | 2× seed on temp DB |

**Middleware / edge:** CORS + origin-based CSRF + security-header middleware in `app/main.py`
(`_SECURITY_CSP`, HSTS, `X-Content-Type-Options`); **authoritative CSP is served by nginx**
(`nginx.host.conf` `add_header Content-Security-Policy … always`) and is stricter/updated relative to the
app constant. Cloudflare tunnel terminates TLS.

**Service Desk (Next.js monorepo, `service-desk-app/`):** pnpm workspace, `apps/{web,api}` +
`packages/{database,shared,simulation-engine,ui}`, Turbo. Deployed as `nexus-service-desk` container,
base-path `/service-desk`, `NEXUS_INTEGRATION=1`.

**Candidate "dead" services — actually wired (overturns a prior-discussion assumption):**
`proxmox_service` and `guacamole_service` are imported by `app/routers/admin_content.py` and
`app/routers/labs.py`; `evidence_validator` by `app/routers/evidence.py`; `discord_service` by
`app/services/xp_service.py`. Only `vm_orchestrator` (if present) had no importer. Not dead code.

---

# Findings

Evidence column cites file:line, command output, or live probe. Nothing carried forward unverified.

## P0 — immediate security / data-loss / production-failure
**None found.** The Priority-0 investigations (leaked creds, hosting mismatch, schema drift) all came
back clean or already-resolved.

## P1 — serious risk or major blocker

| # | Finding | Evidence | Impact |
|---|---|---|---|
| **P1-1** | **Live production working directory is being mutated by automation** — `git reflog` shows `checkout: moving from main to feature/sentry-student-bug-reporting`, back to detached, `commit: Nightly snapshot 2026-08-26`, then `checkout: moving from 8ea625a → 44b7723` **during this review**. `git status` shows `tasks/loop-log.md` modified in the live tree. `docs/DEPLOYMENT.md` explicitly calls "never checkout a dev/review branch in the production WorkingDirectory" a *hard invariant*. | `git reflog -8`; `git status -b --porcelain=2`; `systemctl cat nexus-admin-academy.service` (`WorkingDirectory=…/nexus-admin-academy/backend`) | A feature branch or dirty tree can be what uvicorn imports on its next `Restart=on-failure`. Deploys are happening without the `DEPLOYMENT.md` pre-flight (backup → tests → review). Not caused by this review — all review git ops were in an isolated `/tmp` clone. |
| **P1-2** | **nginx config reloaded / frontend redeployed mid-review, unattended.** At review start `curl https://nexus.builtfromzero.fyi/` returned CSP `connect-src 'self'`; ~30 min later the same probe returned `connect-src 'self' https://o4511978744840192.ingest.us.sentry.io; worker-src 'self' blob:`. The deployed `HEAD` also advanced to include the Sentry commits (`89ad712`, merge `44b7723`). | two `curl -D -` captures of `/`; `docker exec nexus-frontend grep Content-Security-Policy /etc/nginx/conf.d/default.conf`; `git show -s 89ad712 44b7723` | Confirms P1-1 in a second dimension: production is a moving target with no change window. Sentry (`initSentry()` in `frontend/src/main.jsx`) now *can* reach its ingest origin — good — but the change shipped silently. |
| **P1-3** | **Shared `JWT_SECRET_KEY` is a 62-hex-char (~248-bit) value and lives only in host env / container env.** It signs *all* student sessions and is consumed by both the FastAPI backend and the `nexus-service-desk` container. Visible via `docker inspect nexus-service-desk`. Not committed (compose uses `${JWT_SECRET_KEY}` interpolation), so this is not a repo leak — but rotation logs everyone out and there is no documented rotation path, and the length is just under the "≥ 32 bytes" the test suite assumes. | `docker inspect nexus-service-desk --format '{{.Config.Env}}'`; `git show HEAD:docker-compose.yml` (interpolated, not hardcoded); `backend/tests/conftest.py:3` (`"…at-least-32-bytes"`) | Single secret, two processes, no rotation runbook. Lengthen to ≥ 64 hex on the next planned logout-tolerant window and document rotation in `AUTHORING_CONFIG_SECURITY.md`. |
| **P1-4** | **Service Desk student-side still not validated end-to-end (prior NB-5).** The integration path now demonstrably *exists* — token claims in `backend/app/routers/auth.py:28-31` (`sub`,`name`,`email`,`is_mentor`) exactly match `service-desk-app/apps/web/lib/nexus-auth.ts` `isStudentPayload()`; nginx proxies `/service-desk*` behind an `auth_request` to `/auth/me`; `NEXUS_INTEGRATION=1`, `NEXUS_ADMIN_CHECK_URL`, shared `JWT_ALGORITHM=HS256` on the container; `/service-desk/api/health` → `200` live; `/service-desk` → `307 /login?next=/service-desk` when unauthenticated. **But** no authenticated login → open ticket → tool panels → close → grade → refresh-persist run was performed (no browser tooling here; needs prod creds). | source diff both repos; `docker inspect nexus-service-desk`; `docker exec nexus-frontend cat …/default.conf`; live `curl` of `/service-desk`, `/service-desk/api/health`, `/service-desk/api/session` | Cannot certify the student loop works in prod. This is the one Priority-1 item from the brief that remains genuinely open; it needs a manual or Playwright click-through from a browser-capable environment with a seeded student account. |

## P2 — important usability / maintainability / operational

| # | Finding | Evidence |
|---|---|---|
| **P2-1** | Host root FS at **94% used, 3.8 GB free**, carrying the live SQLite writer, Docker, the `nexus-staging-*` stack (postgres + 3 containers, up weeks), and `~/backups/nexus/`. `/tmp` is a 3.7 GB tmpfs with 1.3 GB free. A full disk stalls SQLite writes and journald. | `df -h /` , `df -h /tmp`, `docker ps` |
| **P2-2** | **Duplicate / conflicting CSP headers on proxied endpoints.** `curl -D - https://nexus.builtfromzero.fyi/health` returns **two** `content-security-policy` headers — one from the FastAPI middleware (`connect-src 'self'`) and one from nginx (with the Sentry origin + `worker-src`). Browsers enforce the intersection. Prior review NB-25 ("header de-dup"), still open. | `curl -sS -D - -o /dev/null https://nexus.builtfromzero.fyi/health` |
| **P2-3** | Backend `_SECURITY_CSP` (`app/main.py:96`) is now a **stale duplicate** of the authoritative nginx CSP (missing the Sentry `connect-src` and `worker-src` that nginx has). Two places define "the CSP"; only nginx's is real for browser traffic. Collapse to one source of truth. | `app/main.py:96-101` vs `docker exec nexus-frontend grep -n Content-Security-Policy …/default.conf` |
| **P2-4** | **No application-layer login rate limiting.** `app/services/rate_limiter.py` throttles only AI endpoints and is keyed by authenticated `user_id`. Live `POST /auth/login` with bad creds → `401`, no `Retry-After` / `RateLimit-*`. Cloudflare is the only brake. Prior review NB-6, still open. | `grep -n rate_limiter app/services/rate_limiter.py:12,65-86`; live `curl -X POST …/auth/login` |
| **P2-5** | **Three stacked systemd drop-ins** (`99-service-desk-admin.conf`, `override.conf`, `zz-service-desk-admin.conf`) all set the same two `SERVICE_DESK_LAB_*` env vars, `99-` disagreeing with the other two. Final state is consistent (`…ADMIN_ENABLED=false`, `…LAB_ENABLED=false`) but the layering is a foot-gun. Collapse to one drop-in. | `systemctl cat nexus-admin-academy.service` |
| **P2-6** | `Nexus dupe/` directory tracked at repo root — 3 stale Playwright deployment screenshots (`deployment-step-3-*.png/html`). Plus stale `../Nexus dupe` path references noted in `AGENTS.md` / `tasks/loop-log.md`. Remove the directory and the refs. | `git ls-files 'Nexus dupe/'` (3 files); observation S2852 |
| **P2-7** | Seeds are duplicate-safe but **not a clean no-op on re-run**: second `seed_curriculum.py` still reports `Video requirements: updated: 23`, `Weeks 3-6 … updated_activities: 11`, `Weeks 15-18 … updated_activities: 5`, etc. Creation is correctly guarded (`already_applied`, `configuration_exists`, `created: 0`); the repeated UPDATEs are idempotent but make "did the seed change anything?" unanswerable from the log. | `seed.py`/`seed_curriculum.py` run twice on temp DB; row counts identical, `0` duplicate `seed_key`/title/week |
| **P2-8** | Prior review's structural-debt items are **unaddressed**: no per-student admin monitoring (NB-3); duplicated progress/XP/mastery logic (NB-10); overlapping admin content editors (NB-11); `training_service.py` / `students.py` still oversized. Not re-verified line-by-line this pass — flagged as still-open per unchanged file shapes and no corresponding commits. | prior review §14; `wc -l app/services/training_service.py app/routers/students.py` |

## P3 — useful improvement

| # | Finding | Evidence |
|---|---|---|
| **P3-1** | Root `.gitignore` ignores only `artifacts/e2e-launch-verification/`, not a blanket `artifacts/` or `website-capture/`. Add both to be safe against re-created capture trees. | `.gitignore` |
| **P3-2** | Archive `docs/PRODUCTION_STATE_2026-07-25_schema_ahead_of_code.md` (resolved — see P0.3); as written it reads as a live warning. | doc body: "this file can be archived" |
| **P3-3** | `alembic heads` / `upgrade` need `PYTHONPATH=.` because `alembic/versions/0043_retire_legacy_tickets.py` imports `app.services…` at module load. Add `prepend_sys_path = .` to `alembic.ini`. | `./.venv/bin/alembic heads` → `ModuleNotFoundError: No module named 'app'` |
| **P3-4** | Fix the prior review's "Render" language in `NEXUS_FULL_PROJECT_REVIEW.md` §2/§4/§18 (or add a header note that it is superseded by this document). | that file |
| **P3-5** | `turbo.json` `test` tasks emit `no output files found` warnings for `api`, `shared`, `simulation-engine`, `ui`, `web` — set `outputs: []` on the `test` task to silence. | `pnpm test` output |
| **P3-6** | CI had two recent red merges on `main` that self-healed (`sentry-student-bug-reporting` merge `33013380468` failure, Phase 4C.3 merge `32946968403` failure). Current `main` (`44b7723`) run `33084046494` is green. Consider blocking merges on red rather than merging then fixing forward. | `gh run list --branch main` |

## Prior-review items — current status

| Prior | Was | Now |
|---|---|---|
| P1-1 NB-1 lesson `outcomes` never rendered | open | not re-checked this pass |
| P1-2 NB-2 `/service-desk` 404 noise | open | superseded — SD is now served (307→login), not 404; not re-verified in browser |
| P1-3 NB-3 admin per-student monitoring | open | **still open** (P2-8) |
| P1-4 NB-4 no CI | open | **done** — `.github/workflows/ci.yml` runs on every push/PR; `main` green |
| P1-5 NB-5 SD student-side E2E | open | **still open** (P1-4) — infra path now verified to exist |
| NB-6 login rate limit | open | **still open** (P2-4) |
| NB-25 CSP header de-dup | open | **still open** (P2-2/P2-3) |
| "backend on Render" | assumed | **wrong** — self-hosted (P0.2) |

---

# Roadmap

### Now — operational hygiene (before any further feature work)
- **P1-1 / P1-2:** stop mutating the production working directory. Give the systemd unit a dedicated
  read-only deploy checkout (or a tag it never leaves), move "nightly snapshot" commits and any
  branch experimentation to a `git worktree`, and gate frontend/nginx changes behind the
  `DEPLOYMENT.md` pre-flight (backup → tests → review → reload).
- **P2-1:** reclaim disk — tear down the `nexus-staging-*` stack if it is not actively needed, prune
  Docker images (`nexus-service-desk:331efc…` and friends), and confirm `~/backups/nexus/` retention
  is enforced. Target < 80% on `/`.
- **P3-2 / P3-4:** archive the schema-ahead doc; annotate the July review as superseded.

### Next — close the one real Priority-1 gap
- **P1-4 (NB-5):** authenticated Service Desk click-through from a browser-capable environment with a
  seeded student — login → `/service-desk` hydrates identity → open a ticket → reveal hints → exercise
  Directory + Remote Desktop + Company Chat → close → grade shows → refresh persists. Screenshot each
  step. Only then mark NB-5 closed and Phase 1B unblocked.
- **P1-3:** plan `JWT_SECRET_KEY` rotation (lengthen to ≥ 64 hex, document the procedure, schedule a
  logout-tolerant window).

### Then — maintainability
- **P2-2 / P2-3:** one CSP, defined once (nginx), remove the app-layer duplicate; add a test that the
  live header set has no duplicates.
- **P2-5:** collapse the three systemd drop-ins into one.
- **P2-6:** delete `Nexus dupe/` and its stale references.
- **P2-8:** resume the prior review's structural-debt track — admin monitoring first (highest program
  value), then progress/XP/mastery consolidation.

### Unchanged guidance from July
No rewrite. Resist premature expansion (VMs, Postgres, AI scope) until a concrete trigger. The
platform's strength is still its focused simplicity, and the test posture (555 + 322 green, 0 audit
findings, clean migrations, duplicate-safe seeds) is genuinely strong.

---

## Appendix — raw verification output (abridged)

```
# backend suite (clean venv, in-memory sqlite)
555 passed, 9 warnings in 142.63s (0:02:22)   exit 0

# migrations from empty (isolated clone, temp sqlite)
alembic upgrade head → 0061_integrated_support_prove (head)
tables: 57   integrity: ('ok',)   foreign_key_check rows: 0

# seed idempotency (temp DB, run x2)
run1 counts == run2 counts (modules 35, lessons 79, quizzes 38, questions 259,
  tickets 48, training_weeks 35, week_activities 320, sd_scenarios 25)
dup seed_key questions: 0   dup module titles: 0   dup week_number: 0

# service-desk-app (fresh pnpm install --frozen-lockfile, isolated clone)
lint      → 5 successful, 5 total          rc=0
typecheck → 10 successful, 10 total        rc=0
test      → shared 37 | sim-engine 182 | ui 29 | web 74  = 322 passed   rc=0
build     → 5 successful, 5 total (21 static pages)       rc=0
pnpm audit --prod  → No known vulnerabilities found      rc=0
pnpm audit (all)   → No known vulnerabilities found      rc=0

# live edge
GET  https://nexus.builtfromzero.fyi/health            → 200 {"success":true,…}
GET  https://nexus.builtfromzero.fyi/service-desk      → 307 /login?next=/service-desk
GET  https://nexus.builtfromzero.fyi/service-desk/api/health → 200 {"status":"ok"}
POST https://nexus.builtfromzero.fyi/auth/login (bad)  → 401  (no Set-Cookie, no RateLimit-*)
resp headers: HSTS max-age=63072000; includeSubDomains · CSP (nginx) strict + sentry ingest ·
              X-Content-Type-Options nosniff · Referrer-Policy strict-origin-when-cross-origin ·
              Permissions-Policy geolocation=(),camera=(),microphone=() · server: cloudflare

# git history forensics
git log --all --full-history -- '*.har' '*sanitized*' '*firestore*' '*website-capture*' \
  '*crawlee*' '*browsertrix*' 'service-desk-app/artifacts/*'  → (empty, all patterns)
```
