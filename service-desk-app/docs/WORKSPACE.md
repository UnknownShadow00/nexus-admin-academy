# Student Service Desk Workspace

The student side of the Service Desk is one **unified ticket workspace** built
around the existing authoritative grading engine in the Nexus FastAPI backend.
This document describes how the pieces fit together after the V2 redesign
(`feature/v2-service-desk-redesign`).

> The grading authority is **`backend/app/`**, not `service-desk-app/apps/api`.
> Everything here is additive to that engine - no new progression system, no
> client-side grade.

---

## 1. One workspace, embedded tools

`app/(app)/tickets/[ticketId]/page.tsx` -> `components/TicketWorkspace.tsx` is
the single working surface. It holds:

- **`TicketContextBar`** - module return target (primary), ticket id, priority,
  status, experience-mode chip, attempts remaining. "Back to queue" is a
  secondary link.
- **`WorkflowRail`** - the six authoritative stages (see §2).
- **`WorkspaceToolLauncher`** (right rail) - guided suggested subset + the full
  catalog. Buttons call `setActiveTool(slug)`; they never navigate away.
- **`ActiveToolPane`** - renders the mapped tool inline via
  `components/tool-registry.tsx` `renderTool(slug)`. The open tool is tracked in
  an `activeToolSlug` state that is mirrored to a **`?tool=<slug>`** search
  param, so a browser refresh restores the same tool. A context-mismatch guard
  renders the tool's own empty state rather than another ticket's data.
- **`EvidencePanel` / `ResolutionNotePanel` / `HintPanel`** (right rail) - see
  §2 and §3.
- **`OutcomeBar`** - `Resolve` and `Escalate` as two first-class terminal
  actions (see §3).
- **`TicketDebrief`** - replaces the working surface once the attempt is
  finished (see §4).

On phones the case / active tool / right rail become a `Tabs` control; the
context bar and workflow rail stay pinned above.

### Legacy routes

`app/(app)/tools/[slug]/page.tsx` still renders each tool standalone for direct
or bookmarked access, re-implemented over the same `renderTool(slug)` helper.
`generateStaticParams` is unchanged. The normal curriculum flow (launch ->
`/tickets/[id]`) never leaves the workspace.

---

## 2. Authoritative workspace state - `workspace_view`

`backend/app/services/service_desk_workspace_view.py` `process_progress()`
builds a **read-only** contract from the *same* trusted events and objective
definition that `compute_grade` uses. It is surfaced on:

- `GET /api/service-desk/attempts/{id}` - as `workspace_view`
- `GET /api/service-desk/assignments` - a minimal form per scenario, so the
  rail can render before the first action

```jsonc
{
  "stages": [
    { "key": "understand",  "status": "complete" },
    { "key": "investigate", "status": "current", "needs_more_evidence": true },
    { "key": "diagnose",    "status": "not_started", "needs_more_evidence": true },
    { "key": "fix",         "status": "not_started", "mode": "fix" },
    { "key": "verify",      "status": "not_started" },
    { "key": "document",    "status": "not_started" }
  ],
  "evidence": [
    { "id": "ip-configuration-checked", "label": "IP configuration checked" }
  ],
  "documentation_target": "ticket" | "remote_desktop",
  "escalation": { "available": true }
}
```

`escalation` is **identical for every scenario** and carries no route. There is
no `resolve_blockers` field: it had no consumer and could emit `complete_fix`
on a ticket whose correct outcome was *not* to self-fix.

### Leak safety (do not regress)

While the attempt is **in progress**:

- `evidence[]` contains **only** objectives the trusted ledger has already
  established - id + authored label. An **unmet** objective produces **no
  entry**: not its id, not its label, not a placeholder, not the rule.
- Per-stage progress is a coarse `needs_more_evidence` boolean only.
- `escalation` is `{ "available": true }` for **every** ticket. It never
  carries the destination team, an `expected` flag, or a rationale, so its
  presence cannot tell the student that this is an escalation ticket. The
  student chooses the reason **and** the destination; the server decides
  whether that was right (`compute_grade`).
