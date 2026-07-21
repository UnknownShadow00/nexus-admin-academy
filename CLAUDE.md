# Nexus IT Academy — Claude Code Context

Private IT training platform. Mentor (Abdi, ~5 years help desk/network admin) personally coaching 5 friends through WGU Cloud/Network Engineering. Goal: close the gap between CompTIA memorization and real troubleshooting skill.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, React Router 6, Tailwind CSS, Axios, Lucide React, xterm.js |
| Backend | FastAPI, SQLAlchemy 2, Alembic, SQLite in active production (PostgreSQL supported) |
| Auth | PyJWT with an explicit HMAC allowlist, passlib, httpOnly cookies; separate server-side admin sessions |
| AI | Local Ollama through the OpenAI-compatible API in `app/services/ai_service.py` |
| Scraping | Playwright + BeautifulSoup as development-only dependencies |
| Deployment | Self-hosted `nexus-services`: systemd backend, nginx frontend container, Cloudflare HTTPS |
| Dev comms | Discord (weekly calls, methodology card, student coordination) |

---

## Project Structure

```
nexus-admin-academy/
├── CLAUDE.md                  ← you are here — update after every task
├── TASKS.md                   ← backlog — update after every task
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/            ← SQLAlchemy models (one file per domain)
│   │   ├── routers/           ← FastAPI route handlers
│   │   ├── schemas/           ← Pydantic request/response schemas
│   │   └── services/          ← business logic, AI calls, scrapers
│   ├── alembic/versions/      ← migrations through 0028 — always add new ones here
│   ├── scripts/seed_users.py  ← seeds 1 mentor and 6 students from env passwords
│   ├── seed.py                ← idempotently seeds all 24 weeks
│   ├── seed_curriculum.py     ← required idempotent Study Tracker catalog
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/        ← shared UI (Badge, PageHeader, FilterBar, Banner, RequireAuth)
│       ├── hooks/             ← useAuth, custom hooks
│       ├── pages/             ← route-level pages
│       │   └── admin/         ← admin-only pages
│       └── services/api.js    ← ALL axios calls go here — never call axios directly in components
└── tasks/
    └── loop-log.md            ← append a log entry after every completed task
```

---

## Existing Models (do not duplicate)

```
Student, LoginStreak, XPLedger
Quiz, Question, QuizAttempt
Ticket, TicketSubmission
LabTemplate, LabRun
CapstoneTemplate, CapstoneRun
Module, Lesson, CurriculumVideo, VideoWatch
CommandReference
ComptiaObjective, StudentObjectiveProgress
StudentDomainMastery, WeeklyDomainLead
EvidenceArtifact
Resource
SquadActivity
AIUsageLog, AIRateLimit
Incident, IncidentTicket, IncidentParticipant, RootCause, RCASubmission
Role, PromotionGate, StudentRole, MethodologyFramework, StudentMethodologyProgress
```

---

## Existing Services (do not duplicate)

```
ai_service.py           ← OpenRouter chat-completions calls, budget cap, cost logging
proxmox_service.py      ← VM clone/start/IP/destroy via proxmoxer
guacamole_service.py    ← Guacamole connection lifecycle + scoped temporary users
fsrs_service.py         ← flashcard scheduling (SM-2 algorithm)
auth_service.py         ← JWT issue/verify
admin_auth.py           ← admin session auth
quiz_generator.py       ← YouTube transcript → MCQ via AI
examcompass_scraper.py  ← Playwright scraper (permission granted)
ticket_generator.py     ← generates ticket scenarios
ticket_grader.py        ← AI grades plain-English explanations
xp_service.py / xp_calculator.py
activity_service.py
discord_service.py      ← passive notifications
mastery_service.py
squad_service.py
progression_service.py
rate_limiter.py
evidence_validator.py
methodology_enforcer.py
content_extractor.py
cve_service.py
```

---

## Auth Model

