# Weeks 1-4 Visual QA — PR #23 Release Candidate

Date: 2026-08-16, updated 2026-08-17
RC commit: `54cb22f773889c8938db8fd8f6395c450cbf4af1` (initial QA pass) →
see "Fix verification" below for the follow-up commit that resolves Finding 1.
Scope: Student experience for Weeks 1-4 (This Week page, lessons, quizzes,
structured labs, CLI practice, Apply/Service Desk cards), Today, Progress.
Viewports: Desktop 1440×1000, Mobile 375×812.
Method: real-browser Playwright pass against an isolated local stack
(throwaway SQLite DB, fresh migrate + seed, disposable fixture accounts) via
`scripts/e2e/start_local_stack.sh`. No production system touched. No merge,
no deploy.

## Acceptance result

**PASS, no blockers.** The Weeks 1-4 student experience is clear, internally
consistent, and free of mobile overflow or clipping. The one **IMPORTANT**
finding from the initial pass (structured lab left-column empty space) is now
**FIXED** — see Finding 1. Findings 2-5 remain informational, not defects.

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
| 13 | [`13-hardware-id-exercise.png`](weeks-1-4-visual-qa/13-hardware-id-exercise.png) (before) → [`13-hardware-id-exercise-AFTER-top.png`](weeks-1-4-visual-qa/13-hardware-id-exercise-AFTER-top.png), [`13-hardware-id-exercise-AFTER-scrolled.png`](weeks-1-4-visual-qa/13-hardware-id-exercise-AFTER-scrolled.png) (after) | **FIXED** (see Finding 1) |
| 14 | [`14-question-answer-ui.png`](weeks-1-4-visual-qa/14-question-answer-ui.png) | PASS |
| 15 | [`15-hardware-id-failing-state.png`](weeks-1-4-visual-qa/15-hardware-id-failing-state.png) | PASS |
| 16 | *(see note below — no separate retry screen exists)* | N/A |
| 17 | [`17-hardware-id-passing-state.png`](weeks-1-4-visual-qa/17-hardware-id-passing-state.png) | PASS |
| 18 | [`18-week2-apply-card.png`](weeks-1-4-visual-qa/18-week2-apply-card.png) | PASS (see naming note) |

### Week 3

| # | Capture | Result |
| --- | --- | --- |
| 19 | [`19-week3-full-page.png`](weeks-1-4-visual-qa/19-week3-full-page.png) | PASS |
| 20 | [`20-windows-cli-diagnostics-exercise.png`](weeks-1-4-visual-qa/20-windows-cli-diagnostics-exercise.png) (before) → [`20-windows-cli-diagnostics-exercise-AFTER-top.png`](weeks-1-4-visual-qa/20-windows-cli-diagnostics-exercise-AFTER-top.png), [`20-windows-cli-diagnostics-exercise-AFTER-scrolled.png`](weeks-1-4-visual-qa/20-windows-cli-diagnostics-exercise-AFTER-scrolled.png) (after) | **FIXED** (see Finding 1) |
| 21 | [`21-windows-cli-result-feedback.png`](weeks-1-4-visual-qa/21-windows-cli-result-feedback.png) | PASS |
| 22 | [`22-week3-apply-card.png`](weeks-1-4-visual-qa/22-week3-apply-card.png) | PASS (see naming note) |

### Week 4

| # | Capture | Result |
| --- | --- | --- |
| 23 | [`23-week4-full-page.png`](weeks-1-4-visual-qa/23-week4-full-page.png) | PASS |
| 24 | [`24-prioritize-queue-exercise.png`](weeks-1-4-visual-qa/24-prioritize-queue-exercise.png) (before) → [`24-prioritize-queue-exercise-AFTER-top.png`](weeks-1-4-visual-qa/24-prioritize-queue-exercise-AFTER-top.png), [`24-prioritize-queue-exercise-AFTER-scrolled.png`](weeks-1-4-visual-qa/24-prioritize-queue-exercise-AFTER-scrolled.png) (after) | **FIXED** (see Finding 1) |
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

### Finding 1 — FIXED: excessive empty space on structured lab pages (desktop)

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

