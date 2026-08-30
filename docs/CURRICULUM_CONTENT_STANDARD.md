# Nexus V2 — Curriculum Content Standard

Owner-facing ZIP and folder intake is documented in
[`CURRICULUM_INTAKE_WORKFLOW.md`](CURRICULUM_INTAKE_WORKFLOW.md).

Status: **Phase 0 (planning only).** Defines how V2 curriculum content is
structured, labelled, authored, and reviewed. No content is produced here.

Companion: `docs/NEXUS_V2_PRD.md`, `docs/NEXUS_V2_MIGRATION_PLAN.md`.

---

## 1. Hierarchy

```
Certification
└── Certification Version            (e.g. A+ 220-1201 / 220-1202)
    └── Domain                       (an official objective domain, e.g. 1.0 Mobile Devices)
        └── Module                   (a coherent skill promise, e.g. "Windows Troubleshooting")
            ├── Lesson [1..n]        (short, single-topic)
            │   └── Quick Check      (3–5 questions; 5–7 if Job Critical)
            ├── Module Assessment    (Module Quiz, drawn from the Module Question Bank)
            └── Practical Work       (guided practice, independent lab, Service Desk ticket, Explain — as warranted by Importance)
```

Certification-level assessments sit above modules:

```
Certification Version
├── Certification Knowledge Review   (~40–60 mixed questions)
├── Certification Practical Final    (~4–8 troubleshooting scenarios)
└── Interview / Explain Review       (~3–5 prompts)
```

### 1.1 Identity rules

- Every entity has a **stable key** independent of title and display order.
  Renaming a module or reordering lessons never breaks progress or content
  references. (Same principle as today's `curriculum_structure.py` stable IDs
  and `questions.seed_key`.)
- Suggested key shapes:
  - certification: `cert.aplus`
  - version: `cert.aplus.v.220-1201` (a version row may span paired exams;
    see A+ note in the PRD)
  - domain: `cert.aplus.220-1201.domain.1_0`
  - module: `module.aplus.windows_troubleshooting`
  - lesson: `lesson.aplus.windows_troubleshooting.boot_failure_isolation`
- Display order is a separate integer field per level, unique within parent.
- One recommended path: modules are globally ordered within a certification
  version; students advance by passing checks, not by date.

## 2. Lesson template

Every lesson is a Markdown file with frontmatter. Body sections are fixed and
appear in this order. Sections 6 and 7 are omitted only when genuinely N/A
(e.g. a pure-concept Awareness lesson with no tooling).

```markdown
---
lesson_key: lesson.aplus.windows_troubleshooting.boot_failure_isolation
title: Isolating Windows Boot Failures
certification_version: cert.aplus.v.220-1202
domain: cert.aplus.220-1202.domain.3_0
module: module.aplus.windows_troubleshooting
lesson_order: 3
importance: job_critical            # job_critical | working_knowledge | awareness
learning_relationship: new          # new | review | deep_dive
builds_on: []                       # list of lesson_keys this deep-dives / reviews
objectives:                         # official objective codes, >=1 required
  - "3.1"
  - "3.2"
estimated_minutes: 15
status: draft                       # draft | review | published
---

## 1. What is this?
Two or three plain sentences. No jargon before it is defined.

## 2. Why does an IT worker care?
The concrete job situation where this matters.

## 3. Watch / read
Curated free resources (see §5). Each is support, not replacement.

## 4. What you need to remember
A short bullet list. The load-bearing facts only.

## 5. Real workplace example
A short, realistic scenario a technician would actually meet.

## 6. Commands / tools
Only when relevant. Real commands, real output shapes.

## 7. Interview / example question
One question a hiring manager might ask, with a model answer outline.

## 8. Quick Check
Reference to the lesson's Quick Check question set (by objective/tag or an
explicit question-key list). Questions themselves live in the question bank
(XLSX/CSV), not inline.
```

### 2.1 Length and tone

