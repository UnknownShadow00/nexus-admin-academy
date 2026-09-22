# Validation and coverage ledger

This ledger separates observations from claims. All mutable checks used disposable data. Production was not used as a test target.

## Candidate identities

- Main/production baseline: `07780a98b6f93e76c5744a0af6ec9480cd3105d9`.
- PR #39 final implementation: `b4d57113a401a14ad3b186f9e80cd36b765740f0`.
- PR #40 final implementation: `ab7918573c133a82f31f6e2d9a5fe19bffb781eb` (application code introduced at `ffb823a`; the follow-up adds a regression).
- Resolved combination: `4fc0193e54f28989954c70dca135d18a38538639`, branch `prelaunch/nexus-student-experience-combined-validation`. Its parent is the final PR #39 implementation. Backend application/test files match that parent; its quiz component/tests match the quality branch. Both task-log histories are retained.

The combined branch is a validation artifact, not a merged PR. Final documentation-only commits may follow the implementation SHAs; live CI remains visible on [PR #39](https://github.com/UnknownShadow00/nexus-admin-academy/pull/39/checks) and [PR #40](https://github.com/UnknownShadow00/nexus-admin-academy/pull/40/checks).

## Reproduced regressions

| Failure | Before correction | After correction |
| --- | --- | --- |
| Late StrictMode request / old quiz route | 2 component tests fail | Pass on both branches and combined tree. |
| Failed next quiz route renders prior questions | 1 component test fails | Pass; prior quiz cleared before the load. |
| Accessible↔locked lab route state | 2 tests fail; stale-request guard case already passes | All 3 pass; lab session keyed by lab/V2 route. |
| Evidence on assigned/in-progress retired run after week relock | 2 tests fail | Pass; ownership and published-week restrictions retained. |
| Distinct instructor assignments sharing seed content refs | 1 test fails | Pass over two synchronization passes; identity/requirements/estimates/metadata retained. |
| Retired V2 template with revoked pilot/inactive module/inactive assessment | 3 cases fail; published cases already pass | All 6 parameter combinations pass for VM status/access and evidence. No real VM is used. |

## Final local runs

- Quality: `npm test` — **90 passed**; production build passed; npm audit zero vulnerabilities; `cli:validate` **48 lessons**; `cli:sanity` passed.
- PR #39: **70 frontend tests**; final focused backend curriculum/V2/gating/lab suite **84 passed**. Earlier upload/security verification **62 passed** and lab/gating/availability **50 passed**. Ruff, compilation, pip check and manifest audit passed.
- Full PR #39 backend run before the final follow-ups: **1,206 passed, 2 skipped** at `1303c55`, approximately 668 seconds. Do not label that local run as the final commit; current-head full-suite CI is separate.
- Combined tree: **93 frontend tests**, **84 focused backend tests**, production build and npm audit passed.
- Quality fresh-stack browser run: **27 + 2 + 1 = 30 passed**.
- Combined fresh-stack browser run: **27 + 2 + 1 = 30 passed** against final combined code.
- The 27-test browser command included `forced-password-change`, `my-training`, `student-recovery`, `service-desk-integration`, and `weeks-1-4-quality`, with one worker. It was followed by `p1-service-desk-workspace` (2) then `p0-service-desk-beginner` (1), in that order because completion affects the shared assignment fixture.
- Service Desk local lint/typecheck/build and workspace tests passed: engine 268, UI 36, shared 37, web 176 = **517**. Existing Turbo cache was used for some tasks. CI separately runs its workspace checks and container smoke. High-severity audit gate passes; two moderate package findings for one Vitest advisory remain documented.
- Combined fresh database: migration `0072_weeks_3_4_prelaunch_quality`, integrity `ok`, **zero foreign-key violations**. Synthetic progression through Week 12 is byte-for-byte equivalent to the stored model report.

## Remote CI

- PR #39 implementation `b4d5711`: [CI run 35711110244](https://github.com/UnknownShadow00/nexus-admin-academy/actions/runs/35711110244) passed all six jobs. Full backend: **1,213 passed, 7 skipped**, 10 warnings; manifest audit: no known vulnerabilities. All 19 returned review threads are resolved; final independent review is quota-blocked.
- PR #40 implementation `ab79185`: [CI run 35711252434](https://github.com/UnknownShadow00/nexus-admin-academy/actions/runs/35711252434) passed all six jobs. Full backend: **1,192 passed, 7 skipped**, 10 warnings; manifest audit: no known vulnerabilities. Frontend, browser integration/recovery, database/migration/seeds, Service Desk/container, and deployment failure simulations all pass.
- CI uses a shallow checkout; historical-commit regression helpers can skip when their pinned commits are unavailable. The full local PR #39 run above used the available repository history and had two skips. The recorded passing/skipped totals are kept separate rather than treating skips as passes.
- Final documentation-only changes rerun CI on PR #40. The implementation SHA and immutable run link above identify the tested application; the PR checks link identifies the current documentation head.

## Master-prompt coverage

| Phases | Evidence / completed work | Limit |
| --- | --- | --- |
| 0–1 Preserve and PR #39 | Original dirty worktrees preserved; remote main used; all returned findings reproduced/fixed/resolved; all six current implementation CI jobs pass. | Final independent Codex review is unavailable due account quota. |
| 2–3 Product audit and research | Source, seeded data, real browsers, primary/institutional learning research, W3C guidance, and a labelled UX pattern. | Findings distinguish research from inference; no claim of improved measured learner outcomes. |
| 4–5 First ten minutes/navigation | Disposable temporary credentials, password rotation, Today, orientation, quiz, Week 1 lesson/practice/ticket, Progress; vocabulary specification. | A full first week is not a ten-minute promise. |
| 6–7 Quiz deep dive/design | Actual request/storage/submit code, regressions, mobile/keyboard/fault injection, detailed before/after/retry/review specification. | Formative immediate-feedback mode remains proposed. |
| 8–10 Lesson/practice/Service Desk | Notes and completion recovery; CLI catalog/engine; real Service Desk tool/evidence/note/resolve paths and screenshots. | CLI partial-state and unsent ticket-note reload loss remain findings. |
| 11–13 Progression/A+/Network+ | Required activity map, 13 synthetic checkpoints, prerequisite tests, historical/custom/V2 regression coverage. | Synthetic completion records do not prove every Week 5–12 exercise is solvable in its UI. |
| 14–15 Mobile/accessibility | Quiz 375/390/768/1440px measurements, native keyboard controls, 44px targets, focus/status/error semantics; representative other screens. | No full screen-reader, contrast, 200% zoom, Safari, or every-dialog certification. Admin screenshot is desktop. |
| 16–17 Failure/persistence | HTTP 500 distinction, failed submit/save recovery, stable refresh order/place, learner isolation, stale requests, in-flight note edits. | Multiple open tabs can still create separate server attempts; no cross-device conflict resolution. |
| 18–20 Instructor/auth/performance | Admin field/workflow audit, reset/rotation/session/ownership tests, removed redundant quiz GET, recorded build warning. | No real account edits; no production performance measurement. |
| 21–24 Audit, priorities, implementation | Audit written before product edits; scoped main-based branch; concrete UX specs and safe implemented subset. | No broad curriculum rewrite or new migration on PR #40. |
| 25–26 Journey/chaos | Real login→orientation→Week 1 browser journey; structured Weeks 2–4 browser exercises; synthetic complete progression; logout/reset/offline/refresh/failure/retry/direct-lock checks. | No claim of one uninterrupted browser-only completion of all four weeks; not every cross-tab race is solved. |
| 27–30 Validation/review/PR/evidence | Local suites and remote CI; fresh self-review; PRs open; resolved combination; safe reviewed screenshots. | Codex quota blocks final independent review. |
| 31 Handoff | Twenty-section prelaunch report, exact candidates, follow-ups and first-fortnight plan. | No merge or deployment authorization exercised. |

## Known test-environment incidents

The first quality stack requested a port used by an unrelated development server. Vite chose another port, while readiness hit the requested one. Tests were stopped, only owned process groups were terminated, and the new preflight/strict-port behavior was verified against an occupied listener. The unrelated server was preserved. Fresh starts also support recently closed ports without mistaking TIME_WAIT for a live listener.

A repeat against a reused fixture failed because an earlier spec had advanced the nominally fresh learner. A clean stack passed all 30 checks. Earlier Service Desk test order and cold development startup caused isolated failures; ordered warm reruns passed. A build/cache restore colliding with an isolated Next development server was resolved by restarting only that test stack. These incidents are not presented as product failures or silently omitted.

Old UI assertions for Skills, the save indicator, and review labels were deliberately updated with the product changes. One new test's visible-text/textContent mismatch was corrected before the successful full run. Genuine product regressions were reproduced and fixed rather than repeatedly rerun.

## Cleanup

Disposable audit-created users are deleted in `finally` blocks. The three owned stack directories (databases, uploads, cookies, fixture credentials) and model database copies were removed. Startup logs containing generated exports and failed-run browser traces were removed after preserving only safe screenshots and summarized evidence. Package environments and clean feature worktrees remain available for review. Original production and Weeks 3–4 dirty worktrees retain their original HEADs and file-status lists.
