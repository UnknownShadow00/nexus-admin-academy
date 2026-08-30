# Nexus V2 — Phase 2A implementation note

**The first end-to-end V2 curriculum MVP: one CompTIA A+ module built
completely, in data.**

Module: `module.aplus.core1.ip_configuration` —
"IP Configuration & Basic Connectivity Troubleshooting"
(CompTIA A+ Core 1, exam **220-1201**, domain **2.0 Networking**).

Everything here is development/testing only. Production remains at schema
`0064` with empty V2 tables. No seed, no deploy, no student migration.

---

## 1. What Phase 2A added

### Content (all data files — no Python holds curriculum)

| Area | File(s) |
|---|---|
| Module + 9 assessments | `backend/content/certifications/comptia_aplus.yaml` (module `module.aplus.core1.ip_configuration`) |
| 5 lessons (Markdown, Phase 1B system) | `backend/content/curriculum/comptia-a-plus/220-1201/ip-configuration/01..05*.md` |
| ~9 learning resources | `backend/content/resources/comptia-a-plus.yaml` (`res.aplus.ipcfg.*`) |
| 3 Explain / interview prompts | `backend/content/interview-prompts/comptia-a-plus.yaml` (`interview.aplus.ipcfg.*`) |
| 40-question bank (CSV) | `backend/content/questions/aplus-ip-configuration.csv` |
| 1 guided practical lab | `backend/content/labs/comptia-a-plus.yaml` |

### Loader extensions (`app/services/v2_content_loader.py`)

* `load_question_banks(db, questions_dir)` — imports every `content/questions/*.csv`
  / `*.xlsx` through the **existing** `app.services.question_importer`
  pipeline (same validation, fingerprint de-dup, freeform grading-metadata
  parsing, companion `question_v2_meta` writes). Questions are never
  hard-coded in Python.
* `load_labs(db, path)` — upserts guided `LabTemplate` rows from
  `content/labs/*.yaml`, matched on `title` (the key `module_assessments.lab_ref`
  resolves against). Never provisions a VM; `proxmox_template_vmid` stays
  NULL unless the file names one.
* `load_content(...)` now also runs those two, then the existing resource /
  interview-prompt loaders. **Run order for full wiring:**
  `load_all` → `load_content` → `load_all` again (the second `load_all` lets
  `module_assessments` resolve the `quiz_ref` / `lab_ref` that only exist
  once `load_content` has created the quiz and lab rows — this is the same
  two-pass pattern Phase 1B established).

### Progress + mentor infrastructure (minimal dev flow)

| Piece | File |
|---|---|
| Migration `0065` (additive) — table `v2_module_activity` | `backend/alembic/versions/0065_v2_module_activity.py` |
| Model `V2ModuleActivity` | `backend/app/models/v2_progress.py` |
| `record_activity()` / `module_progress()` | `backend/app/services/v2_progress_service.py` |
| `module_report()` (mentor data) | `backend/app/services/v2_mentor_service.py` |
| Student router `POST/GET /api/v2/progress/*` | `backend/app/routers/v2_progress.py` |
| Admin router `GET /api/admin/v2/mentor/module/{k}/student/{id}` | `backend/app/routers/admin_v2_mentor.py` |

`v2_module_activity` is **one row per (student, activity_type, ref_key)**,
upserted. It is a development-flow record only: **no** promotion gate, mastery
calc, XP ledger, login streak, or legacy `TrainingWeek` reads it. Nothing
migrates existing students.

---

## 2. Objective mapping (exact, no invented codes)

The module maps to three objectives, all present in
`backend/content/objectives/comptia-a-plus-220-1201.yaml`:

| Code | Objective (abbreviated) | Lessons |
|---|---|---|
| **2.5** | Install/configure basic wired/wireless SOHO networks (IPv4/IPv6, APIPA, static vs dynamic, DNS, DHCP, subnet mask, gateway) | 1, 2, 3, 4 |
| **5.7** | Troubleshoot common wired/wireless network problems (APIPA/link-local, no/limited connectivity) | 2, 3, 4, 5 |
| **5.1** | Apply the CompTIA best-practice troubleshooting methodology | 5 |

220-1202 objectives `1.2` (Microsoft command-line tools) and `1.6` (Windows
networking configuration) were considered for the Windows-commands lesson but
**not used**: a lesson under a 220-1201 module can only map 220-1201
objective codes (the loader resolves codes within one certification version).
Lesson 5 maps to `5.7` + `5.1` instead. No objective number was invented.

