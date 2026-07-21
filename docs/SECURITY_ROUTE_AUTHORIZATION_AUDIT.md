# Route-by-Route Authorization Audit

Date: 2026-07-21
Scope: every FastAPI route registered in `backend/app/main.py`, read directly from
`backend/app/routers/*.py` and cross-checked against `app/services/auth_service.py`
and `app/services/admin_auth.py`. This is a point-in-time audit; re-run it whenever
a new router or route is added.

## Auth primitives referenced below

- `get_current_student` (`app/services/auth_service.py`) — accepts a verified JWT via
  `Authorization: Bearer` or the httpOnly `student_session` cookie. Rejects unless the
  token has `exp`+`sub` and the algorithm is in the `HS256/384/512` allowlist.
- `verify_admin` (`app/services/admin_auth.py`) — accepts `X-Admin-Key` header (constant-time
  compare against `ADMIN_API_KEY`) OR a valid, non-expired `admin_session` cookie
  (random token, server-tracked, 12h TTL).
- `allow_admin_or_student` — accepts either a valid admin session, a verified Bearer JWT,
  or the `student_session` cookie.
- `ensure_student_access(current_student, student_id)` (`app/services/auth_service.py`) —
  403s unless `current_student.id == student_id` or `current_student.is_mentor`.

## Admin sub-router mounting — verified no gap

`app/routers/admin.py` mounts `admin_quiz`, `admin_tickets`, `admin_students`, and
`admin_content` with no prefix/dependencies of its own:

```python
router = APIRouter()
router.include_router(admin_quiz.router)
router.include_router(admin_tickets.router)
router.include_router(admin_students.router)
router.include_router(admin_content.router)
```

Each sub-router declares its own `dependencies=[Depends(verify_admin)]` at
`APIRouter(...)` construction time, which FastAPI bakes into every route defined on
that router before `include_router()` ever runs. Mounting order and the lack of a
prefix on the parent router does not strip these — every route from all four modules
requires `verify_admin`. `admin_curriculum.py` is mounted directly in `main.py` and
carries the same `dependencies=[Depends(verify_admin)]` on its own router.

## Per-router inventory

### `auth.py` (no prefix)

| Method | Path | Auth | Access | Ownership | State-changing |
|---|---|---|---|---|---|
| POST | /auth/login | none (issues session) | public | n/a | Y |
| GET | /auth/me | `get_current_student` | student | returns caller's own data only | N |
| POST | /auth/logout | none | public | n/a | Y (clears cookie) |

### `admin_session.py` (prefix `/api/admin/session`, no router-level dependency)

| Method | Path | Auth | Access | Ownership | State-changing |
|---|---|---|---|---|---|
| GET | /status | none | public (reveals only whether a session is active) | n/a | N |
| POST | /login | inline `validate_admin_credentials` | public entry point | n/a | Y |
| POST | /logout | none | public | n/a | Y (server-side revocation) |
| GET | /student-token | inline `has_valid_admin_session` check | admin (manually gated) | n/a | Y (mints mentor JWT) |

**Finding (informational):** `/student-token` guards itself with a manual
`has_valid_admin_session(request)` check instead of `Depends(verify_admin)`, so it
only recognizes the cookie path, not `X-Admin-Key`. Functionally correct (still 403s
without a valid session) but inconsistent with the rest of the admin surface.

### `admin_content.py`, `admin_curriculum.py`, `admin_quiz.py`, `admin_students.py`, `admin_tickets.py`

All routes require `verify_admin` at the router level. All cross-student visibility
(e.g. `/api/admin/students/overview`, `/api/admin/submissions`) is intentional admin
tooling, not an ownership gap. Full method/path list verified during this audit;
omitted here for brevity — every route in these five files is `admin`-only,
`verify_admin`-gated, with no route missing the dependency.

**Finding (informational, audit-trail only):** `admin_tickets.py`'s `verify_proof`
handler hardcodes `submission.verified_by = 0` — the single shared admin credential
means individual admin actions aren't attributable. Not an authorization gap in a
one-mentor deployment; worth revisiting if the admin model ever becomes multi-user.

### `capstones.py`, `cli_labs.py`, `commands.py`, `resources.py`, `search.py`