- 7 seeded accounts: `Mentor` (`is_mentor=True`) + 6 students (`Shak`, `Rakib`, `Ahmed`, `Emran`, `Walo`, `Hudayfa`)
- Seeded by `backend/scripts/seed_users.py` — passwords come from `SEED_PASSWORD_*` vars in gitignored `backend/.env` (script refuses to run without them; never hardcode passwords)
- Usernames are case-insensitive (`Shak` = `shak` = `SHAK`; input is trimmed + casefolded, DB enforces a unique index on `lower(username)` — migration `b7c8d9e0f1a2`). Display capitalization is preserved in the DB/UI. Passwords stay case-sensitive.
- No public registration — `/auth/register` endpoint does NOT exist
- JWT in httpOnly cookies — never localStorage
- Two separate auth flows:
  - Students → `/auth/login` → JWT → `RequireAuth` guard
  - Admin → `/admin-login` → admin session → `AdminAccessGate` guard
- Mentor can read all student data but cannot access admin panel

---

## Hard Rules

1. **Alembic migration required for every schema change** — never alter tables directly
2. **All API calls go through `frontend/src/services/api.js`** — never axios directly in components
3. **Tailwind only** — no inline styles, no CSS modules
4. **Parameterized queries only** — no string concatenation in SQL
5. **JWT never in localStorage** — httpOnly cookies or memory only
6. **AI calls must log to `AIUsageLog`** and respect `AIRateLimit`
7. **`python -m py_compile`** must pass on any changed backend file
8. **`npm run build`** must pass after any frontend change
9. **Append to `tasks/loop-log.md`** after every completed task
10. **Update `CLAUDE.md`** if stack, structure, or rules change
11. **Update `TASKS.md`** when a backlog item is completed or added

---

## What Is Done

### Backend — Complete
- [x] JWT auth, student/mentor/admin separation
- [x] Seed script for all 6 accounts (`scripts/seed_users.py`)
- [x] Alembic schema through revision `0028`
- [x] Ticket system: variants, XP, plain-English explanation field
- [x] Quiz engine: ExamCompass scraper + YouTube transcript → AI MCQ
- [x] Multi-select questions, option E, publish/draft workflow
- [x] Learning path: YouTube embed + lesson completion tracking
- [x] Study tracker, login streak, weekly leaderboard (`WeeklyDomainLead`)
- [x] Lab model + API routes (`LabTemplate`, `LabRun`) + evidence upload endpoint
- [x] Capstone model + API routes (`CapstoneTemplate`, `CapstoneRun`)
- [x] Discord service (passive notifications)
- [x] Admin panel APIs: student mgmt, quiz editor, curriculum editor, AI cost dashboard
- [x] Admin lab + capstone CRUD APIs (create/update/delete via admin_content router)
- [x] ExamCompass bookmarklet + scraper
- [x] CompTIA objectives JSON → `ComptiaObjective` model
- [x] `CommandReference` model + router (seeded, backend complete)
- [x] Evidence uploader with screenshot storage
- [x] Squad/domain mastery weekly recompute
- [x] Rate limiter + cost logging for AI calls
- [x] Admin quiz publish/draft fixed (May 2026)
- [x] `.gitignore` updated: `frontend/dist`, `pytest` cache excluded
- [x] `StudentLessonNote` model + router (`/api/lesson-notes`)
- [x] `FlashcardReview` model + FSRS service + router (`/api/flashcards`)
- [x] Quiz attempt `time_per_question` JSON field (timing migration)
- [x] Proxmox/Guacamole VM integration layer: asynchronous persistent provisioning, scoped temporary Guacamole users, linked/full clone selection, refresh recovery, teardown, and admin cleanup

### Frontend — Complete
- [x] Dark mode, shared design system (Badge, PageHeader, FilterBar, Banner)
- [x] Route guards: `RequireAuth`, `AdminAccessGate`
- [x] Error boundaries, skeleton loaders
- [x] Student home dashboard: XP, streak, ticket/quiz counters
- [x] Learning path with expandable lessons + embedded YouTube player
- [x] Quiz taker with MCQ flow + review screen (`QuizReviewScreen`)
- [x] Ticket submit with plain-English explanation field
- [x] Labs page + Lab detail page + evidence upload UI
- [x] Capstones page + Capstone detail page
- [x] Terminal component via xterm.js (component exists — NOT connected to backend)
- [x] Admin: curriculum editor, quiz editor, student manager, bookmarklet page, AI cost page
- [x] Admin lab creation/edit UI (`/admin/labs`)
- [x] Admin capstone creation/edit UI (`/admin/capstones`)
- [x] Admin ticket review UI (`/admin/ticket-review`) — explanation grade view
- [x] Command reference page (`/commands`) with search
- [x] Flashcard review panel (`FlashcardReviewPanel.jsx`) on StudentHome
- [x] VM-backed lab UI: admin template VMID field, LabPage Guacamole iframe, and visible VM start failure state

