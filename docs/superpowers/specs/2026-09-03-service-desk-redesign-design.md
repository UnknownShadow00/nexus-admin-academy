# Nexus V2 Service Desk — Unified Student Workspace + Visual Design Redesign

**Date:** 2026-09-03
**Branch:** `feature/v2-service-desk-redesign` (cut from `fix/v2-beginner-ux` @ `b9cf476`)
**Status:** Design approved; ready for implementation planning.

> This sprint **redesigns and consolidates the student workspace** around the
> existing authoritative Service Desk engine. It does **not** rebuild the engine.
> No deploy, no production migration, no production DB write, no V2 enablement,
> no merge to `main`.

---

## 0. Verified starting state

### Git

- Worktree clean at `b9cf476`.
- Anchor commits confirmed ancestors of HEAD: `7e38ed8`, `9774849` (runtime
  stabilization); `fb327ac`, `00a5dd2`, `5fe8736`, `b9cf476` (beginner UX).
- `feature/v2-service-desk-redesign` created from `b9cf476`. No history rewrite.

### Architecture (as found)

The Service Desk is a **separate Next.js monorepo** at `service-desk-app/`:

| Path | Role |
| --- | --- |
| `service-desk-app/apps/web` | Static-exported Next.js student/admin UI |
| `service-desk-app/apps/api` | Node API (not the grading authority) |
| `service-desk-app/packages/simulation-engine` | Client simulation + objective evaluation mirror |
| `service-desk-app/packages/shared` | Ticket/tool types, fixtures, tool catalog |
| `service-desk-app/packages/ui` | Reusable primitives (`Button`, `Card`, `Modal`, …) |

The Nexus React app (`frontend/`) only redirects into it:
`frontend/src/pages/v2/V2ServiceDeskRedirect.jsx` → `launchV2ServiceDesk()` →
`window.location.assign(res.data.launch_url)`.

**The grading authority is the Nexus FastAPI backend**, not `apps/api`:

- `backend/app/routers/service_desk.py` — trusted-event ledger, transition graph
  (`_action_allowed`), `request_action`, `record_event`, `record_hint`,
  `persist_snapshot`, `complete_attempt`, `_student_scenario_definition`
  redaction.
- `backend/app/services/service_desk_grading.py` — `compute_grade()`, recomputed
  purely from the published `definition_json` + trusted events.
- `backend/app/services/service_desk_objectives.py` — `SCENARIO_OBJECTIVES`
  (process profiles: 5 categories, weights investigation 15 / diagnosis 25 /
  remediation 30 / verification 20 / documentation 10), ordering enforcement
  (investigation+diagnosis before first repair; verification after last repair).
- `backend/app/models/service_desk.py` — append-only `ServiceDeskAttemptEvent`
  (`trusted` flag), immutable published `ServiceDeskScenarioVersion`,
  `ServiceDeskAttemptGrade`.

**All of the above stays authoritative and structurally intact.** New behavior
is additive.

### Discrepancies from the reported "current state" (documented, not regressions)

1. **The live stage rail is a heuristic, not real state.**
   `service-desk-app/apps/web/components/ticket-workflow.ts` computes stages by
   regex over activity-log label strings. Replaced in Group 2.
2. **Escalation is decorative.** `EscalateDialog.tsx` sets a local
   `escalated` overlay; its own copy admits "No specialist queue or backend
   handoff is active in this fixture-only phase." Zero `escalat*` references in
   any backend grading module. Made first-class in Group 3.
3. **Light mode is body-deep only.** `apps/web/app/globals.css` +
   `packages/ui/src/styles.css` flip a handful of `.sd-*` component classes and
   `body`; every component's raw `zinc-*` / `sky-*` utilities do not respond to
   `data-theme`. Fixed in Group 5.
4. **Two note surfaces, two hint surfaces, two workspaces** — confirmed. The
   ticket page (`TicketWorkspace` → `NotesSection`, `HintDialog`) and the
   standalone tool pages (`/tools/[slug]` → `RemoteDesktopTool` with its own
   notes + hints). Consolidated in Groups 1–2.

Beginner-UX guards in `TicketWorkspace.tsx` (first-guided orientation gate,
guided-context preservation, `useNexusReturnTarget`) are intact and are
**preserved** through the refactor.

---

## 1. Goals & non-goals

### Goals

One student ticket workspace where, at every moment, the student can see: what
the user needs, what stage they are in, what evidence is proven, which tools
exist, what to do next, whether to fix or escalate, what needs verification,
what must be documented, whether the ticket is complete, and how to get back to
their Nexus module.

### Non-goals (explicit — do NOT build)

Enterprise CMDB, real SLA engine, assignment queues, many statuses,
change-management workflow, AI requester, LLM grading, ServiceNow clone. No
rebuild of the ten button-driven converted scenarios (`inc2501`–`inc2510`) —
that is a later realism sprint; this workspace must host them without
regression. See §9 Deferred backlog.

### Production safety (hard constraints)

No deploy. No Alembic migration against production. No write to
`backend/nexus.db`. No change to production students or progression. V2 stays
disabled. Not merged to `main`. All escalation grading metadata is **server
code in `service_desk_objectives.py` keyed by `stable_key`** — it needs **no
migration and no new scenario version**, because published `definition_json`
already carries `id`, `priority`, `title`, `description`, `hints`.

---

## 2. Commit groups

Spec order, one branch, one focused commit per group.

| # | Group | Primary surface |
| --- | --- | --- |
| 1 | Unified ticket workspace + embedded tools | `apps/web` |
| 2 | Real workflow rail + evidence + one notes + one hints | `apps/web` + backend read contract |
| 3 | First-class escalation outcome + grading + priority scenarios | backend + engine + `apps/web` |
| 4 | Ticket debrief | backend read contract + `apps/web` |
| 5 | Light/dark semantic token system + typography + buttons + gamification demote | `packages/ui` + `apps/web` |
| 6 | Tests, docs, backlog | all |

Each group must leave the app building and green. Groups 2 and 4 add
**read-only** backend contract fields; Group 3 is the only group that changes
backend grading logic.

---

## GROUP 1 — Unified ticket workspace + embedded tools

### Problem

