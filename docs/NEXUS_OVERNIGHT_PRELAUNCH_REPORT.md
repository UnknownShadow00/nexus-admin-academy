# Nexus overnight prelaunch report

22 September 2026, UTC. Prepared for the instructor and seven learners with no prior IT experience. Implementation validation finalized at 2026-09-22T09:56:23Z; documentation-only follow-up CI remains visible on the linked PR checks.

## 1. Executive summary

Nexus has a sound beginner foundation: one next action on Today, explicit lesson completion, retryable server-graded quizzes, topic-gated tickets, and server-enforced password setup. The main prelaunch weaknesses were loss/confusion around drafts and failures, invisible quiz keyboard focus, and a first quiz that assumed ticket terminology not taught by orientation.

The audit produced **0 P0, 6 P1, 10 P2, and 1 P3 findings**. The new student-experience PR fixes all six P1 findings within their documented scope, plus selected P2/P3 recovery and review improvements. PR #39 received additional curriculum ownership, remediation, stale-request/lab-state, and historical evidence-access fixes. This is a tested candidate, not a production release.

Production remains at the supplied `07780a98b6f93e76c5744a0af6ec9480cd3105d9` baseline. No production files, data, services, containers, nginx, Proxmox, or Hybrid settings were changed. No PR was merged. Existing uncommitted work in the production and original Weeks 3–4 worktrees was preserved.

Read the [master audit](NEXUS_STUDENT_EXPERIENCE_MASTER_AUDIT.md) for each finding's evidence, reproduction, risk, implementation concept, and tests. The [evidence index](evidence/overnight-2026-09-22/README.md) links reviewed screenshots and machine-readable curriculum/progression observations.

## 2. PR #39 status

