# Architecture

## 1. Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js 15+ (App Router), React 19, TypeScript strict** | Public marketing pages (`/`, `/login`, `/testimonials`, `/teachers`, `/blog`) are genuinely path-routed and SEO-relevant per PRODUCT_MAP.md §2 — Next.js serves those natively. The authenticated app shell (`/#...` in the original) becomes a single Next.js route (`/app`) that owns its own client-side sub-router (a thin custom router or React Router in "declarative" mode) so tool switches never trigger a Next.js navigation/remount — this preserves the "shared mounted shell" behavior the simulation state depends on. |
| Styling | **Tailwind CSS v4** | DESIGN_SYSTEM.md confirms the real product's classes map 1:1 onto Tailwind's default scale — no custom design tokens needed beyond `tailwind.config` extensions for the `sd-*` component layer. |
| UI components | **`packages/ui`** — Radix UI primitives (Dialog, Tabs, DropdownMenu, Tooltip) styled with the `sd-*` visual layer from DESIGN_SYSTEM.md | Radix gives accessible, unstyled behavior (focus trap, keyboard nav) for free under Modal/Tabs/Tooltip — matches the a11y gaps REPORT.md flagged in the original ("sparse accessible labels"); we should do better, not replicate that gap. |
| Icons | `@tabler/icons-react` | Exact visual match confirmed in DESIGN_SYSTEM.md §5; MIT-licensed, safe to depend on directly. |
| API layer | **`apps/api`** — Node.js + TypeScript, **tRPC** for internal web↔api calls, plain REST for anything that needs to be called from outside the web app (webhooks, future integrations) | tRPC gives end-to-end type safety between `apps/web` and `apps/api` without hand-written OpenAPI/schemas for the bulk of the surface, while REST stays available for Stripe/webhook-style external callers. |
| Database | **PostgreSQL 16**, accessed via **Prisma** (`packages/database`) | Relational integrity matters here (per-attempt world state referencing global templates, append-only events referencing attempts) — Postgres + Prisma is the standard, well-supported choice and keeps migrations reviewable. |
| Realtime | **Postgres LISTEN/NOTIFY** or a lightweight WebSocket layer (e.g. `ws` behind `apps/api`), **not** Firebase/Firestore | The original uses Firestore's realtime channel (confirmed in evidence) purely as a sync transport for one user's own state (ticket queue, points, quotas) — we don't need a third-party realtime DB; Postgres + a thin pub/sub is sufficient and keeps all grading-relevant data server-authoritative in one system. |
| Auth | **Auth.js (NextAuth) v5** with a credentials provider backed by our own `Account` table (bcrypt/argon2 password hashing) + optional Google OAuth provider | Matches the original's email/password + Google login (PRODUCT_MAP.md §2.2) without taking a hard dependency on Firebase Auth. Session tokens are JWT or database-backed sessions — use database sessions so a teacher/admin can force-revoke a student session (needed for classroom management). |
| Payments | **Stripe Checkout + Billing Portal + webhooks** | Matches the original's plan/paywall UX (PRODUCT_MAP.md §21) exactly — Free/Pro tiers, monthly/annual, self-serve cancel via Billing Portal. Implement this in a later phase (§ IMPLEMENTATION_PLAN.md Phase 13) — not required for the core simulation to be usable. |
| Background jobs | **A simple Postgres-backed queue (e.g. `pg-boss`) or a cron-triggered API route** | Needed for: daily quota resets (midnight reset timer observed throughout captures), leaderboard rollups, achievement evaluation. Low volume — no need for Redis/Kafka. |
| Testing | **Vitest** (unit, `packages/simulation-engine` and `packages/database` logic), **Playwright** (`tests/`, e2e across `apps/web`) | Playwright is already the toolchain used for the evidence capture itself (`../playwright/*.mjs`) — reuse the same mental model and, where useful, adapt `../playwright/complete-ticket.mjs`'s recorded sequence directly into a `tests/deployment-flow.spec.ts`. |
| Deployment | **Docker Compose** for local/dev (`docker/`: `web`, `api`, `postgres`, optional `mailhog` for dev email); a single Postgres-backed container image per app for prod, deployable to any container host | Keeps the whole stack runnable with `docker compose up` for contributors and for CI, without coupling the plan to a specific cloud vendor. |

