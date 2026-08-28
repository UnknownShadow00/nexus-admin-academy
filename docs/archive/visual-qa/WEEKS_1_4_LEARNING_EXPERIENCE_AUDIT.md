# Weeks 1–4 Learning Experience Audit

Conducted against `origin/main @ fb68edc` on branch `feature/weeks-1-4-learning-experience`,
using the isolated local stack (`scripts/e2e/start_local_stack.sh`) with a fresh
disposable student (`browser-fresh-student-a`) and a disposable admin session —
no production data touched. Findings are cross-checked against rendered UI output
(Playwright + manual API calls against the isolated stack), the FastAPI response
payloads actually sent to the browser, and the source files that produce them —
not seed/config text alone.

## Method

- Backend/admin API pulled live from `/api/admin/training/weeks`, `/api/admin/labs/templates`,
  `/api/admin/curriculum/videos`, `/api/admin/lessons` against the isolated stack.
- Frontend rendering verified by reading the exact component that renders each
  screen (`TrainingWeekPage.jsx`, `LessonPage.jsx`, `LabPage.jsx`, `StudyTrackerPage.jsx`)
  and by a live login walkthrough as a fresh student.
- "Fake lab" classification follows the brief's rule literally: a required activity
  is FAKE if the student cannot actually perform the claimed technical skill in a
  functioning environment — a textbox and/or screenshot upload does not count.

---

## 1. Video importance labels — root cause

**The data already exists and is already returned by the API. The frontend for
the weekly view simply never reads it.**

- Authoritative field: `CurriculumVideo.job_relevance` (`backend/app/models/curriculum_video.py:19`),
  one of `job_critical` / `know_it` / `awareness` (`backend/app/routers/admin_curriculum.py:16`).
- `training_service.py` already attaches it to every weekly video activity:
  `job_relevance=video.job_relevance` (`backend/app/services/training_service.py:294`) and
  again in the serialized activity dict, `"job_relevance": content.job_relevance if content else None`
  (`backend/app/services/training_service.py:491`). This ships to the browser today on
  every `GET` of a week's training payload.
- The **old** "All Course Content" library page (`frontend/src/pages/StudyTrackerPage.jsx`)
  reads `video.job_relevance` and renders it with a local `JobRelevanceBadge` component
  (lines 14–33) — this is the only place in the frontend that renders the classification.
- The **new** weekly "This Week" view (`frontend/src/pages/TrainingWeekPage.jsx`) renders
  activity cards from the exact same API payload but never reads `activity.job_relevance`
  anywhere in the file (confirmed by full-text search — only `activity_label`,
  `requirement_label`, `estimated_minutes`, and `linked_quiz` are used). This is a pure
  frontend rendering gap, not a data or migration problem.

**Fix path (no new classification system):** reuse `JOB_TAGS` / `JobRelevanceBadge`
from `StudyTrackerPage.jsx` — extract it into a shared component (e.g.
`components/ui/Badge.jsx`, which already hosts `DifficultyBadge`) and render it on
video activity cards in `TrainingWeekPage.jsx`, plus a small legend near the Learn
section.

**Missing classification:** none in Weeks 1–4. Every `curriculum_video` row referenced
by a Week 1–4 activity has a `job_relevance` value (the column defaults to `know_it`,
so nothing is `NULL`). Counted directly from the live API response for all 52 video
activities across Weeks 1–4:

| Classification | Count |
|---|---|
| Job Critical | 27 |
| Know It | 15 |
| Awareness | 10 |
| Missing/unclassified | 0 |

No new classifications need to be authored for this phase — this is a rendering fix only.

---

## 2. "Meet the Command Line" — dead instruction, confirmed

`Lesson.summary` for lesson id 3 (`Meet the Command Line`, Week 1) literally says:

> "ACTIVITY: complete CLI labs 1-9 of the 'meet-the-cli' pack (all 18 for accelerated
> pace). You will navigate a simulated network device, run show commands..."

