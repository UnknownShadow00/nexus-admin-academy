# Codex Prompts

One copy-paste prompt per phase from `IMPLEMENTATION_PLAN.md`. Run them in order — each assumes the previous phases are merged. Every prompt follows the global Codex defaults (`gpt-5.6-sol`, effort `medium`/`high` for architecture-heavy phases, sandbox `workspace-write`, `--full-auto --skip-git-repo-check 2>/dev/null`) and the project's standing rule: **Claude reviews every Codex output against the phase's completion checklist before it's considered done — run `/review` after Codex finishes, before moving to the next phase.**

Every prompt already embeds the required guardrails (scope lock, evidence-only grounding, no touching capture folders, lint/typecheck/test/build, Playwright validation, changed-files summary). Do not strip these out when copying.

---

## Phase 1 — Project setup and design system

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not read, write, or modify anything outside that folder — specifically never touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`. Those are read-only research evidence for an authorized recreation project.

Read first, in full:
- service-desk-app/docs/ARCHITECTURE.md (§1 Stack, §2 Monorepo boundaries)
- service-desk-app/docs/DESIGN_SYSTEM.md (all sections)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 1 — Project setup and design system"

Task: implement Phase 1 only, exactly as scoped in IMPLEMENTATION_PLAN.md. Set up the pnpm + Turborepo monorepo skeleton (apps/web, apps/api placeholder, packages/ui, packages/shared, docker/docker-compose.yml with postgres only), and build the packages/ui component library per DESIGN_SYSTEM.md §5: Button (primary/light/soft/default variants), IconButton, Card/CardHeader, Modal, PanelFrame (4 variants: default/--ad/--assets/--contained/--fab-clearance), Input, Tabs, Badge/PriorityBadge (Critical/High/Medium/Low), Tooltip. Use Tailwind CSS v4 with the zinc/sky/red/orange/amber palette from DESIGN_SYSTEM.md §1 — do not invent custom hex tokens. Add a `/design-system` debug route in apps/web that renders every component and its variants for visual review.

You may spot-check these screenshots for color/spacing sanity, but do not copy any text/branding from them: ../artifacts/screenshots/desktop/authenticated-queue.png, ../artifacts/screenshots/desktop/tool-directory.png.

Do not build any real product page, do not create packages/database or packages/simulation-engine, do not add authentication. Do not modify any file outside service-desk-app/.

Before finishing: run and show output for `pnpm install`, `pnpm build`, `pnpm lint`, `pnpm typecheck`, and the Vitest unit suite for packages/ui (all green). Then start the dev server and use Playwright (or your available browser tool) to open `/design-system` and confirm every component variant renders without console errors, at both 1440x1000 and 375x812 viewports.

Finish with a summary listing every file created or changed, grouped by package. Do not report success if lint, typecheck, tests, or the build are not all clean.
```

---

## Phase 2 — Main shell and navigation

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §0 (navigation model), §1 (global chrome), §2 (public pages), §3 (dashboard layout)
- service-desk-app/docs/DESIGN_SYSTEM.md §7 (responsive breakpoints), §8 (reference screenshots)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 2 — Main shell and navigation"

Also open and closely compare against these evidence files before writing any layout code:
- ../artifacts/screenshots/desktop/authenticated-queue.png and ../artifacts/html/authenticated-queue.html
- ../artifacts/screenshots/desktop/tools-menu.png and ../artifacts/html/tools-menu.html
- ../artifacts/screenshots/desktop/public-home.png, login-empty.png
- ../artifacts/screenshots/mobile/mobile-authenticated-queue.png and ../artifacts/metadata/mobile-overflow.json

Task: implement Phase 2 only. Build the authenticated app shell (header with all button clusters from PRODUCT_MAP.md §1, footer, dark-theme pre-paint script per DESIGN_SYSTEM.md §6), the Tools panel modal (3 category groups — INFRASTRUCTURE/KNOWLEDGE/MANAGEMENT — with the exact 8 tools and icons listed in PRODUCT_MAP.md §0, opens via TOOLS button, closes via click-outside/Esc/close button, focus-trapped), the Dashboard page shell with static mock ticket data (no database yet — hardcode 1-2 original mock tickets), a client-side sub-router stub so tool routes resolve without a full page reload, and the public logged-out `/` and `/login` pages (form only, no real submission logic yet). All copy must be original — do not reuse any real names, ticket text, or branding from the evidence.

Use only components from packages/ui built in Phase 1. Do not add packages/database, packages/simulation-engine, or any authentication logic. Do not implement any tool's actual functionality — placeholders/mock data only.

Before finishing: run lint, typecheck, and the full test suite (all green). Build apps/web for production and confirm it succeeds. Use Playwright to load the shell at 1440x1000 and 375x812, confirm zero horizontal overflow (clientWidth === scrollWidth, matching ../artifacts/metadata/mobile-overflow.json), open and close the Tools panel, tab through it with keyboard only, and run an axe accessibility scan with zero critical violations.