---

## What Is NOT Done (Build These Next)

**The live backlog is `TASKS.md` — always pick from there.** The verified
launch/security/dependency/VM code fixes are complete. Automated VM use remains
disabled for cohort launch until the configured Proxmox and Guacamole 1.6.0
deployment passes a real start/connect/isolation/expiry/destroy smoke test.

---

## Environment Variables

### Backend `.env`
```
# Core — required
DATABASE_URL=
JWT_SECRET_KEY=
JWT_EXPIRE_MINUTES=1440
ADMIN_USERNAME=
ADMIN_PASSWORD=             # also the admin session secret; ADMIN_SECRET_KEY is a legacy fallback
ADMIN_API_KEY=              # X-Admin-Key header alternative to the session cookie
CORS_ORIGINS=
UPLOAD_DIR=
APP_LOG_PATH=
COOKIE_SECURE=true          # set false for local dev

# AI — local Ollama or another OpenAI-compatible endpoint; optional
AI_BASE_URL=http://<ollama-host>:11434/v1
AI_MODEL=deepseek-r1:32b
AI_API_KEY=                # omit for local Ollama
AI_ENABLED=true
DAILY_AI_BUDGET=1.00
COST_PER_1K_TOKENS=0.001
MAX_TOKENS=600
AI_TIMEOUT_SECONDS=30
AI_TEMPERATURE=0.6

# Discord (optional)
DISCORD_WEBHOOK_URL=

# Proxmox (VM-backed labs)
PROXMOX_HOST=
PROXMOX_TOKEN_ID=           # format: apiuser@pve!tokenname
PROXMOX_TOKEN_SECRET=
PROXMOX_NODE=pve
VMID_POOL_START=200
VMID_POOL_END=299
PROXMOX_VERIFY_SSL=true
PROXMOX_FULL_CLONE=false   # linked when storage is supported; otherwise safe full fallback
LAB_VM_TTL_MINUTES=120

# Guacamole 1.6.0 (VM-backed labs)
GUACAMOLE_URL=
GUACAMOLE_ADMIN_USERNAME=
GUACAMOLE_ADMIN_PASSWORD=
GUACAMOLE_DATASOURCE=postgresql
```

### Frontend `.env`
```
VITE_API_URL=
```

---

## Key Patterns

### Adding a new backend feature
1. Add model in `backend/app/models/` (import in `backend/app/models/__init__.py`)
2. `alembic revision --autogenerate -m "describe_change"` → review → `alembic upgrade head`
3. Add schema in `backend/app/schemas/`
4. Add router in `backend/app/routers/` → register in `backend/app/main.py`
5. `python -m py_compile app/models/newmodel.py app/routers/newrouter.py`
6. Write test in `backend/tests/`

### Adding a new frontend page
1. Create `frontend/src/pages/NewPage.jsx`
2. Use shared components: `PageHeader`, `Badge`, `FilterBar`, `Banner` from `components/ui/`
3. Add API calls to `frontend/src/services/api.js` — never inline
4. Register route in `frontend/src/App.jsx` — wrap with `<RequireAuth>` if student-facing
5. `npm run build` must pass

### Adding a new migration
```bash
cd backend
alembic revision --autogenerate -m "add_vm_assignments"
# review the generated file in alembic/versions/
alembic upgrade head
```

### Running tests
```bash
cd backend
python -m pytest tests/ -q
# or scoped:
python -m pytest tests/test_labs.py tests/test_capstones.py -q
```

---

## Proxmox VM Integration — Design Reference

