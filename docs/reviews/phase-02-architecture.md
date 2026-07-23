# Phase 2 — Architecture Map

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`

## Plain-language overview

Nexus is a two-tier app: a **React/Vite SPA** (`frontend/`) talking to a **FastAPI +
SQLAlchemy + Alembic** backend (`backend/`) over a JSON API, backed by **SQLite** in
production. Auth is split: **students** use a signed JWT delivered as an HttpOnly cookie;
**admins** use a separate server-side, expiring session (`admin_session` cookie) validated
in-process. Production sits behind **Cloudflare** with the backend apparently on **Render**
(login copy), which diverges from the documented self-hosted systemd/nginx picture.

## Frontend layers

- **Routing / shell:** `src/App.jsx` (468 LOC) owns the route table, both nav configs,
  desktop+mobile chrome, search, and auth gating (`RequireAuth`, `AdminAccessGate`).
- **Student primary nav:** Home `/`, My Training `/training`, **Practice Library** (dropdown:
  Support Tickets `/tickets`, Guided Labs `/labs`, Networking Labs `/cli-labs`, Capstones
  `/capstones`, Command Library `/commands`, Terminal Practice `/terminal`; **Service Desk Lab
  `/service-desk` is spliced in at position 1 only when `serviceDeskAvailable` flag is on**),
  Progress `/progress`. Capstones child is hidden when `has_unlocked_capstones === false`.
- **Admin nav (workflow-grouped):** Dashboard `/admin`; Learning Content (Modules/Lessons/
  Quizzes, Weekly Training, Study Curriculum, Job Relevance Tags, ExamCompass Import);
  Students `/admin/students`; Assessments & Labs (Ticket Review, Service Desk Lab [flag-gated],
  Labs & VM Assignments, Capstones); System (AI Usage & Costs). Matches CLAUDE.md's intended IA.
- **Redirects (retired routes):** `/learning-path → /training`, `/study-tracker →
  /training/content`, `/admin/review → /admin/ticket-review`.
- **API layer:** all HTTP in `src/services/api.js` (473 LOC) — one `api` client (student) and
  an `adminApi` client, with a `request()` wrapper doing retries + backend warmup.
- **Pages/components:** `src/pages/**` (student + `admin/**`), shared `src/components/**`,
  `src/features/cli-labs/**` (networking simulator, incl. `engine/commandEngine.js` at 930 LOC).

## Backend layers

- **App factory / middleware:** `app/main.py` mounts routers and installs **CORS**, a custom
  **`csrf_origin_validation`** middleware (Origin allowlist built dynamically from CORS config +
  forwarded headers), and a `validation_error_handler`.
- **Routers (28 files, all mounted):** auth, students, onboarding, training, study_tracker,
  quizzes, lesson_notes, tickets, submissions, evidence, labs, cli_labs, capstones, commands,
  resources, flashcards, search, service_desk; admin aggregate (`admin.py` includes
  admin_content, admin_quiz, admin_students, admin_tickets) + admin_curriculum, admin_session,
  admin_training, admin_service_desk. **No unmounted/orphan routers.**
- **Services (37):** domain logic — training_service, progression_service, xp_service/
  xp_calculator, mastery_service, quiz_generator/quiz_progression/quiz_visibility, ticket_
  generator/ticket_grader/ticket_params, service_desk_engine/lab/features/definitions/health,
  onboarding_service, activity_service, squad_service, fsrs_service, a_plus_access,
  methodology_enforcer, auth_service, admin_auth, rate_limiter, ai_service, plus
  **deferred-feature services** (guacamole_service, proxmox_service, cve_service, discord_service).
- **Models (30):** student, progression (roles/gates/methodology), training, learning,
  curriculum_video, quiz, lesson_notes, ticket, incident, evidence, lab, cli_lab, capstone,
  command_reference, service_desk, squad_activity, xp_ledger, mastery, login_streak, onboarding,
  video_watch, flashcard, resource, comptia, app_setting, weekly_lead, ai_usage_log,
  ai_rate_limit, **vm_assignment** (deferred feature).
- **Migrations:** 47 files, single head `0035_service_desk_browser_mvp`.
- **Seeds:** `seed.py` (roles/gates/curriculum), `seed_curriculum.py` (video/quiz catalog),
  `scripts/seed_users.py`, plus `seed_phase_a..g.py`, `seed_quiz_organization.py`.

## Auth & authorization

- **Student:** `auth.py` issues JWT (`/auth/login`) as HttpOnly Secure cookie; `students.py`
  and feature routers resolve the current student and enforce ownership.
- **Admin:** `admin_session.py` + `services/admin_auth.py` — shared `ADMIN_USERNAME/PASSWORD`
  from env; random expiring in-memory session token; `verify_admin` dependency guards admin
  routers (accepts session cookie or `X-Admin-Key`).
- **CSRF:** origin-allowlist middleware (no double-submit token) — satisfied by same-origin
  browser requests. **CORS** origins from `CORS_ORIGINS`/`FRONTEND_URL`.

## Duplicated / overlapping logic (the important part)

1. **Training vs. legacy curriculum systems.** "My Training" (`training.py` + `training_service.py`
   870 LOC + `training_curriculum_seed`, `training_reference_seed`, `training_quiz_mapping`)
   coexists with the older `study_tracker.py` + `learning.py`/`curriculum_video` catalog. The
   retired Learning Path UI is gone but its backend surface likely lingers → investigate dead
   backend learning-path API in Phase 6.
2. **Support Tickets vs. Service Desk.** Two parallel simulated-support subsystems:
   tickets (`tickets.py`, `ticket_generator`, `ticket_grader`, `ticket_params`, `submissions.py`,
   `admin_tickets.py`) and Service Desk (`service_desk_engine` 558 LOC, `service_desk_lab`,
   `service_desk_features`, `service_desk_definitions`, `service_desk_health`, admin_service_desk).
   Distinct data + grading + XP + admin workflows → deep-dived in Phase 9.
3. **Progress / XP / mastery — several calculators.** `progression_service` (491),
   `quiz_progression`, `xp_service` + `xp_calculator` + `xp_ledger`, `mastery_service`,
   plus progress computed inside `training_service`. Risk of divergent completion/XP rules and
   double-award → Phase 7.
4. **Quiz stack breadth.** `quizzes.py` + `admin_quiz.py` + `quiz_generator` + `quiz_visibility`
   + `quiz_progression` + `training_quiz_mapping` + `seed_quiz_organization` — many moving parts
   for one domain → Phase 7/12.
5. **Seeds vs. migrations.** Content/repair logic lives in both migrations and `seed.py`
   (plan explicitly flags MOD-001 prerequisite repair on full seed) → Phase 11.

## Oversized / coupled / hard-to-test modules

- `services/training_service.py` **870 LOC** and `features/cli-labs/engine/commandEngine.js`
  **930 LOC** both exceed the 800-line refactor threshold.
- `routers/students.py` (719) and `routers/admin_content.py` (681) are large routers mixing
  many responsibilities (candidates to split services out) → Phase 12 refactor list.
- Service Desk engine (558) concentrates scenario state, tool behavior, scoring, events.

## Deferred features with live code (premature/dead-code risk)

`guacamole_service.py`, `proxmox_service.py`, `cve_service.py`, `discord_service.py`,
`vm_assignment` model, and "Labs & VM Assignments" admin area exist though Proxmox/Guacamole/VM/
AI integrations are explicitly deferred. `ai_service.py` (344) is wired for AI usage tracking.
Confirm which are dead vs. dormant-behind-flags in Phase 12.

## Testing / deployment (map only; detail in later phases)

- Backend: 40 pytest files / 238 tests. Frontend: 2 Playwright e2e specs + CLI-lab validators.
- Deploy: `docs/DEPLOYMENT.md`; `docker-compose.yml` offers a Postgres path; `scripts/` holds
  backup tooling. Live stack (Cloudflare/Render) to be reconciled with docs in Phase 16.
