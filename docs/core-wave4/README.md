# Core Wave 4 — Practice and assessment integrity

## Initial reproduction

The pre-Wave 4 legacy flow was reproduced from the learner UI and API contract:

1. `GET /api/quizzes/{quiz_id}` returned the fixed bank and the browser shuffled it.
2. `POST /api/quizzes/{quiz_id}/submit` created the only attempt record after submission.
3. A failed response returned every `correct_answer`, `correct_answers`, option, and explanation.
4. The result page offered immediate `Try Again` against the same fixed bank.
5. A passing retry was accepted by the same credit/progression queries and unlocked required progress.

Refresh rebuilt both question and option order. The draft key was only `quiz_progress_<quizId>`, so it was neither learner- nor attempt-scoped. The jump grid counted an empty multi-select array as answered because it counted keys, even though final submission validation used the selection length.

## Learner contracts

### Practice Check

- Displays `Practice Check` and `Learn from mistakes · does not affect module credit`.
- Provides feedback only after the learner commits an answer.
- Shows the learner's answer text, correct answer text, a key idea, and the linked lesson worked example.
- Allows unlimited repeats and records no assessment attempt or module credit.
- Cannot open a required assessment's exact items as practice.

### Assessment

- Displays `Assessment` and `Counts toward module completion`.
- Starts or resumes a server-owned `QuizAttempt` before answers are accepted.
- Freezes question order, option order, wording, and the answer-key mapping in a server snapshot.
- Saves answers, current position, and an optimistic revision; stale saves receive `409`.
- Scores only on the server and makes duplicate submission of the same attempt idempotent.
- A failed attempt shows score, the learner's answer text, concepts, and an exact lesson link, while withholding the complete key and explanation.
- A passed attempt shows full worked review. Historical review always reads the saved result snapshot.

## Question-bank depth

All currently seeded credit-bearing legacy quizzes draw their entire bank. Their questions have no objective/category tags, so balanced alternate draws cannot be claimed safely.

| Quiz | Bank size | Draw size | Objective/category distribution | Materially distinct retry sets | Safe to reveal full answers before retry? | Chosen policy |
|---|---:|---:|---|---:|---|---|
| Ticketing Systems Quiz | 4 | 4 | Untagged | 1 | No | Withhold exact key until passed |
| Incident Response Quiz | 4 | 4 | Untagged | 1 | No | Withhold exact key until passed |
| Core PC Hardware Troubleshooting Quiz | 19 | 19 | Untagged | 1 | No | Withhold exact key until passed |

## Editorial backlog

- Add objective/category tags and materially comparable alternate items before enabling retry-set answer disclosure.
- Author separate non-credit practice banks for required topics that do not reuse the exact assessment items.
- Add more specific question-to-worked-example mappings where a quiz currently has only a lesson-level link.
