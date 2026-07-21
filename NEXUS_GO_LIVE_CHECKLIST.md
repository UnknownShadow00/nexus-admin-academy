# NEXUS GO-LIVE CHECKLIST — Day-by-Day

Format: small confirmatory steps. Each ☐ has a **VERIFY** line — paste that
output back to Claude/Claude Code if anything looks off before moving on.
Don't skip verifies; they're the difference between "deployed" and "hoping."

## CURRENT RELEASE CHECKPOINT — 2026-07-19

The manual-cohort release checks pass (`154 passed`, Alembic `0028`, zero npm
vulnerabilities, successful frontend and networking CLI builds), and the
release candidate is deployed on `.101`:

- the remote Ollama model is reachable, calibrated, and live ticket grading passes;
- `POST /api/admin/students`, login, supported deletion, and ID reuse pass after
  the controlled five-row orphan repair;
- SQLite application connections enforce foreign keys and both integrity checks
  are clean;
- all additional curriculum records are inventoried read-only in
  `docs/PRODUCTION_CONTENT_INVENTORY.md`;
- automated labs remain disabled (zero published automated templates, incomplete
  Proxmox/Guacamole configuration).

The repair backup is under `/home/nexus/backups/nexus-launch-fix-20260719T100246Z/`.
The project is ready for the manual-VM cohort; do not publish automated VM labs
until their separate real-infrastructure acceptance test passes.

## FINAL QUIZ-PROTECTION LIVE VERIFICATION — 2026-07-20 UTC

- `nexus-admin-academy.service` was restarted by an authorized operator and is
  active. `http://127.0.0.1/health` returned HTTP 200 both before and after
  the live smoke test.
- The current restart log shows a clean application startup with no startup,
  migration, database, or import errors.
- A disposable student confirmed a validated required Week 3 quiz in Required
  and a validated optional Week 3 quiz in Practice. The required quiz changed
  from `available` to `done` after a correct submission and recorded mastery.
  The optional quiz submitted successfully, left the required quiz
  `available`, and created no mastery row.
- An unvalidated Week 3 quiz was absent from This Week, All Weeks, Practice,
  Remediation, and Certification Library student surfaces. Its direct detail
  and submission requests both returned HTTP 404.
- Admin editorial review returned HTTP 200, contained that quiz, and reported
  all 76 pending quizzes.
- The disposable account was deleted through the supported admin endpoint;
  the readback found zero owned attempts, progress, or related rows. SQLite
  `integrity_check` returned `ok` and `foreign_key_check` returned no rows.

**Status:** Ready for manual-VM cohort. No quiz-content review, scenario
authoring, or automated-VM work was performed in this verification.

---

## DAY 1 — Deploy the new repo to .101 (nexus-services)

**Goal: the complete 24-week build running against your real database.**

☐ 1. Back up the current state first:
```bash
# on .101
cd /opt/apps/"IT TRAINING PROJECT CODE"/projects
cp -r nexus-admin-academy nexus-admin-academy.bak-$(date +%F)
pg_dump "$DATABASE_URL" > ~/nexus-pre-24wk-$(date +%F).sql   # if Postgres; skip for fresh DB
```
**VERIFY:** `ls -d nexus-admin-academy.bak-*` shows the backup folder.

☐ 2. Unzip `nexus-complete-24-weeks.zip` over the project (or into a fresh
folder and swap — your call, backup exists either way).
**VERIFY:** `ls backend/seed_phase_g.py` exists — that file only exists in the
new build.

☐ 3. Backend deps + env:
```bash
cd backend
pip install -r requirements.txt --break-system-packages
# .env must have: DATABASE_URL, JWT_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_API_KEY
# Do NOT set AI_* yet — the app boots fine without them (that's tested).
```
**VERIFY:** `python -c "from app.main import app; print('boots')"` prints `boots`.

☐ 4. Migrate + seed:
```bash
alembic upgrade head
python scripts/seed_users.py
python seed.py
python seed_curriculum.py
```
**VERIFY:** the seed summary line ends with
`phase_g={'modules': 2, 'lessons': 3, ...}` and no traceback.
Run `python seed.py` a SECOND time — counts should show 0 new
modules/tickets (idempotency proof).
**VERIFY:** `seed_curriculum.py` prints `Curriculum seeded successfully` and
`SELECT COUNT(*) FROM curriculum_videos` is non-zero (fresh-install proof: 62) —
Study Tracker shows nothing without this step.