Coverage after load (`certification_version_coverage`, 220-1201):
`covered = {2.1, 2.5, 5.1, 5.7}` (2.1 is the pre-existing Phase 1B fixture
lesson), everything else still correctly uncovered. **Not** aiming for 100%
A+ coverage — only this module.

---

## 3. Question bank (40 questions, real, in CSV)

`backend/content/questions/aplus-ip-configuration.csv`, quiz title
`A+ IP Configuration & Basic Connectivity — Module Bank`.

| Type | Count |
|---|---|
| single-choice MCQ | 28 |
| multi-select MCQ | 2 |
| short_answer | 7 |
| free_response (Explain) | 3 |
| **total** | **40** |

By objective: `5.7` ×24, `2.5` ×14, `5.1` ×2. Mix of terminology,
scenario/application, and troubleshooting-reasoning items.

Every row carries the full V2 metadata set: `certification=comptia_aplus`,
`certification_version=comptia_aplus_220-1201`, `domain=2.0`,
`module=module.aplus.core1.ip_configuration`, per-question `objective_code`,
`importance` (38 job_critical, 2 working_knowledge — not mechanically all
job_critical), `source_name=Nexus curriculum team`, `permission_status=owned`,
and an `explanation` that teaches *why*.

**Existing-question audit (read-only against production `nexus.db`, 1009
questions).** 36 rows use IP/DHCP/APIPA/DNS/gateway/`ipconfig` vocabulary,
spread across ~14 quizzes (`IP Addressing Quiz`, `Client Network Triage`,
`Network Troubleshooting Quiz`, `Windows Command-Line Diagnostics`, …). None
carry V2 metadata yet.

| Disposition | Count | Notes |
|---|---|---|
| **NOT RELEVANT** to this module | ~11 | Network+ subnetting depth, ARP/MAC learning, Linux `/etc/hosts`, RFC1918 range-trivia, spoofing. Out of A+-beginner scope. |
| **EDIT before reuse** | ~15 | Sound stems (APIPA self-config, "ping IP works / name fails", `ipconfig` 169.254, DHCP UDP ports) but need V2 metadata, provenance, and a teaching explanation before they can be imported. Candidates for a later consolidation pass. |
| **KEEP as-is** | 0 | None are import-ready without the metadata/explanation edit above. |
| **ARCHIVE** | 0 | No action taken — this phase does not modify the production bank. |

Decision: **author a fresh 40-question bank** for the MVP rather than
edit-and-migrate 15 legacy rows in place. The legacy rows stay untouched in
production; folding the ~15 EDIT candidates into the V2 bank is future
cleanup, not MVP-blocking. The new bank's answers were each validated
independently while authoring; distractors are plausible; no duplicate stems.

The imported quiz is created **draft / not validated / not in the practice
library** — invisible to students until a mentor validates it, exactly like
the ExamCompass import convention. It is **not** wired to any `TrainingWeek`
(`week_number = 0`) or the legacy 40% A+ gate.

---

## 4. Assessments wired (module YAML → existing engines)

| Role | Key | Engine ref | Resolved? |
|---|---|---|---|
| quick_check ×5 | `assess.aplus.ipcfg.qc.*` | quiz `A+ IP Configuration…Module Bank`, `displayed_count` 4–5, pass 60% | ✅ quiz_id |
| module_quiz | `assess.aplus.ipcfg.module_quiz` | same bank, `displayed_count` 12, pass **70%** | ✅ quiz_id |
| practical | `assess.aplus.ipcfg.practical` | lab `A+ Practical — Inspect Windows IP Configuration` | ✅ lab_template_id |
| service_desk | `assess.aplus.ipcfg.service_desk` | `service_desk_ref: inc2503` | row present; scenario_id resolves only where `inc2503` is seeded |
| explain | `assess.aplus.ipcfg.explain` | Phase 1B interview-prompt data | n/a (data-role) |

### CLI practice — documented limitation

The `frontend/src/features/cli-labs` xterm engine is a **Cisco-IOS switch
simulator**; its PC terminal supports only `ping` and `arp -a`. It cannot
execute `ipconfig`, `ipconfig /all`, `nslookup`, or `ipconfig /release|/renew`.
Extending it is a major, separate piece of work.

Phase 2A therefore does **not** fake an interactive Windows CLI. Command
coverage lives in Lesson 5's Markdown (full reference table + the six-step
methodology), the `res.aplus.ipcfg.mslearn.*` command-reference resources,
and 7 `short_answer` questions that test command recall
(e.g. "What Windows command displays the current IP configuration?" → `ipconfig`).
An interactive Windows CLI sandbox is deferred.

### Practical lab — guided, no VM

