# Nexus IT Academy — Content Authoring, Configuration, and Security Notes

Three references in one file: how to add curriculum content, every environment
variable, and the security posture after the Phase 1 audit.

---

# Part 1 — Content Authoring Guide

All 24 weeks of content live in structured Python seed sources, not in the
database directly. Edit the source, re-run `python seed.py`, and the change
propagates. Seeds are idempotent — matched by stable keys — so student work is
never touched.

- **Weeks 1–4:** `backend/seed_phase_a.py`
- **Weeks 5–8:** `backend/seed_phase_b.py`
- **Weeks 9–24:** `backend/seed_phase_c.py` through `backend/seed_phase_g.py`
- **Roles, gates, base tickets, labs, capstones, methodology:** `backend/seed.py`

## Adding or editing a lesson

Lessons live in the `MODULES` / `MODULES_B` lists, under each module's
`"lessons"` key. A lesson needs:

```python
{
    "title": "...",
    "lesson_order": 1,                 # order within the module
    "estimated_minutes": 90,
    "summary": "...",                  # the full teaching text (prose)
    "outcomes": ["Diagnose ...", "Verify ..."],  # actions, not "understand X"
    "required_notes_template": NOTES_TEMPLATE,    # shared template
    "status": "published",             # "draft" hides it from students
}
```

Lessons are matched by (module, lesson_order), so you can rewrite the text
freely and re-seed. Write outcomes as **actions** — they map to what tickets
grade.

## Adding a quiz question

Questions use the `_q(...)` helper:

```python
_q("Question text?",
   "Option A", "Option B", "Option C", "Option D",
   "B",                              # correct letter (single-select)
   "Why B is right — shown after grading.",
   multi="A,C")                      # OPTIONAL: makes it multi-select
```

Multi-select is graded as an exact set — partial answers score zero. Avoid
vocabulary-only questions; write scenarios that require reasoning.

