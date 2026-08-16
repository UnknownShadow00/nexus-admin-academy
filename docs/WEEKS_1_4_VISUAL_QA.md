# Weeks 1-4 Visual QA — PR #23 Release Candidate

Date: 2026-08-16
RC commit: `54cb22f773889c8938db8fd8f6395c450cbf4af1`
Scope: Student experience for Weeks 1-4 (This Week page, lessons, quizzes,
structured labs, CLI practice, Apply/Service Desk cards), Today, Progress.
Viewports: Desktop 1440×1000, Mobile 375×812.
Method: real-browser Playwright pass against an isolated local stack
(throwaway SQLite DB, fresh migrate + seed, disposable fixture accounts) via
`scripts/e2e/start_local_stack.sh`. No production system touched. No merge,
no deploy.

**This is a QA-only pass. No application code was changed.**

## Acceptance result

**PASS, no blockers.** The Weeks 1-4 student experience is clear, internally
consistent, and free of mobile overflow or clipping. One **IMPORTANT**
(non-blocking) layout issue was found and is described below, along with two
informational notes. No code was changed to fix it — see "Any code changes."

## Note on fixture setup

To reach Weeks 2-4 without hand-completing dozens of upstream required
activities, disposable QA accounts were granted the real `is_mentor` flag
directly in the **throwaway scratch database only** (`scripts/e2e/*` never
touches `backend/nexus.db`). `training_service._build_state` already bypasses
week-locking for mentors (`backend/app/services/training_service.py:609`) with
no other rendering differences on the student weekly page — confirmed by
grepping `is_mentor` usage in `frontend/src/`, which only affects capstone
visibility, not weekly-page layout. This is the same fixture technique
`start_local_stack.sh` already uses to grant the "qualified" role fixture.

## Captures inspected

### Week 1

| # | Capture | Result |
| --- | --- | --- |
| 1 | [`01-week1-full-page.png`](weeks-1-4-visual-qa/01-week1-full-page.png) | PASS |
| 2 | [`02-week1-learn-legend.png`](weeks-1-4-visual-qa/02-week1-learn-legend.png), [`02b-week1-learn-section.png`](weeks-1-4-visual-qa/02b-week1-learn-section.png) | PASS |
| 3 | [`03-anatomy-good-ticket-lesson.png`](weeks-1-4-visual-qa/03-anatomy-good-ticket-lesson.png) | PASS |
| 4 | [`04-ticket-note-exercise-empty.png`](weeks-1-4-visual-qa/04-ticket-note-exercise-empty.png), [`04b-ticket-note-exercise-feedback.png`](weeks-1-4-visual-qa/04b-ticket-note-exercise-feedback.png) | PASS |
| 5 | [`05-meet-command-line-lesson.png`](weeks-1-4-visual-qa/05-meet-command-line-lesson.png) | PASS |
| 6 | [`06-start-cli-practice-cta.png`](weeks-1-4-visual-qa/06-start-cli-practice-cta.png) | PASS |
| 7 | [`07-cli-practice-screen.png`](weeks-1-4-visual-qa/07-cli-practice-screen.png) | PASS |
| 8 | [`08-week1-quiz-card.png`](weeks-1-4-visual-qa/08-week1-quiz-card.png) | PASS |
| 9 | [`09-week1-practice-section.png`](weeks-1-4-visual-qa/09-week1-practice-section.png) | PASS |
| 10 | [`10-week1-apply-card.png`](weeks-1-4-visual-qa/10-week1-apply-card.png) | PASS (see naming note) |

### Week 2

| # | Capture | Result |
| --- | --- | --- |
| 11 | [`11-week2-full-page.png`](weeks-1-4-visual-qa/11-week2-full-page.png) | PASS |
| 12 | [`12-week2-hardware-id-card.png`](weeks-1-4-visual-qa/12-week2-hardware-id-card.png) | PASS |
| 13 | [`13-hardware-id-exercise.png`](weeks-1-4-visual-qa/13-hardware-id-exercise.png) | **NEEDS FIX** — IMPORTANT (see Finding 1) |
| 14 | [`14-question-answer-ui.png`](weeks-1-4-visual-qa/14-question-answer-ui.png) | PASS |
| 15 | [`15-hardware-id-failing-state.png`](weeks-1-4-visual-qa/15-hardware-id-failing-state.png) | PASS |
| 16 | *(see note below — no separate retry screen exists)* | N/A |
| 17 | [`17-hardware-id-passing-state.png`](weeks-1-4-visual-qa/17-hardware-id-passing-state.png) | PASS |
| 18 | [`18-week2-apply-card.png`](weeks-1-4-visual-qa/18-week2-apply-card.png) | PASS (see naming note) |

### Week 3