☐ 5. Test suite on the real box:
```bash
python -m pytest tests/ -q
```
**VERIFY:** `151 passed, 0 failed` (verified 2026-07-19). Anything else → stop and investigate the exact failure.

☐ 6. Frontend build + serve:
```bash
cd ../frontend && npm ci && npm run build
```
**VERIFY:** `✓ built` with no errors (chunk-size warning is fine/known).

☐ 7. Restart your services (docker compose / systemd — however you run it).
**VERIFY:** log into the web UI as admin; you can see modules MOD-000 → MOD-024.

**Day 1 done when:** admin login works, 25 modules are visible, all 151 current tests are green, and Alembic reports `0028 (head)`.

---

## DAY 2 — Finish GPU passthrough on VM 200 (AI-VM, .104)

**Goal: the RTX 5090 visible inside Ubuntu on VM 200.**
You were interrupted mid-start last time — resume exactly here.

⚠ **STANDING RULE: never `sudo reboot` inside VM 200. Always `qm stop 200`
then `qm start 200` from the Proxmox host.** (5090 has no FLR reset.)

☐ 1. From the Proxmox host, clean start:
```bash
qm stop 200
qm status 200        # wait for: stopped
qm start 200
```
**VERIFY:** `qm status 200` → `running`, and it STAYS running for 2+ minutes
(watch `journalctl -f` on the host for vfio errors). Last session it may have
already been working when Ctrl+C hit — this confirms it.

☐ 2. If it stays up, SSH in and check the GPU:
```bash
lspci | grep -i nvidia
```
**VERIFY:** the 5090 (and its audio function) listed. If the VM dies instead:
paste the host `journalctl` tail + `qm config 200` back to Claude before
changing anything.

☐ 3. NVIDIA driver inside the VM:
```bash
sudo apt update && sudo apt install -y nvidia-driver-570   # or current recommended
# then FROM THE HOST: qm stop 200 && qm start 200
nvidia-smi
```
**VERIFY:** `nvidia-smi` shows the RTX 5090 with driver + CUDA version.

**Day 2 done when:** `nvidia-smi` works and survives a host-side stop/start cycle.

---

## DAY 3 — Ollama live + grader calibration

**Goal: AI grading trusted, not assumed.**

☐ 1. Install Ollama on VM 200 and pull your model:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:70b     # or your chosen model
```
**VERIFY:** `nvidia-smi` during a test prompt shows GPU memory in use
(proves it's not CPU-only).

☐ 2. Expose it on the LAN (systemd override: `OLLAMA_HOST=0.0.0.0`).
**VERIFY:** from .101:
`curl http://<vm200-ip>:11434/v1/models` returns JSON with your model.

☐ 3. Wire Nexus to it — on .101, add to backend `.env`:
```
AI_BASE_URL=http://<vm200-ip>:11434/v1
AI_MODEL=llama3.1:70b
```
(no AI_API_KEY needed for local Ollama). Restart the backend.

☐ 4. **RE-CALIBRATE after changing the model or grader prompt:**
```bash
cd backend && python scripts/calibrate_grader.py
```
**VERIFY:** all five fixtures print `OK` and it says `Calibration PASSED`.
- strong → 8-10, weak → ≤5, incomplete → verification ≤1, unsafe → ≤4,
  **malicious → ≤3** (the injection test — this one matters most).
- `NEEDS TUNING` → try a different model size or paste the scores back to
  Claude for a prompt adjustment. **Do not put students on AI grading until
  this passes.**

**Day 3 done when:** calibration PASSED, printed output saved into loop-log.

---

## DAY 4 — End-to-end smoke test as a student

**Goal: walk the actual student path before any student does.**

☐ 1. Log in as a test student account (from seed_users).
**VERIFY:** "This Week" panel shows Week 1 with lessons/quiz/labs/tickets.

☐ 2. Read a lesson, submit lesson notes.
**VERIFY:** the lesson flips to done on the week panel.