Implemented (see `labs.py`, `proxmox_service.py`, `guacamole_service.py`, `VmAssignment`):

```
Student clicks "Start Lab"
  → POST /api/labs/{lab_id}/start
  → persists one VmAssignment and returns 202 immediately
  → worker-owned DB session clones/starts/waits/configures the connection
  → frontend polls GET /api/labs/{lab_id}/vm-status
  → POST /api/labs/{lab_id}/vm-access rotates a random temporary Guacamole user
  → temporary user receives READ on only this assignment connection
  → LabPage.jsx embeds the scoped URL; refresh restores the same assignment

Student submits evidence
  → POST /api/labs/{lab_id}/submit
  → asynchronous cleanup deletes temporary user, connection, and VM
  → update vm_assignments.status = "destroyed"
```

**VM template → ticket scenario mapping** lives in `LabTemplate.break_script` (JSON field). Each template row has a `proxmox_template_vmid` field (add in migration).

---

## FSRS Flashcard Design Reference

Implemented (`flashcard_reviews` table, `fsrs_service.py` — actually SM-2 scheduling, `FlashcardReviewPanel.jsx`). Original design:

```sql
-- New table
CREATE TABLE flashcard_reviews (
    id            INTEGER PRIMARY KEY,
    student_id    INTEGER REFERENCES students(id),
    question_id   INTEGER REFERENCES questions(id),
    due_date      DATE NOT NULL,
    interval_days INTEGER DEFAULT 1,
    ease_factor   REAL DEFAULT 2.5,
    review_count  INTEGER DEFAULT 0,
    last_rating   INTEGER,  -- 1=Again 2=Hard 3=Good 4=Easy
    created_at    TIMESTAMP DEFAULT now()
);
```

Auto-generate cards: when a student submits a quiz attempt with wrong answers, create `flashcard_reviews` rows for each wrong question with `due_date = today`. FSRS scheduling in `services/fsrs_service.py`.

Student dashboard shows: "Today's Review (N cards due)" — flip card UI, 4 rating buttons.

---

## Sidecar Services — Architecture

These run on the Proxmox network and are separate from this codebase.

```
[nexus-services — FastAPI Backend]
        |
        | proxmoxer (HTTPS)        | Guacamole REST API
        |                          |
[Proxmox VE Host]
        |
  ┌─────┴─────────────────────────────┐
  │  LXC/VMs on Proxmox              │
  │  ┌──────────┐ ┌───────────────┐  │
  │  │ Guacamole│ │ GLPI + MySQL  │  │
  │  │ :8080    │ │ :80           │  │
  │  ├──────────┤ ├───────────────┤  │
  │  │ Netdata  │ │ Uptime Kuma   │  │
  │  │ :19999   │ │ :3001         │  │
  │  ├──────────┤ ├───────────────┤  │
  │  │  Gitea   │ │     n8n       │  │
  │  │ :3000    │ │ :5678         │  │
  │  └──────────┘ └───────────────┘  │
  │                                  │
  │  Student VM Pool (VMID 200-299)  │
  │  win10-dns-broken, ubuntu-ssh... │
  └──────────────────────────────────┘
        |
   Private network (connects Proxmox ↔ nexus-services)
```

---

## Curriculum Phases (Content Context)

Students progress through these phases. Lab scenarios must match current phase.

| Phase | Duration | Focus | Tools |
|---|---|---|---|
| Month 0 | Pre-bootcamp | Computer literacy, A+ fundamentals | Nexus quizzes, Professor Messer videos |
| Month 1 | Week 1-4 | Windows troubleshooting tickets | Guacamole, GLPI, Event Viewer, Services |
| Month 2 | Week 5-8 | Linux basics | Ubuntu VMs, Gitea wiki, systemctl, journalctl |
| Month 3 | Week 9-12 | Monitoring & networking | Netdata, Uptime Kuma, nmap, DNS |
| Month 4 | Week 13-16 | Automation | Ansible playbooks, Gitea, GLPI workflows |
| Month 5 | Week 17-20 | Capstone | Full onboarding scenario end-to-end |
| Month 6 | Week 21-24 | Infrastructure integration | Operations, recovery, and final capstone work |

