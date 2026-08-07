# Product Map

Source of truth for every page, tool, and state to recreate. Grounded in captured evidence — every section names the exact files Codex must inspect before building it. Evidence lives in (relative to `service-desk-app/`):

- `../artifacts/screenshots/desktop/*.png`, `../artifacts/screenshots/mobile/*.png` — visual reference
- `../artifacts/html/*.html` — rendered DOM/CSS reference
- `../artifacts/metadata/*.json` — headings/buttons/links/forms/dialogs/viewport per state
- `../artifacts/state-manifest.json` — state name → route/URL → size-label map (the authoritative route list)
- `../website-capture/crawlee-servicedesk/output/{text,html,json,screenshots}/` — broader crawl (388 states, 51 routes), useful for secondary/edge states not in the curated `artifacts/` set
- `../REPORT.md` — narrative summary of the whole capture pass

Do not use `../website-capture/ai-website-cloner/` as ground truth for layout or IA — it is an unexecuted scaffold with one hand-written mockup page whose 3-column always-visible sidebar layout is **not** supported by evidence and contradicts the real Tools-panel pattern documented below. Its ticket-copy fidelity (pulling real strings from crawl text) is the only part worth imitating as a *technique*.

Recreate structure and behavior only. All copy (ticket titles, employee names, articles, company name, branding) must be wholly original — see `../REPORT.md` § "Legal original-code recreation plan".

---

## 0. Navigation model

The real app is a **React/Vite SPA using hash-based client routing**, not path-based routing, for everything past the authenticated shell. Confirmed via `../artifacts/state-manifest.json`:

| Hash route | Tool/page |
|---|---|
| `/` (authenticated) | Dashboard / Ticket Queue |
| `/#ticket` or `/#ticket/{INC-ID}` | Ticket workspace |
| `/#ad` | Directory (Active Directory simulator) |
| `/#serverroom` | Server Room |
| `/#remotedesktop` | Remote Desktop |
| `/#deployment` | Computer Deployment |
| `/#pcshelf` | PC Shelf |
| `/#docs` | Documentation / Knowledge Base |
| `/#assets` | Asset Management |
| `/#shipmanager` | Ship Manager |
| `/#analytics` | Analytics (under Profile) |
| `/#achievements` | Achievements (under Profile) |
| `/#pasttickets` | Past Tickets (under Profile) |

True browser (path-based) routes exist only for **public, unauthenticated marketing pages**: `/`, `/login`, `/testimonials`, `/teachers`, `/blog`, `/blog/posts/...`. Recommendation for the rebuild: keep this split — Next.js path routes for public marketing, and a client-side router (React Router or a simple state machine) for the authenticated app shell, mirroring the original's SPA-behind-one-shell architecture. This also matches the shared-simulation-state requirement: one mounted shell, tools swap in a `<main>` outlet without a full navigation/reload, so in-memory + optimistic state stays coherent between tool switches.

Tools are **not** a persistent sidebar. They live behind a **"TOOLS" button in the header that opens a dialog/panel** grouping tools under three category headers — confirmed by `../artifacts/metadata/tools-menu.json`:

```
TOOLS
  INFRASTRUCTURE
    👥 Directory
    🖧 Server Room
    🖥️ Remote Desktop
    💿 Computer Deployment
    🗄️ PC Shelf
  KNOWLEDGE
    📚 Documentation
  MANAGEMENT
    📦 Asset Management
    🚚 Ship Manager
```
Evidence: `../artifacts/screenshots/desktop/tools-menu.png`, `../artifacts/html/tools-menu.html`, `../artifacts/metadata/tools-menu.json`. This is the #1 correction to make versus the AI clone, whose `page.tsx` renders these as a flat always-visible sidebar list (missing PC Shelf entirely) — do not build it that way.

---

## 1. Global chrome (present on every authenticated page)

**Header** (persistent, confirmed across every non-public metadata file):
- Left: app wordmark/logo (small, links to Dashboard) + **TOOLS** button (opens the Tools panel above).
- Center-right cluster of icon+label buttons: **CALL USED / Resets 12 AM** (or "0 CALLS LEFT · RESETS IN Xh Ym" depending on quota state), **VOICEMAILS**, **MOCK INTERVIEW**, **COMPANY CHAT** (`aria-label="Company Chat"`), **JOIN CLASS** (`aria-label="Join Class"`), **LEADERBOARD** (`aria-label="Leaderboard"`).
- Points cluster: **`{n}` POINTS**, **`{n} TICKETS LEFT · RESETS IN Xh Ym`** (`aria-label="Tickets left"`), **`{n} CALLS LEFT · RESETS IN Xh Ym`** (`aria-label="Calls left"`).
- Right: **GET PRO** button, then the profile-menu trigger button showing avatar emoji + display name + rank label (e.g. "🦸‍♂️ SHADOW ROOKIE").
- On tool/detail pages a **DASHBOARD** button additionally appears (breadcrumb-style return-home). On the ticket workspace this becomes **BACK TO QUEUE**.

**Footer** (public/dashboard pages): legal link row — Blog, Privacy Policy, Terms of Service, Disclaimer, Refund Policy, Contact us, Leave a review (Trustpilot, external), Become an affiliate (external, Rewardful), plus `© {year} {ProductName}™ · v{version}`.

**Theming**: dark theme is default; a `data-theme` attribute plus an inline pre-paint script reads a persisted preference and swaps `light`/`dark` before first paint (avoids FOUC). Rebuild this exact pattern — see `DESIGN_SYSTEM.md`.

**Responsive scaling**: header/tool chrome uses CSS custom properties (`--app-vh`, `--app-zoom`) for a deliberate ~0.75 zoom-out compensation on phone widths rather than element-by-element breakpoint rewrites. `../artifacts/metadata/mobile-overflow.json` confirms `clientWidth === scrollWidth === 375` at 375×812 — no horizontal overflow. Reproduce the same "scale the whole shell down" strategy rather than rebuilding mobile layouts from scratch per page.

Evidence: any `../artifacts/html/*.html` file (DOM structure is consistent), `../artifacts/screenshots/mobile/mobile-authenticated-queue.png`.