`LessonPage.jsx` renders `lesson.summary` as plain markdown text (`LessonSummary`
component, lines 15–41) with no parsing of that instruction into a link or button.
There is no CTA on the lesson page that leads to the CLI environment. A student who
reads this lesson has no way to act on it from that screen — this is exactly the
"dead instruction" problem in the brief.

**The referenced environment is real, not fake:** `frontend/src/features/cli-labs/`
contains a genuine simulator (`components/LabRunner.jsx`, `data/lessons/meet-the-cli.json`,
`data/lessonCatalog.js`) with its own router-backed lab model (`backend/app/routers/cli_labs.py`).
It is already wired into the Week 1 curriculum as a **separate activity**:
`networking_lab`, `content_ref="meet-cli-001"`, but it is currently `is_required=False`
(week 1 activity id 243). So the CLI practice activity already exists as its own
distinct Practice item — it is simply (a) not linked from the lesson that tells the
student to do it, and (b) not required, while the lesson's text implies it is
mandatory ("complete CLI labs 1-9").

**Recommendation:** Option B from the brief — keep CLI practice as its own weekly
Practice activity (it already is one), rewrite the lesson summary to stop claiming
"complete CLI labs 1-9" as an embedded requirement, and add a direct "Start CLI
Practice" CTA on the lesson page linking to the existing `networking_lab` activity/route.
No new terminal implementation needed.

---

## 3. Guided Lab inventory (all weeks, full table)

Pulled from `GET /api/admin/labs/templates` (5 templates exist total) and rendered
against the single generic `frontend/src/pages/LabPage.jsx`.