☐ 3. Take the "Ticket Writing Fundamentals" quiz — deliberately retake it.
**VERIFY:** both attempts appear in history; best score kept; XP only from
attempt one.

☐ 3a. Verify quiz organization with a disposable student: the required quiz appears in **Required This Week**, optional practice appears in **Practice This Week**, remediation is hidden until assigned/triggered, and certification banks appear only in the optional certification library. Confirm an incomplete required quiz blocks the week while optional/certification attempts do not.

☐ 4. Open the DNS ticket, reveal ONE hint.
**VERIFY:** cost was shown BEFORE reveal; hint text has your student-specific
values substituted (no `{{PLACEHOLDER}}` visible).

☐ 5. Submit a real writeup on that ticket (write a decent one).
**VERIFY:** AI grading returns anchors + feedback in ~seconds; score is sane
for what you wrote. Then check the admin review queue shows it.

☐ 6. As admin: leave a flag on the submission, check the student's promotion
status shows the gate blocked; resolve the flag, status clears.
**VERIFY:** gate requirement flips as expected.

☐ 7. Evidence upload: try a >10MB file (should 413) and a normal screenshot
(should attach).

**Day 4 done when:** the full loop — lesson → quiz → hint → ticket → AI grade
→ mentor review → gate math — works with your hands on it.

---

## DAY 5 — Cohort prep + launch

☐ 1. Create/verify the 5 real student accounts; delete/disable any test ones.
☐ 2. Skim `docs/STUDENT_GUIDE.md` and `docs/MENTOR_GUIDE.md` — they're the
day-one handouts. Adjust anything that doesn't match your setup.
☐ 3. Post the Student Guide + login info to the Discord.
☐ 4. Schedule the Week-1 kickoff call (guide's day-one talking points:
tickets are the product, escalation is a win, verification is mandatory,
hints cost XP, tickets are individually parametrized).
☐ 5. Backups: confirm `scripts/backup_sqlite.sh` runs nightly and both its
SQLite online backup and uploads copy are present. (`scripts/backup_db.sh` is
only for an intentional Docker/PostgreSQL deployment.)
**VERIFY:** restore one table from last night's dump to a scratch DB — the
Week-17 lesson applies to you too: an untested backup is a hope.
☐ 6. Update loop-log.md: deployment date, calibration results, launch date.

**Day 5 done when:** students have credentials, kickoff is scheduled, backups
are proven restorable.

---

## SECURITY REVIEW CHECKPOINT — 2026-07-21

An external Deep Research report was reconciled against current code and the
live deployment (`docs/DEEP_RESEARCH_FINDINGS_RECONCILIATION.md`,
`docs/SECURITY_ROUTE_AUTHORIZATION_AUDIT.md`,
`docs/SECURITY_HEADERS_AND_SESSION_REVIEW.md`). Its three critical/high
findings (Guacamole admin-token exposure, bearer-bypass, deterministic admin
session) were already fixed before this review — all confirmed and
regression-tested. Route-by-route authorization across all ~20 routers is
clean; no foreign-resource-ID route was found skipping an ownership check.

Fixed during this review (code-complete on `.101`'s working tree, **not yet
deployed**): cookies tightened to `SameSite=Lax`, a new Origin/Referer CSRF
middleware, security response headers (CSP/HSTS/nosniff/Referrer-Policy/
Permissions-Policy/no-store) added to both the FastAPI backend and both nginx
configs, an unbounded-file-read fix on the ticket screenshot upload route, and
`GET /api/students` trimmed to `id`/`name` only (email/`last_active_at`
removed — admins keep email access via the existing admin-only overview
endpoint). Backend suite: **176 passed, 0 failed**, `python -m py_compile`
clean, `alembic current` at `0029 (head)`, live and backup SQLite both pass
integrity + foreign-key checks, frontend `npm run build` and `npm audit`
(0 vulnerabilities) both clean.

The prior 2 failing tests (`test_username_case.py`) were caused by an
uncommitted temporary "Claude" entry in `seed_users.py`'s `ACCOUNTS` list —
reverted (code only; the live DB row and `.env` were not touched).