All routes use `Depends(get_current_student)`. None accept a foreign student-owned
resource ID without scoping the query to `current_student.id` (capstone/lab/lesson
IDs here are shared curriculum objects, not student-owned). No gaps.

### `evidence.py` (prefix `/api/evidence`)

| Method | Path | Auth | Access | Ownership | State-changing |
|---|---|---|---|---|---|
| POST | /upload | `get_current_student` | student | `EvidenceArtifact.student_id = current_student.id` set at creation (`# Part 9: uploader ownership`) | Y |

`ticket_id` references a shared curriculum object, not a student-owned one — no
cross-student check needed there. Size cap (`MAX_EVIDENCE_UPLOAD_BYTES`, bounded
read) and extension/MIME allowlist both enforced before write.

### `flashcards.py`

`POST /{card_id}/rate` filters `FlashcardReview.id == card_id AND student_id ==
current_student.id` — returns 404 rather than another student's card. No gap.

### `labs.py` (prefix `/api/labs`)

All routes scope `LabRun`/`VmAssignment` lookups through `_get_lab_run(db, lab_id,
current_student.id)`. `POST /{lab_run_id}/evidence` explicitly checks
`run.student_id != current_student.id → 403`. No gap. Guacamole scoped-access
issuance (`guacamole_service.create_scoped_access`) never returns the admin token —
only a per-assignment temporary user's own token.

### `lesson_notes.py`

No `student_id`/`note_id` parameter exists at all — every read/write is scoped to
`current_student.id` implicitly, addressed only by the shared `lesson_id`. No gap.

### `quizzes.py`, `students.py`, `study_tracker.py`, `submissions.py`, `tickets.py`

Every route that accepts a foreign `student_id` (path, query, or body) calls
`ensure_student_access(current_student, student_id)` before using it, or fetches the
owning row first and checks it (e.g. `submissions.py` fetches the submission, then
calls `ensure_student_access(current_student, submission.student_id)` before
returning any data). `tickets.py`'s submit flow additionally verifies
`before_screenshot_id`/`after_screenshot_id` belong to the submitting student
(`# Part 9: a submission may only reference the submitter's own artifacts`).

**Finding (privacy, confirm intent — not an auth bug):** `GET /api/students`
returns every student's `name`/`email`/`last_active_at` to any authenticated
student, not just mentors; combined with `GET /api/leaderboard` (XP/level for all
students), any logged-in student can enumerate the full roster including emails.
Plausibly intentional for this 6-person cohort's social/leaderboard features —
confirm before treating as a gap. Not launch-blocking.

**Finding (confirmed, fixed during this review):** `tickets.py`'s
`POST /uploads` read the full multipart body into memory before checking the 5MB
per-file cap, with no aggregate cap across multiple files in one request —
inconsistent with the already-hardened `evidence.py` bounded-read pattern. See
`docs/DEEP_RESEARCH_FINDINGS_RECONCILIATION.md` for fix status.

### `admin.py` sub-mounting

See above — verified no gap.

## Static file mount (`/uploads/screenshots`) — no per-request auth

`app/main.py` mounts `StaticFiles(directory=...)` at `/uploads/screenshots` with no
auth dependency — anyone with a direct URL can fetch a screenshot. Filenames are
`uuid4()`-generated (128 bits of entropy) at upload time, so this relies on
unguessability rather than an access-control check. This is consistent with how
the evidence/ticket-upload flows already work (the API responses that hand back a
`storage_key`/filename are themselves auth-gated) and is a common, accepted
tradeoff for small self-hosted apps serving image evidence — flagged here for
visibility, not as a launch blocker. If this ever needs tightening, the fix is a
signed/expiring URL or a proxied download route behind `get_current_student` +
ownership check, not a schema change.

## Live spot checks performed

- `curl -H "Authorization: Bearer garbage"` against a protected route → 401 (JWT
  decode required; no longer accepts arbitrary bearer strings).
- Student JWT against an admin-only route → 403 (no `verify_admin` bypass).
- `admin_session_status` and `AdminAccessGate.jsx` round-trip confirmed server-side
  (not a `localStorage`-only gate — see `frontend/src/components/AdminAccessGate.jsx`).

## Summary

No route was found with a foreign resource ID that skips a required ownership
check. The two informational findings (student roster email exposure,
`verified_by` audit-trail gap) are documented for the operator to confirm intent;
neither blocks the manual-VM cohort launch.