- PR: [Weeks 3–4 quality #39](https://github.com/UnknownShadow00/nexus-admin-academy/pull/39), base `main`.
- Latest implementation SHA: `b4d57113a401a14ad3b186f9e80cd36b765740f0`.
- CI: [run 35711110244](https://github.com/UnknownShadow00/nexus-admin-academy/actions/runs/35711110244) passed all six jobs at the latest implementation SHA. Full backend: **1,213 passed, 7 skipped**, 10 warnings; dependency audit clean. All **19 returned review threads are resolved**.
- Fixed review findings: preserve instructor-required quiz/video and custom lesson requirements; block unassigned/untriggered remediation detail and submit even if library flags expose it; reset lab session state on lab/V2 route changes; allow the owner of an active retired lab run to upload evidence after a curriculum relock; clear old quiz data on a failed route load; restrict video/scenario/capstone changes to seed-owned stable identities; validate V2 provenance before the retired legacy gate exception.
- Additional reproduced fix: late StrictMode quiz reads could reset an active question and shuffle. Both stale-load regressions fail before and pass after the guard.
- Final review verdict: **not labelled READY FOR MERGE** because independent review of the last fixes is unavailable. All returned review findings are resolved and fresh self-review is complete. The [Codex quota response](https://github.com/UnknownShadow00/nexus-admin-academy/pull/39#issuecomment-5774256233) is the external limitation. **NOT merged.**

Required boundaries remain: Week 3 uses INC2501 after its topic foundation; password reset stays Week 6; MFA stays Week 7; Network+ begins Week 9; broader switch labs require the A+/half-Network+ gate; Hybrid/INC2504 VM provisioning stays unavailable. Historical attempts/owned runs and instructor assignments have regression coverage. No new migration was added beyond PR #39's existing `0072_weeks_3_4_prelaunch_quality`.

## 3. Audit summary

| Severity | Baseline findings | Disposition |
| --- | ---: | --- |
| P0 launch blocker | 0 | None demonstrated within this audit's scope. |
| P1 strongly recommended | 6 | N01–N06 addressed in the candidate branches. |
| P2 high-value follow-up | 10 | N07 and N14 fixed; N08 presentation/filter subset fixed; remaining content, persistence, admin, and idempotency work documented. |
| P3 polish | 1 | N15 Progress heading fixed; broader vocabulary consistency remains. |

These are baseline finding counts, not an assertion that every remaining edge case is solved. PR #39 review-thread findings and test-harness incidents are tracked separately rather than inflating this product inventory.

## 4. Most important findings

1. An old quiz GET could reset work already in progress; a shared `quiz_progress_<quiz>` key also let a different learner inherit answers. Refresh changed question/option order. Fixed with request generations and validated learner-scoped drafts.
2. Keyboard users could focus a 1px hidden answer input without seeing its focus. Fixed with visible answer-card rings, named groups, larger controls, and question/result focus management.
3. Lesson HTTP 500 looked like a prerequisite lock; review HTTP 500 looked like no saved attempt; completion and notes failures were silent. Fixed with honest inline state and retries.
4. Orientation taught navigation but tested intake, category, escalation, and notes. A short support-ticket worked example now introduces those concepts before the quiz.
5. Weeks 5–8 have nuanced required quizzes while their authored lessons are optional. The first CLI exercise also introduces Cisco/Catalyst/EXEC/VLAN terminology early. Both need deliberate teaching alignment, not a speculative overnight migration.

## 5. Changes implemented

**Quiz:** one detail-fetch owner; stale response protection; learner+quiz draft keys; content/attempt validation; stable question/option order and place after reload; guarded storage access; synchronous pending-submit lock; retained answers after failed submit; named native answer groups and visible focus; 44px primary targets; accurate answered counts; a single shared review with explicit correct/incorrect/unanswered text, authored explanations, and missed/all filtering. A retake includes every question and preserves attempt history.

**Lessons and progress:** distinguish load failure from genuine 403 locks; expose lesson completion failure without marking it complete; retry orientation checklist failures; isolate lesson state by learner/route; add the ticket example; label notes; show persistent save status and explicit Save; serialize saves within the editor; restore local unsaved notes only after learner choice; preserve newer edits while a save is pending; retry Progress and report partial Service Desk evidence failure; use the Progress heading.

**Verification:** add unit and real-browser regression coverage, update existing assertions for intentional copy changes, include the recovery test in CI, and reject occupied test ports before creating disposable data. Vite uses `--strictPort`.

## 6. Changes deliberately not implemented

- Broad Weeks 5–8 reordering or changing required lesson flags: needs a concept-to-assessment matrix and a historical-progress policy.
- Replacing the early Cisco introduction: explain it during first practice, then design a Windows-first alternative without invalidating completed work.
- CLI checkpoint persistence and Service Desk unsent-note recovery: separate lifecycle/state designs; tool-tab persistence already works.
- Server quiz idempotency and cross-device note revision control: require API/transaction/schema decisions. A client pending-submit guard cannot guarantee exactly-once processing after an ambiguous network failure.
- Immediate per-question graded feedback or missed-only scored attempts: a new formative mode needs its own grading/progression contract. The shipped flow still submits the full quiz once at the end.
- Rewriting every explanation or adding an analytics platform: prioritize actual missed concepts and instructor observation.
- Admin Students implementation: the production checkout already contained uncommitted overlapping admin work. It was preserved and identified for separate reconciliation.
- Service Desk dependency upgrades: two moderate findings share one Vitest/mocker advisory; a test-runner major upgrade belongs in a focused dependency PR.

## 7. Quiz UX

Before answering, students see the quiz title/topic, instructions, current position, answered count, and a readable question card. Native radio/checkbox behavior is retained. Selection is visually distinct from correctness. Next/Previous and question navigation preserve work and move focus to context.

After submission, score/pass status is compact; explanations, missed-question filtering, retry, and Continue Learning are close to the top. Each answer shows what the learner chose and what was correct using text as well as color. The bottom returns to the summary. A deliberate retry starts a full new answer set; prior attempts and best progress remain server-owned.

The audit specifies a future formative mode, spaced concept checks, practical examples, and explanations of tempting wrong choices. These are proposals, not implemented learning-outcome claims. Historical review uses stored result text/options where available; full versioning of changed/deleted questions remains an engineering follow-up.

## 8. First 10 minutes

Current recommended path: temporary credentials → Login → choose a personal password → Today → Start Training → short orientation → worked ticket example → Mark lesson complete → Ticketing Systems Quiz → review explanations/retry → Continue Learning → Week 1 ticket-writing lesson, communication resources, quiz and guided practice → first topic-unlocked ticket → Progress.

The first ten minutes should establish confidence with login, navigation, vocabulary, and the first knowledge check. Completing all of Week 1 and a realistic ticket is not a ten-minute promise. The instructor should introduce “user/device/problem,” progress notes versus resolution, and L1/L2 escalation before the first quiz, then demonstrate the unfamiliar CLI prompt before independent practice. Optional notes never block progression.

Refresh recovers the quiz and optional note draft on the same browser. Back/return retains server completions. A failed save is visible and retryable. Locked future work points toward requirements rather than masquerading as a server error.

## 9. Weeks 1–8 curriculum health

The [audit's Learn → Check → Practice → Troubleshoot map](NEXUS_STUDENT_EXPERIENCE_MASTER_AUDIT.md) lists required resources, assessments, tickets, prerequisites, and estimates for every week.

Weeks 1–4 form a useful progression from ticket documentation and hardware to account/diagnostic work and safe queue decisions. PR #39 corrects the Week 3 ticket and Week 4 structured queue practice. The isolated model reached Week 5 without circular prerequisites, and a separate extension reached Week 13 with required completion records synthesized.

Weeks 5–8 need the next curriculum pass: required time estimates are approximately 88/84/68/98 minutes, compared with week allowances of 300/210/300/300. Optional authored lessons add substantial instruction, so these figures are not proof the weeks are too short; they expose a teach/check alignment and estimation question. Do this review before learners reach Week 5.

Network+ remains Week 9+. With four active Network+ modules, the broader switch gate opens after two; the model observed this at the start of Week 11. The required introductory CLI exception is narrow. Hybrid stayed unavailable throughout. No claim is made that every Week 5–12 task was solved end-to-end in the browser.

## 10. Service Desk health

The existing workspace is a strength: reported problem, investigation tools, confirmed evidence, internal notes, verification, and resolve/escalate decisions represent useful support work. Desktop and 375/390px mobile views were inspected. Tests cover keyboard/tool switching, retained pane drafts, authentic grading evidence, offline outbox replay, pending-evidence completion, and legacy/V2 isolation.

The local Service Desk lint, typecheck, tests, build, and high-severity audit gate pass. Existing Turbo cache supplied some workspace validation; CI performs its own checks and container smoke. No Service Desk application code changed in this quality PR.

Remaining issues: unsent notes disappear on full reload/navigation, first guided-introduction state is browser-global, and some initial terminology needs scaffolding. Submitted records and mounted-pane state are different from unsent reload recovery. The audit's beginner workspace specification prioritizes these behaviors over a visual reskin.

## 11. Mobile / accessibility

Quiz layouts were measured at 375, 390, 768, and 1440px; tested answer cards are at least 44px high and do not cause horizontal page overflow. Keyboard Space selection and visible focus were exercised in Chromium; question navigation focuses its heading. Results and save/error states use text and live/alert semantics. Notes have an explicit label.

Screenshot review led to moving long questions inside their card and offsetting result focus below sticky navigation. Representative Today, lesson, CLI, Progress, admin, and Service Desk screenshots were inspected. These checks do not certify full WCAG conformance, contrast in every theme, screen-reader behavior, all dialogs, or Safari/mobile-device compatibility. Those remain focused follow-ups.

## 12. Admin / instructor experience

Students already shows password-change-required status and supports account reset. It is less effective at answering current module, repeated failures, active ticket, inactivity, and intervention needs at a glance. Last activity must not be labelled last login.

Before launch, reconcile the existing Admin Students work and verify the seven accounts through the instructor's normal account workflow. No real passwords were requested or exposed. After launch, build a compact needs-attention view from observed requirements rather than a large analytics system. The audit includes a concrete field and workflow plan.

## 13. Security / auth

Existing tests and source inspection cover server-enforced forced rotation, direct route/API restrictions, admin-reset session invalidation, student ownership, V2 provenance, and admin-only deletion. The disposable browser journey verifies invalid credentials, rotation policy, logout, reset, and preserved progress. No production auth bypass was demonstrated.

New drafts are scoped by learner, but localStorage is a convenience mechanism, not a security boundary against another person controlling that browser. No new answer-key endpoint or client grading was introduced. In-flight double clicks are prevented; concurrent tabs and ambiguous retries remain N13.

Frontend npm audit reports zero vulnerabilities. Backend manifest audit passed; the later environment-wide audit exposed old disposable-venv pip/setuptools tooling, which was upgraded within `/tmp` and then audited clean. Service Desk has two moderate package findings for [GHSA-82fw-gwwq-j7x9](https://github.com/advisories/GHSA-82fw-gwwq-j7x9), affecting `apps/api`'s Vitest/mocker 3.2.7; the audit lists 4.1.11+ as fixed. No application dependencies were changed.

## 14. Test results

| Area | Result / scope |
| --- | --- |
| PR #39 full backend | **1,213 passed, 7 skipped**, 10 warnings in final `b4d5711` CI. Earlier full local run: 1,206 passed, 2 skipped at `1303c55`; latest focused curriculum/V2/gating/lab suite: 84 passed; earlier upload/security suite: 62 passed. |
| PR #39 frontend | 70 passed after route regression fixes; build passed. |
| Quality full backend CI | **1,192 passed, 7 skipped**, 10 warnings at `ab79185`; manifest audit clean. CI uses a shallow checkout with historical-commit tests able to skip. |
| Quality frontend | 90 passed; production build passed; existing large-entry-chunk warning remains. |
| Quality browser | 27 core/auth/recovery/Service Desk/Weeks 1–4 checks + 2 P1 workspace + 1 P0 beginner integrity = **30 passed** on a fresh isolated stack. |
| PR #39 browser | 26 core checks plus ordered 2 workspace and 1 beginner integrity checks passed; final CI also passes the browser and integration job. |
| CLI | 48 catalog lessons validated; engine sanity passed. |
| Service Desk | Local lint/typecheck/build and 517 workspace tests passed, with cache use disclosed; configured high audit gate passes, two moderate findings remain. |
| Backend quality | Ruff, compilation, pip check, manifest audit passed in the PR #39 validation; no quality-branch backend changes. |
| Progression model | Synthetic required completion records through Week 12 reach Week 13; exact ticket/network/Hybrid boundaries checked. |
| Combined branches | 93 frontend tests, 84 focused backend tests, build, and all 30 browser checks pass after resolving the overlap paths. |
| Port collision | Occupied listener rejected before scratch DB or generated credentials; clean stack starts on verified ports. |

Failures were investigated, not hidden. Two stale quiz regressions, a failed-next-quiz route, two stale lab-route cases, two retired-upload cases, instructor assignment preservation, and three retired-V2 authorization cases failed before their fixes. A browser repeat reused a “fresh” learner already advanced by another spec; a fresh stack passed. Old browser assertions were updated for intentional Progress/review/save wording. The new recovery test initially compared `innerText` with `textContent`; consistent visible-text comparison fixed that assertion. An unrelated occupied port caused the first quality harness attempt to target the wrong frontend; only owned processes were stopped, and the harness now refuses this condition. Earlier Service Desk cold-start/cache collisions were isolated test-environment issues, separately rerun without changing production.

## 15. Open PRs / branches

| Branch / PR | Base | SHA | CI / review / readiness |
| --- | --- | --- | --- |
| `prelaunch/weeks-3-4-quality`, [#39](https://github.com/UnknownShadow00/nexus-admin-academy/pull/39) | main | `b4d57113a401a14ad3b186f9e80cd36b765740f0` | All six CI jobs pass; all 19 returned threads resolved; final independent review quota-blocked; not merged. |
| `prelaunch/nexus-student-experience-quality`, [#40](https://github.com/UnknownShadow00/nexus-admin-academy/pull/40) | main `07780a9` | `ab7918573c133a82f31f6e2d9a5fe19bffb781eb` implementation; this report follows without application changes | All six implementation CI jobs pass; final independent Codex review blocked by account quota; not merged. |
| [`prelaunch/nexus-student-experience-combined-validation`](https://github.com/UnknownShadow00/nexus-admin-academy/tree/prelaunch/nexus-student-experience-combined-validation) | PR #39 `b4d5711` plus quality `ab79185` | `4fc0193e54f28989954c70dca135d18a38538639` | 93 frontend + 84 backend + 30 browser tests pass locally; no separate PR/remote CI; not merged or deployed. |

[PR #39 implementation CI](https://github.com/UnknownShadow00/nexus-admin-academy/actions/runs/35711110244) and [PR #40 implementation CI](https://github.com/UnknownShadow00/nexus-admin-academy/actions/runs/35711252434) each passed all six jobs. Documentation-only follow-ups rerun the checks on the PR; no application change follows `ab79185`.

The [validation ledger](evidence/overnight-2026-09-22/VALIDATION.md) records exact test scope and the limitations of synthetic completion. Original dirty worktrees keep their original HEADs/file-status lists. All three owned stacks and copied model databases were removed after safe evidence capture.

The two PRs overlap in `QuizTaker.jsx`, its tests, and the append-only task log. The quality component/tests include PR #39's request-generation protections; the prepared combination keeps the quality versions and preserves both log histories. Remaining files combine automatically. A maintainer must use the documented tested resolution when updating PR #40 after PR #39 reaches main; no claim is made that two green independent PRs automatically merge without conflict.

## 16. Blockers before seven students start

No P0 product blocker was demonstrated. Before accepting this candidate release, require current-head green CI/review, reconcile the two PRs using the tested combination, and follow the project's normal explicit release process. This run is not deployment approval and did not deploy.

The instructor should verify the seven actual accounts/password setup and watch the first learner complete orientation. Real account status was not changed or certified here. Explain the Cisco CLI simulation before the first practice; do not wait until a beginner has already become stuck on its vocabulary.

Codex returned an explicit [account review-quota block on PR #40](https://github.com/UnknownShadow00/nexus-admin-academy/pull/40#issuecomment-5774113794), and [PR #39](https://github.com/UnknownShadow00/nexus-admin-academy/pull/39#issuecomment-5774256233). An independent review after quota restoration or by a human reviewer remains a follow-up; no final automated approval is claimed. No interactive credentials, sudo, or production write was needed for the completed work.

## 17. Safe to wait until after launch

Full formative-quiz mode, missed-concept spaced practice, richer authored explanations, broad dashboard analytics, CLI checkpoint persistence, Service Desk draft revision/sync, cross-tab submission idempotency, measured chunk splitting, and the test-runner dependency upgrade can be separate focused changes. Schedule the Weeks 5–8 alignment review before the cohort reaches Week 5; “after launch” does not mean indefinite deferral.

## 18. First week after launch plan

- Day 1: observe login/rotation, the ticket example, first quiz, and retry with each learner; note hesitation and accessibility needs without changing their history.
- Day 2: demonstrate the first CLI prompt, let learners predict output, then complete the first topic-gated ticket; check notes and return navigation.
- Days 3–4: review repeated missed concepts and incomplete tickets; give a short delayed retrieval question about documentation, identity, and safe investigation.
- Day 5: compare actual time with estimates, triage recurring blockers using audit IDs, and choose the smallest next improvement. Review activity as evidence, not as proof of independent skill.

## 19. Two-week product roadmap

Week 1: stabilize observed cohort issues; reconcile Admin Students work; add a concise first-CLI glossary/worked example; confirm draft/retry behavior; collect actual novice time estimates.

Week 2: complete the Weeks 5–8 concept/resource/quiz matrix; choose a narrow lesson requirement migration with history preservation if warranted; implement the highest-frequency CLI/Service Desk recovery issue; prototype only the essential instructor intervention fields. Design server idempotency and versioned historical quiz review separately. Keep later Network+ and Hybrid boundaries unchanged.

## 20. If I could change only five things before these seven students start, I would change:

1. Finish PR #39's progression and historical-access protections, including stale quiz/lab requests, so the required path stays trustworthy.
2. Give each learner a recoverable quiz draft with stable order/place and clear submission recovery.
3. Make quiz controls keyboard-visible and results teach through explicit answer/explanation review and a missed-question filter.
4. Teach the ticket vocabulary with a concrete example before the first required quiz, and explicitly introduce the first CLI simulation.
5. Make lesson completion, notes, review, and Progress failures honest, persistent, and retryable so beginners can distinguish their own work from a service failure.