`TicketWorkspace` (`app/(app)/tickets/[ticketId]/page.tsx`) and the 10
standalone tool pages (`app/(app)/tools/[slug]/page.tsx`) are separate routes.
`ToolsPanel` and `SuggestedTools` navigate away with `router.push` / `<Link>`.
The student loses ticket context to run a tool.

### Design

`TicketWorkspace` becomes the single working surface. It gains an
`activeToolSlug: string | null` state, synced to a `?tool=<slug>` search param
for refresh durability. Verified precondition: the 10 tool components
(`DirectoryTool`, `RemoteDesktopTool`, `CompanyChatTool`,
`AssetManagementTool`, `PcShelfTool`, `ServerRoomTool`, `DocumentationTool`,
`DeviceManagementTool`, `ComputerDeploymentTool`, `ShippingManagerTool`) take
**no route props** — they read everything from `TicketSessionProvider` context
and `useSearchParams`. So they can render inline unchanged.

#### Layout (desktop, direction not pixels)

```
┌───────────────────────────────────────────────────────────────┐
│ TOP CONTEXT BAR                                                │
│  ← Back to [Module]   INC2401 · Finance portal sign-in loop    │
│  [High] [Guided Practice]              Attempts remaining: 2   │
├───────────────────────────────────────────────────────────────┤
│ WORKFLOW RAIL  Understand→Investigate→Diagnose→Fix/Escalate→   │
│                Verify→Document        (Group 2)                 │
├──────────────────────────────────────┬────────────────────────┤
│ CASE / ACTIVE TOOL (left/center)     │ RIGHT RAIL             │
│  ┌─ RequesterCase ────────────────┐  │  Tools launcher       │
│  │ requester message, impact,     │  │  Evidence  (Group 2)  │
│  │ what they tried, device/acct   │  │  Notes     (Group 2)  │
│  └────────────────────────────────┘  │  Hints     (Group 2)  │
│  ┌─ Active tool pane ─────────────┐  │                       │
│  │ <RemoteDesktopTool /> etc.     │  │                       │
│  │ or "no tool open" empty state  │  │                       │
│  └────────────────────────────────┘  │                       │
├──────────────────────────────────────┴────────────────────────┤
│ OUTCOME BAR   [Resolve]  [Escalate]   (eligibility explicit)  │
└───────────────────────────────────────────────────────────────┘
```

#### Top context bar

New `TicketContextBar` component (replaces the ad-hoc header block in
`TicketWorkspace.tsx` lines 64–85 + `TicketDetailHeader`'s duplicated identity
row):

- `← Back to [Module]` — from `useNexusReturnTarget()`. When a module return
  target exists, show its label (`nexusReturnLabel` already yields
  "Back to your module"); **do not** show a generic "Back to queue" as the
  primary back affordance. "Back to queue" moves to a secondary link.
- Ticket ID (mono), title, `PriorityBadge`.
- Mode chip: `Guided Practice` | `Practice` | `Assessment` — mapped from
  `assignment.experience_mode` (`guided`→"Guided Practice",
  `practice`→"Practice", `assessment`→"Assessment").
- Attempts remaining — only when `assignment.maximum_attempts != null`:
  `maximum_attempts - attempt_number + 1`. Hidden otherwise.
- The safe validated return route (`nexus-return.ts` regex + sessionStorage)
  is used unchanged.

#### Tool launcher & active tool pane

- New `WorkspaceToolLauncher` (right rail) — reuses `ToolsPanel`'s catalog
  iteration (`TOOL_CATEGORIES`, `getToolsByCategory`, `TOOL_ICONS`) but its
  buttons call `setActiveTool(slug)` instead of `router.push`. In guided mode,
  show `SuggestedTools`' curated subset first, then "All tools"; in
  practice/assessment show the full catalog.
- New `ActiveToolPane` — renders the mapped tool component for `activeToolSlug`
  (same switch as `app/(app)/tools/[slug]/page.tsx` lines 44–96, extracted to a
  shared `renderTool(slug)` helper in `components/tool-registry.tsx` so both the
  pane and the legacy route use one mapping). Empty state when `null`:
  "Open a tool from the right to start working. Your ticket stays here."
- `SuggestedTools` links (`suggestedToolHref`) change from `<Link href>` to
  buttons calling `setActiveTool`, preserving the query hints
  (`?category=…&ticket=…&contact=…`) by pushing them onto the workspace URL
  alongside `?tool=`.

#### Legacy routes

`app/(app)/tools/[slug]/page.tsx` stays, re-implemented over the shared
`renderTool(slug)` helper, for direct/legacy/bookmarked access. The normal
curriculum flow (launch → `/tickets/[id]`) never leaves the workspace.
`generateStaticParams` unchanged.

#### State & durability requirements

- Ticket ID stays visible whenever a tool is open.
- Switching tools does not lose tool state — `TicketSessionProvider` already
  holds per-domain overlays; inline rendering keeps providers mounted, so this
  is satisfied by construction (an improvement over full navigation).
- Browser refresh restores the correct scenario/attempt and the open tool via
  `?tool=` + existing provider hydration.
- No unrelated ticket can appear — the workspace is scoped to one `ticketId`;
  `RemoteDesktopTool` already resolves its workstation from the ticket/assignment
  context, not a free-typed ID. Add a guard: if a tool's resolved context does
  not match the active ticket, render the tool's own "not part of this ticket"
  empty state rather than a different ticket's data (mirrors the existing
  `TicketWorkspace` "Case unavailable" guard).

#### Responsive (full detail in Group 5 / §19)

- Desktop/tablet: side-by-side as drawn; right rail collapses under the case on
  `< lg`.
- Phone: stacked/tabbed panes — `Case | Tool | Evidence/Notes/Hints` as a
  `Tabs` control (`@service-desk/ui` `Tabs`). Ticket context bar and workflow
  rail stay pinned above the tabs.

### Group 1 acceptance

- Launching a curriculum ticket opens `/tickets/[id]`; every tool is reachable
  without leaving it.
- `?tool=remote-desktop` deep-links and survives refresh.
- `/tools/remote-desktop` still renders standalone.
- First-guided orientation gate, `returnTo`, guided suggested-tools subset all
  still work.

---

## GROUP 2 — Workflow rail, evidence, one notes surface, one hint surface

