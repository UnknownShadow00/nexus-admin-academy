# Archived documentation

These documents are historical implementation, audit, QA, and launch records.
They are retained for context but do **not** describe the current Nexus
production state. Current documentation lives in `docs/` and the repository
root.

## Layout

| Folder | Contents |
|---|---|
| `reviews/` | The 2026-07-23 full project review set and its 19-phase per-phase reports (`phase-reports/`). |
| `launch-readiness/` | Completed pre-launch hardening and launch-readiness reports. |
| `phases/` | Completed phase upgrade plans and phase audits. |
| `question-bank/` | Completed question-bank / imported-content audit and research reports, including the point-in-time `QUESTION_BANK_AUDIT.md` prose snapshot, `imported_question_quiz_audit.json`, and the legacy `SERVICE_DESK_TICKET_MIGRATION_MAP.md` (Phase 5 decision record — no ticket data was ever migrated). |
| `visual-qa/` | Completed Weeks 1–4 visual QA reports and their screenshots. |
| `production-incidents/` | Point-in-time production-state and drift-fix records for resolved incidents, including `SERVICE_DESK_P0_GRADING_HOTFIX.md` (P0 grading defects — resolved in the shipped `service_desk` grading code). |

The machine-readable audit snapshots `docs/question_bank_audit.json` and
`docs/editorial_review_worklist.json` are **not archived** — they are
regenerable outputs of `backend/scripts/audit_question_bank.py` and
`backend/scripts/build_editorial_review_worklist.py`, are `.gitignore`d, and
should be regenerated on demand rather than committed.
