# PR #34 CI failure triage

Original run: [35419303637](https://github.com/UnknownShadow00/nexus-admin-academy/actions/runs/35419303637), head `b5cdcf8`, base `research/hybrid-lab-phase0` at `de54127`.

Classification: A = introduced by Hybrid Labs; B = present on the base; C = a runner/checkout assumption present on the base. No original failure was traced to Hybrid Labs. All implicated tests, workflow, authentication/curriculum logic, scripts, and dependency manifests are unchanged between the base and original PR head.

| Failure | Class | Evidence and scoped repair |
| --- | --- | --- |
| Cohort query count 10 versus 9 | B | Reproduced on an exported base snapshot. Wave 4 caches the quiz-attempt schema probe in `Session.info`; compare both cohort sizes with cold capability caches, retaining equal counts and the maximum of 10. |
| Migration guard assumes `backend/nexus.db` exists at revision 0064 | C | Test reads a deployment artifact absent from clean checkouts. CLI tests now copy backend source into a temporary directory and create a synthetic revision marker; migration refusal and unchanged database contents remain asserted. No real default database is opened. |
| Operator script reports interpreter unavailable | C | Reproduced on the base without `.venv`. Test now passes `sys.executable` through the existing `NEXUS_PYTHON` override; operator deployment defaults are unchanged. |
| Four practical migration count assertions | B | Reproduced on base. Commit `4db90b8` made “Anatomy of a Good Ticket” and “Meet the Command Line” required. Current seeds therefore add two required activities and remove two optional ones, without changing the 320 total. These are not INC2504 changes. Preserve historical totals until current seeding occurs; retain migration identity/progress checks. |
| Inventory subprocess and V2 integrity gate | C | Both fail on the same missing `backend/.venv/bin/python`. Inventory test now launches its subprocess with `sys.executable`. |
| Privileged endpoint returns 500 to a student | B/C | Base reproduction logs `admin_auth_missing_env`. Missing configuration previously returned 500 before credential rejection. Return generic 403 while retaining the internal diagnostic; test anonymous, bearer, and invalid admin-key requests with no configuration. |
| Playwright stack startup | C | Actual log fails at `start_local_stack.sh:121` invoking missing `.venv` Python after successful scratch migration/seeding. Select the interpreter once using the existing seed-script convention and use it for all setup steps. |
| Frontend audit | B | Unchanged lockfile contains vulnerable Browserslist and related parser/mapping packages. Refresh only these compatible transitive dependency trees; no audit suppression. |
| Service Desk audit | B | Unchanged Next.js 15.5.22 and sharp 0.35.3 are affected. Patch to Next.js 15.5.24 and sharp 0.35.4 with matching lockfile. No framework-major migration. |
| Deploy simulations | — | Passed in the original run; no deployment behavior is changed. |

Seven representative tests reproduced on the unmodified base snapshot: cohort count, operator interpreter, Phase 4C.1/4C.2/4C.3 counts, V2 admin authorization, and inventory interpreter. Migration guard assumptions are directly visible in the unchanged tests and original runner traceback. Dependency findings are from the unchanged lockfiles and GitHub audit logs.

## Failures exposed after startup was repaired

The existing `my-training` and Service Desk browser specs predate Core Waves 2–5. They expect Dashboard/Learning Path/Skills navigation, pre-prerequisite quiz entry, and “Submit Quiz.” The base already uses Today/My Course/Progress, lesson prerequisite enforcement, and “Submit assessment.” Update the browser contracts to current behavior while retaining real UI grading, authorization, reload, student isolation, desktop/mobile layout, and progression checks. Do not revert application prerequisites to satisfy old tests.

The required quiz test now completes orientation, both required foundational lessons, and both required communication videos through the UI. It checks the locked quiz and its recovery links before completing the missing teaching. The orientation handoff waits for the asynchronously resolved next-activity link instead of racing its temporary module fallback. No browser tests are skipped, and unexpected console/network errors remain asserted.

## Dependency scope

Patched advisories: [Next.js](https://github.com/advisories/GHSA-p293-qw3h-jr36), [sharp](https://github.com/advisories/GHSA-rgj7-g3m4-5g8c), [Browserslist](https://github.com/advisories/GHSA-c83g-rgw3-j3cx).

Frontend audit reports zero vulnerabilities after the update. Service Desk has no high/critical findings; two moderate entries remain for Vitest 3 / `@vitest/mocker` ([advisory](https://github.com/advisories/GHSA-82fw-gwwq-j7x9), patched in 4.1.11). That test-tool major upgrade is deferred rather than silently suppressed. The existing high-severity CI threshold is unchanged.

## Validation

Local validation uses Python 3.12 and Node 22; Actions supplies Python 3.11 and Node 22. Migration and browser checks use disposable SQLite databases and fixture accounts, never production services or Proxmox.

- Frontend: 84 unit tests, production build, CLI validation/sanity, and zero-vulnerability audit pass.
- Service Desk: lint, all workspace typechecks, 519 unit tests, production build, and high-severity audit gate pass.
- Backend: Ruff, compilation, dependency consistency, and manifest-based `pip-audit` pass with no known vulnerabilities.
- V2 P0 integrity gate: all 41 tests pass, including the inventory subprocess. Scratch curriculum validation confirms 11 stages, 35 modules, 320 mapped activities, and 137 mapped videos; SQLite integrity and foreign keys pass.
- Script checks: shell syntax, 287 deployment failure-simulation assertions, and 23 predeploy container-check assertions pass using fake services only.

All live-POC production blockers in [INC2504-LIVE-TEST.md](INC2504-LIVE-TEST.md) remain in force. CI success does not authorize production/student rollout.
