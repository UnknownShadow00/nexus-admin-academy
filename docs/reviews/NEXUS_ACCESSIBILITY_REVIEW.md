# Accessibility & Mobile Review

Date: 2026-07-21. Phase 13. Evidence: static analysis of the frontend source
(52 component/page `.jsx` files) via targeted greps for ARIA usage, label
association, focus-indicator styling, heading structure, and image alt text,
plus direct reads of `App.jsx`'s nav (confirmed identical markup for mobile/
desktop), `StudentHome.jsx`, and `TicketFeedback.jsx`. **No browser or
screenshot tool was available in this environment** — pixel-level contrast,
actual tab order, rendered layout at specific breakpoints, and real
screen-reader behavior are marked **Not testable** throughout and would
require a live browser pass before launch.

---

## 1. What was actually measurable from source

| Check | Result | Verdict |
|---|---|---|
| ARIA attributes (`aria-*`, `role=`) | 26 occurrences across only 12 of 52 files | Thin — most interactive components have no explicit ARIA support |
| `<label>` elements vs. styled input fields | 55 labels vs. 113 input-styled fields | Roughly half of inputs likely rely on placeholder text alone, not an associated label (confirmed pattern in `TerminalCommandsPage.jsx`'s search input: `placeholder="Search command name or category..."` with no adjacent `<label>`) |
| Explicit keyboard focus-ring styling (`focus:ring`, `focus-visible`, `focus:outline`) | 5 occurrences total across the whole app | Very thin — most interactive elements rely on browser-default focus indication only, which Tailwind's reset/base styles can sometimes visually suppress |
| `<img>` tags with `alt` text | 0 of 1 | The one `<img>` in the entire codebase (the evidence-screenshot lightbox thumbnail in `TicketFeedback.jsx`) has no `alt` attribute |
| Heading tags (`h1`-`h3`) | 83 across the app | Reasonable volume; correct nesting order (h1→h2→h3 without skipping levels) not verifiable by static grep |
| Skip-to-content link | 0 found | No skip-navigation link exists anywhere — a keyboard user must tab through the full nav on every single page load |

## 2. Direct findings

**Finding ACCESS-001 (P2).** No skip-to-content link exists. Combined with a
9-item nav rendered identically on every page, a keyboard-only user must tab
through the entire navigation bar before reaching page content on every
single navigation — a real, cumulative friction cost across a 24-week
program used daily.

**Finding ACCESS-002 (P2).** Explicit focus-visible styling is rare (5
occurrences app-wide). Whether this matters in practice depends on whether
Tailwind's base reset preserves the browser's native focus ring by default
(it generally does, unless explicitly overridden) — this needs a live
keyboard-only pass to confirm actual visible focus behavior, but the low
number of *explicit* focus styles means the team has not deliberately
designed for keyboard-focus visibility, which is a risk given a mixed-
ability cohort that includes an explicit ADHD/dyslexia consideration in the
review brief.

**Finding ACCESS-003 (P3).** The single evidence-screenshot `<img>` lacks
`alt` text. Low severity given it's one component, but worth a one-line fix
(`alt="Submitted evidence screenshot"` at minimum) since screenshots are a
recurring, central artifact type across tickets and labs.

**Finding ACCESS-004 (P3).** Roughly half of styled input fields across the
app appear to rely on placeholder text without a paired `<label>` (measured
by count, not exhaustively verified per-file). Placeholder-only labeling is
a well-known accessibility anti-pattern (the hint disappears the moment a
user types, and many screen readers don't reliably announce placeholder
text as a label).

## 3. Mobile navigation

**Confirmed in code**: the same `studentNavItems`/`adminNavItems` arrays
render for both desktop and mobile in `App.jsx`, differing only in CSS
layout (`flex flex-col gap-2` for mobile vs. `hidden items-center gap-3
md:flex` for desktop) — there is no separate, reduced mobile nav, which is
consistent (no mobile-only broken links) but means all 9 student nav items
must be scrollable/tappable in a mobile column layout. **Actual rendered
mobile usability (tap target size, scroll behavior, whether the 9-item list
requires excessive scrolling on a small phone) is Not testable without a
live device or browser session.**

## 4. Long-page fatigue and plain-language support

The lesson content itself (Lesson Review) uses short, labeled sections
(ALL-CAPS lead-ins, bullet lists, numbered sequences) that generally favor
ADHD/dyslexic readers over dense prose — this is a genuine strength inherited
from the curriculum-writing style, not a UI-level accessibility feature.
Some dense lessons (Week 12 L3, Week 17 L2) are single long paragraphs under
their headers rather than further broken up — noted already in the Lesson
Review (LESSON-004) and not duplicated in full here.

## 5. Confirmations and empty/loading/error states

`StudentHome.jsx` and `TicketFeedback.jsx` both show deliberate empty-state
copy ("No recent submissions yet," "Submission not found") and explicit
loading text ("Loading feedback...") rather than blank screens — this is a
positive, confirmed-in-code pattern that reduces the "is this broken or
still loading" confusion common in DIY platforms.

## 6. What could not be assessed in this environment

Real contrast ratios, actual tab order across a full page, whether focus
traps exist in any modal/lightbox component, real screen-reader
announcement behavior, and actual responsive behavior at common breakpoints
(360px/768px/1024px) are all **Not testable** without a browser-automation
tool, which was unavailable to both Claude and Codex in this environment
(Codex's sandbox has no network access; no screenshot/browser tool was
provisioned for this session). **Recommend a follow-up pass with an actual
browser/axe-core accessibility scan before broader launch, even though the
current cohort is small and known** — accessibility debt compounds and is
cheaper to fix now, before content/routes multiply further.

## 7. Summary findings

- **ACCESS-001 (P2):** No skip-to-content link.
- **ACCESS-002 (P2):** Minimal deliberate keyboard-focus-visibility styling.
- **ACCESS-003 (P3):** Missing `alt` text on the one evidence-screenshot
  `<img>`.
- **ACCESS-004 (P3):** Placeholder-only labeling on roughly half of styled
  inputs.
- **ACCESS-005 (P4):** Recommend a live browser/axe-core accessibility audit
  as a near-term follow-up — this review's findings are grounded in source
  code, not rendered behavior.
