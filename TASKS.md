
## Pre-Week-0 Launch Readiness Sprint (2026-07-21)

Fixed the P0/P1 findings below before the five real students begin. Full
detail: `docs/reviews/PRE_WEEK_ZERO_IMPLEMENTATION_REPORT.md`,
`docs/reviews/PRE_WEEK_ZERO_BROWSER_ACCEPTANCE.md`,
`docs/reviews/PRE_WEEK_ZERO_FINAL_READINESS.md`.

- [x] **A+ gate replaced** with week-based prerequisite gating
  (`require_week_reached`, reusing existing week-derivation logic). Optional
  A+ video progress no longer blocks any hands-on work. Structured 403s,
  `PrerequisiteLock` UI component, tests in `test_week_prerequisite_gating.py`.
- [x] **Week 0 onboarding added**: new "Welcome to Nexus" lesson + guided
  zero-stakes practice walkthrough (`onboarding_service.py`, `onboarding.py`,
  `OrientationPracticePanel.jsx`). Fixed a bug found during live testing
  where completing onboarding claimed Week 1 readiness the real gate didn't
  agree with (`week_one_unlocked` field now reconciles the two).
- [x] **Capstone role-gate fixed** — 3 live templates now have correct
  `role_level` (Support Technician I/II, Junior Systems Technician) instead
  of `NULL`.
- [x] **MOD-001 false-lock fixed** — cosmetic-only Learning Path lock caused
  by an unsatisfiable `MOD-000` mastery prerequisite; nulled via migration.
  (LESSON-001's original "0 lessons" premise was found false during
  reconciliation — no new lesson was needed there.)
- [x] **Mentor activity filtered from student squad feed** (role-based
  filter, both roster and activity queries).
- [x] **Quiz visibility reconciled** — QUIZ-001's original finding
  (unvalidated quizzes visible/attemptable) was found false; live testing
  confirmed the existing filter already excludes them everywhere.
- [x] **Admin onboarding visibility added** to the existing student-activity
  admin endpoint.
- [x] Findings inventory normalized (`NEXUS_FINDINGS.csv`: 44 primary + 4
  alias rows); account-count reconciled (7 total: 1 mentor + 6 students).
- [x] Full verification: 188/188 backend tests, Alembic head `0031`, DB
  integrity/FK clean, `npm audit` 0 vulnerabilities, `npm run build` clean.
  No rendered-browser check was possible in this sandbox (see acceptance
  doc) — recommend a human click-through on desktop/mobile after deploy.
- [ ] **Phase 11 deploy** — not yet executed; pending explicit go-ahead
  (production action on shared infrastructure). Once approved: backup,
  deploy, restart, live re-verify, remove the disposable review account,
  confirm the 6 real students unchanged, tag the release.

## Full platform review — beginner readiness, curriculum, technical (2026-07-21)

A 17-phase product/curriculum/UX/technical review, led by Claude with Codex
used for static system mapping and content extraction, plus live testing
(site walkthrough, admin actions, real ticket submission/grading, DB
verification) performed directly by Claude. Full detail in
`docs/reviews/NEXUS_FULL_REVIEW.md` and its 17 supporting documents;
prioritized fix sequencing in `docs/reviews/NEXUS_PRIORITIZED_ACTION_PLAN.md`;
per-area go/no-go in `docs/reviews/NEXUS_PUBLISH_READINESS.md`. **No
production code was changed as part of this review** — awaiting
project-owner approval of the action plan before any fix is implemented.

- [ ] **P0 — fix before Week 0:** the A+ Study Tracker 40%-unlock gate
  silently blocks all ticket/lab/capstone/CLI-lab actions for every student
  (confirmed live: a fresh 0%-progress student gets a 403 on their very
  first ticket submission) — contradicts Week 1's designed ticket
  assignments. See `NEXUS_TICKET_REVIEW.md` (TICKET-001) and
  `NEXUS_TECHNICAL_REVIEW.md` (TECH-001).
