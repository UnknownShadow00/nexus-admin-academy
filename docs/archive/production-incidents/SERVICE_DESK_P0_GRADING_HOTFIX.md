# Service Desk P0 Grading Hotfix

## Scope

This code-only hotfix aligns the simulated Remote Desktop workflow with the
server-owned Service Desk grade. It creates no database migration.

## P0 #1: INC2405 verification evidence

**Root cause.** File Explorer correctly recognized a repaired Facilities
Calendar mapping and set the local `scenarioProgress` verification phase, but
that local fact never became the matching
`remote_desktop.perform_scenario_step` event required by the server. There was
no normal Explorer control that invoked a matching scenario-step action.

**Design.** A scenario declares server evidence keys that arise from genuine UI
transitions. The action dispatcher applies the Explorer navigation first, asks
the simulation engine whether it reached one of those declared keys, then
queues the derived scenario-step event immediately after the navigation. This
is reusable metadata-driven behavior, not an `INC2405` button or a ticket-ID
conditional in the UI. The server requires a trusted source navigation after
the preceding process phases before accepting `explorer.verify-share`; direct
or replayed step posts are rejected.

The reachability tests prove that the normal INC2405 Explorer workflow derives
the audit event without a manual `performScenarioStep` call, and that the
server rejects a direct step lacking its Explorer source. INC2406’s real
Explorer root navigation is also exercised against server grading.

## P0 #2: Windows path matching

**Root cause.** INC2406’s UI emits File Explorer’s `Z:\\` drive root, while
the objective rule stored `Z:`. Payload matching used exact scalar equality,
so valid Explorer evidence was rejected.

**Design.** `payload_matches()` has a strict allowlist of semantic Windows path
fields: `path` and `uncPath`. It canonicalizes drive roots (`Z:` and `Z:\\`)
and UNC spelling (case, duplicate/trailing slash). All other evidence payload
fields remain exact; ticket IDs, asset tags, step IDs, and commands are never
normalized.

## Client/server final-grade divergence

**Root cause.** The browser completed a local scenario checklist and rendered
`scenarioProgress.finalScore` / local grade data as a final result before the
authoritative completion endpoint had accepted and graded the attempt.

**Design.** Local workflow state is interim UX only. The completion panel now
renders final pass/fail, score, and feedback only from the `NexusGrade` returned
by `POST /attempts/{id}/complete`. Until that response arrives it explicitly
shows an awaiting-server state. A rendering test gives local state an
optimistic 100 and a server grade of 40 and proves only 40 is displayed.

## Close Ticket gating

**Root cause.** Close Ticket used the local workflow phase checklist. For
INC2405 that checklist had a verification fact which was disconnected from the
server evidence ledger, leaving the client and server unable to agree.

**Design.** The existing closure gate continues to use the scenario workflow
tracker, but it now receives its verification phase from the same real
Explorer-derived evidence path that is queued to the server. The server
completion endpoint remains the final authority and can reject closure.

## Assessment hint leak

**Root cause.** Persisted Guided-mode reveal counts were reused by Assessment
rendering, and Assessment showed hints after completion.

**Design.** Assessment mode always returns an empty hint body list, and the UI
also zeros any persisted local reveal count for Assessment rendering. This is
safe across Guided-to-Assessment transitions, refreshes, and resume. The
backend’s existing assessment-mode 409 remains unchanged. A server-rendered
DOM test verifies that prior Guided hint text is absent from a resumed
Assessment view.

## Independent review findings (addressed)

An independent review of this diff (pre-merge) found two real regressions,
both fixed in this branch:

- Completed attempt grades disappeared from `CompletionSummary` after a
  browser refresh or resumed session, because `authoritativeGradeByTicket`
  was only ever populated during the live completion round trip and reset to
  empty on every hydration. `TicketSessionProvider.tsx`'s attempt-hydration
  effect now also fetches the attempt for any assignment whose
  `most_recent_attempt.status === 'completed'` and seeds
  `authoritativeGradeByTicket` from its server `grade`, so a completed
  scenario shows its real result on resume instead of a misleading
  "awaiting server grade" state.
- The Assessment-mode hint panel still read "Hints are now available because
  the assessment is complete," left over from before hints were permanently
  suppressed in Assessment mode. Copy corrected to state hints are simply
  not shown during an assessment attempt.

## Known pre-existing scope boundary (not addressed by this hotfix)

The review also confirmed that a sufficiently sophisticated attacker could
bypass `_action_allowed`'s trusted-event check by POSTing a hand-crafted
`remote_desktop.explorer_navigate` event with a matching payload directly to
`/attempts/{id}/actions`, without ever having driven the real simulator to
that state, and then following it with the derived `perform_scenario_step`.
This is not a new gap introduced by this hotfix: every existing scenario
objective (diagnosis, remediation, etc., across all eight seeded scenarios)
already trusts `event.trusted`/`event.success` from the same
payload-matching mechanism rather than a server-side replay of the
TypeScript simulation engine, as already documented in
`docs/SERVICE_DESK_TRUST_BOUNDARY.md`. Closing it for real would mean
porting `evaluate-objectives.ts`'s deterministic replay to the Python
backend (or requiring mentor sign-off before a completion counts toward
progression) — a substantial, already-tracked P0 scope gap, not something a
narrowly-scoped grading hotfix should absorb. This hotfix does not make that
boundary any wider than it already was for every other objective category.

## Explicitly out of scope

- Mail/Company Chat requester-name cosmetic issue.
- Map Network Drive Escape-key handling.
- Initial Remote Desktop ticket context.

None were modified by this hotfix.