## 2. Monorepo & package boundaries

Managed with **pnpm workspaces + Turborepo** (fast, incremental builds/tests across `apps/*` and `packages/*`, minimal config surface):

```
apps/web                → imports packages/ui, packages/shared, calls apps/api via tRPC client
apps/api                → imports packages/database, packages/simulation-engine, packages/shared
packages/ui             → imports packages/shared only (no API/DB imports — must be usable in Storybook/tests in isolation)
packages/database        → Prisma schema + generated client + seed scripts; no framework imports
packages/simulation-engine → imports packages/database (via a repository interface, not raw Prisma calls scattered around) + packages/shared; pure, testable domain logic
packages/shared          → zod schemas, shared TS types/enums, constants (priority levels, quota defaults, tier thresholds) — importable by everything, imports nothing app-specific
```

**Rule enforced by this boundary**: all correctness/grading logic lives in `packages/simulation-engine`, called only from `apps/api`. `apps/web` never contains business logic that decides whether an action is valid or how many points it's worth — it only renders state and calls API mutations. This directly implements the task brief's requirement: *"Keep all correctness decisions server-side. The browser should receive only safe state projections; never ship hidden solution predicates or scoring keys."*

## 3. Simulation foundation (the core architectural problem)

This is the part that makes every tool feel like one product instead of eight unrelated pages. Design:

### 3.1 Environment templates vs. student attempt environments

