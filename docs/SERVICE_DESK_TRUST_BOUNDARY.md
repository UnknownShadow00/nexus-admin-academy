# Service Desk Trust Boundary

Nexus and the standalone Service Desk simulator (`service-desk-app`, a sibling
Next.js repo) are two applications. This document is the authoritative record
of who trusts whom, for what, and why — written during the Phase 1/2 backend
integration work (2026-08-01). Update it whenever the trust boundary changes.

## Identity

Nexus is the sole identity provider. Students never authenticate directly
against `service-desk-app`.

- Nexus issues a signed JWT (`JWT_SECRET_KEY` / `JWT_ALGORITHM`, HS256/384/512)
  via `backend/app/services/auth_service.py::create_access_token`, carried in
  the `student_session` cookie.
- `service-desk-app` verifies that same JWT itself, using the same shared
  secret, in `apps/web/lib/nexus-auth.ts::verifyStudentSession` — it never
  calls back to Nexus just to check "is this token valid." This is a shared-
  secret verification pattern, not a per-request signed handoff token. It is
  gated behind `NEXUS_INTEGRATION=1` / `NEXT_PUBLIC_NEXUS_INTEGRATION=1`
  (default off; audited but not yet enabled in this phase — enabling it is a
  deployment decision, not made here).
- Admin/mentor access inside `service-desk-app` (`/admin` routes) is decided
  by `apps/web/lib/nexus-auth.ts::hasNexusAdminAccess`, which trusts the JWT's
  `is_mentor` claim directly, or falls back to asking Nexus
  (`GET /api/service-desk/admin-check`, forwarding the raw `admin_session`
  cookie) when the student isn't a mentor. Nexus — not the Next.js app — is
  the final word on admin status.
- No token, password, or secret is ever stored in `service-desk-app`'s
  browser-side `localStorage`. The only client-visible cookie is the same
  `student_session` cookie Nexus already set.

**Audit result (this phase):** `nexus-auth.ts` / `middleware.ts` /
`api/session/route.ts` were reviewed line-by-line. No changes were needed —
algorithm is pinned to an allow-list (no `alg: none`), the payload shape is
strictly validated before use, and admin bypass requires either a verified
mentor claim or an explicit Nexus round-trip. The bridge was already built
correctly; it was simply dormant.

## What the Service Desk app is allowed to tell Nexus

The Service Desk app runs deterministic simulation logic (ticket state
machine, tool interactions, objective evaluation) client-side, because that
logic lives in `packages/simulation-engine` (TypeScript) and has no Python
equivalent. Nexus cannot independently recompute it today. Given that
constraint, the trust boundary is:

- **Allowed:** raw action events (`tool used`, `command entered`, `note
  written`, `hint requested`, `field changed`) — these are stored verbatim as
  an append-only audit trail (`service_desk_attempt_events`, added in commit
  3a56c30) with a server-assigned, monotonic `sequence_number` and a
  client-supplied `idempotency_key` that Nexus deduplicates on. The client
  cannot rewrite history — events are immutable once stored (enforced by a
  SQLAlchemy `before_update`/`before_delete` listener in
  `service_desk.py`), and it cannot skip/reorder them, because Nexus assigns
  the sequence number, not the client.
- **Not allowed:** telling Nexus "give this student N XP" as a bare number.
  Fixed as of this phase — see below.

## Score/pass computation — arithmetic is server-side, but the underlying facts mostly aren't (scope corrected 2026-08-07)

`POST /api/service-desk/attempts/{id}/complete` now accepts only an
idempotency key, and the *arithmetic* — priority points, hint penalties,
closure penalties — is computed server-side in `service_desk_grading.py`
from the immutable published scenario definition and the append-only event
log. Client-supplied grade fields are no longer accepted or used.

