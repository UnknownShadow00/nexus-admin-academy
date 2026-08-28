# Old Ticket System → Service Desk Migration Map

Written during Phase 5 of the Nexus/Service Desk integration (2026-08-01).
Source models read in full: `backend/app/models/ticket.py` (`Ticket`,
`TicketSubmission`), `backend/app/models/evidence.py` (`EvidenceArtifact`).
Destination models: `backend/app/models/service_desk.py`, as extended by
commits 3a56c30 (attempt/event/grade APIs) and 0c8c441/ff2051b (trust
boundary, idempotent XP).

**Local dev database snapshot for scale context only** (`backend/nexus.db`,
2026-08-01 — this is *not* a production count, real counts must be pulled
from the live deployment before any Phase 11 migration work):
`tickets`: 48 rows. `ticket_submissions`: 1 row. `evidence_artifacts`: 1 row.

## Headline recommendation

**Do not physically migrate historical `TicketSubmission` rows into the new
Service Desk tables.** They stay exactly where they are, exactly as they
are, read-only, reachable through the existing (untouched)
`/admin/ticket-review` page. This matches the implementation prompt's rule
("do not remove the old UI until the new system supports the approved
replacement features and migration has been verified") and the source
review's Phase A/D sequencing (stabilize without deleting anything now;
retire the duplicate student UI only after real migration is verified,
later). The table below exists to answer two different questions people
will actually ask, not to justify a data migration:

1. **Capability parity** — which useful *behaviors* of the old system does
   the new one still need to grow, before old submissions/UI are ever
   retired?
2. **Where does old content go, if anything** — for the handful of fields
   that are template/reference content (not per-student history), is there
   a real migration path into the new scenario model?

## Per-student submission data (`TicketSubmission`)

