# Quiz Editorial Review Log

Review started: 2026-07-19 UTC  
Scope: imported quiz banks only. No quizzes or questions were deleted, and no new questions were created.

## Safety disposition

The prior answer-correction review remains the authoritative per-question record for the 120 confirmed answer-key corrections and the swollen-battery safety correction: see [QUIZ_ANSWER_CORRECTIONS.md](QUIZ_ANSWER_CORRECTIONS.md).

This review found 71 active imported quizzes whose answer keys and/or editorial status were not validated. On 2026-07-19 they were moved to the admin-only editorial queue by `backend/scripts/quarantine_unvalidated_quizzes.py`:

- `show_in_practice_library`: disabled for every affected active quiz.
- `editorial_status`: normalized from `unreviewed` to `needs_edit` where necessary.
- Student routes now require both `answer_keys_validated=true` and `editorial_status=validated`, so an accidental published/active flag cannot expose a pending quiz.
- No answer key, question wording, explanation, status, week, or ID was changed by this safety pass.

## Review status by queue priority

| Priority | Purpose | Quiz IDs | Questions | Missing explanations | Reviewer status |
|---:|---|---|---:|---:|---|
| 1 | Weekly practice | 29, 32, 34, 37, 39, 43, 44, 51, 53, 57, 58, 64, 71, 73, 76, 77, 79, 82, 86, 90, 92, 93, 97, 100, 102, 104 | 263 | 210 | Needs validation; hidden from students |
| 2 | Remediation | 31, 41, 52, 56, 59, 60, 63, 68, 69, 72, 85, 89, 91, 94, 98, 101, 103 | 135 | 117 | Needs validation; hidden from students |
| 3 | Cumulative / gate | — | 0 | 0 | All active cumulative and gate questions are already validated with explanations |
| 4 | Certification library | 26, 27, 28, 30, 33, 35, 36, 38, 40, 46, 47, 49, 50, 54, 62, 65, 66, 70, 74, 75, 80, 81, 83, 84, 87, 88, 96, 99 | 298 | 260 | Needs validation; hidden from students |
| 5 | Archived merge sources | 45, 55, 61, 67, 95 | 62 | 28 | Preserved, archived, and not student-visible |

The queue API (`GET /api/admin/quizzes/editorial-queue`) is the live, paginated source of truth for each quiz's title, purpose, recommended week, actual question count, explanations missing, answer-key status, quality score, source, and editorial status.

## Per-question review standard

Each pending question must have a row added below before its quiz is marked validated. A reviewer must independently verify the answer and distractors; answer-letter frequency is not evidence.

| Quiz ID | Question ID | Old answer | New answer | Wording change | Explanation added | Validation source | Reviewer status |
|---:|---:|---|---|---|---|---|---|
| See `QUIZ_ANSWER_CORRECTIONS.md` | See source log | Recorded there | Recorded there | Recorded there | Recorded there | Recorded there | Independently verified |
| Pending queue | Pending queue | Not reviewed | Not reviewed | Not reviewed | Not reviewed | Required before validation | Admin-only / needs edit |

## Validation rules before release

1. Check the technical answer against an authoritative vendor, standards body, or product documentation source and record that source.
2. Verify every distractor is wrong or clearly less appropriate for the stated scenario.
3. Rewrite obsolete Windows 10, Microsoft Entra, or certification-only wording where it does not teach workplace practice.
4. Add a concise rationale for the correct answer and, when useful, the strongest distractor.
5. Mark `answer_keys_validated=true`, `editorial_status=validated`, and then explicitly enable the intended student surface in one reviewed admin update.

No pending imported quiz is marked validated merely because it has an explanation or because an answer is in position A.