- [ ] **P1 — fix before Week 0:** no platform-onboarding content exists
  anywhere (ONBOARD-001); the capstone role-gate is a no-op because all 3
  live templates have `role_level = NULL` so Capstones is fully visible/
  usable at 0 XP (CUR-002); Week 1 has zero lessons despite two graded
  tickets (LESSON-001). See `NEXUS_WEEK_ZERO_REVIEW.md`,
  `NEXUS_BEGINNER_NAVIGATION_REVIEW.md`, `NEXUS_LESSON_REVIEW.md`.
- [ ] **P2/P3 — during Weeks 1-4 or after cohort start:** ~30 further
  findings (labs award no XP/no mentor gate, screenshot evidence has no
  content validation, Terminal Practice duplicates Command Library with a
  non-functional terminal widget, optional/certification quizzes with
  unvalidated answer keys are visible to students, accessibility gaps,
  mentor-workload reductions) — full list with severity/evidence/fix
  complexity in `docs/reviews/NEXUS_FINDINGS.csv`.
- [x] **Live re-verification of platform health (2026-07-21):** 176/176
  backend tests, Alembic head 0029, SQLite integrity/FK clean, npm audit 0
  vulnerabilities, clean frontend build, HTTPS redirect + security headers
  live, CSRF/rate-limiting confirmed via real rejected requests, full
  ticket-grading lifecycle (submit → AI grade → mentor reject/revise/verify
  → XP) live-tested end to end on a disposable account, disposable account
  and all owned rows fully removed afterward with zero orphans.
- [ ] **Automated Proxmox/Guacamole VM labs** — confirmed still correctly
  disabled; no action recommended until a real infrastructure smoke test
  passes (unchanged from prior status).

## Security review reconciliation (2026-07-21)

An external Deep Research report (written without repo/ZIP access or live
auth, from older handoff docs) was reconciled against current code and the
live `.101` deployment. Full detail: `docs/DEEP_RESEARCH_FINDINGS_RECONCILIATION.md`,
`docs/SECURITY_ROUTE_AUTHORIZATION_AUDIT.md`,
`docs/SECURITY_HEADERS_AND_SESSION_REVIEW.md`.

- [x] **Confirmed already fixed, pre-dating this review:** Guacamole admin-token
  exposure, `allow_admin_or_student` bearer bypass, deterministic admin
  session, client-only `AdminAccessGate`, evidence upload cap/ownership,
  SQLite FK enforcement + admin student-creation 500, synchronous VM
  provisioning. See reconciliation doc for evidence per item.
- [x] **Fixed during this review (code-complete, not yet deployed):** cookies
  tightened from `SameSite=None` to `SameSite=Lax`; new Origin/Referer CSRF
  middleware on cookie-authenticated state-changing routes; security response
  headers (CSP/HSTS/X-Content-Type-Options/Referrer-Policy/Permissions-Policy/
  Cache-Control) added in both FastAPI and nginx; unbounded file read fixed on
  `POST /api/tickets/uploads` (now bounded + 20MB aggregate cap). 10 new
  regression tests in `backend/tests/test_security_hardening.py`; full suite
  172 passed / 2 pre-existing unrelated failures (see below).
- [ ] **Deploy the above to `.101`** — requires a frontend rebuild/redeploy and
  a backend service restart. Not done as part of this review; needs an
  explicit go-ahead since it touches the live site.
- [ ] **Cloudflare dashboard: enable "Always Use HTTPS"** on the
  `builtfromzero.fyi` zone — plain `http://` currently serves `200` with no
  redirect. Not a code fix; dashboard-only.
- [x] **`GET /api/students` no longer returns email/`last_active_at`** — now
  returns only `id`/`name` (the only fields the ticket-collaborator picker
  reads). Admins still see email via the existing admin-only
  `/api/admin/students/overview`. Tests added.
- [x] **Test suite failures resolved** — the uncommitted temporary "Claude"
  entry in `backend/scripts/seed_users.py`'s `ACCOUNTS` list was reverted
  (code only). Full suite now **176 passed, 0 failed**.