| Old field | New destination | Transformation | Historical migration? | Display-only? | Archivable later? |
|---|---|---|---|---|---|
| `writeup` | **Gap.** No equivalent field exists yet. Recommend a new append-only event (`event_type="closure_summary"`) on `service_desk_attempt_events`, not a new column — fits the existing model, no schema change. | New event type in the attempt-completion flow (frontend-side, when wired). | No — old writeups stay attached to their `TicketSubmission` row. | Old rows: display-only via existing admin ticket-review page. | Yes, once retired. |
| `commands_used` | **Already superseded, better.** New attempts record individual `event_type="command_entered"` events per action, not one text blob. | None needed going forward. | No. | Old rows: display-only. | Yes. |
| `ai_score` / `structure_score` / `technical_score` / `communication_score` | **Product decision needed.** New `ServiceDeskAttemptGrade.overall_score` is a single number; the new TS grading engine (`evaluate-objectives.ts`) is not currently sub-scored on structure/technical/communication axes. `details_json` (already a free JSON column) could hold a breakdown if this multi-axis rubric is still wanted — no schema change required either way, just a product call on whether it's needed. | Only if the product decision says yes: grading-engine work in `service-desk-app`, not a Nexus change. | No. | Old rows: display-only. | Yes. |
| `final_score` | `ServiceDeskAttemptGrade.overall_score` | Direct conceptual equivalent, already built (Phase 1/3). | No. | — | — |
| `ai_feedback` (JSON) | `ServiceDeskAttemptGrade.details_json` | Directly compatible, already a free JSON blob — no schema change. | No. | Old rows: display-only. | Yes. |
| `xp_awarded` / `xp_granted` | `XPLedger` (same table both systems already share — `source_type="service_desk_attempt"` vs the old ticket source type) | Already unified — Phase 3 wired new completions through the same ledger the old system uses. | No — old ledger rows are untouched, already correct. | — | — |
| `status` | `ServiceDeskAttempt.status` (`in_progress`/`completed`/`failed`) | Old `status` is a free string (no CheckConstraint enumerating it) — **verify the actual vocabulary in `ticket_grader.py`/`tickets.py` before assuming any 1:1 mapping**; not done as part of this phase. | No. | Old rows: display-only. | Yes. |
| `submitted_at` / `graded_at` | `ServiceDeskAttempt.started_at`/`completed_at`, `ServiceDeskAttemptGrade.calculated_at` | Direct conceptual equivalents, already built. | No. | — | — |
| `verified_at` / `verified_by` | `ServiceDeskAttemptGrade.mentor_feedback_at`/`mentor_feedback_by` (added in this integration's migration 0036) | Direct conceptual equivalent, already built — mentor sign-off is mentor sign-off. | No. | — | — |
| `duration_minutes` | Derivable from `ServiceDeskAttempt.started_at`/`completed_at` | Not stored separately by design — compute on read if ever needed. | No. | — | — |
| `hints_used` (count) | Derivable: `COUNT(*)` over `service_desk_attempt_events WHERE event_type='hint_requested'` for the attempt | Richer than the old single count — full hint history, not just a tally. | No. | — | — |
| `overridden` / `override_score` | **Gap.** No numeric override field exists on `ServiceDeskAttemptGrade` yet — only free-text `mentor_feedback`. | Would need one more small additive migration (same pattern as 0036: nullable `override_score`, `overridden_by`, `overridden_at`). **Not required for the 5-student pilot** — a mentor can explain a disagreement in free-text feedback for now. Recommended as a Fix-Next item if grade disputes become common. | No. | — | — |
| `evidence_complete` / `before_screenshot_id` / `after_screenshot_id` | **Gap, but cheap to close.** `EvidenceArtifact` is already polymorphic (`submission_type` + `submission_id`, not FK'd to `Ticket`/`TicketSubmission` specifically) — a new `submission_type="service_desk_attempt"` value pointing `submission_id` at `ServiceDeskAttempt.id` needs **zero schema changes**, just a new upload endpoint reusing the existing evidence service. | New router endpoint, when/if evidence upload is wanted for Service Desk attempts. | No. | — | Fix-Next, not required for pilot launch (browser-simulated scenarios reduce the need for screenshot evidence relative to the old text-based tickets). |
| `collaborator_ids` | No equivalent, no current plan. | — | No. | — | Later — not required; the review didn't flag group collaboration as a launch need. |
| `methodology_steps_mentioned` / `methodology_score` | **Superseded, not migrated.** The old AI inferred methodology from free text; the new deterministic engine verifies actual tool/action usage directly (`evaluate-objectives.ts`'s point table), which is a stronger signal for the same underlying goal. | None — different mechanism achieving the same intent. | No. | — | — |
| `admin_reviewed` / `admin_comment` | `ServiceDeskAttemptGrade.mentor_feedback` + presence check (`mentor_feedback is not null`) | Direct equivalent, already built (Phase 1). | No. | — | — |

## Template/reference content (`Ticket`)

The old `Ticket` rows (48 in the local dev snapshot) aren't per-student
history — they're scenario templates: `hints`, `required_checkpoints`,
`required_evidence`, `scoring_anchors`, `model_answer`, `root_cause`,
`root_cause_type`. This is pedagogically valuable prior art, but it's a
**content-authoring task, not a schema-mapping task**: the new system's
equivalent (`ServiceDeskScenarioVersion.definition_json`, a free-form JSON
column designed to hold exactly this) has no real scenario content in it
yet — nothing has been published through the `POST /scenarios/{id}/versions`
endpoint from Phase 1. The actual current scenario content for the new
simulator lives in TypeScript fixtures
(`packages/shared/src/ticket-fixtures.ts`, INC2401–INC2408) in the
`service-desk-app` repo, not in Nexus at all yet.

Recommendation: treat old `Ticket.hints`/`scoring_anchors`/`root_cause` as
source material a content author (human or an assisted authoring pass)
draws from when writing the first real `definition_json` scenario versions
— not something to programmatically copy field-for-field. This is exactly
the "Import the strongest beginner scenarios" work item the source review
already scoped as Fix-Next, not Fix-Now.

## What this phase deliberately does not do

- No code changes. No migration executed. No old row touched.
- No decision made on the multi-axis scoring question — flagged for the
  product owner, not decided unilaterally here.
- Does not implement the two identified "Fix-Next" gaps (score override,
  evidence upload) — noted for prioritization, not built, since neither
  blocks the 5-student pilot per the source review's own checklist.