Finish with a summary of every file changed and a short note on any visual deviation from the reference screenshots and why. Do not modify any file outside service-desk-app/.
```

---

## Phase 3 — Dashboard and ticket workspace

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §3, §4
- service-desk-app/docs/DATABASE.md §1 (identity/org), §2 (environment templates), §3 (scenarios) — implement exactly this schema, do not redesign it
- service-desk-app/docs/ARCHITECTURE.md §1 (auth choice: Auth.js v5, credentials + Google)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 3 — Dashboard and ticket workspace"

Also review: ../artifacts/metadata/complete-ticket-workflow.json (exact ticket-detail field shape and close-review copy pattern — for structure only, write original copy) and ../artifacts/screenshots/desktop/ticket-assigned-baseline.png through ticket-close-review.png.

Task: implement Phase 3 only. Create packages/database with a Prisma schema for DATABASE.md §1-3 (Account/Student/Teacher/Admin/Organization/Classroom/Enrollment/Assignment, EnvironmentTemplate and its children, Scenario/ScenarioVersion/ScenarioObjective/ScenarioHint) — no Attempt/overlay tables yet, those are Phase 4. Wire Auth.js (credentials provider with bcrypt or argon2 password hashing, plus Google OAuth) against the Account model. Write a seed script creating one original environment template (an original org roster/servers, not copied names) and 2-3 original scenarios. Build the real Dashboard (queue from DB) and the Ticket Workspace page per PRODUCT_MAP.md §4: header actions (Back to Queue, Split Screen View, Options, Unassign), full ticket-detail fields, the progressive hint-reveal mechanic (client-visible only, no scoring effect yet — that's Phase 4), and the Close Ticket flow UI including the unresolved-close warning modal (UI/copy only, real point penalty computation comes in Phase 4).

Do not implement any of the 8 tools yet. Do not implement real grading/points math (stub it or leave it visually present but non-functional, Phase 4 wires the real engine). Do not implement chat.

Before finishing: run lint, typecheck, unit tests (including Prisma seed integrity checks), and the full test suite. Run `prisma migrate dev` against a local/test Postgres and confirm it applies cleanly. Build apps/web for production. Use Playwright to: register a new account, log in, view the seeded queue, open a ticket, reveal all hints in order, and close it via both the resolved and unresolved paths, confirming the warning modal appears before an unresolved close.

Finish with a summary of every file changed, the exact seed data created (scenario titles, roster size), and confirmation all ticket/employee copy is original. Do not modify any file outside service-desk-app/.
```

---

## Phase 4 — Shared simulation engine

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full and carefully — this phase is the architectural core of the whole project:
- service-desk-app/docs/ARCHITECTURE.md §3 (Simulation foundation) in full
- service-desk-app/docs/DATABASE.md §4 (Attempts & world-state overlay), §5 (Events, grading, progress)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 4 — Shared simulation engine"

Task: implement Phase 4 only. Create packages/simulation-engine with a single `applyAction(attemptId, actorId, actionType, payload)` entry point implementing exactly the 5-step validation sequence in ARCHITECTURE.md §3.4 (ownership check, attempt-active check, action-permitted-for-current-state check, quota check, then mutate+log), an `evaluateObjectives()` pure function per §3.6, and event logging that is strictly insert-only (no update/delete call sites against the Event model anywhere in apps/api — this will be checked in review). Migrate DATABASE.md §4-5's tables: Attempt, DirectoryUserOverlay, DeploymentRun, ProvisionedDevice, Shipment, ChatThread, ChatMessage, Event, Grade, Progress. Wire this engine under the Phase 3 ticket-close flow as the first real consumer: closing a ticket now calls applyAction + evaluateObjectives and produces a real, server-computed Grade with a real points delta (structurally like the captured -17-point unresolved-close example, but using your own original scenario's point values, not the captured numbers). Implement attempt reset per §3.5: never deletes old Attempt/Event rows, always creates a new Attempt.

Do not build Directory, Deployment, or any other tool's UI yet — prove the engine through the one flow already wired in Phase 3, not by adding new tool surfaces.

Before finishing: run lint, typecheck, and the full test suite — this phase should have the heaviest unit-test coverage so far (Vitest): valid action happy path, out-of-order/invalid action rejected and logged with success:false, quota-exhausted rejection, objective evaluation against hand-built event-log fixtures, and a reset test proving old Event/Grade rows survive. Build apps/web and apps/api for production. Use Playwright to close a ticket both ways and confirm the UI shows a real computed points delta, then reset the attempt and confirm a fresh Attempt exists while the old one's history is still queryable (assert via a test-only debug query or admin view, not by exposing this in the student UI).

