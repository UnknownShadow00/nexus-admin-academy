# Final Prelaunch Hardening Report

Date: 2026-08-08
Branch: `prelaunch/final-hardening`

## 1. Scenario Builder

- Reused the existing Service Desk scenario/version tables and admin router rather than creating a second persistence system.
- Added admin-only create, detail, draft update, validate, publish, and safe-delete behavior.
- Incomplete drafts can be saved, but publishing requires server validation. Published versions are immutable; editing after publish creates the next draft version.
- Preview and test-student tooling now load definitions from Nexus. Local storage remains only for disposable test-student recovery data.
- Integrated browser coverage proves create, UI save, refresh/reload, publish, immutable version 1, and new version 2 draft behavior.

## 2. Questions

- Total questions: 966.
- Missing explanations before: 633.
- High-confidence explanations added: 234.
- Missing explanations after final red-team correction: 397. None are currently student-visible because the affected banks have not passed the centralized editorial visibility gate.
- Human-review IDs and reasons are recorded in `docs/question_explanation_review.json`. IDs 647 and 651 were confirmed against Microsoft documentation, corrected to Task Manager and Device Manager respectively, and now have reviewed explanations.
- The signature-based catalog is used by migrations and import flows so reviewed explanations survive reseeding/importing.

## 3. Previously Unmapped Quizzes

- Original: 71.
- Safely mapped as optional: 6; required blockers added: 0.
- Practice: quizzes 28, 32, 33. Remediation/review: quizzes 56, 59, 63.
- Intentionally left unmapped and student-hidden: 65, pending explanation and answer-key review.
- Full A-F classification is in `docs/unmapped_quiz_mapping_report.json`.

## 4. Curriculum

- Weeks 0-24 remain structurally valid.
- Week pages now show a clear required path grouped as Learn, Quiz, Practice, and Review, with one highlighted next action and required progress.
- Optional material is collapsed under “Extra practice” and explicitly does not affect completion, removing the card-wall problem in Weeks 2, 3, 4, and 10.
- Week 20 was reduced from 10 required / 19 total to 5 required / 19 total. Five duplicate security videos remain useful optional material; the required path now stays focused on Linux operations.

## 5. Service Desk Content

- Reviewed and scored all 13 active definitions and all 8 assigned runtime scenarios. The complete scorecard is `docs/service_desk_scenario_quality_report.json`.
- Changed INC2402 and INC2404 through new published versions, preserving prior attempt history.
- INC2402 now uses one failing scanner beside a working peer and a progressive scope/adapter/repair/verification hint ladder.
- INC2404 now requires diagnosis, marking the headset damaged, shipping a headset replacement to the correct requester, and meaningful technician notes. This also fixed INC2404's previously impossible server grading contract.

## 6. React Router

- Before: `react-router-dom` 6.30.4.
- After: `react-router-dom` 7.18.2.
- Declarative routes, redirects, auth/admin guards, back navigation, Service Desk links, 404 handling, and browser flows pass. `npm audit`: 0 vulnerabilities.

## 7. Xterm

- Before: `xterm` 5.3.0 and `xterm-addon-fit` 0.8.0.
- After: `@xterm/xterm` 6.0.0 and `@xterm/addon-fit` 0.11.0.
- CLI validation covers 48 lessons. Browser tests cover xterm rendering/input/mobile resize and CLI command validation/completion/restart.

## 8. Performance

- Main production JS before: 1,009.72 kB (282.65 kB gzip).
- Main production JS after: 302.30 kB (99.39 kB gzip), a 70.1% raw reduction and 64.8% gzip reduction.
- Student route-level lazy loading joins the existing admin splitting. Heavy ticket, CLI lab, lesson catalog, and xterm functionality are no longer in the first-load chunk.

## 9. Student UX

- Preserved the primary Today / Service Desk / Progress navigation and grouped secondary material under Extra Practice.
- Added path-oriented week grouping, optional-content disclosure, required-path progress, a clear 404 recovery action, quiz retry/load recovery, multi-select checkmarks, submission guarding, and explicit explanation cards.
- Quiz language now explains the workflow before answering and offers “Continue Learning” after review.

## 10. Admin UX

- Scenario actions now save and publish on the server with clear validation errors and publish/delete confirmation.
- Fixed Service Desk middleware so a verified Nexus admin cookie can access the builder without also requiring a student JWT; mentor access remains supported and unauthorized access still fails closed.
- Existing quiz import/edit/publish and weekly training admin browser flows pass.

## 11-14. Regression Results

- Backend: 338 passed; Alembic head `0041_verified_question_keys`.
- Service Desk: lint, typecheck, build, and audit passed; 251 tests passed; no known vulnerabilities. One existing non-fatal Next.js ESLint-plugin configuration warning remains.
- Frontend: `npm audit`, production build, `cli:validate`, and `cli:sanity` passed; 0 vulnerabilities.
- Integrated launch verification: 9/9 passed, including real UI completion for INC2402 and INC2404. Full isolated browser suite: 22/22 passed.

## 15-17. Remaining Work and Launch Status

- Confirmed remaining application bugs: none found by the completed regression/browser pass.
- Content-quality backlog: 397 explanations and 65 intentionally hidden quizzes require human editorial review.
- Launch blockers: no technical blocker found. The hidden editorial backlog should not be exposed until reviewed.

## 18. Version-Control Safety

- No push, PR, merge, or production deployment was performed.