- [x] **Deployed 2026-07-21** — backend restarted (`kill -KILL $MAINPID`,
  `Restart=on-failure`, since interactive `sudo` is unavailable here), health
  200 before/after, clean startup logs. Frontend rebuilt and redeployed to the
  `nexus-frontend` container (`docker cp` + `nginx -s reload`, `nginx -t`
  passed first). 41/41 live smoke-test checks passed.
- [x] **Temporary review-account cleanup done** — live "Claude" account
  (id 8, zero owned rows) removed via the supported deletion workflow;
  `SEED_PASSWORD_CLAUDE` removed from `.env`; `ADMIN_USERNAME` (found to
  literally be the temporary `codex` value) replaced with the real mentor
  credentials by the operator. Verified: 7 real accounts remain, zero orphans,
  integrity `ok`, zero FK violations, live admin login round-trip succeeds.
☐ **Cloudflare dashboard:** enable "Always Use HTTPS" on `builtfromzero.fyi` —
confirmed still not enabled post-deploy; plain `http://` serves `200` with no
redirect. Dashboard-only, no code lever exists. See
`docs/DEEP_RESEARCH_FINDINGS_RECONCILIATION.md` for exact steps.
☐ **Minor follow-up (not blocking):** nginx's new security headers are set at
the `server` block level, so proxied backend paths get duplicate (identical)
headers from both nginx and FastAPI — cosmetic only, scope `add_header` to
`location /`/`location /assets/` when convenient.

**Not launch-blocking:** the residual ExamCompass CORS/credentials note, the
public (UUID-obscured) evidence file mount, and the `verified_by=0` audit-trail
gap — all documented, none exploitable in a way that changes the "ready for
manual-VM cohort" status.

---

## PRE-WEEK-0 LAUNCH READINESS SPRINT — 2026-07-21

Full detail: `docs/reviews/PRE_WEEK_ZERO_IMPLEMENTATION_REPORT.md`,
`docs/reviews/PRE_WEEK_ZERO_BROWSER_ACCEPTANCE.md`,
`docs/reviews/PRE_WEEK_ZERO_FINAL_READINESS.md`.

- [x] A+ Study Tracker gate (the sprint's P0) replaced with week-based
  prerequisite gating; no longer blocks any hands-on work.
- [x] Week 0 platform onboarding added, including a bug found and fixed
  during live testing where the onboarding "complete" state didn't agree
  with the real Week 1 unlock gate.
- [x] Capstone role-gate data fixed (all 3 templates were `NULL`, open to
  everyone; now correctly role-gated).
- [x] Mentor activity filtered from the student squad feed.
- [x] Two of the original review's findings (LESSON-001, QUIZ-001) were
  reconciled and found not to hold — corrected in `NEXUS_FINDINGS.csv` and
  the relevant detail docs, not silently dropped.
- [x] Full verification: 188/188 backend tests, Alembic head `0031`, DB
  integrity/FK clean, `npm audit` 0 vulnerabilities, `npm run build` clean.
- ☐ **No rendered-browser check was possible in this sandbox** (unsupported
  Chromium build for this Ubuntu version, no system browser, sandbox blocks
  localhost binding). Do a quick desktop + ~375px mobile click-through on
  the live/staging site after deploying this sprint's changes, covering:
  Home welcome banner, Week Plan panel, orientation practice panel, and
  locked-state banners.
- ☐ **Deploy not yet executed** — pending explicit go-ahead. Once approved,
  follow the existing deploy procedure (fresh timestamped backup first,
  backend restart via `kill -KILL $MAINPID`, frontend rebuild + `docker cp`
  to `nexus-frontend`, live re-verify, remove the disposable review account,
  confirm the 6 real students unchanged, tag the release).

---

## PARKED (do not block launch on these)
- The 60 proposed scenario-based quiz gap questions; do not create them until the quiz placement/results plan is reviewed after launch readiness.
- Proxmox/Guacamole AUTO-VM infrastructure acceptance — application P0s are
  fixed, but manual-VM paths remain the launch default until a real isolated
  start/connect/refresh/expiry/destroy smoke test passes.
- learn-routing CLI engine — Packet Tracer fallback stands for Week 11.
- Interactive Ollama-roleplay tickets, Ludus break-fix pipeline, monthly
  research pipeline — post-launch enhancements.
- Frontend lint/E2E harness — new scope, only if it starts hurting.
