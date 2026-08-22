# Progression Contract

What "progression" currently means in Nexus: which systems are authoritative,
what each seeded promotion gate actually proves, and what is explicitly
deferred. Written at the end of the progression-foundation refactor
(2026-08-22) so the student-UX redesign that follows can treat this system as
a stable, understood dependency rather than something to re-derive from code
on every touch.

Do not build a second progression system — extend this one. See
`CLAUDE.md` → "Domain boundaries" and `docs/AUTHORING_CONFIG_SECURITY.md` for
the requirement-type reference table.

---

## A. Authoritative systems

These are the only sources of truth for student progression. If a UI needs to
show or gate on progress, it reads from one of these — never from client
state.

| System | Table(s) | Feeds |
|---|---|---|
| Lesson completion | `student_lesson_progress` (server-stamped `completed_at`) | `min_completed_lessons` gates, `derive_current_week` |
| Quiz results | `quiz_attempts`, `quizzes.quiz_purpose="gate"` | `required_quiz` gates, `mastery_service.record_quiz_mastery` |
| Quiz-derived domain mastery | `student_domain_mastery` (`domain_id` in `1.0`–`5.0`) | `min_mastery_by_domain` gates, `get_module_mastery` (quiz half) |
| Service Desk assessment results | `service_desk_attempts` (`experience_mode="assessment"`, `passed=True`), graded server-side in `service_desk_grading.compute_grade` from the attempt's own event log | `min_service_desk_passes` gates |
| CLI lab completion | `cli_lab_attempts.completed_at` | `min_cli_labs` gates |
| Lab runs | `lab_runs.final_score` | `get_module_mastery` (lab half) |
| Role/promotion state | `student_roles`, `students.current_role_id` | `get_promotion_status`, role-gated routes |

**Grading trust:** Service Desk `passed` is never a client-supplied field.
`ServiceDeskAttempt.passed` is set once, server-side, by
`compute_grade()` re-deriving the result from the attempt's `ticket.close`
event and the scenario's server-stored objective definition — the close
event's own `success` flag is explicitly documented in code as "a browser
assertion... never resolution evidence" and is not used for scoring. A
student cannot self-report a pass.

**Ownership:** every authoritative query above filters by `student_id` at the
SQL level (see `_passed_scenario_keys`, `_check_lessons_requirement`, etc.).
One student's evidence cannot satisfy another student's gate — there is no
code path that evaluates a gate against any student other than the one whose
promotion is being checked.

## B. Non-authoritative systems

- **XP is motivational only.** No gate evaluator reads an XP total or ledger
  balance. XP awards happen alongside real evidence (e.g. a passed Service
  Desk attempt) but promotion is decided from the underlying evidence table,
  not from XP.
- **Frontend state does not grant progression.** `frontend/src/pages/QuizzesPage.jsx`
  and `frontend/src/services/api.js` only *read* `/promotion`-shaped
  endpoints. No frontend code computes or writes eligibility; it is a display
  concern only, matching the "frontend guards are UX, not security" rule in
  `CLAUDE.md`.
- **Browser/local state never overrides backend truth.** Every check in this
  document re-queries the database on each call; there is no cached or
  client-supplied progression state trusted by the backend.
- **Video/lesson completion is not practical competency.** Lesson completion
  gates on *reading*, not *doing* — it only unlocks the next content and
  contributes to `min_completed_lessons`. Practical evidence for promotion
  comes from Service Desk / lab / CLI results, never from lesson completion
  alone.
- **Retired Ticket attempts cannot satisfy modern Service Desk requirements.**
  `Ticket`/`TicketSubmission` rows (however old) are never read by
  `_check_service_desk_requirement`, `_check_lessons_requirement`, or any
  other active-gate evaluator. See "Legacy Ticket status" below.

## C. Gate semantics

All five gates are seeded in `backend/seed.py`'s `PROMOTION_GATES` and
evaluated generically by `check_promotion_eligibility()` in
`backend/app/services/progression_service.py`. Every requirement type there
maps to exactly one `_check_*` evaluator (see the table in
`docs/AUTHORING_CONFIG_SECURITY.md`).

### Gate 1 — Trainee → Support Technician I (target: end of Week 4)

Proves: foundational hardware/software troubleshooting, ticket-writing
literacy, and enough hands-on reps to trust the student with real desks.

| Requirement | Config | Evidence source | Satisfiable |
|---|---|---|---|
| `required_quiz` | week 4 | gate-purpose quiz attempts | Yes |
| `min_completed_lessons` | MOD-000..004 | `student_lesson_progress` | Yes |
| `min_mastery_by_domain` | hardware ≥70, software_troubleshooting ≥70 | quiz-fed `student_domain_mastery` | Yes |
| `min_service_desk_passes` | pack `starter-support`, ≥4 | `service_desk_attempts` | Yes |
| `min_cli_labs` | ≥9 | `cli_lab_attempts` | Yes |
| `no_unresolved_flags` | — | `TicketSubmission.admin_comment`/`admin_reviewed` | **Vacuously yes** — see note below |

