# Nexus V2 — Product Requirements Document

Status: **Phase 0 (planning only).** Nothing in this document is implemented.
No migrations, no behavior change, no deployment follow from it.

Companion documents:

- `docs/CURRICULUM_CONTENT_STANDARD.md` — how content is structured and authored.
- `docs/NEXUS_V2_MIGRATION_PLAN.md` — how we get from today's week-based system
  to this without losing student history.
- `docs/PROGRESSION_CONTRACT.md` — the *current* progression system this PRD
  replaces the week/40% parts of.

---

## 1. Mission

Reteach the knowledge behind certifications our students already hold, so they
can actually do IT support and infrastructure work: understand concepts, use
tools, troubleshoot, work tickets, and explain themselves in an interview.

Nexus is a **teaching and practice platform**, not an exam cram tool. Passing
the real exam is a side effect of genuinely knowing the material and having
done the hands-on work.

## 2. Problem statement

- Our ~5 students have WGU IT certifications (A+, Net+, etc.) but their working
  knowledge and hands-on experience are close to beginner.
- The current Nexus curriculum is organised as a fixed 25-"week" path
  (`training_weeks` / `training_week_activities`). Weeks are a pacing metaphor,
  not a knowledge structure, and they are welded into progression, seeds,
  migrations, routes, and tests.
- Curriculum content lives as multi-megabyte hardcoded Python seed modules
  (`training_curriculum_seed.py` is ~330 KB). Adding 30 questions or swapping a
  video URL currently requires a code change and a deploy.
- There is no first-class model of a certification, a certification version, or
  an official objective beyond a single unversioned A+ objective table
  (`comptia_objectives`) and hardcoded A+ exam codes.
- Progression has multiple overlapping gates: a 40% A+ video-watch unlock
  (`a_plus_access.py`), a 70% quiz pass rule, quiz-derived domain mastery, and
  five role promotion gates. The PRD's new module system must not add a sixth.
- Free-response / "explain it" assessment exists only for tickets and the
  Service Desk simulator, never for lesson- or module-level checks.

## 3. Target students

- **Count:** ~5. Single cohort. No scale requirements.
- **Profile:** certified on paper, beginner in practice. Motivated, adult,
  self-paced. Preparing for real IT jobs (help desk → sysadmin → cloud/infra).
- **Mentor:** one operator (the owner) who authors/curates content, reviews
  free-response and Service Desk work, and watches where students struggle.
- **Not in scope:** public signups, cohorts, classrooms, marketplace,
  student-vs-student ranking, monetisation.

## 4. Product principles

1. **Nexus is the system of record.** External videos and quizzes support
   Nexus; they never replace Nexus tracking. Mastery is measured by
   Nexus-controlled assessments, labs, tickets, and explain answers.
2. **Certification-shaped, not calendar-shaped.** The structure is
   Certification → Version → Domain → Module → Lessons → Module Assessment →
   Practical Work. No weeks, no calendar pacing.
3. **One recommended path, self-paced speed.** Everyone follows the same
   ordered path. Students who know a topic move faster by passing its checks.
   No adaptive engine, no skill DAG, no AI-selected paths, no automatic
   test-out routes.
4. **Objectives are the source of truth.** Every lesson maps to one or more
   official certification objectives. Coverage is measurable.
5. **Content is data, not code.** Lessons are Markdown; questions are
   XLSX/CSV; resources and interview prompts are simple data files. Routine
   curriculum maintenance requires no programmer.
6. **Provenance is mandatory.** Every question and resource records where it
   came from and whether we're allowed to use it.
7. **Short, honest lessons.** Beginner-friendly, tightly scoped, always tied
   to why an IT worker cares and what it looks like on the job.
8. **Practical spine for important topics.** Job-critical concepts get the
   full Learn → Quick Check → Guided Practice → Independent Lab → Service Desk
   Ticket → Explain loop. Awareness topics get much less.
9. **Graceful degradation.** If AI/GPU grading is down, the student's answer
   is still saved, marked `pending_grading`, retried automatically, and never
   lost. Curriculum never fails silently.
10. **Additive migration.** V2 is built alongside the week system. Old tables
    and student history are preserved until explicit acceptance criteria are
    met.

## 5. Certification path

Fixed recommended order. Each is a stored `certification` with at least one
stored `certification_version`:

| # | Certification | Version(s) stored | Notes |
|---|---|---|---|
| 1 | CompTIA A+ | 220-1201 / 220-1202 | Core rebuild of fundamentals. |
| 2 | CompTIA Network+ | N10-009 | DNS/routing/switching Deep Dives building on A+. |
| 3 | ITIL 4 Foundation | ITIL 4 Foundation | Kept short. Nexus-authored lessons + Service Desk scenarios. |
| 4 | CompTIA Security+ | SY0-701 | Security as a cross-cutting concern, plus DNS security etc. |
| 5 | LPI Linux Essentials | 1.6 / 010-160 | Real CLI practice. |
| 6 | Microsoft Azure Fundamentals | AZ-900 | Microsoft Learn + free practice assessments. |
| 7 | Microsoft Azure Administrator | AZ-104 | Deeper Azure/admin content. |

Future certifications and deeper Azure/network/system-administration tracks are
added later as additional `certification` rows. **Certification versions are
data, never hardcoded into application logic** (contrast today's
`A_PLUS_EXAM_CODES = ("220-1201", "220-1202")` constant).

## 6. Student UX

### 6.1 Navigation

Primary surfaces, in order:

- **Continue** — the single next recommended activity on the path (next
  unfinished lesson, its Quick Check, a module assessment, or a practical
  step). One clear call to action.
- **Certifications** — the path browser: the seven certifications, each
  expanding to Domains → Modules → Lessons, with per-item state
  (Locked / Available / In progress / Complete) and objective coverage.
- **Service Desk** — the ticket simulator (kept and expanded, see §12).
- **Practice** — optional/extra work: CLI labs, guided labs, VM labs,
  command library, flashcards, interview/explain review.
- **Progress** — the student's own view of what they've done and what's weak.
  Never a leaderboard, never a comparison to other students.

### 6.2 Certification progression stays visible even when topics overlap

A+ teaches "DNS basics" (Learning Relationship: **New**). Network+ does not
repeat it — it has a "DNS Deep Dive" (**Deep Dive**) that references the A+
lesson. Security+ later has "DNS security" (**New** within Security+, building
on both). The student always sees which certification they are in and how the
current lesson relates to earlier ones.

### 6.3 Lesson experience

Every lesson renders the standard template (full spec in
`CURRICULUM_CONTENT_STANDARD.md`): What is this / Why an IT worker cares /
Watch–read selected resources / What to remember / Real workplace example /
Commands & tools / Interview question / Quick Check.

### 6.4 Assessment experience

- **Quick Check** at the end of a lesson (3–5 questions; up to 5–7 for
  job-critical lessons).
- **Module Quiz** (10–15 shown, drawn from a 20–40+ question module bank so
  retakes randomise).
- **Certification Knowledge Review** (~40–60 mixed questions).
- **Certification Practical Final** (~4–8 troubleshooting scenarios).
- **Interview / Explain Review** (~3–5 prompts).

Not every small lesson gets a big quiz.

### 6.5 External videos & quizzes

- Videos/resources may be external (Professor Messer, Microsoft Learn, LPI).
  For V1, Nexus tracks **opened / completed / marked watched**. Video
  completion is *learning activity*, not mastery, and does not by itself
  advance module completion.
- External-only quizzes are supplemental unless their questions can be
  legally imported. For external practice Nexus can record: completed,
  reported score, student notes, confusing topics, a question for the mentor.
  No screenshots required for normal external practice.

## 7. Mentor UX

- **Roster view:** every student's current position on every certification
  (mentor may see everyone; students may not).
- **Weakness analytics (built incrementally):** weak topics per student, weak
  objectives per student, cohort-wide weak topics, most-missed questions,
  module progress, ticket/lab performance.
- **Review queue:** free-response / Explain answers and Service Desk attempts
  needing review, low-confidence AI grades prioritised, mentor override
  captured.
- **Student notes & questions-for-mentor** surfaced inline with the relevant
  lesson/module.

## 8. Admin / content UX

Target: **routine curriculum work needs no programming.**

