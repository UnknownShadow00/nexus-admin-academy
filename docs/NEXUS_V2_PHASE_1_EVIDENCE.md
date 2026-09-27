# Nexus V2 Phase 1: evidence and mastery contract

## Existing model at the 0073 baseline

`v2_student_resource_activity.completed` and `completed_at` were set by the
student's resource activity request. `v2_curriculum_service.resource_activity`
copied that self report to a `v2_module_activity` row with status `completed`.
`v2_progress_service.module_progress` counted every required resource with a
`completed` activity toward its required-resource denominator. Its module
formula also required every published lesson, every active quick check, a
passed module quiz, the first practical and Service Desk assessment if present,
and every active Explain prompt. A self-reported resource completion could
therefore satisfy one required part of `module_complete`. The formula did not
drive legacy week gates, XP, or the certification mastery ledger.

## New V2-only contract

- `opened_at` means the resource link was opened. For a required non-video
  reference, this satisfies exposure only. It cannot by itself master a module.
- `watched_at` means the learner selected “I watched this” after opening a
  video. It is a self report, not playback verification or proof of learning.
- `completed` and `completed_at` remain intact as historical fields. They are
  never backfilled into `watched_at` and do not satisfy the new V2 resource
  exposure requirement. The API exposes their historical meaning separately.
- Required resource links contribute exposure; optional links do not enter
  the mastery denominator. Inactive resources are excluded.
- Active knowledge assessments require a trusted passed result. Active
  practical and Service Desk assessments require a trusted passed result when
  configured as required. Active Explain prompts continue to require a passed
  grade. Passive lesson completion is progress history, not mastery evidence.
- `v2_evidence_requirements` defines optional or required interaction/apply
  requirements. `v2_evidence_records` stores only evidence recorded by a
  trusted server integration after an attempt is checked. Phase 1 exposes no
  student mutation route for these records. Future interaction and apply
  engines must validate their attempt before calling `record_trusted_evidence`.
- A module is mastered only when all configured required exposure, checks,
  interactions, applications, and Explain prompts are satisfied, and at least
  one trusted non-viewing requirement exists. Mastery is derived on read; no
  client-supplied `mastered` field is accepted.
- A due flashcard review is a separate `review_due` flag. It does not revoke
  earned mastery.

The public module status is `not_started`, `in_progress`, `watched`,
`check_required`, `passed`, or `mastered`. `optional` and `locked` are supported
as presentation labels, not stored mastery states. `next_action` is derived
from the first missing required evidence. Raw V2 activity rows and historical
attempts are retained for audit.

`ModuleAssessment.pass_percent` stays configurable with its existing 70%
database default. Phase 1 does not rewrite published assessment meaning or
legacy quiz thresholds. New grouped V2 checkpoints should author 80%
explicitly in their content manifest during the curriculum phase.

Migration 0074 adds one nullable timestamp and two V2-only tables. It changes
no student, legacy week, video watch, ticket, quiz attempt, XP, or existing V2
row. Downgrade removes the new tables and timestamp, so a rollback after new
V2 evidence is written must first preserve those records separately.

Deleting an authored requirement cascades to its evidence records. This is
intentional while V2 requirements are unpublished pilot content: a retired
requirement cannot continue to count toward mastery. Preserve the requirement
and its records before deletion if its attempt history needs an audit trail.
Deleting a student also removes that student's evidence records through the
explicit student-owned data cleanup.
