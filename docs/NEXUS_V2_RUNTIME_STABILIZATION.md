# Nexus V2 runtime stabilization operations note

This branch adds durable V2 assessment attempts and grading-job leases. It does
not enable V2, deploy code, or migrate any production database.

## Independent audit reproduction

| Issue | Classification before implementation | Evidence / outcome |
| --- | --- | --- |
| A — randomized GET/submit mismatch | CONFIRMED | Submission selected the constrained bank again. The server now stores one ordered selection per attempt; a 20-cycle real Module Quiz test scores the displayed correct answers at 100% every time. |
| B — Explain resolution did not complete progress | CONFIRMED | Resolved grades did not write back to V2 progress. One idempotent reconciliation contract now handles AI and mentor pass/fail results and advances Continue. |
| C — forgeable progress endpoint | CONFIRMED | The frontend did not use the generic mutation endpoint, which accepted arbitrary roll-up state. The endpoint was removed. |
| D — legacy gates block V2 engine work | ALREADY FIXED | Exact V2 lab relationships and server-created V2 Service Desk assignments already bypassed legacy gates. Boundary tests now prove valid V2-only access and rejection outside that context; legacy gates remain intact. |
| E — completion regresses after retry | CONFIRMED | The roll-up stored the latest result as mastery. Passing completion is now monotonic while the latest failed result remains separately visible. |
| F — ambiguous short answers score zero | CONFIRMED | `needs_review` was converted to an incorrect answer. Ambiguous responses now use the existing durable grading queue and finalize the attempt only after resolution. |
| G — grading jobs strand | CONFIRMED | `processing` had no lease or recovery schedule. Claims now have timestamps/tokens, stale work is reclaimed, and repository systemd artifacts schedule the worker. |
| H — attempt history in mutable JSON | CONFIRMED | Quiz history lived in `V2ModuleActivity.detail`. Revision 0068 moves selection and response history to relational attempt tables; the activity table remains a roll-up. |
| I — V2 bypasses editorial gates | CONFIRMED | V2 assessment selection did not enforce the quiz visibility contract. It now requires active, published, editorially validated banks with validated answer keys and excludes flagged questions. |

No Module 16–18 content or curriculum package/archive/intake changes are part
of this sprint.

## Student visibility contract

- A V2 lesson is student-visible only when its status is `ready` or
  `published`. `draft` is never served by the student entry, module, or lesson
  APIs.
- A V2 quiz uses `student_visible_quiz_filters()`: the quiz must be
  `published`, active, editorially `validated`, and have validated answer
  keys. Questions flagged for review are excluded.
- An exact-hash entry in `content/questions/editorial-approvals.yaml` promotes
  that reviewed bank to `published`. The A+ IP Configuration bank has no such
  entry and remains blocked. Curriculum/editorial review must approve the exact
  bank bytes; runtime code must not silently approve it.

## Grading worker timer

Repository examples live in `deploy/systemd/`. Before installation, an
operator must copy the API service's `User`, `Group`, `WorkingDirectory`, and
environment-file path into `nexus-grading-worker.service`. Then validate with:

```bash
systemd-analyze verify deploy/systemd/nexus-grading-worker.service deploy/systemd/nexus-grading-worker.timer
```

Installation and enablement are deliberately not performed by development.
During a future approved deployment, copy the reviewed files to
`/etc/systemd/system/`, run `systemctl daemon-reload`, and enable the timer.
The timer's `Persistent=true` catches a missed interval after restart. Jobs in
`processing` whose ten-minute lease expires are reclaimed, and a claim token
prevents a late worker from recording a duplicate provider result.

## Migration rehearsal

Revision `0068_v2_runtime_stabilization` is additive. The automated migration
tests exercise both a fresh database through `head` and a realistic database
at `0067_v2_question_objectives` upgraded to the new head. Production migration
must use the normal backup and guarded deployment procedure in `DEPLOYMENT.md`.