---

## Session Log Protocol

After EVERY completed task, append to `tasks/loop-log.md`:

```markdown
## [TIMESTAMP] Task Completed
- Task: [what was built/fixed]
- Files changed: [list]
- Result: pass | partial | fail against acceptance criteria
- Next: [what to do next or "None"]
```

And update `TASKS.md` backlog accordingly.

---

## Common Gotchas

- **`spawn EPERM` on Windows during `npm run build`** — Vite/esbuild child-process restriction in some sandboxes. Run build in a real terminal, not the sandbox. This is a known environment limitation.
- **`frontend/dist` should NOT be committed** — `.gitignore` now covers it. If you see dist files in git status, run `git rm -r --cached frontend/dist` once.
- **`datetime.utcnow()` is deprecated** — use `datetime.now(timezone.utc)` when touching time fields.
- **Admin routes use `AdminAccessGate`, not `RequireAuth`** — they are completely separate auth flows.
- **Do NOT add a `/auth/register` endpoint** — accounts are seeded only.
- **SQLite is the active production database; PostgreSQL remains supported** — keep SQL portable across both dialects.
- **AI calls must check `AIRateLimit` first** — never call `ai_service` directly from a router without rate check.

## Phase 1 session notes (2026-07-10)
- AI config: AI_BASE_URL/AI_MODEL/AI_API_KEY (OpenRouter vars still work as fallback); app boots with AI unset; endpoints 503 cleanly.
- Roles are now the 6-role ladder (Trainee → Junior Infrastructure Administrator); seed migrates legacy L1/L2 rows in place.
- Quiz attempts: one row PER attempt (uq_student_quiz dropped); mastery = best score, XP = first attempt only.
- Tickets: hints (≤4, XP −5/−10/−20/−35% floor 40%), parameters ({{PLACEHOLDER}} JSON, student_id % len deterministic), five-anchor scoring (investigation/root_cause/safe_fix_or_escalation/verification/communication, sum = final 0-10).
- Phase A content lives in backend/seed_phase_a.py (structured source; idempotent; edit there, not in DB).
- New gate requirement types: practical_checkpoint, min_completed_lessons, min_cli_labs, no_unresolved_flags.
- This dated note records the Phase 1 transition; the current sections above are authoritative.

## Deployment reality note (2026-07-17 — Day 1 go-live on .101)
- Active deployment: self-hosted on nexus-services (.101), systemd unit `nexus-admin-academy.service` → uvicorn from `backend/.venv` on :8000, SQLite (`backend/nexus.db`). AI is local Ollama on the private network per `.env`.
- Restarting the service: `systemctl restart` needs interactive sudo — use `kill -KILL $(systemctl show nexus-admin-academy -p MainPID --value)`; `Restart=on-failure` brings it back in ~8s.
- Pre-go-live state preserved at `../nexus-admin-academy.bak-2026-07-17` and `~/nexus-pre-24wk-2026-07-17.sql`; old DB parked at `backend/nexus.db.pre24wk-2026-07-17`. Do not delete.
- Public access is https://nexus.builtfromzero.fyi via Cloudflare tunnel (`cloudflared.service`) → nginx :80. `COOKIE_SECURE=true` since 2026-07-18: cookies are `Secure; SameSite=none` — logins over plain http:// (LAN IP) will NOT persist; always use the HTTPS domain. `.env` is CRLF — edit COOKIE_SECURE with `sed -i 's/^COOKIE_SECURE=.*\r$/COOKIE_SECURE=<val>\r/'`.
- Frontend is served by the `nexus-frontend` nginx container on :80 (dist COPIED into the container — bind-mounting the host dist 403s on permissions; API proxied to host :8000; config in `frontend/nginx.host.conf`). After `npm run build`, redeploy with the `docker cp` procedure documented in `frontend/nginx.host.conf`.
- Backups: nightly SQLite + uploads backup via `scripts/backup_sqlite.sh` → `~/backups/nexus/` (crontab 23:30, 14-day retention, restore proven 2026-07-17). The 23:59 git snapshot does NOT cover the DB (`*.db` gitignored). `scripts/backup_db.sh` is the pg_dump variant for the Docker/Postgres stack only.
- Grader calibration vs live deepseek-r1:32b: **PASSED 5/5** (2026-07-17) after adding the verification-anchor-0 hard cap in `ticket_grader.py`. AI grading is cleared for students.
- See NEXUS_GO_LIVE_CHECKLIST.md for Day 5 (cohort prep — human items: Discord post, kickoff call).

