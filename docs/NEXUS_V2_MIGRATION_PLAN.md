# Nexus V2 — Migration Plan

Status: **Phase 0 (planning only).** Inventory of the current system and the
additive-first path to the V2 structure in `docs/NEXUS_V2_PRD.md`. No
migrations, schema changes, data changes, or deploys are performed by this
document.

Companion: `docs/NEXUS_V2_PRD.md`, `docs/CURRICULUM_CONTENT_STANDARD.md`,
`docs/PROGRESSION_CONTRACT.md`, `docs/CURRICULUM_STRUCTURE.md`.

---

## 0. Ground truth about production (do not skip)

- `backend/nexus.db` **is the live production database** for
  `nexus-admin-academy.service` (systemd, uvicorn, SQLite, Cloudflare tunnel,
  nginx frontend container, separate `service-desk-app` Next.js container).
  ~5–7 real students, Alembic head `0061`, 57 tables.
- Alembic history is immutable. Every schema change is a new reversible
  migration. SQL stays portable across SQLite and PostgreSQL.
- No production mutation happens without fresh, explicit, per-turn
  authorisation and the backup/verify sequence in the project `CLAUDE.md`.
- V2 is **additive first**. Old tables and student history stay until the
  §12 cutover acceptance criteria are met.

---

## 1. Current-system inventory

Legend: **KEEP** (used as-is in V2) · **REFACTOR** (kept but reworked onto V2
structure) · **ARCHIVE** (data preserved, code paths retired, not read by V2)
· **DELETE LATER** (removable only after §12 acceptance criteria pass).

### 1.1 Week / calendar architecture

| Item | Where | Disposition | Notes |
|---|---|---|---|
| `TrainingWeek` (weeks 0–24, extended to 34) | `models/training.py` | **REFACTOR → DELETE LATER** | Authoritative *sequencing + prerequisite* container today, not just display. V2 module ordering replaces it. |
| `TrainingWeekActivity` (`stable_id`, `activity_type`, `content_ref`, `prerequisite_activity_id`, `prerequisite_mode`) | `models/training.py` | **REFACTOR → DELETE LATER** | The real "what activity comes next" list. V2 attaches activities to modules. |
| `curriculum_structure.py` `STAGES` / `MODULES` metadata (stage.*, module.*) | `services/curriculum_structure.py` | **REFACTOR** | Presentation-only mapping week→module→stage. Becomes redundant once V2 has native module tables; its stable IDs and intended ordering are useful migration input. |
| `intended_module_sequence()` + `SEQUENCE_DRIFT` / `MODULE_WEEK_MISSING` validators | `services/curriculum_structure.py`, `services/training_service.py` | **ARCHIVE** after cutover | Exists only to keep two orderings in sync; V2 has one. |
| `MODULE_WEEKS`, `CLI_PACK_WEEKS` compat maps | `services/training_service.py` | **DELETE LATER** | Legacy-content → source-week bridges. |
| `derive_current_week` / `_active_weeks` / `_build_state` | `services/training_service.py` | **REFACTOR** | Rebuild against module order. |
| `training_service.next_activity` ("Today" / "Continue" source) | `services/training_service.py` (~72 KB) | **REFACTOR** | Keep the "single next activity" idea; re-point at module path. |

### 1.2 Weekly routes / pages

| Route / page | Where | Disposition |
|---|---|---|
| `/training/week/:weekId` → `TrainingWeekPage` | `frontend/src/App.jsx`, `pages/TrainingWeekPage.jsx` | **DELETE LATER** (redirect to module route during cutover) |
| `/training/module/:moduleId` → `TrainingWeekPage` (same component) | `App.jsx` | **REFACTOR** → becomes the real module page |
| `/learning-path` → `TrainingDashboardPage`, `/training` redirect | `App.jsx` | **REFACTOR** → certification/module browser |
| `/skills` → `TrainingProgressPage`, `/progress` redirect | `App.jsx` | **REFACTOR** → progress view |
| `/admin/training` → `AdminTrainingPage` (week + activity CRUD, reorder, validation) | `App.jsx`, `routers/admin_training.py` | **REFACTOR** → module/lesson CRUD on V2 tables |
| Backend `routers/training.py` (student week payloads) | mounted in `main.py` | **REFACTOR** |
| Legacy training URL guard tests | `backend/tests/` | **REFACTOR** with routes |

### 1.3 Week-based quiz fields