- [x] **Temporary review-account cleanup complete (2026-07-21)** — live
  "Claude" student (id 8, zero owned rows) removed via the supported
  `DELETE /api/admin/students/{id}` workflow; `SEED_PASSWORD_CLAUDE` removed
  from `.env`; `ADMIN_USERNAME` (found to literally be the temporary `codex`
  value) replaced with the real mentor credentials by the operator. Verified:
  7 real cohort accounts remain, zero orphan rows, integrity `ok`, zero FK
  violations, live admin login round-trip succeeds with new credentials.
- [x] **Hardening changes deployed to `.101`** — backend restarted, frontend
  rebuilt and redeployed to the `nexus-frontend` container. 41/41 live smoke
  tests passed. See `docs/DEEP_RESEARCH_FINDINGS_RECONCILIATION.md`'s
  deployment record for full detail.
- [x] **Cloudflare dashboard: enable "Always Use HTTPS"** — confirmed live
  during the 2026-07-21 full platform review: `http://nexus.builtfromzero.fyi/`
  now returns `301` to the HTTPS origin. Resolved since the last deploy note.
- [ ] **Minor follow-up:** nginx's new security headers are set at the
  `server` block level, so proxied backend paths get them twice (once from
  nginx, once from FastAPI) — same values, no security impact, but untidy.
  Scope `add_header` to `location /`/`location /assets/` only.

## Production deployment checkpoint (2026-07-19)

The two manual-cohort launch blockers found during deployment verification are
resolved and re-tested on `.101`. The manual/automated VM feature boundary is
unchanged.

- [x] **Restore the remote Ollama connection and re-run ticket grading.** The
  configured endpoint referenced the retired AI host. The current remote host
  was already reachable and serving the configured model; Nexus was corrected,
  the five-fixture calibration passed, and a disposable ticket received live
  grading without installing or changing Ollama on `.101`.
- [x] **Repair legacy orphaned student references before onboarding.** A
  backup-backed, dry-run-first repair removed only five confirmed orphaned
  `student_methodology_progress` rows. SQLite application connections now
  enforce foreign keys; create/login/delete/ID-reuse tests pass and valid
  student progress retained the same digest.
- [x] **Inventory additional production content without changing it.** The
  79 additional quizzes, 778 questions, and 120 videos are recorded in
  `docs/PRODUCTION_CONTENT_INVENTORY.md` with source, linkage, activity,
  duplication, classification, and owner-review recommendations.
- [ ] **Run real automated-lab staging acceptance.** `.101` has neither complete
  Proxmox nor Guacamole configuration and publishes zero automated lab
  templates. Keep the five manual labs as the only student-visible VM path.

## A+ hands-on preview gate (2026-07-18)
DONE (verified and deployed on .101; see tasks/loop-log.md):
- [x] **Schema reality:** live `curriculum_videos` is at Alembic `0027` and has `exam_code` in addition to free-text `section`. The catalog has 108 `220-1201` rows and 74 `220-1202` rows (137 active), so A+ is grouped by those exam codes; there is no separate certification-family column.
- [x] **Enforcement reality before this change:** `check_module_unlock()` / `get_module_mastery()` were called only by the Learning Path response and did not gate Tickets, Labs, Networking Labs, Quizzes, or Capstones. Capstone `role_level` was separately enforced on list/detail/start; it was not module/mastery enforcement.
- [x] Database-backed setting `a_plus_unlock_threshold_pct` defaults to **40** and is read on every request (not statically cached). Admins can read it with `GET /api/admin/settings/a-plus-unlock` and change it without a deploy with `PATCH /api/admin/settings/a-plus-unlock`, JSON body `{"a_plus_unlock_threshold_pct": 50}`, using normal admin auth or `X-Admin-Key`.
- [x] Login and `/auth/me` expose `a_plus_progress_pct`, `a_plus_unlock_threshold_pct`, and `a_plus_unlocked`. Study Tracker watch/unwatch responses refresh the same fields so crossing the threshold updates the stored frontend profile without another request.
- [x] Below-threshold students retain list/detail preview access to Tickets, Labs, Networking Labs, and Capstones, while all state-changing actions (including hints, submissions/completions, starts, and uploads) return a progress-aware 403. Quizzes and Learning Path remain fully open.
- [x] Frontend list/detail pages show the real threshold/progress message linked to `/study-tracker` and hide or disable mutation controls until unlocked. Mentors bypass the gate. If the A+ catalog is empty, the gate deliberately fails open; an admin threshold change is server-immediate but an already-open SPA may need a reload to refresh its cached message/buttons.
- [x] Verification: 119 backend tests pass (115 existing + 4 A+ cases), frontend build + CLI validation/sanity pass, migration backup/integrity + fresh upgrade pass, live below-threshold cohort student receives four 403s while all four browse endpoints remain 200, threshold 0 makes the same student unlocked and the gate stops intercepting mutations (normal 404s on deliberately nonexistent targets), then live threshold restored to **40**.