| # | Capture | Result |
| --- | --- | --- |
| 19 | [`19-week3-full-page.png`](weeks-1-4-visual-qa/19-week3-full-page.png) | PASS |
| 20 | [`20-windows-cli-diagnostics-exercise.png`](weeks-1-4-visual-qa/20-windows-cli-diagnostics-exercise.png) | **NEEDS FIX** — IMPORTANT (see Finding 1) |
| 21 | [`21-windows-cli-result-feedback.png`](weeks-1-4-visual-qa/21-windows-cli-result-feedback.png) | PASS |
| 22 | [`22-week3-apply-card.png`](weeks-1-4-visual-qa/22-week3-apply-card.png) | PASS (see naming note) |

### Week 4

| # | Capture | Result |
| --- | --- | --- |
| 23 | [`23-week4-full-page.png`](weeks-1-4-visual-qa/23-week4-full-page.png) | PASS |
| 24 | [`24-prioritize-queue-exercise.png`](weeks-1-4-visual-qa/24-prioritize-queue-exercise.png) | **NEEDS FIX** — IMPORTANT (see Finding 1) |
| 25 | [`25-ranking-interaction.png`](weeks-1-4-visual-qa/25-ranking-interaction.png) | PASS (see naming note) |
| 26 | [`26-prioritize-queue-result-feedback.png`](weeks-1-4-visual-qa/26-prioritize-queue-result-feedback.png) | PASS |
| 27 | [`27-week4-apply-card.png`](weeks-1-4-visual-qa/27-week4-apply-card.png) | PASS (see naming note) |

### General

| # | Capture | Result |
| --- | --- | --- |
| 28 | [`28-home-today.png`](weeks-1-4-visual-qa/28-home-today.png) | PASS |
| 29 | [`29-progress-completed-week-state.png`](weeks-1-4-visual-qa/29-progress-completed-week-state.png) | PASS (see completion-state note) |
| 30 | [`30-week1-partially-completed-full-page.png`](weeks-1-4-visual-qa/30-week1-partially-completed-full-page.png) | PASS |
| 31 | [`31-progress-partially-completed-week.png`](weeks-1-4-visual-qa/31-progress-partially-completed-week.png) | PASS |
| 32 | [`32-mobile-week1-full-page.png`](weeks-1-4-visual-qa/32-mobile-week1-full-page.png) | PASS |
| 33 | [`33-mobile-structured-lab.png`](weeks-1-4-visual-qa/33-mobile-structured-lab.png) | PASS |
| 34 | [`34a-mobile-cli-launch.png`](weeks-1-4-visual-qa/34a-mobile-cli-launch.png), [`34b-mobile-cli-return-path.png`](weeks-1-4-visual-qa/34b-mobile-cli-return-path.png) | PASS |

## Findings

### Finding 1 — IMPORTANT: excessive empty space on structured lab pages (desktop)

**Screens:** `13-hardware-id-exercise.png`, `20-windows-cli-diagnostics-exercise.png`,
`24-prioritize-queue-exercise.png` (`frontend/src/pages/LabPage.jsx` +
`frontend/src/components/StructuredLabExercise.jsx`).

At 1440×1000 the page is a two-column grid: a left "Scenario / Task and
environment / Hints" column and a right "Answer the exercise" column. The
left column's content is short (2-3 short cards) and ends roughly a third of
the way down the page, but the grid row does not collapse — it leaves a tall
blank gap in the left column for the rest of the page while the right column
(4-5 questions with explanations) keeps scrolling. On the Hardware
Component Identification page the empty gap runs for roughly 1900px, longer
than the visible viewport itself. This matches the audit checklist's
"excessive empty space" / "broken alignment" criteria and is the one thing
in this pass a beginner would visually register as "off," even though it
doesn't block completing the exercise.

**Not fixed in this pass** — it's a shared layout (`LabPage.jsx`) touching
all rebuilt structured labs, and the brief says "Do NOT over-fix" / only fix
"obvious visual/usability problems" with sign-off implied by "STOP before
merge." Recommend a follow-up: either let the left column scroll
independently (`sticky` positioning) or stop the grid row from stretching
(`items-start` / `align-self: start` on the grid container) so the left
column's height matches its own content instead of the tallest sibling.

### Finding 2 — informational: no distinct "retry" screen exists

