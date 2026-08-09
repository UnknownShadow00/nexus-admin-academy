# Implementation Plan

13 Codex-sized phases. Each phase is scoped to be completable, reviewable, and mergeable independently — a fresh Codex run reads only this phase's section (plus the referenced docs/evidence), never the whole product map at once. Every phase's Codex prompt lives in `CODEX_PROMPTS.md` in the same order.

**Global rules for every phase** (repeat in every prompt, not just here):
- Work only inside `service-desk-app/`.
- Never modify `../artifacts/`, `../playwright/`, `../website-capture/`, `../tasks/`, or any file outside `service-desk-app/`.
- Never invent scope beyond the phase's checklist — no unrelated refactors, no "while I'm here" changes.
- All ticket content, employee names, articles, and company branding must be original — evidence files describe structure/behavior only, never copy their literal text into the app.
- Every phase ends with: lint clean, typecheck clean, unit/integration tests passing, `apps/web` production build succeeds, and (from Phase 2 onward) a Playwright check that the built pages render without console errors.

---

## Phase 1 — Project setup and design system

**Goal**: a working monorepo skeleton with the design-system component library, buildable and lintable, with zero product pages yet.

**Files/pages**: `package.json` (workspace root), `pnpm-workspace.yaml`, `turbo.json`, `apps/web` (Next.js app scaffold, empty home page only), `packages/ui` (Button, IconButton, Card/CardHeader, Modal, PanelFrame, Input, Tabs, Badge/PriorityBadge, Tooltip — per DESIGN_SYSTEM.md §5), `packages/shared` (priority/tier/category enums), `docker/docker-compose.yml` (postgres only, unused yet), root ESLint/Prettier/TSConfig.

**Evidence to reference**: `docs/DESIGN_SYSTEM.md` (all sections) as the single source; no need to open raw `../artifacts/` files this phase beyond spot-checking 2-3 screenshots for color/spacing sanity (`../artifacts/screenshots/desktop/authenticated-queue.png`, `tool-directory.png`).

**Database changes**: none.

**API endpoints**: none.

**Tests**: Vitest unit tests for each `packages/ui` component (renders, variant props apply correct classes); no e2e yet (nothing to click through).

