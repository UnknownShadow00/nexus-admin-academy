# Nexus Academy — Phase 1 integration review

Draft integration PR: [#65](https://github.com/UnknownShadow00/nexus-admin-academy/pull/65). Scope: the shared learner shell and Today dashboard only. No Lesson, Quiz, or Service Desk redesign.

Integration branch: `feature/nexus-academy-integration-phase1`, in `/home/nexus/worktrees/nexus-academy-integration-phase1`. Created from freshly fetched and independently verified `origin/main` at `663d623041bd0b434d0bf2724a4161b23ececb6e`; remote main was verified again before handoff. Design authority: approved prototype `76b4a1552c86266442bcff96fd6c5528dea4e47e`. PR #64 is not the design authority and remains untouched.

## Visual evidence

These are the integrated application, built by Vite, using real Nexus authentication and API handlers against a newly created disposable SQLite database. Names, enrollment, XP and progress in this database are synthetic fixtures, not live student records. The primary action and displayed counts were checked against actual API responses in each capture.

| Today viewport (DPR 1, height 900) | Light | Dark |
| --- | --- | --- |
| 1440 desktop | [Screenshot](today-light-1440.png) | [Screenshot](today-dark-1440.png) |
| 1280 desktop | [Screenshot](today-light-1280.png) | [Screenshot](today-dark-1280.png) |
| 390 responsive | [Screenshot](today-light-390.png) | [Screenshot](today-dark-390.png) |

Side-by-side boards: [Light](comparison-light.png), [Dark](comparison-dark.png). Each contains 1440 and 1280 comparisons at native screenshot width, without rescaling. The approved 1440 images come directly from commit `76b4a15`; the approved 1280 images were rendered read-only from that same unchanged prototype. No screenshot pixels were retouched.

The 248px desktop sidebar, hero position (x 276, y 96), native panorama framing, hood placement, tower sidebar/thumbnail, shadow quote, three-card row, four-card Up next area, path and footer scenery follow the approved design. Actual course text changes card heights: the integrated page is about 60px taller at 1440 and 92px taller at 1280. The 390 full-page images retain the fixed navigation at the initial viewport bottom; it stays fixed during ordinary scrolling.

Seven unique runtime assets total **4,804,584 bytes (4.58 MiB)**. Day/night panoramas remain 2172×724, the tower remains 724×2172, with quality-96 WebP encoding and no resizing. Their average RGB difference from the approved WebPs is below 1.45/255. The hood and shadow army are lossless WebP conversions of the approved PNG masters: every decoded RGBA byte is identical. Mist and branding are copied unchanged. Hero ratios and decoded image dimensions are browser-checked; supporting panels use intentional `cover` cropping. No duplicate masters or generated replacement artwork are bundled.

## Focused implementation mapping

| Source | Integration |
| --- | --- |
| Prototype `components.js`, `styles.css`, approved artwork | React learner shell, purpose-specific decorative scenes and scoped Academy theme; existing admin header retained. |
| Existing `buildStudentNavItems`, `isNavItemActive`, `RequireAuth`, `useV2Access`, `useDarkMode` | Reused unchanged for routes, enrollment, access controls and persisted theme. |
| Existing Today continuation and mentor model | Reused unchanged; new cards render its real next action, corrections, review waiting, mastery and completion states. |
| Existing stats, training and V2 curriculum APIs | Real account name/XP/level/streak, legacy completion, V2 lesson groups/lessons/checks/practical status and published path. |
| Existing `getV2Module`, `stageSequenceItems`, `TrainingDestination` | Optional ordered work plan and Up next, with existing availability, destination and document-navigation semantics. Detail failure has its own retry and does not remove Continue. |

## Functionality preserved

- Cookie/session login, logout, protected routes and forced-password-change guard; authentication code is unchanged.
- Per-student V2 enrollment, legacy continuation and server rejection of typed V2 URLs for non-enrolled students.
- Exact server Continue destinations, browser back, available work and prerequisite locks.
- Separate lesson-group, lesson and Quick Check counts; practical approval never substitutes for server-owned mastery.
- Mentor corrections remain secondary while learning is available, and become primary when no learning remains. Waiting, completed, empty, loading and retry states remain available.
- Real XP, level/name and streak, hidden when metadata is absent. No fabricated rank thresholds or historical streak days.
- Existing My Course, Progress, Extra Practice and external Service Desk destinations; keyboard menus, account controls, search and theme persistence.
- Admin authentication, navigation, colors and compact header behavior. Academy overrides apply inside the learner shell only.
- Backend API implementations, enrollment rules, feature-flag files, schema and student records are unchanged.

## Verified

| Check | Result / coverage |
| --- | --- |
| Full frontend Vitest suite | **229 passed**, 39 files. Includes existing Today mentor/continuation/completion cases, auth guards, navigation and V2 enrollment, plus six new evidence-mapping cases. |
| Phase 1 browser suite | **13 passed**, real isolated APIs: six light/dark captures, exact data/route mapping, login/logout, cookie restoration, Continue/back, search, theme persistence, legacy/V2 boundaries, mobile menu, recovery and admin isolation. Failure cases deliberately intercept responses, then recover through the real APIs. |
| Navigation reflow suite | **3 passed**, real isolated APIs: 320–1440 widths, actual learner destinations, menu focus trap/resize restoration, reachable compact-sidebar practice links, unchanged admin reflow. |
| Existing learning UI browser suite | **14 passed**, intercepted API fixtures: lesson/resource viewer, all six interaction input types, ordering feedback/retry, Quick Check feedback, reduced motion and 200% equivalent CSS viewport. This is frontend regression evidence, not backend integration evidence. |
| Focused backend pytest | **30 passed, 1 skipped**: auth/JWT, training, current-week stats and beginner continuation. Disposable SQLite; the PostgreSQL concurrency case requires a separate disposable PostgreSQL database and was skipped. |
| Frontend production build | Pass, including V2-enabled build used for preview; existing large-chunk advisory remains. |
| Dependency audit / whitespace | `npm audit`: zero vulnerabilities. `git diff --check`: pass. |
| Visual/accessibility checks | No horizontal overflow at required widths; decoded art and native hero ratios pass. Main text, secondary/muted text, links and primary button token pairs meet 4.5:1 in both themes. Keyboard focus and menu isolation checked. This is not a full WCAG certification or native browser-zoom certification. |

Navigation tests were adapted from the previous horizontal header to the approved sidebar/mobile structure. Full-stack Today checks now select the approved greeting and primary continuation card (secondary Up next cards only appear when other work is available); their authentication, progress and continuation assertions remain intact. The existing learning test now selects the correct-feedback status explicitly so simultaneous continuation loading does not cause a strict-locator race.

## Gaps and remaining limits

- The prototype's Stage 0/seven-stage example is replaced by the actual published course (four stages in the preview). Cards, titles, counts and destinations vary by enrollment and progress.
- Daily deadlines, daily XP budget, XP-to-next-rank threshold, weekly streak calendar, achievements and notifications lack a suitable API here and are omitted. Work plan lists real available requirements; it does not imply daily deadlines or let a learner award completion. The header shows actual level and XP, and uses the existing Report Issue control.
- Theme settings uses the existing theme toggle. Search uses the existing lessons/commands API; it does not claim to search V2 content, labs or tickets.
- The separate Service Desk application/reverse proxy is not running in this minimal preview. Its document link contract is preserved; end-to-end Service Desk handoff was not tested. No ticket UI was changed.
- Backend integration was tested only on synthetic accounts and SQLite in isolation. No live accounts, production dataset, production cookies/TLS, production PostgreSQL, migration or deployment behavior were exercised. Mentor/terminal-stage variants are covered by unit fixtures, not a fully seeded live-course journey.
- The broader CI full-stack suites use separate specialized synthetic datasets. Their Today presentation assertions have been updated; the final CI results are reported separately from the focused local results above.

## Isolated preview and reproduction

Preview: `http://127.0.0.1:5188/`; API: `http://127.0.0.1:8018`. Forward both ports when reviewing from another machine. Random disposable student and admin credentials stay in a private file printed by the harness, outside Git. Use the `v2` or `legacy` student to compare enrollment behavior.

With backend dependencies installed in a separate Python 3.11 environment:

```sh
cd /home/nexus/worktrees/nexus-academy-integration-phase1
python scripts/e2e/academy_phase1_preview.py
```

In another terminal:

```sh
cd /home/nexus/worktrees/nexus-academy-integration-phase1/frontend
npm ci
VITE_V2_CURRICULUM_ENABLED=true VITE_API_URL=http://127.0.0.1:8018 npm run build
npm run preview -- --host 127.0.0.1 --port 5188 --strictPort
```

The harness always creates a new scratch database, overrides DB/auth/admin configuration before importing the app, and binds loopback only. Set `TMPDIR` to a private cache directory if the host's temporary-storage quota is tight. No environment file, credentials, database, dependencies or browser traces are committed. To rerun the new suite, set `NEXUS_ACADEMY_CREDENTIALS` to the printed private JSON path and `NEXUS_E2E_BASE_URL=http://127.0.0.1:5188`; use `npx playwright test tests/e2e/academy-phase1.spec.js --workers=1`. `NEXUS_ACADEMY_CAPTURE` optionally writes the six captures.

Production checkout/services/data, PR #64 and the approved prototype were not modified. Nothing was merged or deployed. Stop here for owner review before any further implementation phase.

## Exact files changed

- `docs/design/academy-phase1/REVIEW.md`
- `docs/design/academy-phase1/comparison-dark.png`
- `docs/design/academy-phase1/comparison-light.png`
- `docs/design/academy-phase1/today-dark-1280.png`
- `docs/design/academy-phase1/today-dark-1440.png`
- `docs/design/academy-phase1/today-dark-390.png`
- `docs/design/academy-phase1/today-light-1280.png`
- `docs/design/academy-phase1/today-light-1440.png`
- `docs/design/academy-phase1/today-light-390.png`
- `frontend/public/academy/academy-tower-refined.webp`
- `frontend/public/academy/ambient-mist.webp`
- `frontend/public/academy/castle-day-refined.webp`
- `frontend/public/academy/castle-night-refined.webp`
- `frontend/public/academy/hooded-wanderer.webp`
- `frontend/public/academy/nexus-mark.svg`
- `frontend/public/academy/shadow-sentinels.webp`
- `frontend/src/App.jsx`
- `frontend/src/components/academy/AcademyScene.jsx`
- `frontend/src/components/academy/LearnerShell.jsx`
- `frontend/src/components/academy/TodayDashboard.jsx`
- `frontend/src/components/academy/TodayDashboard.test.jsx`
- `frontend/src/components/academy/academy.css`
- `frontend/src/pages/StudentHome.jsx`
- `frontend/src/pages/StudentHome.test.jsx`
- `frontend/tests/e2e/academy-phase1.spec.js`
- `frontend/tests/e2e/forced-password-change.spec.js`
- `frontend/tests/e2e/my-training.spec.js`
- `frontend/tests/e2e/phase0a-live-path.spec.js`
- `frontend/tests/e2e/student-recovery.spec.js`
- `frontend/tests/e2e/global-nav-reflow.spec.js`
- `frontend/tests/e2e/learning-ui.spec.js`
- `scripts/e2e/academy_phase1_preview.py`
- `tasks/loop-log.md`