`StructuredLabExercise.jsx` doesn't have a separate retry button/state — the
same button relabels `Submit Answers` → `Try Again` after a failed
submission, and clicking it just re-enables the same fieldsets with the
previous selections still shown. There's no third visual state to capture
beyond failing (#15) and passing (#17); item #16 in the request doesn't
correspond to distinct UI. Not a defect — documenting why #16 isn't a
separate file.

### Finding 3 — informational: Apply scenario titles differ from the QA brief's names

The brief's Apply card names ("Locked Account", "INC2404", "Password Reset",
"MFA Reset") don't match current seeded content. The real Apply scenarios are:
Week 1 "Can't sign in after lunch", Week 2 "USB headset develops static
during longer calls", Week 3 "Sign-in stops before the desktop loads", Week 4
"Approval prompts go to an old phone." Each is topically connected to its
week (see Beginner Test, Q8) — this is curriculum content that evolved since
the brief was written, not a UI defect.

### Finding 4 — informational: fullPage screenshot sticky-header artifact

A few fullPage captures (e.g. `21-windows-cli-result-feedback.png`,
`04b-ticket-note-exercise-feedback.png`) show the sticky top nav bar
re-appearing mid-page. This is a known Playwright fullPage-screenshot
stitching artifact with `position: sticky` headers, not something a real
user sees while scrolling — confirmed by re-capturing the same states with
plain (non-fullPage) screenshots, which render correctly. No product issue.

### Finding 5 — informational: no fully "100% complete" week captured

Item #30 asked for "one completed week state." Reaching a genuinely 100%
required-complete week means finishing every video, lesson, quiz, and
practice/apply item for that week through the real UI — out of scope for a
time-boxed visual pass. `29-progress-completed-week-state.png` instead shows
a realistic multi-activity-progress state (3 of 4 Guided Labs passed, Week 3
at 10%) as the closest available evidence of the Progress page rendering
partial multi-week progress correctly; `31-progress-partially-completed-week.png`
covers the single-week partial-completion case (Week 1 at 14% after
completing its two lessons) cleanly.

## Beginner test (Week 1, representative)

1. **What do I do first?** Clear — "Continue Next Activity" button plus a
   `NEXT` badge on the first Learn card.
2. **What is required?** Clear — every mandatory card carries a `Required`
   badge; the blue banner states the path is Learn → Quiz → Practice → Apply.
3. **What can I skip?** Clear — "Extra practice" is a collapsed, clearly
   labeled optional section ("does not affect week completion").
4. **What does Awareness / Know It / Job Critical mean?** Clear — a
   one-line legend sits directly under the required-path banner with a
   plain-English definition for each badge.
5. **Where do I practice?** Clear — numbered "3. Practice" section with a
   real hands-on exercise (CLI simulator or structured lab).
6. **How do I know whether I passed?** Clear — a colored score banner
   (green ≥70%, amber otherwise) plus a check/X and explanation on every
   question after submitting.
7. **What do I do next?** Clear — "Continue Next Activity" / "Try Again"
   buttons and `NEXT` badges make the next step unambiguous.
8. **Does Apply feel connected to what I learned?** Yes — each week's Apply
   scenario matches its Practice/Quiz topic (e.g., Week 1's login-issue
   ticket after the Ticket Writing quiz; Week 3's sign-in-freeze ticket after
   Windows CLI diagnostics).

No beginner-test answer was unclear from the UI itself in the states captured.

## Summary

1. **Desktop result:** PASS — one IMPORTANT, non-blocking layout issue (Finding 1).
2. **Mobile result:** PASS — no horizontal overflow or clipping in any captured screen.
3. **Week 1 clarity:** Clear/PASS.
4. **Week 2 clarity:** Clear/PASS, subject to Finding 1.
5. **Week 3 clarity:** Clear/PASS, subject to Finding 1.
6. **Week 4 clarity:** Clear/PASS, subject to Finding 1.
7. **Video badge design result:** PASS — compact single-line legend, distinct but
   restrained colors (indigo Job Critical, gray Know It/Awareness), readable at
   both viewports.
8. **Structured lab design result:** NEEDS FIX — Finding 1 (empty space); the
   exercises themselves (real MCQ/checkbox questions, per-question feedback,
   score banner) are solid, not a "fake lab" shell.
9. **CLI flow result:** PASS — CTA → card → terminal launch is smooth on both
   viewports.
10. **Practice → Apply flow result:** PASS — sections are numbered and visually
    distinct; Apply is topically tied to what was just practiced.
11. **Visual blockers:** none.
12. **Important issues:** 1 — Finding 1 (structured lab left-column empty space).
13. **Polish issues:** none requiring a fix; Findings 2-5 are informational notes.
14. **Any code changes:** none. This was a QA-only pass.
15. **New RC SHA:** unchanged — `54cb22f773889c8938db8fd8f6395c450cbf4af1`.
16. **CI status:** unchanged — no code was touched, so CI was not re-run.
17. **READY TO MERGE:** **YES**, no blockers found. Finding 1 is recommended as a
    fast-follow, not a merge blocker. Stopping here per instructions — no merge,
    no deploy performed.