All four read from **real authoritative attempt state**. No second progression
system, no client grading.

### 2a. Backend read contract (additive, read-only)

New module `backend/app/services/service_desk_workspace_view.py` with:

```python
def process_progress(definition, events) -> dict
```

Returns, computed from the same trusted events + `objective_definition` used by
`compute_grade`, **without disclosing which specific evidence rule is missing**:

```jsonc
{
  "stages": [
    {"key": "understand",  "status": "complete"},   // assigned => complete
    {"key": "investigate", "status": "complete"},
    {"key": "diagnose",    "status": "current"},
    {"key": "fix",         "status": "not_started", "mode": "fix|escalate|either"},
    {"key": "verify",      "status": "not_started"},
    {"key": "document",    "status": "not_started"}
  ],
  "evidence": [
    {"id": "sign-in-loop-reproduced", "label": "Sign-in loop reproduced", "met": true},
    {"id": "profile-storage-cleared", "label": "Profile storage cleared",  "met": false}
  ],
  "documentation_target": "remote_desktop" | "ticket",
  "resolve_blockers": ["verify_first", "add_note", "need_diagnosis_evidence"],
  "escalation": {"available": true, "route": "Identity & Access"} | null
}
```

Rules:

- `status`: `complete` if that category's objectives are all met (reuse
  `_matching_positions` logic); the first non-complete stage is `current`;
  the rest `not_started`. `understand` = complete once the attempt exists
  (student is assigned).
- `fix.mode` comes from the scenario's escalation profile (§Group 3):
  `escalate` if `EscalationProfile.expected`, `fix` if no profile, `either`
  reserved for future.
- `evidence[].label` is authored server-side — see 2b.
- `documentation_target` = which note event the documentation category grades
  (`ticket.add_note` vs `remote_desktop.add_internal_note`), derived from the
  documentation `ProcessCategory`'s objective rule `event_type`.
- `resolve_blockers` — coarse, pre-submission reasons only (see 2e). Never an
  ordered solution.
- Pre-completion this view **never** contains the full ordered "stronger path"
  or unmet-evidence specifics beyond the boolean `met` per already-named
  objective. The named objectives are the scenario's own declared checklist,
  not a hidden key.

Surface it on **`GET /api/service-desk/attempts/{attempt_id}`** as a
`workspace_view` field (alongside the existing `_attempt_dict`), and include a
minimal form in `GET /assignments` so the rail can render before the first
action. Add a thin client wrapper in
`apps/web/lib/nexus-service-desk-client.ts` and expose via
`TicketSessionProvider` (`workspaceViewByTicket`).

### 2b. Evidence labels

Add a `labels` mapping to `service_desk_objectives.py`, keyed by objective `id`,
colocated with the `SCENARIO_OBJECTIVES` definitions (one authored phrase per
`EvidenceObjective.id`, e.g. `"sign-in-loop-reproduced": "Sign-in loop
reproduced"`). A generic fallback derives a title-cased phrase from the id.
This is content, not logic — safe to expand incrementally.

### 2c. Workflow rail (frontend)

- **Delete** `components/ticket-workflow.ts` and its regex heuristic. Its test
  `ticket-workflow.test.ts` is replaced by a rail-render test against
  `workspace_view.stages`.
- New `WorkflowRail` component: renders the 6 stages from
  `workspace_view.stages`. Each stage shows an icon/shape **and** a text status
  ("Completed" / "Current step" / "Not started") — never color alone. Uses
  `aria-current="step"` on the current stage; the list is an `<ol>` with a
  visually-hidden legend.
- Guided/Practice mode: each stage exposes one short authored explanation
  (the copy already in `WORKFLOW_COPY` in the deleted file — **preserve that
  copy**, move it into `WorkflowRail`). Assessment mode: labels only, no
  explanations.
- Stage 4 label is "Fix / Escalate"; when `fix.mode === "escalate"` the
  explanation reads "This ticket is likely not yours to fix directly — decide
  where it should go."

### 2d. Evidence panel (frontend)

- New `EvidencePanel` (right rail): renders `workspace_view.evidence` as a
  read-only list — met items with a check + "Confirmed", unmet items muted +
  "Not yet". Header: "What you've proven". Helper line: "Evidence is recorded
  automatically when a tool action succeeds. You can't mark it yourself."
- No inputs, no buttons. State from server only.

### 2e. One notes surface

- New `ResolutionNotePanel` (right rail) — the single student-authored
  working/resolution documentation field. It is the **only** notes input in the
  workspace.
- On submit, `TicketSessionProvider` dispatches the event named by
  `workspace_view.documentation_target`:
  - `ticket` → existing `addNote` path (`ticket.add_note`, body ≥ 20 chars —
    enforced server-side already at `service_desk.py:88`).
  - `remote_desktop` → existing `remote_desktop.add_internal_note` action
    (currently only reachable inside `RemoteDesktopTool`). Provider gains
    `submitResolutionNote(ticketId, body)` that routes to the right action.
- `RemoteDesktopTool`'s own internal-notes input is **removed** from its UI;
  the action itself stays in the provider. Any notes previously authored
  through it remain in `ticket.notes` history and render in the panel's
  history list (merge `ticket.notes` from both event types — they already land
  in the same overlay).
- Guided/Practice mode: show structured **prompts** (placeholder /
  helper text, not separate fields, not canned answers): "What did the
  requester report? · What did you check? · What did you find? · Likely cause? ·
  Action taken? · How did you verify?". Assessment mode: single free-text
  internal note, no prompts.
- Backend note-quality validation is **not** broadened in this sprint beyond
  the existing ≥20-char rule and the account-scenario
  `meaningful-resolution-note` objectives. Generalized note-quality grading is
  **deferred** and recorded in §9 — the UI scaffolding (prompts) ships now, the
  grading does not, to avoid brittle cross-scenario regex.

### 2f. One hint surface

- Keep a single `HintPanel` (right rail), built from the existing
  `HintDialog.tsx` behavior:
  - Collapsed by default; opens on explicit user action.
  - `Reveal the next hint` / `Reveal another hint (n/total)`; revealed hints
    stay visible; shows which number you're on and whether another exists.
  - Never auto-spent. Reveal calls the existing
    `recordHintReveal` → `POST /attempts/{id}/hints` (server rejects in
    assessment mode — `service_desk.py:958`). In assessment mode the panel
    renders a disabled state with "Hints are not available during an
    assessment."
  - Hint content is the authored `ticket.hints` from the published definition
    — **unchanged**.