| Field | Where | Disposition | Notes |
|---|---|---|---|
| `quizzes.week_number` (NOT NULL, CHECK 0–24) | `models/quiz.py` | **REFACTOR** | Becomes nullable / dropped; replaced by `certification_version_id` + `module_key` + `assessment_role`. CHECK 0–24 already strained by extended content (weeks 25–34). |
| `quizzes.recommended_week`, `quizzes.prerequisite_week` (CHECK 0–24) | `models/quiz.py` | **DELETE LATER** |
| `quizzes.show_in_weekly_checklist` | `models/quiz.py` | **REFACTOR** → "is module assessment" |
| `quizzes.is_required`, `quiz_purpose` (`required`/`practice`/`remediation`/`cumulative`/`gate`/`certification`) | `models/quiz.py` | **KEEP / REFACTOR** — maps cleanly to V2 assessment roles (Quick Check / Module Quiz / Knowledge Review / Practical Final) |
| `quiz_progression.required_quizzes_for_week(week)` / `is_quiz_passed` (`QUIZ_PASS_PERCENT = 70`) | `services/quiz_progression.py` | **REFACTOR** | Re-key from week to module. 70% pass rule is reusable as the module-quiz pass rule. |
| `tickets.week_number`, `lab_templates.week_number`, `capstone_templates.week_number` | respective models | **REFACTOR** | Re-map to module. |
| Migrations named `00xx_weeks_*`, `0039_week20_required_path` | `backend/alembic/versions/` | **KEEP (immutable history)** | Never edited/deleted; superseded by new migrations. |

### 1.4 Old progression logic

| Item | Where | Disposition | Notes |
|---|---|---|---|
| 5 role promotion gates (`min_completed_lessons`, `min_mastery_by_domain`, `min_service_desk_passes`, `min_cli_labs`, `required_quiz`, `no_unresolved_flags`) | `seed.py` `PROMOTION_GATES`, `services/progression_service.py` | **KEEP / REFACTOR** | Authoritative and well-tested (`PROGRESSION_CONTRACT.md`). Re-key gate configs from "week 4/8/12/17/23" to module keys. Not deleted. |
| `_check_*` evaluators + `promotion_gate_validation.py` | `services/progression_service.py` | **KEEP / REFACTOR** | Keep the generic evaluator pattern. |
| `Module.unlock_threshold` (default 70) on the `modules` table (MOD-000..MOD-034) | `models/learning.py` | **REFACTOR** | This is a *second* "module" concept, separate from `curriculum_structure.MODULES` and `TrainingWeek`. V2 unifies to one module entity. |
| `get_module_mastery` (50/50 quiz/lab split) | `services/progression_service.py` | **REFACTOR** |
| `student_domain_mastery` + `mastery_service.py` (weighted quiz/ticket → `mastery_percent`, ×10 scaling, domains `1.0`–`5.0`) | `models/mastery.py`, `services/mastery_service.py` | **KEEP** for domain mastery gates; **REFACTOR** domain ids to real per-certification objective domains |
| `comptia_objectives` + `student_objective_progress` (A+ only, unversioned) | `models/comptia.py` | **REFACTOR** → generalised `objectives` keyed by `certification_version` |
| `_check_no_flags` (vacuous since `0043`) | `services/progression_service.py` | **ARCHIVE** — leave failing-closed, do not build on it |
| Legacy ticket-based evaluators `_check_ticket_requirement`, `_check_practical_checkpoint` | `services/progression_service.py` | **DELETE LATER** — unreachable, kept for stray historical rows |

### 1.5 The 40% completion threshold (explicit — do not leave implicit)

**What it is:** `DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT = 40` in
`backend/app/services/a_plus_access.py`. It gates hands-on access on the
percentage of **A+ curriculum videos** (`curriculum_videos` with
`exam_code in ("220-1201","220-1202")`) a student has marked watched
(`video_watches`). Overridable at runtime via `AppSetting` key
`a_plus_unlock_threshold_pct`.

**Every reference to inventory before removal (grep targets):**

| Reference | File | Kind |
|---|---|---|
| `DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT = 40` | `services/a_plus_access.py` | constant |
| `A_PLUS_UNLOCK_THRESHOLD_KEY = "a_plus_unlock_threshold_pct"` | `services/a_plus_access.py` | setting key |
| `get_a_plus_unlock_threshold`, `set_a_plus_unlock_threshold`, `get_a_plus_progress` (`a_plus_unlocked`, `a_plus_progress_pct`) | `services/a_plus_access.py` | functions |
| `A_PLUS_EXAM_CODES = ("220-1201", "220-1202")` | `services/a_plus_access.py` | hardcoded version list (also a §1.6 objective-versioning problem) |
| `GET/PATCH /api/admin/content/settings/a-plus-unlock` | `routers/admin_content.py` (~L54–66) | admin endpoint |
| Callers of `get_a_plus_progress` / `a_plus_unlocked` | `routers/labs.py`, `routers/students.py`, `routers/cli_labs.py` (confirm by grep at implementation time) | consumers — labs/CLI-lab gating |
| Frontend display of `a_plus_progress_pct` / unlock state | `pages/LabsPage.jsx`, `pages/CliLabsPage.jsx`, `services/api.js` (confirm by grep) | UI |
| `AppSetting` row `a_plus_unlock_threshold_pct` in production DB | `app_settings` table | data |
| Tests referencing `a_plus_unlock` / `a_plus_progress` | `backend/tests/` | tests |

**Migration decision (from the PRD):** the V2 **module assessment / practical
completion** system *replaces* this gate. There must not be two progression
gates for the same surface.

**How it is removed without conflict:**

