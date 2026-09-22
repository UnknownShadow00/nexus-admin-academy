# Nexus student experience master audit

Audit date: 22 September 2026 (UTC). Audience: the instructor preparing seven people with no IT experience.

## Scope, safety, and evidence

This audit covers the student and instructor surfaces requested in `NEXUS_OVERNIGHT_MASTER_PROMPT.md`. Source baseline: current remote main `07780a98b6f93e76c5744a0af6ec9480cd3105d9`. Weeks 3–4 candidate: PR #39, initially `a4820628036e348db2e58411074a7e7fa3428a18`, continued through `b4d5711` (final SHA/checks are recorded in the prelaunch report).

The original working directory is the production-serving checkout and was **not edited**. It already contained changes to Admin Students and its tests/log, plus the untracked master prompt. The original Weeks 3–4 worktree also had four uncommitted fixes; these were preserved in place, inspected, and copied into a clean continuation worktree. Remote main differs from the stale local branch named `main`; the new quality branch is based on **remote main**, not that local branch.

Worktrees used:

- `/home/nexus/worktrees/nexus-weeks34-review`: isolated PR #39 continuation; pushed to the existing PR branch without altering its original dirty worktree.
- `/home/nexus/worktrees/nexus-student-experience-quality`: new product-quality branch from remote main.
- Existing production preflight and other release worktrees were inspected only for orientation; no development was performed there.

No production database, service, container, nginx configuration, deployment, student account, or progress was changed. No PR is to be merged during this run. Network access is used for research, dependency installation/audits, and authorized GitHub work. Local services use loopback ports 18111/15173/13001 and 18232/15232/13232 and disposable databases under `/tmp/nexus-overnight-*`.

Evidence types are explicit:

- **Repository fact**: directly read implementation, authored content, tests, or fresh seeded data.
- **Browser reproduction**: actual isolated browser behavior, including fault injection and screenshots.
- **Model check**: synthetic completion records used to exercise real progression calculations; this does not prove every exercise is solvable through its UI.
- **Research**: external learning/accessibility evidence linked below.
- **Inference**: Nexus-specific product judgment requiring instructor or learner observation.

There is no claim of complete WCAG conformance, visual testing of every module, or destructive/concurrent production testing. Browser inspection uses disposable accounts. User-created audit accounts are deleted; stack fixture data is removed when the isolated stack is stopped. The final report records final CI/review status and limitations.

## What already works well

Today offers a single prominent Start/Continue Training action and a clear current-module checklist. Beginner navigation is restricted to Today, Service Desk, and Progress. Optional work is distinguished from requirements. Manual lesson completion is explicit. Ticket writing includes a concrete rewrite exercise. Required quizzes support retries, server grading, explanations, and best-score progression rather than allowing a later failed attempt to erase a pass.

PR #39 makes Weeks 3–4 a coherent Learn → Check → Practice → Troubleshoot sequence and protects historical lab runs and instructor assignments. The backend gates direct URLs independently of the UI. Password rotation is checked by the server, and admin resets invalidate earlier sessions. Service Desk has meaningful investigation, verification, documentation, and server-authoritative evidence rather than giving credit for decorative clicks. Its mobile Work/Evidence/Notes tabs preserve mounted tool and draft state while switching panes.

## Research and how it applies