- `RemoteDesktopTool`'s separate hint affordance is removed; `HintPanel` is the
  only one. `remote-desktop-learning.ts` hint helpers that feed it stay.

### Group 2 acceptance

- Rail reflects `workspace_view.stages`; kill a tool action → the matching
  stage flips to complete on next fetch.
- Evidence panel shows only server-confirmed items; no client control can add
  one.
- Exactly one notes input exists; it writes the event the server grades for
  that scenario.
- Hints reveal only on explicit click; count persists across reload; assessment
  disables them.

---

## GROUP 3 — First-class escalation outcome + grading

### 3a. Reason taxonomy (fixed enum)

New `backend/app/services/service_desk_escalation.py`:

```python
ESCALATION_REASONS = {
  "permissions-access",        # Permissions / access
  "security-incident",         # Security incident
  "policy-authorization",      # Policy / authorization
  "change-approval-required",  # Change approval required
  "hardware-replacement",      # Hardware replacement
  "unknown-root-cause",        # Unknown root cause
  "other-team-owns-system",    # Other team owns the system
}
```

Frontend mirror in `packages/shared/src` as a const + display-label map.

### 3b. Escalation profile (server-side, per scenario, no migration)

In `service_desk_escalation.py`:

```python
@dataclass(frozen=True)
class EscalationProfile:
    expected: bool
    route: str                                  # "Identity & Access", "Information Security", …
    accepted_reasons: tuple[str, ...]
    required_containment: tuple[EvidenceRule, ...] = ()   # trusted events that must also succeed
    prohibited: tuple[EvidenceRule, ...] = ()             # any success => critical_failure
    rationale: str = ""                          # shown in debrief when escalation WAS right
    no_escalation_rationale: str = ""            # shown when it was NOT

ESCALATION_PROFILES: dict[str, EscalationProfile] = {
    "inc2506": EscalationProfile(
        expected=True,
        route="Identity & Access",
        accepted_reasons=("policy-authorization", "permissions-access"),
        required_containment=(),
        prohibited=(
            _remote("INC2506", "NX-2506", "scenario.apply-safe-remediation"),
        ),
        rationale="Restricted payroll access requires authorization from the data owner / Identity & Access. A help-desk technician cannot grant it.",
        no_escalation_rationale="",
    ),
    "inc2508": EscalationProfile(
        expected=True,
        route="Information Security",
        accepted_reasons=("security-incident",),
        required_containment=(
            _remote("INC2508", "NX-2508", "scenario.apply-safe-remediation"),
        ),
        prohibited=(),
        rationale="Entered credentials on a phishing page is a security incident: contain first, then hand off to Information Security.",
        no_escalation_rationale="",
    ),
}

def escalation_profile(stable_key: str) -> EscalationProfile | None
```

**Why these rules use `remote_desktop.perform_scenario_step` and not
`directory.*`:** both priority scenarios are built by
`_converted_service_desk_ticket()` (`backend/seed.py:948`), whose requester
object has **no `directoryUserId`** and whose `suggestedTools` are
`["remote-desktop", "documentation", "company-chat"]` — there is no Directory
tool in the scenario and `directory.reset_password` is therefore **unreachable**.
Their objective profile is `_converted_process_profile`, whose only vocabulary
is `remote_desktop.perform_scenario_step` (`scenario.inspect-symptom`,
`scenario.collect-evidence`, `scenario.isolate-root-cause`,
`scenario.apply-safe-remediation`, `scenario.verify-original-symptom`) plus
`remote_desktop.add_internal_note`. Escalation grading must therefore be
expressed in *that* vocabulary. This keeps the sprint additive: **no fixture
edits, no new event types, no scenario content rebuild** (the content rebuild is
the deferred realism sprint, §9).

Consequences:

- `inc2506` (must NOT self-serve): the remediation step is **prohibited** —
  taking it is a `critical_failure`. Passing requires investigation + diagnosis
  evidence, then `ticket.escalate`, then the closure note.
- `inc2508` (contain **then** hand off): the remediation step is **required
  containment**, and escalation is additionally required. Containment alone,
  or `ticket.close` without escalating, does not resolve.
- `inc2506`'s authored `verification` objective
  (`scenario.verify-original-symptom`) is meaningless when nothing was fixed —
  which is exactly why §3d waives the verification weight for a resolved
  escalation rather than requiring it.
- "Revoke active sessions" is **not** modeled (no new event vocabulary this
  sprint); recorded in §9.

### 3c. New trusted action `ticket.escalate`

- Schema: `event_type="ticket.escalate"`, `tool="ticket"`, payload
  `{ticketId, reason, routeTeam}`. `_validate_event_shape` gains a branch:
  `reason ∈ ESCALATION_REASONS`, `routeTeam` non-empty string, `ticketId`
  matches the definition id (422 otherwise).
- `_action_allowed` gains, before the generic objective matching:
  ```
  if event_type == "ticket.escalate":
      profile = escalation_profile(key)
      if profile is None or not profile.expected:
          return False   # untrusted-but-audited; can never pass
      if payload["reason"] not in profile.accepted_reasons: return False
      if payload["routeTeam"] != profile.route: return False
      # investigation + diagnosis + documentation prerequisites, same
      # category-prerequisite mechanism as ordered_workflows
      return _prerequisite_categories_met(definition, events, upto={"investigation","diagnosis"})
  ```
  For non-escalation scenarios `ticket.escalate` still records as an untrusted
  event (audit/timeline) but `trusted=False`, so it cannot satisfy grading.
- `request_action` treats `ticket.escalate` for an escalation-profile scenario
  as a `protected_*`-style action: if not trusted, return 409 with
  "Escalation is not available yet — complete your investigation first."

### 3d. `compute_grade` escalation branch

In `service_desk_grading.py`, after loading `definition` / `events`:

```
profile = escalation_profile(scenario.stable_key)
escalated = any(e for e in events if e.trusted and e.success and e.event_type == "ticket.escalate")
```

