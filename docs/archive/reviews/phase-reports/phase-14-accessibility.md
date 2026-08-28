# Phase 14 — Accessibility & Responsive Design

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** LIVE DOM audit as temp student at **1440×1000** and **375×812** across Home, My
Training, Progress, All Course Content, plus a keyboard focus walk. (Structural audit — no axe-core
in env; color-contrast was spot-checked visually, not formally measured.)

## Strong results (measured)
| Check | Mobile (375) | Desktop (1440) |
|---|---|---|
| Horizontal overflow | **0 px on every page** | 0 px |
| Unlabeled inputs | **0** | 0 |
| Buttons/links w/o accessible name | **0** | 0 |
| `<h1>` per page | **exactly 1** | exactly 1 |
| Images without alt | 0 (icons are inline SVG) | 0 |

- **Keyboard navigation works with visible focus:** tabbing Home hit Start Training → each stat
  card → "Show Answer", **all with a visible focus ring** (`focus:ring-2` utilities in
  `styles.css` on `.input-field`, `.btn`, `.btn-danger`, `.btn-secondary`). `any_focus_visible:true`.
- **Dark mode fully supported** — pervasive `dark:` classes + a header theme toggle; both themes
  render cleanly (verified across all screenshots).
- **Mobile navigation** uses a hamburger drawer; content stacks without clipping; sub-tab strips
  scroll horizontally rather than overflowing the body.

## Findings
**A1 — Small touch targets on "All Course Content" (P2, mobile).** The dense video list has **25
interactive elements < 24 px** at 375 px (video "mark watched" circles, job-relevance chips,
inline controls) — below the WCAG 2.5.8 (24×24) minimum and well below the comfortable 44×44.
This is the one page where mobile tapping will be error-prone. *Fix:* enlarge the watch-toggle hit
area (padding/min-size) and chip tap targets; the rest of the app already meets target sizing.

**A2 — No `prefers-reduced-motion` support (P3).** The UI uses `transition-all duration-200`
animations with no reduced-motion media query, so motion-sensitive users can't opt out. *Fix:* add
a global `@media (prefers-reduced-motion: reduce){ *{transition:none!important;animation:none!important} }`.

**A3 — Color contrast not formally measured (info).** No obvious low-contrast text in screenshots
(slate-on-white / light-on-blue), but a formal audit (axe/Lighthouse) should run in CI to confirm,
especially the muted `text-slate-500` secondary text and the blue hero's body copy.

## Not observed (good)
- No off-screen content, no clipped controls at 375 px, no dense unscrollable tables (the wide
  admin roster is desktop-oriented; not part of the student mobile flow).
- Status is not conveyed by color alone — Locked/Required/Optional use **text labels + icons**, not
  just color (verified on My Training / week pages).
- Modals/drawers: the mobile drawer opens/closes; focus behavior looked correct in interaction but
  wasn't exhaustively screen-reader-tested (recommend a manual NVDA/VoiceOver pass pre-cohort).

## Priorities
- P2: A1 touch targets on All Course Content (mobile).
- P3: A2 reduced-motion; A3 add automated contrast checks (axe/Lighthouse) to CI; one manual
  screen-reader pass before the cohort.
- Overall: **accessibility and responsiveness are in good shape** for launch; A1 is the only
  student-facing item worth fixing soon.
