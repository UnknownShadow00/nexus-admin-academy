# Nexus IT Academy — Claude Code Context

Private IT training platform. Mentor (Abdi, ~5 years help desk/network admin) personally coaching 5 friends through WGU Cloud/Network Engineering. Goal: close the gap between CompTIA memorization and real troubleshooting skill.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, React Router 6, Tailwind CSS, Axios, Lucide React, xterm.js |
| Backend | FastAPI, SQLAlchemy 2, Alembic, SQLite → Supabase (PostgreSQL) |
| Auth | JWT (python-jose), passlib, httpOnly cookies |
| AI | Anthropic Claude via `app/services/ai_service.py` |
| Scraping | Playwright + BeautifulSoup (ExamCompass — permission confirmed) |
| Deployment | Railway (backend), Supabase (DB + auth) |
| Dev comms | Discord (weekly calls, methodology card, student coordination) |

---

## Project Structure

```
nexus-admin-academy/
├── CLAUDE.md                  ← you are here — update after every task
├── TASKS.md                   ← backlog — update after every task
├── NEXUS_UPGRADE_PLAN.md      ← full feature roadmap (Proxmox, Guacamole, etc.)
├── NEXUS_ADDONS_RESEARCH.md   ← open-source tool research (GLPI, Netdata, etc.)
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/            ← SQLAlchemy models (one file per domain)
│   │   ├── routers/           ← FastAPI route handlers
│   │   ├── schemas/           ← Pydantic request/response schemas
│   │   └── services/          ← business logic, AI calls, scrapers
│   ├── alembic/versions/      ← 26 migrations — always add new ones here
│   ├── scripts/seed_users.py  ← seeds 6 hardcoded accounts
│   ├── seed.py                ← seeds lab/capstone/quiz content
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
ai_service.py           ← Anthropic API calls, cost logging
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

- 6 hardcoded accounts: 1 mentor (`is_mentor=True`), 5 students
- Seeded by `backend/scripts/seed_users.py`
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
- [x] 26 Alembic migrations — schema is mature (+ 3 new: lesson_notes, flashcard_reviews, quiz_attempt_timing)
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

---

## What Is NOT Done (Build These Next)

Priority order. Pick the top item unless told otherwise.

### P2 — Remaining retention gap
- [ ] **Quiz speed-flag admin view** — `time_per_question` is tracked on `QuizAttempt` but no admin UI shows flagged fast attempts (avg < 8s). Build a view in the admin quiz review page.

### P3 — Proxmox VM integration (biggest feature)
- [ ] **`proxmox_template_vmid` on `LabTemplate`** — nullable Integer column + migration; links a lab to a Proxmox VM template VMID
- [ ] **`VmAssignment` model + migration** — vmid, student_id (FK→students), lab_run_id (FK→lab_runs), status (provisioning/running/submitted/destroyed), ip_address, guac_conn_id, created_at, destroyed_at
- [ ] **`proxmox_service.py`** — clone/start/get_ip/destroy via `proxmoxer` library; reads PROXMOX_HOST, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET, PROXMOX_NODE env vars
- [ ] **`guacamole_service.py`** — create_connection(vm_ip, protocol)/get_token_url(conn_id); reads GUACAMOLE_URL, GUACAMOLE_ADMIN_USER, GUACAMOLE_ADMIN_PASS env vars
- [ ] **Wire `/labs/{id}/start`** — if template.proxmox_template_vmid set → provision VM → create VmAssignment → return guac_token_url
- [ ] **Wire `/labs/{id}/submit`** — if VmAssignment exists for run → destroy VM → set status=destroyed
- [ ] **`DELETE /api/admin/vms/cleanup`** — destroy all VmAssignment rows idle > 2 hours (called by n8n on schedule)
- [ ] **LabPage iframe embed** — if startLab() returns guac_token_url → render `<iframe>` filling main content area
- [ ] **`proxmoxer` in requirements.txt**

### P4 — Sidecar services (run on Proxmox, not in this codebase)
These are deployed separately. Document config here when done.
- [ ] Apache Guacamole (Docker Compose on Proxmox VM)
- [ ] GLPI (student "work ticketing system" — separate from Nexus tickets)
- [ ] Netdata (infrastructure monitoring — students read dashboards as lab skill)
- [ ] Uptime Kuma (service status — wire to Discord for lab-down alerts)
- [ ] Gitea (student runbook wikis + break script version control)
- [ ] n8n (VM cleanup automation + Discord → ticket bridge + weekly reports)

---

## Environment Variables

### Backend `.env`
```
# Existing — required
DATABASE_URL=
JWT_SECRET_KEY=
ADMIN_USERNAME=
ADMIN_PASSWORD=
ANTHROPIC_API_KEY=
CORS_ORIGINS=
UPLOAD_DIR=
COOKIE_SECURE=true          # set false for local dev

# New — Proxmox (add when building P3)
PROXMOX_HOST=
PROXMOX_TOKEN_ID=           # format: apiuser@pve!tokenname
PROXMOX_TOKEN_SECRET=
PROXMOX_NODE=pve
VMID_POOL_START=200
VMID_POOL_END=299

# New — Guacamole (add when building P3)
GUACAMOLE_URL=
GUACAMOLE_ADMIN_USER=
GUACAMOLE_ADMIN_PASS=
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

When building P3, follow this pattern:

```
Student clicks "Start Lab"
  → POST /api/labs/{lab_id}/start
  → proxmox_service.clone_template(template_vmid, new_vmid, name)
  → proxmox_service.start_vm(new_vmid)
  → guacamole_service.create_connection(vm_ip, protocol="rdp")
  → returns {guac_token_url, vmid}
  → LabPage.jsx embeds guac_token_url in <iframe>

Student submits evidence
  → POST /api/labs/{lab_run_id}/submit
  → proxmox_service.destroy_vm(vmid)
  → update vm_assignments.status = "destroyed"
```

**VM template → ticket scenario mapping** lives in `LabTemplate.break_script` (JSON field). Each template row has a `proxmox_template_vmid` field (add in migration).

---

## FSRS Flashcard Design Reference

When building P2 flashcards:

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

These run on your Proxmox box, NOT on Railway. They're separate from this codebase.

```
[Railway — FastAPI Backend]
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
   Tailscale mesh (connects Proxmox ↔ Railway backend)
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
- **SQLite locally, PostgreSQL (Supabase) in prod** — SQLAlchemy handles both but watch for SQLite-specific syntax in raw queries.
- **AI calls must check `AIRateLimit` first** — never call `ai_service` directly from a router without rate check.