- `stages[fix].mode` stays the literal `"fix"` for every scenario. **Never**
  wire it to `escalation_profile` / `profile.expected` - that leaks the answer.
  The frontend no longer reads it at all (the dead `mode === "escalate"` branch
  in `WorkflowRail` is gone); it exists only to keep the stage shape stable.
- There is **no** `stronger_path` and **no** ordering narrative.

The authored path, the ordering explanations, and the escalation verdict live
in `build_debrief` and are only returned **after** completion (§4).

Backend tests: `backend/tests/test_service_desk_workspace_view.py`.
Frontend tests: `WorkflowRail.test.tsx`, `WorkspacePanels.test.tsx`.

---

## 3. One notes surface, one hint surface, one escalation dialog

- **`ResolutionNotePanel`** is the only editable note input anywhere in the
  student flow. `ResolveDialog` renders a **read-only** `DocumentationSummary`
  of the latest note ("Documentation recorded" / "Documentation required") and
  closes with that exact note, so Resolve can never create a second, ungraded
  note store. On
  submit the provider's `submitResolutionNote()` dispatches the event named by
  `workspace_view.documentation_target` (`ticket.add_note` or
  `remote_desktop.add_internal_note`). Guided/Practice shows structured prompts
  as placeholder text; Assessment is a plain field. `RemoteDesktopTool` lost its
  own internal-note input but keeps the provider action.
- **`HintPanel`** is the only hint surface. Collapsed until an explicit click,
  reveals one authored hint at a time, disabled in Assessment. `RemoteDesktopTool`
  lost its own hint affordance.
- **`EscalateDialog`** is available on **every** ticket. It offers the fixed
  reason taxonomy **and** a fixed destination-team list, both mirrored from the
  backend in `packages/shared/src/escalation.ts`
  (`ESCALATION_REASONS` / `ESCALATION_ROUTES`), plus an audit-only free-text
  context box. The student picks both; nothing is pre-selected and no team is
  announced. Both selectors use explicit `label htmlFor` + `id` association. It
  gates the confirm button on the authoritative `investigate` + `diagnose`
  stages being complete, and never tells the student escalation is the right
  call before they choose.
- **`ResolveDialog`** shows **no points or pass preview**. The browser cannot
  predict every server branch (escalation profiles, prohibited actions), so a
  predicted score could contradict the authoritative grade. It says only that
  Nexus will check investigation, diagnosis, action, verification, and
  documentation after submission.

---

## 4. Escalation as a terminal outcome

`backend/app/services/service_desk_escalation.py` owns the model:

- **`ESCALATION_REASONS`** - a fixed 7-value taxonomy.
- **`ESCALATION_ROUTES`** - the fixed list of destination teams the student may
  choose from. A plain list of real teams, not routing infrastructure. Mirrored
  in `packages/shared/src/escalation.ts`.
- **`EscalationProfile`** per scenario, keyed by `stable_key`: `expected`,
  `route`, `accepted_reasons`, `required_containment` (trusted events that must
  also succeed), `prohibited` (any success => `critical_failure`), and the
  debrief `rationale`. Because it rides on the already-published
  `definition_json`, it needs **no Alembic migration and no new scenario
  version**.

Flow:

1. `ticket.escalate` is validated at the router boundary (reason in the
   taxonomy, non-empty `routeTeam`, `ticketId`).
2. `_action_allowed` trusts it only for a scenario whose profile `expected` is
   set, only for the declared `route` and an accepted reason, and only after
   investigation and diagnosis are established on the trusted ledger.
   Otherwise it records **untrusted** and `request_action` returns `409`.