Finish with a summary of every file changed, and explicitly confirm (with a grep or equivalent) that no Event row is ever updated or deleted from application code. Do not modify any file outside service-desk-app/.
```

---

## Phase 5 — Directory

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §6 (Directory)
- service-desk-app/docs/ARCHITECTURE.md §3.1 (copy-on-write read rule) and §3.2 (worked cross-tool example — this IS the Directory unlock example)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 5 — Directory"

Also compare against: ../artifacts/screenshots/desktop/tool-directory.png, ../artifacts/html/tool-directory.html, ../artifacts/metadata/tool-directory.json (structure/copy pattern only — write original names).

Task: implement Phase 5 only. Build the Directory tool page (client sub-router route matching the original's `#ad` hash equivalent) with an original user roster list (name/username), a user detail panel, a "New User" action, and unlock/reset-password/group-change actions — all routed through Phase 4's `applyAction()`, all reading via the template+overlay merge pattern from ARCHITECTURE.md §3.1 (template rows LEFT JOIN this attempt's DirectoryUserOverlay rows, overlay wins). Implement the API endpoints as tRPC procedures: directory.list, directory.unlockUser, directory.resetPassword, directory.updateGroups.

Do not build Remote Desktop or Asset Management yet — this phase proves the shared-state pattern with Directory alone.

Before finishing: run lint, typecheck, and the full test suite, including a Vitest test for the template+overlay merge logic specifically. Build apps/web and apps/api for production. Use Playwright to: open Directory, unlock a locked user, reload the page, and confirm the unlock is still shown (real persistence, not client state) — this is the task's explicit "survives refresh" requirement and must be demonstrated, not assumed.

Finish with a summary of every file changed. Confirm the Directory panel's visual structure (panel-frame variant, back button, learn-link placement) matches ../artifacts/screenshots/desktop/tool-directory.png's layout, with original copy. Do not modify any file outside service-desk-app/.
```

---

## Phase 6 — Documentation and chat

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §11 (Documentation) and §14 (Company Chat)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 6 — Documentation and chat"

Also compare against: ../artifacts/screenshots/desktop/tool-documentation.png, company-chat-empty.png, ticket-chat-diagnosis-and-address.png, ticket-chat-delivery-confirmation.png, and ../artifacts/metadata/complete-ticket-workflow.json (for the scripted-reply pattern shape only — write entirely original dialogue).

Task: implement Phase 6 only. Build the Documentation tool page with 10 original categories (matching the captured category/count structure: e.g. one category with 1 doc, several with 3-5) and original article content per DATABASE.md §2's KnowledgeBaseArticle model — category list view, article detail view. Build the Company Chat panel (header-triggered overlay, not a route) with Recent/Contacts/Pinned tabs, a searchable contact list backed by the same roster as Directory, a conversation view, quick-reply chips, and a message input hard-capped at 500 characters (enforce both client- and server-side). Implement scripted branching dialogue: when a student sends a message matching a scenario-defined trigger, a canned NPC reply is looked up and inserted — this is NOT a live LLM integration, do not wire any AI/chat-completion API for this. Implement at least one full scripted script (diagnosis question + delivery confirmation, mirroring the captured 2-beat structure with original content) tied to one of the seeded scenarios from Phase 3.

Do not build any tool beyond Documentation and Chat this phase.

Before finishing: run lint, typecheck, and the full test suite, including a Vitest test for the trigger-key-to-scripted-reply resolver. Build for production. Use Playwright to open chat from within a ticket, send a message matching the seeded trigger, confirm the scripted NPC reply appears and an Event was logged, and confirm the 500-character input cap is enforced in the UI.

Finish with a summary of every file changed and the exact category/article/script content created (titles only, to confirm originality, not full text). Do not modify any file outside service-desk-app/.
```

---

## Phase 7 — Asset and PC tools

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §8 (Remote Desktop), §10 (PC Shelf), §12 (Asset Management)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 7 — Asset and PC tools"

Also compare against: ../artifacts/screenshots/desktop/tool-remote-desktop.png, tool-asset-management.png, tool-pc-shelf.png (structure only, original copy).

Task: implement Phase 7 only. Build Remote Desktop (workstation list keyed by asset tag + employee, Connect action opening a minimal stub session view), Asset Management (By Users / By Assets toggle, "Sync from AD" action that pulls current Directory overlay state into this view, search, the ASSET TAG/NAME/DEPARTMENT/STATUS table), and PC Shelf (empty state with original copy, populated state listing provisioned devices with a Ship shortcut). Implement as tRPC procedures: remoteDesktop.list, remoteDesktop.connect, assets.list, assets.syncFromAd, pcShelf.list. Use the same asset-tag key consistently across Directory (Phase 5), Remote Desktop, and Asset Management — one shared identifier, per DATABASE.md.

PC Shelf must persist server-side across refresh — do not replicate the original product's session-only PC Shelf limitation; this is a deliberate improvement documented in ARCHITECTURE.md §3.5, not a bug to introduce. Do not build the Computer Deployment tool that populates PC Shelf yet — seed PC Shelf with fixture ProvisionedDevice rows for this phase's own tests if you need populated-state coverage.

Before finishing: run lint, typecheck, and the full test suite. Build for production. Use Playwright to: unlock a user in Directory, then check Remote Desktop reflects the change without a full page reload; run "Sync from AD" in Asset Management after a Directory change and confirm it reflects; reload PC Shelf and confirm fixture data persists.