`A+ Practical — Inspect Windows IP Configuration` (`lab_type: guided`,
`proxmox_template_vmid: null`). The student inspects any working Windows
machine's IPv4 address / subnet mask / default gateway / DNS with `ipconfig
/all`, runs `ping`/`nslookup`, and answers six diagnostic questions against
the real output. Reuses the existing `LabTemplate` engine (`success_criteria`
/ `required_evidence` / `hints` / `model_solution`).

A **fully broken VM** (169.254.x.x APIPA fault to remediate) is deferred to
**Phase 2B** — building one significantly expands scope (Proxmox template,
break script, Guacamole wiring).

### Service Desk — reuse, don't reinvent

`assess.aplus.ipcfg.service_desk` maps the module to an existing,
already-validated, already-server-graded scenario (`inc2503`, a workstation
that lost network connectivity after an office move) via `ModuleAssessment`
role `service_desk`. No second ticket engine.

A **dedicated APIPA / 169.254 Service Desk scenario** is deferred to
**Phase 2B**: `service_desk_scenario_validation.validate_scenario_definition`
requires at least one required objective producing *server-verifiable tool
evidence*, and the current SD simulator's supported action types are
directory / asset / ticket / shipping / remote-desktop operations — there is
**no network-diagnostics tool** that could evidence `ipconfig /release
/renew` or DHCP-reachability steps. The APIPA storyline is still fully
covered in 2A by Lesson 2, the `169.254` free-response Explain prompt, the
guided practical, and 8 scenario/troubleshooting questions in the bank.

---

## 5. Grading

* **short_answer** → `deterministic_grader.grade_short_answer` against the
  stored `acceptable_answers` (`["ipconfig", "ipconfig.exe", "ip config"]`
  etc.), `answer_match_mode = normalized`: case / spacing / edge-punctuation
  tolerant, so `ipconfig`, `IPConfig`, `  ipconfig ` all pass; a short wrong
  answer is a confident fail; a long rambling answer → `needs_review`.
* **free_response / Explain** → `deterministic_grader.grade_free_response`
  against `expected_concepts` (concept + aliases) with `rubric_version =
  ipcfg-2026-08-a`, `min_concepts_for_pass = 4`, `partial_credit = true`.
  A thorough APIPA answer clears the threshold deterministically; a vague
  answer returns `needs_review` — which is exactly the state the **Phase 1C**
  `pending_grades` pipeline picks up (durable job → local AI attempt →
  mentor review). **No AI grade is faked.** The GPU grading server is not
  provisioned; ambiguous answers simply stay pending / manual.

---

## 6. Student progress + mentor data

`record_activity()` writes one upserted `v2_module_activity` row per
(student, activity_type, ref_key). `module_progress()` rolls it up for the
student's own view (lessons done, resources done, quick-check states, module
quiz score/pass, practical / service-desk / explain states, `module_complete`).

`module_report()` answers, for a mentor, per (student, module):

* completion state, lessons/resources completed vs total
* module-quiz score + pass/fail + threshold
* **missed questions** (from the quiz activity's `detail.missed_question_ids`)
* **objectives those missed questions map to** (join `question_v2_meta.objective_code`)
* **weak objectives** ranked by missed count, with objective text
* Explain / free-response state — pulled from the Phase 1C `pending_grades`
  pipeline *and* any directly-recorded Explain activity
* practical + Service Desk results

No polished dashboard — this is the backend/service/API layer, which is all
Phase 2A requires.

---

## 7. Data-driven maintenance — proven

`tests/test_v2_aplus_ip_module.py` proves normal curriculum maintenance needs
**no Python change**:

* `test_editing_markdown_updates_lesson` — edit a lesson `.md`, re-run
  `load_content`, `content_hash` changes.
* `test_editing_resource_yaml_updates_resource` — change a resource YAML
  title, re-run `load_resources`, the stored resource updates.
* `test_adding_and_updating_a_question_via_csv` — add a question row to a CSV
  → it imports as a new question; edit that row's `explanation` in the CSV
  and re-run → the stored question updates, **no new row**, no seed code.
* `test_load_is_idempotent` — full `load_all`/`load_content` re-runs create
  nothing new and keep the question count stable.

Note: the question importer **re-syncs each row in place** on every run
rather than diffing, so a `load_content` rerun reports questions as
"updated" even when nothing changed. That is a harmless no-op write, not a
duplicate; the idempotency guarantee for questions is *no new rows, stable
set*. `test_v2_content_and_assessment.py::test_shipped_content_loads_and_reruns_clean`
was updated to reflect this (lessons/resources/prompts/labs still rerun
fully clean).

---

## 8. Tests

`cd backend && ./.venv/bin/python -m pytest -q` → **701 passed, 0 failed**
(was 682; +19 new in `tests/test_v2_aplus_ip_module.py`; 2 Phase 1B tests +
1 prod-guard test updated for the new module/migration — see below).

New: `tests/test_v2_aplus_ip_module.py` (19 tests) — module + lessons
created, idempotent load, resource mapping, objective mapping (only real
codes, coverage math), question-bank breakdown + V2 metadata, module-quiz /
quick-check wiring, practical + Service Desk mapping, short-answer grading,
free-response pending path, student progress + mentor weakness data, upsert
idempotency, "no legacy `TrainingWeek` / student touched", quiz not wired to
`TrainingWeek`, the four data-driven proofs, and the student + admin router
surfaces (incl. 422 on bad activity type, 404 on unknown module).

Updated (Phase 2A intentionally adds content + a migration, not a bug):
* `test_v2_content_and_assessment.py::test_shipped_content_loads_and_reruns_clean`
  — questions exempt from the "zero updated" rerun check (importer re-syncs
  in place); still asserts zero creates and clean rerun for everything else.
* `test_v2_content_and_assessment.py::test_module_assessments_load_with_roles_and_optional_lesson_ref`
  — the assertion "no practical/service_desk role exists" now scopes to the
  `networking_fundamentals` fixture module (the new module legitimately adds
  those roles).
* `test_alembic_prod_guard.py::test_cli_scratch_database_upgrade_and_downgrade`
  — head-revision assertion made head-agnostic (reads `alembic heads`)
  instead of hard-coding `0064`.

Migration `0065` verified on a scratch DB via the Alembic prod-guard opt-in
workflow: `upgrade head` → `downgrade 0064` → `upgrade head` all clean;
`v2_module_activity` columns + indexes match the ORM model. The
`test_v2_aplus_ip_module.py` suite additionally exercises the ORM
`create_all` path. **Production `nexus.db` was never a migration target** —
only `DATABASE_URL=sqlite:////<scratch>` was used.

