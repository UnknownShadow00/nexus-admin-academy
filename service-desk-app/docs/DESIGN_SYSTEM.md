# Design System

Extracted from rendered HTML class usage across all 58 captured states (`../artifacts/html/*.html`). The captured app renders no external stylesheet content locally (fonts/CSS are fetched remotely at capture time), so every token below is reconstructed from **Tailwind utility-class usage frequency** plus the custom `sd-*` component-class vocabulary actually present in the DOM — this is real, load-bearing evidence, not guesswork, but exact hex/spacing values should be treated as "Tailwind's default scale at these class names" rather than pixel-verified against a stylesheet. Where a screenshot is the better reference for a value (e.g. exact card corner radius), the section says so explicitly.

Do not pull colors/tokens from `../website-capture/ai-website-cloner/src/app/globals.css` — confirmed to still be the unmodified shadcn/ui default oklch theme, not derived from this product at all.

---

## 1. Color palette

Frequency-ranked from `grep -oE` across all `../artifacts/html/*.html` (Tailwind `zinc`/`sky`/`red`/`orange`/`amber` families dominate):

| Role | Tailwind classes (real usage, ranked) | Use |
|---|---|---|
| App background (deepest) | `bg-zinc-950` (181×) | page/root background, Directory panel body |
| Surface / chrome background | `bg-zinc-900` (491×), `bg-zinc-800` (609×) | header bar, cards, panels, dialog backgrounds |
| Borders | `border-zinc-700` (210×), `border-zinc-800` (143×), `border-zinc-900` (37×) | card borders, header bottom border, dividers |
| Primary text | `text-zinc-100` (88×), `text-zinc-200` (43×) | headings, high-emphasis body text |
| Secondary text | `text-zinc-300` (427×), `text-zinc-400` (580×) | body copy, labels |
| Muted / disabled text | `text-zinc-500` (626×), `text-zinc-600` (57×) | placeholders, inactive tabs, meta text |
| Primary accent (brand blue) | `text-sky-400` (850×), `text-sky-300` (626×), `bg-sky-600` (31×), `bg-sky-500` (30×) | links, active tab underline, primary icon buttons, primary button fill |
| Accent hover/lighter | `text-sky-200` (76×), `bg-sky-400` (12×) | hover states |
| Gold/leaderboard accent | `text-amber-400` (55×), `text-amber-300` (55×) | rank/leaderboard/trophy iconography, "Get Pro" or premium cues |
| Critical priority | `text-red-500` (37×) | Critical severity badge |
| High priority | `text-red-400` (60×) | High severity badge |
| Medium priority | `text-orange-400` (40×) | Medium severity badge |
| Low priority | not observed directly — use `text-amber-500`/`yellow-400` family for the 4th tier, consistent with the amber accent already in the palette | Low severity badge |
| Success/online | `bg-emerald-500` (2×, Server Room online indicators) | status-online dots, success confirmations |
| Light-theme inversion | `bg-zinc-100` (9×), `text-zinc-900` (3×), `bg-zinc-300` (2×) | light-theme surface swaps (see §6 Theming) |

**Rebuild rule**: use Tailwind's stock `zinc`/`sky`/`red`/`orange`/`amber`/`emerald` palettes directly (v3 or v4 default scale) rather than hand-rolled hex tokens — the evidence shows the real product uses Tailwind's defaults unmodified, which is also the fastest, most maintainable path for Codex to reproduce faithfully.

## 2. Typography

**Font families** (Google Fonts, loaded non-render-blocking via `media="print"` + `onload` swap — reproduce this loading pattern for performance parity):

| Family | Weights | Role (inferred from an HTML comment referencing "cyberpunk" headings + observed class patterns) |
|---|---|---|
| **Orbitron** | 400,500,600,700,800,900 | Display/heading font — H1 app title, tool titles, big stat numbers (SCORE, POINTS) |
| **Rajdhani** | 400,500,600,700 | Secondary UI/label font — nav buttons, section headers, badges |
| **JetBrains Mono** | 300,400,500,600,700 | Monospace UI — asset tags (`SD####`), incident IDs (`INC####`), technical fields (IPs, hostnames, code-like values) |
| **Share Tech Mono** | (single weight) | Secondary monospace accent — likely terminal-styled surfaces (deployment task-sequence log, server room metrics) |