- **Terminal trigger:** a trusted `ticket.escalate` satisfies the
  "attempt is closeable" precondition exactly like `ticket.close` does today
  (so `AttemptNotClosedError` is not raised when the student escalated).
- **If `profile and profile.expected`:**
  - `prohibited_hit` = any trusted successful event matching a `profile.prohibited`
    rule → `critical_failure = True`, `passed = False`,
    `feedback_summary` = "You applied a change that was not yours to make. This
    ticket required escalation."
  - `containment_met` = every `profile.required_containment` rule has a trusted
    successful event.
  - `resolved` = `escalated and containment_met and not prohibited_hit`.
  - Process points: `investigation`, `diagnosis`, `documentation` scored as
    today. The `remediation` weight (30) is awarded for **correct escalation**
    (`escalated and route/reason valid and containment_met`). `verification`
    weight (20): awarded when `containment_met` (for `inc2508`) or waived to
    "n/a" and redistributed — **decision: waive and treat the 20 as earned when
    `resolved`**, so a correct pure-escalation (`inc2506`) can reach 100.
    (Keeps `POINTS_BY_PRIORITY` math intact.)
  - `feedback_summary` on pass: "You correctly escalated this to
    {route}." + penalty note if any.
- **If `profile is None` (ordinary scenario) and the student escalated:**
  `resolved = False`, `passed = False`,
  `feedback_summary` = "This ticket was within your authority — it did not need
  escalation. Review what a full fix looks like." (No `critical_failure`; it's a
  wrong call, not a safety breach.)
- **If no escalation occurred:** unchanged behavior.

`details_json` gains: `escalated`, `escalation_route`, `escalation_reason`,
`containment_met`, `prohibited_hit`, `escalation_expected`.

### 3e. Frontend escalation UI

- `EscalateDialog.tsx` rewritten: a reason `<select>` (7 taxonomy options with
  descriptions), a short free-text context box (audit only, not graded), and a
  visible **route destination** ("This will be routed to: Information Security")
  from `workspace_view.escalation.route`. Confirm button calls a new provider
  method `escalateTicket(ticketId, {reason, routeTeam})` →
  `POST /attempts/{id}/actions` with `ticket.escalate`.
- On 409, show the server reason inline (never silent) — same pattern as
  `ResolveDialog`'s `closeRejectionMessage`.
- The outcome bar (§Group 1) shows **Resolve** and **Escalate** as two
  first-class terminal actions. Escalate is **not** styled as failure/danger —
  it is a `secondary` action (Group 5 hierarchy), equal weight to Resolve.
  Which one is the "expected" primary is **not** revealed pre-completion (no
  answer key) — both are enabled per their own eligibility.
- Post-escalation the workspace goes to the debrief state (Group 4).

### 3f. Priority scenario intent

- `inc2506` (restricted salary records): correct terminal outcome = escalate,
  reason `policy-authorization` (or `permissions-access`), route "Identity &
  Access". Running `scenario.apply-safe-remediation` = `critical_failure`.
- `inc2508` (phishing credentials): correct = `scenario.apply-safe-remediation`
  (containment) **then** escalate, reason `security-incident`, route
  "Information Security". Containment alone with no escalation → not resolved.
  `ticket.close` without escalation → not resolved.

### 3g. Engine mirror

`packages/simulation-engine/src/evaluate-scenario-objectives.ts` +
`serialize.ts` get the `ticket.escalate` action type and an escalation-aware
`previewCloseGrade` so the client preview (used by `ResolveDialog` /
`EscalateDialog` and the "why not ready" reasons) matches the server. The
client preview is advisory only; the server remains authoritative.

### Group 3 acceptance

- A correct escalation completes `inc2506` and `inc2508` (regression tests).
- `scenario.apply-safe-remediation` on `inc2506` → `critical_failure`, no pass.
- Escalating an ordinary scenario (e.g. `inc2402`) → not resolved, non-punitive
  feedback.
- `ticket.escalate` with a bad reason/route → 409, visible message.
- Non-escalation flows unchanged (existing grading tests still green).

---

## GROUP 4 — Ticket debrief

### 4a. Backend (read-only, post-completion)

`_grade_dict` in `service_desk.py` gains a `debrief` block, computed by a new
`service_desk_workspace_view.build_debrief(definition, events, grade)` — only
returned when `attempt.status != "in_progress"` (so revealing ordering + the
authored path is allowed):

```jsonc
{
  "result": {"passed": true, "score": 88, "attempts_remaining": 1,
             "outcome": "resolved" | "escalated" | "needs_another_try"},
  "categories": [
    {"key": "investigation", "points": 15, "max": 15, "status": "full",
     "explanation": "You reproduced the sign-in loop before changing anything."},
    {"key": "diagnosis", "points": 0, "max": 25, "status": "missed",
     "explanation": "Your network test happened after you changed DNS, so it "
                    "could not count as pre-change investigation evidence."},
    ...
  ],
  "student_note": "…final resolution note text…",
  "note_dimensions": {"cause": true, "action": true, "verification": false},
  "stronger_path": [
    "Reproduce the reported symptom",
    "Check IP configuration",
    "Confirm DNS resolution fails",
    "Set the approved DNS servers",
    "Re-test name resolution",
    "Confirm with the requester and write the closure note"
  ],
  "escalation_feedback": {
    "appropriate": false,
    "text": "No — this was within your access and authority."
  }
}
```

- `categories[].explanation` uses the **ordering** facts already computed in
  `evaluate_objectives` (`first_repair` / `last_repair` positions) to explain
  *why* investigation/diagnosis/verification missed when the objective events
  exist but are mis-ordered. No new grading; it re-narrates existing signals.
- `stronger_path` = the authored category order + objective labels (2b). Only
  present post-completion.
- `note_dimensions` = simple presence heuristic on the student's final note
  (does it contain a cause statement / an action statement / a verification
  statement). Advisory display only — **not** fed back into the score.
- `escalation_feedback` from `EscalationProfile.rationale` /
  `no_escalation_rationale`, or the generic "within your authority" line when
  no profile exists. Answers "Would escalation have been appropriate here?" for
  **every** completed ticket (§14).

### 4b. Frontend

