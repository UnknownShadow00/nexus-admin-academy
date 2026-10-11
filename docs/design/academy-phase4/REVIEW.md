# Academy Phase 4 — Guided Ticket integration

## Result accuracy correction after review of `f3a4dfa`

**Finding: misleading presentation, not a demonstrated backend credit/progression defect.** The old result screenshot contains a real, persisted **assessment** pass. After that pass, the assignment API changes its next launch mode to `practice` while retaining the completed assessment as `most_recent_attempt`. The header incorrectly used the next launch mode; the debrief also called every result an assessment and claimed module credit from a Boolean pass.

The completed header and result now use the matching graded attempt's server-returned `id` and `experience_mode`. Missing/mismatched metadata produces neutral “Ticket result” wording without a credit claim. Active workspace modes, grading and evidence validation are unchanged.

| Server state | Result wording / behavior |
| --- | --- |
| Guided pass | “Guided practice result: PASS — check Academy for activity progress.” |
| Practice pass | “Practice result: PASS — no assessment credit or mastery XP.” |
| Independent assessment pass | “Assessment result: PASS — check Academy for awarded credit.” |
| Failed attempt | Mode-specific “NEEDS ANOTHER ATTEMPT — no pass for this attempt.” Does not revoke earlier credit. |
| Server-confirmed successful escalation | Mode-specific “ESCALATED SUCCESSFULLY” with the same mode-specific credit wording; a failed grade cannot become a pass from operational escalation. |
| Server `awaiting_review` | Mode-specific “AWAITING REVIEW — no final result yet.” Scores are explicitly provisional; no retry prompt while review is pending. |
| Local closure not yet graded by API | “AWAITING SERVER RESULT — not yet graded.” This does not imply a mentor queue. |

Authoritative rules reviewed and preserved: `complete_attempt` awards mastery XP only for an assessment pass, with ledger idempotency; Service Desk progression and progress-summary use authoritative assessment attempts. V2 module activity credit additionally requires the trusted curriculum launch and correct required guided activity. An optional practice/assessment pass cannot earn initial required V2 activity credit; subsequent failures cannot revoke already earned credit. No result wording awards XP or changes progression. The grade API has no module-credit/XP award receipt, so the UI does not claim an amount or module completion from the displayed grade.

Corrected existing historical assessment screenshots: [light](ticket-result-light.png) / [dark](ticket-result-dark.png). Actual completed practice replay: [light](ticket-practice-result-light.png) / [dark](ticket-practice-result-dark.png). These four images come from the same-origin preview and real disposable API; no response mocking or synthetic grades. The six approved Guided Ticket screens, comparisons, CSS, artwork, layout and Today/Lesson/Quiz runtime are unchanged.

Verification for this correction:

- Service Desk web: all **196 unit tests** passed, including mode-specific pass/fail/escalation/review, mismatched attempt IDs, historical assessment header, pending-server wording, provisional scores and resolved-but-failed presentation. ESLint and TypeScript passed.
- Backend: **155 tests passed** across attempts, assignment modes, escalation and V2 runtime stabilization; after adding a failed-practice case, **4 focused parameterized regression cases passed**. These run real router/service code with disposable in-memory SQLite, not production services. They verify assessment-to-practice history, passed/failed practice without additional XP/progression, repeat completion idempotency, and guided-only initial V2 activity credit.
- Real browser/API: **1 end-to-end test passed** on the isolated Academy + Next + API stack. It reopens the actual assessment, starts an optional practice attempt through the authenticated API, performs all real simulator diagnostics, documentation and closure, reloads its server grade, and verifies XP and completed-ticket totals remain unchanged both after practice and after rendering results. Existing beginner test retains its server V2-credit assertions and now expects the actual completed guided mode after reload. CI runs the new replay after the existing assessment workflow.
- Pending review is covered by UI fixtures; this pass does not introduce a review queue or claim a real mentor-reviewed attempt was tested. Production behavior is untested and production is untouched.
- Audit: Academy production npm dependencies and backend requirements report no known vulnerabilities. The unchanged Service Desk production lockfile reports two moderate Next.js SSG/ISR advisories, no high/critical; no dependency upgrade is included.