| Content type | Authoring format | Sync mechanism |
|---|---|---|
| Lessons | Markdown files with frontmatter, in-repo under `content/curriculum/...` | Idempotent loader keyed on a stable lesson key |
| Questions | XLSX / CSV | Existing importer (`question_importer.py`), extended — preview/confirm, fingerprint dedup |
| Resources (videos/links) | XLSX / CSV or simple data file | Idempotent loader |
| Interview / Explain prompts | XLSX / CSV or simple data file | Idempotent loader |
| Objectives | Data file per certification version (official objective list) | Idempotent loader |
| Service Desk tickets | Structured scenario data (JSON/Markdown); admin Scenario Builder later | Existing versioned scenario store (`service_desk_scenarios`) |

Admin screens that survive: Modules/Lessons/Quizzes editor, question import,
Service Desk review + scenario CRUD, labs & VM assignments, AI usage. Screens
tied to `training_weeks` (`/admin/training` week/activity CRUD) are refactored
onto the V2 module tables during cutover.

Codex / Claude Code are for software features — not for adding 30 quiz
questions or replacing a video URL.

## 9. Assessment model

### 9.1 Sizes

| Assessment | Displayed | Bank target |
|---|---|---|
| Lesson Quick Check | 3–5 (job-critical: up to 5–7) | — |
| Module Quiz | 10–15 | 20–40+ per module |
| Certification Knowledge Review | 40–60 mixed | — |
| Certification Practical Final | 4–8 scenarios | — |
| Interview / Explain Review | 3–5 prompts | — |

### 9.2 Question types

1. **Multiple choice / multi-select** — already supported
   (`question_validation.py`: single / multi / true_false).
2. **Short answer** — NEW. May define acceptable answers, synonyms, expected
   concepts.
3. **Scenario / free-response** — NEW. May define expected concepts and a
   rubric.

Short-answer and free-response never require exact wording. Example: "A
workstation gets a 169.254.x.x address — what would you investigate?" →
expected concepts: APIPA, DHCP failure, physical/link connectivity, DHCP
server reachability, `ipconfig /release` + `/renew`.

### 9.3 Question record fields

Every question stores provenance and mapping (superset of today's `questions`
columns):

`question_id`, `certification`, `certification_version`, `domain`, `module`,
`objective_code`, `importance`, `question_type`, `question`, `options`,
`correct_answer`, `acceptable_answers`, `expected_concepts`, `explanation`,
`difficulty`, `source_name`, `source_url`, `permission_status`, `active`.

## 10. Practical learning model

For important topics:

```
Learn → Quick Check → Guided Practice → Independent Lab → Service Desk Ticket → Explain / Interview
```

- **Job Critical** concepts get the full loop.
- **Working Knowledge** concepts get Learn → Quick Check → some practice.
- **Awareness** concepts may get only Learn → Quick Check.

Practice infrastructure is reused, not rebuilt: CLI/xterm labs
(`cli_labs`), guided labs (`lab_templates` / `lab_runs`), Proxmox VM labs
(`proxmox_service.py` + `vm_assignments`), Guacamole access
(`guacamole_service.py`), and the Service Desk simulator.

## 11. Progress tracking

Nexus tracks, per student:

- Certification progress, module progress, lessons completed.
- Videos / resources completed (activity, not mastery).
- Every question attempt; every incorrect question and its objective/topic.
- Quiz scores, lab results, Service Desk ticket results, practical final
  results.
- Short-answer / free-response results; Interview / Explain responses.
- AI and manual grading history (see §12).
- Student notes and questions for the mentor.

Interview/Explain answers and their grading history are **permanent** student
progress records.

Student-facing UI never ranks students against each other. The mentor may see
everyone's position.

## 12. AI grading requirements

AI does **not** author the curriculum. The owner uses ChatGPT / Claude /
Gemini to help draft and review content, then imports it.

Local/self-hosted AI (already wired: `ai_service.py`, OpenAI-compatible
endpoint, Ollama-friendly, daily budget cap, rate limiter, usage log) may
assist grading free-response / Explain answers.

### 12.1 Grading order

1. Deterministic acceptable-answer / expected-concept checks.
2. Partial-credit rubric evaluation.
3. AI fallback for ambiguous responses only.

AI grading must be **rubric-driven** (the Service Desk simulator already does
this: `service_desk_objectives.py` process rubric, `service_desk_grading.py`
`RUBRIC_VERSION`).

### 12.2 Every AI grade stores

`rubric_version`, `grader/model version`, `score`, `confidence` (if
available), `explanation/reasoning summary`, `timestamp`, `mentor_override`
(if changed). Low-confidence grades are prioritised for mentor review.