Frontend: **no frontend code changed** in Phase 2A, so no `npm` build/tests
were run.

---

## 9. Manual dev smoke (no production accounts)

Driven by an in-memory SQLite DB + a throwaway dev student (`test_*` fixtures
and the router tests):

| Step | Result |
|---|---|
| `load_all` → `load_content` → `load_all` | module id, 5 lessons, quiz (40 Q), lab, 11 resources, 4 prompts, 12 module assessments; second `load_content` idempotent (only in-place question re-sync) |
| Lesson complete (`POST /api/v2/progress/activity`) | recorded; `GET /api/v2/progress/module/{k}` shows `lessons.completed` incrementing |
| Resource complete | recorded; `resources.completed` reflects it |
| Quick Check pass | recorded (status `passed`, score) |
| Module Quiz (fail, with `missed_question_ids`) | recorded; `module_complete` stays false |
| Practical (guided, complete) | recorded |
| Service Desk (`needs_review`) | recorded; row visible in report |
| Explain prompt (`needs_review`) | recorded; surfaces in `explain_state` |
| Mentor report (`GET /api/admin/v2/mentor/module/{k}/student/{id}`) | returns completion, quiz score, missed questions, **weak objective 5.7 (missed_count 2) with objective text**, explain state, practical/SD results |

**Stubbed / deferred (documented above):** interactive Windows CLI sandbox;
broken-VM connectivity lab; dedicated APIPA Service Desk scenario; AI grading
of ambiguous Explain answers (stays pending — GPU server not provisioned);
polished student/mentor dashboards; folding the ~15 legacy EDIT-candidate
questions into the V2 bank.

---

## 10. Production confirmation

* **No production seed.** Loaders do not run automatically and were never run
  against `nexus.db`.
* **No deploy.** No code shipped; no service restarted.
* **No student migration.** `v2_module_activity` is empty; the 7 production
  students are untouched.
* Read-only prod check: `nexus-admin-academy.service` **active**, `/health`
  **200**, `alembic_version` still **`0064_v2_ai_grading_infrastructure`**
  (migration `0065` NOT applied to prod), all V2 tables present and empty,
  legacy counts sane (students 7, questions 1009, quizzes 114,
  training_weeks 35). The Alembic production guard remains enabled and was
  not bypassed.
* **Operator deploy script:** `~/bin/nexus-deploy` (dated Aug 28) is still
  **stale** — it differs from repo `scripts/deploy.sh` and its
  `alembic_backend()` lacks `NEXUS_ALLOW_PROD_MIGRATION=1`, so the prod guard
  would **block** its migration step. It needs refreshing from
  `scripts/deploy.sh` before the next deploy. (Reported only; not modified.)