| id | Title | lab_type | Week | Classification | Why |
|---|---|---|---|---|---|
| 4 | Hardware Component Identification | identification | **1** | **SHELL/FAKE** | `setup_instructions`: "Read each component description and answer the identification questions below." No images/diagrams, no actual questions data beyond `success_criteria.tasks` (3 generic bullet strings), no structured answer controls. Rendered through the fully generic `LabPage.jsx` — free-text "Work and explain" box + optional screenshot upload, `Submit Lab` just posts the text. Nothing verifies the student actually identified anything. |
| 1 | IP Addressing & Subnetting Practice | guided | **2** | **SHELL/FAKE** | "You will answer subnetting questions using pen and paper or a calculator. No software required." No actual question/answer capture — same generic textarea + submit. `required_evidence: {}` (empty), so even the upload control's own justification is absent. |
| 2 | Troubleshoot a Network Connectivity Scenario | scenario | **3** | **SHELL/FAKE** | Real scenario text (DNS misconfiguration) and a real 5-item task list, but the student only writes prose into the notes textarea; nothing checks whether they actually diagnosed the DNS server or performed any command. `required_evidence: {}`. |
| 3 | Windows Command-Line Diagnostics | guided | **4** | **SHELL/FAKE** | Asks the student to run real commands (`ipconfig /all`, `nslookup`, `tracert`) on "your Windows machine or approved training VM" and paste results into the same generic textarea. No connected environment, no output validation — self-reported free text only. |
| 5 | AD Break-Fix: locked and misplaced account on a live domain | break_fix | 15 | **REAL** (out of scope for this PR) | Backed by actual Proxmox VM templates (`WS2022-DC`, `Win11-Enterprise`) and Guacamole remote access (`LabPage.jsx`'s `guacUrl`/VM-assignment flow), with typed `required_evidence.evidence_types` and concrete `success_criteria`. This is the one genuinely real lab in the current template set — outside Weeks 1–4, not touched in this phase. |

**Root architectural cause (Phase 5 target):** `LabPage.jsx` shows "Evidence Upload"
whenever `lab.status` is `in_progress`/`assigned` **regardless of `lab_type`** and
regardless of whether `required_evidence` is even populated (lines 214–240), and
always shows the generic "Work and explain" textarea + "Submit Lab" for every
`lab_type` (`guided`, `scenario`, `identification`, `break_fix` alike). There is no
per-`lab_type` branching anywhere in the component. This is exactly the "one generic
textbox template" problem called out in Phase 5 of the brief.

**Week/topic misalignment (separate from the fake-lab problem):** the guided labs
attached to Weeks 2–4 do not match those weeks' stated learning goals:
- Week 2 goal: "Identify core PC components; explain storage/memory/CPU/power/firmware
  symptoms" (hardware) → assigned lab is **IP addressing/subnetting** (networking).
- Week 3 goal: "Navigate Windows support tools; use basic Windows diagnostics" → assigned
  lab is a **DNS/network connectivity scenario**.
- Week 4 goal: "Prioritize by impact; support common peripherals; use professional
  communication" → assigned lab is **Windows CLI diagnostics** (a Week-3-shaped skill).
- Week 1 is the one week where the lab *topic* (Hardware Component Identification)
  does not match the week's own stated theme either — Week 1's goals are ticket-writing
  and command-line basics, not hardware identification. Hardware ID's content fits
  Week 2's theme far better than Week 1's.

This reads as templates assigned in raw numeric order (`ref=1,2,3,4` mapped
sequentially to weeks 2,3,4,1) rather than by topic.

---

## 4. Per-week activity table (Weeks 1–4)

Legend for TYPE: L=lesson, V=video, Q=quiz, GL=guided_lab, NL=networking_lab (CLI),
SD=service_desk_scenario, CS=capstone.

### Week 1 — "IT Support and Ticket Basics"
Goals: write a useful ticket · communicate clearly · recognize common support requests.

| TYPE | Title | What student actually does | Current value | Problem | Verdict | Connection to next |
|---|---|---|---|---|---|---|
| L | Anatomy of a Good Ticket | Reads static text, clicks "Mark lesson complete" | Concept lesson, genuinely useful content | Claims to teach ticket-writing but gives no formative exercise before the graded quiz | **IMPROVE** — add a short structured formative exercise (fix-the-bad-note pattern from brief) | Should feed directly into the Ticket Writing quiz |
| L | Meet the Command Line | Reads static text incl. "complete CLI labs 1-9" instruction | Concept lesson + dead instruction (see §2) | No CTA to the CLI simulator; text claims a requirement that isn't wired up or required | **IMPROVE** — add direct "Start CLI Practice" CTA, rewrite copy to stop claiming a hard requirement | Should link into the `networking_lab` (meet-cli-001) Practice activity |
| V×3 (2 required) | Professionalism/communication + ticketing videos | Watches video, optional linked quiz | Correctly classified (`job_relevance` present) but label not shown | Importance not visible to student (see §1) | **IMPROVE** (render label) | Feeds Ticket Writing quiz |
| Q | Ticket Writing Fundamentals Quiz | Takes quiz | Required, gates progression | Not independently audited for question-level mismatch beyond spot-check; no obvious misalignment found | **KEEP** | Should follow Learn section directly |
| GL | Hardware Component Identification | Reads text, types into free-text box, optional screenshot | SHELL/FAKE (see §3) | Doesn't test ticket-writing/CLI skills Week 1 is about; not a real identification exercise either | **MOVE + REBUILD** — belongs conceptually closer to Week 2 (Computer Hardware); if kept as genuine practice, rebuild as structured identification (see §6) | N/A until moved |
| NL | CLI Practice (`meet-cli-001`) | Real simulator, `is_required=False` | Real, functioning, but optional and disconnected from the lesson that references it | Under-surfaced, not required despite lesson implying it is | **IMPROVE** — link from lesson, keep as its own Practice activity; decide required vs. optional deliberately | Directly follows "Meet the Command Line" lesson |
| SD | Locked User Account | Real Service Desk simulator ticket | Functional, appropriately scoped to Week 1 skills (identity verification, ticket documentation) | None found | **KEEP** | Terminal step of Week 1 |

**Week 1 assessment:** Learn → Quiz is coherent. Practice is broken — the one
required "lab" (Hardware ID) doesn't teach a Week 1 skill and isn't a real exercise,
while the one genuinely real, on-topic practice activity (CLI simulator) is optional
and unlinked from its own lesson. Apply (Locked User Account) is solid and correctly
scoped to what Learn/Quiz actually taught.

### Week 2 — "Computer Hardware"
Goals: identify core PC components · explain storage/memory/CPU/power/firmware symptoms.

| TYPE | Title | What student actually does | Current value | Problem | Verdict | Connection to next |
|---|---|---|---|---|---|---|
| L×3 | Storage: Symptoms Before Specs / RAM CPU Power POST / BIOS-UEFI and Boot Order | Reads static text, marks complete | Genuinely concept-appropriate content for a hardware week | None major found in a spot-check | **KEEP** | Feed into hardware quiz |
| V×13 (4 required) | Hardware video set | Watches videos | Correctly classified, label not shown | Same §1 issue | **IMPROVE** (render label) | Feeds hardware quiz |
| Q | Hardware quiz (id 78) | Takes quiz | Required | Not independently flagged | **KEEP** | — |
| GL | IP Addressing & Subnetting Practice | Free-text box, no software | SHELL/FAKE, and **topically mismatched** — this is a networking skill assigned to the hardware week (see §3) | Doesn't reinforce anything Week 2 taught | **REMOVE from Week 2 / REBUILD as a real hardware exercise** — this slot should hold genuine structured hardware identification (component photos/diagrams, connector/slot matching, deterministic feedback) once Hardware Component Identification is rebuilt and moved here from Week 1 | Should connect into the Week 2 Apply ticket |
| SD | INC2404 (asset isolation / peripheral hardware) | Real Service Desk ticket | Functional, hardware/asset-adjacent | Reasonably aligned with Week 2 theme | **KEEP** | Terminal step of Week 2 |

**Week 2 assessment:** Learn/Quiz are coherent and on-topic. Practice is the weakest
link — a subnetting worksheet with no connection to hardware identification, textbox-only.
Recommended target state: move the rebuilt Hardware Component Identification exercise
here (its content matches this week, not Week 1) as the real structured Practice.

### Week 3 — "Windows Fundamentals"
Goals: navigate Windows support tools · use basic Windows diagnostics.

| TYPE | Title | What student actually does | Current value | Problem | Verdict | Connection to next |
|---|---|---|---|---|---|---|
| L×3 required + 1 optional | Accounts/Profiles/Permissions, Investigator's Toolkit, Command-Line Diagnostics, Windows Update/Defender | Reads static text | Reasonable concept content for the week | Lesson 9 ("Command-Line Diagnostics") likely has the same referenced-but-unreachable-activity risk as lesson 3 — flagged for the implementation phase to re-check its summary text against the CLI/CLI-diagnostics lab before rewriting | **IMPROVE / VERIFY** | Feed Windows quizzes |
| V×14 (4 required) | Windows videos | Watches | Correctly classified, label not shown | §1 issue | **IMPROVE** (render label) | Feeds quiz |
| Q×3 (1 required) | Windows quizzes | Takes quiz | Required + 2 optional extra practice | Not independently flagged | **KEEP** | — |
| GL | Troubleshoot a Network Connectivity Scenario | Free-text diagnosis of a DNS issue | SHELL/FAKE, and networking-flavored rather than Windows-tool-flavored (see §3) | Doesn't exercise "navigate Windows support tools" — it's a paper DNS scenario | **REBUILD or MOVE** — either rebuild as a structured Windows-diagnostics exercise (matches lesson 9's actual content) with deterministic checks, or move this DNS scenario to a networking-themed week and pull a Windows-tool-based structured exercise into Week 3 | Should connect to the Week 3 Apply ticket |
| SD | Password Reset | Real Service Desk ticket | Functional, appropriately scoped | None found | **KEEP** | Terminal step of Week 3 |

**Week 3 assessment:** Same pattern as Week 2 — Learn/Quiz coherent, Practice is a
generic textbox exercise on the wrong topic (DNS/networking instead of Windows tools).

### Week 4 — "Working the Queue"
Goals: prioritize by impact · support common peripherals · professional communication.

| TYPE | Title | What student actually does | Current value | Problem | Verdict | Connection to next |
|---|---|---|---|---|---|---|
| L×2 | Priority/Impact/Not Making It Worse, Talking to Humans | Reads static text | Directly on-theme for this week's goals | None major found | **KEEP** | Feed quiz |
| V×18 (4 required) | Mixed video set | Watches | Correctly classified, label not shown | §1 issue | **IMPROVE** (render label) | Feeds quiz |
| Q | Week 4 quiz (id 5) | Takes quiz | Required | Not independently flagged | **KEEP** | — |
| GL | Windows Command-Line Diagnostics | Free-text, run commands on own machine, paste results | SHELL/FAKE, and topically closer to Week 3 ("navigate Windows support tools") than Week 4 (prioritization/peripherals/communication) — see §3 | Doesn't reinforce prioritization or peripheral support, this week's actual goals | **MOVE to Week 3 (or rebuild as a real environment) / REPLACE with a Week-4-appropriate structured exercise** (e.g. a prioritization/triage exercise matching "Priority, Impact, and Not Making It Worse") | Should connect to Week 4 Apply |
| SD | MFA Reset | Real Service Desk ticket | Functional | None found | **KEEP** | Terminal step of Week 4 |
| CS | Capstone (optional) | — | Optional, not required | Out of required path | **KEEP as optional** | — |

**Week 4 assessment:** Learn/Quiz coherent and on-theme. The Practice slot is not
just a fake lab, it is also the clearest week/topic mismatch in the whole set — a
Windows CLI diagnostics exercise sitting in a week about prioritization and peripherals.

---

## 5. Cross-week Practice/Lab reshuffle recommendation

The four Guided Lab templates read like they were built as a themed set (hardware,
networking, Windows CLI, subnetting) and then assigned to Weeks 1–4 by raw id order
rather than topic. Recommended target mapping once rebuilt as real/structured
exercises (implementation phase, not this audit):

- **Week 1** (ticket/CLI basics) → keep CLI Practice (already correct), drop Hardware ID
  as the required lab.
- **Week 2** (hardware) → Hardware Component Identification, rebuilt as genuine structured
  identification with images/diagrams and deterministic feedback (moved from Week 1).
- **Week 3** (Windows tools/diagnostics) → Windows Command-Line Diagnostics, rebuilt with
  real verification instead of free text (moved from Week 4), or reworked into a
  Windows-tool-navigation exercise matching lesson 8/9 content.
- **Week 4** (prioritization/peripherals) → new/rebuilt structured triage exercise, or the
  IP addressing/subnetting content repurposed into something Week-4-relevant, or simply
  drop the required-lab slot here if prioritization is adequately covered by the lesson +
  Service Desk ticket alone.

Any move must preserve `stable_id` semantics and existing student progression records —
this is a Phase 6/7 implementation concern, not resolved by this audit.

---

## 6. Summary counts

- Weeks 1–4 activities reviewed: **93** (23 in Week 1, 23 in Week 2, 23 in Week 3, 24 in Week 4 — counts per the live `/api/admin/training/weeks` payload).
- Videos reviewed: 52 (all correctly classified; 0 missing metadata).
- Lessons reviewed: 12 (all currently render as passive "read → mark complete"; 2 flagged as containing unreachable/dead instructions referencing labs — lesson 3 confirmed, lesson 9 flagged for verification).
- Guided Labs inventoried (all weeks): 5 total; **4 of 4** assigned to Weeks 1–4 are SHELL/FAKE; the 1 REAL lab (AD Break-Fix) is in Week 15, out of scope.
- Structural root causes identified: (1) frontend never renders `job_relevance` on weekly cards despite the API already returning it; (2) `LabPage.jsx` renders one generic template for every `lab_type` with no per-type branching; (3) the 4 Weeks 1–4 lab templates are topically mismatched to the weeks they're assigned to.

## 8. Implementation addendum — Guided Lab rebuild and reshuffle (Phases 4-6)

Implemented on commits `239ecb2`/`1799b1a`/`24531f4`. Final week→lab mapping:

| Week | Lab | lab_type | Status |
|---|---|---|---|
| 1 | none (CLI simulator is Practice) | — | `networking_lab` `meet-cli-001` flipped `is_required=True` |
| 2 | Hardware Component Identification (id 4) | `structured_identification` | Rebuilt: 5 deterministic multiple-choice questions (CPU socket, DDR generation, M.2/NVMe vs SATA, PCIe slot sizing, PSU connectors), moved from Week 1 |
| 3 | Windows Command-Line Diagnostics (id 3) | `structured_diagnostic` | Rebuilt: 5 questions pairing a symptom with realistic tool output (ipconfig, nslookup, tracert, Event Viewer, Task Manager) and asking for the correct interpretation/next step, moved from Week 4 |
| 4 | Prioritize the Queue (new, id 6) | `structured_triage` | New: 5 tickets to prioritize against a stated impact rubric (P1-P4) |
| retired | IP Addressing & Subnetting (id 1), Network Connectivity Scenario (id 2) | — | Unpublished, removed from the required path. Rebuild deferred — subnetting/DNS troubleshooting content belongs to a later networking-focused week, out of this phase's Weeks 1-4 scope |

**Grading**: all three rebuilt/new labs are graded server-side in `submit_lab` — the client posts `{question_id: [selected_option_ids]}`, the server compares against `LabTemplate.success_criteria.questions[].correct` and computes `final_score`/`structured_feedback`. No client-supplied score is trusted. The one real lab (AD Break-Fix, id 5, Week 15) is untouched and keeps its self-attested notes+evidence flow, since it's backed by an actual VM environment.

**Evidence Upload**: `LabPage.jsx` now only renders it when `required_evidence` has actual content — previously showed unconditionally by run status for every lab type.

**Progression safety**: `LabTemplate.week_number` (used by `require_week_reached` gating) and `TrainingWeekActivity.training_week_id` (used for weekly-page display/progress) are independent fields that both had to move together — verified this explicitly against a simulated pre-existing student with `LabRun` history on the retired/moved labs: history survives untouched (LabRun is keyed by `lab_template_id`+`student_id`, never by week), the realignment sync (`sync_weeks_1_4_practice_realignment`) is idempotent (verified by running it 3x with no drift), and `validate_training_curriculum()` reports valid afterward. Full backend suite: 421/421 passing.

## 7. Implementation status (updated after Phases 2–11)

All items below are now complete:

- Rebuilding/moving the 4 fake labs — done, see §8.
- Extracting `JobRelevanceBadge` into a shared component and wiring it into `TrainingWeekPage.jsx` — done (`29220b4`).
- Adding the CLI CTA to lesson 3 and rewriting its summary copy — done (`e784bc3`).
- Verifying lesson 9's summary text against the CLI-diagnostics lab — confirmed it had the same dead-instruction pattern and was softened; no CTA added since that lab's week assignment changed in the reshuffle (`e784bc3`).
- Ticket-note formative exercise for "Anatomy of a Good Ticket" — done (`6c7de7d`).
- Practice/Apply section split on the weekly page — done (`a33ec1b`).
- Mobile/desktop QA passes (Phases 9–10) — done, no horizontal overflow at 375×812 or issues at 1440×1000; covered by `weeks-1-4-quality.spec.js`.
- Automated test coverage (Phase 11) — done: 421/421 backend tests, 13/13 frontend Playwright tests (`my-training.spec.js` + `weeks-1-4-quality.spec.js`), 13/13 Service Desk integration tests unaffected (verified against a clean baseline run — see PR description).

Not done (explicitly out of scope for this phase, per the brief):

- Any quiz question-level content edits beyond the Weeks 1–4 mismatches already covered.
- Rebuilding the retired subnetting/DNS-scenario lab content — deferred to their natural networking-focused week.
