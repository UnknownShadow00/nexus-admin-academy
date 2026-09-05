# Sprint 2 repository isolation — 2026-09-05

Before scenario edits, HEAD was `7b12f94` on
`feature/service-desk-scenario-realism-1`. Both `4991eb1` and `7b12f94`
were verified ancestors. No staged changes existed.

## Classification of pre-existing changes

A — Pilot readiness (preserved, outside this sprint):

- `backend/app/services/v2_curriculum_service.py`: published-ticket availability gate.
- `backend/tests/test_v2_assessment_availability.py`: availability regression test.
- `backend/tests/test_operator_scripts.py`: operator helper tests (untracked).
- `docs/DEPLOYMENT.md`: pilot operations documentation.
- `scripts/predeploy_check.sh`: disk headroom checks.
- `scripts/check_grading_worker_install.py`: installation validator (untracked).
- `scripts/make_cutover_snapshot.sh`: backup helper (untracked).
- `scripts/pilot_status.sh`: status helper (untracked).
- `scripts/v2_pilot_preflight.py`: readiness checks (untracked).

B — Scenario realism: no uncommitted files. Sprint 1 is committed.

C — Accidental/generated: none among the dirty paths.

One additional legitimate change does not fit A/B/C:
`service-desk-app/apps/web/app/layout.tsx` implements OS/theme preference
handling. It is unrelated UI work, not generated content or scenario realism.

## Preservation and recovery

All ten paths were shelved together, including the five untracked files,
using an explicit-path `git stash push -u`. Recovery object:
`9aea8669826b181fcedc3207d74032b02a340f40`, titled
`pre-sprint-2 preserved pilot-readiness and theme work`.
The older failed-release stash was left untouched.

To resume that work later, switch to its intended branch based on `7b12f94`
and apply the stash by this object ID. Do not pop it onto the realism branch
or delete it until recovery is verified. No pilot scripts were executed.

`feature/service-desk-scenario-realism-2` was created from `7b12f94` after
confirming the working tree was clean. No history was rewritten.