Body text otherwise inherits a system sans stack layered under these display fonts (standard Tailwind `font-sans` default) — do not force Orbitron/Rajdhani onto dense body copy, only headings/labels/stat numbers, matching how a "flight simulator" aesthetic typically reserves display fonts for HUD-style elements.

**Sizes observed** (Tailwind scale, ranked by usage in `authenticated-queue.html`): `text-xs` (nav button labels, meta text), `text-sm` (body/secondary), `text-base` (default body / stat labels), `text-lg` (mobile logo/H2), `text-xl` (desktop H1/logo, `md:text-xl`), plus one bespoke `text-[10px]` (rank micro-label under avatar). Nav/tab buttons consistently pair `text-xs sm:text-sm font-extrabold uppercase tracking-normal` — i.e. **all-caps, extrabold, tight tracking** is the signature nav-label treatment; reproduce it exactly for header/tab buttons.

**Line height**: `leading-none` (stat numbers), `leading-tight`/`leading-snug` (headings, avatar+rank stack), default otherwise.

## 3. Spacing & layout primitives

From class-frequency in `authenticated-queue.html` (representative of the whole shell):

- **Header padding**: `px-2 pt-2 pb-1 sm:px-3 sm:pb-2 md:px-5 md:py-2` — i.e. padding scales up through 3 breakpoints (base/`sm`/`md`), tight on mobile, roomier on desktop.
- **Header height**: logo `h-8 md:h-10`; a separate points/stat column uses `h-8` / `h-14`; treat **header total height ≈ 56–64px** (`h-14`-ish) on desktop, ~48px on mobile, as the target.
- **Nav/tab buttons**: `px-2 sm:px-3 py-2.5 sm:py-3` — generous vertical padding (12px+) relative to horizontal, consistent with large touch targets for a training tool used at a desk.
- **Icon buttons** (Company Chat, Join Class, Leaderboard, tool tabs): `w-8 h-8 rounded-sm` container, `w-5 h-5` icon inside (Tabler icons), `gap-1.5` between icon and label when both present.
- **Card gap/grid**: header uses CSS grid — `grid grid-cols-[1fr_auto] items-center gap-2 gap-y-1.5` mobile, `md:grid-cols-[auto_minmax(0,1fr)_auto] md:gap-3` desktop.
- **Common gaps**: `gap-1`, `gap-2`, `gap-3`, `gap-4` all in active use — default to `gap-2`/`gap-3` for compact clusters (icon+label), `gap-4` for card-level spacing.
- **Common padding scale in use**: `p{x,y}-2`, `-2.5`, `-3`, `-4`, `-5`, `-6`, `-8` all appear — i.e. the app uses Tailwind's default spacing scale untouched; don't introduce a custom scale.
- **Divider**: vertical separators use `w-px h-5 bg-zinc-700/50` (hairline, 50% opacity) — reuse this exact "thin translucent zinc divider" pattern between header button clusters instead of visible full-opacity borders.

## 4. Border radius & elevation

- **Small controls** (icon buttons, badges): `rounded-sm`.
- **Cards, tooltips, dropdown surfaces**: `rounded-md`.
- **Shadow**: `shadow-lg` on tooltips/popovers, paired with `ring-1 ring-zinc-700/60` (a subtle 1px ring, not a heavy drop shadow) — this ring+shadow combo, not a colored glow, is the product's signature "floating surface" treatment. Reuse it for all dropdowns, tooltips, and modal cards.
- **Panel frames**: `sd-panel-frame` is the reusable tool-page container; variants observed: `sd-panel-frame--ad` (Directory), `sd-panel-frame--assets` (Asset Management), `sd-panel-frame--contained` (Ship Manager, Remote Desktop), `sd-panel-frame--fab-clearance` (leaves room for a floating action button). Build one `PanelFrame` component with a `variant` prop matching these four.

## 5. Component inventory (real class names → components to build)

Confirmed `sd-*` custom classes across the whole capture — build exactly these as your `packages/ui` component set (names below are the evidence; component/prop naming in code can be idiomatic React, but the visual variants must match):