3. A trusted `ticket.escalate` terminates the attempt like `ticket.close`.
4. `compute_grade` escalation branch:
   - `prohibited` hit  -> `critical_failure`, cannot pass.
   - `escalation_correct` = correct route + accepted reason + all
     `required_containment` met + no prohibited hit.
   - `resolved` = `escalation_correct` **and** `documentation_complete`. A
     correctly routed hand-off is still not a pass until the closure note is on
     the trusted ledger - Investigate -> Diagnose -> Fix/Escalate -> Verify ->
     **Document** applies to escalations too. When only documentation is
     missing, `escalation_correct` stays `true` and the feedback says the
     closure note is still required.
   - **Process score is normalized across the categories that apply**:
     investigation, diagnosis, documentation, and the remediation weight
     repurposed as the escalation slot. Verification is included **only** when
     the profile requires verifiable containment; otherwise it is
     **not applicable** - never reported as earned work. Full applicable-category
     performance => normalized 100%, and `POINTS_BY_PRIORITY` scaling is
     unchanged.
   - Ordinary scenarios never enter this branch. An ordinary-scenario
     `ticket.escalate` stays untrusted and does not move the score.

Priority scenarios:

| Scenario  | Correct outcome |
| --------- | --------------- |
| `inc2506` (restricted payroll/salary access) | investigate -> diagnose -> recognise the authorization boundary -> **escalate to Identity & Access** -> document. Running `scenario.apply-safe-remediation` is **prohibited**. |
| `inc2508` (phishing credentials) | investigate -> diagnose -> **permitted containment** (`scenario.apply-safe-remediation`) -> **escalate to Information Security** -> document. Containment alone, or escalation alone, does not resolve. |

Backend tests: `backend/tests/test_service_desk_escalation.py`.

---

## 5. Debrief - `build_debrief`

Returned inside the grade payload on `GET /attempts/{id}` and `POST /complete`
**only when the attempt is finished** (`status != "in_progress"`):

```jsonc
{
  "coaching_tier": "full" | "limited",
  "result": { "passed": true, "score": 100, "attempts_remaining": 1,
              "outcome": "resolved" | "escalated" | "needs_another_try" },
  "categories": [
    { "key": "investigation", "label": "Investigation", "points": 15, "max": 15,
      "status": "full" | "partial" | "missed" | "not_applicable",
      "explanation": "..." }
  ],
  "student_note": "...the student's closure note...",
  "note_dimensions": { "cause": true, "action": true, "verification": false },
  "stronger_path": ["Reproduce the reported symptom", "...", "Confirm and document"],
  "escalation_feedback": { "appropriate": false, "text": "No - this was within your authority." }
}
```

### Coaching tiers (do not regress)

`build_debrief` tiers what it reveals so a graded retry cannot become a
transcription exercise:

| Situation | `coaching_tier` | Reveals |
| --- | --- | --- |
| Passed | `full` | Everything below. |
| Failed, **attempts remaining** | `limited` | Score, broad per-category status, the student's own note feedback, generic process coaching. `stronger_path` is `[]` and `escalation_feedback` is `null`. Category explanations are generic - never the missing evidence, the exact fix, or the correct team. |
| Failed, **no attempts left** (`attempts_remaining` 0 or `null`) | `full` | The authored path, the correct route, and the full narrative. There is no further graded attempt to copy them into. |

`TicketDebrief` renders `Start attempt N` (label derived from the server's
`most_recent_attempt.attempt_number`) whenever the attempt failed and the
server still has an attempt left; `TicketSessionProvider.startNextAttempt()`
calls the existing `POST /assignments/{id}/attempts` and clears only that
ticket's attempt-scoped client state. The server owns attempt numbering and the
ceiling - a refusal (403) leaves the debrief on screen with an explanation.