This correction leaves trusted backend runtime, authentication, ownership, prerequisites, scenarios, evidence, XP/progression and retry limits untouched. No migrations, deployment, merge, Phase 5 or deferred grading changes. Current-head CI results are tracked in PR #68; the earlier full CI results below apply to `f3a4dfa`.

## Scope and lineage

- Base: verified PR #67 head `ec294c6e22d8a6f9345528b1caa64bd43d391051`.
- Verified ancestors: Phase 1 `2ddb099`, Phase 2 `2cccddc`.
- Branch/worktree: `feature/nexus-academy-integration-phase4`, `/home/nexus/worktrees/nexus-academy-integration-phase4`.
- Visual authority: prototype `76b4a15`, its `prototype/screens.js`, `prototype/styles.css`, and `evidence/refinement/final/ticket-{light,dark}-1440.png`, inspected before editing.
- PR #64 was not used. No previous worktree, production source, production service, live database, curriculum, grading rule, or deployment configuration was changed.

## Focused implementation map

| Existing authority | Reuse / adaptation |
| --- | --- |
| Academy `V2ServiceDeskRedirect` and curriculum launch API | Unchanged secure handoff and validated module/assessment context; real enrollment and prerequisite checks. |
| `service_desk_bridge`, contract 2.0, progression and objective validation | Unchanged backend-owned progress, attempts, XP, evidence, review and completion. |
| Next `ApplicationShell`, `Header`, session provider | Learner-only Academy frame; retain existing tools, account/profile, sync status, dialogs and supported return links. Reuse the authenticated Academy global search API and lesson/command destinations. Operational/admin/standalone shell remains available. |
| `TicketWorkspace`, workflow rail, notes, requester/device cards, queue | Approved ticket header above investigation/notes with an evidence/details rail. Keep real tools, authored content, actions, retries, hints and case switching. |
| Existing Academy `/academy/` assets and theme storage | Reuse the same-origin artwork and `theme` preference. No duplicate assets or new dependencies. Portal dialogs inherit learner colors. |

## Visual evidence

All evidence is rendered from the real React + Next + isolated API stack, using the repository's seeded authored scenarios and disposable accounts. No API mocking or fabricated grades were used. Test-only instructor assignments in the established stack are fixture setup, not proof of production enrollment configuration.

Main screenshots:

| Width | Light | Dark |
| --- | --- | --- |
| 1440 | [Guided Ticket](ticket-light-1440.png) | [Guided Ticket](ticket-dark-1440.png) |
| 1280 | [Guided Ticket](ticket-light-1280.png) | [Guided Ticket](ticket-dark-1280.png) |
| 390 | [Guided Ticket](ticket-light-390.png) | [Guided Ticket](ticket-dark-390.png) |

[Prototype comparison — light](comparison-light.png) · [Prototype comparison — dark](comparison-dark.png).

Additional evidence: `ticket-queue-{light,dark}.png`, `ticket-tools-{light,dark}.png`, `ticket-feedback-{light,dark}.png`, `ticket-result-{light,dark}.png`, `ticket-note-saved-{light,dark}.png`, `ticket-notes-mobile-{light,dark}.png`.

The prototype's synthetic requester chat is not substituted for the simulator's actual case. Reported symptoms, native workflow stages and live tools occupy the corresponding investigation area. Unsupported prototype controls (fictional requester replies, category changes, mentor messages) were not added. Real tool UIs remain fully functional, including the independent Windows desktop inside the Academy frame.

## Isolated preview

Academy and Service Desk share `http://127.0.0.1:5194`; API is loopback port 8024 and Next is loopback port 3014. The Academy proxy serves `/service-desk` and `/api` under one browser origin. No production proxy or service configuration was changed.

Disposable credentials and local server logs are private under `/home/nexus/.cache/nexus-academy-phase4/stack-owner/`; they are excluded from Git/evidence. Use an SSH tunnel to port 5194 for remote browser review. Production data and credentials were not used. If the host is restarted, these development processes must be restarted before previewing.

## Verification