## Nav restructure batch (2026-07-18, second session)
DONE (verified on .101, see tasks/loop-log.md):
- [x] Quizzes hidden from top nav (routes + all entry points intact — reachable via Study Tracker, Home cards, Learning Path)
- [x] Nav renames: Commands→Command Library, Terminal & Commands→Terminal Practice, CLI Labs→Networking Labs (+ on-page titles/back-links synced; routes/files unchanged)
- [x] Capstone unlock now real: `role_level` enforced server-side (list/404/403, mentor bypass, NULL=everyone) + `has_unlocked_capstones` on login+/auth/me (zero new round-trips) + nav tab hidden when false. All live capstones NULL → behavior unchanged until role_level set on a template. 115/115 tests.

## Codex-review fix batch + All Weeks feature (2026-07-18)
DONE (verified on .101, see tasks/loop-log.md):
- [x] Study Tracker 401-after-refresh — `allow_admin_or_student` now accepts the `student_session` cookie; reproduced live before fix, 200 after; 2 regression tests; 112/112 tests pass
- [x] `seed_curriculum.py` documented in README + go-live checklist (was a silent required step); fresh-DB proof: migrate+seed.py+seed_curriculum.py → 62 curriculum_videos, idempotent
- [x] COOKIE_SECURE actually enabled — was still `false` in .env (07-18 01:20 session set it false for http; HTTPS domain via Cloudflare tunnel now exists); flipped to true, service restarted, live Set-Cookie via https://nexus.builtfromzero.fyi shows `HttpOnly; SameSite=none; Secure`. NOTE: http:// LAN logins no longer persist the cookie — use the HTTPS domain.
- [x] SelectProfile.jsx deleted (dead code, fake student profiles); bundle clean, build passes
- [x] Test-count truth: current complete suite is 151 passing as of 2026-07-19; historical totals are retained only in dated loop-log entries
- [x] "All Weeks" view with per-week collapse/expand + Expand All/Collapse All on Tickets/Quizzes/Labs/Capstones pages (Codex-implemented, reviewed; CLI Labs & Learning Path have no week filter — out of scope); deployed to nginx container

## Go-live Day-1 + grader/smoke session update (2026-07-17)
DONE (verified on .101, see tasks/loop-log.md):
- [x] Day 1 of NEXUS_GO_LIVE_CHECKLIST.md — 24-week build deployed, fresh DB migrated+seeded, frontend built, service restarted, admin login + 25 modules verified; current suite is 151 passing
- [x] Real-AI grader calibration RUN against live Ollama (deepseek-r1:32b): **NEEDS TUNING** — strong=10 OK, weak=2 OK, unsafe=1 OK, malicious=1 OK, incomplete=6 (expected ≤5; its verification anchor correctly 0). One band miss; prompt/model tweak pending.
- [x] AI grader JSON parsing fixed: `extract_json_payload()` restored in ai_service (json_mode), `_strip_think_tags` belt-and-suspenders in ticket_grader — Ollama ignores `response_format: json_object`
- [x] Calibration script: 25s spacing between fixtures + self-reset of user-0 rate counters (8/day cap made re-runs impossible)
- [x] bcrypt pinned to 4.0.1 (passlib 1.7.4 incompatible with bcrypt≥4.1)
- [x] P0 "seed_students() phantom accounts" — REGRESSED in the 24-week pack's seed.py (shipped admin/admin123, alex/alex123... on every deploy); removed again, ghost rows purged, reseed verified clean
- [x] Quiz retake 500 fixed: `first_attempt_xp=None` vs NOT NULL DB column (migration 0002 vs model drift) — retakes write 0
- [x] NEW `PUT /api/admin/submissions/{id}/flag` + `/resolve-flag` — no endpoint could create the open-flag state `no_unresolved_flags` gates check for
- [x] Ticket submit response now includes `anchors`
- [x] Day-4 smoke test automated: `backend/scripts/day4_smoke_test.py` — **8/8 PASS** (login, week-plan, lesson→done, quiz retake/XP-once, hint cost+substitution, live AI grade 9/10, flag→gate block→resolve, evidence 413/200); smoke residue purged from DB

