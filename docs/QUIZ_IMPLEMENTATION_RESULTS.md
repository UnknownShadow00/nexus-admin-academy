# Quiz Implementation Results

Implementation date: 2026-07-19 UTC

## Outcome

- Alembic head: `0029`
- Live database integrity: `ok`; foreign-key check: no violations
- Content preserved: 104 quizzes and 967 questions
- Required checklist: 25 quizzes, exactly one for every Week 0–24
- Active student-visible metadata: 99 quizzes; 5 superseded merge sources are preserved and archived
- Certification quizzes required: 0
- Confirmed broken answer keys corrected: 120
- Required/gate/cumulative explanations: 196/196 complete
- Whole corpus explanations: 333 complete, 634 optional imported questions still missing explanations

## Week balance

| Week | Required | Practice | Conditional remediation | Cumulative/gate | Required questions | Optional questions* | Coverage note |
|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 1 | 0 | 0 | 0 | 4 | 0 | Core assessment present; practice remains weak |
| 1 | 1 | 0 | 0 | 0 | 8 | 0 | Properly covered |
| 2 | 1 | 3 | 3 | 0 | 19 | 72 | Well supplied; optional load must remain opt-in |
| 3 | 1 | 5 | 2 | 0 | 10 | 52 | Well supplied; optional load must remain opt-in |
| 4 | 1 | 2 | 0 | 1 | 6 | 19 | Properly covered |
| 5 | 1 | 2 | 0 | 0 | 8 | 17 | Properly covered |
| 6 | 1 | 1 | 0 | 0 | 9 | 11 | Properly covered |
| 7 | 1 | 4 | 3 | 0 | 8 | 53 | Well supplied; optional load must remain opt-in |
| 8 | 1 | 3 | 1 | 1 | 8 | 35 | Properly covered |
| 9 | 1 | 1 | 2 | 0 | 8 | 28 | Properly covered |
| 10 | 1 | 0 | 0 | 0 | 7 | 0 | Core assessment present; practice remains weak |
| 11 | 1 | 4 | 1 | 0 | 7 | 48 | Well supplied; optional load must remain opt-in |
| 12 | 1 | 0 | 0 | 1 | 7 | 0 | Core assessment present; practice remains weak |
| 13 | 1 | 0 | 2 | 0 | 8 | 12 | Properly covered |
| 14 | 1 | 0 | 0 | 0 | 7 | 0 | Core assessment present; practice remains weak |
| 15 | 1 | 0 | 0 | 0 | 7 | 0 | Core assessment present; practice remains weak |
| 16 | 1 | 0 | 1 | 1 | 8 | 7 | Properly covered |
| 17 | 1 | 0 | 0 | 1 | 7 | 0 | Core assessment present; practice remains weak |
| 18 | 1 | 1 | 2 | 0 | 8 | 23 | Properly covered |
| 19 | 1 | 0 | 0 | 0 | 8 | 0 | Core assessment present; practice remains weak |
| 20 | 1 | 0 | 0 | 1 | 8 | 0 | Core assessment present; practice remains weak |
| 21 | 1 | 2 | 0 | 0 | 8 | 31 | Properly covered |
| 22 | 1 | 0 | 0 | 0 | 8 | 0 | Core assessment present; practice remains weak |
| 23 | 1 | 1 | 0 | 0 | 4 | 10 | Interim 4-question required bank; weak until future scenario phase |
| 24 | 1 | 0 | 0 | 1 | 6 | 0 | Core assessment present; practice remains weak |

\* Optional questions exclude the separate 29-bank certification library. Remediation questions are conditional and do not appear until assigned or triggered.

## Organization totals

- `required`: 18 total / 18 active
- `practice`: 33 total / 29 active
- `remediation`: 17 total / 17 active
- `cumulative`: 2 total / 2 active
- `gate`: 5 total / 5 active
- `certification`: 29 total / 28 active

## Remaining editorial work

- 634 optional imported questions still need explanations and full key validation; they remain non-required.
- 31 quizzes are `needs_edit`, 40 remain `unreviewed`, 28 are `validated`, and 5 are `archived`.
- Weeks 0 and 23 use small existing imported banks as safe interim assessments; Week 24 uses the repositioned six-question Integrated Operations Readiness gate. The proposed 60 new scenarios remain a separate future phase.
- Seed single-answer bias was safely reduced with a deterministic, idempotent swap that preserves the correct answer text and skips multi-selects. Required seed distribution is A 32, B 41, C 37, D 42.

