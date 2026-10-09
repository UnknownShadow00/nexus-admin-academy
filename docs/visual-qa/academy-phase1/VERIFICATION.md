# Phase 1 visual correction verification

Draft PR: [#64](https://github.com/UnknownShadow00/nexus-admin-academy/pull/64). Owner approval remains pending; no merge or deployment.

Worktree: `/home/nexus/worktrees/nexus-academy-phase1`; branch `feature/nexus-academy-phase1`.

Fresh remote main was reverified as `663d623041bd0b434d0bf2724a4161b23ececb6e`. The correction continues the existing draft branch from `536fb8c`. Its previously committed 1440px light/dark screenshots were copied byte-for-byte to `pr64-before-*.png` before editing. The [gallery](README.md) compares the rejected PR result directly with this correction using the same synthetic account, API responses, theme and 1440×900 CSS viewport. Full-page captures extend below the viewport.

## Changes and visual review

- Replaced empty castle/character/army slots with original daylight and moonlit fortress scenes, a faceless hooded foreground character and glowing-eye shadow sentinels. All are local assets; no supplied board was cropped or used as an image-generation input.
- Added subtle original ambient mist behind the dashboard and coherent blue/violet card borders, surfaces, shadows and icon wells. Reading panels remain opaque.
- Integrated the same artwork at the sidebar foot, refined selected navigation, prevented expanded submenu width from clipping the sidebar, and reduced desktop heading/hero spacing. Narrow heroes place art above a solid text surface.
- Changed learner header, login and document title to **Nexus Academy**. Added an original SVG N mark; admin header branding stays separate.
- Preserved the existing Phase 1 model, API routes, counts, navigation access, status vocabulary, theme and account behavior. This correction makes no changes to `StudentHome.jsx` or backend logic.

The rendered 1440/1280 light/dark, 1024/390 sanity views, expanded sidebar, keyboard focus and mobile menu captures were inspected. The castle, hood and army are now visible rather than absent; daylight remains softer and night carries the moonlit shadow atmosphere. See [asset placement, generation recipes and hashes](../../design/phase1-artwork.md).

## Results

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Full frontend Vitest suite | PASS: 39 files, 228 tests, 29.42s | `npm test -- --maxWorkers=1`; existing nav, auth, Today and theme/count tests retained |
| Browser suite | PASS: 17 tests, 18.6s | `npx playwright test --config playwright.phase1.config.js`; 14 Phase 1 checks plus 3 existing reflow/pilot tests |
| Frontend build | PASS: 2.28s | `npm run build`; existing >500kB JavaScript chunk warning remains |
| Dependency audit | PASS: zero vulnerabilities | `npm audit --json`; no dependency or lockfile changes |
| Rendered contrast | PASS: 200 samples across 8 theme/viewport combinations | Light minimum 5.77:1; dark minimum 7.10:1. Exact foreground/background samples in `contrast-*.json`; sampled checks are not a comprehensive accessibility certification |
| Local artwork | PASS | All five WebPs decode; selected day/night hero assets load; both cutouts retain >20% fully transparent pixels |
| Reflow, focus, reduced motion | PASS | No overflow at 1440/1280/1024/390; existing nav test covers 320–1440 and CSS zoom surrogate; expanded links remain inside the sidebar; menu inert/Escape, skip link and 3px sidebar focus preserved |
| Diff/scope | PASS | Whitespace clean; no backend, Service Desk, deployment, workflow, feature configuration or access-hook changes |
| Lint / static types / coverage | NOT CONFIGURED / NOT RUN | No lint/type-check scripts or coverage tooling configured; no percentage claimed |
| Owner visual approval | PENDING | Generated branch art and monogram are provisional; PR remains draft |

`verification-summary.json` records the final browser statistics and contrast minima. Ignored `browser-results.json` is available locally. The existing jsdom canvas-not-implemented warning appeared during the passing unit suite; no dependency was added to suppress it.

The existing reflow test's two accessible-name expectations were updated from “Nexus Admin Academy home” to “Nexus Academy home” to match the requested learner branding. Focus/reflow assertions were retained. New checks assert the learner name, theme-specific art selection and transparent compositing. No unrelated test was weakened. A new sidebar-boundary assertion caught the shared floating-menu width clipping the expanded sidebar; the scoped width override fixes it. One subsequent run encountered loading timeouts while host memory/swap was pressured (807 MiB available, swap full); no production process was touched, and the final suite was rerun unchanged after available memory recovered.

## Preserved behavior and safety

`buildContinueTarget` and `buildTodayModel` are unchanged. Browser checks verify the exact server continuation route, one primary action, real lesson rendering and browser back. Legacy keeps exactly three destinations; backend cohort denial and admin redirect remain enforced. Counts, estimates, XP, rank and streak still come from existing APIs, with missing values hidden and motivation separate from mastery. Waiting, correction, loading, retry and empty states retain their semantics.

Tests use disposable frontend servers on loopback `5819` and synthetic HTTP API `5820`; Playwright owns and stops them. No backend code, database, real credentials, env files or production process was used. Fixture V2 flags affect only the disposable frontend process. Synthetic unsigned fixture tokens cannot authenticate to Nexus. External requests are blocked in Phase 1 browser tests.

The production checkout remains detached at `663d623`, with its pre-existing modified `tasks/loop-log.md` and untracked package ZIP untouched. All implementation, screenshots, build output, review documentation and required log updates are confined to the isolated worktree. No merge, deploy, migration, grading, curriculum import, service activation or Phase 2 work occurred.

These are frontend/API-contract checks using synthetic data. No live backend grading, real Service Desk runtime or admin mutation test is claimed. The retained pilot test's Service Desk responses come from clearly marked fixtures. Admin auth/role unit tests pass; browser admin login/reflow is outside this fixture scope.

## Remaining gaps

No requested artwork slot is empty. Owner approval is still needed for visual fidelity and the provisional art/monogram. System fonts remain rather than a supplied standalone brand typeface. Reference-only fictional schedules, achievements and extra navigation were not fabricated. Other screen-specific artwork and redesigns remain outside Phase 1. The existing build chunk warning is unchanged.

## Reproduce safely

In an isolated checkout, install frontend dependencies with `npm ci --ignore-scripts --no-audit --no-fund`. Run sequentially with one worker:

```sh
npm test -- --maxWorkers=1
npm run build
npm audit
npx playwright test --config playwright.phase1.config.js
```

Chromium must be installed for Playwright. No real credentials are required. The `pr64-before-*.png` files are immutable historical evidence from `536fb8c`; final browser runs regenerate only the corrected captures. Earlier `before-*.png` files from original main remain separate.

## Exact files changed in this correction

Relative to `536fb8c` (the rejected draft PR state):

```text
docs/design/phase1-artwork.md
docs/visual-qa/academy-phase1/README.md
docs/visual-qa/academy-phase1/VERIFICATION.md
docs/visual-qa/academy-phase1/contrast-dark-1024.json
docs/visual-qa/academy-phase1/contrast-dark-1280.json
docs/visual-qa/academy-phase1/contrast-dark-1440.json
docs/visual-qa/academy-phase1/contrast-dark-390.json
docs/visual-qa/academy-phase1/contrast-light-1024.json
docs/visual-qa/academy-phase1/contrast-light-1280.json
docs/visual-qa/academy-phase1/contrast-light-1440.json
docs/visual-qa/academy-phase1/contrast-light-390.json
docs/visual-qa/academy-phase1/legacy-light-1440.png
docs/visual-qa/academy-phase1/mobile-menu-dark.png
docs/visual-qa/academy-phase1/mobile-menu-light.png
docs/visual-qa/academy-phase1/pr64-before-dark-1440.png
docs/visual-qa/academy-phase1/pr64-before-light-1440.png
docs/visual-qa/academy-phase1/sidebar-expanded-dark.png
docs/visual-qa/academy-phase1/sidebar-expanded-light.png
docs/visual-qa/academy-phase1/sidebar-focus-dark.png
docs/visual-qa/academy-phase1/sidebar-focus-light.png
docs/visual-qa/academy-phase1/today-dark-1024.png
docs/visual-qa/academy-phase1/today-dark-1280.png
docs/visual-qa/academy-phase1/today-dark-1440.png
docs/visual-qa/academy-phase1/today-dark-390.png
docs/visual-qa/academy-phase1/today-light-1024.png
docs/visual-qa/academy-phase1/today-light-1280.png
docs/visual-qa/academy-phase1/today-light-1440.png
docs/visual-qa/academy-phase1/today-light-390.png
docs/visual-qa/academy-phase1/verification-summary.json
frontend/index.html
frontend/public/academy/ambient-mist.webp
frontend/public/academy/castle-day.webp
frontend/public/academy/castle-night.webp
frontend/public/academy/hooded-wanderer.webp
frontend/public/academy/nexus-mark.svg
frontend/public/academy/shadow-sentinels.webp
frontend/src/App.jsx
frontend/src/academy.css
frontend/src/components/ui/AcademyScene.jsx
frontend/src/pages/LoginPage.jsx
frontend/tests/e2e/global-nav-reflow.spec.js
frontend/tests/phase1/academy.spec.js
tasks/loop-log.md
```