- Short. A lesson is one topic. If it needs two Quick Checks, it is two
  lessons.
- Beginner-first. Assume near-zero working experience despite the cert.
- Every lesson answers "why do I care" before "how does it work".

## 3. Importance labels

Set per lesson (`importance`). Drives how much practical work is attached and
how large the Quick Check is.

| Label | Meaning | Practical expectation |
|---|---|---|
| **Job Critical** | You will do this on the job, hands-on, regularly. | Full loop: Learn → Quick Check (5–7) → Guided Practice → Independent Lab → Service Desk Ticket → Explain. |
| **Working Knowledge** | You need to understand and apply it, but less often / lower stakes. | Learn → Quick Check (3–5) → at least one practice or troubleshoot activity. |
| **Awareness** | You should recognise the term and the idea; depth not required now. | Learn → Quick Check (3–5). Practical optional. |

An existing near-equivalent already lives on `curriculum_videos.job_relevance`
(`job_critical` / `know_it` / `awareness`). V2 renames `know_it` →
`working_knowledge` and extends the label from videos to lessons and
questions.

## 4. Learning Relationship labels

Set per lesson (`learning_relationship`). Keeps certification progression
visible when topics recur across certifications.

| Label | Meaning | Rule |
|---|---|---|
| **New** | First real teaching of this concept in the path. | Teach from the ground up. |
| **Review** | Same concept, light refresher before using it again. | Do not re-teach in full; link `builds_on` to the New lesson. |
| **Deep Dive** | Advances a concept already taught earlier. | Assume the New lesson; teach only the delta. Link `builds_on`. |

Example: A+ "DNS Basics" = New. Network+ "DNS Deep Dive" = Deep Dive,
`builds_on: [lesson.aplus.networking.dns_basics]`. Security+ "DNS Security" =
New within Security+, `builds_on` both. Network+ must **not** contain a second
beginner DNS lesson.

## 5. Video / resource rules

- Nexus is the primary tracker. Resources are external and supportive.
- Each resource row records: `title`, `provider`, `url`, `type`
  (video / article / doc / practice), `objective_codes`, `duration`
  (if video), `importance` inherited or overridden, `source_name`,
  `permission_status` (see §9), `active`.
- V1 tracking granularity: **opened / completed / marked watched**. Video
  completion is learning *activity*, not mastery, and does not by itself
  complete a module.
- Approved primary free sources:
  - A+ / Network+ / Security+: Professor Messer; official CompTIA objectives;
    other high-quality free resources.
  - Linux: LPI official objectives/material; reputable free Linux tutorials;
    real CLI practice.
  - Azure: Microsoft Learn; official Microsoft study guides; free Microsoft
    Practice Assessments where useful.
  - ITIL: short Nexus-authored lessons; free explanatory resources; realistic
    Service Desk scenarios.
- **Do not assume content is reusable just because it is publicly reachable.**
  Linking out is fine; copying text/questions/images into Nexus requires
  recorded permission.

## 6. Question authoring standards

- Questions are **data**: authored/maintained in XLSX/CSV and imported via the
  existing importer (`question_importer.py`), extended with the V2 fields.
- Never hardcode question banks into Python/source.
- Preferred workflow: edit spreadsheet → importer preview (validation +
  fingerprint duplicate detection) → confirm. Imported content lands
  `draft` / unreviewed / student-invisible until an editorial pass validates
  answer keys.
- Sources questions may come from: existing Nexus questions; ExamCompass
  **where permission exists**; other proven free/community banks where reuse
  is permitted; official/vendor practice material where permitted;
  questions created/reviewed by the owner with ChatGPT/Claude/Gemini;
  Nexus-authored practical/scenario questions.
- Every question records provenance (§9).

### 6.1 Question record fields

