# Core Wave 1: assessment reporting

## Initial reproduction

Base: `77621d1` on `feature/service-desk-p1-workspace`. The original worktree contained an audit document and a loop-log change. Neither was altered. Implementation uses a clean child worktree on `fix/core-wave1-assessment-truth`, preserving the complete Service Desk P0/P1 ancestry, including `c11348e`, `bcc9957`, `c18e968`, and `77621d1`.

Strict desired-behavior tests were written and run before behavior changes: 10 backend failures and 5 frontend failures. Browser regressions then failed on Today and saved review. A subsequent isolated checkout of the same base reproduced the failures again and captured fully loaded screenshots. All data came from generated fixtures, not production copies.

| Bug | Observed baseline proof |
| --- | --- |
| A: 4/4 becomes 4% | `/stats.recent_activity` returned raw `score: 4`; Today appended `%`. The baseline browser explicitly found `Score 4%`, then failed the `Score 100%` assertion. |
| B: failed event called passed | Submitting 0/4 inserted `SquadActivity.activity_type = quiz_passed`. The strict assertion expected `quiz_failed`. |
| C: earlier failure reopened | Submitting 0/4 then 4/4 returned review `score: 0`. The query used unordered `.first()`. Baseline browser also reproduced failure then pass on a two-question quiz and reopened 0%. |
| D: false mastery | Perfect 2/2 and 6/6 submissions produced a domain `mastery_percent` of 13.3, from raw-count averaging and ticket weighting. The UI rendered that diagnostic as `Skills Mastery`. |
| E: raw admin mean | `avg_quiz` averaged `QuizAttempt.score`: perfect 2/2 and 6/6 yielded raw mean 4, with no percentage contract. The strict normalized-field assertion failed. |

Evidence: `backend-before.txt`, `frontend-before.txt`, `browser-before.txt`; independently repeated baseline evidence in `backend-baseline-verified.txt`, `browser-baseline-verified.txt`, and `before-screenshots/`. The repeated baseline checkout ran 15 expanded regression cases, all red.

A separate failing StrictMode test proved that an older quiz-load response could replace a newer active quiz. A request sequence guard now rejects stale responses. This is an assessment-integrity fix, not a quiz-platform redesign.

## Score contract

`backend/app/services/quiz_scores.py` defines `AttemptScore`:

- `correct_count`: raw count for this attempt, preserving the stored `score` meaning.
- `question_count`: saved result snapshot length; never today's bank size when a snapshot exists.
- `percentage`: `correct_count * 100 / question_count`, rounded to two decimal places; null if unrecoverable/invalid.
- `passed`: exact count/denominator comparison against the threshold, before percentage rounding; null if unknowable.
- `passing_percentage`: 70 for historical V1 attempts; new result snapshots also retain the threshold.
- `attempt_id`: stable database identity.
- `submitted_at`: submission timestamp.
- `score_basis`: `saved_results` or `current_bank_legacy_estimate`.

The API adds `latest_attempt`, `best_attempt`, `earned_pass`, and an ordered attempt history. No schema migration was added. Existing raw `score`, `best_score`, `avg_quiz`, and other legacy raw diagnostics retain their meanings. Current consumers use explicit score summaries; deprecated raw averages are labeled in API metadata rather than silently reinterpreted.

## Today

4/4 → 100%; 3/4 → 75%; 0/4 → 0%. Each recent activity is an individual attempt with count/total, pass state, identity, submission time, and a link to that specific attempt. It does not substitute the best attempt's score. Service Desk scores retain their existing percentage contract.

## Event semantics

New passing submissions log `quiz_passed`; failures log `quiz_failed`. Event details include attempt identity, count/total and percentage. Consumers were inspected: the activity feeds forward the type and details; progression gates read attempts rather than event names. No historical events were changed.

A future historical analytics backfill may be appropriate if old `quiz_passed` rows are counted as actual passes. It must reconcile against attempt evidence. Older event rows lack an attempt foreign key, so title/time matching alone is not sufficient for a blind backfill. No backfill or production mutation is included.

## Attempt review

Default review selects the latest `(completed_at, id)` deterministically. `?attempt_id=` selects a particular attempt, scoped to the requested learner and quiz after access checks. The UI labels latest versus historical review, identifies the attempt, shows pass state and the separately labeled best result, and exposes history links. Refresh preserves an explicit selection. Missing or another learner's attempt ID returns 404.

Question text, choices, explanations, and correctness come from saved results. Old responses are not regraded against an edited bank. For pre-snapshot history, the original answers are unavailable and the denominator estimate is disclosed. An impossible legacy denominator produces no fabricated percentage or pass state.