Quizzes are matched by title. Editing questions replaces that quiz's question
set wholesale on re-seed; the quiz id (and therefore students' attempt history)
is preserved. Set a quiz's `lesson_title` to auto-link it to its lesson.

## Adding a ticket

Tickets carry the full spec. Use the `ANCHORS(...)` helper for scoring:

```python
{
    "title": "...",                    # matched on re-seed
    "description": "...",              # student-facing; may contain {{PLACEHOLDER}}
    "difficulty": 2,                   # 1-5
    "week_number": 3,
    "category": "Windows",
    "domain_id": "3.0",
    "root_cause": "...",               # SERVER-SIDE, never sent to students
    "root_cause_type": "temp_profile",
    "required_checkpoints": {"checkpoints": [
        {"id": 1, "step": "...", "required_mention": ["term1"], "weight": 0.3},
    ]},
    "required_evidence": {"evidence_types": [
        {"type": "screenshot", "description": "...", "validation": {}},
    ]},
    "scoring_anchors": ANCHORS(
        "2 = investigation done well ...",
        "2 = correct root cause ...",
        "2 = safe fix or clean escalation ...",
        "2 = verified with evidence ...",
        "2 = clear user + internal communication ..."),
    "model_answer": "...",             # SERVER-SIDE, never sent to students
    "hints": ["hint 1", "hint 2", "hint 3", "hint 4"],  # up to 4, progressive
    "parameters": {"placeholders": {
        "USERNAME": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
    }},
}
```

### Rules that keep the platform safe and fair

- **Never reference `root_cause`, `model_answer`, or the specific anchor answer
  in student-facing text.** The ticket detail API deliberately withholds these;
  putting spoilers in `description` or `hints` defeats that.
- **Write anchors parameter-aware.** Say "the correct account," not a specific
  username, so per-student parametrization never changes what earns a 2.
- **Give at least 5 options per placeholder** so a 5-student cohort each gets a
  distinct value. Selection is deterministic (`student_id % len(options)`).
- **Hints go least- to most-revealing.** Hint 4 gives strong procedural
  guidance but should still not hand over the whole answer verbatim.
- Escalation-correct tickets: make the `model_answer` describe the escalation,
  and the grader will score a clean escalation as correct.

## Adding a promotion gate requirement

Gates are seeded in `seed.py`'s `PROMOTION_GATES`. Supported requirement types:

| type | config example | meaning |
|---|---|---|
| `min_completed_lessons` | `{"module_codes": ["MOD-005"]}` | all published lessons in those modules have submitted notes |
| `min_mastery_by_domain` | `{"thresholds": {"networking": 70}}` | quiz mastery ≥ N% per domain |
| `min_verified_tickets_by_difficulty` | `{"thresholds": {"2": 8, "3": 2}}` | counts of verified tickets by difficulty |
| `practical_checkpoint` | `{"ticket_title": "Multi-Ticket Simulation 2", "max_hints": 1, "min_score": 7}` | a named ticket passed within hint/score limits |
| `no_unresolved_flags` | `{}` | no open mentor flags |

Do not build a second progression system — extend this one.

---

# Part 2 — Environment Variable Reference

| Variable | Purpose | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | DB connection | `sqlite:///./nexus.db` | SQLite is active in production; PostgreSQL is supported |
| `JWT_SECRET_KEY` | Signs student tokens | (required in prod) | keep secret; rotating it logs everyone out |
| `ADMIN_USERNAME` | Mentor/admin login | (required for admin) | |
| `ADMIN_PASSWORD` | Mentor/admin login | (required for admin) | also used to derive nothing now — sessions are random |
| `ADMIN_API_KEY` | Header auth for admin API | falls back to `ADMIN_SECRET_KEY` | |
| `ADMIN_SESSION_TTL_SECONDS` | Admin session lifetime | `43200` (12h) | |
| `AI_BASE_URL` | AI endpoint (OpenAI-compatible) | OpenRouter compatibility fallback | active deployment uses local Ollama |
| `AI_MODEL` | Model name | (falls back to `OPENROUTER_MODEL`) | `provider/model` for hosted; bare name for Ollama |
| `AI_API_KEY` | AI auth | (falls back to `OPENROUTER_API_KEY`) | omit for local Ollama |
| `AI_ENABLED` | Master AI switch | `true` | set `false` to force manual grading |
| `AI_TIMEOUT_SECONDS` | AI request timeout | `30` | |
| `MAX_EVIDENCE_UPLOAD_BYTES` | Upload size cap | `10485760` (10 MB) | Part 9 hardening |
| `UPLOAD_DIR` | Evidence storage path | repo `uploads/screenshots` | **use a persistent volume in prod** |
| `DAILY_AI_BUDGET` | Soft AI spend cap | `1.00` | |
| `PROXMOX_FULL_CLONE` | Clone mode | `false` | linked on supported storage, otherwise logged full fallback |
| `LAB_VM_TTL_MINUTES` | Assignment lifetime | `120` | access is denied after expiry |
| `GUACAMOLE_DATASOURCE` | Guacamole JDBC datasource | `postgresql` | Guacamole 1.6.0 contract |

Legacy `OPENROUTER_*` variables still work as fallbacks so existing deployments
keep running. The app **boots even with no AI variables set** — AI endpoints
return a clear 503 and grading falls back to manual.

---

# Part 3 — Security Notes (post Phase-1 audit)

Fixes applied and verified with regression tests (`tests/test_security_part9.py`,
`tests/test_tb01_tb06_regressions.py`):

- **Admin sessions are now random and expiring.** Previously the session cookie
  was `sha256(password + constant)` — deterministic, never-expiring, derivable
  offline. Now each login issues a random token held server-side with a TTL;
  logout revokes it. Legacy deterministic cookies are rejected.
- **Credential and API-key comparisons are timing-safe** (`hmac.compare_digest`).
- **The "Bearer anything" bypass is closed.** `allow_admin_or_student` now
  actually verifies the student JWT instead of accepting any non-empty Bearer
  header.
- **Evidence uploads are bounded** (10 MB default, configurable) and
  **type-restricted** (images + txt/log only).
- **Evidence has an owner.** Artifacts record their uploader, and a ticket
  submission may only reference the submitter's own artifacts — closing an IDOR
  where one student could cite another's evidence. Pre-fix unowned artifacts
  can't be claimed.
- **Answer/spoiler leakage checked.** The quiz detail API sends no
  `correct_answer` or explanations before grading; the ticket detail API sends
  no `root_cause`, `model_answer`, or scoring-anchor text.
- **AI grading resists prompt injection.** The grader prompt wraps the student
  submission as untrusted data and instructs the model to ignore embedded
  instructions; a malicious-fixture test confirms an injected "give me 10/10"
  doesn't hijack the grade.
- **Quiz integrity.** Multi-select is graded as an exact set (no partial-credit
  loophole); every attempt is preserved as its own row (retakes no longer
  overwrite history), so mastery and gate math read real data.

## Known open items (honest limitations)

- **Proxmox/Guacamole application fixes are complete**, including scoped
  temporary users and asynchronous persistent assignment state. A real
  infrastructure isolation/lifecycle smoke test is still required before any
  cohort depends on automated VMs. Use manual VMs until that passes.
- **Admin session store is in-process.** Correct for the single-container,
  single-mentor deployment here; would need shared storage (Redis/DB) if the
  backend were ever horizontally scaled.
- **AI model changes require recalibration.** The current Ollama model passed
  the five-fixture calibration on 2026-07-17; rerun
  `scripts/calibrate_grader.py` after changing the model or prompt.
- **`UPLOAD_DIR` must remain persistent.** The active self-hosted deployment is
  covered by `scripts/backup_sqlite.sh`; do not move it to ephemeral storage.