RESOLVED later same day (2026-07-17, see loop-log):
- [x] Grader calibration — verification-anchor-0 hard cap added to ticket_grader.py (unverified fix now caps final ≤5); re-run vs live deepseek-r1:32b: **Calibration PASSED (5/5 fixtures)**
- [x] Frontend now served on .101 — `nexus-frontend` nginx container on :80 (dist copied into container, API proxied to :8000; config: `frontend/nginx.host.conf`)
- [x] Nightly SQLite + uploads backup — `scripts/backup_sqlite.sh` (Python online-backup API, 14-day retention, small-dump guard), crontab 23:30 installed, restore-to-scratch-DB PROVEN (6 students / 25 modules / 48 tickets). The 23:59 git snapshot never covered the DB (`*.db` gitignored) — this closes that gap.

## Phase 1 status update (2026-07-10)
DONE (verified, tested — see tasks/loop-log.md for evidence):
- P0 #6 (app boots without AI env) and #7 (phantom seed removed + purge script)
- P1: multi-select set grading; per-attempt quiz history (uq_student_quiz dropped); study-tracker "Bearer anything" bypass closed; weak deterministic admin session replaced with random expiring sessions; evidence ownership + 10MB size cap (IDOR closed)
- Ollama/OpenAI-compatible AI config (AI_BASE_URL/AI_MODEL/AI_API_KEY) + calibration script (NOT yet run against live AI)
- Six-role ladder + Gate 1 & Gate 2 seeded, enforced, pass/fail tested
- Full 24-week seed verified: 25 modules, 63 lessons, 25 quizzes/189 questions, 48 tickets, 5 lab templates, 48 networking CLI labs, and 3 capstones
- "This Week" dashboard (API + panel), ticket hint UI, drift fix (quizzes.status)

STILL OPEN (unchanged priority):
- Proxmox/Guacamole application P0s are fixed; only a live-infrastructure isolation/lifecycle smoke test blocks AUTO-VM cohort use
- Real-AI grader calibration run (needs the Ollama VM)
- Weeks 9-24 content (Phase C onward)

# TASKS.md — Nexus Backlog

Source: full project audit 2026-06-11 (historical reviews are in `docs/archive/`).
Priority order. Pick the top unchecked item unless told otherwise. Reference lines may drift — verify before editing.

---

## P0 — Broken / data-risk (fix before anything else)

- [x] **Fix Guacamole client URL encoding** — DONE 2026-07-19: Guacamole 1.6.0 NUL-separated connection identifiers use deterministic unpadded base64url encoding and are unit-tested.
- [x] **Stop handing students the Guacamole admin token** — DONE 2026-07-19: each access request rotates a random temporary user with READ permission on only its assignment connection; administrator credentials/tokens remain server-side and temporary users are deleted during cleanup.
- [x] **Make VM provisioning async** — DONE 2026-07-19: start persists a duplicate-protected assignment and returns 202, a background task uses its own DB session through all provisioning states, polling reports safe failures, and cleanup is asynchronous.
- [x] **Return existing VM connection info from `GET /labs/{id}`** — DONE 2026-07-19: persisted VM/IP/connection/status/error/start/expiry state survives refresh; the frontend resumes polling and obtains fresh scoped access without creating another VM.
- [x] **Verify production persistence** — DONE 2026-07-17: Railway/Supabase plans were dropped; active production is self-hosted SQLite with all upload routes honoring persistent `UPLOAD_DIR`, plus nightly online SQLite and uploads backups via `scripts/backup_sqlite.sh`.
- [x] **Remove `seed_students()` from `main.py`** — DONE 2026-07-17: only `scripts/seed_users.py` creates cohort accounts; legacy phantom rows were purged.
- [x] **Make `ai_service` import-safe** — DONE 2026-07-10: backend boots without AI configuration and AI calls fail cleanly when disabled/unconfigured.