1. **Additive phase:** leave `a_plus_access.py` running unchanged. V2 module
   gating is built in parallel and does not consult it.
2. **MVP phase:** MVP A+ modules gate hands-on strictly on their own V2
   module-assessment rule. Confirm (test) that no MVP module path calls
   `get_a_plus_progress`.
3. **Cutover phase:** set the production `AppSetting`
   `a_plus_unlock_threshold_pct = 0` (after backup) so the legacy gate is a
   no-op for every student, *then* delete `a_plus_access.py`, its endpoint,
   its callers, and its tests in one migration/PR. The `AppSetting` row is
   dropped by that migration's `upgrade`, restored by its `downgrade`.
4. **Acceptance before deletion:** see §12, criterion C4.

`video_watches` / `curriculum_videos` themselves are **KEEP** — video
completion remains tracked learning activity in V2, just not a gate.

### 1.6 Objective tracking / certification versioning

| Item | Where | Disposition |
|---|---|---|
| `comptia_objectives` (`domain`, `objective_number`, `objective_text`, `subtopics`) | `models/comptia.py` | **REFACTOR** → `objectives` FK to `certification_versions` |
| `student_objective_progress` | `models/comptia.py` | **KEEP / REFACTOR** (re-point FK) |
| `curriculum_videos.exam_code` (free-text `"220-1201"` etc.) | `models/curriculum_video.py` | **REFACTOR** → FK to `certification_versions` |
| `A_PLUS_EXAM_CODES` constant | `services/a_plus_access.py` | **DELETE LATER** — versions must be data |
| `quizzes.domain_id` default `"1.0"`, `student_domain_mastery.domain_id` (`1.0`–`5.0`) | `models/quiz.py`, `models/mastery.py` | **REFACTOR** → per-certification-version domain keys |

### 1.7 Quiz / question architecture

| Item | Where | Disposition | Notes |
|---|---|---|---|
| `quizzes` (`editorial_status`, `source_type`, `answer_keys_validated`, `explanations_complete`, `is_active`, `quiz_purpose`) | `models/quiz.py` | **KEEP / REFACTOR** | Strong editorial/visibility model. Add `certification_version_id`, `module_key`, `assessment_role`. Drop week fields (§1.3). |
| `quiz_visibility.student_visible_quiz_filters()` (published + active + editorial `validated` + answer keys validated) | `services/quiz_visibility.py` | **KEEP** | Reuse verbatim as the V2 visibility rule. |
| `questions` (`option_a`–`option_h`, `correct_answer` CHAR(1), `correct_answers` CSV for multi, `explanation`, `difficulty`, `tags`, `source`, `fingerprint`, `import_filename`, `seed_key`, `flagged_for_review`) | `models/quiz.py` | **KEEP / EXTEND** | Add: `certification_version_id`, `objective_code(s)`, `importance`, `learning_relationship` (nullable), `question_type` (extend enum), `acceptable_answers`, `expected_concepts`, `source_name`, `source_url`, `permission_status`, `active`. Extend, **do not** create a parallel table (domain-boundary rule). |
| `question_type` support: `single` / `multi` / `true_false` only | `services/question_validation.py` | **EXTEND** → add `short_answer`, `free_response` with `acceptable_answers` / `expected_concepts` / rubric validation |
| `quiz_attempts` (per-attempt rows, `answers`/`results` JSON, `score`, `best_score`, `time_per_question`) | `models/quiz.py` | **KEEP** — historical attempts preserved |
| `quiz_assignments` (mentor assignment) | `models/quiz.py` | **KEEP** |
| `quiz_generator.py`, `quiz_editorial_mapping.py`, `training_quiz_mapping.py`, `seed_question_sync.py`, `verified_question_corrections.py`, `question_explanation_catalog.py` | `services/` | **REFACTOR** — re-key week→module; keep editorial tooling |
| Hardcoded question content in `seed_phase_a..g.py`, `seed.py`, `training_curriculum_seed.py` | `backend/` | **ARCHIVE** — migrate useful questions to XLSX (§9), then stop running for V2 content |
| Flashcards (`flashcard_reviews`, FSRS `fsrs_service.py`) built from wrong quiz answers | `models/flashcard.py` | **KEEP** — re-point at V2 questions |

### 1.8 Lesson / module architecture

| Item | Where | Disposition | Notes |
|---|---|---|---|
| `modules` table (`code` MOD-000..034, `unlock_threshold`, `prerequisite_module_id`, `module_order`, `target_role`) | `models/learning.py` | **REFACTOR** → one of the three "module" concepts; folded into V2 `cert_modules` |
| `lessons` table (`module_id`, `video_url`, `summary`, `outcomes` JSON, `lesson_order`, `related_activity_stable_id`, `required_notes_template`, `status`) | `models/learning.py` | **REFACTOR / EXTEND** → add `certification_version_id`, `domain_key`, `importance`, `learning_relationship`, `builds_on`, `objective_codes`, Markdown body source path |
| `student_lesson_progress` (server-stamped `viewed_at` / `completed_at`) | `models/lesson_progress.py` | **KEEP** — authoritative lesson completion, preserved |
| `student_lesson_notes` (`lesson_notes.py` router) | `models/lesson_notes.py` | **KEEP** |
| Markdown lesson drafts | `references/lesson-drafts/*.md` | **KEEP** — the format V2 standardises on |
| `curriculum_structure.MODULES` stage grouping | `services/curriculum_structure.py` | **REFACTOR** — see §1.1 |