## Deployment verification checkpoint (2026-07-19)

- Source inspected and deployed from commit
  `d15dde3ebf13210faf240f1bf1968e26c8b16b6a` plus the reviewed release-candidate
  worktree. Backend is active under `nexus-admin-academy.service`; the built
  frontend is active in `nexus-frontend`.
- Pre-deployment backups are under
  `/home/nexus/backups/nexus-deploy-20260719T093436Z/`: `application.tar.gz`,
  `nexus.db`, and `uploads.tar.gz`. Archives are non-empty/readable and the
  SQLite backup passed `PRAGMA integrity_check`.
- Production requirements installed cleanly in `backend/.venv`; Alembic is at
  `0028 (head)`; compilation passed; the complete suite is `154 passed`; npm
  audit reports zero vulnerabilities; Vite and both networking CLI checks pass.
- Live seed runs were idempotent and preserved all existing progress. The live
  catalog is 25 modules, 63 lessons, 104 quizzes, 967 questions, 48 tickets,
  5 manual lab templates, 48 networking labs, 3 capstones, and 182 videos. The
  higher quiz/question/video totals are pre-existing imported catalog content;
  the verified fresh-seed baseline remains 25/189/62.
- The stale remote-AI host reference was corrected to the current private AI
  server; no AI-server service or firewall change was required. The configured
  model is present, calibration passed 5/5, and disposable ticket grading passed.
- Five orphaned `student_methodology_progress` rows for deleted IDs 8–12 were
  removed by `scripts/repair_orphaned_student_data.py` after a fresh backup and
  dry run. `app/database.py` now enables SQLite foreign keys on every SQLAlchemy
  connection, supported student deletion handles legacy no-FK tables, and the
  valid-progress digest is unchanged. Foreign-key and integrity checks pass.
- Full live smoke testing passed 25/25 with admin-created disposable accounts;
  all test rows and files were removed. The additional catalog is inventoried at
  `docs/PRODUCTION_CONTENT_INVENTORY.md` and was not edited.
- Release status: **Ready for manual-VM cohort**. Automated VM testing remains
  pending because Proxmox/Guacamole config is incomplete and zero automated labs
  are published.

## Security review reconciliation (2026-07-21)

- An external Deep Research report (written without repo/ZIP access or live
  auth testing) was reconciled against current code and the live `.101`
  deployment. Full detail in `docs/DEEP_RESEARCH_FINDINGS_RECONCILIATION.md`,
  `docs/SECURITY_ROUTE_AUTHORIZATION_AUDIT.md`, and
  `docs/SECURITY_HEADERS_AND_SESSION_REVIEW.md`.
- Its three critical/high findings (Guacamole admin-token-in-student-URL,
  `allow_admin_or_student` bearer bypass, deterministic `sha256(password)`
  admin session) were already fixed before this review — confirmed via
  `guacamole_service.py`'s scoped per-student temp users, `admin_auth.py`'s
  JWT-verifying bearer check, and the random/expiring/revocable admin session.
  Route-by-route authorization across all routers is clean.
- Fixed during this review, code-complete but **not yet deployed** to `.101`:
  cookies now `SameSite=Lax` unconditionally (was `None` in production with no
  same-origin need); a new Origin/Referer CSRF-validation middleware in
  `app/main.py` for cookie-authenticated state-changing requests; security
  response headers (CSP, HSTS, X-Content-Type-Options, Referrer-Policy,
  Permissions-Policy, `Cache-Control: no-store` on `/api/`+`/auth/`) added in
  both the FastAPI backend and `frontend/nginx.conf`/`nginx.host.conf`; and a
  bounded-read + aggregate-size fix on `POST /api/tickets/uploads` (previously
  read entire uploads into memory before the size check, unlike the already
  bounded `evidence.py` upload path).
