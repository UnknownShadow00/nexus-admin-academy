# Academy Phase 4 — Guided Ticket integration

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
- GitHub CI: pending draft PR creation.
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
