# Question Bank Audit

Generated: 2026-07-25T02:08:52.215156+00:00

Read-only audit run through the shared question validation service (`backend/app/services/question_validation.py`). No question data was modified. No student names, attempts, or other private data are included.

## Totals

- Total questions: 967
- Single-choice: 781
- Multi-select: 186

## Classification

| Classification | Count |
|---|---:|
| Already valid | 966 |
| Safe automatic cleanup | 0 |
| Requires human answer-key review | 1 |
| Should be unpublished temporarily | 0 |

## By source type

| Source | Count |
|---|---:|
| examcompass | 778 |
| seed | 189 |

## Required vs optional content

- Required quizzes: 196 questions
- Optional/practice quizzes: 771 questions

## Specific issue counts

- Select-N text/answer-count mismatches: 1
- Questions with blank options: 0
- Questions with duplicate option text: 0
- Questions with invalid answer references: 0
- Questions missing an explanation: 634
- Flashcards pointing at multi-select questions (pre-fix render bug exposure): 1

## Findings requiring attention

| Question ID | Quiz | Status | Source | Classification | Issues |
|---:|---|---|---|---|---|
| 648 | Windows OS Troubleshooting Quiz (#39) | published | examcompass | Requires human answer-key review | This question says Select 2, but 1 correct answer(s) are stored. |