---

## 11. Recommendation

**Approve this module pattern and expand A+.** The data-driven pipeline holds:
a module, its lessons, resources, prompts, a real question bank, a practical,
and Service Desk wiring were all built without touching application code
beyond two small additive loader functions and one additive progress table.
The two-pass `load_all` / `load_content` / `load_all` sequence and the
"questions re-sync in place" quirk are the only rough edges — both are
documented and neither blocks authoring the next module.

Before scaling, two small clean-ups worth doing (not blockers): (a) give
`load_question_banks` a real change-detection skip so reruns report questions
as unchanged; (b) do one consolidation pass folding the ~15 legacy
EDIT-candidate networking questions into V2 metadata so the bank isn't
duplicating concepts the production bank already covers.

---

# Phase 2A.1 — cleanup & quality-control pass (2026-08-29)

Applied after Phase 2A was approved technically. No new module, no Network+,
no production seed/deploy/migration, no student UI redesign. Production still
at `0064`, V2 tables empty.

## 1. Question-sync change detection

`question_importer._apply_question_fields` and `_upsert_question_v2_meta` now
diff-and-set (via a shared `_diff_set` helper) and return whether anything
actually changed. `confirm_import` returns a new **`unchanged`** count and only
re-stamps `imported_at` / `import_filename` when content or V2 metadata
genuinely changed. Result:

* new row → `created`
* unchanged row → `unchanged` (a true no-op: no write, no provenance churn)
* changed content **or** changed V2 metadata (objective, importance,
  permission, rubric, …) → `updated`

Preserved unchanged: fingerprint de-duplication, question IDs/history,
preview/confirm behaviour, the admin `/api/admin/question-import/confirm`
contract (the extra key is additive; the log line now includes `unchanged`),
provenance, and V2 metadata. A `load_module` / `load_content` rerun now
reports every entity — questions included — as `unchanged`.

## 2. Single high-level module loader

`v2_content_loader.load_module(db, *, commit=False, …dirs)` runs the whole
sequence in one call: `load_all` → `load_content` (lessons, question banks,
labs, resources, prompts) → `load_all` again to reconverge
`module_assessments` engine refs. It returns the merged `LoadSummary` plus a
`references` block:

```
references: {
  content_engine_assessments, content_engine_resolved,
  content_engine_unresolved,          # quick_check/module_quiz/practical that
                                      # still have no quiz/lab (fixture module
                                      # networking_fundamentals has 2 — it never
                                      # defined a quiz_ref; not this module)
  service_desk_assessments, service_desk_resolved,   # scenario owned by a
                                      # separate Service Desk seed
}
```

`load_all` and `load_content` gained an optional shared `summary=` param so the
three passes accumulate into one summary. Curriculum authors call `load_module`
and never need to know about the two-pass ordering. Lower-level loaders were
not rewritten.

## 3. Legacy question review (read-only; production untouched)

Re-audited the production bank (`nexus.db`, 1009 questions): **81 rows** use
IP/DHCP/APIPA/DNS/gateway/`ipconfig` vocabulary once the net is widened.
Classification of every plausible candidate for THIS module:

| Bucket | Count | Notes |
|---|---|---|
| **KEEP / EDIT (migrated)** | 6 | Nexus-authored seeds (`seed_key nexus-authored:*`, `source_type=seed`, `editorial_status=validated`, answer keys validated). See table below. |
| **DUPLICATE** | ~20 | Same concept as a stronger new question — e.g. #834 (APIPA T/F wall-of-text) vs the new APIPA MCQs; #837/#838 (subnet-mask / gateway T/F) vs the new "what does it tell the computer" MCQs; #1150/#1152/#4019/#4055/#4056/#4058/#4063/#4066/#4072 (169.254, IP-vs-name, gateway-off-subnet, wrong-mask, local-vs-remote) all already covered; #1261/#1262/#1264/#4018 (ipconfig/ping/nslookup recognition) covered by the short-answer recall items and the new scenario items. |
| **NOT RELEVANT** | ~40 | AD/Group-Policy/OU (#4098/#4106/#4112/#4114–#4116/#4120), Linux/`ip a`/`/etc/hosts`/journalctl/cron/nginx/SSH (#4142–#4153), Azure/NSG (#4167–#4176), ARP/MAC-learning & VLAN/DHCP-relay/SVI depth = Network+ (#4069/#4071/#4075/#4088/#4090/#4093), DNS record types A/AAAA/CNAME/MX/NS (#805–#808 — explicitly Network+ depth in Lesson 4), port-number trivia (#772–#774), PXE/TFTP OS-deploy (#1198/#1210), NIC loopback plug (#860), spam gateway / proxy / NetBIOS (#758/#799/#802), `tracert`/`pathping` (#1266/#1267 — out of this module's command scope), `netstat -ano` / login-speed (#4012/#4014). |
| **ARCHIVE CANDIDATE** | ~15 | The ExamCompass-derived family (`IP Addressing Quiz`, `Network Protocols Quiz`, `TCP & UDP Ports Quiz`, `Network Services / Configuration Concepts Quiz`, `Microsoft Command-Line Tools Quiz`): `source_type=examcompass`, `editorial_status=archived`, `answer_keys_validated=0`, explanations are the generic "Validated against the cited technical reference; correct selection: X" stub. #824/#825/#827–#829/#831–#835/#837/#838 etc. Provenance is only "permitted" under the blanket Phase 1A ExamCompass decision, quality is unconfirmed, and every useful concept is already covered. **Not migrated.** (Recommend the platform team formally archive/replace these in a later cleanup — this phase does not modify production.) |
| **KEEP as-is (import ready with no edit)** | 0 | Even the 6 migrated ones needed at least metadata + a stem/option rewrite. |

### Legacy questions actually migrated into the V2 bank (6)

All are genuinely Nexus-authored (`seed_key nexus-authored:*`) → recorded as
`permission_status: owned`, `source_name: "Nexus curriculum team (adapted from
seed <seed_key>)"`, copied — **not moved** — via the CSV workflow; the
production rows are untouched.

| Origin seed_key | New concept in bank | Obj | Importance | Edit made |
|---|---|---|---|---|
| `client-network-triage:03` | `nslookup name` fails but `nslookup name 1.1.1.1` works → configured DNS server at fault (compare-against-known-good-resolver technique) | 5.7 | job_critical | terse stem → full scenario; metadata |
| `client-network-triage:05` | "fixing" a DHCP failure with a hand-typed static from the pool → future address conflict | 2.5 | job_critical | full-sentence stem/options; metadata |
| `server-dns-dhcp-and-powershell:02` | stable device address = **DHCP reservation** (MAC→IP), not a manual static | 2.5 | working_knowledge | reframed server→workstation; metadata |
| `server-dns-dhcp-and-powershell:08` | **DHCP scope exhaustion** → new clients get APIPA (server-side cause, distinct from a link fault) | 5.7 | job_critical | reworded to a technician framing; metadata |
| `ipv4-addressing-and-subnetting:05` | private IPv4 ranges multi-select that forces "169.254 is APIPA, **not** private" | 2.5 | job_critical | widened options; APIPA-contrast framing; **replaced** the old single-choice private-range item |
| `windows-command-line-diagnostics:04` | which CLI tools actually diagnose "no internet" (multi: `ipconfig /all`, `ping`, `nslookup`; not `gpresult` / `sfc`) | 5.1 | job_critical | full-description options; metadata |

## 4. New Phase 2A questions removed or edited (and why)

Removed **6** from the original 40 (all superseded, not just trimmed to a count):

| Removed | Why |
|---|---|
| "Which address block is a private IPv4 range?" (single) | replaced by the stronger multi-select from `ipv4-addressing-and-subnetting:05` that also teaches APIPA ≠ private |
| "Which command asks a client to obtain a fresh DHCP lease?" (MCQ) | pure duplicate of the `ipconfig /renew` **short-answer** recall item (harder format kept) |
| "Which command clears the local DNS name cache?" (MCQ) | pure duplicate of the `ipconfig /flushdns` short-answer |
| "Which command shows DNS servers / DHCP state …?" (MCQ) | pure duplicate of the `ipconfig /all` short-answer |
| "`ipconfig /all` shows DHCP Enabled: Yes but no DHCP Server + 169.254 …" (single) | third near-identical APIPA-recognition item; concept covered by two others + the practical; its slot went to the distinct **scope-exhaustion** concept |
| "`nslookup … Non-existent domain`, server shows 8.8.8.8 — best fix?" (single) | overlapped the "why internal DNS matters" item; replaced by the sharper compare-against-known-good-resolver technique from `client-network-triage:03` |

Net: 40 − 6 + 6 = **40** (count is incidental — the goal was one strong item
per concept, no weak duplicates).

## 5. Final question bank — count & breakdown (40)

| Question type | Count |
|---|---|
| single choice | 26 |
| multi-select | 4 |
| short answer | 7 |
| free response | 3 |

| Style | ~Count |
|---|---|
| scenario / application / troubleshooting-reasoning | 20 |
| terminology / basic knowledge | 13 |
| recall / explain (short-answer + free-response) | 7 |

| Objective | Count | Note |
|---|---|---|
| 2.5 (SOHO IPv4/DHCP/DNS/gateway/APIPA) | 16 | |
| 5.7 (connectivity troubleshooting) | 21 | the module's core; A+ domain 5 is 28% of the exam |
| 5.1 (troubleshooting methodology) | 3 | single objective, assessed at recognition level — **intentionally light**, not forced up |

| Importance | Count |
|---|---|
| job_critical | 37 |
| working_knowledge | 3 (IPv6 recognition, "ping timeout ≠ outage", DHCP reservation) |
| awareness | 0 — intentional; nothing in a hands-on connectivity module is background-only |

**Balance verdict:** not imbalanced. Scenario-heavy (right for A+),
troubleshooting-weighted (right for this module), APIPA/169.254 is the
most-covered single concept (~7 items across recognition / characteristics /
causes / server-side cause / remediation / explain) — deliberate, since it is
*the* signature A+ connectivity symptom and objective 5.7 names it explicitly.
No duplicate fingerprints (asserted in tests).

## 6. Lesson-quality changes (small, targeted)

| Lesson | Change |
|---|---|
| 1 IPv4 Basics | §5 wrong-mask example now flags the forward reference ("you will see exactly why … in the *Default Gateway* lesson") so a beginner isn't asked to assume routing they haven't met. `Watch/read` items tagged *(required)/(optional)*. |
| 2 DHCP & APIPA | Removed a `Watch/read` bullet that named a **Microsoft Learn "TCP/IP addressing and APIPA"** doc that is not in the resource data (avoids an invented/dead link). §6 fixed a **misleading** sentence: it implied "DHCP Enabled: No" + 169.254 means the adapter is on automatic — rewritten to "DHCP Enabled: No = a manual/static config, DHCP isn't involved, check the typed-in IPv4 properties." |
| 3 Default Gateway | `Watch/read` aligned to the linked resources; *(required)/(optional)* tags. |
| 4 DNS Basics | `Watch/read` aligned; tags. |
| 5 Windows Commands | `Watch/read` rewritten to match the linked resources and dropped a `tracert` mention (out of this module's command scope — `ipconfig`/`ping`/`nslookup` only). |

No lesson was expanded into a textbook chapter. Reviewed for: beginner
readability (good — plain language, defined-on-first-use), WHY-it-matters
(every §2 ties to a real ticket), not-yet-taught assumptions (only the Lesson-1
forward reference, now signposted), commands-explained-before-use (yes),
realistic workplace examples (yes — office move, mapped drive, "internet is
down"), exam-trivia crowding (low — scenario-led), technical accuracy (one
misleading DHCP sentence fixed), Network+ creep (bounded — Lesson 4 explicitly
defers record types; no ARP/VLAN depth), methodology clarity (Lesson 5's
six-step list is concrete and worked through an example). **Diagram
opportunities flagged for a later pass:** Lesson 1 (the four values on one
`ipconfig` screen), Lesson 3 (local-vs-remote decision → gateway), Lesson 5
(the ping ladder loopback→name). Not built now.

## 7. Resource changes

* **Added** `res.aplus.ipcfg.messer.network_troubleshooting` ("Professor Messer
  — Network Troubleshooting", 220-1201) — a real, free, relevant video that
  three lessons referenced in prose but that had no data entry. Linked
  **required** to Lesson 5, **optional** to Lessons 3 and 4. URL is the stable
  course index (no invented deep link), matching the other Messer entries.
* Every lesson's `Watch/read` list now matches exactly the resources linked to
  that lesson in `content/resources/comptia-a-plus.yaml`, each tagged
  *(required)/(optional)*.
* Verified: URLs well-formed; provider/title mappings sensible; each lesson has
  exactly one required "watch/read" anchor; `mslearn.nslookup` is shared by
  Lessons 4 and 5 (one row, two links — not a duplicate); all
  `permission_status: permitted`, `license_note` = linked/not-rehosted; no paid
  or private content.
* "Opened ≠ mastered" confirmed by design: `StudentResourceActivity` has
  separate `opened_at` vs `completed`/`completed_at`; `module_progress` counts
  a resource done only when its activity status is `completed`/`passed`; the
  model docstring states no gate evaluator reads that table.

## 8. Practical / Service Desk / Explain review (no expansion)

Roles are complementary:

| Activity | Question it answers | Engine |
|---|---|---|
| Quick Check (5) | "Do you understand the concept?" | quiz, per-lesson, formative |
| Module Quiz (12 of 40) | "Can you recognise / apply it?" | quiz, summative, 70% |
| Practical (guided lab) | "Can you inspect / use the tools?" | `LabTemplate`, `ipconfig`/`ping`/`nslookup` on a real machine + 6 diagnostic questions |
| Service Desk (`inc2503`) | "Can you troubleshoot a real ticket?" | existing SD engine, server-graded |
| Explain (3 interview prompts) | "Can you explain your reasoning?" | `InterviewPrompt` data, mentor-facing |

One **acceptable topical overlap**, documented as intentional: the 3
free-response items *inside the question bank* (169.254 scenario; IP-works-
names-don't; local-works-remote-fails) sit close to two of the three
`InterviewPrompt` prompts. They are kept because they live in different engines
and serve different moments — a bank free-response is graded formatively inside
the quiz flow (deterministic-first → Phase 1C pending path), while an
`InterviewPrompt` is the mentor-facing summative "Explain" role. The 169.254
free-response with its specific rubric is also a hard Phase 2A requirement.
Interview prompt #1 ("what does DHCP do") has no bank counterpart. No content
change made. Broken-VM APIPA lab and the Windows CLI sandbox remain deferred to
Phase 2B.

## 9. Data-driven maintenance — re-proven

`tests/test_v2_aplus_ip_module.py`:

* `test_editing_markdown_updates_lesson` — edit `.md` → `content_hash` changes.
* `test_editing_resource_yaml_updates_resource` — edit resource YAML → row updates.
* `test_adding_and_updating_a_question_via_csv` — add row → `created`; re-run
  unchanged → `unchanged: 1, updated: 0`; edit explanation → `updated: 1`.
* `test_question_sync_detects_real_changes` — `created 40` → re-import identical
  → `unchanged 40` with **no `imported_at` churn** → edit one explanation →
  `updated 1 / unchanged 39` → edit one `objective_code` → `updated 1 /
  unchanged 39` (V2-meta path) → add one row → `created 1` → **no duplicate
  fingerprints**.
* `test_load_module_is_one_call_and_resolves_all_refs` — `load_module` once:
  every `assess.aplus.ipcfg.*` engine ref resolves; a second call changes
  nothing.
* `test_load_is_idempotent` — full rerun: `created 0`, `updated 0`, questions
  `unchanged 40`.

## 10. `~/bin/nexus-deploy`

**Refreshed.** Backed up to `~/bin/nexus-deploy.bak.20260829-095712` (matches
the previous stale copy), then overwritten from the reviewed
`scripts/deploy.sh`. Now byte-identical to the repo script (sha256
`02f99a68…`). Verified: contains the Alembic `NEXUS_ALLOW_PROD_MIGRATION=1`
opt-in in `alembic_backend()`; `--allow-db-ahead` protection intact; `bash -n`
syntax OK; exec bit preserved. **No deployment, no migration, no production DB
access** — a file copy plus read-only checks. No operator action remains for
the script itself.

## 11. Tests & production

* Full backend suite: **705 passed / 0 failed** (was 701; +4 net new tests).
  `compileall` clean; `ruff` clean on every changed file.
* New/updated tests: `test_question_sync_detects_real_changes`,
  `test_load_module_is_one_call_and_resolves_all_refs`,
  `test_bank_has_no_duplicate_fingerprints`,
  `test_legacy_derived_questions_carry_provenance`; the idempotency and
  CSV-edit tests tightened to assert the new `unchanged`/`updated` counts; the
  `loaded` fixture now dogfoods `load_module`. Phase 1B
  `test_shipped_content_loads_and_reruns_clean` restored to the strict
  "`created == 0 and updated == 0`" form now that questions detect no-ops.
* V1 progression, the Alembic production guard, and the grading tests are
  unchanged and green.
* Production (read-only): service **active**, `/health` **200**,
  `alembic_version` still **`0064`**, `v2_module_activity` **absent** in prod,
  all V2 tables empty, legacy counts sane (students 7, questions 1009, quizzes
  114, training_weeks 35, lessons 80), `nexus.db` mtime unchanged
  (`07:40:52`). No seed, no migration, no student migration, no deploy, guard
  not bypassed.

## 12. Remaining rough edges

* `load_module`'s `references.content_engine_unresolved` always lists the two
  `networking_fundamentals` fixture assessments (that Phase 1B module never
  defined a `quiz_ref`). Harmless, but a caller filtering "did MY module wire
  up" must match on the key prefix. Could be scoped per-module later.
* The ExamCompass-derived networking questions in production (`editorial_status
  = archived`, unvalidated) are still there. Out of scope to touch; flagged for
  a platform-team archive/replace pass.
* Diagram assets for Lessons 1/3/5 would help beginners — deferred.