Finish with a summary of every file changed. Do not modify any file outside service-desk-app/.
```

---

## Phase 8 — Server Room and Remote Desktop depth, Computer Deployment

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full — §9 is the most detailed section in the whole product map, treat it as the literal spec:
- service-desk-app/docs/PRODUCT_MAP.md §7 (Server Room) and §9 (Computer Deployment) in full
- service-desk-app/docs/DATABASE.md's DeploymentStepTemplate and DeploymentRun models
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 8 — Server Room and Remote Desktop depth, Computer Deployment"

Also open and study closely: ../artifacts/screenshots/desktop/tool-server-room.png, tool-computer-deployment.png, and all 10 deployment-*.png files; and ../playwright/complete-ticket.mjs — use this script as the literal interaction/selector sequence to translate into both your UI step components and your e2e test (structure and sequencing only — write original strings/copy, do not copy the file's literal text into product copy, though it is fine to mirror it in comments for traceability).

Task: implement Phase 8 only. Build Server Room (Overview/Topology/Devices/Servers tabs, 8 network devices + 5 servers with live status/CPU/memory, matching PRODUCT_MAP.md §7's exact dataset shape with original names). Build the Computer Deployment hub (3 method cards: Server Imaging enabled with a Start button, Manual Domain Enrollment and Cloud Provisioning both shown as "under development" — do not implement those two beyond that card state) and the full 11-step Server Imaging flow as a real server-validated state machine: device-type selection, cable matching (5 cables to 5 ports, wrong-port rejection with inline correction copy), POST/F12 timing interaction (ignore input ~900ms, accept within a ~3.5s window), boot-source selection (reject local-disk and IPv6 boot with specific inline correction text, accept IPv4 PXE), deployment-share password auth (reject wrong password), hostname/computer-name entry (validate an original naming-convention pattern equivalent to the captured SD#### scheme, reject duplicates via a DB unique constraint), automated task-sequence progress display, reboot, domain login (reject wrong credentials), and a Deployment Successful screen with "Ship from Ship Manager" / "Go to PC Shelf" CTAs that creates a real ProvisionedDevice landing on PC Shelf.

Seed 11 DeploymentStepTemplate rows for one Server Imaging scenario with original wrong-path copy that structurally matches the captured pattern (specific, helpful inline corrections) without copying the captured text verbatim.

Before finishing: run lint, typecheck, and the full test suite. Build for production. This phase's Playwright spec is the most important in the whole plan — adapt ../playwright/complete-ticket.mjs's sequence directly: attempt every documented wrong path (wrong cable/port, missed F12 timing, local-disk boot, IPv6 boot, wrong share password, invalid/duplicate hostname, wrong domain login) and assert the correct rejection/correction UI appears for each, then complete the correct path end-to-end and assert a ProvisionedDevice lands on PC Shelf.

Finish with a summary of every file changed. Confirm in the summary that all 11 steps are validated server-side (deployment.submitStepAction), not client-side-only. Do not modify any file outside service-desk-app/.
```

---

## Phase 9 — Deployment and shipping

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §13 (Ship Manager)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 9 — Deployment and shipping"

Also compare against: ../artifacts/screenshots/desktop/tool-ship-manager.png, shipping-form-complete.png, shipping-required-field-validation.png, replacement-shipped.png.

Task: implement Phase 9 only. Build the Ship Manager tool: recipient-name searchable dropdown (same roster as Directory), address fields (auto-filled from recipient, editable), sender department dropdown, equipment-to-ship list with quantities, a provisioned-PC selector that appears only when "Computer" is selected (sourced from the current attempt's PC Shelf), shipping speed (Standard/Express/Priority/Rush — Rush ships instantly, no simulated delay needed), an "include return label" checkbox, empty-form validation showing an inline (not toast-only) address-required message, and a post-ship success state with a "Refill Last Address" convenience button. Implement shipManager.createShipment (must consume/remove the selected ProvisionedDevice from PC Shelf, and must run through Phase 4's applyAction so it can complete a ScenarioObjective) and shipManager.getLastAddress.

Do not implement any real Stripe/payment/carrier integration — shipping speed and delivery are entirely simulated.

Before finishing: run lint, typecheck, and the full test suite. Build for production. Use Playwright to: take a provisioned device from Phase 8's PC Shelf, ship it to the seeded scenario's requester, and confirm (a) it no longer appears on PC Shelf, and (b) the associated ticket's ScenarioObjective (e.g. "device shipped to requester") completes and awards points via a real Grade update.

