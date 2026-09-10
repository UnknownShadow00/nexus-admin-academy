# Core Wave 5 — Progress and Review Contract

## Initial Progress findings

- The learner page led with a course-wide percentage and six mixed activity cards before explaining what the counts represented.
- “Quizzes completed” could be read as passed assessment evidence even though submitting and passing are different events.
- Lessons, quizzes, guided labs, tickets, role progression, capstones, XP, and streaks competed in one hierarchy.
- Empty role/capstone categories appeared before a new learner had evidence in those areas.
- Today always rendered a large Daily Review panel. A fresh learner, a learner with no review due, and a review API failure could all end at the same “All caught up” copy.
- Weak items exposed question-level repetition but did not provide a learner-facing concept, exact worked-example link, or related practice action.
- Practical records without explicit assistance metadata could not truthfully establish independent work.

## Progress vocabulary

| Label | Learner-facing meaning |
| --- | --- |
| Lesson complete | The learner explicitly finished the lesson; this is not mastery. |
| Practice completed | The learner worked through low-stakes practice; no assessment credit is awarded. |
| Assessment passed | The learner met the threshold on a credit-bearing assessment independently. |
| Guided practice | Practical work completed with procedural assistance. |
| Independent demonstration | Practical work explicitly recorded without procedural guidance. |
| Service Desk ticket passed | An assessment-mode ticket met its stored rubric. |
| Module complete | Every required activity in that module is satisfied. |
| Review due | A missed or scheduled concept is ready for reinforcement. |

The default learner UI does not use “mastered,” “expert,” “job ready,” or a global readiness percentage.

## New Progress hierarchy

1. A+ Foundations and an evidence disclaimer.
2. A fresh-learner start card when no learning history exists.
3. Current module and required activity progress.
4. Learning: required lessons and separate optional practice history.
5. Assessments: required assessments passed, plus compact latest/best evidence.
6. Practical work: guided, independent, historical-unclassified, and Service Desk rubric evidence.
7. Review: zero to three deduplicated, actionable concept priorities.
8. Collapsed course totals and clearly marked planned certifications.

Raw XP, streak, rank/capstone analytics, giant event totals, and empty future categories are not in the beginner default hierarchy.

## Required denominators

- Current module required progress counts only required activities in the current module.
- Current module lessons count required lessons in that module.
- Current module assessments count required assessments passed in that module.
- Current module practical work counts required practical activities in that module.
- Optional practice is filtered to activities whose learning role is `practice`; it never changes required progress.
- Course required lessons and assessments use course-wide required populations and say so explicitly.
- Course required activities are available only in the collapsed secondary section.

## Knowledge vs practical evidence

Assessment pass evidence is shown under Assessments. Lab and ticket evidence is shown under Practical work. The page does not combine them into a score.

## Guided vs independent

Only explicit `assistance_level: guided` or `assistance_level: independent` metadata supplies those labels. Older practical records without that evidence are shown as historical unclassified work and are never inferred to be independent.

## Latest vs best

Each attempted assessment shows Latest, Best, and Passed separately. A weaker latest retry does not erase already-earned passing credit. Detailed history remains behind the saved review link.

## Review prioritization

The ordering is deterministic:

1. New misses with no prior review.
2. Previously reviewed items rated hard or again.
3. Other due review items.
4. Within a tier, oldest due date, then stable review id.

The result is deduplicated by learner-facing concept and capped at three priorities. Reading speed and lesson duration are not inputs.

## Weak concept UX

An internal tag such as `networking.ipv4.dhcp.03` is never shown. The learner instead sees a label such as “DHCP and APIPA,” a short missed-concept reason, an exact `#worked-example` lesson link, and a related practice link when a published practice check exists.

## Review states

- Fresh: “Review will appear after you complete some learning.”
- Clear: “No review is due right now.”
- Due: a compact count/time estimate and up to three actions.
- Error: “We couldn’t load your review items.” with Try again.

Today omits review entirely for fresh/clear states, shows a compact card only when due, and never converts a failure into success copy.

## Historical and Service Desk limitations

- Historical practical records without assistance-level metadata remain unclassified.
- Service Desk counts only passed assessment-mode attempts and preserves the existing rubric; Wave 5 does not alter scenario grading.
- Concept naming is a deterministic reviewed keyword map with a humanized quiz-title fallback, not a predictive recommendation model.

## Screenshots

All images were captured from the disposable loopback Wave 5 fixture:

- `screenshots/fresh-progress.png`
- `screenshots/partial-progress.png`
- `screenshots/assessment-failed.png`
- `screenshots/assessment-passed.png`
- `screenshots/knowledge-vs-practical-evidence.png`
- `screenshots/actionable-review-recommendation.png`
- `screenshots/no-review-due-state.png`
- `screenshots/review-error-state.png`
- `screenshots/today-review-due.png`
- `screenshots/mobile-progress.png`

## Production safety

This wave adds backward-compatible response fields and presentation behavior only. It adds no migration and performs no deployment, production content load, enrollment, V2 enablement, or merge.

## Verification summary

- Wave 5 backend contracts: 45 passed.
- Waves 1–4, progress/training, and selected Service Desk backend regressions: 243 passed; one unrelated cache-sensitive admin query-count assertion tracked separately.
- Frontend unit/component suite: 24 files, 84 tests passed.
- Browser: Wave 1 4 passed; Wave 2 4 passed; Wave 3 3 passed; Wave 4 3 passed; Wave 5 3 passed.
- Frontend production build, Python compileall, Ruff, formatting, and whitespace checks passed.
- Full backend baseline: 1,193 passed, 11 unrelated/environment failures. These comprise six stale migration inventory-count assertions, two worktree-local virtualenv assumptions, one empty local Alembic database assertion, one missing admin-auth environment assertion, and one cache-sensitive query-count assertion.
- Dependency audit baseline: frontend build tooling reports one high, one moderate, and one low transitive advisory; the shared Python environment reports pip 26.1.2 with a fix in 26.2. No dependency mutation was made in this feature branch.