**Finding:** there are **three overlapping "module/stage" notions** today —
the `modules` table (MOD-* codes, used by promotion gates), the
`curriculum_structure.MODULES` presentation metadata (stage.* / module.*
stable IDs), and the `training_weeks` sequencing containers. V2 collapses
these into **one** `cert_modules` entity.

### 1.9 Current importer (CSV/XLSX)

| Item | Where | Disposition |
|---|---|---|
| `question_importer.py` (parse CSV/XLSX, `sanitize_text` formula-injection guard, `compute_fingerprint` sha256 dedup, `preview_rows` / `confirm_import` two-phase txn, imports as draft/unreviewed/invisible) | `services/question_importer.py` | **KEEP / EXTEND** — the PRD's preferred question workflow already exists |
| Template columns: `quiz_title, question_type, question_text, option_a..h, correct_answers, explanation, difficulty, tags, source, published` | `question_importer.TEMPLATE_COLUMNS` | **EXTEND** — add `certification`, `certification_version`, `domain`, `module`, `objective_code`, `importance`, `acceptable_answers`, `expected_concepts`, `source_name`, `source_url`, `permission_status`, `active` |
| `/api/admin/quiz/import/{template,preview,preview/error-report,confirm}` | `routers/admin_question_import.py` | **KEEP / EXTEND** |
| `QuestionImportPage.jsx` (`/admin/question-import`) | frontend | **KEEP / EXTEND** |
| `examcompass_scraper.py` + `BookmarkletPage.jsx` (`/admin/bookmarklet`) ExamCompass import path | `services/`, frontend | **KEEP but gate on `permission_status`** — see §1.13 licensing question |
| `question_validation.py` (shared canonical validator) | `services/` | **KEEP / EXTEND** (§1.7) |

There is currently **no importer for lessons, resources, or interview
prompts** — V2 adds idempotent data-file loaders for those (Markdown for
lessons; XLSX/CSV for resources and prompts).

### 1.10 Labs

| Item | Where | Disposition |
|---|---|---|
| `lab_templates` / `lab_runs` (`environment_requirements`, `break_script`, `success_criteria`, `required_evidence`, `hints`, `model_solution`, `proxmox_template_vmid`, `structured_feedback`) | `models/lab.py`, `routers/labs.py` | **KEEP / REFACTOR** — swap `week_number` for `module_key` |
| `evidence_artifacts` + `evidence_validator.py` (bounded reads, allowed types, safe filenames, ownership) | `models/evidence.py`, `routers/evidence.py` | **KEEP** |
| Capstones (`capstone_templates` / `capstone_runs`) | `models/capstone.py`, `routers/capstones.py` | **KEEP / REFACTOR** — map to Certification Practical Final where appropriate |
| Incidents / RCA (`incidents`, `incident_tickets`, `rca_submissions`) | `models/incident.py` | **ARCHIVE** unless reused by V2 Mixed Support Shift — currently thinly used |
| `final_shift` / `integrated_support_final_shift.py` / `network_linux_cloud_practical.py` / `windows_ad_server_practical.py` (large practical seed services) | `services/`, `routers/final_shift.py` | **KEEP / REFACTOR** — valuable practical content; re-key to modules |

### 1.11 CLI labs

| Item | Where | Disposition |
|---|---|---|
| `cli_lab` / `cli_lab_attempt` (`compartment_id`, `vendor_id`, `content` JSON, `command_log`) | `models/cli_lab.py`, `routers/cli_labs.py` | **KEEP** |
| `features/cli-labs` simulator (xterm engine, `data/lessons/*`) | `frontend/src/features/cli-labs/` | **KEEP** — already data-driven, matches PRD |
| `cli_lab_seed.py` | `services/` | **REFACTOR** — data-file loader, re-key to modules |
| `min_cli_labs` promotion-gate evidence | `progression_service.py` | **KEEP** |

### 1.12 Proxmox

| Item | Where | Disposition |
|---|---|---|
| `proxmox_service.py` (proxmoxer, token auth, linked/full clone, start, guest-agent IP, destroy; VMID pool 200–299; env `PROXMOX_HOST/TOKEN_ID/TOKEN_SECRET/NODE`) | `services/proxmox_service.py` | **KEEP — do not rebuild** |
| `vm_assignments` (`vmid`, `lab_run_id`, `guac_conn_id`, `guac_username`, `expires_at`, retry/error fields) | `models/vm_assignment.py` | **KEEP** |
| `DELETE /api/admin/vms/cleanup`, `GET /api/admin/vms/assignments` | `routers/admin_content.py` | **KEEP** |
| Not-yet-enabled-for-students status | `TASKS.md` | unchanged — infra acceptance test still pending, independent of V2 |