## Latest vs best

- Latest: greatest submission time, then greatest attempt ID.
- Best: highest score ratio among valid recorded attempts; ties choose latest time/ID.
- Earned pass: any recorded passing attempt. Pre-append-history `best_score` credit recognized by the existing completion rule is also retained, with `legacy_passing_credit` explicitly disclosed; no missing passing attempt or percentage is fabricated. A later lower score does not erase completion.
- Today: individual recent attempts.
- Saved review: latest by default, or explicitly selected history.
- Progress/mentor detail: separately labeled latest and best attempts plus earned completion.
- Training week and quiz library: best result is explicitly labeled; review opens latest.
- Admin average: mean of required-quiz attempt percentages, including retries; it is labeled as an average attempt percentage, not mastery. Older estimated totals are disclosed in its heading tooltip.
- Progress's retained average is the mean of per-quiz best percentages, with duplicate curriculum references removed from that average. No attempts is displayed as no scored attempts.

## Skills Mastery

Removed the legacy numeric Skills Mastery widget from the shared learner-detail presentation. Current learner surfaces do not render that legacy number. Admin detail now shows required quizzes passed/total and explicit assessment evidence. Existing Progress completion counts remain.

Historical mastery aggregates and their compatibility APIs remain intact, labeled `legacy_internal_non_competency`. Their existing write behavior remains for compatibility; no new competence, readiness, or AI formula was introduced. No current learner/admin mastery widget consumes them.

## Historical safety

Regression coverage includes no attempts, one/several attempts, failure→pass, pass→failure, identical timestamps, mixed quiz sizes, edited and emptied banks, original saved answers, missing snapshots, impossible denominators, and unauthorized historical selection. Earned passing completion remains monotonic for saved attempts even if the current question bank grows or disappears. Pre-append-history rows that retain only a prior `best_score` keep their existing earned credit, explicitly labeled as lacking the original passing attempt. A strict regression reproduced this compatibility case before its fix. Pre-snapshot totals cannot be recovered exactly after unrecorded bank edits; that limitation is explicit rather than hidden.

## Screenshots

All screenshots use a disposable local fixture:

- `screenshots/failed-result.png`
- `screenshots/passed-result.png`
- `screenshots/today-after-pass.png`
- `screenshots/saved-review-after-fail-pass.png`
- `screenshots/progress-after-pass.png`
- `screenshots/admin-learner-summary.png`

Baseline screenshots: `before-screenshots/today-4-percent.png` and `before-screenshots/review-earlier-failure.png`.

## Tests

Final validation results and exact commands are recorded in `VALIDATION.md`. This includes focused backend contracts and V1/V2 gates, frontend tests, Service Desk tests and browser gates, local production builds, lint/typecheck, Ruff, compileall, formatting, and whitespace checks.

Dependency audits: Python reports no known vulnerabilities. The unchanged frontend lockfile reports one high Browserslist advisory and one low postcss-selector-parser advisory. These are existing build-tool dependency findings, recorded in `npm-audit.txt`; no dependency upgrades were folded into this wave. The Vite build also retains its large-chunk warning. The main frontend is JavaScript and has no configured TypeScript gate; the configured Service Desk typecheck passes, and touched core JavaScript was explicitly linted and built.

The Service Desk P1 desktop test read URL state immediately after navigation. It now waits for the expected URL transition; no Service Desk application behavior was changed. Desktop, mobile and P0 browser assertions remain intact.

## Git

Dedicated branch: `fix/core-wave1-assessment-truth`. Implementation commit: `ba6b411` (`fix(core): report quiz attempts and earned progress truthfully`). The following documentation commit records this report, evidence and the completion log. See the final handoff for clean status. No merge or push is included. The original worktree's audit changes remain untouched.

## Deferred Core Wave 2

- Beginner entry path.
- First quiz prerequisites and untaught concepts.
- My Course/navigation.
- Locked-state recovery.
- Required/optional teaching alignment.

Also deferred: prerequisite sequencing/enforcement, practice-versus-assessment redesign, answer exposure/retry pedagogy, lesson/Quick Check redesign, full Today/Progress/mentor redesign, Service Desk P1 Wave 2, and VM/Proxmox proof of concept.

## Production safety

No production connection, deployment, migration, content load, student enrollment, or merge to main was performed. The user-provided production baseline—schema `0064_v2_ai_grading_infrastructure`, V2 OFF, no pilot enrollment—was left untouched; it was not re-queried remotely. Core browser fixtures kept V2 OFF. Existing V2 regression gates used only isolated, generated test identities and disposable databases; no real pilot enrollment occurred. Local builds and fixture schema creation are not deployments or production migrations.
