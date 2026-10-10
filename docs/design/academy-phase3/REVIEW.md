# Academy Phase 3 — owner visual and functional review

## Scope and lineage

This isolated branch is based on verified PR #66 head `2cccddc7b2d409bfffc566e23510c60db0dd3ce3`, which contains approved Phase 1 `2ddb099`. Its draft PR targets `feature/nexus-academy-integration-phase2`. The only visual authority is approved prototype `76b4a15`; PR #64 was not used.

Focused mapping reused Phase 1 LearnerShell, AcademyScene, themes and existing WebP artwork; legacy QuizTaker's shuffle/draft/request guards and QuizReviewScreen; V2 assessment attempts, snapshots and next-step APIs; all six original V2 interaction renderers; and the existing PendingGrade/mentor-override reconciliation. No third progression system, new assets, dependency changes, migrations or curriculum edits were added.

## Review evidence

- `quiz-{light,dark}-{1440,1280,390}.png`: actual integrated V2 Quick Check, backed by the isolated API and SQLite database with existing authored content. These are disposable preview students, not production student data.
- `comparison-{light,dark}.png`: approved prototype on the left, integration on the right, at all three widths. Screenshot pixels are composed at native size, without stretching. Different titles, counts and question text come from real authored content: the prototype's fictional twelve-question example is not imported.
- `quiz-result-{light,dark}.png` and `legacy-quiz-result.png`: actual server-graded assessment and legacy result/review.
- `exercise-*-{light,dark}.png`: real server feedback for matching, ordering, safe action, image identification, typed answer and command output.
- `written-pending-{light,dark}-fixture.png`: explicitly **synthetic UI response** exercising pending grading and suppression of provisional scores/keys. Real written persistence/reconciliation is tested separately through actual API handlers and disposable databases.
- `changed-files.txt`: exact changed paths relative to Phase 2.

The desktop header starts at x=276/y=96 with the approved 300px attempt rail; card spacing, typography, purple controls, panoramic castle backdrop and supporting shadow artwork follow the prototype. The current question, answered count, total and answered percentage have separate labels. Mobile reflows to one column; the fixed navigation visible inside full-page screenshots is captured at the initial viewport boundary. Actual controls remain reachable by scrolling. Basic keyboard/reflow testing also covers 320px. The supporting text uses its own compositing layer to avoid a Chromium dark-mode paint issue.

## Behavior preserved and improved

Legacy randomization, original option keys, timing, account-scoped draft recovery, retry policies, first-attempt XP rules and review destinations remain authoritative. V2 questions/options, pass thresholds, authorization, enrollment, prerequisites, attempts, next actions and mastery remain server-owned. No assessment passes merely because every question has an answer.

Both quiz presentations support previous/next, direct question navigation, unanswered review, revision before submission, synchronous duplicate-submission protection, and failure recovery. Local storage is explicitly described as browser storage, not a server submission; storage failures keep the form usable. V2 assessment drafts add module/attempt isolation and question signatures, migrate the previous scoped key, and clear only after confirmed submission. Native exercises restore validated local drafts or recent server responses, scoped by student, module, interaction version and attempt count. Original six renderer formats and native server validation remain intact. Flags are explicitly visit-only reminders.

Ticket-note practice now treats wording suggestions as advisory, retains empty-field handling and original study instructions, and makes no correctness/grade claim for filled fields. It does not change authoritative Service Desk grading.

Supported written **assessments** preserve the original text, including whitespace. The API accepts up to 10,000 characters per answer, 200 question IDs and eight selected options; unsafe control characters are rejected. Literal accepted short answers and definite numeric/known-command alternatives retain deterministic grades. Ambiguous prose and concept matching enter the existing durable pending-grading infrastructure. Keyword presence cannot automatically pass a prose explanation, and missing keywords alone cannot automatically fail it. Empty/unanswered responses remain incorrect. Existing Explain/interview callers retain their grading policy.