### 1.13 Guacamole

| Item | Where | Disposition |
|---|---|---|
| `guacamole_service.py` (admin token, per-assignment temp user with READ on one RDP connection, scoped client URL, cleanup; env `GUACAMOLE_URL/ADMIN_USERNAME/ADMIN_PASSWORD/DATASOURCE`) | `services/guacamole_service.py` | **KEEP — do not rebuild** |

### 1.14 Service Desk

| Item | Where | Disposition |
|---|---|---|
| **Modern simulator** — `service_desk_scenarios` → `service_desk_scenario_versions` (immutable published definition + hash) → `service_desk_attempts` → append-only `service_desk_attempt_events` (`trusted` flag) → `service_desk_attempt_grades` | `models/service_desk.py` | **KEEP** — core asset |
| Deterministic server-side grading, process rubric Investigation 15 / Diagnosis 25 / Remediation 30 / Verification 20 / Documentation 10 (`PROCESS_CATALOG_VERSION "process-v3"`, `RUBRIC_VERSION "server-process-v3"`) | `services/service_desk_grading.py`, `services/service_desk_objectives.py` | **KEEP** — already matches the PRD's process philosophy and rubric requirements |
| Experience modes `guided`/`practice`/`assessment`; modes `learning`/`simulation`; 3-attempt policy; admin reset; beta enrollment allow-list | `models/service_desk.py`, `routers/service_desk.py` | **KEEP** — maps to the Guided → Assisted → Independent → Mixed Support Shift ladder |
| `service_desk_progression.py`, `service_desk_objectives.py` mapping to objectives | `services/` | **KEEP / REFACTOR** — point objective refs at V2 `objectives` |
| Admin scenario CRUD + version + validate + publish endpoints | `routers/admin_service_desk.py` | **KEEP** — backend for a future Scenario Builder already exists |
| Standalone `service-desk-app/` Next.js app + `service_desk_bridge.py` JWT bridge + `AdminServiceDeskReviewPage.jsx` | repo subdir, `routers/`, frontend | **KEEP as-is** for V2 (decision — see §11). Student "Tickets" nav links out to it. |
| `min_service_desk_passes` promotion-gate evidence (server-derived `passed`, ownership-filtered) | `progression_service.py`, `PROGRESSION_CONTRACT.md` §A | **KEEP** — re-key gate configs from packs-per-week to packs-per-module |

### 1.15 Old / legacy tickets

| Item | Where | Disposition |
|---|---|---|
| `tickets` (`week_number`, `difficulty`, `root_cause`, `required_checkpoints`, `scoring_anchors`, `hints`, `model_answer`) | `models/ticket.py` | **ARCHIVE** — retired for students by `0043_retire_legacy_tickets`, data preserved, inert for progression (`PROGRESSION_CONTRACT.md` §E) |
| `ticket_submissions` (AI-graded, 5-anchor rubric) | `models/ticket.py` | **ARCHIVE** — history preserved, no student create path |
| `ticket_grader.py` (`grade_ticket_with_answer_key`, deterministic checkpoint scan + AI anchors + guards) | `services/ticket_grader.py` | **KEEP as reference** for V2 free-response grading; the *deterministic-then-AI-with-guards* pattern is exactly the PRD §12 order |
| `ticket_generator.py`, `ticket_params.py`, `methodology_enforcer.py`, `routers/tickets.py`, `routers/submissions.py`, `routers/admin_tickets.py` | `services/`, `routers/` | **ARCHIVE → DELETE LATER** — after confirming no V2 dependency and history export |
| Legacy ticket evaluators in `progression_service.py` | see §1.4 | **DELETE LATER** |

### 1.16 Progress / mastery models

| Item | Where | Disposition |
|---|---|---|
| `student_lesson_progress`, `video_watches`, `quiz_attempts`, `cli_lab_attempts`, `lab_runs`, `service_desk_attempts`, `capstone_runs` | various | **KEEP** — the canonical completion records; V2 derives module/cert progress from these, same philosophy as today (`CURRICULUM_STRUCTURE.md` "no persisted week-progress rows") |
| `student_domain_mastery` / `mastery_service.py` | `models/mastery.py` | **KEEP / REFACTOR** (§1.4) |
| `student_objective_progress` | `models/comptia.py` | **KEEP / REFACTOR** (§1.6) |
| Roles / promotion (`roles`, `promotion_gates`, `student_roles`, `students.current_role_id`) | `models/progression.py` | **KEEP / REFACTOR** — re-key gate configs to modules; keep role ladder |
| XP (`xp_ledger`, `xp_service.py`, `xp_calculator.py`; motivational only, no gate reads it) | `models/xp_ledger.py` | **KEEP** — unchanged, still non-authoritative |
| Login streaks, weekly leads, squad activity | `models/login_streak.py`, `weekly_lead.py`, `squad_activity.py` | **KEEP** (streak) / **ARCHIVE** (`weekly_lead`, `squad_activity` are week/cohort-flavoured and lightly used) |
| **NEW in V2:** durable `pending_grading` queue + auto-retry worker for free-response/Explain | — | does not exist today (ticket `status="pending"` has no worker) |
| **NEW in V2:** `student_certification_progress`, `student_module_progress` derived-state cache (optional) | — | only if performance needs it; prefer deriving like today |