- Academy: 242 frontend unit tests and production build passed.
- Service Desk: full workspace unit suite, lint, TypeScript and production build passed. Build and dev-server checks run separately to avoid sharing Next's build directory.
- Backend: 190 focused tests passed (bridge, attempts, escalation, integrity, workflow view, progression, retries, anti-gaming, V2 prerequisites/onboarding, admin review).
- Actual isolated API browser integration: all 14 existing Service Desk integration tests passed, including tools/remediation, access restrictions, reload/offline replay, grading, duplicate completion/XP, cross-student isolation, mentor feedback and scenario draft/version publishing.
- Additional real API browser checks: 5 persistent-workspace tests, 2 independent-workflow/blocked-resolution tests, 4 Phase 4 tests (responsive/theme/search/navigation, server result, natural ticket notes without XP, missing-session recovery), and 1 beginner V2 completion test passed. The added Phase 4 checks were run before completing the shared guided assignment, as required by their fixture ordering. All six main screenshots and additional evidence were captured from the actual isolated stack. All 11 applicable authentication, password rotation, dashboard/lesson/quiz navigation, admin and mobile-recovery checks passed. One fresh-student dashboard assertion initially ran after shared fixture progression; it passed unchanged using a newly created disposable student through the real admin/login/password-rotation APIs.
- Initial CI exposed two legacy browser selectors that filled all visible inputs by position; the new search field shifted simulator-login inputs. Selectors now target the existing simulator placeholders, with functional assertions unchanged. This test-only correction does not change the captured UI.
- Draft stacked PR: [#68](https://github.com/UnknownShadow00/nexus-admin-academy/pull/68), targeting `feature/nexus-academy-integration-phase3`. GitHub CI results for the final head are available in the [PR checks](https://github.com/UnknownShadow00/nexus-admin-academy/pull/68/checks); consult those checks for the current status.
- Dependency audit: Academy npm and backend requirements have no known vulnerabilities. Service Desk frozen lockfile reports four moderate findings and no high/critical findings; dependency upgrades are outside this visual integration phase.

## Functionality preserved

Academy login/logout and feature flags; existing secure session cookies; enrollment and prerequisite enforcement; ticket queue/assignment; actual scenario/version data; all supported tools and action contracts; investigation/history/events; note persistence and failure recovery; escalation and resolution verification; trusted grading, XP, retries and attempts; mentor corrections/review; admin authoring; existing return/module navigation. Academy Today, Lesson and Quiz runtime source is unchanged.

## Grading/security boundaries and remaining gaps

1. **Workstation documentation remains gated by authored fact checks.** Native `remote_desktop.add_internal_note` validates scenario facts before accepting documentation evidence, unlike general `ticket.add_note`. It can reject paraphrases that omit fact strings. This phase preserves that authoritative rule, keeps the student's rejected text in the editor, and gives retry guidance without claiming that a natural-language answer is objectively wrong. General ticket notes continue to accept natural wording within existing limits; saving one does not award credit.
2. **Separate approval proposal:** introduce a clearly distinct save-only workstation note contract, then submit selected documentation for existing evidence validation. Specify persistence, replay, size limits, ownership, revision history and truthful saved-versus-validated status. Review how this interacts with grading before implementation. No schema, event contract, validation or grading change was made here.
3. The pre-release native V2 typed-answer pending-grade schema/reconciliation blocker from Phase 3 remains deferred, as do grading-worker operations and final deployment verification.
4. Production-only cookies, proxy configuration, deployment operation and live student behavior remain untested. The local same-origin tests are real API integration on disposable SQLite, not a production verification claim.
5. The learner shell uses real profile and support controls instead of fictional rank/XP/notifications where the Service Desk shell lacks equivalent reliable data. Actual XP and progress continue to come from the existing Academy/Service Desk APIs. Real scenario differences prevent a pixel-identical copy of the synthetic prototype.
6. No Lesson shadow imagery, unrelated mobile polish, curriculum additions, new scenarios, paid APIs, Phase 5 work, merge or deployment.

Exact changed paths are in [changed-files.txt](changed-files.txt). Owner visual and functional approval is required before continuing.