## P1 — Security / correctness

- [x] **Organize audited quiz corpus** — DONE 2026-07-19: Alembic 0029 adds required/practice/remediation/cumulative/gate/certification metadata; progression counts only active validated checklist quizzes; 120 confirmed imported key failures and unsafe swollen-battery guidance were corrected; all 104 quizzes and 967 questions were preserved.
- [x] **Fix `allow_admin_or_student` bearer bypass** — DONE (Part 9: JWT now verified). 2026-07-18: also accepts the httpOnly `student_session` cookie — study-tracker no longer 401s after page refresh (regression tests in test_security_part9.py).
- [x] **Fix multi-select grading** — DONE 2026-07-10: multi-select answers are exact-set graded with regression coverage.
- [x] **Harden admin session** — DONE 2026-07-10: random expiring/revocable server-side sessions, timing-safe comparisons, and no secret-length logging.
- [x] **Evidence upload limits + ownership** — DONE 2026-07-19: lab and ticket evidence enforce a 10 MB cap, bounded reads, type checks, ownership, uploader IDs, empty-file rejection, safe names, and failed-save cleanup. `EvidenceArtifact.submission_type` disambiguates whether `submission_id` is a ticket or lab run.
- [x] **Per-attempt quiz history** — DONE 2026-07-10: each retake inserts its own row; best-score mastery and first-attempt-only XP are preserved.
- [x] **Remove localStorage-driven mentor admin shell** — DONE 2026-07-19: admin pages and navigation now require the protected backend admin-session status; forged mentor profiles and student JWTs do not authenticate admin routes.

## P2 — Lighter / cheaper

- [x] **Update vulnerable frontend dependencies** — DONE 2026-07-19: Axios and React Router patched within their existing majors; vulnerable Vite/Rollup/PostCSS/Babel/transitive packages refreshed; `npm audit` reports zero vulnerabilities and the production build passes.

- [x] **Swap AI to local Ollama** — DONE 2026-07-17: configurable OpenAI-compatible endpoint targets local Ollama and the five-fixture grader calibration passed.
- [x] **Move Playwright out of prod requirements** — DONE 2026-07-19: retained in `requirements-dev.txt`, documented Chromium setup, and proved a fresh production-only environment imports the backend with Playwright absent.
- [x] **Linked clones** — DONE 2026-07-19: `PROXMOX_FULL_CLONE=false` requests linked clones on supported LVM-thin/ZFS/RBD/Btrfs storage, otherwise logs a full-clone fallback; Proxmox API arguments are tested.
- [x] **Lazy-load admin routes** — DONE 2026-07-19: 12 admin pages emit as separate Vite chunks; main JS dropped from 1,083.71 kB to 976.00 kB. The remaining large-chunk warning is student/shared code, not eager admin code.
- [x] **`datetime.utcnow()` sweep** — DONE 2026-07-19: application code uses timezone-aware UTC, the AI budget window is UTC, and legacy naive activity timestamps are normalized before comparison.

## P3 — Maintainability / cleanup

