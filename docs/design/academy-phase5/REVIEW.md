# Nexus Academy Phase 5 — release-readiness review

Review date: 2026-10-10 (America/Chicago). Phase 5 is based on Phase 4 `bef6573`; the reviewed final head is recorded in the draft PR and its checks. Initial main-screen captures/comparisons use `b9ffb37`; result captures also include the subsequent operational-status correction. This is a **draft integration review, not release approval**.

- Draft stacked PR: [#69](https://github.com/UnknownShadow00/nexus-admin-academy/pull/69), targeting `feature/nexus-academy-integration-phase4`.
- Isolated branch/worktree: `feature/nexus-academy-integration-phase5`, `/home/nexus/worktrees/nexus-academy-integration-phase5`.
- Same-origin Academy + Service Desk preview: `http://127.0.0.1:5195` (API 8025, Service Desk 3015). Additional disposable curriculum preview: `http://127.0.0.1:5196` (API 8027).
- Preview credentials stay in private local test configuration. They are deliberately absent from this report and evidence package. These previews are loopback services, not public deployments.

## Engineering summary

The approved design, curriculum, server grading, progression, authentication, enrollment, scenario contracts and deployment configuration are preserved. Six focused product corrections were made:

| Reproduced problem | Correction and evidence |
| --- | --- |
| Lesson top tabs and step rail disagreed; section selection did not reliably survive reload/back. | Both now derive the active section from the validated route hash. Keyboard selection, section focus, reload, browser back and the footer completion anchor agree. Four new component tests failed before the fix and pass afterward. |
| Lesson background extended the document to 1028px at a 1024px viewport and 772px at 768px. | Use the existing compact shell's 24px gutter for the backdrop at tablet widths. No layout or artwork replacement. Six-width browser geometry assertions pass. |
| Long actual foundation module titles escaped Today learning-path cards by approximately 5–12px despite no document overflow. | Allow the text flex item to shrink and wrap. [Actual before/after crops](today-title-fix.png) show the defect and correction; all six widths and both themes check card boundaries. |
| Two synchronous note submissions could call the save handler twice before React updated the disabled button. | A synchronous in-flight guard permits one request. Failure preserves exact entered text and permits retry; only confirmed success clears it. The new component regression reproduced two calls before the fix. |
| After reload, a completed ticket could show its scenario's initial OPEN status beside the actual pass result. | Completed headers now read operational status from the matching server attempt's stored ticket snapshot. [Actual before/after evidence](ticket-status-fix.png). Unknown/mismatched status is not guessed from pass/fail. Five status variants, failed/pending grades, legacy snapshots and missing/malformed metadata have focused tests; the real assessment/Practice browser regression also checks RESOLVED after reload. |
| Next.js 15.5.24 had two moderate runtime advisories. | Exact patch update to 15.5.27 with a coherent pnpm lockfile. Unit, lint, typecheck, builds and real cross-application browser checks passed. No broad dependency upgrade. |

Test-only changes add the actual-API responsive/pending-worker suite to CI, fetch full history for backend/seed historical migration checks, capture Phase 5 result evidence, and make an existing randomized multi-select test select answers idempotently with `check()`. Its old `click()` could deselect the already-selected first answer. An answered-count assertion now checks the precondition before submission; no product grading or test expectations were weakened.

No new backend runtime code, migration, authored content, image asset, dependency family, navigation route or grading rule was introduced.

## Verification results

Commands used the existing project tools, with memory-heavy builds/tests run sequentially. Dependencies were installed only in the new worktree. The existing private Python environment was reused without changing it.

| Check | Result and scope |
| --- | --- |
| Frontend `npm test` / Vitest | **246 passed**, 42 files, on final code. Existing canvas-environment notice remains nonfatal. |
| Backend complete `python -m pytest -q -rs` | **1,349 passed, 3 skipped**, 10 warnings, 14m32s, including the new pending-worker regression. The earlier baseline collected before that test and had 1,348 passes. |
| Written assessment focused suite | **19 passed**, including the added actual-handler/ORM worker and authorized reconciliation regression. This overlaps the full suite and is not added to its count. |
| Service Desk `pnpm test` | **546 passed**: shared 37, UI 36, simulation 269, web 204. The API package has no unit tests; its pass-with-no-tests result is not claimed as API coverage. |
| Actual Academy/Service Desk browser journey | **43 passed** in ordered existing suites plus the new Phase 5 suite, on disposable SQLite and real authenticated APIs. |
| Additional actual Academy curriculum browser suites | **48 passed** on a fresh disposable preview, covering Phase 1/2/3 legacy and V2 surfaces. |
| Synthetic pending UI fixtures | **2 passed**. Mocked responses, reported separately from the real pending submission/worker test. |
| Frontend production build | Passed. Main JS chunk approximately 685KB (226KB gzip) still produces the existing >500KB warning. |
| Service Desk lint / TypeScript | Passed, 5 lint tasks and 10 typecheck tasks. |
| Service Desk production builds | Passed with Next 15.5.27, including the integrated environment. The isolated Service Desk preview runs the production build after the full browser pass; its separate smoke check covers queue/session, persisted Practice result, reload, secure Academy launch/return and unchanged XP/ticket totals. |
| Backend configured CI lint / compile / pip check | Passed: `ruff check app tests seed.py seed_curriculum.py`, Python compilation, dependency consistency. |
| Dependency audits | Frontend 0; Service Desk runtime 0, all-dependency audit 2 moderate development-only findings; backend application requirements 0. Details below. |
| Git whitespace validation | Passed. |

The three local backend skips are explicit: two retired legacy INC2504 route cases in `test_service_desk_realism.py` (the scenario is gated V2-only and its supported path is exercised), and one PostgreSQL concurrency test without `NEXUS_TEST_POSTGRES_URL`. GitHub CI supplies disposable PostgreSQL; its outcome must be checked separately, not inferred from SQLite.

An optional wider `ruff check .` found 19 pre-existing unused-import errors in historical migration/seed/audit scripts outside configured CI lint scope. These were not changed as unrelated cleanup. Test warnings include existing framework/API deprecations.

Early browser attempts exposed test-environment/precondition problems: a Next dev/build collision, dependent suites run in the wrong order, and reusing a fixture whose legacy course was already completed. Those attempts are not counted as passes. Only this Phase 5 stack was recreated. A later browser regression expected the historical header to revert to OPEN; actual stored server state verified RESOLVED. That assertion was corrected and strengthened to require the saved server status after reload and in a clean browser, independently of pass/fail. The complete ordered pass and fresh Academy pass are reported above. The multi-select test defect above was reproduced and fixed separately.

### CI provenance

Before editing, origin/main was verified at `663d623`; PR #68 at `bef65734d5187eac006ce5ff18fbe23628f6c55b`. Ancestry checks confirmed `2ddb099`, `2cccddc` and `ec294c6`. All six PR #68 checks ultimately passed. Its backend job completed with **1,344 passed, 7 skipped**: five historical-source checks skipped in the shallow CI checkout, plus the two retired legacy ticket cases. Its disposable PostgreSQL test ran. Phase 5 now fetches full history in backend and seed jobs to remove those five avoidable skips; the local full-history run already covers them. No failed check was disregarded.

All six checks passed for initial Phase 5 code `b9ffb37` ([run](https://github.com/UnknownShadow00/nexus-admin-academy/actions/runs/38098736518)). Final-head results, including the subsequent status correction and full-history checks, are tracked in [PR #69 checks](https://github.com/UnknownShadow00/nexus-admin-academy/pull/69/checks) and summarized in the PR description after completion. Evidence-only commits also trigger CI, so a green earlier code run is not represented as a green later head. The final evidence ZIP includes a separate CI result snapshot. The deploy-script checks simulate failure paths; they do not deploy anything.

## Visual comparison and accessibility

- [Light comparison](comparison-light.png) and [dark comparison](comparison-dark.png): approved `76b4a15` prototype on the left, actual integration on the right; rows Today, Lesson, Quiz and Guided Ticket. Source desktop images are uniformly scaled crops, not stretched artwork.
- `today`, `learning-path`, `lesson`, `quiz`, `ticket`, and `ticket-queue` each have light/dark evidence at **1440px and 390px**. All **1440, 1280, 1024, 768, 390 and 320px** widths were exercised in both themes; redundant intermediate-width screenshots were not retained.
- `written-pending-{light,dark}-1440.png` uses a real accepted written submission and real API state, not the separately tested synthetic fixtures.
- `quiz-result-{light,dark}.png` captures a real server-graded assessment result after exercising failed-transport recovery. This focused evidence rerun overlaps the 48-case Academy suite and is not added to its count.
- `ticket-result-{light,dark}.png` shows a historical server-graded independent assessment. `ticket-practice-result-{light,dark}.png` shows a subsequent actual optional replay with no new XP or completed-ticket credit. Their data differs because they are different real attempts.
- Existing tool, notes and feedback visuals remain available in [Phase 4 evidence at the approved correction](https://github.com/UnknownShadow00/nexus-admin-academy/blob/bef65734d5187eac006ce5ff18fbe23628f6c55b/docs/design/academy-phase4/REVIEW.md), including `ticket-tools-*`, `ticket-notes-mobile-*`, `ticket-note-saved-*` and `ticket-feedback-*`. Those are retained baseline evidence, not newly claimed Phase 5 captures.
- The six interaction types' light/dark feedback references remain in [approved Phase 3 evidence](https://github.com/UnknownShadow00/nexus-admin-academy/blob/ec294c6/docs/design/academy-phase3/REVIEW.md). Their real API-backed exercises were retested in both themes; their styling was not changed or duplicated into this evidence folder.

The castle/hood/shadow artwork, cards, page structure and themes are retained. Real module titles, actual counts, supported navigation and server states intentionally differ from fictional prototype text. The separate Service Desk application's tools/evidence/actions remain available even where the prototype showed a conversation mockup. Unsupported prototype controls were not added.

Normal scrolling and keyboard navigation were exercised in addition to screenshot capture. Images decode successfully and use cover/contain framing. No horizontal page overflow was found after the fixes. The skip link is hidden above the viewport until focused; Enter focuses learner content and removes the overlap. At 320px, section controls and the lesson footer remain reachable above fixed navigation. Service Desk notes can be focused and scrolled into the usable viewport. Theme persistence, focus and existing contrast assertions pass. No new browser page errors occurred in the matrix.

Full-page mobile captures show fixed navigation at its viewport position; this does not mean the navigation scrolls with the document. Initial in-progress ticket captures used the isolated Next development server and can show its development indicator; queue/practice-result captures were refreshed from the production build. No indicator was removed by editing the screenshots.

Known limits: Chromium automation does not certify a physical phone's software keyboard, every screen reader, every authored content combination, or every external video player. These remain manual release checks. No additional Lesson shadow artwork was generated or imported.

## Learning-flow verification

| Transition / boundary | Evidence and result |
| --- | --- |
| Login, forced password change, role separation, logout/session handling | Existing actual-stack forced-password, recovery, navigation and Service Desk suites passed; backend permission/session regressions passed. Admin/scenario-authoring checks remain intact. |
| Today → Learning Path → correct lesson/resource/Quick Check | Actual API curriculum titles, objectives, continuation destinations and module counts were exercised for legacy and V2 enrollments. Locked/unlocked states use server responses. |
| Teaching resources | Existing destinations and Professor Messer attribution preserved; link opening is distinct from watched evidence. Opening a video does not automatically complete it. Required-resource structure and asset tests pass. |
| Lesson notes, completion, history | Real legacy note persistence, V2 resources/completion, section reload/back, footer navigation and server-owned progression tested. The Phase 2 browser regression also found the same-state Today screenshot byte-identical before/after visiting Lesson. |
| Six interaction types | Matching, image identification, ordering, command-output interpretation, typed answers and safe actions exercised through actual API-backed browser content and existing service tests. Persistence, revision and safety failures retained. |
| Quick Checks / module assessments | Single and multi-select, stable identities, student-scoped drafts, reload recovery, stale attempts, unanswered warnings, failed network retry, double-submit prevention, actual result review and prerequisite gates covered by browser/component/backend suites. |
| Written response → pending → worker/review | New browser test accepts original prose, survives reload, hides provisional grade/keys/retry, denies student queue access and runs the authorized existing worker with automatic grading disabled. Durable job becomes `needs_review`; XP and ticket count remain unchanged. Backend test also exercises authorized override reconciliation. |
| Secure Academy → Service Desk | Existing same-origin session launch, correct scenario/assignment, enrollment/prerequisites and return-to-module mechanisms tested with real handlers. No tokens added to URLs or local storage. |
| Guided investigation → trusted result | Real tools, remediation, notes, action history, verification and closure passed. The P0/V2 route earned the required ticket activity through server grading; it did not falsely complete the entire module. |
| Independent result → optional Practice replay | Actual INC2501 assessment result remained labeled by its graded attempt despite the next launch mode being Practice. Completing the replay returned a practice pass with unchanged XP/completed-ticket totals. Reload/render also awarded nothing. |
| Failed, escalated, pending and mentor correction states | Existing backend, component result-mode and actual-stack suites cover accurate statuses, retry policies, evidence failures, mentor feedback and no premature credit. No backend rule was changed to improve wording. |

This is **not** a claim that one disposable beginner earned the entire published curriculum in a single uninterrupted browser session. The main stack contains explicit prerequisite fixtures for qualified accounts. The additional Academy preview's practice account has fixture continuation grants for later-stage coverage; its ungranted V2 account tests locks. The full-module backend rehearsal explicitly seeds practical review/onboarding evidence. Those fixture records are not presented as browser-earned learning achievements. Separately, actual beginner-continuation service tests exercise supported stage progression and locking through API handlers. No missing transition was filled with invented production progress.

External destination spot checks succeeded for [Professor Messer multifunction devices](https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/multifunction-devices-220-1201/), [IPv4 and IPv6](https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/ipv4-and-ipv6-220-1201/), and [Microsoft printer troubleshooting](https://support.microsoft.com/en-us/windows/hardware/printer/fix-printer-connection-and-printing-problems-in-windows). These are samples, not an exhaustive live-link or playback certification. No curriculum destination or video ID was replaced.

## Security, grading and data integrity

No frontend calculation awards XP, mastery, ticket credit or assessment completion. The Phase 4 `bef6573` correction remains intact: display mode comes from the matching graded attempt, missing metadata uses neutral wording, pending review is not a final grade, and Practice replay does not meet required assessment credit. Existing guided/practice/assessment/fail/escalation/pending result tests were retained. The additional operational-status correction reads the stored server snapshot independently of grade; a failed assessment can still truthfully have a resolved operational status. It does not modify simulator state or award anything.

Actual isolated coverage includes unauthorized roles, cross-student attempts/answers/tickets, forged progression and missing evidence, locked prerequisites, session handoff, duplicated/replayed actions and XP idempotency. The new written-worker regression checks student denial of queue/override access, exact original wording, durable review status, no provisional XP and reconciliation without falsely passing unanswered questions. These tests do not establish production cookie/proxy/worker configuration correctness.

### Written-grading operations

The existing `PendingGrade` queue is durable. With `AI_GRADING_ENABLED=false`, an ambiguous written submission is accepted but cannot automatically become a final grade. The existing worker sends it to `needs_review`; repeated worker calls do not invent a pass. Authorized existing mentor/admin overrides can reconcile it, as tested. No paid provider, human reviewer or turnaround time is promised.

Before release, an owner must verify actual worker availability, authorized review staffing, visibility/age of pending jobs, retry/terminal-failure handling and reconciliation in the target environment. None of that live configuration was changed or asserted operational here.

### Native typed-answer proposal — approval required, not implemented

The Phase 3 proposal is still necessary. Native `V2InteractionAttempt` requires a numeric score and Boolean pass/fail; it has no accepted-but-ungraded lifecycle or native worker reconciliation. Natural paraphrases can still receive the existing failed grade. The approved deferral was honored.

Minimum backward-compatible implementation:

1. Add explicit native grading state and durable job linkage; allow null grade only in ungraded states. Preserve immutable question/definition/response snapshots. Backfill historical final grades as graded without regrading, unlocking or awarding anything.
2. Use a student-scoped submission UUID plus interaction/version identity and payload hash. Identical retries return the same attempt; reused keys with different payloads conflict. Keep it across transport retries and enforce current attempt/retry rules.
3. Persist attempt and queue job transactionally, with stable `v2-interaction-attempt:<id>` source references. Reuse existing queue claim tokens, retry/backoff and terminal/review states. Extend reconciliation explicitly; current handlers support written assessment/Explain sources, not native interactions.
4. Reconciliation locks and verifies student, attempt, definition version and grade generation. Only a trusted final pass can create required evidence/XP; award/evidence uniqueness makes repeated reconciliation harmless. Stale workers must not overwrite authorized overrides. New revisions are new immutable attempts where permitted, not mutations of historical proof.
5. Version/capability-gate the API so old clients expecting numeric grades do not misread nulls. Preserve the other interaction types and deterministic safety-critical failures. Provide real authorized review operations before advertising pending acceptance.

Required tests: SQLite and PostgreSQL concurrency; transaction rollback; identical/conflicting replay; ownership and enrollment; stale versions; original wording/size/security boundaries; pending with no keys, XP or unlock; worker timeout/retry exhaustion/recovery; authorized override audit and precedence; duplicate/stale reconciliation; retry/revision policies; historical compatibility and all six existing interaction types. Schema/API/queue changes need separate approval.

### Workstation-note proposal — approval required, not implemented

The workstation `remote_desktop.add_internal_note` action can reject reasonable paraphrases because trusted evidence validation uses authored fact strings. General ticket notes already support natural saved text; this is a different contract. Rejected workstation text remains in the current interface, but is not independently saved and can be lost on reload. The duplicate-submit fix does not change this limitation or evidence rules.

Minimum separation:

1. A distinct save-only record/action stores original plain text, owner, ticket, attempt, scenario version, revision parent and timestamps within reviewed size/security limits. Saving must not create validated objective evidence or XP. Show “saved, not validated” only after server confirmation; failed saves retain text.
2. Validate a selected immutable revision separately using trusted rules. Store the outcome with revision/scenario/rubric identity. Editing creates another revision and does not silently transfer validation. Historical completed-attempt evidence remains immutable.
3. Enforce session, enrollment, current-attempt and ownership checks on save/read/revise/validate. Escape notes as text, prohibit unsafe control content, retain privacy/redaction policy and avoid token storage. Define concurrent-edit conflicts and replay behavior with submission keys/payload hashes.
4. A retry/new attempt must not inherit prior validated evidence. Optional copying is an explicit unvalidated draft. Any browser draft must be student/attempt scoped, cleared on logout and have a server conflict policy. Closure still requires actual trusted diagnostics, remediation, verification and server grading.

Required tests: natural wording save/reload, revision history, conflicting edits, bounds/control characters, unauthorized/cross-student access, failure recovery, duplicate requests, old scenario/attempt replay, evidence-to-revision linkage, no early XP/unlock, and unchanged safety/closure rules. This new persistence/evidence contract needs separate approval; existing fact matching was not weakened.

## Dependency review and performance

| Finding | Exposure, action and risk |
| --- | --- |
| Next.js 15.5.24, two moderate advisories | [Cache poisoning advisory](https://github.com/vercel/next.js/security/advisories/GHSA-4jqv-mc3x-m676) and [routing/cache advisory](https://github.com/vercel/next.js/security/advisories/GHSA-mcj8-r9mp-w47p). Specific Pages Router/SSG or root catch-all conditions are not the current Service Desk App Router shape, but a runtime package is involved. Updated to patched 15.5.27; builds and affected tests passed. |
| Vitest 3.2.7 and `@vitest/mocker` 3.2.7, two moderate findings | Development-only [mocker-server arbitrary file read](https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9); no application use of the affected standalone mocker plugin/interceptor was found. Not in runtime audit. Fix is 4.1.11, a major test-tool upgrade; defer to separately validated workspace upgrade rather than broadening Phase 5. Do not expose development test servers. |
| Python shared test-environment tooling | The application requirements audit is clean. The reused private environment separately reports pip 24.0/setuptools 79.0.1 tooling advisories; these are not application-manifest packages. The environment belongs to prior verification work and was not upgraded. Refresh disposable tooling separately. |

Approved Academy artwork totals approximately 4.7MB, with the largest hooded and sentinel panels approximately 1.9MB/1.3MB. No quality-reducing compression was applied. Cache-warm local development samples reached ready content/images in approximately 0.7–2.1s, with 6–15 API reads depending on the page; repeated image requests used cache/304 responses. This is diagnostic sampling on a shared test host, not a production latency promise.

Development layout-shift samples were approximately Today 0.013, Lesson 0.175, Quiz 0.056, queue 0. Enrollment navigation/account metadata and asynchronous lesson catalog metadata can shift content. These were not addressed by redesigning the shell. Follow-up should reserve metadata space and measure a cold production build before choosing a focused fix. The frontend chunk warning also merits later measured route splitting. No browser memory failure remained after avoiding overlapping Next builds.

## Release-readiness checklist and blockers

| Priority | Finding / required next step |
| --- | --- |
| P0 | **None demonstrated in this review.** This is not a declaration that production has no undiscovered issues. |
| P1 | Native typed free-text accepted-but-ungraded schema/reconciliation remains the owner-approved pre-release blocker. Review the proposal and tests above before implementing it. |
| P1 | Workstation note save/evidence separation is unresolved: a reasonable paraphrase can be rejected and an unsaved note lost on reload. Review the contract proposal without weakening trusted evidence grading. |
| P1 | Written-grade worker/review availability in the target environment is unverified. Without an operating worker/reviewer, accepted prose can remain pending and block progression indefinitely. Verify operations and recovery before release. |
| P1 | Final target-environment same-origin/cookie/proxy/session and deployment verification remains owner-gated. Local tests cannot certify production integration; no deployment was attempted. |
| P2 | Service Desk development-only Vitest/mocker major upgrade; refresh private Python test tooling. Runtime application audits are clean after the patch. |
| P2 | Measure/fix asynchronous metadata layout shifts and main-bundle weight; perform physical-phone keyboard and assistive-technology checks, and broader external-link review. |
| P2 | Historical migration/seed/audit-script lint cleanup outside the configured CI gate. |
| Cosmetic | Additional Lesson shadow imagery and optional polish remain deferred. Approved artwork/layout is preserved. |

- [x] New isolated branch and draft stacked PR; approved Phase 1–4 ancestry verified.
- [x] Focused regression fixes and real isolated API/browser coverage; design preserved.
- [x] Six widths, both themes, desktop/mobile evidence and prototype comparisons.
- [x] Proposals recorded without migrations, grading rewrites or paid providers.
- [ ] Owner visual/functional review and explicit approval for remaining architecture work.
- [ ] Operational grading/release-environment verification before any production release.

## Exact changed files and safety confirmation

[changed-files.txt](changed-files.txt) is the complete manifest relative to `bef6573`. Product changes are limited to the shared Lesson component, two Academy stylesheets, the Service Desk note panel/result-status presentation and the Next patch/lockfile. Other code changes are regression tests and CI coverage; remaining files are this review, selected evidence and the required completion log.

Production checkout remained at `663d623`; the approved prototype remained at `76b4a15`. PR #65–#68 branches/worktrees, unique existing work, production services/databases/student data, secrets and deployment configuration were not modified. No merge, deploy, production migration, grading-rule change or new phase was performed.

Recommended next step: owner review of draft PR #69 and this evidence, then separate approval of the two grading/persistence proposals and grading operations before release-readiness signoff.