**Completion checklist**:
- [ ] `pnpm install && pnpm build` succeeds from repo root.
- [ ] `pnpm lint` and `pnpm typecheck` clean across all packages.
- [ ] Storybook or a simple `/design-system` debug route in `apps/web` renders every `packages/ui` component with its documented variants (Button primary/light/soft, PanelFrame's 4 variants, etc.) — a visual smoke page for the next 12 phases to trust.
- [ ] Tailwind config's color usage matches DESIGN_SYSTEM.md §1 (zinc/sky/red/orange/amber families, no invented hex tokens).

**Must not**: build any actual product page, touch `packages/database` or `packages/simulation-engine` (those don't exist yet), add auth.

---

## Phase 2 — Main shell and navigation

**Goal**: the authenticated app shell (header, Tools panel, Dashboard placeholder, client-side sub-router) is navigable and visually matches the original, with mock/static data (no DB yet).

**Files/pages**: `apps/web/app/(app)/layout.tsx` (header + shell), `apps/web/app/(app)/page.tsx` (Dashboard shell, static mock tickets), Tools panel modal component, profile-menu dropdown, footer. Public marketing shell too: `apps/web/app/page.tsx` (logged-out `/`), `apps/web/app/login/page.tsx` (form only, no real auth submission yet).

**Evidence to reference**: `docs/PRODUCT_MAP.md` §0 (navigation model), §1 (global chrome), §2 (public pages), §3 (dashboard layout); screenshots `authenticated-queue.png`, `tools-menu.png`, `public-home.png`, `login-empty.png`, `mobile-authenticated-queue.png`; HTML siblings for exact class structure.

**Database changes**: none yet.

**API endpoints**: none yet (static/mock data in the component).

**Tests**: Playwright specs: shell renders at desktop 1440×1000 and mobile 375×812 with no horizontal overflow (matches `../artifacts/metadata/mobile-overflow.json`'s `clientWidth === scrollWidth` assertion); Tools panel opens/closes via click and Esc, focus-traps; header buttons all present with correct `aria-label`s per PRODUCT_MAP.md §1.

**Completion checklist**:
- [ ] Header, Tools panel (3 category groups, 8 tools, exact icons/order from PRODUCT_MAP.md §0), footer match the referenced screenshots closely.
- [ ] Client-side sub-router exists (tool routes resolve to placeholder pages, no page reload between them) — this is the architectural seed every later phase plugs into.
- [ ] Dark theme default with pre-paint inline script (no FOUC), per DESIGN_SYSTEM.md §6.
- [ ] Axe accessibility check passes on shell + Tools panel.

**Must not**: wire real authentication, create any database package, implement any tool's actual functionality (placeholders only).

---

## Phase 3 — Dashboard and ticket workspace

**Goal**: real auth + the ticket queue and ticket workspace work against a real (seeded, static-for-now) dataset — the core gameplay loop is clickable end to end minus cross-tool actions.

**Files/pages**: `packages/database` created (Prisma schema for §1-§3 of DATABASE.md: identity, environment templates, scenarios — no attempt/overlay tables yet, those arrive in Phase 4), Auth.js setup (credentials + Google provider), `apps/web` Dashboard (real queue from DB), Ticket Workspace page (`docs/PRODUCT_MAP.md` §4): header actions, ticket detail fields, help/reveal mechanic (client-visible steps only — no scoring yet), Close flow UI (no real grading yet, just the modal/warning UX).

**Evidence to reference**: `docs/PRODUCT_MAP.md` §3, §4 in full; `../artifacts/metadata/complete-ticket-workflow.json` for exact ticket-detail field shape and close-review copy pattern; `../artifacts/screenshots/desktop/ticket-assigned-baseline.png` through `ticket-close-review.png`.

**Database changes**: `packages/database` created; migrate identity models + `EnvironmentTemplate`/`DirectoryUserTemplate`/`ServerTemplate`/etc. + `Scenario`/`ScenarioVersion`/`ScenarioObjective`/`ScenarioHint` (DATABASE.md §1-3); seed script with one original environment template (roster/servers) and 2-3 original scenarios.

**API endpoints**: `auth.*` (Auth.js routes), `tickets.listQueue`, `tickets.getById`, `tickets.revealHint` (client-visible only, no scoring effect yet), `tickets.closeTicket` (records intent, real grading deferred to Phase 4).

**Tests**: Vitest for auth flows and Prisma seed integrity; Playwright for login → dashboard → open ticket → reveal all hints → close (resolved and unresolved paths, checking the penalty-warning copy renders).

**Completion checklist**:
- [ ] A student can register/login, see a real seeded queue, open a ticket, reveal hints in order, and close it.
- [ ] All ticket copy is original (no real captured company/employee names beyond structurally-equivalent originals).
- [ ] Login form validation matches PRODUCT_MAP.md §2.2 (native email validation, required password).

**Must not**: implement any of the 8 tools yet, implement real grading/points (Phase 4), implement chat (Phase 6).

---

## Phase 4 — Shared simulation engine

**Goal**: `packages/simulation-engine` exists with `applyAction()`, event logging, and deterministic grading — this is the architectural core every subsequent tool plugs into. No new UI in this phase; wire it under the Phase 3 ticket-close flow as the first real consumer.

**Files/pages**: `packages/simulation-engine/src/{applyAction.ts, evaluateObjectives.ts, actions/*.ts}`; `packages/database` migration for `Attempt`, `Event`, `Grade`, and the overlay/instance tables from DATABASE.md §4-5.

**Evidence to reference**: `docs/ARCHITECTURE.md` §3 in full (this phase *is* that section, implemented); `docs/DATABASE.md` §4-5.

**Database changes**: add `Attempt`, `DirectoryUserOverlay`, `DeploymentRun`, `ProvisionedDevice`, `Shipment`, `ChatThread`, `ChatMessage`, `Event`, `Grade`, `Progress`.

**API endpoints**: `attempts.start`, `attempts.reset`, a generic `attempts.applyAction` tRPC mutation (thin wrapper over `simulation-engine.applyAction`), `attempts.getGrade`.

**Tests**: this phase is unit-test-heavy — Vitest coverage for: valid action happy path, out-of-order/invalid action rejection (logged with `success:false`), quota-exhausted rejection, objective evaluation against hand-built event-log fixtures, reset creates a new Attempt without deleting the old one's Events. Playwright: the Phase 3 ticket-close flow now produces a real `Grade` row and the UI reflects real points delta (matching the observed -17-point unresolved-close example structurally, using original numbers).

**Completion checklist**:
- [ ] `Event` table is provably insert-only (no update/delete call sites in `apps/api` — grep-checked in review).
- [ ] Closing a ticket now computes and displays a real, server-computed grade.
- [ ] Resetting an attempt preserves old `Event`/`Grade` rows and starts a fresh `Attempt`.

**Must not**: build Directory/Deployment/etc. UI yet — this phase proves the engine works through the one flow already wired (ticket close), not through every tool.

---

## Phase 5 — Directory

**Goal**: first real tool, and the flagship "shared state" demo (unlock a user → visible elsewhere later).

**Files/pages**: `apps/web`'s Directory tool page (`#ad` route in the client sub-router), 83-row (or your original roster's size) list, user detail panel, "New User" action.

**Evidence to reference**: `docs/PRODUCT_MAP.md` §6; `../artifacts/screenshots/desktop/tool-directory.png`; `../artifacts/html/tool-directory.html`; `../artifacts/metadata/tool-directory.json`.

**Database changes**: none beyond Phase 4's `DirectoryUserOverlay` (already migrated) — this phase is the first to actually read/write it.

**API endpoints**: `directory.list` (template + overlay merge, per ARCHITECTURE.md §3.1's copy-on-write read rule), `directory.unlockUser`, `directory.resetPassword`, `directory.updateGroups` — all routed through `attempts.applyAction`.

**Tests**: Vitest for the template+overlay merge logic; Playwright: open Directory, unlock a locked user, refresh the page, confirm the unlock persisted (the task brief's explicit "survives refresh" requirement, testable for real starting this phase).

**Completion checklist**:
- [ ] Directory panel visually matches `tool-directory.png` (panel-frame `--ad` variant, back button, learn-link).
- [ ] Unlock/reset actions write `Event` rows and are reflected after refresh.
- [ ] "New User" creates a real overlay-backed entry scoped to the attempt.

**Must not**: build Remote Desktop or Asset Management yet (their consumption of Directory state is Phase 7).

---

## Phase 6 — Documentation and chat

**Goal**: Knowledge Base tool + Company Chat, including the scripted-branching-dialogue model.

**Files/pages**: Documentation tool page (`#docs`), category list + article detail; Company Chat panel (header-triggered, not a route) with Recent/Contacts/Pinned tabs, 500-char-capped input, quick-reply chips.

**Evidence to reference**: `docs/PRODUCT_MAP.md` §11 (Documentation, 10 categories/38 docs) and §14 (Company Chat); screenshots `tool-documentation.png`, `company-chat-empty.png`, `ticket-chat-diagnosis-and-address.png`, `ticket-chat-delivery-confirmation.png`; `../artifacts/metadata/complete-ticket-workflow.json` for the scripted-reply pattern.

**Database changes**: none beyond Phase 4's `ChatThread`/`ChatMessage` (already migrated) + this phase adds `KnowledgeBaseArticle` seed content (schema already in DATABASE.md §2).

**API endpoints**: `docs.listCategories`, `docs.getArticle`; `chat.listThreads`, `chat.sendMessage` (triggers scripted NPC reply lookup keyed by scenario's chat script), `chat.markPinned`.

**Tests**: Vitest for the scripted-branch resolver (given a trigger key, returns the right canned reply); Playwright: open chat from within a ticket, send a message matching a scripted trigger, confirm the NPC reply appears and an `Event` is logged.

**Completion checklist**:
- [ ] 10 original KB categories with original article content, matching the captured category/count structure.
- [ ] Chat message input hard-caps at 500 characters client- and server-side.
- [ ] At least one scenario's chat script (diagnosis + delivery confirmation, mirroring the captured 2-beat pattern) is fully wired end-to-end.

**Must not**: wire a live LLM for chat — this is scripted branching dialogue per ARCHITECTURE.md's explicit call-out, not generative AI.

---

## Phase 7 — Asset and PC tools

**Goal**: Remote Desktop, Asset Management, PC Shelf — the tools that consume Directory/Device state written by other tools, proving the shared-state model generalizes beyond Phase 5's single example.

**Files/pages**: Remote Desktop tool page (`#remotedesktop`, workstation list + minimal connected-session view), Asset Management tool page (`#assets`, By Users/By Assets toggle, Sync from AD action, search), PC Shelf tool page (`#pcshelf`, empty + populated states).

**Evidence to reference**: `docs/PRODUCT_MAP.md` §8, §9 (PC Shelf note), §10, §12; screenshots `tool-remote-desktop.png`, `tool-asset-management.png`, `tool-pc-shelf.png`.

**Database changes**: none beyond what Phase 4 migrated (`ProvisionedDevice`, `DeviceTemplate` already exist) — this phase is the second/third consumer of the overlay-merge pattern.

**API endpoints**: `remoteDesktop.list`, `remoteDesktop.connect` (stub session); `assets.list` (by-user/by-asset views), `assets.syncFromAd` (pulls current Directory overlay state into the Asset view — the "Sync from AD" flagship integration); `pcShelf.list`.

**Tests**: Playwright: unlock a user in Directory (Phase 5), confirm Remote Desktop reflects login-availability change without a full reload; run "Sync from AD" in Asset Management after a Directory change, confirm it reflects.

**Completion checklist**:
- [ ] Asset tags are consistent across Directory, Remote Desktop, Asset Management, and PC Shelf (one `assetTag` key, per DATABASE.md).
- [ ] PC Shelf persists across refresh (explicitly *not* replicating the original's session-only limitation, per ARCHITECTURE.md §3.5/PRODUCT_MAP.md §10).
- [ ] Realtime or at-minimum refetch-on-focus keeps two tools showing consistent state without manual reload.

**Must not**: build the Deployment tool that populates PC Shelf yet (Phase 8) — seed PC Shelf with fixture data for this phase's tests if needed.

---

## Phase 8 — Server Room and Remote Desktop depth, Computer Deployment

**Goal**: the two deepest interaction surfaces — Server Room's live infrastructure view, and the full 11-step Computer Deployment flow as a real deterministic state machine.

**Files/pages**: Server Room tool page (`#serverroom`, Overview/Topology/Devices/Servers tabs); Computer Deployment hub (`#deployment`, 3 method cards, Server Imaging enabled, other two "under development") + the full 11-step flow UI (cable matching, F12 timing interaction, boot source, share auth, hostname entry, task-sequence progress, reboot, domain login, success screen).

**Evidence to reference**: `docs/PRODUCT_MAP.md` §7 and §9 in full — §9 is the richest single section in the whole document, use it as the literal spec; `../artifacts/screenshots/desktop/tool-server-room.png`, `tool-computer-deployment.png`, all 10 `deployment-*.png` files; `../playwright/complete-ticket.mjs` as the literal interaction/selector sequence to translate into both the UI's step components and the e2e test.

**Database changes**: none beyond Phase 4 (`DeploymentRun`, `DeploymentStepTemplate` already migrated) — seed 11 `DeploymentStepTemplate` rows for the Server Imaging scenario with original wrong-path copy structurally matching (not copying) the captured pattern.

**API endpoints**: `serverRoom.getOverview` (topology/devices/servers); `deployment.startRun`, `deployment.submitStepAction` (validates against `DeploymentStepTemplate.expectedAction`, returns success or the matching `wrongActionResponses` entry), `deployment.completeRun` (creates `ProvisionedDevice`, lands it on PC Shelf).

**Tests**: this phase's Playwright spec is the highest-value e2e test in the whole plan — adapt `../playwright/complete-ticket.mjs` directly: attempt each documented wrong path (wrong cable/port, missed F12 timing, local-disk boot, IPv6 boot, wrong share password, invalid/duplicate hostname, wrong domain login) and assert the correct inline-correction copy appears, then complete the correct path and assert a `ProvisionedDevice` lands on PC Shelf.

**Completion checklist**:
- [ ] All 11 steps implemented as a true server-validated state machine (`deployment.submitStepAction`), not client-side-only logic.
- [ ] Hostname validation enforces the uppercase `SD####`-equivalent pattern and rejects tags already used by another `DeploymentRun` (DB unique constraint per DATABASE.md §4).
- [ ] F12/POST timing interaction reproduces the "ignore input for ~900ms, accept within a ~3.5s window" behavior.
- [ ] Server Room's Devices/Servers/Topology tabs render the same 13-node dataset consistently.

**Must not**: implement Manual Domain Enrollment or Cloud Provisioning beyond their "under development" card state — matches the original's own scope exactly.

---

## Phase 9 — Deployment and shipping

**Goal**: close the loop — Ship Manager consumes PC Shelf output, and a ticket's objectives can require a real shipment.

**Files/pages**: Ship Manager tool page (`#shipmanager`) — recipient/address form, sender department, equipment list, provisioned-PC selector, shipping speed, return label, validation states, "Refill Last Address" post-ship convenience.

**Evidence to reference**: `docs/PRODUCT_MAP.md` §13; screenshots `tool-ship-manager.png`, `shipping-form-complete.png`, `shipping-required-field-validation.png`, `replacement-shipped.png`.

**Database changes**: none beyond Phase 4 (`Shipment` already migrated).

**API endpoints**: `shipManager.createShipment` (validates full address, consumes a `ProvisionedDevice` off PC Shelf if a computer was selected, routed through `applyAction`), `shipManager.getLastAddress`.

**Tests**: Playwright: from the Phase 8 deployment's provisioned device, ship it to the scenario's requester, confirm it leaves PC Shelf and the associated ticket objective (e.g. "device shipped to requester") completes and awards points.

**Completion checklist**:
- [ ] Empty-form submit shows the exact validation UX pattern from `shipping-required-field-validation.png` (inline, not a toast-only error).
- [ ] Rush/Priority speed ships instantly (no artificial delay simulation needed).
- [ ] A shipped device is provably removed from PC Shelf and provably completes the relevant `ScenarioObjective`.

**Must not**: implement real Stripe/payment flows here — Ship Manager's "shipping speed" is entirely simulated, no real carrier integration.

---

## Phase 10 — Analytics and progress

**Goal**: Analytics, Achievements, Leaderboard, Profile/Settings, Past Tickets — all the read-model/rollup surfaces, built on top of the now-real `Event`/`Grade` history from Phases 4-9.

**Files/pages**: Analytics page (`#analytics`), Achievements page (`#achievements`), Leaderboard modal, Profile menu + Settings modal (Profile tab minimum; Account/Preferences/Billing/Classroom/Community/Our Story as thin stubs), Past Tickets, Tutorial & Guides / Support & Feedback / About (static content pages).

**Evidence to reference**: `docs/PRODUCT_MAP.md` §15-19; screenshots for each.

**Database changes**: add `Achievement`, `StudentAchievement`, `CareerTier`, `Progress` (DATABASE.md §5) if not already migrated in Phase 4; seed the 17 achievements + 4 career tiers.

**API endpoints**: `analytics.getSummary` (reads `Progress`, rebuilt by a background job folding `Event`+`Grade`), `achievements.list`, `leaderboard.getGlobal` (and `getClassroom` once Phase 11 exists), `settings.updateProfile`.

**Tests**: Vitest for the `Progress` rollup job (given a fixture event log, produces correct score/accuracy/category breakdown); Playwright: resolve a ticket end-to-end, confirm Analytics and Achievements reflect it without a manual recompute trigger.

**Completion checklist**:
- [ ] Every number on Analytics is provably derived from `Event`/`Grade`, not a separately hand-maintained counter (spot-checked in review).
- [ ] All 17 achievements and 4 career tiers implemented with correct thresholds from PRODUCT_MAP.md §16.
- [ ] Settings' Profile tab (display name + avatar picker) is fully functional; other tabs may be minimal/stubbed but must not 404.

**Must not**: implement real Stripe billing in the Billing settings tab yet (Phase 13).

---

## Phase 11 — Admin scenario builder

**Goal**: teacher/admin surfaces — classroom creation, roster, scenario authoring, assignment, and the Classroom foundation the task brief calls out explicitly.

**Files/pages**: teacher-facing classroom dashboard, "Create Classroom"/"Join Classroom" flows (student side already stubbed in earlier phases — this phase makes Join Classroom fully real), scenario builder (author a `Scenario`/`ScenarioVersion`/`ScenarioObjective` set through a form, not raw DB edits), assignment creation.

**Evidence to reference**: `docs/PRODUCT_MAP.md` §20 (explicitly the sparsest-evidenced surface — build from the database plan and the task brief's requirements, not from screenshots, since none exist beyond the student-facing Join Classroom code entry).

**Database changes**: none beyond Phase 1's `Organization`/`Classroom`/`Enrollment`/`Assignment` (already migrated) — this phase is the first real consumer/UI for them.

**API endpoints**: `classrooms.create`, `classrooms.join` (join-code flow), `classrooms.listRoster`, `scenarios.create/update/publish` (creates a new `ScenarioVersion`, never mutates a published one), `assignments.create`.

**Tests**: Playwright: teacher creates a classroom, gets a join code, a second test student joins via that code, teacher authors a scenario and assigns it, student sees it as an assignment.

**Completion checklist**:
- [ ] Publishing a new `ScenarioVersion` never mutates a previously-published version (immutability enforced, matching ARCHITECTURE.md §3.1).
- [ ] Classroom-scoped leaderboard works (extending Phase 10's global leaderboard with a real second scope, per PRODUCT_MAP.md §17's design note).
- [ ] RBAC enforced: a student account cannot reach any teacher/admin route (tested, not just hidden in the UI).

**Must not**: build a full curriculum/grading-rubric authoring UI beyond what DATABASE.md §3 already models — keep the objective/predicate editor form-based against the existing `predicateType`/`predicateParams` shape, don't invent a new content model.

---

## Phase 12 — Testing and deployment

**Goal**: close every testing/CI/deployment gap left implicit in earlier phases; this phase adds no product features.

**Files/pages**: `.github/workflows/ci.yml` (or equivalent), `docker/docker-compose.prod.yml`, `docker/Dockerfile.web`, `docker/Dockerfile.api`, expanded Playwright coverage (full desktop+mobile pass across every page in PRODUCT_MAP.md's evidence index, plus `@axe-core/playwright` on all of them), load/seed scripts for a demo environment.

**Evidence to reference**: `docs/ARCHITECTURE.md` §5-7 in full.

**Database changes**: none (this phase hardens migrations/CI around the existing schema, e.g. confirms `prisma migrate deploy` runs cleanly from empty).

**API endpoints**: none new.

**Tests**: this phase's deliverable *is* the test suite — full CI pipeline (lint → typecheck → unit → integration → e2e → build) green on a clean checkout.

**Completion checklist**:
- [ ] CI runs on every PR and blocks merge on failure.
- [ ] `docker compose -f docker/docker-compose.prod.yml up` boots a working stack from a clean environment.
- [ ] Full Playwright suite covers every page listed in PRODUCT_MAP.md's evidence index, desktop + mobile.
- [ ] `prisma migrate deploy` runs cleanly against a fresh empty Postgres.

**Must not**: add new product features "while touching CI."

---

## Phase 13 — Later Nexus integration

**Goal**: connect `service-desk-app` to the broader Nexus platform (auth/account federation, shared design tokens if Nexus has its own, deployment into Nexus's infra) plus the deferred payment (Stripe) and voice/interview features explicitly called out as later-phase in `../REPORT.md`'s recommendations and `ARCHITECTURE.md`/PRODUCT_MAP.md §22.

**Files/pages**: Stripe Checkout + Billing Portal wiring (Settings' Billing tab, Subscription Plans modal → real checkout), webhook handler for subscription state; voice call / voicemail / mock interview modules **only after** explicit microphone-consent UX, recording/transcript retention policy, abuse controls, and a cost budget are defined (per REPORT.md's own recommendation — do not build these reactively).

**Evidence to reference**: `docs/PRODUCT_MAP.md` §21 (Subscription/paywall UX) and §22 (voice/call gap — explicitly undocumented in the evidence, treat as new original design, not reconstruction).

**Database changes**: `Plan`, `Subscription`, `DailyQuotaUsage` (DATABASE.md §7) if not already migrated earlier for quota enforcement; add call/voicemail/interview models only when this phase is actually scoped in detail (out of scope for this planning pass).

**API endpoints**: `billing.createCheckoutSession`, `billing.createPortalSession`, `stripe.webhook`.

**Tests**: Stripe test-mode integration tests (webhook signature verification, plan upgrade/downgrade flows); do not test against live Stripe.

**Completion checklist**:
- [ ] Free/Pro plan gates match PRODUCT_MAP.md §21 exactly (5 tickets/day, 1 call/day on Free; unlimited + audible voicemails + AI mock interviews on Pro).
- [ ] No checkout or payment code path can be exercised without explicit test-mode Stripe keys — never wire real payment collection during planning/dev.
- [ ] A written consent/retention policy doc exists in `docs/` **before** any voice/recording code is written.

**Must not**: build voice/voicemail/mock-interview UI or backend without the consent/retention/abuse-control design existing first — this is a hard gate, not a suggestion.

---

## Phase 14 — Remote Desktop layout and interaction bug fixes

**Goal**: fix the reported visual/UX defects in the existing Remote Desktop tool without touching the simulation-engine action model, scenario data, or grading logic. Pure layout/CSS/state-guard pass.

**Grounding** (exact current-state findings, do not re-derive — verify against the file first, line numbers may have drifted slightly since this was written):
- `apps/web/components/MainContainer.tsx:5` caps every tool page at `max-w-7xl` (1280px), overriding `RemoteDesktopTool.tsx:171`'s own `max-w-[1540px]` request — root cause of "too small on large monitors."
- `RemoteDesktopTool.tsx:217` grid has default `align-items: stretch`; combined with fixed `min-h-[720px]`/`min-h-[693px]` inner surfaces (`ComputerPicker` 580, `RemoteSurface` 676, `ConnectingScreen` 761, `LoginGate` 805, `SimulatedDesktop` 945) that don't fill the stretched column, this produces the white box below the desktop and the "desktop not filling available height" / "excessive black space" bugs.
- `DesktopWindow` (def ~1079) positions windows with `top-[12%] left-[18%]` plus `translate(${(index % 3) * 24}px, ${(index % 3) * 20}px)` (~1100-1105) — the `% 3` cascade resets every 3rd window, causing a 4th+ window to overlap the 1st exactly; the desktop surface has `overflow-hidden` and the taskbar (`absolute inset-x-0 bottom-0 h-11`, ~984) has no explicit z-index versus window z-index 20-40+ (~1106) — windows can render under/behind the taskbar or get clipped.
- Mobile overflow: same fixed pixel heights force vertical scroll on short viewports; `DesktopWindow`'s `w-[min(680px,76%)]` (~1100) and the aside/main grid's `minmax(18rem,…)` column (217) are not verified against very narrow viewports.
- Contradictory messages: the toast (def 382-410, message set at ~397) and `CompletionSummary`'s "Solution complete" panel (def 467-529, heading ~486) are independent and non-exclusive — once `completedScenarioIds` includes the scenario, a rejected `perform_scenario_step` (e.g. re-clicking a completed or incorrect step) still sets the toast to "Try another approach." with no guard suppressing it while Solution complete is showing (`apply-action.ts` reject path ~920-932 sets `lastError` but nothing disables further step-button clicks or the toast once completed).

**Files**: `apps/web/components/MainContainer.tsx`, `apps/web/components/RemoteDesktopTool.tsx`, `apps/web/lib/remote-desktop-learning.ts`. No changes to `packages/simulation-engine` or `packages/shared` — this phase touches presentation only.

**Fixes required**:
1. Let the Remote Desktop tool page opt out of (or widen) `MainContainer`'s `max-w-7xl` cap so `RemoteDesktopTool.tsx`'s own `max-w-[1540px]` actually applies, without changing `MainContainer`'s default width for every other tool that still wants 1280px.
2. Replace fixed `min-h-[720px]`/`min-h-[693px]` arbitrary pixel heights with viewport-relative sizing (e.g. `h-full` against a flex/grid ancestor sized from real available viewport height, or `dvh`-based) so the desktop fills available height with no leftover box on any screen size, and the `aside`/`main` grid columns no longer mismatch.
3. Fix the window cascade so a 4th+ opened window does not exactly overlap an earlier one (extend the offset pattern beyond `% 3`, e.g. `% N` for a larger N or wrap-and-nudge), and make sure no open window can render under the taskbar or bleed outside the visible desktop surface at any supported viewport — the desktop surface should clip/contain windows without ever leaving a window partly unreachable.
4. Fix mobile sizing: at 375×812 the tool must have zero horizontal overflow (`clientWidth === scrollWidth`) and windows must be able to be fully seen/dismissed without unreachable off-screen chrome.
5. Suppress the "Try another approach" / failed-action toast whenever the active scenario is already in `completedScenarioIds` — a completed scenario should never show a "try again" message; either disable further `perform_scenario_step` UI interaction for that scenario once complete, or swallow the toast for rejected actions in that state (student-facing copy must never contradict itself).
6. Fix taskbar/icon/window alignment so icons, the taskbar, and window chrome align on a consistent grid at both viewports (no icons overlapping taskbar, no icon drift versus window title bars).
7. Improve ticket panel (`aside`, `RemoteDesktopTool.tsx:218-351`) readability — verify sufficient contrast/spacing for ticket description, hints, and completion summary text against the existing dark theme tokens used elsewhere in the app (do not invent new colors, reuse `packages/ui`/existing Tailwind tokens).

**Tests**: extend/adjust any existing Remote Desktop Playwright coverage plus manual Playwright checks at 1440×1000 and 375×812: open 4+ windows and confirm none exactly overlap or clip under the taskbar; complete a scenario and confirm no "Try another approach" toast can appear afterward for that scenario; confirm zero horizontal scroll at 375×812; confirm no visible empty box below the desktop at both viewports.

**Completion checklist**:
- [ ] No white box below the desktop at any tested viewport.
- [ ] Desktop fills available height; simulator is not artificially small on large monitors.
- [ ] No excessive empty/black space around the tool.
- [ ] Zero horizontal overflow at 375×812; all controls reachable on mobile.
- [ ] "Try another approach" never renders while "Solution complete" is showing for the same scenario.
- [ ] Application windows never extend outside the desktop surface or render under the taskbar.
- [ ] Taskbar, icons, and windows are visually aligned.
- [ ] Ticket panel text is readable (contrast/spacing) at both viewports.

**Must not**: change any `remote_desktop.*` action type, payload shape, overlay field, or scenario fixture data; must not change `MainContainer`'s default max-width for other tools; must not alter grading/completion logic, only its visual presentation.

---

## Phase 15 — Remote Desktop Terminal application

**Goal**: add a real Terminal/Command Prompt app to the simulated desktop with deterministic, scenario-aware command output. No real OS commands are ever executed — every command's output is computed server-side from the attempt's current `RemoteDesktopOverlay` state.

**Grounding**: today there are 9 inline app cases in `AppContent` (`RemoteDesktopTool.tsx:1174-1318`) including a `system` case (~1269-1279, icon `IconTerminal2`) that is just 3 buttons, not a command-line UI. The action model is a single generic `remote_desktop.perform_scenario_step` (`actions/index.ts` ~292, validated in `apply-action.ts:784-808`) that only supports discrete labeled buttons, not free-text command input. `RemoteDesktopOverlay` (`types.ts:160-173`) has no field for terminal history.

**Files**: `apps/web/components/RemoteDesktopTool.tsx` (new `terminal` appId + `TerminalWindow` component: scrollback + input line, styled as a monospace command prompt), `packages/simulation-engine/src/actions/index.ts` (new action type `remote_desktop.run_terminal_command`, payload `{ assetTag: string; command: string }`), `packages/simulation-engine/src/apply-action.ts` (new deterministic command resolver + validation branch), `packages/simulation-engine/src/types.ts` (add `terminalHistory: { command: string; output: string[]; timestamp: string }[]` to `RemoteDesktopOverlay`), `packages/simulation-engine/src/serialize.ts` (extend `isRemoteDesktopOverlay` validation and the `restoreAttempt` back-fill block at ~519-554 to default `terminalHistory: []` for older saved attempts), `packages/shared/src/remote-desktop-fixtures.ts` (per-scenario deterministic command output table).

**Command set and behavior** (all output is plain text lines, computed from the current overlay + scenario, never from a real shell):
- `ipconfig` — short adapter summary (IPv4 address, subnet, default gateway) reflecting current network/VPN state.
- `ipconfig /all` — full adapter detail including DNS servers currently configured (this is the field the DNS ticket's fix changes).
- `ping <host>` — succeeds/fails based on overlay `networkStatus`; must succeed by IP even when DNS is broken (for the DNS ticket, `ping <ip>` succeeds, `ping <hostname>` fails until DNS is fixed).
- `nslookup <host>` — fails with a resolution-timeout-style message while the DNS misconfiguration is present, succeeds after the fix.
- `tracert <host>` — a short deterministic hop list consistent with `ping`'s success/fail state.
- `net use` — lists mapped drives and their status (`OK` / `Disconnected` / `Unavailable`) reflecting the overlay's drive-mapping state; for the mapped-drive ticket, shows Disconnected until repaired.
- `whoami` — the current simulated user for that workstation.
- `hostname` — the workstation's asset tag / hostname.
- `gpupdate` — deterministic "Updating policy..." + success/no-op message; does not itself change state, just reports.
- `systeminfo` — short fixed system summary block (OS, boot time, etc. — static per workstation).
- `tasklist` — a short fixed list of running processes; for the service ticket, reflect whether the relevant service's process is present.
- `sc query <service>` — reports the named service's state (`RUNNING` / `STOPPED`) from a new `serviceStates` lookup already present on the overlay type (`types.ts:160-173` lists `serviceStates`; confirm its exact current shape before extending — reuse it, don't duplicate); for the service ticket, shows `STOPPED` until the student restarts it.
- `net start <service>` / `net stop <service>` — mutates that same `serviceStates` entry (this is a second way, alongside any Services app from Phase 17, to fix the service ticket — both must stay consistent with each other).
- `cls` — clears the visible scrollback (client-only, no event needs to be logged for a pure clear).
- `help` — lists the supported commands.
- Anything unrecognized — a deterministic "'<input>' is not recognized..." style message (do not silently ignore).

**Tests**: Vitest in `packages/simulation-engine` — one test per command against at least the VPN, DNS, and service-failure scenario states (happy path + the "still broken" path before the fix), plus an unrecognized-command test and a `net start`/`net stop` state-mutation test. Playwright: open Terminal, run `ipconfig /all` and `nslookup` before and after fixing the DNS ticket's misconfiguration, confirm output changes accordingly; confirm `cls` clears scrollback without an extra event/rerender glitch.

**Completion checklist**:
- [ ] All 14 listed commands implemented deterministically, no real process execution anywhere (grep the diff for `exec`/`spawn`/`child_process` — none should appear).
- [ ] Command output for `ping`/`nslookup`/`net use`/`sc query` correctly reflects current scenario/overlay state and changes after the relevant fix action.
- [ ] `net start`/`net stop` and the Phase 17 Services app (once built) read/write the same `serviceStates` data — no divergent duplicate state.
- [ ] Terminal history persists through the existing Attempt save/restore path (confirm via refresh: history survives, matching the rest of the tool's persistence model).
- [ ] Unrecognized commands return a clear, deterministic rejection message rather than being silently ignored.

**Must not**: execute any real shell/process command; must not let terminal commands bypass `apply-action.ts`'s existing connection-state/permission guards (Terminal actions must require `connected`, same as other app actions per `remoteDesktopRejectReason` ~772-781).

---

## Phase 16 — File Explorer overhaul

**Goal**: replace the current single-panel `explorer` app case (`RemoteDesktopTool.tsx:1208-1224`, currently just 4 flat action buttons: `explorer.verify-share`, `explorer.repair-mapping`, `explorer.remove-share`, `explorer.check-free-space`) with a real navigable File Explorer whose state is driven by, and stays consistent with, Terminal's `net use` output and the VPN/Directory state.

**Files**: `apps/web/components/RemoteDesktopTool.tsx` (new `FileExplorerWindow` component: This PC / Local disk / Network drives tree + folder/file list pane), `packages/simulation-engine/src/actions/index.ts` (extend or replace the flat `explorer.*` step actions with explicit navigation/action types: `remote_desktop.explorer_navigate` `{assetTag, path}`, `remote_desktop.explorer_reconnect_drive` `{assetTag, driveLetter}`, `remote_desktop.explorer_refresh` `{assetTag}`), `packages/simulation-engine/src/apply-action.ts` (validation + state transitions for navigation/permission-error/network-path-error/reconnect/refresh), `packages/simulation-engine/src/types.ts` (overlay fields for current explorer path + per-drive connection state, reusing/aligning with Terminal's `net use` drive-status data from Phase 15 — one source of truth for drive state, read by both Terminal and File Explorer), `packages/shared/src/remote-desktop-fixtures.ts` (per-scenario folder/file tree + disk-space figures).

**Required capabilities** (scope this to what the ticket scenarios actually need — a small fixed tree per workstation, not a general filesystem):
- This PC view listing Local disk (C:) and any mapped network drives with their current status.
- Navigating into Local disk and a couple of representative folders/files (enough to feel real, not exhaustive).
- Opening a mapped network drive: succeeds when the drive is connected/reachable, shows a permission-error state when access is denied by scenario design, shows a network-path-error state when the underlying share/VPN path is unreachable (mapped-drive and VPN tickets both exercise this).
- "Reconnect" action on a disconnected/errored mapped drive — must produce the same resulting state whether triggered from File Explorer's reconnect action or from fixing VPN/Terminal state that the drive depends on (single source of truth, no drift).
- Disk-space info (used/free) shown per drive, static per workstation fixture.
- Refresh action that re-reads current overlay state (useful after fixing VPN/service state elsewhere so File Explorer visibly updates without a full page reload).

**Tests**: Vitest for each new explorer action's happy/permission-error/network-path-error/reconnect paths; a specific test asserting File Explorer and Terminal's `net use` report the *same* drive status for a given overlay state (no divergence); Playwright: for the VPN ticket, confirm the mapped drive shows a network-path error before VPN connects and succeeds after; for the mapped-drive ticket, confirm reconnect actually clears the disconnected state and persists through refresh.

**Completion checklist**:
- [ ] File Explorer's drive/connection state and Terminal's `net use` output never disagree for the same attempt state.
- [ ] Permission-error and network-path-error are visually and textually distinct states (not the same generic error).
- [ ] Reconnecting a drive from File Explorer produces the same overlay state as fixing the underlying VPN/network issue that caused the disconnect.
- [ ] Disk-space info renders per drive.
- [ ] Refresh re-reads current state without requiring a full page reload.

**Must not**: build a general-purpose virtual filesystem beyond what the three target tickets and a plausible "This PC" baseline require; must not duplicate drive-status state separately from Phase 15's Terminal/`net use` state — extend the same overlay fields.

---

## Phase 17 — VPN, Settings, Services, System Update, Chat/Mail, Browser depth

**Goal**: turn the remaining shallow one-button "apps" into believable multi-step tools, and add the missing Services app, per the spec's "avoid simple click-one-button-and-solved interactions" requirement.

**Current shallow state** (`RemoteDesktopTool.tsx` `AppContent`, ~1174-1318): `vpn` (1193-1207, one `vpn.connect` action only, no disconnect/error/log state), `settings` (1225-1240, two flat buttons, no tabs), `browser` (1241-1256, two flat retry buttons, no navigation), `updates` (1257-1268, one install button, no pending-update/restart state), `chat` (1280-1291, one confirm button — separate from and unrelated to the real `CompanyChatTool` component), `mail` (1292-1304, one review-alert button). There is no `services` app at all.

**Files**: `apps/web/components/RemoteDesktopTool.tsx` (rework each app case into a small dedicated component per app, replacing the inline `switch` cases with `VpnClientWindow`, `SettingsWindow` (tabbed: Network/Storage/Applications/Updates), `ServicesWindow` (new), `SystemUpdateWindow`, `ChatMailWindow`, `BrowserWindow`), `packages/simulation-engine/src/actions/index.ts` (new/extended action types per app below), `packages/simulation-engine/src/apply-action.ts`, `packages/simulation-engine/src/types.ts` (overlay fields: VPN connection status/log, services list with per-service state, pending-update/restart flag), `packages/shared/src/remote-desktop-fixtures.ts`.

**Per-app requirements**:
- **VPN Client**: explicit connect/disconnect actions (not just connect), a status indicator (Connected/Disconnected/Connecting/Error), an error state with a plausible message when connecting fails for scenario reasons, and a short connection log (timestamped entries) — the VPN ticket's core surface.
- **Settings**: tabbed UI — Network (adapter/DNS settings; this is where the DNS ticket's fix actually happens — changing a DNS server value, not a single "repair network" button), Storage (disk usage summary, consistent with File Explorer's disk-space info from Phase 16), Applications (installed apps list, read-only is fine), Updates (surface the same pending-update state as the System Update app — one source of truth, not two).
- **Services**: new app — list of simulated Windows services with a status column (Running/Stopped), and a Restart/Start/Stop action per selected service; must read/write the *same* `serviceStates` overlay data Terminal's `sc query`/`net start`/`net stop` (Phase 15) already uses — this is the primary surface for the service-failure ticket (e.g. Print Spooler).
- **System Update**: a pending-update state with an explicit "Install" step and a subsequent "restart required" state before the update is considered applied (not one click = done).
- **Chat/Mail**: extend to real requester communication tied to the active ticket — should be able to reference/complement (not duplicate) the existing `CompanyChatTool` component's data model rather than maintaining a second unrelated chat concept inside Remote Desktop.
- **Browser**: keep scope to reaching in-app Documentation articles relevant to the current ticket (link into the existing `DocumentationTool`/documentation fixtures) rather than building general web navigation.

**Tests**: Vitest per new action type (VPN connect/disconnect/error, service restart, update install/restart-required, settings DNS change); Playwright: for the VPN ticket, connect VPN and confirm the connection log and status update, then confirm File Explorer's mapped drive becomes reachable; for the service ticket, restart the correct service via Services and confirm both the Services app and Terminal's `sc query` reflect Running afterward.

**Completion checklist**:
- [ ] VPN has real connect/disconnect/error/log states, not a single boolean button.
- [ ] Settings' Network tab is where DNS is actually changed for the DNS ticket (not a generic "repair" button).
- [ ] Services app exists and shares state with Terminal's service commands.
- [ ] System Update has a distinct pending → installing → restart-required → applied sequence.
- [ ] No app in this phase can complete its relevant ticket objective via a single undifferentiated click with no intermediate state.

**Must not**: implement real external web browsing in Browser; must not create a second, divergent chat data model separate from `CompanyChatTool`'s existing structures if it can reasonably be reused.

---

## Phase 18 — Three complete tickets, learning modes, and completion grading

**Goal**: implement Ticket A (VPN + shared drive), Ticket B (DNS configuration failure), and Ticket C (Windows service failure) as full diagnose → fix → verify → note → close workflows, add the three learning modes, and upgrade the post-completion summary — building on Phases 14-17's Terminal/File Explorer/VPN/Services depth.

**Grounding**: today scenario objectives are a flat set (`requiredSteps`/`optionalSteps`/`incorrectSteps` in `remote-desktop-fixtures.ts`, validated as one undifferentiated list in `apply-action.ts:784-808, 900-913`) with no diagnose/fix/verify/note/close phase distinction, and closing a ticket happens entirely outside the scenario model via `CompletionSummary`'s hardcoded `resolutionNote: scenario.explanation` (`RemoteDesktopTool.tsx:524-526`) — students never write their own note today. The existing `vpn-shared-drive` scenario (`remote-desktop-fixtures.ts:167-198`) is Ticket A's starting point and needs upgrading, not replacing. **No DNS scenario exists at all today** — Ticket B is entirely new. **No service-failure scenario tied to a Services app exists** — Ticket C is entirely new (build it against Phase 17's new Services app). Only a flat boolean `trainingMode` exists today (`TicketSessionProvider.tsx:199`, `actions/index.ts:284-287`) — no Guided/Practice/Assessment distinction.

**Files**: `packages/shared/src/remote-desktop-fixtures.ts` (upgrade `vpn-shared-drive`; add new `dns-configuration-failure` and `service-failure` scenarios, each modeling explicit diagnose/fix/verify sub-goals plus a required internal note and close step), `packages/simulation-engine/src/types.ts` (extend the scenario/objective and overlay types to track phase completion — diagnosed/fixed/verified/noted/closed — rather than one flat step set; add a `learningMode: 'guided' | 'practice' | 'assessment'` field replacing/extending the boolean `trainingMode`, keeping the old field or migrating it cleanly via `serialize.ts`'s back-fill block), `packages/simulation-engine/src/apply-action.ts` (grading logic requiring diagnosis evidence + correct fix + verification action + a real student-authored note before allowing close, per-mode hint gating), `packages/simulation-engine/src/actions/index.ts` (a `remote_desktop.add_internal_note` action carrying the student's own note text, replacing the hardcoded `scenario.explanation` close path), `apps/web/components/RemoteDesktopTool.tsx` (`CompletionSummary` upgrade — root cause, fix performed, why it worked, evidence gathered, missed useful actions, hints used, final score/feedback; note-entry UI before close is enabled; mode-aware hint UI), `apps/web/lib/remote-desktop-learning.ts` (mode-aware hint/feedback helpers), `packages/shared/src/ticket-fixtures.ts` (fix the existing `suggestedTools` gap noted below, and add/adjust ticket entries for the two new scenarios).

**Ticket A — VPN and shared drive** (upgrade existing `vpn-shared-drive`/INC2406): read complaint → test network access (Terminal `ping`/File Explorer network-path error) → inspect VPN state (VPN Client) → connect VPN → verify the mapped drive (File Explorer, now reachable) → add an internal note (own words, not autofilled) → close.

**Ticket B — DNS configuration failure** (new scenario): use `ipconfig`, `ping` (by IP, succeeds), and `nslookup`/`ping` by hostname (fails) to diagnose → correct the DNS setting in Settings' Network tab (Phase 17) → verify name resolution (`nslookup`/`ping` by hostname now succeeds) → add a note → close.

**Ticket C — Windows service failure** (new scenario, e.g. Print Spooler): gather evidence (Terminal `sc query`/`tasklist` or Services app showing Stopped, plus a plausible symptom like a failed print/app action) → inspect service status → restart the correct service (Services app or Terminal `net start`, Phase 15/17 — both valid, both must be recognized) → verify the dependent application now works → add a note → close.

**Grading rule** (explicit, per spec): grade final system state and verification evidence gathered during the attempt, not one exact click order — a scenario should accept any valid path through diagnose → fix → verify as long as the required evidence-gathering and fix actions all occurred and the internal note was written, not a single hardcoded sequence. Do not accidentally allow close without a real verification action or without the student's own note text.

**Learning modes**:
- **Guided**: hints surface progressively and proactively with helpful feedback on incorrect actions.
- **Practice**: hints available on request, normal (non-punitive) feedback on incorrect actions.
- **Assessment**: no hints available until after completion; feedback on incorrect actions is minimal/neutral, not instructive.
- In every mode, students must never see internal objective definitions, action keys, or the required-action list — this is already enforced for the general case via the existing mentor-only `MentorScenarioReview` gate (`RemoteDesktopTool.tsx:347-349`); confirm it still holds for the new phase-tracked objective data.

**Ticket completion rule** (explicit, per spec) — a ticket is only completable with all of: correct diagnosis evidence, correct fix, a real verification step, a real internal note (student-authored text, minimum non-trivial length), and explicit ticket closure. After completion, show: root cause, fix performed, why it worked, evidence gathered (a list of the qualifying actions the student actually took), missed useful actions (optional actions available but not taken — informational, not scored as a penalty unless the existing scoring model already does that), hints used (count/list), and final score/feedback.

**Data-wiring fix** (found during grounding, fold into this phase): `packages/shared/src/ticket-fixtures.ts` — INC2401, INC2402, and INC2405's `suggestedTools` arrays are missing `'remote-desktop'` even though they have wired Remote Desktop scenarios; add it so the ticket UI correctly suggests the tool.

**Tests**: Vitest — full diagnose→fix→verify→note→close path for each of the 3 tickets, plus at least one incorrect-order/incomplete-evidence rejection test per ticket (confirming grading is evidence-based, not order-locked, but still can't be gamed by closing early); per-mode hint-gating tests (Assessment mode blocks hints pre-completion, Guided surfaces them proactively); a regression test confirming the existing `pdf-export-update`, `profile-storage`, `network-configuration`, `mapped-drive-permissions` scenarios still function unchanged. Playwright: complete all 3 tickets end-to-end at 1440×1000, confirm the completion summary shows every required field, confirm an attempt cannot close without a written note, confirm refresh mid-ticket preserves diagnose/fix/verify progress.

**Completion checklist**:
- [ ] All 3 tickets completable start-to-finish through their full diagnose→fix→verify→note→close flow.
- [ ] Grading only requires correct final state + verification evidence, not one exact click order (explicit test proves an alternate valid order also passes).
- [ ] Incorrect/incomplete actions cannot accidentally complete a ticket (explicit rejection tests per ticket).
- [ ] A ticket cannot close without a real student-authored internal note.
- [ ] Guided/Practice/Assessment modes behave distinctly per the spec's hint-availability rules.
- [ ] No mode ever exposes internal objectives, action keys, or the required-action list to the student.
- [ ] Completion summary shows root cause, fix performed, why it worked, evidence gathered, missed useful actions, hints used, and final score/feedback.
- [ ] `ticket-fixtures.ts`'s `suggestedTools` gap for INC2401/INC2402/INC2405 is fixed.
- [ ] The 5 pre-existing Remote Desktop scenarios still pass their existing tests unchanged.

**Must not**: hardcode the resolution note from `scenario.explanation` anymore for these 3 tickets; must not lock grading to one exact action sequence; must not regress existing scenario behavior, refresh persistence, or Nexus auth/progress sync.