Pending attempts show saved/awaiting-grading status, suppress provisional final scores, pass/retry controls and answer keys, and award no XP/mastery. Existing mentor overrides reconcile the stored attempt; no new human review queue or promised reviewer was invented. Correct/incorrect item feedback and final server pass/fail are distinct.

## Explicit architecture blocker — native typed exercises

**Owner decision: keep native typed grading unchanged; document a separately reviewed architecture proposal.** Native interaction attempts require non-null numeric score and Boolean pass/fail and have no PendingGrade reconciliation. This phase makes no backend native-interaction changes. A valid native typed paraphrase can therefore still receive the old failed grade; the browser tests explicitly verify that limitation rather than pretending it was fixed.

A follow-up proposal would add an explicit grading state with nullable provisional grade, a durable reference from native attempts to the existing grading job, and idempotent final reconciliation into native progress. Passing evidence/XP/continuation would be created only after an authoritative final pass. It requires a reviewed backward-compatible migration, historical-attempt policy, actual operator review routing, and authorization, concurrency, retry, safety-rule and cross-student isolation tests. No schema or queue changes from that proposal are implemented here.

## Verification

- Frontend: 242 unit tests across 41 files passed; production build passed. Existing large-chunk build advisory remains.
- Backend: targeted 162-case suite and additional 47-case suite passed (overlapping coverage; not summed). Coverage includes legacy quizzes, V2 content/assessment/progression, grading queue, all six interaction types and Service Desk grading gates. The new written-response suite has 18 cases, including actual handlers/ORM persistence, original wording, pending idempotence, no XP, cross-student denial, definite incorrect answers, bounds and existing override reconciliation.
- Real browser/API: 21 Phase 3 cases and 28 Phase 1/2/navigation/admin regression cases passed against disposable loopback services. The Today before/after navigation screenshot comparison is byte-identical. Lesson content, embedded exercise saves, resources, sequence, retry and prerequisites remain covered. Native exercises use a separate fixture student with explicit development-only continuation grants; a separate ungranted student tests genuine server locks.
- Synthetic browser fixtures: 16 cases passed, covering pending-state and authored learning-surface checks are recorded separately from real API coverage. Existing fixtures retain their assertions and now include the API's separate correctness field. Seeded browser tests target the approved question card and heading instead of the previous presentation's panel selectors; grading, progress and answer-review assertions are unchanged.
- Ruff and `git diff --check` passed. npm audit and manifest-based pip-audit found no known vulnerabilities. No lockfiles changed.
- GitHub CI runs on the draft PR; consult its current checks for the exact head result. The repository's existing CI browser list does not automatically run the new opt-in local preview suites. CI does run unit/backend suites and the existing seeded browser/Service Desk flows.

On this constrained host, shared-browser asset requests exhausted Chromium resources. Regression verification was rerun with a fresh browser per case, retaining all assertions. An interrupted isolated API process was restarted with new disposable fixtures before the final Phase 3 capture run. No production behavior is claimed tested.

## Preview and remaining limitations

Preview: `http://127.0.0.1:5190` with isolated API `http://127.0.0.1:8020`. Forward both loopback ports when reviewing remotely. Disposable credentials remain only in the private preview fixture file outside Git; no passwords, cookies, databases or traces are included in evidence.

The content and navigation intentionally reflect the real application instead of prototype mock data. Unsupported authored hints are replaced with neutral study instructions, not invented explanations. Native typed grading remains the approved blocker above. Written assessment prose may remain pending until the existing grading worker or authorized override resolves it; this phase neither enables a paid provider nor guarantees an automatic turnaround. Other than the targeted quiz/practice presentation and advisory study-aid behavior, Today, Lesson artwork/layout, Guided Tickets, admin and Service Desk interfaces are not redesigned.

Production checkout/services, live databases/student records, PR #65/#66 worktrees, the approved prototype and deployment configuration were not modified. Nothing was merged or deployed. Stop here for owner Phase 3 visual and functional review; Phase 4 and deferred Lesson shadow imagery are untouched.