- New `TicketDebrief` component — a workspace state, not a route. Shown by
  `TicketWorkspace` when `attempt.status !== "in_progress"` (from
  `authoritativeGradeByTicket` / attempt fetch). Survives reload (server state).
- Sections: **Result** (passed / needs another try, authoritative score,
  attempts remaining, outcome), **Process** (5 category cards with
  points/status + explanation), **Your documentation** (the student's final
  note + the 3 advisory dimensions), **A stronger troubleshooting path**
  (ordered list; only shown after completion), **Escalation feedback** (the
  yes/no + rationale).
- "Return to [Module]" button (validated `returnTo`) is the primary action.
- No internal implementation details (no rubric internals, no raw event
  payloads, no pre-completion answer key).

### Group 4 acceptance

- After completion the debrief renders in the workspace and survives refresh.
- A mis-ordered pass shows the ordering explanation.
- Escalation feedback appears on every completed ticket, escalation or not.
- Nothing from `debrief` is retrievable while `status == in_progress`.

---

## GROUP 5 — Light/dark design system, typography, buttons, gamification demote

### 5a. Semantic tokens

Define CSS custom properties in `packages/ui/src/styles.css` (`@layer base`)
for both themes:

```
:root, [data-theme='dark'] {
  --sd-surface: …; --sd-surface-raised: …; --sd-surface-muted: …;
  --sd-text: …; --sd-text-muted: …; --sd-border: …;
  --sd-accent: …; --sd-success: …; --sd-warning: …; --sd-danger: …;
  --sd-pending: …; --sd-focus: …;
}
[data-theme='light'] { /* same names, light values */ }
```

Expose as Tailwind utilities via `@theme inline` in
`apps/web/app/globals.css` (`--color-surface: var(--sd-surface)` etc.) so
`bg-surface`, `text-muted`, `border-border`, `ring-focus` work. Dark stays the
default (`html data-theme="dark"`); the existing `themeScript` toggle is kept.

Values: derive dark from the current `zinc-950 / zinc-900 / zinc-800 / zinc-100
/ zinc-400 / sky-400` palette so the dark look barely shifts; pick a light
palette that meets WCAG AA for body text and UI text in both themes (contrast
checked during implementation).

### 5b. Component sweep

Replace raw `zinc-*` / `sky-*` / `bg-black` / `text-white` / `bg-white` in
`apps/web/components/**` and `apps/web/app/**` with token utilities. Priority:
every component touched in Groups 1–4, then the rest of the workspace surface,
then admin (lower priority — admin may keep raw utilities if time-boxed;
recorded in §9 if so). `@service-desk/ui` primitives
(`button/card/modal/input/textarea/badge/tabs/tooltip/panel-frame`) move to
tokens so consumers inherit correct theming; delete the `[data-theme='light']
.sd-*` override block in `styles.css` once primitives use tokens directly.

State must not be color-only anywhere (icons/text labels alongside color) — the
workflow rail, evidence panel, status badges, and outcome eligibility already
carry text in this design; audit during the sweep.

### 5c. Typography

- Remove `Orbitron` (`--font-display`) and `Rajdhani` (`--font-label`) and
  `Share Tech Mono` from `apps/web/app/globals.css` `@theme` and from the
  Google Fonts `<link>` in `apps/web/app/layout.tsx`.
- `--font-display` / `--font-label` → `ui-sans-serif, system-ui, -apple-system,
  "Segoe UI", Roboto, sans-serif`. Keep a monospace token
  (`ui-monospace, "JetBrains Mono", "SF Mono", Menlo, monospace`) for the
  terminal/command surfaces; **drop the JetBrains Mono web font** too and let
  the system mono stack apply — this removes the external Google Fonts
  dependency entirely (the whole `<link rel="stylesheet">` + `fontScript` +
  `preconnect` block goes). §16 compliant: no distributed font files, no
  external font dependency.
- Replace `font-display` / `font-label` utility usages with normal weight/size
  utilities. Raise 10–11px labels (`text-[10px]` / `text-[11px]`) to `text-xs`
  (12px) minimum where they carry meaning (workflow rail help text, evidence
  captions, requester field labels, badges).
- Service Desk keeps a denser, flatter, more "support tool" feel than Nexus —
  smaller radii, tighter spacing, restrained accent use — but shares the token
  vocabulary so the two feel related.

### 5d. Button hierarchy

Consolidate `@service-desk/ui` `Button` to four intents: `primary` (the one
action to do now), `secondary` (valid alternate), `tertiary` (nav / low
priority), `danger` (destructive only). Map current variants:
`primary`→`primary`, `soft`/`light`→`secondary`, `ghost`/`default`→`tertiary`,
add `danger`. Update all call sites. In the outcome bar, **Resolve** and
**Escalate** are both `secondary`-weight terminal actions with explicit
eligibility text; neither is a lone dominating `primary`, and neither is
`danger`. The workspace never shows six equally-loud controls — assignment /
status / hint controls demote to `tertiary`.

### 5e. Gamification demotion

- Remove points total / score HUD / rank / leaderboard entry points from
  `TicketActionBar`, `TicketWorkspace`, and any workspace-level surface.
  `useAttemptScore().previewCloseGrade` stays **only** to drive the Resolve
  "why not ready / what it will score" copy inside `ResolveDialog`; the raw
  running-points display is removed from the working surface.
- `LeaderboardModal`, rank, XP visuals remain available under
  `app/(app)/achievements` and `app/(app)/analytics` — not on the ticket.
- `authoritativeGradeByTicket` is retained (needed by the debrief).
- The full gamification system is **not** removed this sprint (it is not
  tightly coupled to the workspace once the HUD is gone).

### Group 5 acceptance

- Both themes render every major workspace state (queue, workspace, tool open,
  resolve dialog, escalate dialog, debrief) with AA-contrast text and no
  color-only state.
- No `Orbitron` / `Rajdhani` / `Share Tech Mono` / `JetBrains Mono` web font
  request; no `fonts.googleapis.com` `<link>`.
- `Button` has exactly four intents; no workspace view shows more than one
  `primary`.
- No score/leaderboard/rank on the ticket-working surface.

---

## GROUP 6 — Tests, docs, backlog

### Test plan (regression coverage for the redesign)