Finish with a summary of every file changed. Do not modify any file outside service-desk-app/.
```

---

## Phase 10 — Analytics and progress

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §15 (Analytics), §16 (Achievements), §17 (Leaderboard), §18 (Friends), §19 (Profile menu + Settings)
- service-desk-app/docs/DATABASE.md §5 (Achievement, StudentAchievement, CareerTier, Progress)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 10 — Analytics and progress"

Also compare against: ../artifacts/screenshots/desktop/profile-analytics.png, profile-achievements.png, leaderboard.png, profile-friends.png, profile-menu.png, profile-settings.png, profile-past-tickets.png.

Task: implement Phase 10 only. Migrate and seed Achievement (17 achievements matching PRODUCT_MAP.md §16's exact thresholds: First Ticket, Speed Demon <60s, First Call, Getting Started 10 tickets, Troubleshooter 25, Helpdesk Hero 50, IT Veteran 100, Ticket Machine 250, Legend 500, Call Master 10 calls, Call Center Pro 25 calls, Streak Starter 3-day login streak, Dedicated 7-day, Unstoppable 30-day, 1K Club 1,000 score, High Roller 10,000 score, Sharpshooter 90%+ accuracy at 20+ tickets) and CareerTier (4 tiers: 50/100/250/500 points). Build a background job that rebuilds the Progress read-model from Event+Grade history (score, accuracy, tickets resolved, call volume, category breakdown, priority breakdown, training-focus toggles). Build the Analytics page (stat row, tier-progress ladder with the full 10-rung scale from PRODUCT_MAP.md §15, category/priority breakdowns, call-activity table, training-focus toggle grid with Save Preferences), Achievements page (current rank hero, career-progression ladder, Earned/Locked sections), Leaderboard modal (Global scope, ranked rows), Profile menu (dropdown to all these surfaces), Settings modal (Profile tab fully functional — display name + emoji avatar picker; Account/Preferences/Billing/Classroom/Community/Our Story may be minimal stubs but must render without 404), and Past Tickets (read-only list from the student's Attempt/Grade history).

Every number shown on Analytics must be derived from Event/Grade via the Progress rebuild job — do not hand-maintain a separate counter anywhere. Do not implement real Stripe billing in the Settings Billing tab yet.

Before finishing: run lint, typecheck, and the full test suite, including a Vitest test for the Progress rollup job against a fixture event log with known expected output. Build for production. Use Playwright to resolve a ticket end-to-end (from earlier phases' flows) and confirm Analytics and Achievements reflect it without any manual recompute trigger in the UI.

Finish with a summary of every file changed. Do not modify any file outside service-desk-app/.
```

---

## Phase 11 — Admin scenario builder

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §20 (Classroom foundation) — note this section is explicitly the sparsest-evidenced surface; build from the database plan and this document's design notes, not from screenshots that don't exist
- service-desk-app/docs/DATABASE.md §1 (Organization/Classroom/Enrollment/Assignment) and §3 (Scenario/ScenarioVersion/ScenarioObjective) — do not invent a new content model, extend the existing predicateType/predicateParams shape
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 11 — Admin scenario builder"

Also compare the one real piece of evidence for this surface: ../artifacts/screenshots/desktop/join-classroom.png, ../artifacts/html/join-classroom.html, ../artifacts/metadata/join-classroom.json.

