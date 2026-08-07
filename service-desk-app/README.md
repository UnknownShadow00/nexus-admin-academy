# service-desk-app

An original, client-side IT service-desk training simulator built with Next.js,
TypeScript, pnpm workspaces, and Turbo. The implemented application persists its
simulation state entirely in browser `localStorage`; it has no application
backend, database, authentication service, or external platform integration.

Phases 1–11 provide:

- the responsive service-desk shell, ticket queue, ticket workspace, and
  deterministic simulation engine;
- Directory, Documentation, Company Chat, Asset Management, and PC Shelf tools;
- Server Room, Remote Desktop, Computer Deployment, and Shipping Manager tools;
- analytics, achievements, rank progression, leaderboard, and past tickets; and
- a browser-local scenario builder, scenario preview, and isolated test-student
  slots under `/admin`.

The project is now hardened for deployment. Backend-related files remain
explicitly deferred scaffolding for a possible future migration.

## Local development

Requirements: Node.js 22+ and pnpm 10.15.1 (Corepack can activate the pinned
version).

```sh
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). The admin scenario tools
are at [http://localhost:3000/admin](http://localhost:3000/admin).

## Verification

Run the complete production gate from this directory:

```sh
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

## Docker

The production image installs the frozen pnpm workspace, builds the web app and
its internal package dependencies, then runs Next.js on port 3000.

```sh
cp .env.example .env
docker compose -f docker/docker-compose.yml up web
```

The application liveness endpoint is
[`GET /api/health`](http://localhost:3000/api/health). It returns HTTP 200 with
`{"status":"ok","timestamp":"<ISO timestamp>"}` and has no external
dependencies.

The Compose file also retains a Postgres service as future scaffolding. The
`web` service neither starts nor connects to it.

## Environment

The current `apps/web` application reads zero environment variables and needs
none at runtime. All state is local to each browser.

`.env.example` retains `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`
only because the deferred Postgres Compose service references them. They are not
read by the current application. Copying the example to ignored `.env` lets
Docker Compose interpolate that reserved service definition even when starting
only `web`.

## Browser backup

The `/admin` dashboard can export a versioned JSON backup containing the main
student attempt, authored scenarios, test-student slots, and their attempts. An
import is validated before it replaces those local browser stores. The feature
is entirely client-side; no backup is uploaded to a server.

## Docs

- [`docs/PRODUCT_MAP.md`](docs/PRODUCT_MAP.md) — page/tool routes, layouts,
  components, and states.
- [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) — colors, type, spacing,
  components, and breakpoints.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the original architecture
  brief, including deferred backend plans.
- [`docs/DATABASE.md`](docs/DATABASE.md) — future-state data-model planning, not
  a current database implementation.
- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) — phased build
  plan.
- [`docs/CODEX_PROMPTS.md`](docs/CODEX_PROMPTS.md) — phase implementation
  prompts.

## Folder structure

```
service-desk-app/
├── apps/
│   ├── web/                 # Implemented Next.js app, admin, and health route
│   └── api/                 # Intentionally deferred TypeScript placeholder
├── packages/
│   ├── ui/                  # Shared design-system components
│   ├── database/            # Documentation-only future placeholder; no Prisma
│   ├── simulation-engine/   # Deterministic world-state and attempt serializer
│   └── shared/              # Fixtures, types, browser stores, and backups
├── tests/                   # Test guidance
├── docker/                  # Production web image + deferred Postgres Compose service
├── docs/                    # Product and architecture documentation
└── tasks/                   # Required implementation completion log
```

## Rules for anyone (human or Codex) working in this folder

1. Work only inside `service-desk-app/`. Never modify `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/` — those are read-only research evidence.
2. Never commit anything from `../website-capture/crawlee-servicedesk/.auth/`, `../website-capture/crawlee-servicedesk/storage/`, `../website-capture/browsertrix/crawls/profiles/`, `../website-capture/browsertrix/crawls/**/profile/`, or `../artifacts/network/session.sanitized.har` — see `docs/ARCHITECTURE.md` § Security/Evidence Handling.
3. Recreate behavior and structure, not proprietary copy, branding, or assets. Invent original ticket content, employee names, articles, and wording — the captured evidence is a structural/behavioral reference only.