Frontend (`apps/web`, Vitest + Testing Library; Playwright where a real flow
exists):

1. Ticket opens with correct module return context (`returnTo` → context bar
   label + href).
2. Correct ticket context persists while switching tools (`?tool=` changes,
   ticket ID stable, no refetch of a different ticket).
3. Remote Desktop never silently defaults to an unrelated ticket — mismatched
   context renders the tool's empty state, not another ticket.
4. Workflow rail reflects `workspace_view.stages` (mock the contract; assert
   statuses + `aria-current`).
5. Evidence panel renders only `workspace_view.evidence`; no control mutates
   it.
6. One notes surface: submitting routes to `ticket.add_note` for an
   account scenario and `remote_desktop.add_internal_note` for `inc2401`
   (assert the dispatched action by `documentation_target`).
7. Hints reveal only on explicit click; revealed count persists across a
   simulated reload; assessment mode disables the panel.
8. Resolve unavailable → `resolve_blockers` reasons visible before submit.
9. Resolve works once blockers clear.
10. Escalate unavailable pre-investigation (409 surfaced); available after.
11. Correct escalation completes `inc2506` / `inc2508` (component-level with
    mocked API; backend covers the grade).
12. Inappropriate remediation on `inc2506` does not pass (UI reflects
    `critical_failure` debrief).
13. Authoritative grade shown after completion (score from server, not client).
14. Debrief survives reload (re-mount reads server state).
15. V2 module return works from the debrief.
16. Malicious `returnTo` rejected (`isSafeNexusReturnPath` cases:
    `//evil.com`, `/training/../x`, `javascript:`).
17. Light theme renders queue / workspace / tool-open / resolve / escalate /
    debrief.
18. Dark theme renders the same set.
19. Mobile/tablet: tabbed panes render; context bar + rail stay visible;
    dialogs fit (viewport-sized render assertions).
20. Client-only state cannot manipulate evidence/progression — attempting to
    post a raw `event` for an objective does not flip a stage (contract test:
    untrusted event → stage unchanged).

Backend (`backend/tests`, pytest):

- `test_service_desk_escalation.py` (new): taxonomy validation; `ticket.escalate`
  trusted only after prerequisites + valid reason/route; `inc2506` pass on
  escalate; `inc2506` `critical_failure` on `scenario.apply-safe-remediation`;
  `inc2508` requires containment **and** escalate (containment alone fails,
  escalate alone fails); escalate on `inc2402` → not resolved, not
  `critical_failure`; verification weight waived for a resolved escalation;
  `compute_grade` `details_json` escalation fields.
- `test_service_desk_workspace_view.py` (new): `process_progress` stage
  derivation; evidence `met` flags; `documentation_target` selection;
  `resolve_blockers`; no leakage of unmet-evidence specifics or `stronger_path`
  while `in_progress`; `build_debrief` only post-completion; ordering
  explanation for a mis-ordered pass.
- Extend `test_service_desk_attempts.py` / `test_tickets.py` /
  `test_service_desk_progression.py` as needed; **all existing grading tests
  must stay green** (non-escalation behavior unchanged).
- Engine: `packages/simulation-engine` — `ticket.escalate` in
  `serialize.test.ts` / `evaluate-scenario-objectives.test.ts`;
  `service-desk-quality.test.ts` still green.

### Verification commands (run what the change touches)

```bash
# service-desk-app
cd service-desk-app && pnpm install --frozen-lockfile
pnpm -w lint
pnpm -w typecheck
pnpm -w test
pnpm --filter @service-desk/web build

# backend (see §Disk quota before the full suite)
cd backend
./.venv/bin/python -m compileall -q app tests
DATABASE_URL=sqlite:///"$(mktemp -d)/scratch.db" ./.venv/bin/python -m pytest -q \
  tests/test_service_desk_escalation.py tests/test_service_desk_workspace_view.py \
  tests/test_service_desk_attempts.py tests/test_service_desk_progression.py \
  tests/test_tickets.py tests/test_ticket_hints.py
./.venv/bin/python -m ruff check app tests           # requires requirements-dev.txt
./.venv/bin/python -m alembic current                 # expect no new migration

# frontend (Nexus React app — only if V2 redirect wrapper is touched; likely not)
cd frontend && npm ci && npm run build
```

CI (`.github/workflows/ci.yml` + `service-desk-app` gates ported into it) runs
the equivalent on push/PR. Do not run the full backend suite blindly — see
below.

### Disk quota

Before any full backend suite, inspect and clean **only regenerable test
artifacts**: `backend/.pytest_cache`, `backend/pytest-cache-files-*`,
`backend/pytest-cache-files-lgjhdlkt`, `.ruff_cache`, stray `*.db` under
`$TMPDIR` / repo root created by prior runs, `service-desk-app/test-results`,
`service-desk-app/**/.turbo`, `service-desk-app/**/.next/cache`,
`test-results/`, `artifacts/` scratch. **Never** delete `backend/nexus.db`,
`backend/uploads`, `content-pack/`, `references/`, `deploy/`,
curriculum-approved archives, backups, or any tracked repo file. If the host
still cannot run the full suite, run the focused Service-Desk + escalation +
workspace-view subset and **report that honestly** in the final report.

### Docs

- `service-desk-app/docs/` — new `WORKSPACE.md`: the unified workspace
  architecture, the `workspace_view` / `debrief` read contracts, the escalation
  profile model, which legacy routes remain.
- `docs/PROGRESSION_CONTRACT.md` — add an "Escalation as a terminal outcome"
  subsection (what a pass means when `EscalationProfile.expected`).
- `docs/DEPLOYMENT.md` — note the removed Google Fonts dependency (one less
  external origin) under the frontend/CSP notes if present.
- `tasks/loop-log.md` — mandatory completion entry.
- `TASKS.md` — move the redesign line to done; add the deferred backlog
  pointers.

### §9 Deferred realism backlog (record in `service-desk-app/docs/WORKSPACE.md`)

- **Scenario realism backlog:** `inc2501`–`inc2510` are button-driven
  `_converted_process_profile` scenarios whose `scenario.*` steps effectively
  reveal the answer. This workspace hosts them without regression but they need
  a content rebuild in a later realism sprint (real tool actions instead of
  `scenario.inspect-symptom` / `scenario.apply-safe-remediation` /
  `scenario.verify-original-symptom`).
