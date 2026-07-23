# My Training architecture and operations

My Training is the canonical guided student flow. It adds a weekly ordering
layer over existing Nexus content; it does not copy videos, quizzes, lessons,
labs, tickets, commands, networking labs, capstones, or student progress.

## Student routes

- `/training` is the weekly dashboard and canonical next-action view.
- `/training/week/:weekNumber` is an available or completed week.
- `/training/content` is the complete A+ video catalog, named **All Course
  Content**.
- `/quizzes` remains the **Quiz Library**.
- `/progress` reports training results and readiness.
- `/study-tracker` redirects to `/training/content` so catalog bookmarks keep
  their original meaning.

The primary navigation is Home, My Training, Practice Library, and Progress.
Learning Path remains a supported deep link and is used by assigned course
lessons. Existing quiz, ticket, lab, command, terminal, and capstone routes are
unchanged.

## Data model

`training_weeks` stores the ordered week title, description, learning goals,
estimated workload, enabled state, and previous-week gate. A
`training_week_activities` row has a stable ID, activity type, existing content
ID, order, required flag, estimate, and optional soft or hard prerequisite.
The generic content reference is validated in the admin API and by the
curriculum validator because activities point at several existing tables.

Supported types are `lesson`, `video`, `quiz`, `guided_lab`,
`networking_lab`, `support_ticket`, `command_exercise`, `terminal_exercise`,
`review`, and `capstone`. Command and terminal exercises currently lack a
trustworthy per-exercise completion record, so validation rejects them as
required activities. They may be assigned as optional practice.

Migration `0032_my_training` creates 25 enabled weeks (Week 0 and Weeks 1–24)
aligned with the existing Nexus modules and promotion phases. On an upgrade it
also references the content already in the database. On a brand-new database,
`seed_curriculum.py` calls an idempotent synchronizer after normal content
seeding; the synchronizer exits without changing anything when activities
already exist. The fresh-database seed also restores the reviewed 220-1202
catalog and three approved quizzes that carry stable IDs used by the weekly
mapping; it never overwrites an existing record. Every active A+ video is
assigned exactly once by subject.
Migration `0033_finalize_training_quiz_mappings` adds reviewed quiz metadata to
the existing video activities and reduces the required-video load in Weeks 3,
4, 7, 8, and 20. Content remains assigned and reviewable when made optional.
No video, quiz, attempt, or progress row is duplicated or replaced.
Only published, editorially validated quizzes with validated answer keys are
assigned. One real support ticket per populated week is required and additional
tickets are optional. A small set of relevant networking labs is included;
the full lab catalog remains available in Practice Library. Capstones remain
optional weekly references because their existing rank authorization is the
hard gate.

## Server-side completion and next activity

`training_service.py` is the single calculation used by Home, My Training,
week detail, and Progress.

- Video: an existing `video_watches` row exists.
- Quiz: a submitted attempt exists; a required quiz must meet the existing 70%
  pass rule, while an optional quiz is complete after a valid attempt.
- Lesson: an existing student lesson note exists.
- Guided lab: the newest existing lab run is submitted or verified.
- Networking lab: the newest existing CLI-lab attempt has `completed_at`.
- Support ticket: the newest existing submission has been graded server-side
  and is pending review, in review, or passed. Instructor verification remains
  required for XP, mastery, and rank credit, but cannot indefinitely block the
  weekly learning path.
- Capstone: the existing run is submitted/reviewed/passed and the existing
  rank authorization still controls access.
- Review: all earlier required activities in that week are complete.

The current week is the first enabled, unlocked week with incomplete required
work. Continue Training chooses its first incomplete required activity by
display order. Optional activities never replace an incomplete required next
action and never block the next week. Completed weeks stay available. A locked
week returns HTTP 403 without its activity metadata.

## Progress calculations

- **Weekly completion** = completed required activities in that week / required
  activities in that week.
- **Overall training completion** = completed distinct required weekly
  activities / all distinct required activities across enabled weeks.
- **Video completion** = distinct assigned videos watched / distinct assigned
  videos.
- **Quiz completion** = distinct assigned quizzes complete / distinct assigned
  quizzes. Average quiz score is the mean best percentage for attempted
  assigned quizzes. A quiz linked from several video rows is counted once by
  quiz ID, while its best score and review state appear consistently beside
  every linked video.
- **Practice completion** = completed required labs, tickets, command/terminal
  exercises, and capstones / required assigned practice.
- **Rank progress** remains the existing promotion-gate calculation; it is not
  combined with overall training percentage.

## Admin workflow

Open **Learning Content → Weekly Training** (`/admin/training`). Administrators
can create, enable/disable, edit, and reorder weeks; add an existing content
reference; remove or reorder activities; set required/optional; configure a
soft or hard prerequisite; select the approved quiz and mapping basis for a
video; preview a week; and run reference validation.
Referenced IDs are deliberately visible to administrators and are never shown
as student-facing labels.

Before publishing a curriculum change:

1. Confirm the referenced record in its existing content manager.
2. Add it to the intended week and choose required/optional deliberately.
3. Put learning and approved quizzes before related practice.
4. Run the Weekly Training validation panel. Broken, disabled, hidden quiz, and
   untracked-required references, duplicate videos, mapping gaps, and hard
   prerequisite cycles must be fixed before deployment.
5. Preview with both a new student and an appropriately ranked student.

## Video-to-quiz mappings and health checks

Every active video activity records `quiz_id`, `quiz_mapping_basis`,
`quiz_mapping_confidence`, and review evidence in `metadata_json`. The accepted
bases are `exact`, `topic_group`, and `week_fallback`. The quiz must remain
published, active, editorially validated, and answer-key validated. The
frontend never guesses from titles; the legacy title relationship is only a
temporary compatibility fallback while migration 0033 is being applied.

Run the operational validator from `backend/`:

```bash
PYTHONPATH=. .venv/bin/python scripts/validate_training_curriculum.py
PYTHONPATH=. .venv/bin/python scripts/validate_training_curriculum.py --markdown
```

It fails on invalid references, missing/disabled mappings, duplicate active
video assignments, empty completion paths, required untracked work, required
work that hard-depends on optional work, or hard-prerequisite cycles. It also
reports distinct mapping counts and required workload by week. The reviewed
137-row mapping and workload snapshot is in
`docs/MY_TRAINING_QUIZ_MAPPING.md`.

## Deployment and rollback

Follow `docs/DEPLOYMENT.md`. Back up the application, database, and uploads,
verify database integrity, then apply `alembic upgrade head`. Do not run either
seed command for this migration and do not modify production progress records.
Migration 0033 changes only weekly activity metadata and required flags. Its
downgrade removes those mapping keys and restores the earlier required flags;
historical migrations remain intact. If authentication, progress, permissions,
migration, health, or frontend deployment fails, use the documented rollback
procedure and verified pre-deployment backup.

The Service Desk Lab is not part of this architecture. A future implementation
may be referenced by an additional activity type only after its own design,
authorization, completion tracking, migration, and deployment review.