- [x] Pydantic schemas for admin CRUD — DONE 2026-07-19: major create/update/import endpoints use bounded, extra-forbidden typed schemas with 1–24 week and 1–5 difficulty validation.
- [x] Replace `python-jose` with PyJWT — DONE 2026-07-19: explicit HMAC algorithm allowlist with valid/expired/bad-signature/malformed/unsigned tests; fallback JWT shim removed.
- [x] Delete dead code — DONE 2026-07-19 after reference searches: `SelectProfile.jsx`, `components/Dashboard.jsx`, `QuizList.jsx`, `Leaderboard.jsx`, and root `tmp_bookmarklet.js` are gone.
- [x] Fix hardcoded `week_number = 1` in `students.py` stats — DONE 2026-07-19: stats reuse the existing progression-week derivation; Weeks 1, 2, and 5 tested with a legacy naive student timestamp.
- [x] Prune old `AIRateLimit` rows — DONE 2026-07-19: bounded seven-day cleanup runs at most hourly per worker; active and expired records plus throttling are tested.
- [x] Unify on `httpx` — DONE 2026-07-19: Guacamole uses one reusable client with explicit connect/read/write/pool timeouts; application imports no `requests`.
- [ ] Weekly mentor digest: `/api/admin/weekly-summary` + scheduled Discord post (n8n or GitHub Actions)

## P4 — Sidecar deployment (on Proxmox, outside this repo)

Deploy in teaching-value order; document config in CLAUDE.md when done.
- [ ] Apache Guacamole (required for VM labs) + real end-to-end lab smoke test
- [ ] Scheduler calls `DELETE /api/admin/vms/cleanup?idle_hours=2` on cadence
- [ ] GLPI (student work-ticketing; consider Nexus↔GLPI scenario sync later)
- [ ] Gitea (runbook wikis — capstone portfolio artifact)
- [ ] n8n (cleanup schedule, Discord bridge, weekly reports)
- [ ] Netdata / Uptime Kuma — as student lab content, not maintained infra

## Content backlog (highest job-readiness value)

- [ ] **Quiz editorial follow-up** — review the remaining 634 optional imported questions, add explanations in priority order, and approve any future answer-position rebalance through a stable seed/live mapping. Keep the proposed 60 scenario questions as a separate approved phase.

### CLI lesson packs (SwitchLab courses — source MD in `references/lesson-drafts/`)

- [x] **Step framework** — 6 step types (explanation, multiple-choice, observe, forward-decision, hex-input, frame-builder), StepPanel + widgets, validator rules (2026-07-02)
- [x] **Engine: ping/ARP/MAC table** — PC ping with ARP transcript, dynamic MAC learning, `show mac address-table`, static MAC entries (2026-07-02)
- [x] **Learn Network Foundations pack** — 7 labs converted from `learn-network-foundations.md`, registered frontend+backend seed (2026-07-02)
- [x] **CLI Labs page: collapsible topic sections** — compartments collapsed by default with per-topic progress (2026-07-02)
- [ ] **Wave 2 — Learn Switching pack** (44 labs from `learn-switching.md`): engine needs trunking (802.1Q, native VLAN, allowed list), STP/Rapid PVST+ (root election, PortFast, BPDU Guard), EtherChannel/LACP, 2-switch topologies. Convert per section A–H; exams have no hints.
- [ ] **Wave 3 — Learn Routing pack** (23 labs from `learn-routing.md`): engine needs router device type, IPv4/VLSM host config, SVIs, static/default routes, OSPF, IPv6 (statics, SLAAC, EUI-64), L3 EtherChannel.

- [ ] **Active Directory lab template family** — Windows Server (AD DS) + domain-joined client: password resets, lockouts, group membership, GPO, share access. Biggest help-desk skill gap in current content.
- [ ] Parametrized ticket variants per student (reuse `break_script`-style JSON) — anti-answer-sharing
- [ ] Escalation-type tickets (correct answer = clean escalation note)
- [ ] Grade `commands_used` field; occasional "write the email to the user" communication grading
- [ ] Anki deck export of missed questions (`genanki`)

---

## Done (audit-confirmed 2026-06-11)

- [x] P2 quiz speed-flag admin view (`admin_content.py` flagged endpoint + QuizEditorPage)
- [x] P3 Proxmox/Guacamole application layer (models, services, lab start/submit wiring, idle cleanup endpoint) — code complete, has P0 bugs above, never smoke-tested against real infra
- [x] FSRS-style flashcards (SM-2 algorithm), lesson notes, quiz timing capture