---

## 2. Public marketing pages

### 2.1 Landing page — `/`

**Purpose**: unauthenticated marketing/conversion page; becomes the Dashboard once authenticated (same path, different rendered tree based on auth state).

**Layout**: long scrolling single page (`scrollHeight: 2737` vs viewport 1000 — this is the one page that scrolls past viewport height; every authenticated app-shell page caps near `scrollHeight: 1000`).

**Sections** (from `../artifacts/metadata/public-home.json`): H1 hero ("THE FLIGHT SIMULATOR FOR HELPDESK. BEFORE YOUR FIRST DAY." — write an original equivalent tagline), "TRY IT YOURSELF" interactive demo with tabbed tool previews (Ticket Queue / Directory / Remote Desktop / Server Room demo tabs), "TICKET QUEUE" section showing 3 sample demo tickets with title/requester/priority, "WHAT YOU'LL PRACTICE" feature-card grid (Solve Tickets Like Day One, Handle Calls Without Freezing, Team Chat, Server Room, Master Directory, Remote Into Workstations, Asset Management, Documentation Station, Mock Interview — 9 cards).

**Header (public variant)**: language switcher (expandable), theme toggle, Log In, Sign Up, Get Started buttons.

**Buttons/links**: Log In, Sign Up, Get Started, demo tool tabs, footer legal links, `/testimonials`, `/teachers`, `/blog` nav links, Trustpilot review link, Discord link, LinkedIn.

**States**: public (logged out, this section) vs. authenticated (renders Dashboard instead — see §3). A `<noscript>` block serves static SEO copy for non-JS crawlers — include one for SEO parity.

Evidence: `../artifacts/screenshots/desktop/public-home.png`, `../artifacts/html/public-home.html`, `../artifacts/metadata/public-home.json`, `../artifacts/cdp/public-home-dom-snapshot.json`, `../artifacts/cdp/public-home-performance.json`.

### 2.2 Login — `/login`

**Purpose**: email/password auth entry point.

**Form**: required email input (native browser email-type validation — invalid email shows native type-mismatch UI, not a custom error), required password input, "Remember me" checkbox, password-recovery link, Google OAuth login button.

**States**: empty (`login-empty.png`), browser-native validation triggered (`login-browser-validation.png`), field-level validation failure (`login-validation.json`).

Evidence: `../artifacts/screenshots/desktop/login-empty.png`, `login-browser-validation.png`, `../artifacts/metadata/login-empty.json`, `login-browser-validation.json`, `login-validation.json`, `../artifacts/cdp/login-empty-dom-snapshot.json`, `login-empty-performance.json`, `login-browser-validation-performance.json`.

### 2.3 `/testimonials`, `/teachers`, `/blog`, `/blog/posts/...`

Standard public marketing/content pages. `/teachers` is the classroom-product pitch page (informs Classroom foundation copy/positioning). `/blog/posts/...` articles are the "What is X?" contextual help links that appear from nearly every tool (see §6+ — every tool has a "What is {tool}?" link opening a themed blog post in a new tab). Build these as a thin original blog with one article per tool concept (Active Directory, server room, remote desktop, computer deployment, PC shelf/asset management, documentation/knowledge base, shipping, ticket queue, Teams-style chat, help-desk metrics) — do not invent more scope than that; they are secondary to the app itself.

Evidence: `../website-capture/crawlee-servicedesk/output/text/` and `output/html/` (broader crawl covers these routes in more depth than `artifacts/`).

---

## 3. Dashboard / Ticket Queue — `/` (authenticated)

**Purpose**: home screen after login; shows the student's assigned ticket plus the open incident pool.

**Layout**: stacked `<section class="sd-card">` blocks in a single scrollable column (max-width centered), each card = icon + `<h2>` title + count in `.sd-card-header__meta`, then a `divide-y` list of rows.

**Components**:
- **MY QUEUE `{n}`** card → "ASSIGNED TO YOU" list. In the captured session, exactly one active assigned ticket is allowed at a time (REPORT.md confirms "Only one active assigned ticket was shown"). Each row: ticket title, requester name, priority badge. Row is a `<button aria-label="Open ticket {title}">` → opens Ticket Workspace.
- **TICKET QUEUE** card header with "What is a ticket queue?" learn-link → **INCIDENTS `{n} OPEN`** sub-list of unassigned tickets, same row shape, no requester "assigned" state.
- **TEAM CHAT** card (only on fully-empty-queue / first-look states) → RECENT / CONTACTS / PINNED (n) tabs, empty state copy "No recent chats — Select a contact to start chatting."
- Priority badge colors: Critical = red-500, High = red-400, Medium = orange-400 (see DESIGN_SYSTEM.md for exact tokens) — Low presumably a 4th tier (amber/yellow) per Analytics' priority breakdown showing Low as a category even though not observed on the queue itself.

**Empty state**: not directly captured with zero incidents, but the "My Queue" card conditionally renders only when a ticket is assigned (absent otherwise) — build both card presence branches.

**Actions**: click a queue/incident row → assign + open Ticket Workspace. Header "Dismiss" button dismisses a transient toast/banner (seen in metadata as an unlabeled `aria-label="Dismiss"` button near the header — likely a first-load tip banner).

**Mobile**: `mobile-authenticated-queue.png` shows the same card stack condensed to full width, no horizontal scroll.

**Connections**: opening a ticket reads/writes the shared simulation world state (directory, devices, deployment, shipping) that Directory/Server Room/Remote Desktop/Deployment/PC Shelf/Ship Manager/Company Chat all read and mutate — this is the central integration point; see `ARCHITECTURE.md` § Simulation Foundation.

Evidence: `../artifacts/screenshots/desktop/authenticated-queue.png`, `../artifacts/screenshots/mobile/mobile-authenticated-queue.png`, `../artifacts/html/authenticated-queue.html`, `../artifacts/metadata/authenticated-queue.json`, `mobile-authenticated-queue.json`, `mobile-overflow.json`, `../artifacts/cdp/authenticated-queue-dom-snapshot.json`, `authenticated-queue-performance.json`, `mobile-authenticated-queue-dom-snapshot.json`, `mobile-authenticated-queue-performance.json`.