### 1.17 Admin curriculum screens

| Screen / route | Where | Disposition |
|---|---|---|
| `/admin/modules` → `ModuleManager.jsx` (modules/lessons/quizzes) | frontend, `routers/admin_content.py` | **REFACTOR** onto V2 tables |
| `/admin/training` → `AdminTrainingPage.jsx` (week + activity CRUD, reorder, `/api/admin/training/validation`) | frontend, `routers/admin_training.py` | **REFACTOR** → module/lesson ordering |
| `/admin/curriculum` → `CurriculumEditorPage.jsx` | frontend | **REFACTOR** |
| `/admin/curriculum-tags` → `CurriculumTagsPage.jsx` (video `job_relevance` = job_critical/know_it/awareness) | frontend, `routers/admin_curriculum.py` | **KEEP / REFACTOR** — extend the label to lessons/questions, rename `know_it → working_knowledge` |
| `/admin/question-import` → `QuestionImportPage.jsx` | frontend | **KEEP / EXTEND** (§1.9) |
| `/admin/quizzes/:quizId/edit` → `QuizEditorPage.jsx` | frontend, `routers/admin_quiz.py` | **KEEP / REFACTOR** |
| `/admin/bookmarklet` → `BookmarkletPage.jsx` (ExamCompass) | frontend | **KEEP / gate on permission** |
| `/admin/service-desk-review`, `/admin/labs`, `/admin/capstones`, `/admin/ai-costs` | frontend | **KEEP** |

---

## 2. V2 target schema (additive)

New tables, added by new migrations, **alongside** the existing ones. No
existing table is dropped or altered destructively in this phase.

> **Phase 1A implementation update (2026-08-29):** the lesson/question V2
> fields below were realised as **1:1 companion tables** (`lesson_v2_meta`,
> `question_v2_meta`), not as columns on `lessons` / `questions`. Adding
> columns broke historical data-migration tests (old-checkout DB + current
> ORM). Companion tables leave the legacy schemas untouched. Still "extend,
> not fork" — no parallel lesson/question system. See
> `docs/NEXUS_V2_PHASE_1A_IMPLEMENTATION_NOTE.md`. The `pending_grades` /
> `ai_grades` / `module_assessments` tables and the `short_answer` /
> `free_response` types remain deferred (Phase 1B).

```
certifications
  id, cert_key (uq), name, display_order, active

certification_versions
  id, certification_id -> certifications, version_key (uq),
  label (e.g. "220-1201/220-1202", "N10-009", "SY0-701", "010-160", "AZ-900"),
  is_current (bool), source_url, active
  -- versions are DATA; no code constant lists exam codes

objectives
  id, certification_version_id -> certification_versions,
  domain_key, objective_code, objective_text, subtopics(json),
  uq(certification_version_id, objective_code)
  -- generalisation of comptia_objectives

cert_domains
  id, certification_version_id -> certification_versions, domain_key (uq per version),
  title, display_order

cert_modules
  id, certification_version_id -> certification_versions, cert_domain_id -> cert_domains,
  module_key (uq), title, skill_promise, importance_hint, display_order,
  legacy_training_week_id -> training_weeks (nullable, migration bridge only),
  legacy_module_code (nullable, e.g. "MOD-005")

cert_lessons                 -- OR: add these columns to existing `lessons`
  (existing lessons.id kept) + cert_module_id -> cert_modules,
  certification_version_id, domain_key, importance, learning_relationship,
  builds_on(json list of lesson keys), content_path (markdown file),
  lesson_key (uq)

lesson_objectives
  lesson_id -> lessons, objective_id -> objectives, pk(lesson_id, objective_id)

module_assessments
  id, cert_module_id -> cert_modules, quiz_id -> quizzes,
  assessment_role (quick_check | module_quiz | knowledge_review | practical_final | interview_explain),
  displayed_count, pass_percent (default 70)

-- questions: ADD COLUMNS to existing table (do not fork):
--   certification_version_id, objective_code, importance, learning_relationship,
--   question_type (enum extended), acceptable_answers(json), expected_concepts(json),
--   source_name, source_url, permission_status, active

pending_grades
  id, student_id, submission_type (free_response | interview_explain | ...),
  submission_ref_id, status (pending | grading | graded | failed),
  attempts, last_error, rubric_version, created_at, updated_at

ai_grades
  id, submission_type, submission_ref_id, rubric_version, model_version,
  score, confidence, reasoning_summary, graded_at,
  mentor_override_score, mentor_override_by, mentor_override_at
```

`quizzes`: add `certification_version_id`, `cert_module_key`,
`assessment_role`; make `week_number` nullable in a later migration (not the
first). CHECK constraints on `recommended_week` / `prerequisite_week` are
dropped only at cutover.