**However, the single boolean that arithmetic is built on —
`resolved = close_event.success is True and
close_payload.get("verifiedResolved") is True` (`service_desk_grading.py`,
`compute_grade`) — is taken directly from the client-supplied `success` and
`payload` fields on the `ticket.close` event
(`ServiceDeskEventCreate.success`/`.payload`, both unconstrained client
input) for every scenario, not only the Remote Desktop ones.** A prior
version of this document scoped this gap to `INC2406`–`INC2408` only; that
was inaccurate. The only scenario-specific *independent* server-side
verification is `_directory_objective_satisfied`, which replays real
directory-tool actions to confirm `INC2401`/`INC2405`'s objective — and even
that only adjusts a 0.5–1.0 score multiplier, not the `resolved` flag itself.
For the other 6 of 8 seeded scenarios there is no independent verification
of any kind: a client can `POST` a `ticket.close` event with
`success: true, payload: {"verifiedResolved": true}` and no prior
diagnostic actions, then `/complete`, and receive a full pass with full
priority-based points. `backend/tests/test_service_desk_attempts.py`'s own
`close()` helper exercises exactly this call shape as the normal test path.

This is mitigated today only by full raw event capture being visible to
mentor review — that is not independent server verification, and there is no
automated flag surfacing low-evidence completions to a mentor. Treat this as
an open P0 scope gap, not a deliberate, narrowly-scoped residual: either gate
`resolved` on real replayed evidence per scenario (extending the
`_directory_objective_satisfied` pattern, or porting more of
`evaluate-objectives.ts`), or require mentor sign-off before a completion
counts toward progression, until that lands.

## XP — fixed in this phase

The live bridge endpoint (`backend/app/routers/service_desk_bridge.py`,
`POST /api/service-desk/progress`) previously accepted a client-supplied
`xp_delta: int` and inserted it directly into `XPLedger.delta` — any
authenticated student could award themselves arbitrary XP. This phase
replaces that with a fixed, server-defined lookup table keyed by
`event_type` (`ticket_resolved` → 25 XP, `achievement_unlocked` → 10 XP);
`xp_delta` is no longer an accepted request field.

**Fixed 2026-08-07:** the endpoint now dedupes on `(student_id, activity_type,
title)` — a repeated call with the same title (the client sends a
deterministic title per ticket/achievement) is a 204 no-op, not a second XP
award (`record_service_desk_progress`, regression test
`test_progress_events_are_idempotent_per_student_type_and_title`). This is a
minimal patch on the existing `SquadActivity`/`XPLedger` tables, not the
real fix — migrating this bridge's XP awarding onto the
`service_desk_attempts` / `service_desk_attempt_grades` model (which already
has a proper `(attempt_id, idempotency_key)` unique constraint, and doesn't
need a title-string dedup heuristic) is still the right long-term direction
and remains open.

## Summary table

| Claim from Service Desk app | Trusted today? | Where enforced |
|---|---|---|
| "This JWT is a valid Nexus student" | Yes — cryptographic verification | `nexus-auth.ts::verifyStudentSession` |
| "This student is a mentor/admin" | Yes, from the JWT claim or a Nexus round-trip | `nexus-auth.ts::hasNexusAdminAccess` |
| "This action happened, in this order" | Yes, but Nexus — not the client — assigns order and dedups | `service_desk_attempt_events` |
| "Give this student N XP" (old bridge) | Amount: no longer, fixed table by event_type. Repeat calls: deduped by (student, type, title) as of 2026-08-07. | `service_desk_bridge.py` |
| "This attempt's grade arithmetic is X points" | Yes — computed server-side from the published definition and append-only event log | `service_desk_grading.py` |
| "This ticket was actually resolved correctly" (`resolved`/pass-fail) | **No, for 6 of 8 scenarios** — taken directly from client-supplied `success`/`verifiedResolved` on the `ticket.close` event with no independent replay. Only `INC2401`/`INC2405` get real verification (of the score multiplier, not `resolved` itself). | `service_desk_grading.py::compute_grade`, `_directory_objective_satisfied` |
| "Mark this scenario complete" (duplicate submission) | Old bridge: deduped by (student, type, title) as of 2026-08-07 (not a true idempotency key). New attempt model: closed via idempotency key. |
