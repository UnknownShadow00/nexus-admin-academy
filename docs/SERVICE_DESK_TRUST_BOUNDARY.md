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

## Score/pass computation — closed via server-side deterministic grading

The former client-asserted-grade gap is closed. `POST
/api/service-desk/attempts/{id}/complete` now accepts only an idempotency key;
Nexus computes score, pass/fail, hints, priority points, closure penalties,
and the `inc2401`/`inc2405` directory objective from the immutable published
scenario definition and the server-assigned, append-only attempt event log.
The Python implementation ports the deterministic constants and objective
logic from `evaluate-objectives.ts`, including replay of the relevant
successful directory actions. Client-supplied grade fields are no longer
accepted or used.

### Deliberate residual: remote-desktop workflow evidence

For tickets whose intended resolution path uses the Remote Desktop tool's
multi-phase diagnose/fix/verify workflow — the pilot tickets are `INC2406`,
`INC2407`, and `INC2408` — Nexus still relies on the client-reported
`success`/`verifiedResolved` flags on the already-logged `ticket.close` event
to decide whether that workflow was completed correctly. Nexus does not yet
independently replay the Remote Desktop phase-gating or terminal-command
evidence logic; porting that much larger TypeScript engine surface would be
harder to keep synchronized.

This is mitigated for the pilot by full raw event capture (including terminal
commands and phase actions, being wired in a parallel frontend task) being
visible to mentor review. That is not independent server verification. This
is a deliberate, scoped decision, not an oversight.

## XP — fixed in this phase

The live bridge endpoint (`backend/app/routers/service_desk_bridge.py`,
`POST /api/service-desk/progress`) previously accepted a client-supplied
`xp_delta: int` and inserted it directly into `XPLedger.delta` — any
authenticated student could award themselves arbitrary XP. This phase
replaces that with a fixed, server-defined lookup table keyed by
`event_type` (`ticket_resolved` → 25 XP, `achievement_unlocked` → 10 XP);
`xp_delta` is no longer an accepted request field.

**Still open:** this endpoint has no idempotency/dedup — a client can call it
repeatedly for the same ticket and accumulate XP indefinitely. This is
deliberately deferred to Phase 3, which will migrate real completion+XP
awarding onto the new `service_desk_attempts` / `service_desk_attempt_grades`
model (which already has a proper `(attempt_id, idempotency_key)` unique
constraint — the right place for this, not a patch onto the generic
`XPLedger` table, whose `source_id` is an `Integer` and can't hold the
string ticket IDs (`INC2401`) this domain uses).

## Summary table

| Claim from Service Desk app | Trusted today? | Where enforced |
|---|---|---|
| "This JWT is a valid Nexus student" | Yes — cryptographic verification | `nexus-auth.ts::verifyStudentSession` |
| "This student is a mentor/admin" | Yes, from the JWT claim or a Nexus round-trip | `nexus-auth.ts::hasNexusAdminAccess` |
| "This action happened, in this order" | Yes, but Nexus — not the client — assigns order and dedups | `service_desk_attempt_events` |
| "Give this student N XP" (old bridge) | No longer — fixed table by event_type | `service_desk_bridge.py` (this phase) |
| "This attempt's grade is X" (new endpoint) | Yes — Nexus recomputes it from the published definition and append-only event log; the close event's workflow flags remain a deliberate residual trust boundary | `service_desk_grading.py` + `service_desk.py::complete_attempt` |
| "Mark this scenario complete" (duplicate submission) | Not yet deduped on the old bridge | Old bridge: open. New attempt model: closed via idempotency key. |