Portability: all new columns use `JSON().with_variant(JSONB, "postgresql")`
and plain types, matching existing conventions. Every migration has a working
`downgrade`.

---

## 3. Migration sequence

### Step 1 — Backup & safety

- Verified production DB backup (`scripts/` backup tooling +
  `docs/DEPLOYMENT.md` procedure). Confirm restore works into a scratch DB.
- Snapshot `alembic current` (`0061`) and `git rev-parse HEAD`.
- Record row counts for: `students`, `quiz_attempts`, `service_desk_attempts`,
  `lab_runs`, `cli_lab_attempts`, `ticket_submissions`,
  `student_lesson_progress`, `video_watches`. These are the "nothing lost"
  baseline for §12.
- Prepare rollback commands (migration `downgrade`, service restart, DB
  restore) before touching anything.

### Step 2 — Additive V2 schema

- New migrations create the §2 tables and add the nullable `lessons` /
  `questions` columns. Nothing existing is dropped or made stricter.
- Idempotent data loaders (new, not `seed_phase_*`):
  - `objectives` loader — A+ 220-1201 / 220-1202 official objective list as a
    data file.
  - `certifications` / `certification_versions` loader — the 7-cert path as
    data (only A+ populated for MVP).
  - Markdown lesson loader — keyed on `lesson_key`, upsert, preserves
    `student_lesson_progress` by not renumbering.
  - Resource / interview-prompt loaders — XLSX/CSV.
- Extend `question_importer.py` + template + `question_validation.py` for the
  new fields and `short_answer` / `free_response` types.
- Add `pending_grades` + retry worker; wire the deterministic → rubric → AI
  order; make every AI grade write `ai_grades`.
- Backfill bridges (read-only): populate `cert_modules.legacy_training_week_id`
  and `legacy_module_code` from `curriculum_structure.MODULES` +
  `progression_service` `MODULE_WEEKS` so V2 can map old evidence to modules.
- CI: fresh empty DB → `alembic upgrade head` → new loaders run twice → no
  duplicates. Existing week seeds still run and still pass.

### Step 3 — A+ MVP implementation

- Author 2–3 A+ modules per the PRD (basic networking/troubleshooting,
  Windows troubleshooting, hardware/support) as Markdown lessons + XLSX
  question banks (≥20 per module) with full provenance.
- Each MVP module: Quick Checks, Module Quiz (randomised 10–15 of ≥20),
  ≥1 practical (CLI lab / guided lab / VM lab), ≥1 Service Desk ticket where
  appropriate, ≥1 Interview/Explain prompt.
- New student surfaces: certification browser, module page (reuse
  `/training/module/:moduleId` slot), module-assessment flow, Explain flow.
- Module completion rule: all lessons viewed + Module Quiz ≥ pass_percent +
  required practicals passed. **No call to `a_plus_access.get_a_plus_progress`
  anywhere on this path** (asserted by test).
- Promotion-gate configs for the affected role gain module-keyed equivalents
  *in addition to* the week-keyed ones (both satisfiable during transition).

### Step 4 — Testing

- Unit: new loaders idempotent; extended validator accepts/rejects
  short-answer & free-response correctly; grading order (deterministic hit →
  no AI call; miss → rubric; ambiguous → AI) ; `ai_grades` fields populated.
- Integration: full MVP module flow end-to-end for a test student;
  objective-coverage report lists uncovered A+ objectives; XLSX import adds a
  bank question with zero code change; Markdown lesson appears after sync.
- Resilience: kill the AI endpoint mid free-response submit → answer saved,
  `pending_grades.status = pending`, worker grades on endpoint return, no
  resubmit, student informed.
- Regression: existing backend suite (555+), fresh migrate+seed proof,
  frontend build, Playwright — all green. Existing week routes still work.
- Data: all Step 1 baseline row counts unchanged or only increased.

### Step 5 — Content migration

- Triage legacy questions in `seed_phase_*` / DB: for each, decide KEEP
  (export to XLSX with provenance, `permission_status` set honestly) or
  ARCHIVE (`active = false`, leave in place).
- ExamCompass questions (`source_type = examcompass`, many already archived by
  `0046_archive_unreviewed_examcompass`): **blocked on the licensing question
  in §13** — do not publish any without a recorded `permitted` status.
- Migrate useful lessons from seed prose + `references/lesson-drafts/` into
  the Markdown format.
- Preserve Service Desk scenario history and lab history untouched (KEEP).
- No production DB content editing for ordinary content changes — go through
  loaders/importer.

### Step 6 — V2 cutover

Only after §12 criteria pass:

- Student nav switches to the certification/module IA. `/training/week/:weekId`
  → 301 to the mapped module route. `/learning-path` / `/skills` re-pointed.
- Promotion-gate configs: remove the week-keyed requirement rows, keep the
  module-keyed ones (seed prune handles orphans — `PROGRESSION_CONTRACT.md`
  §F; back up first, it performs a real delete).
- `quizzes.week_number` made nullable; `recommended_week` /
  `prerequisite_week` CHECK constraints dropped.