---

## 4. Ticket workspace — `/#ticket` or `/#ticket/{INC-ID}`

**Purpose**: the core gameplay loop — investigate, act, communicate, close.

**Layout**: full-width workspace with header row (ticket title as H2), then structured incident detail, then a progressive "How to resolve this" (H4) reveal panel.

**Header actions** (from `ticket-assigned-baseline.json`): **BACK TO QUEUE**, **SPLIT SCREEN VIEW** (opens tool alongside ticket — key cross-tool integration control), **OPTIONS** (`aria-expanded` dropdown — likely Abandon/Escalate, confirmed by AI-clone evidence referencing an `AbandonModal`/`AssignmentsModal` bundle), **UNASSIGN**.

**Ticket fields** (from `../REPORT.md` + `complete-ticket-workflow.json`'s `ticket-after-replacement-shipment` entry): incident ID (`INC####` format), title, requester identity, department/location/contact, description, user-reported troubleshooting bullets, business impact, priority (Critical/High/Medium/Low), category/subcategory, SLA, point value, difficulty, solution type, target entity, solution steps (hidden until revealed), explanation, learning points.

**Help/reveal mechanic**: **"I DON'T KNOW HOW TO FIX THIS"** button and **"REVEAL NEXT STEP (n/7)"** button progressively disclose a ticket-specific guided action sequence (7 steps observed for this incident type), each captured as `ticket-help-step-2.png` … `step-7.png`. This must be modeled server-side per scenario (see `DATABASE.md` § ScenarioObjective/Hint) so hints can be scored/penalized and are never shipped to the client pre-revealed.

**Cross-tool integration example** (fully captured, `complete-ticket-workflow.json` + `../playwright/complete-ticket.mjs`): open ticket → Company Chat with the requester (confirm device/cable/address) → open Computer Deployment → Server Imaging → complete the 11-step deployment → provisioned PC lands on PC Shelf → open Ship Manager → select requester + provisioned PC → ship → back in the ticket, confirm delivery via chat → Close Ticket.

**Close flow**: optional resolution notes textarea; closing an **unresolved** ticket shows a warning modal with the **exact point penalty** before confirming (captured: -17 points, 83→66, ticket-attempt count consumed, replacement queue incident generated). Evidence: `ticket-close-review.png`, `ticket-post-close-scoring-or-quiz.png`.

**States**: baseline/assigned (`ticket-assigned-baseline.png`), help-open (`ticket-help-open.png`), help-step-2..7, chat-diagnosis-and-address (`ticket-chat-diagnosis-and-address.png`), chat-delivery-confirmation, post-replacement-shipment, close-review, post-close-scoring, and the `workflow-failure.png` error/incorrect-path state.

Evidence: `../artifacts/screenshots/desktop/ticket-*.png`, `deployment-*.png`, `shipping-*.png`, `replacement-shipped.png`, `workflow-failure.png`; `../artifacts/html/ticket-*.html`; `../artifacts/metadata/ticket-assigned-baseline.json`, `ticket-help-open.json`, `ticket-help-step-{2..7}.json`, `complete-ticket-workflow.json` (richest single source — 14-entry full workflow with exact copy per state); `../artifacts/cdp/ticket-assigned-baseline-dom-snapshot.json`, `ticket-help-step-{2..7}-performance.json`; `../playwright/complete-ticket.mjs` (exact recorded interaction sequence, directly translatable to a Playwright e2e spec and to the simulation-engine's step/action schema).

---

## 5. Tools panel (modal/dialog, not a page)

Covered in §0. Additional detail: `../artifacts/metadata/tools-menu.json` captures it as a `dialogs[]` entry over the dashboard, with a **Close** icon button (`aria-label="Close"`) — i.e. implemented as an overlay dialog, not a route change. Rebuild as a modal/sheet component, keyboard-dismissible (Esc) and click-outside-dismissible, trapping focus per WCAG dialog pattern.

Evidence: `../artifacts/screenshots/desktop/tools-menu.png`, `../artifacts/html/tools-menu.html`, `../artifacts/metadata/tools-menu.json`, `../artifacts/cdp/tools-menu-performance.json`.

---

## 6. Directory — `/#ad`

**Purpose**: Active Directory simulator — user/identity administration.

**Layout**: `sd-panel-frame--ad` variant panel inside `sd-screen`, back button "← Dashboard", "What is Active Directory?" learn-link, panel header with icon+title, then a scrollable **83-user directory list** (`Name / username`, e.g. "Richard Harrison / rharrison").

**Actions**: a **"New User"** submit button (`aria-label="New User"`) — creates a directory entry. REPORT.md's tool description additionally lists **Profile, Groups, Licenses, Devices, Authentication** sub-panels per user, plus identity verification and password/account operations and group/profile changes — these appear on a per-user detail view not separately captured in `artifacts/`; cross-reference `../website-capture/crawlee-servicedesk/output/` for a directory-detail state before building, and treat the per-user detail panel's exact field set as inferred-but-plausible rather than screenshot-confirmed.

**Search**: `visibleText` implies a filter/search affordance (pattern consistent with Remote Desktop's "Type to find a computer") even though no `<form>` element was captured — Tailwind/React apps here consistently omit semantic `<form>` wrappers, so treat "forms: []" in every metadata file as an artifact of the capture method, not evidence the app lacks real inputs. Build real `<input>`+`<label>` controlled components regardless of what the metadata shows.

**Tables**: implicit list/table of 83 rows — Name, Username. Build as a virtualized/paginated list for performance parity (83 rows is fine unvirtualized, but design for the pattern since Asset Management and Remote Desktop scale identically).

**Empty/loading/error**: not captured distinctly; design a skeleton-row loading state and a "No users match your search" empty state consistent with other tools' empty-state copy pattern (see PC Shelf §9).

**Connections**: unlocking/resetting a user here must be visible in Remote Desktop (login availability), Asset Management (ownership), Company Chat (contactability), and any ticket whose objective references that user — this is the flagship "shared state" example named in the task brief.

Evidence: `../artifacts/screenshots/desktop/tool-directory.png`, `../artifacts/html/tool-directory.html`, `../artifacts/metadata/tool-directory.json`, `../artifacts/cdp/tool-directory-dom-snapshot.json`, `tool-directory-performance.json`.

---

## 7. Server Room — `/#serverroom`

**Purpose**: infrastructure health/topology simulator.

**Layout**: header "SERVER ROOM" + "`{n}/{n}` nodes up" status, "What is a server room?" learn-link, then tab bar **OVERVIEW / TOPOLOGY / DEVICES / SERVERS** (`type="submit"` buttons acting as tab triggers), then an overview grid.

**Overview grid contents** (from `tool-server-room.json`): ISP status card (Metro ISP, online, "12ms latency"), **NETWORK LOAD** percentage gauge ("45% · All clear"), **DEVICES** summary card (`8 / 8 ONLINE`), **SERVERS** summary card (`5 / 5 HEALTHY`), then two lists:
- **DEVICE STATUS** — 8 rows, each a card/button: name, location ("SERVER ROOM A/B", "LOBBY", "CAFETERIA"), status badge (ONLINE). Named devices: Metro ISP (External), Core Router, Floor 1/2/3 Switch, Main Firewall, Lobby WiFi AP, Cafeteria WiFi AP.
- **SERVER STATUS** — 5 rows: DC01 (Domain Controller), DC02 (Domain Controller), FILESERV01 (File Server), MAILSRV01 (Mail Server), PRINT01 (Print Server) — each showing live **CPU %** and **MEMORY %** gauges (25/60, 20/55, 45/70, 55/75, 40/65 in the capture).

**Tabs**: Overview (captured), Topology (likely a visual network diagram — not captured, infer from name: nodes+edges of the above devices/servers), Devices (likely the DEVICE STATUS list as its own full view/table with more per-device detail), Servers (likely the SERVER STATUS list as its own full view/table with more per-server detail, possibly including service-level controls). Build Topology as a simple force-directed or fixed-layout node graph using the same 13-node dataset (8 devices + 5 servers) rather than inventing new nodes.

**Connections**: a server going down (via an incident scenario) should be visible in this panel's status badges and should be the "hidden truth" a ticket's objective/grading checks against. Server/device online-percentage should feed the "13/13 nodes up" header stat live.

Evidence: `../artifacts/screenshots/desktop/tool-server-room.png`, `../artifacts/html/tool-server-room.html`, `../artifacts/metadata/tool-server-room.json`, `../artifacts/cdp/tool-server-room-performance.json`.

---

## 8. Remote Desktop — `/#remotedesktop`

**Purpose**: connect into a simulated employee workstation.

**Layout**: `sd-panel-frame--contained` list view, "What is Remote Desktop?" learn-link, search affordance ("Type to find a computer"), then a scrollable list of **~83 workstations**, one row per employee: `AssetTag / Employee Name / CONNECT` button (e.g. "SD1028 / Richard Harrison / CONNECT").

**Actions**: **CONNECT** (submit button per row) opens a workstation session — REPORT.md notes "simulated workstation applications and settings" once connected; this connected-session view was not separately screenshotted in `artifacts/` — check `../website-capture/crawlee-servicedesk/output/` for a `remotedesktop`-session state before designing it, and if absent, design a minimal original "remote session" surface: a faux desktop chrome with a Settings/Control-Panel-style app and a couple of workstation apps (mail client, browser) whose state can be inspected/changed as part of ticket objectives (e.g. verify a printer driver, check IP config, restart a service).

**Table/list columns**: Asset Tag, Employee Name, Connect action. Same 83-person roster as Directory/Asset Management (shared `DirectoryUser`/`Device` join — see DATABASE.md).

**Connections**: asset tags here must match Asset Management's `ASSET TAG` column and PC Shelf-provisioned devices' `SD####` hostnames exactly — one shared `Device` table keyed by asset tag across all three tools plus Deployment.

Evidence: `../artifacts/screenshots/desktop/tool-remote-desktop.png`, `../artifacts/html/tool-remote-desktop.html`, `../artifacts/metadata/tool-remote-desktop.json`, `../artifacts/cdp/tool-remote-desktop-performance.json`.

---

## 9. Computer Deployment — `/#deployment`

**Purpose**: hands-on hardware/imaging simulator; the deepest interaction surface in the product.

**Layout**: header "COMPUTER DEPLOYMENT" + "About this tool" icon button + "What is computer deployment?" learn-link + a callout banner "NOT SURE WHICH SETUP A PC NEEDS? CHECK THE DOCUMENTATION" (cross-links to Documentation tool), then **3 deployment-method cards**:

| Method | State | Copy |
|---|---|---|
| Server Imaging | **Implemented** — `START` button | "DEPLOY A COMPUTER USING PXE BOOT AND AN IMAGING SERVER TASK SEQUENCE." |
| Manual Domain Enrollment | Under development (disabled/badge) | "Configure a workstation by hand and join it to Directory." |
| Cloud Provisioning | Under development (disabled/badge) | "Provision a device with Cloud Provisioning during first-time setup." |

Plus a **HINTS** toggle with guidance copy: "We recommend disabling hints and using the SOP for the best learning experience." — build hints as an explicit, disableable per-scenario overlay (ties into scoring: REPORT.md implies hint usage should affect score, matching the "hints" field the DB plan already has under ScenarioObjective).

**Server Imaging — the 11-step flow** (fully captured end-to-end in `complete-ticket-workflow.json` and replayable via `../playwright/complete-ticket.mjs`):

1. **Select Desktop Deployment** (device-type choice).
2. **Cable matching** — connect POWER, ETHERNET/RJ-45, DISPLAYPORT, USB KEYBOARD, USB MOUSE to correct ports on a diagram; wrong-port attempts show inline correction (`deployment-incorrect-port.png`), correct state shows `0/5 → 5/5` progress (`deployment-cables-complete.png`).
3. **POST/F12 timing interaction** — a simulated F12 window that "deliberately ignores input during the first 900ms of POST" then accepts F12 within a ~3.5s window to reach the **Boot Option Menu** (`deployment-f12-boot-menu.png`): "Workstation OS Boot Manager (P0: Internal NVMe SSD 500GB)", "PXE Network Boot IPv4", "PXE Network Boot IPv6".
4. **Boot source selection** — wrong paths are Local Disk boot (`deployment-incorrect-local-boot.png`) and IPv6 PXE (`deployment-incorrect-ipv6-boot.png`, with inline validation text: "That boots the existing local OS... Choose the IPv4 network boot."); correct path is IPv4 PXE.
5. **Deployment-share authentication** — Task Sequence Wizard modal; wrong password shows "The password is incorrect." (`deployment-incorrect-share-password.png`).
6. **Hostname/computer-name entry** — "Edit Task Sequence Variable" dialog, variable name `OSDCOMPUTERNAME`, hint text "Use the corporate naming convention, e.g. SD1042, SD1108, SD1205"; validation requires uppercase `SD####` pattern and rejects an asset tag already registered to another device (`deployment-invalid-computer-name.png`).
7. **Automated task-sequence run** — progress UI: "Running: Task Sequence / Running action: Contacting distribution point" (`deployment-task-sequence-running.png`).
8. **Reboot**.
9. **Domain login** — domain `SERVICEDESK-SIMULATOR.LOCAL`; wrong credentials show "The password is incorrect. Try again." (`deployment-incorrect-domain-login.png`); correct login succeeds.
10. **Deployment Successful** screen — shows the new asset tag (e.g. `SD6893 · Server Imaging · Desktop`) with two follow-on CTAs: **"SHIP IT FROM SHIP MANAGER"** and **"GO TO PC SHELF"** (`deployment-complete.png`).
11. **Lands on PC Shelf** as a provisioned, shippable device.

**Design implication**: this entire flow must be a **deterministic, replayable step-state-machine** on the server (validated action sequence with named wrong-path branches, not client-side-only logic) — it is the best evidence in the whole capture for the "deterministic state machine" architecture requirement. Model it as `DeploymentRun` → ordered `DeploymentStep`s, each with an `expectedAction`, a set of `wrongActionResponses` (with copy), and a `completedAt`.

Evidence: `../artifacts/screenshots/desktop/tool-computer-deployment.png`, `deployment-*.png` (10 files), `../artifacts/html/tool-computer-deployment.html`, `deployment-*.html`; `../artifacts/metadata/tool-computer-deployment.json`, `complete-ticket-workflow.json` (has full inline copy for every wrong/correct state); `../artifacts/cdp/tool-computer-deployment-performance.json`; `../playwright/complete-ticket.mjs` (exact selectors/sequence — use as the literal spec for the state machine's transition table).

---

## 10. PC Shelf — `/#pcshelf`

**Purpose**: session-scoped holding area for provisioned-but-unshipped computers.

**Layout**: minimal panel, header "PC SHELF".

**Empty state** (fully captured — this is the only state seen live): "Set up a PC to add it to the shelf. Built computers wait here until you ship one out from the Ship Manager." No table/list rendered while empty.

**Populated state** (inferred from `deployment-complete` → Ship Manager's provisioned-PC dropdown in `complete-ticket-workflow.json`, which lists shelf contents as selectable options: `SD9099, SD8765, SD7654, SD6214, SD6893`): build a card/row per shelf item showing asset tag, deployment method used, and a "Ship" shortcut into Ship Manager with that PC preselected.

**Persistence note**: REPORT.md explicitly flags PC Shelf as **browser-session-scoped** in the real product ("Tool state such as the PC shelf is browser-session scoped"). For the rebuild, do **not** copy that limitation — persist shelf contents server-side per student attempt so state survives refresh, per the task's explicit "the change survives refresh" simulation requirement. This is a deliberate improvement over the original, not a deviation to flag as a gap.

Evidence: `../artifacts/screenshots/desktop/tool-pc-shelf.png`, `../artifacts/html/tool-pc-shelf.html`, `../artifacts/metadata/tool-pc-shelf.json`, `../artifacts/cdp/tool-pc-shelf-performance.json`; provisioned-PC dropdown data from `complete-ticket-workflow.json`'s `shipping-form-complete` entry.

---

## 11. Documentation / Knowledge Base — `/#docs`

**Purpose**: in-app knowledge base referenced during tickets.

**Layout**: header "What is a knowledge base?" learn-link, then **10 category cards**, each rendered twice — a compact grid and an "ALL CATEGORIES" expanded list (both are `type="submit"` buttons with text like "NETWORK & CONNECTIVITY\n5" / "...5 DOCS").

**Categories** (exact counts confirmed, 38 docs total):

| Category | Docs |
|---|---|
| Environment Overview | 1 |
| Email & Mail Server | 4 |
| Password & Security | 4 |
| Network & Connectivity | 5 |
| Server Documentation | 4 |
| Standard Procedures / SOPs | 4 |
| Software & Licensing | 3 |
| Hardware & Assets | 5 |
| Contacts & Escalation | 4 |
| Credentials & Access | 4 |

**Article view**: not separately captured in `artifacts/`; check `../website-capture/crawlee-servicedesk/output/` for an opened-article state. Design as: category → article list → article detail (title, body, maybe "related tickets" or "was this helpful"). Keep articles short (matches the Computer Deployment tool's own cross-link: "CHECK THE DOCUMENTATION" for SOP guidance) — these are the source of the deployment SOP and the network/hardware/credentials reference material tickets will cite.

**Connections**: the Deployment tool's own copy directly cross-links here ("NOT SURE WHICH SETUP A PC NEEDS? CHECK THE DOCUMENTATION"), and tickets' help-reveal system should be able to deep-link into a specific article as one hint type.

Evidence: `../artifacts/screenshots/desktop/tool-documentation.png`, `../artifacts/html/tool-documentation.html`, `../artifacts/metadata/tool-documentation.json`, `../artifacts/cdp/tool-documentation-performance.json`.

---

## 12. Asset Management — `/#assets`

**Purpose**: org-wide IT asset inventory.

**Layout**: header "What is asset management?" learn-link, view-toggle **BY USERS / BY ASSETS**, **SYNC FROM AD** action button, search input ("Search assets"), then a table: **ASSET TAG | NAME | DEPARTMENT | STATUS**.

**Data**: full 83-row roster captured verbatim (org chart-shaped: Executive → Finance/Sales/Engineering/Marketing/HR/Legal/Operations/Support/Facilities/Accounting/Design departments), every row status `DEPLOYED` in this capture. Row is a button (`aria-label="View asset details for {name}"`) → opens an asset detail panel (not separately captured — infer standard fields: asset tag, owner, department, status, plus device specs/warranty/purchase-date as plausible original additions).

**"BY ASSETS" view**: not captured distinctly from "BY USERS" in this session (same table shown); likely re-sorts/re-groups by device rather than by person. Build both as real toggled views over the same `Device`+`DirectoryUser` join, not two separate data sources.

**"SYNC FROM AD"**: explicit named integration point with Directory — clicking it should pull any Directory-side user/device changes into this table. This is the second flagship "shared state" example (after Directory→Remote Desktop) and should use the same event-driven read model.

**Table footer**: `"83 of 83"` — build a real pagination/count footer even if the seed dataset stays under one page.

Evidence: `../artifacts/screenshots/desktop/tool-asset-management.png`, `../artifacts/html/tool-asset-management.html`, `../artifacts/metadata/tool-asset-management.json`, `../artifacts/cdp/tool-asset-management-performance.json`.

---

## 13. Ship Manager — `/#shipmanager`

**Purpose**: create and dispatch a shipment (usually a replacement/provisioned device) to an employee.

**Layout**: `sd-panel-frame--contained` variant, header + "How does shipping work?" learn-link, single-column form:

- **Recipient information** — Recipient name (searchable dropdown of the 83-person directory), Street address, City, State, Postal code (auto-filled once recipient chosen, editable).
- **Package details** — **Sender (from)** department dropdown (IT Department, Accounting, Customer Support, Design, Engineering, Executive, Facilities, Finance, HR, Legal, Marketing, Operations, Sales), **Equipment to ship** multi-select/quantity list (HDMI Cable, DisplayPort Cable, USB-C Cable, Laptop Charger, Desktop Power Cable, Computer (laptop/desktop) with a quantity stepper, Monitor).
- Selecting "Computer" reveals an **additional provisioned-PC selector** sourced from PC Shelf (`SD9099, SD8765, ...`).
- **Shipping speed** — radio/select: Standard (5-7 days), Express (2 days), Priority (Same day), **Rush Priority (Instant)** — Rush is instant in-sim (no wait state to simulate, ships immediately).
- **Include return label** — checkbox (prepaid return label for the replaced/broken device).
- **SHIP** submit button.

**Validation**: empty-form submit shows "Enter the full shipping address before shipping." (`shipping-required-field-validation.png`). Completed form: `shipping-form-complete.png`.

**Post-ship**: `replacement-shipped.png` shows a success state with a **"REFILL LAST ADDRESS"** convenience button for the next shipment.

**Connections**: recipient list = Directory/Asset roster; provisioned-PC list = PC Shelf; a completed shipment should be visible back on the originating ticket (delivery-confirmation chat beat) and should remove the item from PC Shelf.

Evidence: `../artifacts/screenshots/desktop/tool-ship-manager.png`, `shipping-form-complete.png`, `shipping-required-field-validation.png`, `replacement-shipped.png`; `../artifacts/html/tool-ship-manager.html`; `../artifacts/metadata/tool-ship-manager.json`, `complete-ticket-workflow.json` (has the exact populated field values used in the recorded run); `../artifacts/cdp/tool-ship-manager-performance.json`.

---

## 14. Company Chat — header button, not a hash route

**Purpose**: direct-message simulated employees; primary channel for ticket-relevant info-gathering (address confirmation, device confirmation, delivery confirmation).

**Layout**: panel/drawer with **Recent / Contacts / Pinned (n)** tabs, a searchable list backed by the same 83-person directory, a conversation view, quick-reply canned-message chips, and a message input capped at **500 characters**.

**Empty state**: "No recent chats — Select a contact to start chatting." (`company-chat-empty.png`).

**Populated/ticket-context state**: `ticket-chat-diagnosis-and-address.png` and `ticket-chat-delivery-confirmation.png` show it opened in-context from a ticket, with the requester's simulated responses appearing as canned/scripted replies keyed to the ticket's scenario script (not a live LLM in the captured evidence — REPORT.md doesn't show any generative chat backend, only Firestore-delivered scripted state). Build this as **scripted branching dialogue per scenario** (a `ChatThread`/`ChatMessage` tree keyed by ticket + trigger conditions), not a live AI chat, matching the observed behavior and avoiding unscoped LLM cost/latency/safety work.

**Connections**: opening chat from within a ticket should pre-select that ticket's requester and can gate ticket objectives (e.g. "confirm address via chat" as a required action before Ship Manager will validate).

Evidence: `../artifacts/screenshots/desktop/company-chat-empty.png`, `ticket-chat-diagnosis-and-address.png`, `ticket-chat-delivery-confirmation.png`; `../artifacts/html/company-chat-empty.html`; `../artifacts/metadata/company-chat-empty.json`, `complete-ticket-workflow.json`; `../artifacts/cdp/company-chat-empty-dom-snapshot.json`, `company-chat-empty-performance.json`.

---

## 15. Analytics — `/#analytics` (under Profile)

**Purpose**: personal performance dashboard.

**Layout**: header "Track your support performance and identify training opportunities." + "What are help desk metrics?" learn-link, then:

- **Stat row**: SCORE, ACCURACY %, TICKETS RESOLVED, CALL VOLUME (4 big numbers).
- **Tier Progress**: "`{n}` pts to `{NextTier}`" + a 10-rung ladder — Rookie(0) → Bronze(100) → Silver(300) → Gold(750) → Platinum(1,500) → Diamond(3,000) → Master(6,000) → Legend(10,000) → Mythic(15,000) → Apex(25,000) → Eternal(50,000) — with current-position marker.
- **Category Breakdown**: "`{n}` of 6" resolved-by-category with counts+percentages (Network, Access, and by extension Hardware/Software/Security/Email — 6 categories total, matching Training Focus below).
- **Priority Distribution**: "`{n}` tickets" with Critical/High/Medium/Low counts+percentages.
- **Call Activity** table: METRIC/VALUE rows — Answered Today, Lifetime Calls, Missed/Declined, Tickets from Calls.
- **Training Focus**: "`{n}` of 6 categories enabled" toggle grid — Network (VPN, WiFi, connectivity), Hardware (Printers, displays, USB, peripherals, battery), Software (Apps, Team Chat, Office Suite, application errors), Access (Directory, permissions, groups, IAM), Security (Identity verification, social engineering), Email (Mail, mobile email, Mail Server config) — each a toggle button, plus **Save Preferences**. This is the student-facing control for which ticket categories populate their queue — a real, persisted per-student setting, not cosmetic.

**Connections**: every number here is a rollup of the append-only event/attempt log (see DATABASE.md) — this page must be a read model over `Events`/`Grades`, never a separately-maintained counter that can drift.

Evidence: `../artifacts/screenshots/desktop/profile-analytics.png`, `../artifacts/html/profile-analytics.html` (confirm exact filename via `state-manifest.json`), `../artifacts/metadata/profile-analytics.json`, `../artifacts/cdp/profile-analytics-performance.json`.

---

## 16. Achievements — `/#achievements` (under Profile)

**Purpose**: gamified progress/badges.

**Layout**: **CURRENT RANK** hero (e.g. "SERVICE DESK TRAINEE", points, "NEXT CERTIFICATE" callout: "`{n}` more tickets to earn `{CertName}`"), **CAREER PROGRESSION** ladder (`0/4`: IT Support Foundations@50, Help Desk Technician@100, Service Desk Professional@250, Senior Service Desk Specialist@500 — each LOCKED until threshold), then an **EARNED** section (`3/17` in capture — First Ticket, Speed Demon "Resolve a ticket in under 60 seconds", First Call, each with an earned date) and a **LOCKED** section listing the remaining 14: Getting Started (10 tickets), Troubleshooter (25), Helpdesk Hero (50), IT Veteran (100), Ticket Machine (250), Legend (500), Call Master (10 calls), Call Center Pro (25 calls), Streak Starter (3-day login streak), Dedicated (7-day), Unstoppable (30-day), 1K Club (1,000 score), High Roller (10,000 score), Sharpshooter (90%+ accuracy, 20+ tickets).

**Design implication**: this is a straightforward rules table — `Achievement{code, name, description, threshold, category}` evaluated against the same event log Analytics reads. Build the 17 listed achievements verbatim (they're generic gamification labels, not proprietary content) plus the 4 career-progression certificates as a separate `CareerTier` table.

Evidence: `../artifacts/screenshots/desktop/profile-achievements.png`, `../artifacts/html/profile-achievements.html`, `../artifacts/metadata/profile-achievements.json`, `../artifacts/cdp/profile-achievements-performance.json`.

---

## 17. Leaderboard — header button (modal over Dashboard)

**Purpose**: global ranking.

**Layout**: modal/panel over the Dashboard (dashboard content visible/blurred behind), header "LEADERBOARD", scope indicator "Global", ranked rows: rank / display name / rank-tier badge / points. Captured with a single row (`#1 shadow Rookie 83` — solo test account). Close button `aria-label="Close leaderboard"`.

**Design implication**: build scope as a real filter (Global / Classroom, once Classroom exists) even though only Global was observed — Classroom-scoped leaderboards are a natural, low-risk extension implied by the Classroom foundation requirement.

Evidence: `../artifacts/screenshots/desktop/leaderboard.png`, `../artifacts/html/leaderboard.html`, `../artifacts/metadata/leaderboard.json`, `../artifacts/cdp/leaderboard-performance.json`.

---

## 18. Friends / Social — under Profile

**Purpose**: social layer (friends list, requests, search).

**Layout**: captured as a left-rail overlay on top of the Dashboard: **SOCIAL** header, **FRIENDS / REQUESTS / SEARCH** tab buttons (`type="submit"`). Populated states (friend cards, pending requests, search results) not captured — REPORT.md's inferred entity list confirms `Friend/FriendRequest` and the crawl evidence separately confirmed real backend functions `getFriendRequests`/`getFriends` (Firebase Cloud Functions), i.e. this is real, server-backed, not decorative. Build with empty/populated/pending states inferred from the tab structure: Friends (accepted list, each removable), Requests (incoming, accept/decline; outgoing, cancel), Search (by name, "Add Friend" action).

Evidence: `../artifacts/screenshots/desktop/profile-friends.png`, `../artifacts/html/profile-friends.html`, `../artifacts/metadata/profile-friends.json`, `../artifacts/cdp/profile-friends-performance.json`.

---

## 19. Profile menu + Settings

### 19.1 Profile menu — header avatar button (dropdown)

**Purpose**: navigation hub for all account-adjacent surfaces.

**Contents** (per REPORT.md + `profile-menu.json`): Analytics, Friends, Achievements, Past Tickets, Tutorial & Guides, Discord (external), Support & Feedback, About, Settings, Log Out.

Evidence: `../artifacts/screenshots/desktop/profile-menu.png`, `../artifacts/html/profile-menu.html`, `../artifacts/metadata/profile-menu.json`, `../artifacts/cdp/profile-menu-performance.json`.

### 19.2 Settings — modal, tabbed

**Tabs**: Profile, Account, Preferences, Billing, Classroom, Community, Our Story (left-nav buttons in the modal).

**Profile tab** (captured): **DISPLAY NAME** text field + Save, avatar picker (~60 emoji options grouped by theme: people, professions, animals — plain buttons, single-select).

**Other tabs** (not separately captured — infer standard shape, keep minimal): Account (email, password change, delete account — REPORT.md flags destructive account actions as intentionally out of scope for capture, so no evidence exists; still needs to exist as a real, low-risk settings surface: email display + password-change flow only for v1). Preferences (theme, notification toggles). Billing (plan display + Stripe portal link — ties to Subscription Plans modal, §21). Classroom (join/leave code, ties to Classroom foundation). Community (Discord link, social prefs). Our Story (static About-style copy).

Evidence: `../artifacts/screenshots/desktop/profile-settings.png`, `../artifacts/html/profile-settings.html`, `../artifacts/metadata/profile-settings.json`, `../artifacts/cdp/profile-settings-performance.json`.

### 19.3 Past Tickets, Tutorial & Guides, Support & Feedback, About — modals under Profile

Secondary informational/history surfaces. Past Tickets = a filterable read-only list of the student's closed/attempted tickets (score, resolution status, date) — a direct read model over `Attempt`/`Grade`. Tutorial & Guides, Support & Feedback, About = mostly static content; keep original copy, minimal build effort, low priority relative to the core tools.

Evidence: `../artifacts/screenshots/desktop/profile-past-tickets.png`, `profile-tutorial-guides.png`, `profile-support-feedback.png`, `profile-about.png` + matching `.html`/`.json`/CDP files for each.

---

## 20. Classroom foundation

**Purpose**: teacher/student grouping, assignment, and classroom-scoped leaderboard.

**Evidence status**: the most sparsely captured surface — `/teachers` public page pitches it; **Join Classroom** is captured as a student-facing entry point:

**Join Classroom** — header "JOIN CLASS" button opens a short-code entry form; invalid/not-found codes show inline feedback without navigating away (no page-level error state, no redirect).

**Design implication**: build the full teacher side (create classroom, roster, assignment authoring/preview, per-student progress view) as original scope grounded in the task's database plan (`Organization` → `Classroom` → `Enrollment` → `Assignment`) rather than the shallow capture — this matches the task brief's explicit "Classroom foundation" requirement and the AI-clone evidence's discovery of `CreateClassroomModal`/`JoinClassroomModal`/`TeacherDashboardModal`/`TeacherWelcomeModal` bundle names (confirms these surfaces exist in the real product, even though their content wasn't captured).

Evidence: `../artifacts/screenshots/desktop/join-classroom.png`, `../artifacts/html/join-classroom.html`, `../artifacts/metadata/join-classroom.json`, `../artifacts/cdp/join-classroom-performance.json`; `/teachers` route text via `../website-capture/crawlee-servicedesk/output/text/`.

---

## 21. Quotas, paywalls, subscription

**Ticket quota exhausted** (`quota-ticket.png`) and **call quota exhausted** (`quota-call-paywall.png`, `voicemails-paywall.png`, `mock-interview-paywall.png`) — each routes the blocked action's button into a **plan modal** rather than a dead-end error.

**Subscription Plans modal** (`subscription-plans.png`, full copy captured): **Monthly/Annual** toggle ("Save 17%"), **Free** plan card ("$0/forever", "No credit card required", "5 ticket completions per day", "One call per day", Past tickets, Analytics, Leaderboard, Desktop tools, marked "Your current plan"), **Pro** plan card ("$20/month", "Billed monthly, cancel anytime", Unlimited tickets, Unlimited voice calls, Audible voicemails, AI mock interviews, "Cancel anytime"), plus a **Teacher · For educators** link and **Subscribe · $20/month** submit button, footer copy: "Payments are handled securely in Stripe." / "Auto-renews until canceled — we charge your payment method each billing period. Cancel anytime in Settings → Billing."

**Design implication**: build the quota/paywall UX exactly as observed (soft paywall via modal, never a hard block with no explanation), and integrate real Stripe Checkout + a webhook-driven `Plan`/`Subscription` table — but Stripe checkout itself was explicitly never exercised in the capture (no bypass attempted), so there is no evidence of the actual checkout screen; treat that final step as standard Stripe-hosted checkout, not something to reverse-engineer.

Evidence: `../artifacts/screenshots/desktop/quota-ticket.png`, `quota-call-paywall.png`, `voicemails-paywall.png`, `mock-interview-paywall.png`, `subscription-plans.png` + matching `.html`/`.json`/CDP files.

---

## 22. Voice calls, voicemail, mock interview — coverage gap

**Status**: legitimately blocked in the capture (Free-tier daily quota exhausted at capture time) — REPORT.md calls this "the only material coverage gap in the accessible authenticated product." No screenshots of an in-progress call, voicemail playback, or mock interview UI exist anywhere in the evidence.

**Design implication**: per REPORT.md's own recommendation, treat these as **later, optional phases** requiring explicit microphone consent, recording/transcript-retention policy, abuse controls, and cost budget — do not build them in the core phases (§ IMPLEMENTATION_PLAN.md marks this explicitly). The AI-clone evidence confirms bundle names `PhoneCallSimulation` and `MockInterviewPanel` exist in the real product's code-splitting, which at minimum confirms these are separate, deferrable modules architecturally (supporting deferring them without guessing at their internal design).

---

## 23. Error / quality states to reproduce deliberately

- **`workflow-failure.png`** — a captured incorrect-path/failure state within the deployment-to-close flow; use as the visual reference for a generic "action rejected" treatment (inline red banner/toast pattern), consistent with the specific inline correction copy seen at each wrong-action step in Deployment.
- **Close-unresolved warning** — modal warning with exact point cost before allowing closure; never a silent penalty.
- **Empty states** observed: PC Shelf (copy above), Company Chat (copy above), Team Chat dashboard card (copy above). Use the same tone/format ("what it is" + "how to fill it") for any additional empty states you must invent (Directory search no-results, Friends empty, Past Tickets empty).

---

## Evidence index (state → files)

`../artifacts/state-manifest.json` is the authoritative machine-readable index tying every `stateName` to its real `url` and desktop/mobile size label — read it first when scripting any bulk evidence lookup. Every state named in this document has a matching `{stateName}.png` under `../artifacts/screenshots/{desktop,mobile}/`, a `{stateName}.html` under `../artifacts/html/`, and (for most single-page states) a `{stateName}.json` under `../artifacts/metadata/`; multi-step workflow states are consolidated in `../artifacts/metadata/complete-ticket-workflow.json` instead. CDP performance/DOM snapshots for key states live under `../artifacts/cdp/`.