| Class | Component to build |
|---|---|
| `sd-card`, `sd-card-header`, `sd-card-header__title`, `sd-card-header__meta` | `Card`, `CardHeader` (title + trailing meta/count slot) — used for Dashboard's Queue/Incidents/Team Chat blocks |
| `sd-button`, `sd-button--primary`, `sd-button--light` | `Button` with `variant="primary" \| "light" \| "default"` |
| `sd-icon-btn` | `IconButton` — square, `w-8 h-8 rounded-sm`, icon-only or icon+tooltip |
| `sd-soft-btn` | `Button variant="soft"` — lower-emphasis filled button (category chips, secondary actions) |
| `sd-link-button` | `LinkButton` — button styled as an inline link (the "What is X?" learn-links) |
| `sd-footer-link` | `FooterLink` |
| `sd-back-button` | `BackButton` ("← Dashboard" pattern) |
| `sd-toolbar-icon` | icon glyph inside toolbars (Asset Management, etc.) |
| `sd-input`, `sd-focus-ring` | `Input` with a shared focus-ring utility class (apply to all interactive elements for consistent a11y focus states) |
| `sd-panel-frame` (+ 4 variants above) | `PanelFrame` |
| `sd-screen`, `sd-screen--remote` | `ToolScreen` wrapper (the `--remote` variant likely adds the simulated-desktop chrome for Remote Desktop sessions) |
| `sd-modal-backdrop`, `sd-modal-card`, `sd-modal-header` | `Modal` primitive (backdrop + card + header slot) — reuse for Tools panel, Settings, Leaderboard, Subscription Plans, all confirm dialogs |
| `sd-settings-modal`, `sd-settings-layout`, `sd-settings-sidebar`, `sd-settings-nav-item`, `sd-settings-content`, `sd-settings-divider` | `SettingsModal` with a left-nav-tab layout — build as a generic "tabbed settings shell," reused verbatim for Settings (Profile/Account/Preferences/Billing/Classroom/Community/Our Story) |
| `sd-assets-layout`, `sd-assets-toolbar`, `sd-assets-table-header`, `sd-assets-row` | `DataTable` primitive (toolbar + header row + data rows) — reuse for Asset Management, and by extension Directory/Remote Desktop's list views even though those didn't get dedicated class names |
| `sd-auth-card`, `sd-auth-brand`, `sd-auth-nav` | `AuthCard` — login/public auth-adjacent chrome |
| `sd-surface-panel` | generic elevated surface (fallback for panels not covered by `sd-panel-frame`) |
| `sd-rotate-hint` | mobile "rotate your device" hint — build for any interaction that's genuinely hard in portrait (the Deployment cable-matching screen is the obvious candidate) |

**Icons**: inline SVG from the **Tabler Icons** set (`tabler-icon tabler-icon-{name}` classes observed: `tool`, `phone-call`, `device-landline-phone`, `message-circle`, `school`, `trophy`, and by extension one per nav item/tool). Use the `@tabler/icons-react` package directly — it is MIT-licensed and match is exact, not approximate.

**Badges**: priority badges are plain colored text (`text-red-500`/`text-red-400`/`text-orange-400`), not pill/chip backgrounds, in the captured queue rows — build `PriorityBadge` as colored bold uppercase text by default, but expose a `pill` variant for places a filled badge reads better (e.g. Achievements' LOCKED/EARNED section headers, which read as bold section labels, not per-item badges).

## 6. Theming

- Dark theme is the default and primary target. A `data-theme="{dark|light}"` attribute on the root element, set by an **inline pre-paint script** reading `localStorage.getItem('theme')`, avoids flash-of-wrong-theme. Reproduce this exact pattern in `apps/web`'s root layout (inline `<script>` before hydration, not a client-side `useEffect`).
- Light-theme tokens are present but secondary (`bg-zinc-100`, `text-zinc-900`, `bg-zinc-300` all appear, low frequency) — the public blog articles are explicitly linked with `?theme=light`, suggesting blog/marketing content defaults light while the authenticated app defaults dark. Build both themes, but treat dark as the primary design target for the simulator shell itself.

## 7. Responsive breakpoints

Standard **Tailwind default breakpoints** — no custom breakpoint values found; every responsive class observed uses stock prefixes:

| Prefix | Min-width | Observed usage |
|---|---|---|
| (none) | 0px (mobile-first base) | tightest padding/gaps, stacked single-column layout |
| `sm:` | 640px | header padding loosens, some labels reveal (`hidden sm:block`, `hidden sm:inline`) |
| `md:` | 768px | header grid switches from 2-col to 3-col (`auto_minmax(0,1fr)_auto`), padding loosens further, logo grows `h-8→h-10` |
| `lg:` | 1024px | additional micro-labels reveal (`hidden lg:inline`) |

**Mobile-specific mechanism**: rather than rebuilding every tool's layout per breakpoint, the app applies a **global CSS-custom-property zoom compensation** (`--app-vh`, `--app-zoom`, referenced in an HTML comment as "~0.75 on phones") to scale the whole shell down on narrow viewports, confirmed by `../artifacts/metadata/mobile-overflow.json` showing zero horizontal overflow at 375×812 with no per-component mobile rewrite evident. **Recommendation**: implement true responsive layouts (stacked cards, condensed nav) for the primary flows (Dashboard, Ticket Workspace, Directory, Ship Manager) since those are the ones explicitly required "mobile behavior" in the task brief, but adopt the same zoom-compensation trick as a fallback safety net for the denser tools (Server Room, Deployment's cable-matching screen) where a full mobile redesign is lower priority — flag Deployment's cable/port interaction explicitly for touch-device UX testing, matching REPORT.md's own caution: "Deployment cable and boot interactions remain visually dense and should receive explicit touch-device testing."

