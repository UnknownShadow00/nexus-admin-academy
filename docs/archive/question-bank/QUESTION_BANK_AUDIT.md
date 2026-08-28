# Question Bank Audit

Generated: 2026-08-08T08:27:46.382693+00:00

Read-only audit run through the shared question validation service (`backend/app/services/question_validation.py`). No question data was modified. No student names, attempts, or other private data are included.

## Totals

- Total questions: 966
- Single-choice: 780
- Multi-select: 186

## Classification

| Classification | Count |
|---|---:|
| Already valid | 966 |
| Safe automatic cleanup | 0 |
| Requires human answer-key review | 0 |
| Should be unpublished temporarily | 0 |

## By source type

| Source | Count |
|---|---:|
| examcompass | 777 |
| seed | 189 |

## Required vs optional content

- Required quizzes: 196 questions
- Optional/practice quizzes: 770 questions

## Specific issue counts

- Select-N text/answer-count mismatches: 0
- Questions with blank options: 0
- Questions with duplicate option text: 0
- Questions with invalid answer references: 0
- Questions missing an explanation: 397
- Exact normalized duplicate question groups: 0
- Duplicate groups within the same quiz: 0
- Questions with malformed HTML entities: 0
- Questions with imported numbering prefixes: 0
- Quizzes with zero questions: 0
- Active quizzes disconnected from curriculum/practice/assignments: 65
- Flashcards pointing at multi-select questions (pre-fix render bug exposure): 1

## Findings requiring attention

| Question ID | Quiz | Status | Source | Classification | Issues |
|---:|---|---|---|---|---|