- Category `explanation` re-narrates the ordering signal already computed by
  `evaluate_objectives` ("evidence recorded after a change cannot count as
  pre-change work"). No new grading.
- `note_dimensions` is a presence heuristic on the student's own note; it is
  **advisory display only** and never feeds the score.
- `stronger_path` is the authored category order; escalation scenarios render it
  as investigate -> diagnose -> [contain] -> escalate to `<route>` -> document.
  Empty in the `limited` tier.
- `escalation_feedback` answers "would escalation have been appropriate here?"
  for every completed ticket in the `full` tier, and is `null` in `limited`.

`TicketWorkspace` shows `TicketDebrief` whenever an authoritative grade exists
for the ticket; the provider restores that grade on reload for **failed**
attempts too, so the debrief survives a refresh.

Backend tests: `test_service_desk_workspace_view.py`,
`test_service_desk_escalation.py`.

---

## 6. Design tokens

`packages/ui/src/styles.css` defines `--sd-*` semantic tokens for dark (bare
`:root`) and light (`[data-theme='light']`). `apps/web/app/globals.css` maps
them to Tailwind utilities (`bg-surface`, `text-text`, `border-border`,
`ring-focus`, ...). There is **no external font dependency** - the console uses
the system sans and mono stacks. `Button` has four intents:
`primary` / `secondary` / `tertiary` / `danger`.

The exhaustive raw-utility -> token sweep of every component body and the admin
surface is **not finished** - see the deferred backlog below.

---

## 9. Deferred realism backlog

Update: [the first realism sprint](SCENARIO-REALISM.md) replaces the normal
INC2501, INC2504, INC2505 and INC2509 wizard path with fault-bearing fixtures
and trusted state-derived operations. The catalog preserves historical grading;
the remaining six conversions and further simulation mechanics are listed there.

Intentionally **not** in this sprint. Do not silently expand scope to cover
these:

1. **`inc2501`-`inc2510` scenario-realism rebuild.** These are button-driven
   `_converted_process_profile` scenarios whose `scenario.inspect-symptom` /
   `scenario.apply-safe-remediation` / `scenario.verify-original-symptom` steps
   effectively reveal the answer. This workspace hosts them without regression,
   but they need real tool actions instead of narrated steps.
2. **Generalized note-quality grading.** Only account scenarios'
   `meaningful-resolution-note` objective plus the >=20-char rule validate note
   substance. Cause/action/verification grading across all scenarios is
   deferred - the debrief's `note_dimensions` ship as advisory display only, no
   scoring, to avoid brittle cross-scenario regex.
3. **Historical backlog, superseded by [Realism Sprint 2](SCENARIO-REALISM-SPRINT-2.md).** All ten current converted cases now use replayed state, and INC2508 has credential and session containment. The following records the pre-realism limitation: containment was modelled with the
   converted scenario's only available step because the fixture has no directory
   user and no Directory tool. Real containment (credential reset +
   session/token revocation + a real Directory surface) needs the fixture
   rebuilt plus one new trusted event type.
4. **Directory <-> workstation state coupling.** Directory changes are currently
   invisible to Terminal/RemoteDesktop simulation state.
5. **Remaining admin theme conversion + account-level theme persistence.** The core
   student path is now fully tokenized: primitives (`Card`, `Modal`, `Input`,
   `Select`, `Textarea`, `Tabs`, `Badge`, `PanelFrame`, `Tooltip`,
   `IconButton`), the queue and dashboard chrome, the ticket workspace, the
   embedded tool bodies, notes, hints, Resolve, Escalate and the debrief.
   Guarded by `apps/web/components/light-mode-coverage.test.tsx`.
   Still outstanding: `apps/web/app/admin/**` and account-level persistence.
   The Service Desk first paint now honors an explicit browser-saved choice,
   otherwise the OS preference, with dark as the detection fallback.
   The simulated Windows desktop inside `RemoteDesktopTool` / `workstation`
   intentionally keeps its own light Windows palette in both themes.
6. **Scenario noise / wrong-requester assumptions.** Scenarios currently present
   a clean, correct problem statement; realistic tickets include red herrings
   and mistaken requester self-diagnosis.
7. **Richer escalation scenarios.** Only `inc2506` and `inc2508` have escalation
   profiles. Change-approval, hardware-replacement, and other-team-owns-system
   outcomes have taxonomy values but no scenario yet.
8. **Client-side escalation grade preview.** Resolved by removing the preview
   rather than mirroring the server: `ResolveDialog` no longer renders any
   points/pass prediction, so the browser can no longer contradict
   `compute_grade`. `previewCloseGrade` remains in the provider for the
   attempt-score read model only. Do **not** reintroduce a numeric preview.
9. **Real session/account containment for `inc2508`.** Confirmed deferred in the
   corrective sprint: the generic `scenario.apply-safe-remediation` containment
   event remains temporarily accepted. Real credential/session revocation
   belongs to the scenario-realism sprint (see item 3).