## 8. Reference screenshot per major page

Use these as the literal pixel/layout reference when Codex builds each page (desktop, 1440×1000 unless noted):

| Page | Reference screenshot |
|---|---|
| Public landing | `../artifacts/screenshots/desktop/public-home.png` |
| Login | `../artifacts/screenshots/desktop/login-empty.png` |
| Dashboard / Queue | `../artifacts/screenshots/desktop/authenticated-queue.png` (+ mobile: `../artifacts/screenshots/mobile/mobile-authenticated-queue.png`) |
| Tools panel | `../artifacts/screenshots/desktop/tools-menu.png` |
| Ticket workspace (baseline) | `../artifacts/screenshots/desktop/ticket-assigned-baseline.png` |
| Ticket workspace (help open) | `../artifacts/screenshots/desktop/ticket-help-open.png` through `ticket-help-step-7.png` |
| Directory | `../artifacts/screenshots/desktop/tool-directory.png` |
| Server Room | `../artifacts/screenshots/desktop/tool-server-room.png` |
| Remote Desktop | `../artifacts/screenshots/desktop/tool-remote-desktop.png` |
| Computer Deployment (hub) | `../artifacts/screenshots/desktop/tool-computer-deployment.png` |
| Computer Deployment (11-step flow) | `../artifacts/screenshots/desktop/deployment-*.png` (10 files, see PRODUCT_MAP.md §9 for the exact step order) |
| PC Shelf | `../artifacts/screenshots/desktop/tool-pc-shelf.png` |
| Documentation | `../artifacts/screenshots/desktop/tool-documentation.png` |
| Asset Management | `../artifacts/screenshots/desktop/tool-asset-management.png` |
| Ship Manager | `../artifacts/screenshots/desktop/tool-ship-manager.png`, `shipping-form-complete.png`, `shipping-required-field-validation.png`, `replacement-shipped.png` |
| Company Chat | `../artifacts/screenshots/desktop/company-chat-empty.png`, `ticket-chat-diagnosis-and-address.png`, `ticket-chat-delivery-confirmation.png` |
| Analytics | `../artifacts/screenshots/desktop/profile-analytics.png` |
| Achievements | `../artifacts/screenshots/desktop/profile-achievements.png` |
| Leaderboard | `../artifacts/screenshots/desktop/leaderboard.png` |
| Friends | `../artifacts/screenshots/desktop/profile-friends.png` |
| Profile menu | `../artifacts/screenshots/desktop/profile-menu.png` |
| Settings | `../artifacts/screenshots/desktop/profile-settings.png` |
| Join Classroom | `../artifacts/screenshots/desktop/join-classroom.png` |
| Subscription plans | `../artifacts/screenshots/desktop/subscription-plans.png` |
| Quota/paywall states | `../artifacts/screenshots/desktop/quota-ticket.png`, `quota-call-paywall.png`, `voicemails-paywall.png`, `mock-interview-paywall.png` |

Corresponding `../artifacts/html/{same-name}.html` gives the exact DOM/class structure for every row above — always cross-check the screenshot against its HTML sibling before implementing a page.