| Field | Notes |
|---|---|
| `question_id` | Stable. Nexus-authored questions also get a `seed_key`. |
| `certification`, `certification_version` | Which cert/version this question belongs to. |
| `domain`, `module` | Placement. |
| `objective_code` | One or more official objective codes. Required. |
| `importance` | job_critical / working_knowledge / awareness. |
| `question_type` | `single` / `multi` / `true_false` / `short_answer` / `free_response`. |
| `question` | Stem text. |
| `options` | For choice types: A–H (min 2 non-blank). |
| `correct_answer` | Choice types: letter(s). |
| `acceptable_answers` | Short answer: accepted strings + synonyms. |
| `expected_concepts` | Short answer / free response: concepts that should appear. |
| `explanation` | Required before publish. |
| `difficulty` | 1–5. |
| `source_name`, `source_url` | Where it came from. |
| `permission_status` | See §9. Only `owned` / `permitted` may be published. |
| `active` | Soft on/off without deletion. |

### 6.2 Validation (reuses `question_validation.py`, extended)

- ≥2 non-blank options for choice questions; correct answers must reference
  real options; `multi` needs ≥2 correct; "Select N" in the stem must match N
  correct answers.
- Short answer requires ≥1 `acceptable_answers` **or** ≥1 `expected_concepts`.
- Free response requires `expected_concepts` and a rubric reference (§8).
- Explanation required before `published`.
- Duplicate detection via content fingerprint (existing sha256 of
  title+stem+options).

## 7. Assessment sizes

| Assessment | Displayed questions | Bank / pool |
|---|---|---|
| Lesson Quick Check | 3–5 (Job Critical: up to 5–7) | The lesson's own tagged questions |
| Module Quiz | 10–15 | Module Question Bank: **20–40+** questions so retakes randomise |
| Certification Knowledge Review | 40–60 mixed | All published module banks for the version |
| Certification Practical Final | 4–8 scenarios | Practical/scenario question pool for the version |
| Interview / Explain Review | 3–5 prompts | Interview prompt set for the version |

Small lessons do not each get a large quiz. The Module Quiz is the
consolidation point.

## 8. Free-response rubric requirements

Applies to `short_answer` and `free_response` questions and to Interview /
Explain prompts.

- **Rubric is versioned.** Each rubric has a `rubric_version` string; changing
  criteria bumps the version.
- **Grading order (hard requirement):**
  1. Deterministic acceptable-answer / expected-concept match.
  2. Partial-credit rubric evaluation (per-criterion points).
  3. AI fallback only for genuinely ambiguous responses.
- **AI grading is rubric-driven**, never free-form scoring. Pattern already in
  the codebase: `service_desk_objectives.py` process categories with weights
  (Investigation 15 / Diagnosis 25 / Remediation 30 / Verification 20 /
  Documentation 10), graded deterministically in `service_desk_grading.py`
  against an immutable scenario definition.
- **Every stored grade records:** `rubric_version`, grader/model version,
  score, confidence (if available), reasoning summary, timestamp, mentor
  override (if changed).
- Exact wording is never required. Concept coverage and correctness are what
  count.
- Low-confidence AI grades are flagged for mentor review.
- **Outage rule:** if AI grading is unavailable the answer still saves, status
  = `pending_grading`, auto-retries later, student never resubmits.

## 9. Content provenance / licensing fields

Carried by every question **and** every resource.

| Field | Values / notes |
|---|---|
| `source_name` | Human-readable origin ("Professor Messer", "ExamCompass", "Nexus author + ChatGPT review", "Microsoft Learn"). |
| `source_url` | Direct link where applicable. |
| `permission_status` | `owned` (we wrote it) · `permitted` (explicit reuse permission on file) · `requested` (asked, awaiting) · `unknown` (default for legacy) · `denied`. |
| `license_note` | Free text — the specific permission/licence basis. |
| `active` | Soft enable/disable. |

Publication gate: only `owned` or `permitted` content may be set
`published` / student-visible. `unknown` and `requested` stay in the
editorial queue. This generalises today's behaviour where imported
ExamCompass content lands invisible and unreviewed.