Task: implement Phase 11 only. Build the teacher-facing classroom dashboard (create classroom, view roster, view join code), make the student-facing "Join Classroom" flow fully real (short join-code entry, inline invalid/not-found feedback without navigating away, matching join-classroom.png's UX), a scenario builder UI (form-based authoring of Scenario/ScenarioVersion/ScenarioObjective/ScenarioHint/DeploymentStepTemplate rows — never raw DB edits, never a new predicate schema beyond what DATABASE.md §3 defines), and assignment creation (assign a published ScenarioVersion to a classroom with an optional due date). Publishing a new ScenarioVersion must never mutate a previously-published version — always insert a new version row. Extend the Leaderboard from Phase 10 with a real classroom-scoped view alongside the existing Global view. Enforce RBAC: student accounts must be rejected (not just UI-hidden) from every teacher/admin route and procedure.

Do not build a full curriculum/rubric-authoring UI beyond the existing objective/predicate model — keep the objective editor form-based against predicateType/predicateParams as already defined.

Before finishing: run lint, typecheck, and the full test suite, including an RBAC test asserting a student session gets rejected from teacher/admin procedures at the API layer. Build for production. Use Playwright to: create a classroom as a teacher, get the join code, join it as a second test student account, author a scenario as the teacher, assign it to the classroom, and confirm the student sees it as an assignment.

Finish with a summary of every file changed. Do not modify any file outside service-desk-app/.
```

---

## Phase 12 — Testing and deployment

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`. This phase adds no product features — it only hardens CI, deployment, and test coverage for everything built in Phases 1-11.

Read first, in full:
- service-desk-app/docs/ARCHITECTURE.md §5 (Testing strategy), §6 (Security & evidence handling), §7 (Deployment)
- service-desk-app/docs/PRODUCT_MAP.md's "Evidence index" section at the end, as the checklist of every page/state that needs Playwright coverage
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 12 — Testing and deployment"

Task: implement Phase 12 only. Add a CI workflow (GitHub Actions or equivalent) running lint, typecheck, unit tests, integration tests (against a service-container Postgres), Playwright e2e, and production build on every PR, blocking merge on failure. Add docker/docker-compose.prod.yml, docker/Dockerfile.web, docker/Dockerfile.api, production-shaped (no dev-only services). Expand the Playwright suite to cover every page/state listed in PRODUCT_MAP.md's evidence index, at both desktop (1440x1000) and mobile (375x812) viewports, with an @axe-core/playwright accessibility scan on each. Add or verify a seed/demo-data script that stands up a realistic demo environment from empty. Confirm `prisma migrate deploy` (not `db push`) runs cleanly against a fresh empty Postgres as a documented, tested step.

Do not add any new product feature, page, or API endpoint "while touching CI" — this phase is testing/deployment infrastructure only.

Before finishing: run the full CI pipeline locally end-to-end (lint, typecheck, unit, integration, e2e, build) and confirm all green on a clean checkout. Boot `docker compose -f docker/docker-compose.prod.yml up` from a clean environment and confirm the stack comes up and is usable.

Finish with a summary of every file changed, plus a coverage note listing which PRODUCT_MAP.md pages now have Playwright coverage and confirming none are missing. Do not modify any file outside service-desk-app/.
```

---

## Phase 13 — Later Nexus integration

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/PRODUCT_MAP.md §21 (Subscription/paywall UX) and §22 (voice/call coverage gap)
- service-desk-app/docs/DATABASE.md §7 (Plan, Subscription, DailyQuotaUsage)
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 13 — Later Nexus integration"

Also compare against: ../artifacts/screenshots/desktop/subscription-plans.png, quota-ticket.png, quota-call-paywall.png, voicemails-paywall.png, mock-interview-paywall.png.

Task: implement only the Stripe/billing portion of Phase 13 in this run — do NOT implement voice call, voicemail, or mock-interview features under any circumstances, even if they seem straightforward; those require a written consent/recording-retention/abuse-control policy document to exist first, and that policy does not yet exist. If you believe those features are needed, stop and report that instead of building them.

Build: the Subscription Plans modal matching subscription-plans.png's exact structure (Monthly/Annual toggle, Free plan card with 5 tickets/day + 1 call/day + past tickets + analytics + leaderboard + desktop tools, Pro plan card at a price you choose with unlimited tickets/calls/audible voicemails/AI mock interviews, "Payments are handled securely in Stripe" and auto-renew disclosure copy), Stripe Checkout session creation wired to the Pro plan, a Stripe Billing Portal link from Settings' Billing tab, and a webhook handler updating the Subscription/Plan state on checkout completion, renewal, and cancellation. Enforce the Free-tier daily ticket/call quotas server-side (DailyQuotaUsage), with the UI routing exhausted actions into this Subscription Plans modal rather than a dead-end error, matching quota-ticket.png/quota-call-paywall.png's pattern.

Use Stripe test-mode keys only. Never wire real payment collection during this development pass.

Before finishing: run lint, typecheck, and the full test suite, including Stripe webhook signature verification tests and plan upgrade/downgrade/cancel flow tests run in Stripe test mode. Build for production. Use Playwright to exhaust a test account's daily ticket quota and confirm it routes into the Subscription Plans modal rather than erroring.

Finish with a summary of every file changed, and explicitly confirm no voice/voicemail/mock-interview code was added. Do not modify any file outside service-desk-app/.
```

---

## Phase 14 — Remote Desktop layout and interaction bug fixes

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`.

Read first, in full:
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 14 — Remote Desktop layout and interaction bug fixes" (contains exact file:line grounding for every bug — verify line numbers against the current file, they may have drifted)
- apps/web/components/RemoteDesktopTool.tsx (full file, ~1318 lines)
- apps/web/components/MainContainer.tsx
- apps/web/lib/remote-desktop-learning.ts

Task: implement Phase 14 only — a pure layout/CSS/interaction-guard pass on the existing Remote Desktop tool. Fix, in order: (1) the `max-w-7xl` cap in MainContainer.tsx overriding RemoteDesktopTool's own wider max-width on large monitors — without changing MainContainer's default for every other tool; (2) the fixed arbitrary-pixel `min-h-[720px]`/`min-h-[693px]` heights and grid stretch mismatch causing a white box below the desktop and non-viewport-filling height; (3) the window-cascade `% 3` overlap bug and missing z-index coordination with the taskbar so windows never render outside the desktop surface or under the taskbar; (4) mobile 375×812 horizontal overflow and unreachable off-screen chrome; (5) the toast/CompletionSummary collision where "Try another approach" can render while "Solution complete" is already showing for the same scenario — suppress it; (6) taskbar/icon/window alignment; (7) ticket panel (aside) text readability/contrast.

Do not touch `packages/simulation-engine` or `packages/shared` — no action types, payloads, overlay fields, or scenario data change in this phase. Do not change MainContainer's default max-width for other tools. Do not alter grading/completion logic, only its presentation.

Before finishing: run `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `pnpm audit --prod`. Use Playwright at 1440×1000 and 375×812: open 4+ app windows and confirm none exactly overlap or clip under the taskbar; complete a scenario and confirm no "Try another approach" toast can appear afterward for it; confirm zero horizontal scroll at 375×812; confirm no visible empty box below the desktop at both viewports; confirm zero browser console/page errors.

Finish with a summary of every file changed, a screenshot-described confirmation of each of the 8 completion-checklist items in IMPLEMENTATION_PLAN.md's Phase 14 section, and explicit confirmation that no simulation-engine/shared file was touched. Do not modify any file outside service-desk-app/. Do not deploy or touch production.
```

---

## Phase 15 — Remote Desktop Terminal application

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`. Phase 14 (layout fixes) must be merged before starting this phase — confirm `git log` shows it, or check with the user if it's missing.

Read first, in full:
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 15 — Remote Desktop Terminal application" (exact command list, per-command behavior, and file list)
- apps/web/components/RemoteDesktopTool.tsx
- packages/simulation-engine/src/apply-action.ts (focus on all `remote_desktop.*` handling and `remoteDesktopRejectReason`)
- packages/simulation-engine/src/actions/index.ts
- packages/simulation-engine/src/types.ts (`RemoteDesktopOverlay`)
- packages/simulation-engine/src/serialize.ts (the `restoreAttempt` back-fill block, ~lines 487-577, and `isRemoteDesktopOverlay`)
- packages/shared/src/remote-desktop-fixtures.ts

Task: implement Phase 15 only. Add a real Terminal app (new `terminal` appId, monospace scrollback + input line) to the Remote Desktop, backed by a new `remote_desktop.run_terminal_command` action with payload `{assetTag, command}`. Implement all 14 commands from the plan's command list (ipconfig, ipconfig /all, ping, nslookup, tracert, net use, whoami, hostname, gpupdate, systeminfo, tasklist, sc query, net start/stop, cls, help) as deterministic string output computed server-side from the attempt's current overlay/scenario state — never execute a real process (no `exec`/`spawn`/`child_process` anywhere in the diff). `net start`/`net stop` and `sc query` must read/write the same `serviceStates` overlay field that any future Services app will also use — do not create a second, divergent copy of service state. Add `terminalHistory` to `RemoteDesktopOverlay` and extend `serialize.ts`'s validation and back-fill block so older saved attempts default it to `[]` without breaking.

Route the new action through the existing `apply-action.ts` guard pattern (`remoteDesktopRejectReason`) — Terminal commands require `connected`, same as other app actions.

Before finishing: run `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `pnpm audit --prod`. Add Vitest coverage in packages/simulation-engine for every command against at least the VPN, DNS-in-progress (if Phase 18 hasn't landed yet, use the closest available broken-network scenario), and mapped-drive scenario states, plus an unrecognized-command test. Use Playwright at 1440×1000 and 375×812 to open Terminal, run several commands, and confirm output; confirm `cls` clears scrollback cleanly; confirm terminal history survives a page refresh (persistence).

Finish with a summary of every file changed and explicit confirmation that no real command execution was introduced. Do not modify any file outside service-desk-app/. Do not deploy or touch production.
```

---

## Phase 16 — File Explorer overhaul

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`. Phases 14 and 15 must be merged before starting this phase (File Explorer must share drive-status state with Phase 15's Terminal `net use` output).

Read first, in full:
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 16 — File Explorer overhaul"
- apps/web/components/RemoteDesktopTool.tsx (current `explorer` app case)
- packages/simulation-engine/src/apply-action.ts, actions/index.ts, types.ts (the `RemoteDesktopOverlay` fields Phase 15 added for drive/service state)
- packages/shared/src/remote-desktop-fixtures.ts

Task: implement Phase 16 only. Replace the current 4-flat-button `explorer` app case with a real navigable File Explorer (This PC, Local disk, network drives, a small representative folder/file tree per workstation) backed by new action types: `remote_desktop.explorer_navigate {assetTag, path}`, `remote_desktop.explorer_reconnect_drive {assetTag, driveLetter}`, `remote_desktop.explorer_refresh {assetTag}`. Model permission-error and network-path-error as visually and textually distinct states. Reconnecting a drive here and fixing the underlying VPN/network issue elsewhere must produce the identical resulting overlay state — no duplicate/divergent drive-status field from Phase 15's Terminal `net use` data; extend the same overlay fields. Add per-drive disk-space info (static per workstation fixture). Refresh re-reads current state without a full page reload.

Keep scope to what the ticket scenarios need — a small fixed tree, not a general filesystem.

Before finishing: run `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `pnpm audit --prod`. Add a Vitest test explicitly asserting File Explorer and Terminal's `net use` report identical drive status for the same overlay state. Use Playwright at 1440×1000 and 375×812: for the VPN scenario, confirm the mapped drive shows a network-path error before VPN connects and succeeds after; for the mapped-drive scenario, confirm reconnect clears the disconnected state and persists through refresh.

Finish with a summary of every file changed. Do not modify any file outside service-desk-app/. Do not deploy or touch production.
```

---

## Phase 17 — VPN, Settings, Services, System Update, Chat/Mail, Browser depth

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`. Phases 14-16 must be merged first (Services must share `serviceStates` with Phase 15's Terminal commands; Settings' Storage tab should stay consistent with Phase 16's File Explorer disk-space info).

Read first, in full:
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 17 — VPN, Settings, Services, System Update, Chat/Mail, Browser depth"
- apps/web/components/RemoteDesktopTool.tsx (current `vpn`, `settings`, `browser`, `updates`, `chat`, `mail` app cases)
- apps/web/components/CompanyChatTool.tsx (the real Company Chat this phase should stay consistent with, not duplicate)
- apps/web/components/DocumentationTool.tsx and packages/shared/src/documentation-fixtures.ts (what the Browser app should link into)
- packages/simulation-engine/src/apply-action.ts, actions/index.ts, types.ts

Task: implement Phase 17 only. Rework each shallow one-button app case into a dedicated component per the plan's per-app requirements: VPN Client (explicit connect/disconnect, status indicator, error state, timestamped connection log), Settings (tabbed: Network — where DNS is actually edited, Storage, Applications, Updates — sharing the same pending-update state as the System Update app), Services (new app; list + Restart/Start/Stop per service, sharing `serviceStates` with Phase 15's Terminal `sc query`/`net start`/`net stop`), System Update (pending → installing → restart-required → applied sequence, not one click), Chat/Mail (extend to reference the existing `CompanyChatTool` data model rather than maintaining a second divergent chat concept), Browser (link into existing Documentation articles relevant to the active ticket — no general web navigation).

Before finishing: run `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `pnpm audit --prod`. Add Vitest coverage per new action type. Use Playwright at 1440×1000 and 375×812: connect VPN and confirm the log/status update and that File Explorer's mapped drive becomes reachable; restart a service via Services and confirm both Services and Terminal's `sc query` show Running afterward.

Finish with a summary of every file changed. Do not modify any file outside service-desk-app/. Do not deploy or touch production.
```

---

## Phase 18 — Three complete tickets, learning modes, and completion grading

```text
You are working only inside `Nexus dupe/service-desk-app/`. Do not touch `../artifacts/`, `../playwright/`, `../website-capture/`, or `../tasks/`. Phases 14-17 must be merged first — this phase depends on Terminal, File Explorer, VPN, Settings' Network tab, and Services all existing and sharing consistent state.

Read first, in full:
- service-desk-app/docs/IMPLEMENTATION_PLAN.md § "Phase 18 — Three complete tickets, learning modes, and completion grading" (contains the exact per-ticket workflow, grading rule, learning-mode definitions, and completion-summary field list)
- packages/shared/src/remote-desktop-fixtures.ts (existing `vpn-shared-drive` scenario to upgrade, and the shape every scenario follows)
- packages/shared/src/ticket-fixtures.ts (the `suggestedTools` gap for INC2401/INC2402/INC2405 noted in the plan — fix it here)
- packages/simulation-engine/src/apply-action.ts (current flat requiredSteps/optionalSteps/incorrectSteps grading at ~784-808, 900-913, and the hardcoded `resolutionNote: scenario.explanation` close path at RemoteDesktopTool.tsx:524-526)
- packages/simulation-engine/src/types.ts, serialize.ts
- apps/web/components/RemoteDesktopTool.tsx (`CompletionSummary`, `ProgressiveHints`)
- apps/web/lib/remote-desktop-learning.ts

Task: implement Phase 18 only. Extend the scenario/objective model to track diagnose/fix/verify/note/close phases (not a flat undifferentiated step set) while keeping backward compatibility with the 5 existing scenarios (`vpn-shared-drive` upgraded in place, `pdf-export-update`/`profile-storage`/`network-configuration`/`mapped-drive-permissions` unchanged — add a regression test proving they still pass). Add a new `dns-configuration-failure` scenario/ticket (Ticket B — entirely new, no DNS scenario exists today) and a new `service-failure` scenario/ticket (Ticket C, e.g. Print Spooler — entirely new). Upgrade `vpn-shared-drive` into Ticket A's full workflow. Add a `remote_desktop.add_internal_note` action carrying real student-authored note text, and require it (non-trivial length) plus a real verification action before a ticket can close — replace the hardcoded `scenario.explanation` autofill. Grade on final state + verification evidence gathered, not one hardcoded click order (write a test proving at least one alternate valid action order also passes each ticket). Add `learningMode: 'guided' | 'practice' | 'assessment'` (extending/replacing the flat `trainingMode` boolean, migrated cleanly via serialize.ts's back-fill) with the exact hint-availability behavior per mode from the plan — and confirm no mode ever exposes internal objectives/action keys/required-action lists to the student (the existing mentor-only `MentorScenarioReview` gate must still be the only way to see them). Upgrade `CompletionSummary` to show root cause, fix performed, why it worked, evidence gathered, missed useful actions, hints used, and final score/feedback. Fix the `suggestedTools` gap in `ticket-fixtures.ts` for INC2401/INC2402/INC2405.

Before finishing: run `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `pnpm audit --prod`. Vitest: full diagnose→fix→verify→note→close path for each of the 3 tickets; an incorrect-order/incomplete-evidence rejection test per ticket; per-mode hint-gating tests; the regression test for the 4 unchanged scenarios. Playwright at 1440×1000 and 375×812: complete all 3 tickets end-to-end, confirm the completion summary shows every required field, confirm close is blocked without a written note, confirm refresh mid-ticket preserves diagnose/fix/verify progress, confirm zero console/page errors.

Finish with a summary of every file changed, confirmation all 9 Phase 18 completion-checklist items in IMPLEMENTATION_PLAN.md pass, and explicit confirmation the 4 pre-existing scenarios still pass unchanged. Do not modify any file outside service-desk-app/. Do not deploy or touch production.
```