### Gate 2 — Support Technician I → Support Technician II (target: end of Week 8)

Proves: workplace help-desk competence — client networking and basic security
added to Gate 1's foundation.

| Requirement | Config | Evidence source | Satisfiable |
|---|---|---|---|
| `required_quiz` | week 8 | gate quiz | Yes |
| `min_completed_lessons` | MOD-005..008 | lesson progress | Yes |
| `min_mastery_by_domain` | software_troubleshooting/networking/security ≥70 | domain mastery | Yes |
| `min_service_desk_passes` | pack `desktop-support`, ≥5 | Service Desk attempts | Yes |
| `no_unresolved_flags` | — | (vacuous, see below) | Yes |

### Gate 3 — Support Technician II → Network Support Technician (target: end of Week 12)

Proves: switching, VLANs, and network troubleshooting depth.

| Requirement | Config | Evidence source | Satisfiable |
|---|---|---|---|
| `required_quiz` | week 12 | gate quiz | Yes |
| `min_completed_lessons` | MOD-009..012 | lesson progress | Yes |
| `min_mastery_by_domain` | networking ≥75 | domain mastery | Yes |
| `min_service_desk_passes` | pack `accounts-access`, ≥4 | Service Desk attempts | Yes |
| `min_cli_labs` | ≥20, prefix `dev-sw-` | CLI lab attempts | Yes |
| `no_unresolved_flags` | — | (vacuous) | Yes |

### Gate 4 — Network Support Technician → Junior Systems Technician (target: end of Week 17)

