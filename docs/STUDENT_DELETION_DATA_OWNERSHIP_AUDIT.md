# Student deletion data-ownership audit

## Scope and semantics

`DELETE /api/admin/students/{student_id}` is an administrator-only operation.
It deletes the selected student and every database record owned exclusively by
that student in one transaction. It never deletes shared curriculum, lessons,
quizzes, questions, lab templates, Service Desk scenarios or immutable scenario
versions, or any other student's records.

The executable ownership map is
`backend/app/services/student_deletion.py`. Its `student_owned_row_counts()`
and `remaining_student_owned_rows()` functions are the release-smoke and test
orphan detectors; they are read-only.

## Root-cause finding from the failed release

The preserved failed-release database capture was inspected read-only. It is at
`0047_student_service_desk_progression`, has `integrity_check=ok` and zero
`foreign_key_check` rows. Its two extra `student_lesson_progress` rows both
have `student_id=1`, the real Mentor account; neither references a missing
student. Therefore the reported two rows were not database orphans left by a
successful deletion in the retained forensic database. The capture instead
shows production-smoke contamination under the Mentor identity.

`student_lesson_progress` nevertheless exposed an unsafe deletion design:
the endpoint explicitly cleaned only a legacy subset and relied on SQLite
`ON DELETE CASCADE` for all remaining tables. Cascades are declared for that
table, but SQLite foreign-key enforcement is connection-local. The supported
delete path must itself be complete and must not depend on the pragma state of
an old or externally created connection. The hotfix makes cleanup explicit,
ordered, and transaction-owned; regression tests cover both the populated
student and a forced mid-cleanup failure.

## Ownership inventory

| Table | FK / ownership path | Delete behavior | Supported student deletion |
| --- | --- | --- | --- |
| `students` | account root | delete last | delete selected row only |
| `ai_rate_limits` | `user_id` application ownership, no FK | explicit | delete selected student's limits |
| `capstone_runs` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `cli_lab_attempt` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `evidence_artifacts` | `student_id` application ownership, no FK | explicit | delete metadata for selected student's uploads; shared content is never selected |
| `flashcard_reviews` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `incident_participants` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `lab_runs` | `student_id → students` CASCADE; `vm_assignments` child | explicit after VM assignment | delete |
| `login_streaks` | `student_id` application ownership, no FK | explicit | delete |
| `quiz_assignments` | `student_id → students` CASCADE | explicit + cascade defense | delete assignment, retain quiz |
| `quiz_attempts` | `student_id → students` CASCADE | explicit + cascade defense | delete attempt, retain quiz/questions |
| `rca_submissions` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `service_desk_assignments` | `student_id → students` RESTRICT | explicit | delete selected assignment only |
| `service_desk_attempts` | `student_id → students` RESTRICT | explicit after event/grade children | delete selected attempt/state |
| `service_desk_attempt_events` | `attempt_id → service_desk_attempts` RESTRICT | explicit by selected attempt IDs | delete |
| `service_desk_attempt_grades` | `attempt_id → service_desk_attempts` RESTRICT | explicit by selected attempt IDs | delete grade and mentor feedback attached to it |
| `service_desk_beta_enrollments` | `student_id → students` RESTRICT | explicit | delete |
| `squad_activity` | `student_id` application ownership, no FK | explicit | delete |
| `student_domain_mastery` | `student_id` application ownership, no FK | explicit | delete |
| `student_lesson_notes` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `student_lesson_progress` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `student_methodology_progress` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `student_objective_progress` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `student_onboarding_practice` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `student_roles` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `ticket_submissions` | `student_id → students` CASCADE | explicit + cascade defense | delete legacy compatibility history |
| `video_watches` | `student_id → students` CASCADE | explicit + cascade defense | delete |
| `vm_assignments` | `student_id → students` and `lab_run_id → lab_runs` CASCADE | explicit first | delete |
| `weekly_domain_leads` | `student_id` application ownership, no FK | explicit | delete |
| `xp_ledger` | `student_id → students` CASCADE | explicit + cascade defense | delete |

`evidence_artifacts.storage_key` names a filesystem object and has no database
foreign key. This hotfix removes the student-owned metadata transactionally;
the deployed upload-retention process remains outside SQLite transaction scope
and is not an orphan-row source. `validated_by` and `student_roles.promoted_by`
are reviewer/actor references, not ownership: their `SET NULL` behavior is
preserved and they are not selected for deletion.

No other model or migration table has a direct `student_id`/`user_id` ownership
column or an indirect foreign-key path from a student-owned row at `0047`.
