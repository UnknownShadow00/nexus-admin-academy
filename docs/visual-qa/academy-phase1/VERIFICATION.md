# Phase 1 verification

Branch: `feature/nexus-academy-phase1`

Worktree: `/home/nexus/worktrees/nexus-academy-phase1`

Base: fresh `origin/main`, `663d623041bd0b434d0bf2724a4161b23ececb6e`, independently matched to `git ls-remote origin refs/heads/main` before worktree creation.

## Results

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Full frontend Vitest suite | PASS: 39 files, 228 tests | `npm test -- --maxWorkers=1`; includes original Today/nav/access/auth tests and new count/theme/error tests |
| Browser suite | PASS: 16 tests, 12.3 seconds | `npx playwright test --config playwright.phase1.config.js`; 13 new checks plus 3 unchanged existing navigation/reflow/pilot tests |
| Frontend production build | PASS | `npm run build`; existing large-chunk warning remains |
| Dependency audit | PASS: zero vulnerabilities | `npm audit --json`; no dependency/lockfile changes |
| Contrast | PASS for sampled new surfaces | 200 rendered-background samples across light/dark at 1440, 1280, 1024, 390. Minima: light 5.29:1; dark 5.90:1. Exact samples in `contrast-*.json` |
| Reflow / keyboard / reduced motion | PASS in browser suite | No page overflow at requested widths; existing nav also checks 320–1440 and CSS zoom surrogate. Menu inert state, Escape, skip link, sidebar outline, reduced motion verified |
| Before screenshots | PASS: 2 separate captures | Unmodified base source extracted to disposable space; same API fixtures and 1440×900 viewport |
| Lint / static type check / coverage | NOT CONFIGURED / NOT RUN | Project has no lint or type-check scripts. No coverage instrumentation installed; no coverage percentage claimed |
| Finished fantasy artwork fidelity | PENDING ASSETS | No standalone cleared art was provided. Asset slots, compositing, themes and scrims implemented per brief; no board crops used |

`verification-summary.json` records final browser statistics and viewport contrast minima. Raw browser results remain locally available as `browser-results.json`; only compact review evidence is committed.

## What was preserved

- `buildContinueTarget` and `buildTodayModel` are unchanged. V2 `continue.route`, availability, status and estimate, plus legacy `next_activity.destination_route`, still determine the next task. Browser checks assert exact supplied paths, one primary action, successful lesson opening and browser return.
- V2 access remains controlled by `useV2Access` and the backend cohort response. Legacy has exactly three destinations. Fixture V2 denial and admin redirect are exercised; no route, access flag, or authorization implementation was changed.
- Rank/XP/streak come only from existing stats fields. Zero is displayed honestly; missing/invalid values are hidden. Lesson and Quick Check counts use existing progress fields; server stage mastery remains separate.
- Mentor pending/correction states keep their existing model and vocabulary. Empty mentor panels are suppressed; real follow-ups remain visible.
- Theme uses the existing persisted `theme` preference and system fallback. No remote fonts, images, analytics configuration, or integration was added.
- Search implementation, Service Desk anchor/document navigation, training destinations and return routes remain unchanged. The account menu now closes when a link/back navigation starts, avoiding a delayed lazy-route commit closing a newly opened menu; the unchanged pilot/logout browser test covers that regression.

## Isolation and honest test boundaries

All source edits, npm installation, build output, screenshots and logs are confined to the development worktree or disposable `/tmp/nexus-academy-phase1-baseline`. Test servers bind only `127.0.0.1:5819` (development frontend), `:5820` (synthetic HTTP API), and optionally `:5818` (baseline frontend). Existing port 5173/5174/8000 services were not used. Playwright owns and stops its own fixture services.

The fixture API contains synthetic accounts and unsigned fixture tokens that cannot authenticate to Nexus. It imports no backend code, opens no database, reads no env/secrets, and calls no other service. Browser configuration sets only disposable-process API/build variables and disables Sentry; production flags and env files remain untouched. New browser tests explicitly reject network requests outside fixture origins.

The original production checkout still has its pre-existing modified `tasks/loop-log.md` and untracked package archive. Neither was edited. Its detached HEAD remains the original commit. The required completion entry is written **in the worktree**. Diff checks confirm no changes to `backend/`, `service-desk-app/`, `deploy/`, `.github/`, `features.js`, or `useV2Access.js`.

These are frontend/API-contract tests with synthetic responses. **No live backend grading, database writes, curriculum publication, or real Service Desk runtime test is claimed.** The unchanged pilot shell test's Service Desk health/contract requests are satisfied by clearly marked fixture responses; they are not evidence of a running Service Desk application. Admin browser login/reflow is not run; existing frontend auth/role tests pass and admin styling/data code is unchanged. Font/contrast QA covers the available system fonts and artwork-free compositing, not future delivered assets.

An earlier concurrent full-suite run failed with worker-start timeouts and a Chromium page crash while host memory/swap was pressured. Final verification was rerun sequentially with one worker: 228 unit tests and 16 browser tests all pass. Before captures passed separately in the earlier comparison run. No unrelated test was weakened; the one changed original Today assertion now requires the intentionally hidden empty mentor panel.

## Reproduce safely

From an isolated checkout, install with `npm ci --ignore-scripts --no-audit --no-fund` in `frontend/`. Use one worker and run suites sequentially:

```sh
npm test -- --maxWorkers=1
npm run build
npm audit
npx playwright test --config playwright.phase1.config.js
```

Do not run these commands in production. No real account credentials are required. Chromium must be available to Playwright. To regenerate before comparisons, extract only `frontend/` from the base commit into disposable space, provide its dependencies, and pass `NEXUS_PHASE1_BASELINE_DIR=/path/to/disposable/extraction` to the same browser command. The baseline server must not be a production path.

## Owner review / next slice

Keep this PR draft and undeployed. Supply cleared original day/night castle scenes, faceless protagonist, shadow-army silhouettes, and the original monogram before claiming the visual direction is fully realized. Review the same-viewport gallery and navigation first. Following explicit owner approval, Phase 2 should be limited to Learning Path and lesson UI; no Phase 2 work is included here.

## Changed files

- Learner UI: `frontend/src/App.jsx`, `frontend/src/pages/StudentHome.jsx`, `frontend/src/styles.css`, `frontend/src/academy.css`, `frontend/src/components/ui/AcademyScene.jsx`.
- Focused unit tests: `frontend/src/pages/StudentHome.test.jsx`, `frontend/src/hooks/useDarkMode.test.jsx`.
- Disposable browser QA: `frontend/playwright.phase1.config.js`, `frontend/tests/phase1/academy.spec.js`, `api-server.mjs`, `fixtures.mjs`, `contrast.mjs`.
- Review evidence: `docs/design/phase1-artwork.md`; this gallery's README, verification report, compact summary, eight contrast JSON files and seventeen actual PNG captures.
- Safety/logging: `.gitignore`, `tasks/loop-log.md`.