- **Generalized note-quality grading:** only account scenarios' 
  `meaningful-resolution-note` objective + the ≥20-char rule validate note
  substance. Cause/action/verification grading across all scenarios is deferred
  (avoid brittle cross-scenario regex without per-scenario tests). UI prompts
  ship now; grading does not.
- **`inc2508` containment fidelity:** containment is modeled with the converted
  scenario's only available step (`scenario.apply-safe-remediation`) because
  the fixture has no directory user and no Directory tool. Real containment
  (credential reset + `directory.revoke_sessions` + a real Directory surface)
  needs the fixture rebuilt in the realism sprint, plus one new trusted event
  type.
- **Admin surface theming:** if the token sweep is time-boxed to the student
  workspace, `app/admin/**` may retain raw utilities — record exactly what was
  left.
- **`apps/api`:** untouched; its relationship to the authoritative Nexus
  backend grading is out of scope here.

---

## 3. Files touched (map)

### `service-desk-app/apps/web`

- `app/(app)/tickets/[ticketId]/page.tsx` — unchanged shell; renders new
  `TicketWorkspace`.
- `app/(app)/tools/[slug]/page.tsx` — re-implemented over shared
  `renderTool(slug)`; kept for legacy/direct access.
- `components/TicketWorkspace.tsx` — becomes the unified shell (activeTool
  state, `?tool=` sync, layout, debrief state).
- **New:** `components/TicketContextBar.tsx`, `components/WorkflowRail.tsx`,
  `components/WorkspaceToolLauncher.tsx`, `components/ActiveToolPane.tsx`,
  `components/tool-registry.tsx`, `components/EvidencePanel.tsx`,
  `components/ResolutionNotePanel.tsx`, `components/HintPanel.tsx`,
  `components/OutcomeBar.tsx`, `components/TicketDebrief.tsx`.
- **Rewritten:** `components/EscalateDialog.tsx`, `components/ResolveDialog.tsx`
  (reasons/eligibility), `components/ToolsPanel.tsx` (state not `router.push`),
  `components/SuggestedTools.tsx` (buttons not links).
- **Removed:** `components/ticket-workflow.ts` (+ `.test.ts`),
  `components/NotesSection.tsx` (folded into `ResolutionNotePanel`),
  `components/HintDialog.tsx` (folded into `HintPanel`).
- `components/TicketSessionProvider.tsx` — add `workspaceViewByTicket`,
  `submitResolutionNote`, escalate-with-reason; keep everything else.
- `components/RemoteDesktopTool.tsx` — remove its internal notes input + hint
  affordance; keep all simulation behavior.
- `components/TicketActionBar.tsx` / `TicketDetailHeader.tsx` — folded into
  context bar + outcome bar; remove score HUD.
- `lib/nexus-service-desk-client.ts` — `workspace_view` + `debrief` wrappers.
- `app/layout.tsx` — remove Google Fonts `<link>` / `fontScript` / `preconnect`.
- `app/globals.css` — token `@theme inline` mapping; drop sci-fi font vars.
- Component-wide `zinc-*` → token sweep.

### `service-desk-app/packages`

- `ui/src/styles.css` — semantic token definitions (both themes); drop the
  `[data-theme='light'] .sd-*` override block once primitives use tokens.
- `ui/src/button.tsx` (+ test) — four intents.
- `ui/src/*` primitives — token classes.
- `shared/src` — `ESCALATION_REASONS` const + label map; `ticket.escalate`
  action type; `documentation_target` type on the student scenario definition.
- `simulation-engine/src/evaluate-scenario-objectives.ts`, `serialize.ts`,
  `types.ts` — `ticket.escalate`, escalation-aware `previewCloseGrade`.

### `backend`

- **New:** `app/services/service_desk_escalation.py`,
  `app/services/service_desk_workspace_view.py`.
- `app/routers/service_desk.py` — `_validate_event_shape` (`ticket.escalate`),
  `_action_allowed` (escalate branch + prerequisite helper), `request_action`
  (protected escalate), `_student_scenario_definition` (add
  `documentation_target`, `escalation` presentation), `_attempt_dict` /
  `get_attempt` (`workspace_view`), `_grade_dict` (`debrief`).
- `app/services/service_desk_grading.py` — escalation branch in
  `compute_grade`; `details_json` fields.
- `app/services/service_desk_objectives.py` — `labels` map for evidence.
- `app/schemas/service_desk.py` — `ServiceDeskActionCreate` already generic;
  add a validated escalate payload note if needed.
- **New tests:** `tests/test_service_desk_escalation.py`,
  `tests/test_service_desk_workspace_view.py`; extend existing SD tests.
- **No migration.** `alembic current` unchanged.

### `frontend/` (Nexus React app)

Expected untouched. `V2ServiceDeskRedirect.jsx` / `launchV2ServiceDesk` already
pass `returnTo`; only touch if a contract gap appears.

---

## 4. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Escalation branch changes `compute_grade` for non-escalation scenarios | Branch is gated on `escalation_profile(key) is not None`; full existing grading test suite must stay green; `details_json` additions are non-breaking. |
| `workspace_view` leaks an answer key | Pre-completion: only boolean `met` on already-named objectives + coarse `resolve_blockers`; `stronger_path` and ordering explanations are `build_debrief` only, post-completion. Covered by test 20 + `test_service_desk_workspace_view.py`. |
| Inline tools change tool component behavior | Tool components already take no route props; render them unchanged; legacy route uses the same `renderTool`. |
| Token sweep churn breaks a theme | Dark values derived from current palette (minimal visual shift); both themes asserted in tests 17–18; sweep is mechanical + reviewable. |
| Disk quota on full backend suite | Focused suite first; documented cleanup of regenerable artifacts only; honest reporting if full suite can't run. |
| Two note-event types confuse the single surface | `documentation_target` from the server picks the graded event; both histories merge for display; test 6. |

---

## 5. Out of scope / deferred

See §9 backlog. Also explicitly out: `apps/api` changes, admin Scenario Builder
persistence, the ten converted scenarios' content rebuild, generalized
note-quality grading, session-revocation modeling, V2 enablement, any
production action.