## 10. Lab requirements

Reuse existing infrastructure; do not rebuild.

| Lab type | Backing | Content format |
|---|---|---|
| CLI / terminal lab | `cli_labs` + `features/cli-labs` simulator | Data-driven lesson JSON (already the pattern) |
| Guided lab | `lab_templates` / `lab_runs` | `environment_requirements`, `success_criteria`, `required_evidence`, `hints`, `model_solution` JSON |
| VM lab | `lab_templates.proxmox_template_vmid` + `vm_assignments` + Proxmox + Guacamole | Proxmox template + break/verify scripts |

Per practical activity, author must specify: objective code(s), Importance
tie-in, environment, explicit success criteria, required evidence,
progressive hints, and a model solution / expected outcome. Independent labs
for identity/network topics must include safe verification and rollback
steps.

## 11. Service Desk ticket standards

The Nexus Service Desk simulator is a core asset — keep and expand it. Do not
replace it with Zammad/osTicket/GLPI.

- Preserve the troubleshooting-process philosophy, which is already encoded as
  the grading rubric:
  **Investigation → Diagnosis → Remediation → Verification → Documentation.**
- Scenarios are **versioned and immutable once published**
  (`service_desk_scenario_versions`, definition hash, append-only event log,
  server-side deterministic grade).
- Realism ladder (author scenarios along this progression):
  1. **Guided** — explicit steps, heavy hinting.
  2. **Assisted** — prompts at decision points.
  3. **Independent** — student drives the whole process.
  4. **Mixed Support Shift** — a queue of mixed tickets under time/priority
     pressure.
- Each scenario records: objective code(s), Importance tie-in, priority,
  the required evidence per process category, the pass rule, and hint ladder.
- A ticket is proof of *practical competence for its objectives*, attached to
  the module's practical work — not a substitute for the Module Quiz.

## 12. Interview / Explain standards

- 3–5 prompts per certification version, plus optional per-module prompts for
  Job Critical modules.
- Each prompt records: objective/topic, `expected_concepts`, a versioned
  rubric, and a model answer outline.
- Graded by the §8 order (deterministic concept check → rubric → AI fallback).
- Responses and their full grading history are **permanent student progress
  records**, visible to the mentor.
- Purpose is spoken-explanation fluency for real interviews — clarity and
  correct reasoning, not memorised phrasing.

## 13. Publication-quality checklist

A lesson/module may move `draft → review → published` only when **all** hold:

**Lesson**

- [ ] Frontmatter complete: stable key, certification version, domain,
      module, order, `importance`, `learning_relationship`, ≥1 `objectives`.
- [ ] `learning_relationship` of `review` / `deep_dive` has a valid
      `builds_on` list.
- [ ] All 8 template sections present (6 and 7 only omitted if truly N/A).
- [ ] Every external resource has `permission_status` ∈ {owned, permitted}
      or is link-only.
- [ ] Reading level is beginner-appropriate; jargon defined on first use.
- [ ] Quick Check exists with the right size for the Importance label.

**Module**

- [ ] Every lesson published.
- [ ] Module Question Bank ≥ 20 questions, all with answer keys validated and
      explanations present.
- [ ] Module Quiz configured to draw a randomised 10–15 from the bank.
- [ ] Practical work attached appropriate to the highest Importance lesson in
      the module (Job Critical → full loop).
- [ ] Every module objective maps to ≥1 lesson and ≥1 question.
- [ ] No uncovered official objective silently dropped (listed explicitly if
      deferred).

**Certification version**

- [ ] Official objective list loaded as data.
- [ ] Objective coverage report shows either coverage or an explicit,
      recorded deferral for each objective.
- [ ] Knowledge Review, Practical Final, and Interview/Explain sets exist and
      meet their size targets.
- [ ] All content `permission_status` ∈ {owned, permitted}.