**Root cause, precisely:** the two-column container (`LabPage.jsx`) is a CSS
grid (`grid gap-6 lg:grid-cols-2`) with the browser default `align-items:
stretch`, so the left `<article>` grid cell was forced to the row's full
height (matching the taller right column) even though the article itself has
no visible background or border — only its child `.panel` cards do. That
means the *first* fix attempted, adding `items-start` to stop the stretch,
changed the DOM/layout metrics (confirmed: left cell height dropped from
matching the right column to its true content height — 378px/398px/300px vs.
1643px/1875px/1683px measured via `getBoundingClientRect()`) but produced
**zero visible pixel difference**, because a non-bordered, non-backgrounded
stretched block renders identically to a shorter block followed by plain
page background. A raw pixel diff of the `items-start`-only screenshot against
the original confirmed this (same 1440×1834 dimensions, near-identical file
size). Fixing the invisible box alone would not have satisfied "confirm no
new empty-space… issue" — documenting this here since it's a case where the
"obvious" grid-alignment cause (per the brief's own suggestion) was real but
insufficient on its own.

**Actual fix applied:** `items-start` on the grid container (still correct
and now a prerequisite — `position: sticky` has no effect on an item that's
already stretched to full row height) plus `self-start lg:sticky lg:top-20`
on the left `<article>`. On desktop, the left Scenario/Task/Hints column now
tracks the viewport as the student scrolls through the longer question list,
instead of being left behind above the fold with dead space beneath it. This
directly targets what a user actually experiences (the column disappearing
off-screen while still-blank space sits under it) rather than only the
underlying DOM metric.

```diff
- <div className="grid gap-6 lg:grid-cols-2">
-   <article className="space-y-4">
+ <div className="grid items-start gap-6 lg:grid-cols-2">
+   <article className="space-y-4 self-start lg:sticky lg:top-20">
```

- `lg:` prefix keeps this scoped to the desktop two-column breakpoint —
  mobile (`<lg`) stays a plain stacked single column with `position: static`,
  confirmed by an explicit assertion (`getComputedStyle(article).position !==
  "sticky"` on mobile).
- No fixed heights were introduced (`top-20` is a scroll offset, not a
  height cap), so nothing clips a lab with more hints/tasks than these three.
- Grading, progression, question content, and `StructuredLabExercise.jsx`
  were not touched. Service Desk was not touched.

**Before/after evidence** (desktop, scrolled ~800px into the question list —
this is where the original gap was most visible):

| Lab | Before (empty space, no scroll benefit) | After (sticky, scrolled) |
| --- | --- | --- |
| Hardware Component Identification | [`13-hardware-id-exercise.png`](weeks-1-4-visual-qa/13-hardware-id-exercise.png) | [`13-hardware-id-exercise-AFTER-scrolled.png`](weeks-1-4-visual-qa/13-hardware-id-exercise-AFTER-scrolled.png) |
| Windows Command-Line Diagnostics | [`20-windows-cli-diagnostics-exercise.png`](weeks-1-4-visual-qa/20-windows-cli-diagnostics-exercise.png) | [`20-windows-cli-diagnostics-exercise-AFTER-scrolled.png`](weeks-1-4-visual-qa/20-windows-cli-diagnostics-exercise-AFTER-scrolled.png) |
| Prioritize the Queue | [`24-prioritize-queue-exercise.png`](weeks-1-4-visual-qa/24-prioritize-queue-exercise.png) | [`24-prioritize-queue-exercise-AFTER-scrolled.png`](weeks-1-4-visual-qa/24-prioritize-queue-exercise-AFTER-scrolled.png) |

Mobile re-check (single-column stack preserved, no overflow, left column not
sticky): [`13-hardware-id-exercise-mobile-AFTER.png`](weeks-1-4-visual-qa/13-hardware-id-exercise-mobile-AFTER.png),
[`20-windows-cli-diagnostics-exercise-mobile-AFTER.png`](weeks-1-4-visual-qa/20-windows-cli-diagnostics-exercise-mobile-AFTER.png),
[`24-prioritize-queue-exercise-mobile-AFTER.png`](weeks-1-4-visual-qa/24-prioritize-queue-exercise-mobile-AFTER.png).

**Verification performed after the fix:**
- Manual `getBoundingClientRect()` measurement on all 3 labs confirms
  `align-items: flex-start` and left-column height « right-column height.
- Desktop viewport screenshots at scroll position 0 and 800px on all 3 labs
  confirm the left column is visible and pinned near the top while scrolling
  through questions, with no dead space left behind it.
- Mobile screenshots on all 3 labs confirm single-column stacking is
  unchanged and `position !== "sticky"` below the `lg` breakpoint.
- No horizontal overflow (`scrollWidth <= clientWidth + 1px`) on any of the
  6 re-captured states.
- `npm run build`, `npm run cli:validate`, `npm run cli:sanity` all pass.
- The committed `frontend/tests/e2e/weeks-1-4-quality.spec.js` suite (5
  tests, including the Hardware ID / Windows CLI / Prioritize the Queue
  structured-exercise checks and the mobile-overflow check) passes unchanged.

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

## Fix verification

See `## Fix round 2 — Finding 1 verification` below for the code change, the
CI run it produced, and the resulting new RC SHA. That section is the
authoritative record of what shipped; the summary numbers below reflect the
fixed state.

## Summary

1. **Desktop result:** PASS — Finding 1 fixed; no remaining blockers or IMPORTANT issues.
2. **Mobile result:** PASS — no horizontal overflow or clipping in any captured screen, before or after the fix.
3. **Week 1 clarity:** Clear/PASS.
4. **Week 2 clarity:** Clear/PASS.
5. **Week 3 clarity:** Clear/PASS.
6. **Week 4 clarity:** Clear/PASS.
7. **Video badge design result:** PASS — compact single-line legend, distinct but
   restrained colors (indigo Job Critical, gray Know It/Awareness), readable at
   both viewports.
8. **Structured lab design result:** PASS — Finding 1 fixed (left info column now
   stays usable via sticky positioning instead of leaving dead space); the
   exercises themselves (real MCQ/checkbox questions, per-question feedback,
   score banner) are solid, not a "fake lab" shell.
9. **CLI flow result:** PASS — CTA → card → terminal launch is smooth on both
   viewports.
10. **Practice → Apply flow result:** PASS — sections are numbered and visually
    distinct; Apply is topically tied to what was just practiced.
11. **Visual blockers:** none.
12. **Important issues:** none remaining — Finding 1 fixed and verified.
13. **Polish issues:** none requiring a fix; Findings 2-5 are informational notes.
14. **Any code changes:** yes — see "Fix round 2" section: `frontend/src/pages/LabPage.jsx`,
    a 2-line CSS/Tailwind class change (`items-start` on the grid container,
    `self-start lg:sticky lg:top-20` on the left column). No grading, content,
    progression, or backend changes; Service Desk untouched.
15. **New RC SHA:** see "Fix round 2" section below.
16. **CI status:** see "Fix round 2" section below.
17. **READY TO MERGE:** see "Fix round 2" section below (not decided in this
    section — filled in once CI finishes).

## Fix round 2 — Finding 1 verification

**Change:** `frontend/src/pages/LabPage.jsx`, two-line Tailwind class change on
the existing two-column grid (`items-start` on the grid container,
`self-start lg:sticky lg:top-20` on the left `<article>`). See Finding 1
above for the diff, rationale, and before/after screenshots.

**Local verification before pushing:**
- `npm run build` — clean.
- `npm run cli:validate`, `npm run cli:sanity` — clean.
- `frontend/tests/e2e/weeks-1-4-quality.spec.js` (5 tests) — all passing
  against the fixed code, run against a fresh isolated local stack.
- Manual re-capture of all 3 structured labs at 1440×1000 (top-of-page and
  scrolled 800px) and 375×812 (full page) — no empty-space regression, no
  overflow, mobile stacking unaffected.

**CI and PR status:** filled in below once the pushed commit's GitHub Actions
run completes.

- Commit: _pending_
- New RC SHA: _pending_
- CI (5-job matrix): _pending_
- Remaining BLOCKER findings: 0
- Remaining IMPORTANT findings: 0 (Finding 1 fixed)
- READY TO MERGE: _pending CI_