| Source and evidence type | Established guidance / pattern | Nexus-specific inference |
| --- | --- | --- |
| [IES practice guide: Organizing Instruction and Study](https://ies.ed.gov/ncee/wwc/PracticeGuide/1), evidence synthesis | Spacing and alternating worked examples with problems have moderate support; retrieval quizzes and explanatory questions have strong support in the guide. | Show one example of a support ticket before the first quiz; revisit its ideas in Week 1 and the first ticket. Completion alone is not demonstrated retention. |
| [NSW CESE: Cognitive load theory in practice](https://education.nsw.gov.au/about-us/education-data-and-research/cese/publications/practical-guides-for-educators/cognitive-load-theory-in-practice.html), institutional teaching guidance | Explicit instruction and worked examples support novices; reduce unnecessary information and gradually reduce guidance as competence develops. | Explain user/device/problem, category, escalation, and notes before asking the beginner to distinguish them. Hide optional tool details until needed, without hiding the current task. |
| [Roediger & Karpicke, Test-Enhanced Learning](https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.2006.01693.x/), primary research | Retrieval can improve later retention relative to additional study under the studied conditions. | Keep low-stakes retries and add delayed retrieval during the first fortnight. Do not equate this evidence with a need for XP or streaks. |
| [Butler, Karpicke & Roediger: feedback timing/type](https://learninglab.psych.purdue.edu/downloads/2007/2007_Butler_Karpicke_Roediger_JEPA.pdf), primary research | Feedback and its timing matter; the experiment compares immediate/delayed feedback and answer-until-correct treatments. | Do not claim immediate feedback is universally superior. Preserve the current scored end-of-quiz flow; consider per-question corrective feedback for a separately defined formative mode. |
| [NN/g progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/), external design pattern | Defer secondary detail while keeping the primary task discoverable. | Retain Today’s one next action and Service Desk’s suggested tools; keep explanation and retry visible after an unsuccessful quiz. This is a design inference, not a proven Nexus outcome. |
| [W3C Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html), accessibility guidance | Keyboard users need a visible focus indicator. | A focusable, visually hidden radio needs a visible indicator on its answer card, not only on its 1px input. |
| [W3C Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), accessibility guidance | WCAG 2.2 AA generally requires 24×24 CSS-pixel targets or an applicable spacing/other exception. | Use 44px targets for primary quiz controls as a usability choice; do not mislabel the existing 32px question buttons as automatically failing AA. |
| [W3C Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html), accessibility guidance | Important updates that do not take focus must be available to assistive technology. | Announce saved drafts, save failures, filtered review counts, and quiz results; use explicit text as well as color. |

These principles apply to mobile learning and help-desk simulation through task design, not by copying another learning product. No unsupported claim is made that a particular dashboard layout or simulation has already improved Nexus learning outcomes.

## Findings register

Severity reflects baseline impact, even when a fix is supplied. P0 = launch blocker; P1 = strongly recommended before launch; P2 = high-value follow-up; P3 = polish. Baseline inventory: **0 P0, 6 P1, 10 P2, 1 P3**. PR #39 review-thread findings are tracked separately in its status section and are not double-counted here.

### N01 — A late quiz request resets active work

- Severity / area: **P1**, quiz reliability. Before launch. Effort: small.
- Problem / student impact: the question number can jump backward and option order change after the learner has started.
- Evidence: PR #39 CI run `35703646168`, failed orientation test; four quiz detail reads in its trace, one finishing substantially later. Two deterministic component regressions fail on the original implementation and pass after the fix.
- Reproduction: mount QuizTaker in StrictMode with the first request delayed; answer a question and advance after the second response; resolve the first response. Also navigate between quiz IDs while the old read remains pending.
- Root cause: every completed request resets shuffled questions, answers, timings, and index; no request generation or unmount invalidation.
- Solution / exact implementation: ignore responses, errors, and finalizers from old load generations; invalidate on effect cleanup. No API/data change.
- Files: `frontend/src/components/QuizTaker.jsx`, `QuizTaker.test.jsx`.
- UX change: the learner stays on the current question. Risk: low; ensure retry and route changes still load.
- Tests required: both race reproductions, full frontend suite, real orientation journey.
- Disposition: request-generation fix on PR #39 at `1303c55`; `b4d5711` also clears the previous quiz when the next route fails to load. The independent quality branch includes both protections and all three route regressions.

### N02 — Quiz drafts mix learners and lose their place

- Severity / area: **P1**, privacy and persistence. Before launch. Effort: medium.
- Problem / impact: `quiz_progress_${quizId}` is shared by all learners using that browser. Refresh restores answers but resets to question 1 and reshuffles questions/options. Storage exceptions can interrupt selection or turn an accepted submission into a failure toast.
- Evidence: QuizTaker’s key, load, selection, and submission code; browser refresh reproduced index reset and changed question order. Saved key was `quiz_progress_42` with no learner identity.
- Reproduction: learner A answers, signs out, then learner B opens the same quiz in that browser. Refresh midway. Deny storage or fill its quota, then select or submit.
- Root cause: unscoped, unversioned localStorage containing answers only; unchecked storage writes/removal.
- Solution / concept: versioned student+quiz draft; persist original question/option order, current index, valid answers, and timing; verify content signature before restoring; ignore legacy unowned drafts; catch storage failures and keep in-memory work usable. Count only nonempty valid answers.
- Files: `QuizTaker.jsx`, a focused quiz-draft utility, related tests.
- UX/data change: resumable same-browser draft notice and honest storage-unavailable message; no server schema or grading change. Drafts are convenience storage, not an authorization boundary or cross-device sync.
- Risk: medium; stale content, malformed JSON, changed questions, account changes, and post-submit cleanup need coverage.
- Tests required: two learners, reload/order, multi-select deselection, malformed/unavailable storage, changed quiz content, successful submit despite storage failure.

### N03 — Quiz keyboard focus is effectively invisible

- Severity / area: **P1**, accessibility. Before launch. Effort: small.
- Problem / impact: answer radios/checkboxes are `sr-only`; the visible label has no focus treatment. Keyboard users cannot reliably locate the active answer.
- Evidence: browser focused input measured 1×1px; its label had no outline or shadow. Question text is a paragraph without a named answer group.
- Reproduction: Tab into a quiz’s answers without using a mouse; use arrows for radios and Space for checkboxes.
- Root cause: hidden native controls without a visible ancestor focus state or question group semantics.
- Solution / concept: native radios/checkboxes inside a named fieldset; visible focus-within ring on the answer card; current question heading receives focus after explicit navigation; textual progress and an accessible progressbar.
- Files: `QuizTaker.jsx`, frontend tests and browser quiz checks.
- UX change: focused card is visibly outlined; current question is announced; selected state stays independent of correctness.
- Risk: low/medium; avoid stealing focus during answer selection or asynchronous draft updates.
- Tests required: native keyboard selection, Next/Previous/jump focus, multi-select, mobile wrapping, named controls.

### N04 — Lesson failures masquerade as locks or never finish loading

- Severity / area: **P1**, first-session reliability. Before launch. Effort: small.
- Problem / impact: any lesson GET error renders “Lesson locked” and “Complete remaining work”; failed completion has no persistent error; orientation-progress failure leaves “Loading your orientation checklist…” indefinitely.
- Evidence: `LessonPage.jsx` error branch and `markComplete`; `OrientationPracticePanel.jsx` catch resets progress to null. Browser-injected HTTP 500 reproduced the false lock.
- Reproduction: fail a lesson detail read, its completion POST, or the orientation-progress GET.
- Root cause: unavailable/forbidden/loading states are conflated; completion uses finally without catch.
- Solution / concept: distinguish a real prerequisite 403 from load failure; show retry for reads, explicit inline completion error, and retryable orientation-checklist failure. Preserve the successful completion state and existing gate contract.
- Files: `LessonPage.jsx`, `OrientationPracticePanel.jsx`, tests.
- UX/API change: copy and state handling only. Risk: low; retain the backend’s next-action link for real locks and do not optimistically mark a failed write complete.
- Tests required: 403 vs 500, retry recovery, completion failure/retry, checklist failure/retry, route change while loading.

### N05 — Lesson notes claim autosave without dependable failure recovery

- Severity / area: **P1**, lost work. Before launch. Effort: medium.
- Problem / impact: note read failure silently opens an empty editable field; save failure is swallowed. Leaving before the 1.5-second timer loses edits. Concurrent saves can finish out of order; “Saved” can describe an older value.
- Evidence: local `LessonNotes` component in `LessonPage.jsx`; no visible error, retry, draft, or explicit save action, and no version comparison for save completion.
- Reproduction: fail notes GET, type and fail PUT, or navigate/reload immediately after typing. Delay an older PUT while editing again.
- Root cause: debounce is treated as persistence; empty data and failed reads share state; requests are not coordinated.
- Solution / concept: separate load/error/saving/saved states, labelled textarea, explicit Save notes/Retry, serialized saves, and student+lesson local draft recovery. A failed initial read must not enable silently overwriting an existing server note. Only clear a draft matching the value confirmed saved.
- Files: extracted `LessonNotes.jsx`, `LessonPage.jsx`, tests.
- UX/data change: visible unsaved/saving/saved/error status; optional notes remain optional. No schema change.
- Risk: medium; local draft may be stale compared with another tab/device. Never claim automatic conflict resolution; offer recovery explicitly rather than silently overriding server content.
- Tests required: read failure, write failure, immediate remount with draft, edits during save, changed lesson/student, disabled storage, no false Saved indicator.

### N06 — The first required quiz assumes untaught ticket terminology

- Severity / area: **P1**, novice learning. Before launch. Effort: small.
- Problem / impact: the required orientation teaches navigation only, then asks a zero-experience learner about ticket categories, escalation levels, and progress notes.
- Evidence: fresh seeded lesson 1 summary versus quiz 42’s four questions. The summary lists lessons/quizzes/labs/Service Desk but defines none of the tested ticket fields. The quiz is a required Week 0 gate; optional resources do not guarantee instruction.
- Reproduction: follow Today → Start Training → read orientation → Take quiz without prior IT knowledge or optional resources.
- Root cause: onboarding completion and the first domain-knowledge assessment were connected without a worked example.
- Solution / concept: a compact “Before your first quiz” ticket example in the orientation panel: requester, device, problem, category, escalation, progress note, and resolution. Explain terms in context, then retain the existing quiz and pass rule.
- Files: `OrientationPracticePanel.jsx`, tests.
- UX/content change: a short model of the work before retrieval; no curriculum IDs, requirements, migration, or answer-key changes.
- Risk: low; keep it instructional rather than merely listing correct option letters. Instructor should observe the first seven learners for wording comprehension.
- Tests required: primer shown before the quiz CTA, existing two-step checklist still operates at 375px, orientation journey still unlocks Week 1.

### N07 — Quiz review reports a network failure as missing history

- Severity / area: **P2**, review reliability. Prefer before launch because tiny. Effort: small.
- Problem / impact: a learner who just passed is told “No attempt found. Take the quiz first” on any review error; no retry is offered. Quiz-ID changes also retain stale data/loading state until the response arrives.
- Evidence: `QuizReviewPage.jsx` effect/catch; isolated HTTP 500 reproduced the missing-attempt message.
- Reproduction: submit successfully, inject a 500/network failure at `/api/quizzes/{id}/review/{studentId}`, open review; navigate between review URLs with delayed responses.
- Root cause: catch-all absence message and no lifecycle reset/cancellation.
- Solution / concept: handle actual no-attempt 404 separately, show retry for transient failures, clear state per route, ignore stale requests.
- Files: `QuizReviewPage.jsx`, tests.
- UX/API change: honest error copy and recovery; no history mutation. Risk: low; a missing quiz 404 must not be described as a known missing attempt without checking the response.
- Tests required: real no-attempt 404, server failure, retry, stale request, route transition.

### N08 — Quiz feedback is correct but difficult to use for targeted learning

- Severity / area: **P2**, learning UX. Safe subset before launch, larger design after launch. Effort: small for review filtering; medium/large for formative mode.
- Problem / impact: large repeated score blocks lead into every question; learners cannot focus on misses. Explanation quality varies; several Week 5–8 explanations are terse and assume terms such as APIPA, WinRE, or access tokens.
- Evidence: `QuizReviewScreen.jsx`, `QuizReviewPage.jsx`; sampled authored quizzes 6–9. All visible required seeded questions had a nonempty explanation, so this is not a missing-explanation claim.
- Reproduction: fail part of a longer quiz, compare correct and missed items, then try to identify the next concept to study.
- Root cause: score-first layout, duplicate review implementations, and explanations stored as a single general string.
- Solution / concept: compact result context, missed/all toggle, explicit correct/incorrect/unanswered text, prominent rationale, and Retry/Continue actions near the summary. Later editorial work should add a tempting distractor explanation and concrete IT example to weak items.
- Files: quiz taker/review components and authored question content (later, with history review).
- UX/data change: first version uses existing result data; do not invent practical explanations or expose answer keys before server grading.
- Risk: low for presentation, higher for changing grading/content/history. Tests: multi-select, unanswered question, perfect score, filter reset across attempts, review and retry without losing historical data.

### N09 — Weeks 5–8 can skip all their authored lessons

- Severity / area: **P2**, curriculum coherence. Resolve before learners reach Week 5. Effort: medium.
- Problem / impact: all three authored lessons in each of Weeks 5–8 are optional, while required quizzes/labs assess their concepts. Learners may jump from one or a few videos to nuanced support judgments.
- Evidence: seeded activity map below. Week 6 requires Windows Security Settings and a quiz covering share-vs-NTFS permissions and stale group tokens; its detailed access lessons are optional. Week 7’s required quiz includes remote-support concepts alongside endpoint security.
- Reproduction: follow only required activities through Weeks 5–8 and compare each quiz concept against required instruction. Exact video coverage still needs instructor content review; titles alone cannot prove a concept is absent.
- Root cause: required/optional normalization and historical curriculum structure differ after the recently polished first four weeks.
- Solution / concept: build a concept→required-resource→question matrix, watch the required resources, then promote only necessary short explanations or add a short prerequisite primer. Preserve custom assignments and historical completion. Do not blanket-convert every long lesson to required.
- Files: curriculum seed/realignment, training quiz mapping, lessons and quizzes. UX/data change: narrowly justified curriculum changes only after evidence and migration tests.
- Risk: high if rushed; extra requirements can move existing learners backward. Tests: upgrade/fresh convergence, instructor content preservation, full required-path model and browser samples.
- Disposition: documented, no Weeks 5–8 curriculum rewrite in this pass.

### N10 — CLI work is session-local until completion, with weak save recovery

- Severity / area: **P2**, practice persistence. After launch; tell learners before longer labs. Effort: medium.
- Problem / impact: refresh resets commands, step state, and partial work. Failed completion shows a transient toast then “Complete locally,” without a clear Save completion action.
- Evidence: `features/cli-labs/components/LabRunner.jsx` stores engine and progress in React state; `postCompletion` clears its lock on failure but offers no explicit retry button.
- Reproduction: execute part of a lab then reload; block completion POST after satisfying objectives.
- Root cause: local simulation and durable completion are separate without an explicit unsaved state.
- Solution / concept: first add durable failure text and a retry using the already-verified command log; then versioned student/lab checkpoints excluding secrets. Preserve backend validation and never mark unverified simulation state complete.
- Files: LabRunner, CLI engine serialization, CLI API/tests. UX/data change: show “Completion not saved” with retry; explain refresh behavior until checkpoint support exists.
- Risk: medium; snapshot/version drift and sensitive simulated command input. Tests: failed POST then retry, no duplicate XP, refresh/reload, changed lab version, completed historical lab.

### N11 — Unsubmitted Service Desk notes disappear on reload

- Severity / area: **P2**, lost work. After launch or before a long ticket session. Effort: medium.
- Problem / impact: mobile pane switches preserve a draft, but browser reload/navigation out discards text not yet added as an internal note.
- Evidence: `ResolutionNotePanel.tsx` uses local `useState('')`; Workspace TabsContent uses `forceMount`, which protects pane switches only. Submitted notes and evidence are separately persisted by TicketSessionProvider.
- Reproduction: enter an unsent note, reload the ticket, compare with an actually submitted note. Existing P1 browser tests cover tool/pane switches, not reload of unsent text.
- Root cause: draft lifetime is the component lifetime.
- Solution / concept: student+attempt+ticket scoped session draft, restored explicitly, cleared only after acknowledged save; visible “Draft not added yet.” Do not store credentials/evidence secrets in generic browser storage.
- Files: ResolutionNotePanel, TicketWorkspace, session identity helper, browser tests.
- UX/data change: recovery of pending note text, no change to authoritative evidence. Risk: medium, especially cross-user isolation and completed/new attempts.
- Tests required: reload, second ticket, new attempt, logout/account switch, submit failure, mobile/tool switches.

### N12 — Instructor overview lacks reliable recovery and intervention context

- Severity / area: **P2**, admin usability. Small recovery change before launch; richer context after. Effort: small/medium.
- Problem / impact: `load()` has no catch/finally, so a failed student overview can remain in skeleton state. Table emphasizes XP/averages; last activity, stuck weeks, and repeated quiz failure are not summarized at the top level.
- Evidence: `AdminStudentsPage.jsx`, `admin_students.py`; model has `last_active_at`, but overview does not expose it. Password-change-required status and expandable training detail already exist.
- Reproduction: inject a failed overview request; try to identify never-started/inactive learners without opening each row. Last activity is not equivalent to last login.
- Root cause: rank-oriented list with incomplete request state handling and limited summary fields.
- Solution / concept: retryable load error, then small columns/badges for current module, required work remaining, password setup required, last activity; define “never started” separately from “never logged in.” Keep seven-row review simple.
- Files: AdminStudentsPage, StudentTrainingDetail, admin overview API/tests.
- UX/API change: small read-only aggregates; no progress mutations or broad analytics platform.
- Risk: medium because original production checkout has overlapping uncommitted Admin Students changes owned outside this run. Do not overwrite or incorporate them silently.
- Tests required: failed read/retry, zero activity, timezone dates, null data, admin authorization, mobile table. Disposition: document and coordinate with the existing work.

### N13 — Quiz submission lacks an idempotency contract

- Severity / area: **P2**, engineering risk. After launch unless duplicate attempts occur in pilot. Effort: medium.
- Problem / impact: two successful POSTs create two attempts. A lost response leaves the browser uncertain whether Retry will submit again; simultaneous first submissions also deserve transaction-level XP review.
- Evidence: submit handler inserts every request and computes first-attempt status from a prior query. There is no request identifier or unique first-attempt claim. The UI’s submitting flag helps ordinary double clicks but does not coordinate tabs or transport retries.
- Reproduction: repeat the same submission request in isolated data; inspect separate records. This alone cannot distinguish an intentional retake; the missing contract is the problem. A concurrent duplicate-XP exploit was not demonstrated and is not asserted.
- Root cause: requests do not identify a logical submission attempt.
- Solution / concept: client-generated per-attempt idempotency key, student+quiz+key uniqueness, payload binding, transactional stored response; generate a new key only for a deliberate retake.
- Files: quiz schema/model/router, migration, client submit utility, integration tests.
- UX/data change: safe retry after an uncertain network outcome; no coalescing deliberate retakes. Risk: medium; requires schema/transaction design and backward compatibility.
- Tests required: same-key replay, changed payload rejected, two tabs, concurrent requests, first-attempt XP once, deliberate retry history retained.

### N14 — Progress failure leaves no recovery action

- Severity / area: **P2**, error UX. Prefer before launch because tiny. Effort: tiny/small.
- Problem / impact: Progress displays an error paragraph on a failed main request without retry; optional Service Desk failure silently removes skill evidence.
- Evidence: `TrainingProgressPage.jsx` effects and error return.
- Reproduction: fail progress API or its Service Desk summary.
- Root cause: one-shot reads with no retry state and optional-widget errors represented as absence.
- Solution / concept: retry for the required progress read; show a modest unavailable/retry message for ticket evidence while retaining successful course progress. Ignore responses after navigation/unmount.
- Files: TrainingProgressPage and tests. UX change only, no data changes.
- Risk: low. Tests: required read failure/recovery, optional read failure, existing successful progress retained, no fabricated zeros.

### N15 — “Progress” opens a page headed “Skills”

- Severity / area: **P3**, vocabulary. Before launch if editing that page. Effort: tiny.
- Problem / impact: beginners need to reconcile different names for the same destination.
- Evidence: navigation label Progress; `/skills` page h1 Skills; also ticket cards use “Resume in Tickets” although primary navigation says Service Desk.
- Reproduction: click Progress, compare heading; view Today’s active-ticket card.
- Root cause: earlier information-architecture terminology survives in local copy.
- Solution / concept: page heading Progress; retain “Skill evidence” as a section explaining demonstrated ability. Use Service Desk in return/launch copy. Retain existing URLs and avoid route migrations.
- Files: TrainingProgressPage, StudentHome. UX/text change only. Risk: low; selectors relying on old copy must be updated.
- Tests required: navigation destination and page title, mobile layout; no new behavioral tests solely for static wording.

### N16 — First-ticket orientation is scoped to the browser, not the learner

- Severity / area: **P2**, onboarding on shared devices. After launch or before shared-computer use. Effort: small.
- Problem / impact: once one learner dismisses the first-guided-ticket introduction, another learner using that browser may never see it.
- Evidence: `TicketWorkspace.tsx` uses constant key `sd:first-guided-orientation-seen`; UI honestly says it is saved in the browser.
- Reproduction: learner A dismisses it, logs out; learner B opens a first guided ticket in the same browser.
- Root cause: global browser preference used for a learner-specific first-time experience.
- Solution / concept: scope key by authenticated learner, keep a discoverable “How tickets work” replay control, and fail open to showing help if storage is unavailable.
- Files: TicketWorkspace and its authenticated identity source/tests. UX/local-data change only.
- Risk: low/medium; do not derive security identity from an untrusted URL. Tests: two learners, reload, replay, unavailable storage, assessment mode unchanged.

### N17 — The first CLI exercise assumes unfamiliar switch vocabulary

- Severity / area: **P2**, novice scaffolding. Instructor explanation before first practice; content redesign after launch. Effort: small.
- Problem / impact: the Week 1 “First Contact” exercise immediately names a Catalyst switch, privileged EXEC, Global Configuration, VLAN 1, and interfaces. A beginner may confuse this Cisco simulator with the Windows command line introduced in the course.
- Evidence: actual 375px screenshot `evidence/overnight-2026-09-22/after/cli-mobile.png`; the seeded required `meet-cli-001` exception is accessible in Week 1. This is intended prerequisite behavior, not a direct-URL bypass.
- Reproduction: complete orientation, open the required first CLI exercise, and read its scenario/objectives/topology without prior networking knowledge.
- Root cause: a generic Cisco CLI introduction is reused as an early A+ command-line activity without enough context or vocabulary scaffolding.
- Recommended solution / exact concept: explain that this is a simulated network device, contrast its prompt with Windows, define command mode, demonstrate `?` and `enable`, and hide topology detail until needed. Consider an introductory Windows shell exercise in a separate curriculum change.
- Files: `frontend/src/features/cli-labs/` lesson catalog and LabRunner, `backend/app/services/training_curriculum_seed.py`; preserve stable activity identity and completion history.
- UX/API/data change: short worked example and glossary; no API change for that first step. Replacing the activity requires a reviewed migration and historical-completion policy.
- Risk: low for explanatory text, medium for replacing the required activity. Do not broaden the early exception or move the switch gate.
- Tests required: novice observation; catalog validation; successful guided completion; Week 1 intro available while broader switch labs stay locked; historical completion preserved.
- Disposition: found during screenshot review of unchanged practice content. Documented rather than bundled into the quiz/notes implementation.

## First ten minutes: current and recommended journey

This is a usability sequence, not a promise that a true novice will finish the first ticket in ten minutes. Week 1 requires more instruction before the first real ticket unlocks.

| Step | Current behavior and likely hesitation | Recommended action and recovery |
| --- | --- | --- |
| Temporary credentials → Login | Labelled fields; password manager support. Learner needs the instructor’s actual temporary credential. | Instructor gives URL, username, temporary password privately and explains the first change. Never include credentials in screenshots/reports. |
| Change Password | Clear forced gate, confirmation, server enforcement; refresh and direct access cannot bypass. | Keep one primary Change password action; retain mismatch/error text and sign out. Password reset repeats this step without clearing learning progress. |
| Today | Prominent Start Training plus current checklist. Clear next action already strong. | Retain it; do not add dashboards, advanced tracks, or celebratory distractions before the first task. |
| Orientation | Short navigation text, explicit completion, first quiz link. Assumes ticket vocabulary. | Insert the worked example before the quiz link. Failed checklist/read/completion should offer retry without claiming a curriculum lock. |
| First lesson/video | Objectives and practical framing exist; some prose uses MSP/DNS before explanation. Video is an external dependency. | Say what to learn, why it matters, what to remember, and next action. Instructor checks external video availability/captions; preserve manual completion. |
| First quiz | Shuffled multiple choice, submit at end, score/explanations. No title while taking; refresh loses place and keyboard focus is hidden. | Named quiz, low-stakes instructions, stable draft, clear question focus, explicit Submit Quiz. Preserve native Back/reload usability. |
| First practice | Ticket-note rewrite and guided CLI use examples and observable outcomes. | Identify command purpose before entry, show expected output, and explain what counts as done. State unsaved partial CLI behavior pending a proper checkpoint feature. |
| First ticket | Locked until topic work completes; guided mode explains investigation and safety. | Explain the lock with the exact remaining prerequisite; use suggested tools, current stage, and evidence rail. Teach “investigate → act → verify → document.” |
| Progress | Shows course counts and skill evidence; heading differs from nav, no retry on failure. | Use Progress consistently and distinguish completion from ability. Never replace unavailable evidence with zero. |

Across the sequence: one obvious next action, persistent errors, a useful Back path, and refresh recovery are more valuable than more features. On mobile, controls should follow the content naturally, wrap long text, and avoid sticky controls that cover answers or the software keyboard.

## Navigation and button vocabulary

| Verb | Consistent meaning |
| --- | --- |
| Start | Open an activity not begun. “Start Training” remains the first Today action. |
| Continue | Next learning action or next step in an active flow; Today continues the current path. |
| Resume | Reopen a saved draft/active ticket at the saved location. |
| Mark lesson complete | Learner explicitly confirms reviewing the lesson; do not use vague “Complete” before the action. |
| Next / Previous | Move between unanswered quiz questions without grading. Keep these labels until formative mode exists. |
| Submit Quiz | Send the full scored attempt to the server once. |
| Check answer / Check my note | Formative feedback only; do not label a final quiz submission as per-question checking. |
| Retry quiz | New complete scored attempt; history remains. Existing Try Again can be retained where browser contracts rely on it. |
| Review answers / Review missed questions | Inspect existing graded work; never creates another attempt. |
| Practice | Guided rehearsal; specify whether it is required or optional. |
| Troubleshoot / Open ticket | Work a support case using the stated tools and evidence. |
| Resolve / Escalate | Operational outcome only after investigation and verification/appropriate handoff; not a generic navigation verb. |

Today, Service Desk, and Progress should remain the primary beginner destinations. Modules/week pages and the quiz library are secondary context, not competing starting points. Locked direct URLs must give an actionable prerequisite; service failures must never pretend to be a lock.

## Concrete quiz redesign specification

### Before answering

Use the existing Nexus blue/slate visual language. A maximum-width reading column contains Back, h1 quiz title, topic/week context when available, and a one-sentence explanation: choose an answer, move with Next, submit at the end, then review explanations. Say that retries are allowed and previous progress is preserved; avoid leading with XP penalties.

Show “Question n of total” and “n answered” separately. A named progressbar reflects position, not mastery. Put the question in a fieldset legend/heading and use full-width native radio/checkbox answer cards with wrapped text, a visible focus ring, and a selected marker. State “Select all that apply” where relevant. Keep original answer IDs through shuffling. Long technical text must wrap or scroll locally, never widen the viewport.

Next/Previous/jump navigation preserves answers and moves focus to the new question heading. Selecting an answer does not move focus or auto-advance. Keyboard arrows operate native radios; Space toggles checkboxes. Draft recovery preserves question order, option order, position, and answers for the current learner. Explain whether storage is unavailable rather than blocking the quiz.

### After an answer and after submission

The safe prelaunch version continues to grade the entire attempt at the end. It **does not add a misleading Check Answer button** or ship answer keys to the client. After server acceptance, focus the result heading and display score, pass/not-yet state, and a short learning-oriented next step. Show missed/all review controls near the summary. Each reviewed question shows original selected answer(s), correct answer(s), explicit correctness/unanswered text, and the existing authored explanation.

Future formative mode needs a deliberate API/data contract: Check answer returns the graded item and rationale, locks the submitted choice for that practice turn, then Continue moves to the next question. It must remain distinct from gate-quiz attempts and cannot silently award scored credit for answer-until-correct behavior.

### Final question, retry, and review

Before Submit Quiz, indicate unanswered items and retain confirmation of submitting incomplete work. While a request is pending, freeze relevant answer/navigation controls and use a synchronous submission lock. On failure, keep the complete draft and show a persistent retryable error. Server idempotency remains separate follow-up N13.

After submission: score plus “Review missed questions,” “Try Again,” and “Continue Learning” near the top. Explain that retrying repeats the whole quiz and preserves prior attempts/best progress. A missed-only review is not a shortened scored retake. Keep all questions in a new scored attempt. Do not auto-mark a learner proficient from repeated guessing.

Historical review uses the saved result’s original choices/options/explanation where provided. Existing API supports latest review and attempt summaries on quiz detail; a full attempt selector requires a versioned historical-question contract before implementation. Link to the associated lesson when a reliable relation exists; otherwise Continue Learning returns to Today rather than inventing a lesson mapping.

### Explanation editorial template

A strong explanation should include: why the correct decision follows from evidence; why the plausible wrong choice is insufficient; a brief workplace example; and one takeaway. For example, a category supports recurring-incident reports, while progress notes record this incident’s investigation. Do not generate such explanations at runtime or insert unreviewed facts. Start with the orientation quiz and Week 5–8 terse items; review against the exact question and intended answer key.

### Mobile and accessibility

Use stacked actions below 640px when needed; aim for 44px primary tap targets and leave the document scrollable. Do not pin a footer over long answers or the mobile keyboard. Preserve readable answer width at 375/390px and tablet. Provide native semantics, visible keyboard focus, named groups, focus after navigation/results, status/error announcements, text labels independent of green/red, and sensible heading order. Test real keyboard behavior and inspect screenshots; unit class assertions alone are insufficient.

## Lessons, practice, and Service Desk design

Lessons should answer four questions in order: what am I learning, why does it matter at work, what should I remember, what do I do next? Week 1’s authored lesson and note-rewrite exercise already do much of this. Optional notes must never gate completion. A lesson completion failure must remain actionable without forcing the learner to read the whole page again.

For CLI/labs, use worked example → guided practice → partially guided practice → independent troubleshooting. The existing First Contact CLI is short but uses Cisco switch vocabulary (N17); it needs an instructor explanation before initial guided practice. Longer switch simulations also need explicit saved/unsaved behavior. Explain the command, expected signal, and success criterion before requiring unfamiliar syntax. Keep the required introductory CLI exception narrow; do not unlock the broader switch catalog before the existing A+/half-Network+ gate.

Service Desk beginner spec:

1. Ticket header gives requester, device, symptom, affected work, status, and priority in plain language. Guided mode should expose the reported issue by default; assessment mode can retain purposeful disclosure.
2. Current stage explains the next investigative goal, without revealing the diagnosis. Suggested tools are primary; All tools is secondary.
3. Tool actions create authoritative evidence. The evidence rail says what was confirmed and why it matters; absence is distinct from a failed read.
4. Notes prompt “reported / checked / found / action / verification.” Submitted notes persist; drafts need recovery as N11 describes.
5. Resolve requires a working verified outcome; Escalate is a valid professional decision with an appropriate handoff. Permission to make a change should come from the scenario’s authorization step, not merely a visible button.
6. Bad paths should allow investigation to continue or an explicit retry according to assignment policy. Do not erase history or claim that a failed attempt invalidates an earlier pass.
7. Desktop keeps evidence and notes near the active tool. Mobile Work/Evidence/Notes preserves state and focus; a saved return link goes back to the exact curriculum module.

Observed screenshots show good mobile containment at 375px. The separate service-desk visual style is functional and work-like; do not reskin it merely to resemble the course dashboard. The biggest remaining beginner risks are draft loss, shared-browser introduction scope, and instructional wording rather than decorative layout.

## Weeks 1–8 and Network+ map

This is the intended PR #39 seeded path. Original numeric weeks remain stable even where display titles differ. Required time below sums available activity estimates plus video durations; it excludes optional work, retry time, and instructor discussion. Week-level estimates are planning allowances and are not equivalent to required runtime.

| Week | Learn | Check | Practice | Troubleshoot | Prerequisites / time observations |
| --- | --- | --- | --- | --- | --- |
| 0 | Nexus navigation orientation | Ticketing Systems quiz (42) | Optional orientation activities | None yet | ~18 min estimated required work; vocabulary gap N06. Week-level estimate 60 min. |
| 1 | Good tickets, command-line introduction, professionalism, communication | Ticket Writing Fundamentals (1) | First Contact CLI (`meet-cli-001`) and formative ticket-note rewrite | `locked-user-account` after topic foundation | ~97 min required estimates; week allowance 180. Introduce requester/device/incident before troubleshooting. |
| 2 | Storage, RAM/CPU/power/POST, BIOS/UEFI; six hardware videos | Core PC Hardware Troubleshooting (78) | Hardware Component Identification | `inc2404` USB headset fault | ~241 min required estimates; week allowance 300. Distinguish symptoms/evidence from specifications. |
| 3 | Accounts/profiles/permissions; investigator tools; command-line diagnostics; two CLI videos | Quizzes 2, 3, 4 | Windows Command-Line Diagnostics | `inc2501` missing Desktop/Documents | ~260 min required estimates; week allowance 270. Password reset is not a Week 3 dependency. |
| 4 | Priority/impact/change safety, human communication, change-management video | Help-Desk Operations (5) | Prioritize the Queue | Work the Queue: Three Tickets (structured lab) | ~152 min required estimates; week allowance 150. No later MFA requirement. |
| 5 | Required Windows troubleshooting video; startup/crash/disk lessons optional | Windows Deep Troubleshooting (6) | Isolate the Windows Failure | `inc2502` Excel crash | ~88 min required estimates vs 300 allowance. Optional lessons add 225 min before optional videos; teach/check mapping needs review. |
| 6 | Required Windows Security Settings; lifecycle/permissions/escalation lessons optional | Accounts and Permissions in Practice (7) | Make the Safe Access Decision | `password-reset`; optional `inc2505` | ~84 min required estimates vs 210 allowance. Identity verification and least privilege must precede access changes. |
| 7 | Required Defender, firewall, malware videos; endpoint/security/remote-support lessons optional | Endpoint Security and Remote Support (8) | Choose the Safe Endpoint Response | Optional `inc2508`; MFA topic becomes available | ~68 min required estimates vs 300 allowance. Confirm remote-support and identity concepts are taught before checks. |
| 8 | Required IP/network-tools/troubleshooting/Windows-IP videos; triage/printing/queue lessons optional | Client Network Triage (9) | Diagnose the Client Network | Optional `inc2407`; optional capstone | ~98 min required estimates vs 300 allowance. Teach DHCP, DNS, subnet/gateway and fault isolation; avoid advanced switch configuration here. |

Network+ begins at Week 9 after required A+ work. Weeks 9–12 cover IP addressing, switching/VLAN concepts, routing/services, and secure network administration. `network_cli_gate_is_unlocked` uses completion of A+ plus **half of active Network+ modules**, not a misleading hardcoded percentage of videos. With four active modules, switch labs unlock after two; isolated progression audit observed the switch gate false through the start of Week 10 and true at Week 11. Required reached instructor CLI assignments and owned historical completions have explicit exceptions.

Explain the transition: “You have practiced troubleshooting a single user’s computer. Next you will learn how devices communicate, then configure a small network after the foundations.” Do not enable Hybrid Labs/INC2504 VM provisioning. Legacy Hybrid availability stayed false through the Week 12 model audit.

Curriculum source evidence: `backend/app/services/beginner_learning.py`, `training_curriculum_seed.py`, `training_quiz_mapping.py`, `training_service.py`, and fresh seeded `training_weeks`/`training_week_activities`. Detailed machine-readable map and the synthetic progression checkpoints are stored with the run evidence. Do not treat the synthetic model journey as a complete UI certification of Weeks 5–12.

## Progression, auth, and engineering risks

Progression checks cover required-vs-optional work, direct URL gates, best quiz pass across attempts, historical lab review/active retired runs, custom assignments, V2 provenance exclusions, topic-gated Service Desk, and active-network-module gating. The source explicitly excludes trusted V2 curriculum launches from legacy Service Desk completion. Isolated progression records reached Week 13; no circular required dependency was found in that path. Existing regression tests cover instructor assignments and historical access; no real progress was altered.

Forced password change is enforced server-side, not only by route redirects. Admin reset increments auth version, and password rotation uses a conditional claim to avoid two simultaneous rotations. Student IDs are checked for ownership on mutations; Service Desk uses its integration/session validation rather than trusting browser snapshots. Student deletion is admin-only and has confirmation; ownership behavior is covered by existing tests and the repository’s deletion audit. No new production auth bypass was demonstrated.

Risks requiring separate work: submission idempotency (N13); unversioned historical question text if authored questions are substantially rewritten; content migration ownership/identity (PR #39 has already required several fixes); shared-device local drafts/introduction state; and cold-development-server timing in the test harness. Frontend build reports a large entry chunk; measure production compressed transfer and render time before undertaking code splitting. Avoid micro-optimizing cached/batched progression without a trace.

Service Desk audit gate passes at high severity but reports two moderate package findings for the same [Vitest mocker path-traversal advisory](https://github.com/advisories/GHSA-82fw-gwwq-j7x9): `apps/api` uses `vitest@3.2.7` and its `@vitest/mocker@3.2.7`. The audit lists a fix at 4.1.11 or later. Treat the major test-runner migration as a separate dependency follow-up; do not expose its test server. Passing the configured gate does not mean zero advisories. No package upgrades are bundled with learning UX changes.

## Priorities and concrete follow-up plans

### Top ten student-impact improvements

1. Teach ticket vocabulary before the first required quiz (N06).
2. Prevent late requests from moving a learner backward in a quiz (N01).
3. Isolate and reliably restore quiz drafts by learner (N02).
4. Make keyboard focus and quiz question context visible (N03).
5. Recover honestly from lesson/checklist/completion failures (N04).
6. Make optional notes’ save status trustworthy and recoverable (N05).
7. Make review failures distinguishable from missing attempts (N07).
8. Put missed-question review and next actions next to the result (N08).
9. Verify required instruction matches Weeks 5–8 assessments (N09).
10. Preserve pending practice/ticket work and expose save recovery (N10/N11).

Top engineering risks: content-migration identity/history, non-idempotent quiz writes, local draft ownership, silent asynchronous failures, and test fixture order. Top UX improvements: a named quiz, honest save/error state, targeted review, consistent Progress vocabulary, and exact prerequisite links. Top curriculum improvements: the first ticket example, concept coverage for Weeks 5–8, faded guidance, and delayed retrieval after each support skill.

### Instructor admin plan

Before launch: verify all seven accounts, required password setup, access to the expected starting module, and a recoverable Students page; reconcile the existing uncommitted Admin Students work separately. Do not label last-active as last-login. After launch: a compact “needs attention” view with current module, latest activity date, repeated failed quizzes, active ticket, and recent mentor feedback. A weekly seven-person review is preferable to a new analytics platform.

### Accessibility priority plan

First: quiz visible focus/group labels, truthful inline errors and save status, question/result focus, labelled notes, keyboard retry. Next: full screen-reader walkthrough, contrast measurements in both themes, modal focus trap/return across course and Service Desk, and video captions/transcripts. Preserve native controls; do not use color as the only indicator. Representative checks are not a conformance certification.

### Mobile priority plan

375/390px: quiz answer wrapping, access to Submit after long multi-select questions, primer readability, notes/error buttons, Today, Progress, CLI, and ticket tabs. Tablet: reflow at 768px and 200% zoom; do not force desktop columns too early. Desktop: keep readable line widths and evidence near the active work. Admin table may scroll locally, but the document must not overflow. Avoid sticky controls unless device testing demonstrates a clear benefit.

### First two weeks after launch

Days 1–2: instructor watches the first orientation/quiz/ticket for each learner, records hesitations using finding IDs, checks password setup and progress without editing student history, and resolves genuine blockers.

Days 3–5: compare first-pass and retry behavior, examine missed concepts rather than only scores, spot-check saved notes and ticket recovery, and add a short delayed retrieval prompt about ticket fields and safe investigation. Confirm time estimates against actual novice sessions.

Week 2: close the most frequent confusion points, evaluate N10/N11 persistence work, complete the Week 5–8 concept/resource matrix before learners reach those modules, and prioritize a small instructor intervention view. Plan idempotency and versioned attempt review as separate engineering work. Keep Network+/Hybrid boundaries unchanged.

## Implementation decision

Complete the audit before product edits. Implement only the high-confidence presentation and reliability subset: N02–N08 (with scored end-of-quiz behavior retained), N14, and the Progress heading part of N15. N01 is already fixed on PR #39 and is required in the independently based QuizTaker. Defer N09–N13/N16/N17 and broader analytics/formative-quiz changes for the reasons above. No curriculum/schema migrations, architectural rewrite, Hybrid enabling, or production change is part of this quality branch.

The final report records what actually shipped, final tests, review status, screenshots, and any divergence from this decision.

## Implemented subset and evidence disposition

The quality branch implements N01–N07, the review presentation/filter subset of N08, N14, and the Progress heading subset of N15. It keeps the existing end-of-quiz grading contract. N05 serializes saves within a mounted editor and offers explicit local-draft restoration; it does not add server revision control across devices/tabs. N02 validates content and attempt generation on load but does not claim that simultaneous open tabs are coordinated. N13 remains a backend follow-up.

Unit coverage includes stale requests, learner isolation, corrupted/unavailable storage, full retakes, notes recovery and in-flight edits, honest failure states, and review filtering. A new real-browser regression exercises forced login, saved/unsaved notes, 375/390/768/1440px quiz layouts, keyboard focus, refresh, submit failure/retry, missed review, and lesson/review HTTP 500 recovery. Existing browser tests were updated for the intended Progress and saved-status wording.

Local harness inspection also exposed an occupied-port hazard: Vite selected another port while readiness checked an unrelated server. The quality branch now preflights distinct unused loopback ports and uses `--strictPort`; occupied-port rejection was verified before any scratch database or credentials were created. No unrelated process was stopped.