Proves: readiness for Windows Server/AD administration content per the role
description ("Passed Gate 4 — Windows Server, AD, and PowerShell
administration"). **See the dedicated section below — this gate's practical
coverage of that role description is intentionally incomplete right now.**

| Requirement | Config | Evidence source | Satisfiable |
|---|---|---|---|
| `required_quiz` | week 17 | gate quiz | Yes |
| `min_completed_lessons` | MOD-013..017 | lesson progress | Yes |
| `min_service_desk_passes` | pack `networking`, ≥4 | Service Desk attempts | Yes |
| `no_unresolved_flags` | — | (vacuous) | Yes |

### Gate 5 (graduation) — Junior Systems Technician → Junior Infrastructure Administrator (target: end of Week 24)

Proves: integrated readiness across the full curriculum, gated on the Week 23
mixed-queue/incident/handoff readiness quiz (moved there because it assesses
Week 23's content, not Week 24's).

| Requirement | Config | Evidence source | Satisfiable |
|---|---|---|---|
| `required_quiz` | week 23 | gate quiz | Yes |
| `min_completed_lessons` | MOD-018..024 | lesson progress | Yes |
| `min_service_desk_passes` | pack `advanced-troubleshooting`, ≥4 | Service Desk attempts | Yes |
| `no_unresolved_flags` | — | (vacuous) | Yes |

### `no_unresolved_flags` — a known vacuous requirement

`_check_no_flags` counts `TicketSubmission` rows with an unresolved mentor
comment. Since migration `0043_retire_legacy_tickets` removed the only
student-facing way to create a new `TicketSubmission`, no student created
after that migration can ever have one — so this requirement is currently
**always met by construction**, not because mentors have no way to flag a
student. It is not a bug (it fails closed, not open — an unresolved flag
would still block if one existed), but it is not doing meaningful work today.
Recalibrating it onto Service Desk mentor feedback (if/when that exists) is
future work, not part of this phase.

## D. Gate 4 — explicit note

Gate 4's role description promises "Windows Server, AD, and PowerShell
administration" competency. Until 2026-08-22, the seeded config tried to
express that as a `min_mastery_by_domain` requirement on domains
`windows_server` / `active_directory`. Those domain ids never existed in
`student_domain_mastery` (mastery is only ever written for `1.0`–`5.0`
via `record_quiz_mastery`/`record_ticket_mastery_verified`), so the
requirement was **permanently unsatisfiable** for every student — a real
gate-1A bug.

A first fix attempt aliased `windows_server`/`active_directory` onto the
existing `4.0` domain (shared with `security`/`procedures`). That was worse:
it let a student clear "Windows Server & AD" readiness purely from unrelated
security-quiz scores, never touching Windows Server content — a gate-bypass
via domain mismatch, not a real fix.

**Current state:** the sub-requirement is removed. Gate 4 currently proves
lesson completion, the week-17 quiz, and general Service Desk practical
competence (the `networking` pack) — it does **not** independently verify
Windows Server or AD skill.

**Explicitly deferred — do not hack a fix in this phase:**

```
TODO / future competency engine:
- Active Directory
- Windows Server
```

This is intentionally left as a gap rather than mis-mapped, because the
coarse 5-bucket mastery model (`hardware` / `networking` /
`software_troubleshooting` / `security+procedures`) has no bucket that
actually represents Windows Server/AD skill. Representing it correctly needs
either a new mastery domain or the skill-based competency engine planned for
a later phase — not a workaround here.

## E. Legacy Ticket status

`Ticket` / `TicketSubmission` history is intact and untouched — migration
`0043_retire_legacy_tickets` explicitly preserves it, and no commit in this
refactor deletes or rewrites a row in either table.

What changed is reachability, not data:

- The evaluators `_check_ticket_requirement` (`min_verified_tickets_by_difficulty`)
  and `_check_practical_checkpoint` (`practical_checkpoint`) still exist in
  `progression_service.py`, for backward compatibility with any stray
  historical `PromotionGate` row of those types — but no such row can exist in
  a freshly-seeded or re-seeded database (see Seed safety below).
- `get_module_mastery`'s ticket-derived scoring component was removed; it now
  splits 50/50 between quiz and lab averages instead of 30/40/30 with a
  ticket-fed term, so tickets cannot influence module-mastery display either.
- `_check_no_flags` still reads `TicketSubmission.admin_comment`, which is why
  that requirement is vacuous for new students (see above) rather than
  reading from nothing.

Net effect: a student's historical Ticket data — however extensive — cannot
advance or block any *active* gate. It is inert with respect to current
progression. `test_historical_ticket_data_does_not_affect_service_desk_gate_or_module_mastery`
in `backend/tests/test_seed_promotion_gates_service_desk.py` asserts this
directly.

## F. Seed safety

`seed_promotion_gates()` in `backend/seed.py`:

1. **Validates first.** Before writing anything, it runs
   `validate_promotion_gates_config()` (`backend/app/services/promotion_gate_validation.py`)
   against `PROMOTION_GATES` and raises `RuntimeError` if any issue is found —
   unknown/retired requirement type, missing/invalid config field, an
   unresolvable mastery domain or Service Desk pack reference, or a
   duplicated `(role, requirement_type)` pair. A bad row can never reach the
   database via this path.
2. **Upserts by `(role_id, requirement_type)`.** Existing rows get their
   config overwritten in place; new rows are inserted. Re-running seeding
   after editing `PROMOTION_GATES` converges to the new config — this part
   was already idempotent before this phase and remains so
   (`test_seed_promotion_gates_is_idempotent`).
3. **Prunes every orphaned row on every run** — any `PromotionGate` row whose
   `(role, requirement_type)` pair is not present in `PROMOTION_GATES` at
   all, not only rows of the two named-retired ticket types. This is
   deliberate, not accidental scope creep, and it is safe specifically
   because `PromotionGate` is exclusively seed-authored: the only admin
   router touching this table (`admin_content.list_promotion_gates`) is a
   read-only `GET`, so there is no legitimate hand-authored row for the
   prune to ever destroy.
   - It is idempotent — deleting zero matching rows is a no-op — and covered
     by `test_seed_promotion_gates_is_idempotent` and
     `test_no_retired_ticket_requirement_type_in_any_active_seeded_gate`.
   - **Incident this generalization fixes:** the original version of this
     delete only targeted the two ticket-based retired types by name. When
     `30c0912` removed Gate 4's unsatisfiable `min_mastery_by_domain`
     (`windows_server`/`active_directory`) sub-requirement from
     `PROMOTION_GATES`, the *already-seeded* production row was never
     deleted — upsert-only logic has no reason to touch a type no longer in
     the config, and the narrow delete didn't name that type. The result:
     Gate 4 kept enforcing that impossible requirement in production, live,
     through the rest of Phase 1A, even though the code fix had already
     shipped. This was discovered and fixed during Phase 1B
     (`test_seed_promotion_gates_prunes_orphaned_rows_not_just_retired_types`
     is the regression test), after taking a verified backup and confirming
     no other `PromotionGate` row in production was orphaned before
     re-running the corrected seed.

**Production precaution:** back up the production database before running
the updated `seed.py`. This is a standing repo rule
(`CLAUDE.md` → "Before production changes") reiterated here because this
specific seed run performs a real (if narrowly-scoped) delete, and
Ticket/TicketSubmission history — while untouched by this delete — should
never be at risk from an unverified deploy. Do not edit the production
database directly to work around this; re-run the seed after a verified
backup.

## G. Related documents

- `docs/AUTHORING_CONFIG_SECURITY.md` — the requirement-type reference table
  and general content-authoring/security notes.
- `docs/SERVICE_DESK_TRUST_BOUNDARY.md` — identity and trust boundary between
  Nexus and the standalone Service Desk simulator app (a separate concern
  from gate evidence sourcing, which is entirely within Nexus's own
  database).
