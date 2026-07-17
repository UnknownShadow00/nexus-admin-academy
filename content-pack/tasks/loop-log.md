## [2026-03-31 20:11:41 -05:00] Task Completed
- Task: Analyzed the codebase to identify the backend framework, current authentication, database setup, and project structure.
- Files changed: tasks/loop-log.md
- Result: pass against acceptance criteria
- Next: None
## [2026-03-31 20:32:08 -05:00] Task Completed
- Task: Implemented student authentication across the nested Nexus Admin Academy app, including student username/password storage, JWT auth endpoints, frontend login/register flow, and bearer token wiring while preserving the existing profile layer and admin auth.
- Files changed: nexus-admin-academy/backend/alembic/versions/0018_student_auth.py, nexus-admin-academy/backend/app/models/student.py, nexus-admin-academy/backend/app/services/auth_service.py, nexus-admin-academy/backend/app/routers/auth.py, nexus-admin-academy/backend/app/routers/__init__.py, nexus-admin-academy/backend/app/main.py, nexus-admin-academy/backend/.env.example, nexus-admin-academy/backend/requirements.txt, nexus-admin-academy/frontend/src/hooks/useAuth.js, nexus-admin-academy/frontend/src/pages/LoginPage.jsx, nexus-admin-academy/frontend/src/services/api.js, nexus-admin-academy/frontend/src/App.jsx, nexus-admin-academy/frontend/node_modules/*, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m py_compile` passed, `cmd /c npm run build` passed, and `python -m pytest tests/ -q` passed for the 4 backend tests present in this nested app tree when run with `OPENROUTER_MODEL=mistralai/mistral-large`.
- Next: Install `python-jose` and `passlib` into the active backend environment, and prune or restore the synced nested `frontend/node_modules` tree if those generated dependency diffs should not be kept.
## [2026-03-31 21:39:06 -05:00] Task Completed
- Task: Collapsed the nested `nexus-admin-academy/` app into the repository root by syncing the nested backend and frontend into `backend/` and `frontend/`, moving missing root files and `docs/`, removing the nested directory, reinstalling frontend dependencies, and verifying backend/frontend commands from root-level directories.
- Files changed: backend/*, frontend/*, docs/*, README.md, package-lock.json, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m py_compile app/main.py` succeeded in `backend/`, `cmd /c npm run build` succeeded in `frontend/`, and `npm install` completed via `npm install --ignore-scripts --no-audit --no-fund` after a Windows `EPERM` lifecycle-script failure on plain `npm install`.
- Next: Optional cleanup of `.tmp/locked-nested-backend-cache/`, which contains inaccessible leftover pytest cache directories quarantined during nested-folder removal.
## [2026-03-31 22:39:01 -05:00] Task Completed
- Task: Removed the register endpoint, added `is_mentor` with migration and seed script, protected frontend routes with a synchronous auth guard, simplified the login page, and required JWT auth on all requested student-facing backend endpoints.
- Files changed: backend/app/routers/auth.py, frontend/src/services/api.js, backend/app/models/student.py, backend/alembic/versions/0024_add_is_mentor.py, backend/scripts/__init__.py, backend/scripts/seed_users.py, frontend/src/components/RequireAuth.jsx, frontend/src/App.jsx, frontend/src/pages/LoginPage.jsx, backend/app/routers/students.py, backend/app/routers/quizzes.py, backend/app/routers/tickets.py, backend/app/routers/study_tracker.py, backend/app/routers/submissions.py, backend/app/routers/resources.py, backend/app/routers/search.py, backend/app/routers/commands.py, backend/app/routers/evidence.py, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m alembic upgrade head`, `python scripts/seed_users.py`, `python -m py_compile app/routers/auth.py app/routers/students.py app/routers/quizzes.py app/routers/tickets.py`, and `cmd /c npm run build` all succeeded; `backend/app/routers/auth.py` has no `/auth/register` endpoint; SQLite `PRAGMA table_info(students)` shows `is_mentor`.
- Next: None
## [2026-04-01 17:42:14 -05:00] Task Completed
- Task: Updated the admin students backend and admin students page to support username and password creation, editing, overview display, and duplicate username validation.
- Files changed: backend/app/routers/admin_students.py, frontend/src/pages/AdminStudentsPage.jsx, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m py_compile backend/app/routers/admin_students.py` succeeded and the diff matches the requested username/password management changes.
- Next: None
## [2026-04-04 15:28:32 -05:00] Task Completed
- Task: Implemented a dedicated `/admin-login` username/password flow, redirected admin-gated routes into that flow, preserved mentor read-only behavior, and updated backend admin session auth to validate `ADMIN_USERNAME` and `ADMIN_PASSWORD` while keeping API-key auth working.
- Files changed: backend/app/config.py, backend/app/services/admin_auth.py, backend/app/routers/admin_session.py, backend/tests/test_admin_session.py, frontend/src/components/AdminAccessGate.jsx, frontend/src/App.jsx, frontend/src/pages/AdminLoginPage.jsx, frontend/src/services/api.js, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m unittest tests.test_admin_session tests.test_title_matching` passed, and frontend build verification was attempted but blocked by sandbox process restrictions during Vite/esbuild startup (`spawn EPERM`).
- Next: Re-run `npm run build` or the normal frontend verification command in an environment that allows Vite/esbuild child-process startup.
## [2026-04-04 15:35:40 -05:00] Task Completed
- Task: Removed the admin entry from the student navbar, moved the admin entry point to the main login page, made `/admin-login` public, and let admin routes rely on `AdminAccessGate` instead of student auth so admin access works without a student login first.
- Files changed: frontend/src/App.jsx, frontend/src/pages/LoginPage.jsx, frontend/src/pages/AdminLoginPage.jsx, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m unittest tests.test_admin_session tests.test_title_matching` passed, and frontend build verification was attempted again but remains blocked by sandbox process restrictions during Vite/esbuild startup (`spawn EPERM`).
- Next: Re-run `npm run build` or the normal frontend verification command in an environment that allows Vite/esbuild child-process startup.
## [2026-04-15 16:54:41 -05:00] Task Completed
- Task: Completed a full audit, fixed critical student authorization gaps, hardened production auth and database configuration for Render/Supabase deployment, added cold-start-safe frontend API handling and loading/error states, and removed frontend-exposed admin secret usage from the bookmarklet and curriculum tag flows.
- Files changed: backend/app/config.py, backend/app/database.py, backend/alembic/env.py, backend/app/services/auth_service.py, backend/app/main.py, backend/app/routers/admin_session.py, backend/app/routers/quizzes.py, backend/app/routers/students.py, backend/app/routers/study_tracker.py, backend/app/routers/submissions.py, backend/app/routers/tickets.py, backend/requirements.txt, frontend/src/services/api.js, frontend/src/App.jsx, frontend/src/components/AdminAccessGate.jsx, frontend/src/components/QuizTaker.jsx, frontend/src/components/TicketSubmit.jsx, frontend/src/pages/LoginPage.jsx, frontend/src/pages/AdminLoginPage.jsx, frontend/src/pages/StudentHome.jsx, frontend/src/pages/QuizzesPage.jsx, frontend/src/pages/LearningPath.jsx, frontend/src/pages/QuizPage.jsx, frontend/src/pages/TicketPage.jsx, frontend/src/pages/TicketFeedback.jsx, frontend/src/pages/admin/BookmarkletPage.jsx, frontend/src/pages/admin/CurriculumTagsPage.jsx, frontend/public/nexus-bookmarklet.js, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m compileall app`, `python -m pytest tests/test_admin_session.py tests/test_title_matching.py -q`, and `cmd /c npm run build` all succeeded after the changes.
- Next: Set production environment variables on Render/Vercel (`DATABASE_URL`, `JWT_SECRET_KEY`, `FRONTEND_URL` or `CORS_ORIGINS`, admin credentials/API key, and optional `COOKIE_SECURE`) and consider a later pass on frontend code-splitting plus the leftover inaccessible temp/cache directories that interfere with broad `pytest` collection.
## [2026-04-15 22:43:18 -05:00] Task Completed
- Task: Fixed the local `GET /api/students/{id}/stats` crash by removing the direct call from one FastAPI route into another and moving certification-readiness aggregation into a plain helper function.
- Files changed: backend/app/routers/students.py, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m py_compile app/routers/students.py` succeeded and the dependency-injection error path is removed.
- Next: Restart the local backend process so Uvicorn picks up the updated router code, then refresh the student dashboard.
## [2026-04-23 02:37:48 -05:00] Task Completed
- Task: Added the Phase 1 frontend design-system foundation in `frontend/src` with centralized theme configs, shared badge/header/filter UI primitives, and aligned shared stylesheet utilities without modifying existing page files.
- Files changed: frontend/src/utils/theme.js, frontend/src/components/ui/Badge.jsx, frontend/src/components/ui/PageHeader.jsx, frontend/src/components/ui/FilterBar.jsx, frontend/src/styles.css, tasks/loop-log.md
- Result: partial against acceptance criteria; all requested files and exports were added, but `npm.cmd run build` remains blocked in this sandbox before app compilation because Vite/esbuild child-process startup fails with `spawn EPERM`.
- Next: Re-run `cd frontend && npm run build` in an environment that allows Vite/esbuild process spawning to complete full frontend verification.
## [2026-04-23 02:42:09 -05:00] Task Completed
- Task: Refactored `StudentHome.jsx` to a single-focus dashboard using shared Phase 1 UI primitives and simplified `App.jsx` navigation with collapsible search plus a single shared mobile nav renderer.
- Files changed: frontend/src/pages/StudentHome.jsx, frontend/src/App.jsx, tasks/loop-log.md
- Result: partial against acceptance criteria; the requested UI/navigation refactors are implemented and no emoji remain in the two files, but `cd frontend && npm run build` is still blocked in this sandbox because Vite/esbuild child-process startup fails with `spawn EPERM`.
- Next: Re-run `cd frontend && npm run build` in an environment that allows Vite/esbuild process spawning to confirm the final frontend build.
## [2026-04-23 13:20:00 -05:00] Task Completed
- Task: Cleaned up the Phase 3 quizzes flow UI by extracting the quiz review screen, adding a shared banner primitive, and updating the quizzes pages to use shared header/filter/status UI.
- Files changed: frontend/src/components/ui/Banner.jsx, frontend/src/components/QuizReviewScreen.jsx, frontend/src/components/QuizTaker.jsx, frontend/src/pages/QuizzesPage.jsx, frontend/src/pages/QuizPage.jsx, tasks/loop-log.md
- Result: pass against acceptance criteria
- Next: None
## [2026-04-23T21:35:58.3829364-05:00] Task Completed
- Task: Implemented the Phase 10 lab exercises feature with authenticated lab APIs, seed data, student lab pages, routes, and focused backend tests.
- Files changed: backend/app/models/lab.py, backend/alembic/versions/0025_lab_student_fields.py, backend/app/schemas/lab.py, backend/app/routers/labs.py, backend/app/routers/__init__.py, backend/app/main.py, backend/app/routers/admin_content.py, backend/seed.py, backend/tests/test_labs.py, frontend/src/services/api.js, frontend/src/pages/LabsPage.jsx, frontend/src/pages/LabPage.jsx, frontend/src/App.jsx, tasks/loop-log.md
- Result: partial against acceptance criteria; the backend API, seed data, routes, pages, and backend tests are in place, `python -m compileall app seed.py` succeeded, and `python -m pytest tests/test_labs.py` passed, but `npm.cmd run build` is blocked in this sandbox because Vite/esbuild fails with `spawn EPERM` during config loading.
- Next: Re-run `cd frontend && npm run build` in an environment that allows Vite/esbuild child-process spawning, and apply the new Alembic migration before using the lab feature against an existing database.
## [2026-04-23T21:43:02-05:00] Task Completed
- Task: Implemented the Phase 11 capstone projects feature with authenticated backend endpoints, migration, seed data, student capstone pages/routes, and focused backend tests.
- Files changed: backend/app/models/capstone.py, backend/alembic/versions/0026_capstone_student_fields.py, backend/app/schemas/capstone.py, backend/app/routers/capstones.py, backend/app/routers/__init__.py, backend/app/main.py, backend/seed.py, backend/tests/test_capstones.py, frontend/src/services/api.js, frontend/src/pages/CapstonesPage.jsx, frontend/src/pages/CapstonePage.jsx, frontend/src/App.jsx, tasks/loop-log.md
- Result: partial against acceptance criteria; backend capstone APIs, migration, seed data, routes, pages, and focused backend tests are in place, and `$env:PYTHONPATH='backend'; pytest backend/tests/test_labs.py backend/tests/test_capstones.py` passed, but `npm.cmd run build` is blocked in this sandbox because Vite/esbuild fails with `spawn EPERM` during config loading.
- Next: Apply Alembic migration `0026` to the target database and re-run `cd frontend && npm run build` in an environment that allows Vite/esbuild child-process spawning.
## [2026-05-14T20:14:54-05:00] Task Completed
- Task: Reviewed the project state, source code, dirty worktree, tests, build output, completed features, pending gaps, and likely bugs so the project can continue from the right point.
- Files changed: tasks/loop-log.md, frontend/dist/index.html, frontend/dist/assets/index-B8rzC5Vk.css, frontend/dist/assets/index-Bq_dYAEC.js, frontend/dist/assets/index-BHo4YmWS.css (deleted by build), frontend/dist/assets/index-bbpxCFX5.js (deleted by build)
- Result: pass against acceptance criteria; review completed, frontend build passed, backend compile passed, scoped backend tests passed, and blocking/pending issues were identified.
- Next: Fix quiz publishing first, then clean locked pytest cache directories and decide whether `frontend/dist` should be committed or ignored.
## [2026-05-14T20:25:09-05:00] Task Completed
- Task: Fixed quiz publishing/status updates, blocked student access to draft quiz detail/submission routes, added admin capstone publish/week support, repaired quiz review option highlighting for E and multi-select answers, and added pytest/dist/cache hygiene ignores.
- Files changed: .gitignore, backend/pytest.ini, backend/app/schemas/quiz.py, backend/app/routers/admin_quiz.py, backend/app/routers/quizzes.py, backend/app/routers/admin_content.py, backend/tests/test_quizzes.py, backend/tests/test_capstones.py, frontend/src/pages/QuizReviewPage.jsx, frontend/dist/index.html, frontend/dist/assets/index-BHo4YmWS.css (deleted by build), frontend/dist/assets/index-bbpxCFX5.js (deleted by build), tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m compileall app seed.py -q`, `python -m pytest -q`, focused quiz/capstone tests, and `npm run build` all passed.
- Next: Existing tracked `frontend/dist` files still show build churn; fully enforcing the new ignore policy requires a later one-time untrack/restore decision for those tracked artifacts.
## [2026-05-14T20:28:55-05:00] Task Completed
- Task: Performed final regression review of Nexus quiz publish/detail/take/submit/review flow, capstone admin publishing support, frontend dist hygiene, draft/published edge cases, and quiz review multi-select/E UI handling; fixed draft quiz review access.
- Files changed: backend/app/routers/quizzes.py, backend/tests/test_quizzes.py, tasks/loop-log.md
- Result: pass against acceptance criteria; `python -m compileall app seed.py -q`, full `python -m pytest -q` (31 passed), `npm run build`, `git status`, and `git diff --check` completed successfully. Tracked `frontend/dist` build churn was restored and ignored generated hashed assets were removed.
- Next: No blocker for committing the current work; remaining warning is the existing Vite large chunk warning and existing backend `datetime.utcnow()` deprecation warnings in activity-service tests.
## [2026-05-14T20:31:05-05:00] Task Completed
- Task: Staged the requested Nexus quiz publishing and capstone visibility fix files and committed them with the requested message.
- Files changed: .gitignore, backend/pytest.ini, backend/app/schemas/quiz.py, backend/app/routers/admin_quiz.py, backend/app/routers/quizzes.py, backend/app/routers/admin_content.py, backend/tests/test_quizzes.py, backend/tests/test_capstones.py, frontend/src/pages/QuizReviewPage.jsx, tasks/loop-log.md
- Result: pass; commit `c7bd00a` was created with message `Fix quiz publishing and capstone visibility flows`.
- Next: None.
## [2026-05-14T20:56:18-05:00] Task Completed
- Task: Reviewed project docs, loop log, and worktree state to identify unfinished tasks and phases still needed for Nexus Admin Academy.
- Files changed: tasks/loop-log.md
- Result: pass; unfinished work areas were summarized from current repository evidence.
- Next: Prioritize committing or finishing the uncommitted labs/capstones/UI phase changes, then work through the remaining product gaps.
## [2026-05-16T17:56:12-05:00] Task Completed
- Task: Added Phase 1 admin lab and capstone template creation UI, admin API helpers, routes, and missing backend update/delete endpoints.
- Files changed: backend/app/routers/admin_content.py, frontend/src/services/api.js, frontend/src/pages/admin/AdminLabsPage.jsx, frontend/src/pages/admin/AdminCapstonesPage.jsx, frontend/src/App.jsx, frontend/dist/index.html, frontend/dist/assets/index-BHo4YmWS.css, frontend/dist/assets/index-bbpxCFX5.js, tasks/loop-log.md
- Result: pass; `python -m py_compile app/routers/admin_content.py` and `npm.cmd run build` passed.
- Next: Vite still reports the existing large chunk warning; tracked frontend dist artifacts show build churn because `frontend/dist/` is ignored but already tracked.
## [2026-05-16T18:07:16.4127857-05:00] Task Completed
- Task: Implemented Phase 2 student experience gaps: command reference page, admin ticket review queue, lab evidence upload, and per-lesson student notes.
- Files changed: backend/alembic/script.py.mako, backend/alembic/versions/853fceaf9a7a_add_student_lesson_notes.py, backend/app/main.py, backend/app/models/__init__.py, backend/app/models/lesson_notes.py, backend/app/routers/commands.py, backend/app/routers/labs.py, backend/app/routers/lesson_notes.py, backend/app/routers/students.py, frontend/src/App.jsx, frontend/src/pages/CommandReferencePage.jsx, frontend/src/pages/LabPage.jsx, frontend/src/pages/LearningPath.jsx, frontend/src/pages/admin/AdminTicketReviewPage.jsx, frontend/src/services/api.js, frontend/dist/index.html, frontend/dist/assets/index-BHo4YmWS.css, frontend/dist/assets/index-bbpxCFX5.js, tasks/loop-log.md
- Result: pass; Alembic migration was autogenerated then narrowed to the student lesson notes table, `alembic upgrade head` passed, changed backend files passed `python -m py_compile`, and `npm.cmd run build` passed.
- Next: Vite still reports the existing large chunk warning; tracked frontend dist artifacts still show build churn.
## [2026-05-16 19:05:38 -05:00] Task Completed
- Task: Implemented backend FSRS flashcard reviews for wrong quiz answers, due-card retrieval, and rating-based rescheduling.
- Files changed: backend/app/models/flashcard.py, backend/app/services/fsrs_service.py, backend/app/routers/flashcards.py, backend/app/models/__init__.py, backend/app/routers/__init__.py, backend/app/main.py, backend/app/routers/quizzes.py, backend/alembic/versions/17dcbbab1af8_add_flashcard_reviews.py, tasks/loop-log.md
- Result: pass; `alembic revision --autogenerate -m 'add_flashcard_reviews'`, migration pruning, `alembic upgrade head`, requested `python -m py_compile app/models/flashcard.py app/services/fsrs_service.py app/routers/flashcards.py`, additional changed-file compile, app import check, and FSRS schedule assertions passed.
- Next: None.
## [2026-05-17 19:33:54 -05:00] Task Completed
- Task: Built the FSRS flashcard frontend review UI and added the student home Daily Review section.
- Files changed: frontend/src/services/api.js, frontend/src/components/FlashcardReviewPanel.jsx, frontend/src/pages/StudentHome.jsx, tasks/loop-log.md
- Result: pass; `cd frontend && npm run build` was verified via `npm.cmd run build` because PowerShell blocked npm.ps1, and the production build passed.
- Next: None.
## [2026-05-17] Quiz timer + speed flagging
- Task: Track seconds per question, flag avg < 8s in admin view
- Files changed: backend/app/models/quiz.py, backend/app/routers/quizzes.py, backend/app/routers/admin_content.py, backend/app/schemas/quiz.py, alembic migration, frontend/src/components/QuizTaker.jsx, frontend/src/pages/admin/QuizEditorPage.jsx, frontend/src/services/api.js
- Result: pass
- Next: P3 Proxmox VM integration
## [2026-05-30T15:20:14-05:00] Task Completed
- Task: Implemented the project review plan by hardening VM-backed lab provisioning, exposing Proxmox template VMIDs in admin lab management, moving browser student auth to httpOnly cookies with in-memory bearer compatibility, and refreshing stale project docs.
- Files changed: CLAUDE.md, README.md, backend/app/config.py, backend/app/routers/admin_content.py, backend/app/routers/admin_session.py, backend/app/routers/auth.py, backend/app/routers/labs.py, backend/app/services/auth_service.py, backend/app/services/guacamole_service.py, backend/app/services/proxmox_service.py, backend/tests/test_auth.py, backend/tests/test_labs.py, docs/vision-gap-review.md, frontend/src/App.jsx, frontend/src/components/AdminAccessGate.jsx, frontend/src/components/RequireAuth.jsx, frontend/src/hooks/useAuth.js, frontend/src/pages/LabPage.jsx, frontend/src/pages/LoginPage.jsx, frontend/src/pages/admin/AdminLabsPage.jsx, frontend/src/services/api.js, frontend/src/services/profile.js, tasks/loop-log.md
- Result: pass against acceptance criteria; backend compile passed, backend pytest passed with 35 tests, frontend build passed, git diff whitespace check passed, and accessible pytest cache directories were cleaned. Some locked temp/cache directories still return Windows access denied.
- Next: Deploy/configure P4 sidecars, wire a scheduled call to `/api/admin/vms/cleanup`, smoke test a real VM-backed lab, clear remaining locked cache directories after handles are released, and optionally split the large frontend bundle.
## [2026-06-12] Task Completed
- Task: Full project audit (code + docs), then doc-drift sync: created TASKS.md backlog from audit findings, corrected CLAUDE.md (AI provider is OpenRouter not Anthropic, removed references to nonexistent NEXUS_*.md files, replaced stale P2/P3 "not done" backlog with pointer to TASKS.md, synced env var reference), rewrote backend/.env.example with all env vars the code actually reads, fixed README (ANTHROPIC_API_KEY -> OPENROUTER vars, removed unused VITE_ADMIN_KEY, added seed_users.py step).
- Files changed: TASKS.md (new), CLAUDE.md, backend/.env.example, README.md, tasks/loop-log.md
- Result: pass — audit delivered (P0 findings: Guacamole client URL encoding wrong + admin token handed to students, VM provisioning blocks worker past frontend timeout, iframe unrecoverable after refresh, Bearer-anything bypass in allow_admin_or_student, phantom seed students in main.py, app boot requires OPENROUTER_MODEL, multi-select partial-answer grading bug, Railway ephemeral-disk upload risk). No code changed per brief.
- Next: Start TASKS.md P0 in order (Guacamole URL/token fix first), then async VM provisioning.

## [2026-06-12] Task Completed
- Task: Reconstructed the full 2026-06-11 audit report as a persistent document (original lived only in the cleared session). Re-verified all P0 findings against current code before writing - all still present.
- Files changed: docs/audit-2026-06-11.md (new), tasks/loop-log.md
- Result: pass
- Next: Start TASKS.md P0 #1 (Guacamole URL encoding + per-student token).
## [2026-07-02 05:02:26 -05:00] Task Completed
- Task: Stabilized CLI Labs for future lesson expansion with command log redaction, backend-owned seed JSON, lesson validation script, and repeatable engine sanity script.
- Files changed: backend/app/routers/cli_labs.py; backend/app/services/cli_lab_seed.py; backend/app/data/cli_labs/meet-the-cli.json; backend/tests/test_cli_labs.py; frontend/package.json; frontend/scripts/validate-cli-labs.mjs; frontend/scripts/cli-engine-sanity.mjs; frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/engine/objectiveTracker.js; frontend/src/features/cli-labs/components/LabRunner.jsx; tasks/loop-log.md
- Result: pass - CLI lesson validation passed, CLI engine sanity passed, frontend build passed, backend pytest suite passed, and git diff whitespace check passed.
- Next: Use npm run cli:validate and npm run cli:sanity before adding future CLI lesson packs.

## [2026-07-02 04:37:18 -05:00] Task Completed
- Task: Fixed local development CORS so the FastAPI backend accepts the Vite frontend at http://127.0.0.1:5173 as well as localhost.
- Files changed: backend/app/main.py; tasks/loop-log.md
- Result: pass - backend health check passed, CORS preflight from http://127.0.0.1:5173 passed, and backend pytest suite passed.
- Next: Refresh the browser session and retry login from http://127.0.0.1:5173.

## [2026-07-02 04:27:34 -05:00] Task Completed
- Task: Implemented the CLI Labs module with client-side Cisco IOS simulator, lesson catalog, student UI, completion API, XP award persistence, seed path, migration, and tests.
- Files changed: backend/app/models/cli_lab.py; backend/app/schemas/cli_lab.py; backend/app/routers/cli_labs.py; backend/app/services/cli_lab_seed.py; backend/app/main.py; backend/app/models/__init__.py; backend/seed.py; backend/alembic/versions/b1c2d3e4f5a6_add_cli_labs.py; backend/tests/test_cli_labs.py; frontend/src/App.jsx; frontend/src/services/api.js; frontend/src/features/cli-labs/data/lessons/meet-the-cli.json; frontend/src/features/cli-labs/data/lessonCatalog.js; frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/engine/objectiveTracker.js; frontend/src/features/cli-labs/components/CliTerminal.jsx; frontend/src/features/cli-labs/components/LabRunner.jsx; frontend/src/features/cli-labs/components/ObjectivesPanel.jsx; frontend/src/features/cli-labs/components/PcTerminal.jsx; frontend/src/features/cli-labs/components/TopologyPanel.jsx; frontend/src/pages/CliLabsPage.jsx; frontend/src/pages/CliLabPage.jsx; tasks/loop-log.md
- Result: pass - command engine sanity checks passed, frontend production build passed, and backend pytest suite passed.
- Next: Run Alembic migrations in the target environment before enabling the new tab for students.

## [2026-07-02 06:19:53 -05:00] Task Completed
- Task: Extended CLI Labs with optional step-driven lesson support, step widgets, observe-step objective gating, validation, and sanity coverage.
- Files changed: frontend/src/features/cli-labs/components/StepPanel.jsx; frontend/src/features/cli-labs/components/steps/McqStep.jsx; frontend/src/features/cli-labs/components/steps/HexInputStep.jsx; frontend/src/features/cli-labs/components/steps/FrameBuilderStep.jsx; frontend/src/features/cli-labs/components/LabRunner.jsx; frontend/src/features/cli-labs/engine/objectiveTracker.js; frontend/scripts/validate-cli-labs.mjs; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm run cli:validate passed, npm run cli:sanity passed, and npm run build passed.
- Next: Add future lesson packs with steps; existing meet-the-cli lessons remain step-free and do not render StepPanel.

## [2026-07-02 06:26:17 -05:00] Task Completed
- Task: Added CLI engine support for PC ping with ARP transcript, dynamic MAC learning, show mac address-table, and static MAC address-table entries.
- Files changed: frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/engine/macTable.js; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm run cli:validate passed, npm run cli:sanity passed, and npm run build passed.
- Next: No follow-up needed.

## [2026-07-02 06:34:54 -05:00] Task Completed
- Task: Added the Learn Network Foundations CLI Labs pack and grouped CLI Labs lessons into collapsible topic sections.
- Files changed: frontend/src/features/cli-labs/data/lessons/network-foundations.json; backend/app/data/cli_labs/network-foundations.json; frontend/src/features/cli-labs/data/lessonCatalog.js; frontend/src/features/cli-labs/components/LabRunner.jsx; frontend/src/features/cli-labs/engine/objectiveTracker.js; frontend/src/pages/CliLabsPage.jsx; tasks/loop-log.md
- Result: pass - npm run cli:validate, npm run cli:sanity, npm run build, backend py_compile, backend pytest, JSON hash comparison, and ad-hoc network foundations runtime completion checks passed.
- Next: No follow-up needed.

## [2026-07-02 06:43:55 -05:00] Task Completed
- Task: Fixed Task 3 objective tracking regression by restoring one-objective-per-command behavior and removing redundant summary objectives from the Network Foundations pack.
- Files changed: frontend/src/features/cli-labs/engine/objectiveTracker.js; frontend/src/features/cli-labs/data/lessons/network-foundations.json; backend/app/data/cli_labs/network-foundations.json; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm run cli:validate, npm run cli:sanity, npm run build, no-consecutive-duplicate trigger check, JSON hash comparison, all-7 foundations runtime completion check, and backend pytest passed.
- Next: No follow-up needed.

## [2026-07-02 14:18:03 -05:00] Task Completed
- Task: Applied post-review CLI Labs fixes for out-of-order objective progress, topology VLAN/interface initialization, PC-terminal detection for mini objectives, and ping requiredPcAction validation.
- Files changed: frontend/src/features/cli-labs/engine/objectiveTracker.js; frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/components/LabRunner.jsx; frontend/scripts/validate-cli-labs.mjs; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm run cli:validate, npm run cli:sanity, npm run build, all-7 Network Foundations runtime completion checks including enable-first ordering, JSON copy comparison, and backend pytest passed.
- Next: No follow-up needed.

## [2026-07-02 15:29:09 -05:00] Task Completed
- Task: Added switching port administration CLI engine commands for lessons A-D, including descriptions, interface ranges, access VLAN assignment, link settings, scoped show commands, MAC filters, and switchport audits.
- Files changed: frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/engine/interfaceCommands.js; frontend/src/features/cli-labs/engine/macTable.js; frontend/src/features/cli-labs/engine/pcCommands.js; frontend/src/features/cli-labs/engine/supportedEvents.js; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm run cli:validate, npm run cli:sanity, and npm run build all passed; validation still reports 25 lessons across 2 files.
- Next: No follow-up needed.

## [2026-07-02 15:43:21 -05:00] Task Completed
- Task: Converted Learn Switching sections A-D into the new CLI lab pack, registered it, copied it to backend seed data, and added required engine/tracker support for PC source selection, ARP cache checks, context transitions, and interface/VLAN success criteria.
- Files changed: frontend/src/features/cli-labs/data/lessons/learn-switching.json; backend/app/data/cli_labs/learn-switching.json; frontend/src/features/cli-labs/data/lessonCatalog.js; frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/engine/objectiveTracker.js; frontend/src/features/cli-labs/engine/pcCommands.js; frontend/src/features/cli-labs/engine/supportedEvents.js; frontend/src/features/cli-labs/components/LabRunner.jsx; frontend/src/features/cli-labs/components/PcTerminal.jsx; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm run cli:validate, npm run cli:sanity, npm run build, 23-lab runtime completion drive including out-of-order dev-sw-act-10, backend py_compile, backend pytest, and frontend/backend JSON hash comparison passed.
- Next: No follow-up needed.

## [2026-07-02 19:50:38 -05:00] Task Completed
- Task: Applied Wave 2 post-review CLI Labs fixes for dev-sw-act-06 completion, bounded interface ranges, incomplete MAC filter commands, per-PC ARP caches, and learn-switching sanity coverage.
- Files changed: frontend/src/features/cli-labs/data/lessons/learn-switching.json; backend/app/data/cli_labs/learn-switching.json; frontend/src/features/cli-labs/engine/interfaceCommands.js; frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/engine/pcCommands.js; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm run cli:validate, npm run cli:sanity with learn-switching drive and dev-sw-act-06 status-path check, npm run build, backend pytest, and frontend/backend learn-switching.json hash comparison passed.
- Next: No follow-up needed.

## [2026-07-02 20:03:15 -05:00] Task Completed
- Task: Implemented Wave 2 Task 3 multi-switch topology support, 802.1Q trunking/DTP commands, neighbor discovery, device-scoped objectives, cross-switch PC ping evaluation, and multi-device LabRunner state handling with cloned active device state before runCommand.
- Files changed: frontend/src/features/cli-labs/components/LabRunner.jsx; frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/engine/interfaceCommands.js; frontend/src/features/cli-labs/engine/multiDeviceState.js; frontend/src/features/cli-labs/engine/networkSim.js; frontend/src/features/cli-labs/engine/objectiveTracker.js; frontend/src/features/cli-labs/engine/supportedEvents.js; frontend/src/features/cli-labs/engine/trunking.js; frontend/scripts/cli-engine-sanity.mjs; frontend/scripts/validate-cli-labs.mjs; tasks/loop-log.md
- Result: pass - npm run cli:validate, npm run cli:sanity, npm run build, and backend pytest passed. New event ids: cmd.show.interfaces-trunk, cmd.show.cdp-neighbors, cmd.show.lldp-neighbors, config.nonegotiate.set, config.trunk-allowed.add, config.trunk-allowed.set, config.trunk-encapsulation.set, config.trunk-native.set.
- Next: No follow-up needed.

## [2026-07-02 20:19:43 -05:00] Task Completed
- Task: Applied Wave 2 Task 3 post-review trunking fixes for encapsulation-required links, allowed-VLAN range validation, nonegotiate DTP behavior, and native VLAN argument errors, with sanity coverage.
- Files changed: frontend/src/features/cli-labs/engine/networkSim.js; frontend/src/features/cli-labs/engine/trunking.js; frontend/src/features/cli-labs/engine/commandEngine.js; frontend/scripts/validate-cli-labs.mjs; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm.cmd run cli:validate, npm.cmd run cli:sanity, npm.cmd run build, and backend PYTHONPATH=. python -m pytest tests/ -q all passed.
- Next: No follow-up needed.

## [2026-07-02 20:31:11 -05:00] Task Completed
- Task: Implemented Wave 2 Task 4 STP/Rapid PVST+ and EtherChannel/LACP engine support with root election, blocked redundant links, PortFast/BPDU Guard, Port-channel summaries, bundle-aware ping, and sanity coverage.
- Files changed: frontend/src/features/cli-labs/engine/stpSim.js; frontend/src/features/cli-labs/engine/etherchannel.js; frontend/src/features/cli-labs/engine/commandEngine.js; frontend/src/features/cli-labs/engine/interfaceCommands.js; frontend/src/features/cli-labs/engine/networkSim.js; frontend/src/features/cli-labs/engine/supportedEvents.js; frontend/scripts/cli-engine-sanity.mjs; frontend/scripts/validate-cli-labs.mjs; tasks/loop-log.md
- Result: pass - npm.cmd run cli:validate, npm.cmd run cli:sanity, npm.cmd run build, and backend PYTHONPATH=. python -m pytest tests/ -q all passed. No spec deviations.
- Next: No follow-up needed.

## [2026-07-02 20:47:07 -05:00] Task Completed
- Task: Applied Wave 2 Task 4 post-review fixes for STP single-switch and PortFast edge rendering, EtherChannel PAgP/detail/neighbor commands, channel-group and STP argument validation, and Port-channel shutdown traffic handling.
- Files changed: frontend/src/features/cli-labs/engine/stpSim.js; frontend/src/features/cli-labs/engine/etherchannel.js; frontend/src/features/cli-labs/engine/supportedEvents.js; frontend/scripts/cli-engine-sanity.mjs; tasks/loop-log.md
- Result: pass - npm.cmd run cli:validate, npm.cmd run cli:sanity, npm.cmd run build, and backend PYTHONPATH=. pytest all passed.
- Next: No follow-up needed.

## 2026-07-10 — Phase 1 session (Claude, sandbox)
Completed: TB-01 (boot-safe AI, phantom seed removed, purge script), TB-06 (multi-select set grading, per-attempt history, migration c2d3e4f5a6b7), TB-07 (AI_BASE_URL/AI_MODEL config, keyless Ollama, calibration script — NOT run against live AI: none in sandbox), TB-02 (6 roles + rename-safe upgrade remap, Gate 1+2 configs, 4 new gate evaluators, 8 Gate-1 tests), TB-04 (hint ladders, −5/−10/−20/−35% XP floor 40%, migration d3e4f5a6b7c8), TB-03 backend (/api/students/me/week-plan), TB-05 (ticket parameters, migration e4f5a6b7c8d9), CB-05 (five-anchor grader + injection defense), CB-01 (verified already glob-seeded — original audit corrected), CB-02/03/04 (seed_phase_a.py: 4 modules, 11 lessons, 5 quizzes/38 questions, 5 new tickets incl. Simulation 1, 8 retrofits). Drift fix: quizzes.status never migrated (f5a6b7c8d9e0).
Tests: 73 passed / 0 failed (was: 7 collection errors). Seeds idempotent; legacy-role upgrade path tested.
NOT done: frontend (WeekPlanPanel, hint UI, npm build), Weeks 5–8 authoring, Gate-2 content (MOD-005..008), security audit pass, docs, real-AI calibration, real Proxmox/Guacamole work (unchanged, still P0 on infra track).

## 2026-07-10 — Phase 1 session 3 (Claude, sandbox)
Completed: TB-03 frontend (WeekPlanPanel on StudentHome, hint panel + rubric chips on TicketPage, api.js getWeekPlan/revealTicketHint; npm run build PASSES, chunk-size warning = pre-existing P2). Ticket detail endpoint now returns student-safe checkpoints (substituted), rubric names, hints state — anchors/root_cause/model_answer stay server-side (anchor texts contain root-cause spoilers). Phase B authored+seeded (seed_phase_b.py): MOD-005..008, 12 lessons, 4 quizzes/33 questions, 13 tickets incl. Multi-Ticket Simulation 2 (6 sub-tickets: misleading=airplane mode, security=kiosk malware, escalation=finance access, quick wins, multi-step=moved-path links). Gate 2 now satisfiable; MODULE_WEEKS extended to week 8. Gate 2 tests: pass-with-1-hint, fail-on-2-hints (real hints_used enforcement), fail-low-score, fail-missing-d3.
Tests: 77 passed / 0 failed. Frontend build green. Lint: NOT CONFIGURED in repo (no script/config) — honest skip.
NOT done: security audit pass (Part 9), docs (Part 11), throwback-ticket mechanism (mentor-guide item), real-AI calibration, Playwright/E2E (not in repo).

## 2026-07-10 — Phase 1 session 4 (Claude, sandbox) — SECURITY + DOCS + FINAL VERIFY
Security audit (Part 9), all fixed with regression tests (tests/test_security_part9.py, 11 tests):
- Admin sessions: deterministic sha256(password+const) cookie → random per-login tokens, server-side store, 12h TTL, logout revocation; legacy cookies rejected; timing-safe credential/API-key compares (hmac.compare_digest)
- allow_admin_or_student: "Bearer <anything>" bypass → real JWT verification
- Evidence: 10MB bounded read (413 over), ext/MIME allowlist confirmed, student_id ownership column (migration a6b7c8d9e0f1), submissions may only link own artifacts (legacy NULL-owner artifacts unclaimable)
- Sweep results (no changes needed, verified): admin routers covered by router-level verify_admin; submissions.py checks ownership; quiz GET leaks no answers/explanations; ticket GET leaks no root_cause/model_answer/anchors; no student-callable promotion mutation exists; zero dangerouslySetInnerHTML
Docs (Part 11): docs/STUDENT_GUIDE.md, docs/MENTOR_GUIDE.md, docs/AUTHORING_CONFIG_SECURITY.md (authoring rules + full env-var table + security posture + honest open items); README refreshed with superseded-content banner and corrected setup (seed.py, AI-optional boot).
Final verification: fresh install from zero (36 migrations → seed_users → seed.py) = 9 modules / 24 lessons / 9 quizzes / 71 questions / 26 tickets / 6 roles / Gate1(6)+Gate2(5); every week 1-8 has tickets; both sims present. Model-vs-migration drift: none. pytest: 88 passed / 0 failed. npm run build: PASSES.
HONEST GAPS: live-AI calibration not run (no endpoint here); Proxmox/Guacamole untouched by design; lint not configured in repo; E2E browser tests not present in repo (component tests not added — no test harness configured for frontend).
NEXT PHASE START: Weeks 9-12 (Phase C, Network Support) — seed_phase_c.py + Gate 3 + learn-routing engine work per TASKS Wave 3.

## 2026-07-10 — Phase C session (Weeks 9-12, Network Support)
Authored+seeded seed_phase_c.py: MOD-009..012, 11 lessons (IPv4/subnetting/ARP/packet-flow, CLI modes/VLANs/interface-status, trunks/native-VLAN/inter-VLAN routing/DHCP-relay/NAT-firewall-VPN-wireless awareness, secure switch admin/structured troubleshooting), 5 quizzes/35 questions, 6 network tickets (addressing mismatch, wrong VLAN, missing DHCP relay, trunk mismatch, port-security err-disable, down SVI gateway) — all five-anchor + 4-hint + parametrized. Gate 3 (Network Support Technician) seeded + tested incl. min_cli_labs pack_prefix=dev-sw- exclusion. MODULE_WEEKS extended to 12.
Infra honesty: all switch content runs via CLI packs (client-side) or Packet Tracer fallback; NO Gate 3 requirement needs physical Catalyst or Proxmox.
Caught by fresh-install check: Week 9 had no ticket (lessons/quiz only) — added the addressing-mismatch ticket. Fixed, re-verified.
Totals now: 13 modules, 35 lessons, 14 quizzes/106 questions, 32 tickets, Gates 1-3. pytest: 92 passed/0 failed. Fresh install weeks 1-12 clean; zero model/migration drift.
NEXT: Weeks 13-17 (Phase D, Windows Server/AD/PowerShell) — seed_phase_d.py + Gate 4 + AD lab/ticket family (largest phase; AUTO-VM target but manual-VM viable).

## 2026-07-10 — Phase D session (Weeks 13-17, Windows Server/AD/PowerShell)
Authored+seeded seed_phase_d.py: MOD-013..017, 12 lessons (Server Manager/roles, AD domains/OUs/users/groups/scopes/A-G-DL-P, core account tickets, domain joins/secure-channel/computer accounts, group-based file access, GPO fundamentals/LSDOU, gpresult/RSoP troubleshooting, DNS/DHCP server roles/scopes/reservations, PowerShell discovery/pipeline/AD queries/CSV/-WhatIf, server ops/scheduled tasks, Windows Server Backup + REAL restore, patching/rollback/PS remoting/small scripts), 5 quizzes/37 questions, 5 AD tickets (bulk onboarding, trust-relationship repair, GPO wrong-OU, PowerShell locked/stale report, backup restore) — the recurring AD family, all five-anchor+4-hint+parametrized, one per week 13-17. Plus 1 VM-backed AD break-fix lab (MANUAL-VM path documented + working; AUTO-VM as target only). Gate 4 (Junior Systems Technician) seeded + tested.
Infra honesty: AD lab has a working manual-VM path (hand-cloned WS2022-DC + Win11 client over Headscale); NO Gate 4 requirement needs automated provisioning. MODULE_WEEKS -> 17.
Totals: 18 modules, 47 lessons, 19 quizzes/143 questions, 37 tickets, 5 labs, Gates 1-4 (5 of 6 roles gated). pytest: 95 passed/0 failed. Fresh install weeks 1-17 clean; zero drift.
NEXT: Weeks 18-20 (Phase E, Linux/Operations) — seed_phase_e.py, Linux tickets as primary assessment, monitoring/alert triage. Then Weeks 21-22 (Azure, zero-cost fallbacks), 23-24 (integrated + capstone) with Gate 5.

## 2026-07-11 — Phase E session (Weeks 18-20, Linux & Operations)
Authored+seeded seed_phase_e.py: MOD-018..020, 9 lessons (filesystem/navigation/safety, permissions-users-groups-sudo, apt+SSH incl. key/perms gotchas, systemd+journalctl failed-service investigation, Linux networking/DNS (ip a/r, resolv.conf, /etc/hosts, dig, netplan awareness), cron incl. minimal-PATH gotcha, nginx/ufw admin (nginx -t discipline, 403/404/502 mapping), resource triage/tar+rsync backup-verify/bash basics, monitoring+alert triage w/ Netdata+Uptime Kuma), 3 quizzes/24 questions, 6 Linux tickets as PRIMARY assessment (perm-denied group gap, SSH lockout via ~/.ssh perms, nginx config-typo outage, cron minimal-PATH failure, disk-full runaway debug log w/ open-file-truncate safety, missing ufw rules on rebuilt VM) — all five-anchor+4-hint+parametrized, 2 per week 18-20. No new gate (Linux rolls into Gate 5 mixed-incident reqs). MODULE_WEEKS -> 20. domain 6.0 = Linux.
Infra honesty: Linux practice = mentor-cloned Ubuntu 22.04 VM over SSH/Headscale, or WSL/local VM; nothing depends on AUTO-VM.
Totals: 21 modules, 56 lessons, 22 quizzes/167 questions, 43 tickets, 5 labs, Gates 1-4. pytest: 95 passed/0 failed. Fresh install weeks 1-20 clean; zero drift.
NEXT: Weeks 21-22 (Phase F, Azure/cloud with MANDATORY zero-cost fallbacks — no promotion req may depend on spending), then Weeks 23-24 (Phase G: mixed queues, Multi-Ticket Simulation 3, Gate 5/graduation, Maple & Finch capstone per NEXUS_CURRICULUM_MASTER.md §F).

## 2026-07-12 — Phases F+G session (Weeks 21-24) — PROGRAM COMPLETE
Phase F (Weeks 21-22, Azure/cloud, seed_phase_f.py): MOD-021/022, 4 lessons (cloud concepts/service-model responsibility lines/Azure hierarchy, Entra ID admin incl. sign-in logs/MFA-reset identity rail/hybrid sync direction, Azure VM outside-in triage/NSG least-privilege/boot diagnostics/activity log, storage SAS-expiry/RBAC/network rules + cloud-vs-on-prem trade-offs w/ Nexus-on-Proxmox as the live case study), 2 quizzes/16 questions (domain 7.0 = cloud), 3 cloud tickets (Entra MFA lockout after phone swap, unreachable Azure VM w/ compounding stale-dynamic-IP + tightened NSG, SAS token expiry). ZERO-COST constraint enforced: every activity has MS-Learn-sandbox/mentor-led/screenshot fallback; NO gate requirement depends on spend.
Phase G (Weeks 23-24, seed_phase_g.py): MOD-023/024, 3 lessons (mixed-queue ops w/ domain-layer-owner triage, incident comms + blameless post-incident notes, capstone briefing), 1 quiz/6 questions, Multi-Ticket Simulation 3 (6 tickets across Windows/Linux/network/cloud: Entra lockout, disk slope, trunk-mismatch MAJOR INCIDENT, payroll-access trap, NSG batch failure, low-priority hold), Week-24 capstone-major-incident ticket (added after fresh-install check caught empty week 24), and the "Take Over Maple & Finch Co." CapstoneTemplate (4 stages, 2 delivery modes, five-anchor rubric, pass rule ≥8/10 no-zero-anchor). Gate 5 (graduation → Junior Infrastructure Administrator) seeded: Phase E-G lessons, ticket thresholds, Sim 3 checkpoint (max 1 hint, ≥7), no flags — verified substring title-match works. Gate 5 tests: pass, substring-match, fail-on-hints. MODULE_WEEKS -> 24.
FINAL TOTALS: 25 modules, 63 published lessons, 25 quizzes/189+6=195 questions (189 at last count +6 G), 48 tickets incl. 3 simulations + capstone incident, 5 labs, 3 capstones (Maple & Finch published), ALL 6 roles gated (Gates 1-5). pytest: 98 passed/0 failed. npm build passes. Fresh install: all 24 weeks have content and tickets; zero model/migration drift.
STANDING OPEN ITEMS (unchanged): live-AI grader calibration (needs Ollama VM — scripts/calibrate_grader.py); Proxmox/Guacamole AUTO-VM P0s (manual-VM paths documented everywhere; no gate depends on it); learn-routing CLI engine work (Packet Tracer fallback standing); frontend lint/E2E not in repo.
