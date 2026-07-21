# Technical Verification Review

Date: 2026-07-21. Phase 15. All checks in this document were **re-run
directly by Claude against the live production system this session**
(`nexus-services`, hostname-confirmed), not inferred from prior documents —
per the brief's instruction not to repeat outdated findings unless still
present in the current code. Where a finding duplicates something already
documented in `docs/SECURITY_HEADERS_AND_SESSION_REVIEW.md` or
`docs/DEEP_RESEARCH_FINDINGS_RECONCILIATION.md`, it is cited and re-verified,
not re-derived from scratch.

---

## 1. Fresh verification results (all run 2026-07-21, this session)

| Check | Result |
|---|---|
| `python -m py_compile` on every changed/live backend `.py` file | **Pass**, no errors |
| `alembic current` | **`0029 (head)`** — matches the documented head, no drift |
| `python -m pytest tests/ -q` | **176 passed**, 0 failed (8 deprecation warnings only — `passlib`'s `crypt` import and one SQLAlchemy 2.0 legacy-API warning, both pre-existing and non-blocking) |
| `PRAGMA integrity_check` on the live `nexus.db` | **`ok`** |
| `PRAGMA foreign_key_check` on the live `nexus.db` | **0 violations** |
| `npm audit` (frontend) | **0 vulnerabilities** |
| `npm run build` (frontend) | **Success**, 1983 modules transformed, build completes in 2.18s |

This exactly reproduces the July 19/21 checkpoint state noted in CLAUDE.md
(176 tests, 0029 head, clean integrity/FK, 0 npm vulnerabilities) — **no
regression has occurred since that checkpoint**, despite this session's live
ticket-submission testing and the temporary admin-setting change (both fully
reversed, see below).

## 2. Pre-existing bundle-size warning (unchanged, not new)

`npm run build` still emits its standing warning: the main JS chunk is
978.44 kB (275.77 kB gzipped), over Vite's 500kB advisory threshold. This is
not a new regression and does not block or break the build; a genuine
code-splitting pass (dynamic `import()` for admin-only routes, which are a
large share of the bundle per the per-chunk breakdown) would be worthwhile
but is a P4 performance-quality item, not a launch blocker.

## 3. Security posture — re-verified live, not re-derived

- **HTTPS redirect:** `curl -I http://nexus.builtfromzero.fyi/` returns
  `301` to the HTTPS origin — **confirmed live this session**, resolving the
  gap that `SECURITY_HEADERS_AND_SESSION_REVIEW.md` had flagged as
  outstanding at that document's time of writing. Cloudflare's "Always Use
  HTTPS" (or equivalent) has evidently since been enabled.
- **Security headers:** `curl -I https://nexus.builtfromzero.fyi/api/health`
  confirms CSP, HSTS, X-Content-Type-Options, and (per the existing
  document) Referrer-Policy/Permissions-Policy are all present.
- **Still-present, still-minor, previously documented:** headers are still
  duplicated on proxied `/api/` paths (nginx `add_header` at the server
  block level plus the FastAPI middleware both firing) — values are
  identical, no security impact, cosmetic only. Confirmed still true this
  session; the documented fix (scope nginx's `add_header` to `location /`
  and `location /assets/` only) remains valid and unapplied.
- **CSRF middleware:** confirmed functioning live this session — the
  initial ticket-test submissions were correctly rejected with `403
  CSRF_REJECTED` until an `Origin` header matching the trusted set was
  added, exactly matching the documented design in
  `SECURITY_HEADERS_AND_SESSION_REVIEW.md`.
- **Rate limiting:** confirmed functioning live this session — the 4th and
  5th ticket-grading calls within one minute correctly received `429 Rate
  limit: Max 3 calls per minute` (surfaced as a wrapped `500`, see TECH-002
  below).

## 4. New findings from this session's live technical work

**Finding TECH-001 (P1, restates TICKET-001 from the technical-cause
angle).** `require_a_plus_unlocked()` is called at 12 separate enforcement
points across `tickets.py`, `labs.py`, `capstones.py`, `cli_labs.py`, and
`evidence.py` (grep-confirmed), gating essentially all hands-on platform
functionality behind a 40%-of-137-videos threshold that is completely
undocumented in the student-facing UI. This is a genuine, currently-live
production behavior, re-verified live this session (403 reproduced, then
threshold temporarily lowered to 0% to complete ticket testing, then
restored to 40% — confirmed via a final `GET /api/admin/settings/a-plus-
unlock` read showing `40`, matching the pre-test value exactly). See the
Ticket Review for the full beginner-impact analysis.

**Finding TECH-002 (P3).** AI-grading rate-limit rejections propagate as a
generic `HTTPException(500, f"AI grading failed: {exc}")` (`tickets.py`'s
broad `except Exception` around the grading call), which means a **429
condition is reported to the student as a 500** with an internal-sounding
message ("AI grading failed: 429: Rate limit: Max 3 calls per minute")
rather than a distinct, friendly 429 response. Low-risk, but worth a small
fix: catch the rate-limit exception specifically and re-raise it as its own
429 with student-facing copy.

**Finding TECH-003 (P4).** `TicketSubmitRequest.grade_now` is accepted by
the schema but never read in `submit_ticket()` — AI grading always runs
synchronously regardless of the flag's value. Dead field; either wire it up
(to support a genuine draft-save-without-grading flow, which could also
help with the rate-limit pressure in TECH-002) or remove it.

**Finding TECH-004 (P3, restates LAB-002 from the technical angle).**
`evidence_validator.py`'s `must_contain_text` check is implemented only for
`artifact_type == "log"`, never for `artifact_type == "screenshot"` — yet
ticket 1's own `required_evidence` JSON specifies a `must_contain_text` rule
on a `screenshot`-type evidence item. This is a schema/implementation
mismatch: the data model supports a validation rule that the validator
silently never applies for the most common evidence type in the program.

**Non-finding, verified and cleared:** the earlier working hypothesis (from
the content-dump read) that Week 24 had a duplicate "Lesson 1" was
**checked directly against `lessons`/`modules` tables this session** and is
**not a bug** — Week 24 legitimately spans two modules (MOD-023 "Integrated
Operations," 2 lessons, and MOD-024 "The Capstone: Take Over Maple &
Finch Co.," which owns the capstone-briefing lesson), each with correct,
non-colliding `lesson_order` sequences. The apparent duplication was an
artifact of the content-dump script grouping both modules under one "Week
24" markdown heading. Corrected in the 24-Week Review.

## 5. Automated VM / Proxmox / Guacamole status — re-confirmed disabled

`admin_vm_assignments` returns 0 rows live; all 5 `LabTemplate` rows have
`proxmox_template_vmid = NULL`. No Proxmox/Guacamole environment variables
were probed directly this session (out of scope — this review does not have
infrastructure-level access beyond the application's own DB/API), but the
application-level evidence is unambiguous and consistent with the CLAUDE.md
record that these env vars are unset in production. **Confirmed disabled,
as required.**

## 6. Backup and persistence

Not independently re-verified this session (would require host-level cron/
filesystem access outside this review's browser+API scope); the existing
record (`scripts/backup_sqlite.sh`, nightly 23:30 cron, 14-day retention,
restore proven 2026-07-17, per CLAUDE.md) is taken as still current absent
any contrary evidence. **Not re-tested — carried forward from existing
documentation, not re-derived.**

## 7. Summary findings

- **TECH-001 (P1):** A+ unlock gate blocks all hands-on work invisibly —
  same root cause as TICKET-001, listed here for the technical-verification
  record.
- **TECH-002 (P3):** Rate-limit 429s surface as generic 500s to students.
- **TECH-003 (P4):** Dead `grade_now` field.
- **TECH-004 (P3):** `must_contain_text` evidence validation is a no-op for
  screenshots, the most common evidence type.
- **No regressions found** versus the July 19/21 checkpoint: compile, full
  test suite (176/176), Alembic head, SQLite integrity/FK, npm audit, and
  npm build are all clean, re-verified fresh this session.
- **One suspected finding (duplicate lesson numbering) was investigated and
  cleared** — documented here specifically so it is not mistakenly
  re-reported as real in a later phase.