- Admin week/activity screens replaced by module/lesson screens.
- `a_plus_unlock_threshold_pct` set to `0` in production (backed up), legacy
  gate now a no-op.

### Step 7 — Removal of old week architecture

Separate migration(s)/PRs, each individually revertible:

- Delete `a_plus_access.py` + endpoint + callers + tests; drop the
  `AppSetting` row.
- Delete `TrainingWeekPage.jsx` week branch, `MODULE_WEEKS` / `CLI_PACK_WEEKS`,
  `intended_module_sequence` drift validators, week CRUD router
  (`admin_training.py`), `routers/training.py` week payloads.
- Drop `training_weeks` / `training_week_activities` **last**, after a final
  export, with a `downgrade` that recreates them from the export fixture.
- `curriculum_structure.py` reduced to (or replaced by) the V2 module reader.
- Retire legacy ticket routers/services (`tickets.py`, `submissions.py`,
  `admin_tickets.py`, `ticket_generator.py`, `ticket_params.py`,
  `methodology_enforcer.py`) after a `ticket_submissions` history export.
- `tickets` / `ticket_submissions` / `incidents` tables: keep as cold history
  or drop-with-export — owner's call at that point.

### Step 8 — Rollback strategy

- **Per migration:** every V2 migration has a tested `downgrade`. Additive
  migrations (Steps 2–5) downgrade to exactly `0061` behaviour.
- **Per PR:** each cutover/removal PR (Steps 6–7) is small and independently
  `git revert`-able + `alembic downgrade` one step.
- **Data safety:** destructive drops (Step 7) only ever run after an export
  fixture is committed and the `downgrade` restores from it.
- **Fast path:** restore the Step 1 DB backup + `git checkout` the pre-cutover
  tag + `systemctl restart nexus-admin-academy` (passwordless sudo restart is
  configured). Frontend container redeploy from the prior image.
- **Trigger conditions:** any Step 1 baseline row count drops; any promotion
  gate becomes unsatisfiable for a current student; free-response answers lost
  on AI outage; fresh migrate+seed proof red.

---

## 12. Acceptance criteria before legacy week code may be deleted

All must hold, with evidence, before **Step 7**:

- **C1 — No student-visible week concept on the MVP path.** A student
  completes Certification → Domain → Module → Lesson → Module Assessment →
  Practical for all MVP A+ modules with no `week` string in any API response
  or UI on that path. (test + manual click-through)
- **C2 — Single progression gate.** Grep proves no MVP module-completion or
  hands-on-unlock code path calls `a_plus_access.*`, `required_quizzes_for_week`,
  or reads `quizzes.week_number`. `a_plus_unlock_threshold_pct = 0` in prod
  and the legacy `a_plus_unlocked` value gates nothing.
- **C3 — Promotion still works.** For every current student, every seeded
  promotion gate is satisfiable via module-keyed requirements alone (with the
  week-keyed rows removed in a scratch DB). `PROGRESSION_CONTRACT.md` tests
  updated and green.
- **C4 — 40% gate fully inventoried and neutralised.** Every reference in
  §1.5 is either deleted or confirmed no-op; a test asserts hands-on access
  for an MVP module does not depend on video-watch percentage.
- **C5 — Objectives are data.** A+ objectives loaded from a data file; no
  `A_PLUS_EXAM_CODES`-style constant remains on the MVP path; admin can list
  uncovered A+ objectives.
- **C6 — Content is data.** Adding a question (XLSX import) and a lesson
  (Markdown + sync) each require zero code change and appear for students.
- **C7 — Free-response resilience.** AI-outage test passes: save,
  `pending_grading`, auto-retry, no resubmit, full `ai_grades` record on
  success.
- **C8 — Nothing lost.** Step 1 baseline row counts for `quiz_attempts`,
  `service_desk_attempts`, `lab_runs`, `cli_lab_attempts`,
  `ticket_submissions`, `student_lesson_progress`, `video_watches` are all
  ≥ baseline. Service Desk and lab history queryable unchanged.
- **C9 — Green everything.** Backend suite, fresh empty-DB migrate+seed proof
  (both old seeds and new loaders), frontend build, Playwright — all pass in
  CI.
- **C10 — Reversible.** The cutover PR set has been dry-run reverted in a
  scratch environment back to `0061` behaviour with no data loss.

---

## 13. Owner-input items feeding this plan

- **ExamCompass reuse:** are the ExamCompass questions currently in the DB
  (and future bookmarklet imports) actually permitted for reuse inside Nexus?
  This decides whether they are exported with `permission_status = permitted`
  (KEEP) or held `active = false` / ARCHIVE. Nothing publishes them until
  this is recorded.
- **Current students' progress on cutover:** the ~5 students are mid-path on
  the week system. On cutover, do they (a) start fresh on the V2 A+ path with
  history preserved but not counted toward V2 module completion, or (b) get
  their week/lesson/quiz history mapped forward into V2 module progress via
  the `legacy_training_week_id` bridge? Both preserve history; they differ in
  student experience.