### 12.3 Outage behaviour (hard requirement)

If the AI/GPU grading service is unavailable:

- The student submission still saves successfully.
- Status becomes `pending_grading`.
- The student never loses the answer and never has to resubmit.
- The curriculum does not fail silently — the student is told it's queued.
- Grading retries automatically when the service returns.

Today: ticket submissions have a `pending` status but there is **no retry
worker**. V2 must add a durable pending-grading queue with automatic retry.

## 13. Objective / versioning rules

- Official certification objectives are the curriculum source of truth.
- Every certification has at least one stored version
  (`certification_versions`), stored as data.
- Every lesson maps to one or more official objectives
  (`lesson_objectives`).
- Every question records `objective_code`.
- Admin can eventually see objective coverage per certification version and
  list uncovered objectives.

## 14. MVP

The MVP proves the V2 architecture — it is **not** the seven-certification
curriculum.

- Build **2–3 A+ modules** only. Preferred: basic networking/troubleshooting,
  Windows troubleshooting, hardware/support troubleshooting.
- Each MVP module supports the full end-to-end flow: lesson → video/resource →
  Quick Check → Module Quiz → practical activity/lab → Service Desk ticket
  (where appropriate) → Interview/Explain → progress & weakness tracking.
- A+ 220-1201 / 220-1202 objectives seeded as data.
- No week code deleted yet; V2 runs alongside.

Phase 0 does **not** implement MVP content.

## 15. Non-goals

- No giant skill DAGs, AI-selected learning paths, automatic test-out routes,
  or calendar/week pacing.
- No adaptive difficulty engine.
- No student-vs-student ranking or public leaderboards.
- No replacement of the Nexus Service Desk with Zammad / osTicket / GLPI.
- No multi-tenant / cohort / classroom features.
- No rewrite of Proxmox / Guacamole / CLI-lab infrastructure — reuse it.
- No deletion of legacy week tables or student history during the additive
  phase.
- No AI authoring of curriculum content.

## 16. Acceptance criteria (product-level)

V2 is "working" when, for the MVP A+ modules:

1. A student can move Certification → Domain → Module → Lesson → Module
   Assessment → Practical entirely without any `training_week` concept
   appearing in their UI.
2. Every MVP lesson maps to ≥1 real A+ objective code, and admin can list
   which A+ objectives are still uncovered.
3. Every MVP lesson carries an Importance label and a Learning Relationship
   label.
4. A module quiz draws a randomised subset from a ≥20-question module bank.
5. At least one short-answer and one free-response question grade through the
   deterministic → rubric → AI-fallback order, and store the full §12.2 grade
   record.
6. Killing the AI endpoint mid-submission leaves the answer saved,
   `pending_grading`, and it grades automatically when the endpoint returns —
   with no resubmission.
7. Module completion is driven **only** by the new module-assessment /
   practical rules. The legacy 40% A+ video-watch gate and the 70%
   week-quiz rule do not gate any MVP module (inventory + disable per
   `NEXUS_V2_MIGRATION_PLAN.md`).
8. A question added via XLSX import with full provenance fields appears in a
   module bank with no code change.
9. A lesson added as a Markdown file appears on the path after running the
   idempotent content sync, with no code change.
10. All existing student history (quiz attempts, Service Desk attempts, lab
    runs, ticket submissions) is still present and queryable.
11. Backend test suite, fresh migrate+seed proof, frontend build, and
    Playwright suite are green.

## 17. Future roadmap (post-MVP, not committed here)

- Remaining A+ modules, then Network+ → ITIL 4 → Security+ → Linux Essentials
  → AZ-900 → AZ-104.
- Objective-coverage dashboard and cohort weakness analytics.
- Admin Scenario Builder UI backed by the existing versioned scenario store.
- Service Desk ticket realism ladder: Guided → Assisted → Independent →
  Mixed Support Shift.
- Lab additions (free/open-source), roughly in this order and never all at
  once: Kathará (lightweight network labs), Wireshark (packet analysis),
  OPNsense (firewall/router); later GNS3, Wazuh, FreeIPA/Samba, Packer.
- Removal of the legacy week architecture once the cutover acceptance
  criteria in `NEXUS_V2_MIGRATION_PLAN.md` are met.