- Still pending, not launch-blocking: Cloudflare's `builtfromzero.fyi` zone
  doesn't redirect plain `http://` to `https://` (dashboard-only fix, no
  code lever exists in this repo); confirm intent on `GET /api/students`
  exposing all student emails to any authenticated student.
- **Resolved (2026-07-21):** the leftover temporary "Claude" student account
  (live, id 8, zero owned rows) was removed via the supported
  `DELETE /api/admin/students/{id}` workflow; `SEED_PASSWORD_CLAUDE` was
  removed from `.env`; the temporary `ACCOUNTS` entry in `seed_users.py` was
  reverted. `ADMIN_USERNAME` was found to literally be the temporary `codex`
  value (confirmed via a boolean-only check, no secret ever printed) and was
  replaced with the real mentor credentials by the operator directly. Post-
  cleanup: 7 real cohort accounts remain, zero orphan rows, integrity `ok`,
  zero FK violations, 176/176 tests pass.
- **Deployed 2026-07-21:** all hardening changes above are live on `.101` —
  backend restarted, frontend rebuilt/redeployed to the `nexus-frontend`
  container. 41/41 live smoke tests passed (auth, CSRF, email privacy,
  uploads, security headers, core workflows, live ticket grading via Ollama).
  Cloudflare "Always Use HTTPS" remains **not enabled** — confirmed live,
  dashboard-only action pending. Minor follow-up: nginx's security headers
  are duplicated (identical values) on proxied backend paths since both nginx
  and FastAPI set them — cosmetic, not a security issue.

## Quiz organization (2026-07-19)

- Alembic head is `0029`. Quiz purpose, editorial state, checklist/library visibility, source, validation, quality, and prerequisite metadata are authoritative; `status=published` alone no longer makes a quiz required.
- Student progression counts only active, published, answer-validated quizzes with both `is_required=true` and `show_in_weekly_checklist=true`. Optional, remediation, and certification attempts retain feedback/history but do not update workplace mastery or block progression.
- Placement and correction scripts are dry-run by default: `backend/scripts/apply_quiz_placement_plan.py` and `backend/scripts/apply_quiz_answer_corrections.py`; both require `--confirm` to commit and preserve 104 quizzes / 967 questions.
- Required coverage is exactly one quiz for every Week 0–24. Certification content lives in the optional library. Remediation is visible only after explicit assignment or a failed required quiz in the same week.
- The source-of-truth implementation reports are `docs/QUIZ_IMPLEMENTATION_RESULTS.md`, `docs/QUIZ_ANSWER_CORRECTIONS.md`, and `docs/QUIZ_MERGE_LOG.md`.

## Full platform review (2026-07-21)

- A 17-phase product/curriculum/UX/technical review is complete; all 18
  documents live in `docs/reviews/` (start at `NEXUS_FULL_REVIEW.md`; fix
  sequencing in `NEXUS_PRIORITIZED_ACTION_PLAN.md`; every finding with
  severity/evidence in `NEXUS_FINDINGS.csv`). No production code was changed
  as part of this review.
- **Confirmed live, not yet fixed:** the A+ Study Tracker unlock gate
  (`a_plus_unlock_threshold_pct`, default/live value 40%, in
  `app/services/a_plus_access.py`) blocks ticket/lab/capstone/CLI-lab
  submission for **every** student until 40% of 137 A+-tagged videos are
  watched (~9 hours) — this silently contradicts Week 1's designed ticket
  assignments and has no in-app explanation anywhere. This is the review's
  single P0 finding; see `NEXUS_TICKET_REVIEW.md`.
- Cloudflare "Always Use HTTPS" is now confirmed **enabled** (`http://`
  returns a live `301`) — the prior "not enabled" status noted above and in
  `TASKS.md` is stale as of this review.
- Capstone unlock is currently a no-op for every student: all 3 live
  `CapstoneTemplate` rows have `role_level = NULL`, so `has_unlocked_
  capstones` is `true` regardless of real progress. Fix by setting each
  template's intended `role_level`.
