# Nexus Academy Phase 2 — Lesson integration

Owner review only. [Draft PR #66](https://github.com/UnknownShadow00/nexus-admin-academy/pull/66) targets `feature/nexus-academy-integration-phase1` (PR #65), not main. Phase 1 head was fetched and verified as `2ddb099de80e77aed28bf03ef563fc59b7d513c6`; approved `2ddb099` is its ancestor/head. New branch/worktree: `feature/nexus-academy-integration-phase2`, `/home/nexus/worktrees/nexus-academy-integration-phase2`.

## Focused mapping and implementation

Inspected the approved light/dark Lesson images, actual HTML/CSS and responsive rules at prototype `76b4a15`, then the legacy/V2 lesson routes, notes, resources, exercises, completion, enrollment and stage guards. PR #64 was not used as a visual reference.

| Approved design | Existing application integration |
| --- | --- |
| Sidebar, header, themes, account controls | Phase 1 LearnerShell, Academy CSS and assets reused unchanged |
| Title, objectives, content, resources | Legacy getLesson/outcomes/summary/video_url; V2 getV2Lesson/objectives/content_markdown/resources |
| Castle poster and supporting atmosphere | Existing AcademyScene and Phase 1 artwork, no copied or new assets |
| Lesson steps and module list | Actual resource exposure, practice/check statuses, getV2Module; legacy current-module activities only |
| Try it | Existing V2Interaction and all six native renderers embedded; standalone routes retained; existing TicketNoteExercise and OrientationPracticePanel reused |
| Notes and completion | Existing LessonNotes autosave/drafts; legacy completeLesson; V2 completeV2Lesson or beginner server-controlled V2NextStep |

Only Lesson styling was added, scoped under `.academy-lesson`. The 248px Phase 1 sidebar, header, Today, admin UI, backend, API service definitions, authentication, enrollment, feature flags, deployment configuration and assets have no diff from `2ddb099`. Existing legacy orientation copy is retained; its heading now displays the full API lesson title rather than shortening it.

## Preview and evidence

- Isolated React preview: http://127.0.0.1:5189
- Disposable real API health: http://127.0.0.1:8019/health
- Lesson: `/learning-v2/modules/module.nexus.beginner.stage1/lessons/lesson.nexus.beginner.s1.support_work`
- Separate disposable V2, legacy and admin accounts; random credentials are stored outside Git with mode 0600. No live accounts or database were used.
- Reuses unchanged `scripts/e2e/academy_phase1_preview.py --port 8019 --frontend-port 5189`; the Phase 1 name is the harness's existing temporary-directory prefix. This run has its own newly created SQLite database.
- Frontend build: `VITE_V2_CURRICULUM_ENABLED=true VITE_API_URL=http://127.0.0.1:8019 npm run build`.

| Viewport | Light | Dark |
| --- | --- | --- |
| 1440 × 900 | [Lesson light](lesson-light-1440.png) | [Lesson dark](lesson-dark-1440.png) |
| 1280 × 900 | [Lesson light](lesson-light-1280.png) | [Lesson dark](lesson-dark-1280.png) |
| 390 × 900 | [Lesson light](lesson-light-390.png) | [Lesson dark](lesson-dark-390.png) |

Screenshots are full-page, unretouched captures from the real React application and API, before the submission tests. They display existing Beginner Stage 1 content, not the prototype's fictional Stage 0 curriculum. The resource is the actual Nexus support-conversation picture, so its central control is a book rather than a misleading video play action. The castle poster stays 2:1 on desktop, 4:3 on mobile, with cover cropping of the original 2172 × 724 image. No artwork is stretched or duplicated.

[Light comparison](comparison-light.png) and [dark comparison](comparison-dark.png) show all three viewport widths, approved prototype left and integration right, at native screenshot resolution. References were rendered read-only from the unchanged approved prototype worktree at `76b4a15`. Differences in page length, lesson counts, content and completion states reflect the real API. The Phase 1 navigation deliberately remains as owner-approved in PR #65.

Full-page mobile capture places the fixed bottom navigation at the initial viewport boundary. Actual scrolling/control clearance was checked at 390px and 320px; this capture artifact does not mean the navigation appears repeatedly in the scrolling page.

## Verification

| Check | Result and scope |
| --- | --- |
| Frontend Vitest | 234 passed, 39 files; includes completion rejection/retry, late route response, optional catalog failure, resource exposure, notes and all six exercise renderers. Synthetic API mocks. |
| Backend pytest | 117 passed: test_lesson_notes, test_v2_curriculum_api, test_v2_interactions, test_v2_beginner_stages, test_v2_pilot_access, test_v2_required_resource_urls. Real handlers/ORM on isolated SQLite/TestClient, not production. |
| Phase 2 browser suite | 12 passed against the real loopback API and disposable database: six viewport/theme captures, authored lesson data, exercise submission/persistence without false mastery, opened vs watched, sequence/back, legacy notes/completion/reload, prerequisite and enrollment denials, theme persistence and 320px focus/control clearance. Only the deliberate HTTP 500 retry case intercepts its API response. |
| Phase 1 and global navigation browser suites | 16 passed on the same fresh isolated stack before completion mutations: login/logout, legacy/V2 Continue, loading/retry, all Today viewport/theme checks, search, theme persistence, mobile focus/navigation and admin authentication/layout boundaries. |
| Existing learning-ui browser suite | 14 passed using synthetic intercepted API fixtures: teaching-card viewer, six exercise types, feedback/retry, reduced motion and narrow viewport reflow. This is not full backend integration. |
| Today visual regression | Before/after SPA navigation screenshot buffers are byte-identical, including after Lesson CSS is loaded. Phase 1 shell/Today source and assets also remain byte-identical to the base. |
| Build / dependencies | V2-enabled frontend production build passed; npm audit: zero vulnerabilities. Existing bundle-size advisory remains. No dependencies or lockfiles changed. |
| GitHub CI | Run through the draft PR using the existing unchanged workflow; consult its checks for the final result. CI has disposable services, including PostgreSQL. Local SQLite results do not claim production/PostgreSQL validation. |

Geometry assertions verify x=276/y=96 for the desktop title card, 290px lesson guide, 248px sidebar, correct poster ratios, decoded source dimensions, and no document overflow. Keyboard-operated section links transfer focus; existing native exercise controls remain keyboard accessible. Phase 1 text/contrast tokens and focus styles are reused. Mobile navigation and admin reflow checks cover widths down to 320px.

## Preserved functionality and limitations

- Real titles, summaries, objectives, written content, Professor Messer/provider attribution, durations and resource destinations come from existing APIs. Direct YouTube URLs are preserved exactly where supplied; legacy embed-ID rewriting was removed in favor of the approved poster and direct external action. No replacement IDs, video completion automation or external playback availability claims.
- Backend authorization, prerequisite order, group mastery, quick checks, saved submissions/attempt counts, legacy completion, enrollment and current-module navigation remain authoritative. No third progression system or grading change. Passing practice does not complete the beginner lesson; resources and checkpoint still apply.
- Existing saved legacy notes, autosave, drafts and practice flows are retained. V2 has no compatible personal-notes API, so its My notes tab is omitted. Existing interaction form restoration behavior is unchanged; recorded submissions and attempts persist on the server.
- Ask mentor, fictional completion XP and prototype-only concept content are omitted. Objectives and real job-context prose replace fictional content; a one-objective lesson fills the available concept area. Empty optional sections are hidden; unavailable content/links, retries, locks and completed states remain explicit.
- Legacy APIs expose only the current module's catalog. A historical lesson outside that catalog hides the list rather than inventing its neighbors; Back to Learning Path remains available.
- Existing written-answer rules are unchanged: V2 typed answers use normalized accepted terms, and ticket-note practice uses substring/keyword checks. Valid paraphrases can be confusingly rejected. Future educational-validation fix; outside this phase.
- Local integration uses disposable SQLite and development cookies, not live services or production TLS/cookies. Synthetic video/component tests are distinct from real API/browser tests; live YouTube playback was not exercised.

## Exact changed files

Application:
- `frontend/src/components/academy/LessonLayout.jsx` (new)
- `frontend/src/components/academy/LessonVideo.jsx` (new)
- `frontend/src/components/academy/lesson.css` (new)
- `frontend/src/components/v2/V2Interaction.jsx`
- `frontend/src/components/v2/V2ResourceCard.jsx`
- `frontend/src/pages/LessonPage.jsx`
- `frontend/src/pages/v2/V2LessonPage.jsx`

Tests:
- `frontend/src/pages/StudentRecovery.test.jsx`
- `frontend/src/pages/v2/V2LessonPage.test.jsx`
- `frontend/tests/e2e/academy-phase2.spec.js` (new; requires explicit disposable credentials)
- `frontend/tests/e2e/forced-password-change.spec.js` (full real orientation-title assertion)
- `frontend/tests/e2e/my-training.spec.js` (same title assertions)
- `frontend/tests/e2e/student-recovery.spec.js` (same title assertion)
- `frontend/tests/e2e/weeks-1-4-quality.spec.js` (same title assertion; full older Weeks 1–4 journey not run locally)

Evidence/required completion log:
- `docs/design/academy-phase2/REVIEW.md`
- `docs/design/academy-phase2/lesson-light-1440.png`
- `docs/design/academy-phase2/lesson-dark-1440.png`
- `docs/design/academy-phase2/lesson-light-1280.png`
- `docs/design/academy-phase2/lesson-dark-1280.png`
- `docs/design/academy-phase2/lesson-light-390.png`
- `docs/design/academy-phase2/lesson-dark-390.png`
- `docs/design/academy-phase2/comparison-light.png`
- `docs/design/academy-phase2/comparison-dark.png`
- `tasks/loop-log.md`

Production checkout/services, live student data, PR #65's worktree and the approved prototype were not modified. No merge, deployment, curriculum import, Quiz/Ticket/Service Desk/Today redesign or Phase 3 work. Stop for owner visual and functional review.