## Verification record

- Fresh coherent online backup: `backend/nexus.db.quiz-organization-online-backup-20260719T111718Z`; integrity `ok`, 104/967.
- Migration rehearsal on a disposable live snapshot: `0029`, integrity `ok`, 104/967, no foreign-key violations. The rehearsal caught and prevented an unsafe SQLite batch-table strategy before live application.
- Backend compile: pass. Backend tests: **161 passed**.
- Fresh seed database: repeated runs produced 25 quizzes / 189 questions, organization digest `93f31b4a0bf3105df23dd1893f3ecdc02a23e1e4276090d283874ff3af5aaa1c`, answer-content digest `b146dab186378fc5348c04d0274683f69657d0e36504ff38f541c45079c0bc06`, and zero students/attempts/assignments. Live seed runs preserved 104/967 and the student-data digest `47981f36a12965394fad90aa43c290f67bd1c5c04e1ff1b716e4d7be079b886f`; five required-quiz gate definitions are present.
- Placement rerun: 0 changes. Correction rerun: 0 stored-key changes.
- npm audit: **0 vulnerabilities**. Vite production build: pass; admin pages remain separate chunks.
- Disposable application smoke test on a live-data snapshot: Week 0 required quiz blocks at 0%, remediation is hidden, certification required count is zero, admin pagination returns all 104 over three pages, search finds Quiz 25, and corrected q1114 grades accurately.
- Live post-test readback: 104 quizzes, 967 questions, 7 pre-existing students, 0 attempts, 0 remediation assignments, integrity `ok`, no foreign-key violations. No live student data was created or changed by testing.

## Editorial protection pass — 2026-07-19 UTC

- A fresh online SQLite backup was created at `backend/nexus.db.editorial-review-backup-20260719T114445Z`; it passed integrity checks at 104 quizzes / 967 questions.
- `backend/scripts/quarantine_unvalidated_quizzes.py` was run dry first and then confirmed in one transaction. It moved 71 active, unvalidated imported quizzes to admin-only editorial review by disabling practice-library visibility and normalizing pending records to `needs_edit`. No quiz/question IDs, placements, question content, or student data changed.
- Student API visibility now requires `published`, active, `editorial_status=validated`, and `answer_keys_validated=true`. The same guard protects list, detail, submit, review, and week-plan queries. The live database has 28 validated student-visible quizzes and zero quizzes satisfying the student visibility predicate while unvalidated.
- The admin editorial queue is paginated and prioritizes practice, remediation, cumulative/gate, certification, then archived merge sources. It contains 76 pending/archived imported banks and reports actual question counts and missing explanations.
- No additional imported question was marked validated in this safety pass. Pending editorial work remains source-backed, question-by-question review; see `QUIZ_EDITORIAL_REVIEW_LOG.md` and `QUIZ_WEAK_WEEK_EXPANSION_PLAN.md`.
- Backend compile and full test suite passed: **164 passed**. Alembic remains `0029 (head)`. `npm audit` reported **0 vulnerabilities** and the production frontend build passed.

## Final live verification — 2026-07-20 UTC

- After the authorized service restart, `nexus-admin-academy.service` was
  active and `http://127.0.0.1/health` returned HTTP 200 before and after
  testing. The restart log contained no startup, migration, database, or
  import errors.
- With one disposable student, validated required quiz #2 appeared in Required
  for Week 3 and validated optional practice quiz #3 appeared in Practice.
  The required quiz moved from `available` to `done` after a correct
  submission and produced one mastery attempt. The optional submission left
  the required quiz `available` and produced zero mastery rows.
- Unvalidated quiz #65 was absent from This Week, All Weeks, Practice,
  Remediation, and Certification Library. Direct student detail and submission
  requests each returned HTTP 404.
- The admin editorial queue returned HTTP 200, included quiz #65, and reported
  76 pending quizzes. Admin visibility is preserved while student access is
  blocked.
- The disposable account was deleted through the supported admin endpoint.
  A complete table readback found no records remaining with its `student_id`
  or `user_id`, including attempts and progress rows. SQLite `integrity_check`
  returned `ok`; `foreign_key_check` returned no violations.

Final status: **Ready for manual-VM cohort**. The 76 pending quizzes remain
admin-only editorial work and were neither reviewed nor changed here.
