# Wave 1 validation

## Results

- Backend: 256 unique tests pass: 252 combined focused/shared tests in `backend-after.txt`, plus 4 study-tracker/squad tests in `backend-additional.txt`. The final additive saved-question compatibility change also passed all 33 quiz/contract tests in `final-review-contract.txt` (overlapping tests, not counted twice).
- Core frontend: 61 tests pass across 19 files, recorded in `frontend-after.txt`.
- Core browser: 4 passing real-browser flows, using the real API and a fresh temporary SQLite database.
- Service Desk browser: 2 P1 checks (desktop/mobile) and 1 P0 authenticated integrity flow pass.
- Service Desk unit tests: 517 pass (shared 37, simulation engine 268, UI 36, web 176); the API package contains no tests.
- Core Vite production build and Service Desk Next production build pass. Nothing was deployed.
- Service Desk lint and TypeScript checks pass. Touched core JavaScript passes explicit ESLint correctness rules using `core-eslint.config.mjs`; the core JavaScript package has no native TypeScript configuration/script.
- Ruff on touched Python, compileall, scoped formatting checks and `git diff --check` pass.
- Python dependency audit: no known vulnerabilities. Frontend dependency audit: unchanged lockfile has 1 high Browserslist and 1 low postcss-selector-parser advisory; see `npm-audit.txt`. No dependency updates were made.

## Backend command

Run from `backend` in the isolated checkout, with its dependencies installed:

```bash
DATABASE_URL=sqlite:///:memory: .venv/bin/python -m pytest \
  tests/test_quizzes.py tests/test_quiz_organization.py \
  tests/test_training_service.py tests/test_training_api.py \
  tests/test_admin_students.py tests/test_admin_training_api.py \
  tests/test_student_data_integrity.py tests/test_core_wave1_truth.py \
  tests/test_gate* tests/test_week_prerequisite_gating.py tests/test_onboarding.py \
  tests/test_v2_v1_quiz_safety.py tests/test_v2_content_and_assessment.py \
  tests/test_v2_assessment_availability.py tests/test_v2_constrained_selection.py \
  tests/test_v2_pilot_access.py tests/test_v2_mentor_intelligence.py \
  tests/test_service_desk_p0_integrity.py tests/test_service_desk_v2_inventory.py \
  tests/test_v2_service_desk_onboarding.py tests/test_service_desk_contract_gate.py \
  tests/test_service_desk_progression.py -q

DATABASE_URL=sqlite:///:memory: .venv/bin/python -m pytest \
  tests/test_study_tracker_mapping.py tests/test_squad_dashboard.py -q
```

All pytest database fixtures are disposable. V2 gate tests use isolated test-only switches/identities, not production enrollment.

## Core browser fixture

The fixture forces a newly generated temporary database, test authentication configuration, and V2 OFF. It must be served on loopback with lifecycle startup disabled. It does not read production content or copy a production database.

Generate a disposable `WAVE1_PASSWORD` and make that same value available to the server and Playwright shell. Never commit it. From `backend`:

```bash
PYTHONPATH=.:tests .venv/bin/python -m uvicorn core_wave1_browser_app:app \
  --host 127.0.0.1 --port 8027 --lifespan off
```

From `frontend` in another shell:

```bash
VITE_API_URL=http://127.0.0.1:8027 npm run dev -- --host 127.0.0.1 --port 5187
```

Run against a freshly started fixture, since these serial tests deliberately build one learner's history:

```bash
NEXUS_E2E_BASE_URL=http://127.0.0.1:5187 \
WAVE1_SCREENSHOTS=/tmp/core-wave1-screenshots \
npx playwright test tests/e2e/core-wave1-truth.spec.js --workers=1
```

The four flows cover fail→Today→pass→Progress→latest review→historical review→refresh, 3/4 and a failed retry after a pass, mixed sizes, and admin evidence. The fixture process cleans up its temporary database on exit.

## Service Desk gates

The existing isolated stack was created at `/tmp/core-wave1-service-desk-verified` with backend/frontend/Service Desk ports 8028/5188/3028. It uses generated disposable accounts and fixture-only V2 configuration. Run P1 before P0, as the existing CI requires:

```bash
set -a
source /tmp/core-wave1-service-desk-verified/stack.env
set +a
npx playwright test tests/e2e/p1-service-desk-workspace.spec.js --workers=1
npx playwright test tests/e2e/p0-service-desk-beginner.spec.js --workers=1
```

The P1 test now waits for the asynchronous URL transition after returning from a tool. It retains every original assertion. No Service Desk application source changed.

## Other commands

- `frontend`: `npm run test`, `npm run build`, `npm audit --audit-level=high`.
- `service-desk-app`: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`.
- `backend`: `.venv/bin/python -m pip_audit -r requirements.txt`.
- Root: `backend/.venv/bin/ruff check` for all touched Python files; `python -m compileall -q backend/app` plus new test files.
- Root: `service-desk-app/node_modules/.bin/eslint --config docs/core-wave1/core-eslint.config.mjs` with touched core JS/JSX and browser-test paths.
- New Python files and the refactored quiz router were fully Ruff-formatted and checked. Modified ranges in other Python files were formatted without rewriting unrelated code. New JSX/tests were Prettier-formatted and checked; existing JSX retains its local formatting style.
- Root: `git diff --check`.

Build warnings were pre-existing large Vite chunks and the Next ESLint-plugin notice. An initial local Next build/dev-output collision was resolved by stopping the dev server and rerunning the build/typecheck before restarting browser fixtures.