- Lab submission (`app/routers/labs.py`, `submit_lab`) awards no XP and has
  no mentor-review gate, unlike tickets — an intentional-looking asymmetry
  that isn't explained anywhere and should be reconciled.

## Pre-Week-0 Launch Readiness Sprint (2026-07-21)

Full detail: `docs/reviews/PRE_WEEK_ZERO_IMPLEMENTATION_REPORT.md`,
`docs/reviews/PRE_WEEK_ZERO_BROWSER_ACCEPTANCE.md`,
`docs/reviews/PRE_WEEK_ZERO_FINAL_READINESS.md`.

- **A+ gate replaced.** `require_a_plus_unlocked()` is gone (dead code
  removed, along with the orphaned frontend `APlusPreviewLock.jsx`).
  `require_week_reached()` in `progression_service.py` is now the single
  gating primitive for ticket/lab/CLI-lab/capstone actions, reusing
  `derive_current_week()` (also now centralized there, previously
  duplicated in `students.py`). Optional A+ video progress no longer
  affects hands-on access at all; the Study Tracker's own progress display
  (`get_a_plus_progress`) is unrelated and unaffected.
- **Two of the original 17-phase review's findings were wrong,
  reconciled this sprint:** LESSON-001 ("Week 1 has 0 lessons") — false;
  `MOD-001`'s two lessons were already served as Week 1 content, the real
  bug was a cosmetic-only Learning Path lock from `MOD-000`'s permanently-0%
  mastery, fixed via migration `0030`. QUIZ-001 ("unvalidated quizzes
  visible/attemptable") — false; live testing confirmed
  `student_visible_quiz_filters()` already excludes them everywhere. Both
  corrected (not deleted) in `NEXUS_FINDINGS.csv` and the relevant detail
  docs — **do not re-attempt either "fix" if it resurfaces in a future
  review without re-verifying live first.**
- **Capstone role-gate fixed** — 3 live templates now have `role_level` set
  (Support Technician I/II, Junior Systems Technician) instead of `NULL`.
- **Week 0 onboarding added**: new lesson "Welcome to Nexus: Your First
  Week" (`MOD-000`, `lesson_order=1`; the pre-existing "CompTIA 6-Step
  Process" lesson moved to `lesson_order=2`, unchanged in substance) plus a
  guided zero-stakes practice walkthrough
  (`onboarding_service.py`/`onboarding.py`/`OrientationPracticePanel.jsx`,
  new minimal `StudentOnboardingPractice` model). Reuses the existing Week 0
  "Ticketing Systems Quiz" — no new quiz was created.
- **Bug found and fixed by live testing, not by the unit test suite**:
  because `derive_current_week()` requires a lesson note on every published
  lesson in a week's module, and `MOD-000` now has two lessons, completing
  only the onboarding walkthrough (which only touched the first lesson)
  left the real Week-1 gate still closed while the onboarding UI claimed
  readiness. Fixed via a `week_one_unlocked` field on
  `get_orientation_state()` that reuses the real gate directly, plus an
  honest fallback message. **If a fixture-only regression test doesn't seed
  both `MOD-000` lessons, it will not catch this class of bug** — see
  `test_orientation_completion_reports_the_remaining_week_zero_lesson_until_week_one_unlocks`
  for the pattern that does.
- **Squad feed** now filters mentor accounts from the student-facing roster
  and activity queries by `Student.is_mentor` (role-based, not hardcoded).
- Full verification: 188/188 backend tests (176 before this sprint),
  Alembic head `0031`, DB integrity/FK clean, `npm audit` 0 vulnerabilities,
  clean frontend build.
- **No rendered-browser verification was possible in this sandbox** —
  Playwright's Chromium doesn't support this Ubuntu version, no system
  browser is installed, and the sandbox blocks localhost binding. All
  verification was API-level (in-process ASGI client against a copied
  DB). A human desktop + ~375px mobile click-through on the live/staging
  site is recommended before/soon after the five students begin.
- **Deployment not yet executed** — held pending explicit approval since it
  is a production action on shared infrastructure; everything needed to
  deploy quickly is ready (see `NEXUS_GO_LIVE_CHECKLIST.md`'s corresponding
  section).
