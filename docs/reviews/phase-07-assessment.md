# Phase 7 — Assessment & Progress

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** Source review + **live** quiz flow as temp student (quiz 42, Week 0).

## Security & integrity — verified live (all PASS)
| Check | Result | Evidence |
|---|---|---|
| Correct answers exposed pre-submit? | **No** | `GET /api/quizzes/42` returns only question text + options a–h + `is_multi_select`; no `correct_answer` field. |
| IDOR on quiz review? | **Blocked (403)** | `GET /api/quizzes/42/review/1` (another student) → 403; `ensure_student_access` enforced. |
| IDOR on quiz submit (body `student_id`)? | **Blocked (403)** | `POST /submit {student_id:1,…}` → 403 Forbidden. |
| XP double-award on retake? | **No** | Live: SUBMIT1 `is_first_attempt:true`; SUBMIT2 `xp_awarded:0, "no XP for retakes"`. Source: `xp_awarded = … if is_first_attempt else 0`, awarded via XP ledger (`award_xp` with `source_type/source_id`). |
| Mastery basis | **Best score** | `record_quiz_mastery(..., max(prior_best, score))`; "mastery=best, speed-flags per attempt". |
| Anti-cheat | **Speed-flag** | `is_speed_flagged` when avg < 8s/question. |
| Progress persistence | **Server-side** | `/api/training/progress` reflects state across sessions/refresh. |

The assessment layer is **well-engineered and safe** — no answer leakage, no IDOR, no double XP.
XP is ledgered and therefore auditable.

## Progress model
- **Completion counting is lenient:** a quiz counts as "done" once **attempted**, regardless of
  score. Live proof: submitting **0/4** returned `score:0` and still recorded the attempt (and
  the UI cheerfully said **"Great work!"**). There is **no hard pass threshold** on formative
  quizzes; mastery/gates use best-score thresholds separately.
  - Consequence: "Quizzes Completed" and overall % can include 0%-score quizzes → the percentage
    measures *coverage*, not *mastery*. Not wrong, but should be labeled so students/admins don't
    read it as proficiency.
- **Best vs latest:** attempt list shows every attempt with per-attempt score + `xp_awarded`;
  mastery uses **best**; XP uses **first**. This is internally consistent and documented in code.
- **Wrong-answer learning loop:** `create_cards_for_wrong_answers` seeds FSRS spaced-repetition
  cards → the Home "Daily Review". Good pedagogy.

## Capstone gating / ranks (from live Progress + source)
- Capstones gated by weekly-requirement completion + role gates ("0 of 3 available"; Rank:
  Trainee → Support Technician I). Rank ladder is the six-role progression. Capstone visibility in
  nav is hidden until `has_unlocked_capstones` (Phase 3). Consistent.

## Answers to the plan's questions
- **Understand why complete/incomplete?** Mostly — required/optional badges + progress bars are
  clear; but "complete = attempted" for quizzes can confuse (a failed quiz shows complete).
- **Progress percentages accurate?** Accurate as *coverage*; **not** a proficiency measure (see above).
- **Completion duplicated / XP twice?** **No** — verified live and in source.
- **Quiz mappings sensible?** Topic-level (Phase 5: only 5/137 exact video→quiz maps); acceptable
  for formative use, loose for graded precision.
- **Test understanding vs memorization / useful explanations?** Review shows correct answers post-
  attempt (good), but questions **don't appear to carry rich explanations** ("why") — just the
  correct letter(s). Improvement opportunity.
- **Failed attempts teach improvement?** Yes via FSRS wrong-answer cards + retakes (no XP), and the
  review page. The **"Great work!" message on a 0-score** undercuts this — should reflect the score.
- **Survive refresh / direct nav?** Yes (server-side).
- **Admin overrides transparent/auditable?** XP is ledgered (auditable). But there is **no admin-
  action audit log** surfaced (Phase 4/10), so manual admin changes to students aren't attributable.

## Misleading-metric risks
- Encouraging copy ("Great work!") independent of score.
- Overall % conflates coverage with mastery.
- "Avg Quiz" in the admin roster is an aggregate that hides per-topic weakness (Phase 4).

## Recommended metrics placement (avoid analytics that won't help five students)
- **Home:** current-week % + next action + Daily Review count (as today).
- **My Training:** per-week required completion + best quiz score per week.
- **Progress:** coverage tiles (as today) **plus a distinct "mastery/avg score"** so coverage and
  proficiency are not conflated.
- **Admin dashboard:** per-student current week, % complete, last-active, and a "needs attention"
  flag (stalled / repeated low scores) — the Phase 4 gap.

## Priorities
- P2/UX: distinguish "attempted" from "passed"; fix "Great work!" on low scores; label
  coverage-vs-mastery.
- P3: add answer explanations to quiz review.
- Cross-ref: admin audit log (Phase 10); per-student monitoring (Phase 4).
- **No security fixes required in assessment** — this layer passed every live check.