- A **`Scenario`** (see DATABASE.md) defines a ticket plus the **world-state delta** it requires: which directory users/devices/servers must exist, in what starting state, and what the hidden objective/solution predicate is.
- An **`EnvironmentTemplate`** is the shared "org" baseline: the 83-person directory roster, the 8 network devices + 5 servers, the 38 KB articles, default license/asset inventory — all of it **global, versioned, immutable once published** (edits go through a new version, never an in-place mutation of a template already in use).
- When a student starts an attempt (opens their first ticket of a session, or a teacher assigns a scenario), the system creates an **`Attempt`** that **copies a snapshot reference** of the template (not a deep row-by-row copy of 83 users into a new table — see DATABASE.md's global-vs-per-attempt split) plus an **attempt-scoped overlay** table for anything the student can mutate (directory changes, PC Shelf contents, shipments, chat messages, deployment runs). Reads merge template + overlay; writes only ever touch the overlay. This is the standard "copy-on-write" pattern and avoids duplicating 83 rows × N students × M attempts.

### 3.2 Shared state, cross-tool example (worked through, per the task brief)

> A student unlocks a user in Directory → the Directory state changes → the ticket detects the action → the event log records it → the change survives refresh → other connected tools show the updated state.

Concretely:
1. Student clicks "Unlock account" on a `DirectoryUser` row inside the Directory tool.
2. `apps/web` calls a tRPC mutation `directory.unlockUser({ attemptId, directoryUserId })`.
3. `apps/api` calls `simulation-engine`'s `applyAction()`, which: (a) validates the action is permitted for this attempt/scenario (§3.4), (b) writes a new row to the attempt's `WorldStateOverlay` (or a dedicated `DirectoryUserState` overlay table) marking that user unlocked, (c) appends an immutable `Event` row (`type: "directory.user_unlocked"`, `attemptId`, `actorId`, `payload`, `createdAt`), (d) re-evaluates the active ticket's `ScenarioObjective`s against the new world state and, if satisfied, appends a `ticket.objective_completed` event and updates `Grade`.
4. The mutation returns the new projected state; `apps/web` updates its local cache (React Query / tRPC's built-in cache).
5. Because the write is server-side and durable (Postgres row, not browser storage), a refresh re-fetches the same overlay — state survives refresh, unlike the original's PC Shelf, which REPORT.md documents as session-scoped (a limitation we deliberately do not copy — see PRODUCT_MAP.md §10).
6. Any other tool reading that same `attemptId`'s world state (Remote Desktop's login-availability check, Asset Management's "Sync from AD" pull) reads the same overlay — one source of truth, not per-tool caches that can drift.
7. Live cross-tab/cross-tool UI updates use the realtime layer (§1) to push an invalidation event so an open Asset Management tab reflects a Directory change without a manual refresh, mirroring the original's Firestore-listener-driven live updates.

### 3.3 Append-only events

`Event` is **insert-only** — no updates, no deletes, ever, from application code (a DBA-level retention/purge job is a separate, explicitly audited operation, out of scope for `apps/api`). Every state-changing action in every tool writes exactly one `Event`. This gives:
- **Replay**: reconstruct an attempt's full world state at any point in time by folding events in order (useful for grading disputes, debugging, and building an instructor "watch a student's session" view later).
- **Audit**: "every click, message, tool mutation, hint, invalid action, and score change" (task brief) is captured, including *rejected* actions (log them with `success: false` and a `reason`, don't just silently ignore them) — this is what makes deterministic grading and anti-cheat/anomaly review possible.
- **Grading**: `Grade` rows are always derived from `Event` + `ScenarioObjective`, never hand-set — this satisfies "deterministic grading."

### 3.4 Action permissions

Every mutation in `simulation-engine` goes through one `applyAction(attemptId, actorId, actionType, payload)` entry point that:
1. Loads the `Attempt`, confirms `actorId` owns it (or is a teacher/admin with an explicit override permission — logged as such).
2. Confirms the attempt is `active` (not `submitted`/`expired`/`reset`).
3. Confirms the action type is one the current `Scenario`'s tool-availability rules allow (e.g. Company Chat actions are always available; Deployment step actions are only valid in the current step's expected order — out-of-order attempts are rejected with a typed error, not silently accepted, matching the original's own "wrong action → inline correction" pattern documented throughout PRODUCT_MAP.md §9).
4. Confirms any quota isn't exhausted (daily ticket/call limits — same soft-paywall UX as PRODUCT_MAP.md §21, enforced server-side, not just hidden in the UI).
5. Only then mutates the overlay and appends the `Event`.

This single choke point is what makes "isolated student environments" and "role-based access" tractable — RBAC (`student` / `teacher` / `admin`) is checked once, here, not scattered per-tool.

### 3.5 Reset behavior

An `Attempt` can be reset (student-initiated "start over" or teacher-initiated for a re-do): this **does not delete** the `Attempt` or its `Event` history — it marks the attempt `reset` and creates a **new** `Attempt` row against the same `Scenario`/template version, with a fresh empty overlay. Old attempts remain queryable for grading history and analytics. This matches the append-only philosophy end-to-end: nothing is ever destroyed, only superseded.

### 3.6 Scenario objectives & deterministic grading

`ScenarioObjective` rows (see DATABASE.md) define, per scenario: a machine-checkable predicate against world-state + event history (e.g. "a `DirectoryUser` matching `requesterId` has `unlocked: true`" or "a `Shipment` exists with `recipientId = requesterId` and `containsDeviceId IN provisionedDevicesThisAttempt`"), a point value, and whether it's required vs. bonus. Grading is a pure function `evaluateObjectives(scenario, attemptWorldState, eventLog) → Grade` — same inputs always produce the same output, runnable server-side on demand or on every relevant event (§3.2 step 3). No solution predicate is ever serialized to the client; `apps/web` only ever receives `{completed: boolean, pointsAwarded, hintsAvailable}`-shaped projections.

### 3.7 Hints

Hints (the ticket workspace's progressive "REVEAL NEXT STEP (n/7)" mechanic, PRODUCT_MAP.md §4) are `ScenarioHint` rows, ordered, each optionally carrying a point penalty. Revealing a hint is itself an `applyAction` call (`ticket.reveal_hint`) so it's logged and can factor into `Grade` — never a client-only reveal.

## 4. Isolated student environments

"Isolated" here means **data isolation, not infrastructure isolation** — every student's `Attempt` and its `WorldStateOverlay`/`Event` rows are scoped by `attemptId` (itself scoped to `studentId` + `classroomId`/`organizationId`), enforced by row-level checks in `simulation-engine` (§3.4) and, as defense-in-depth, Postgres Row-Level Security policies keyed on the authenticated session's org/classroom claims. No separate container/sandbox per student is needed — this is a simulated environment (fake directory, fake servers), not a real one, so logical isolation in one database is sufficient and far cheaper to operate than infra-level isolation.

## 5. Testing strategy

- **Unit** (Vitest, `packages/simulation-engine`): every action type has a test for its happy path, its rejected/invalid-order path (mirroring PRODUCT_MAP.md §9's documented wrong-action states), and its quota-exhausted path. Grading predicates are tested against hand-built event-log fixtures.
- **Integration** (Vitest + a real test Postgres via `docker/docker-compose.test.yml`): `apps/api` tRPC routers, exercised end-to-end against the DB, including RLS policy checks.
- **E2E** (Playwright, `tests/`): one spec per major page from PRODUCT_MAP.md, plus a full **deployment-flow spec adapted directly from `../playwright/complete-ticket.mjs`** (open ticket → chat → deployment 11 steps incl. wrong-path assertions → PC Shelf → Ship Manager → close ticket with penalty check) — this is the single highest-value e2e test since it exercises the shared-state model across 5+ tools in one run. Include a mobile-viewport pass (375×812, matching the original capture) for Dashboard, Ticket Workspace, and Ship Manager at minimum.
- **Accessibility**: `@axe-core/playwright` assertions on every page-level e2e test — deliberately holding a higher bar than the original, which REPORT.md flags as having "sparse accessible labels" in places.

## 6. Security & evidence handling

- **Never commit** (see also `service-desk-app/README.md` and the audit that produced this list):
  - `../website-capture/crawlee-servicedesk/.auth/` (Playwright storage state + copied browser profile — real session tokens)
  - `../website-capture/crawlee-servicedesk/storage/` (Crawlee runtime state)
  - `../website-capture/browsertrix/crawls/profiles/` and `../website-capture/browsertrix/crawls/**/profile/` (exported/unpacked Chromium profiles — **currently not covered by any existing `.gitignore`**, must be added before this project's `.git` history touches those paths)
  - `../artifacts/network/session.sanitized.har` and `../artifacts/api/*firestore*-channel.json` (mislabeled "sanitized" — audit found ~118 live-at-capture-time bearer tokens and a real tester email still embedded in urlencoded Firestore channel bodies; the top-level JSON-field redaction missed values nested inside form-encoded strings)
  - Any `.env`/credentials file for the real disposable test account
- **Action required before first commit touching this history**: extend the root `.gitignore` (`Nexus dupe/.gitignore`) to add `website-capture/browsertrix/crawls/profiles/` and `website-capture/browsertrix/crawls/**/profile/`, and either re-sanitize or gitignore the two flagged files above. This is infrastructure/evidence hygiene, not `service-desk-app` code — track it as a standalone task, not folded into a Codex phase (Codex phases must not touch `website-capture/` or `artifacts/` per the task's folder rule).
- Our own app's secrets (DB URL, Auth.js secret, Stripe keys) live in `.env.local` (gitignored) with `.env.example` committed as documentation, standard Next.js convention.
- Firebase's public web API key visible throughout the evidence (`AIzaSyAZRLdM-sgw9szWLPRgiL6z3CDd5_Ar-Pg`) is a low-severity, by-design-public client identifier — noted for completeness, not actionable.

## 7. Deployment

- `docker/Dockerfile.web`, `docker/Dockerfile.api`, `docker/docker-compose.yml` (postgres + web + api for local dev), `docker/docker-compose.prod.yml` (production-shaped, no dev-only services).
- Migrations run via `prisma migrate deploy` as a release-time step (CI or a deploy hook), never `db push` in production.
- CI (GitHub Actions or equivalent, added in Phase 12): lint → typecheck → unit → integration (against a service-container Postgres) → Playwright e2e → build, on every PR; deploy on merge to `main` after all pass.
