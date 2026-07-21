# Beginner Student Journey & Navigation Review

Date: 2026-07-21. Phase 4. Evidence base: direct reads of `frontend/src/App.jsx`,
`frontend/src/pages/StudentHome.jsx`, `frontend/src/components/
WeekPlanPanel.jsx`; live API responses from the disposable
`nexus-review-student` account (0 XP, fresh login) against production;
`NEXUS_PRODUCT_MAP.md` for structural facts. No browser-automation tool was
available to either Claude or Codex in this environment (Codex's sandbox has
no network access at all), so this review evaluates the exact rendered JSX
and the exact JSON a fresh browser session receives — labeled **Both observed
live and confirmed in code** where the API data and the component logic were
both checked, **Confirmed in code** where only the source was read, and
**Not testable** where a real browser/screenshot would be needed (e.g. actual
pixel layout, CSS truncation, focus order).

Assume the reader is a complete beginner: no prior meaning for Lab, Ticket,
Evidence, CLI, Terminal, Remediation, Escalation, Verification, Active
Directory, DNS, DHCP, VM, or Promotion Gate.

---

## 1. First login experience

**What a first-time student sees** (Both observed live and confirmed in
code): the Home page renders a `PageHeader` with the student's name and the
subtitle *"Stay on track with your next lesson, quiz, and support ticket
milestone."* — followed by four stat cards (Total XP: 0, Day Streak: 0,
Quizzes Done: 0, Tickets Passed: 0), a "This Week" panel, an "Up Next" panel,
and a "Recent Activity" panel showing *"No recent submissions yet."*

**Finding NAV-001 (P1 — onboarding).** There is no welcome message, no
explanation of what Nexus is, no explanation of what a "week" means, no
tutorial, and no distinction drawn anywhere on this page between "required"
and "optional" work. A subtitle that says "stay on track with your next
lesson" assumes the reader already has a lesson in progress — a first-time
user has nothing to "stay on track" with. **Confirmed in code.**

**Finding NAV-002 (P2 — onboarding).** The "Up Next" panel's fallback text is
*"Pick up where you left off in your training plan."* — again phrased for a
returning user, not a day-one user who has never left anywhere. **Confirmed
in code.**

**Finding NAV-003 (P1 — content).** For a fresh student, `WeekPlanPanel`
receives Week 0 data with 0 lessons, 1 quiz, 0 tickets, 0 labs. Because the
panel only renders sections with a non-empty item list, the entire "This
Week" panel — the single most important piece of first-day guidance on the
page — collapses to one line: a single quiz titled "Ticketing Systems
Quiz." Nothing on the page tells the student this IS the entirety of Week 0,
that it's expected to take a few minutes, or what happens after they finish
it. **Both observed live and confirmed in code** (verified against the live
`week_plan` API response for the disposable account).

**Net first-login judgment:** a genuine beginner, on day one, sees their name,
four zeroes, one quiz, and no orientation. Nothing overwhelms them (the
opposite problem exists — see Week 0 Review), but nothing welcomes or
orients them either. This is the single highest-priority fix candidate in
the entire review (see Final Response).

## 2. Navigation item review

9 student nav items, in order, identical on mobile (**Confirmed in code**,
`App.jsx`):

| Item | Route | Beginner-clarity verdict |
|---|---|---|
| Home | `/` | Clear name, matches content (dashboard). Keep. |
| Learning Path | `/learning-path` | Clear enough once used once; a first-timer may not know this is "where lessons and videos live" vs. Study Tracker. Keep, but the first-login gap (§1) should point here explicitly. |
| Study Tracker | `/study-tracker` | Ambiguous name — "tracker" of what? It surfaces the CompTIA certification-objective catalog, a different content spine from Learning Path. A beginner cannot infer this from the label. Rename candidate. |
| Tickets | `/tickets` | Name is workplace-accurate but meaningless to a total beginner until explained once. Acceptable — this is a core, teachable term. |
| Labs | `/labs` | Same — teachable term, acceptable once explained. |
| Networking Labs | `/cli-labs` | The route is literally `/cli-labs` but the nav label is "Networking Labs" — a label/route mismatch that is harmless to students but a maintenance smell, and the label itself risks being confused with "Labs" one item above it. Merge candidate (see Lab Review, Phase 10). |
| Capstones | `/capstones` | Currently visible to a 0-XP brand-new student because `has_unlocked_capstones` defaults true (CUR-002, see Product Map). A nav item for "your final graduation project" appearing on day one, fully clickable, showing real capstone content, is actively confusing — it looks like something the student should be doing now. |
| Command Library | `/commands` | Clear, low-risk, reference-only. Keep. |
| Terminal Practice | `/terminal` | Clear but overlaps conceptually with Networking Labs — both are "practice running commands." Merge candidate. |

**Recommended nav for a beginner-safe launch** (down from 9 to 6, collapsing
where content already overlaps): **Home, Learning Path, Tickets, Labs
(absorbing Networking Labs + Terminal Practice under tabs), Command Library,
Capstones (hidden until genuinely unlocked)** — Study Tracker either folds
into Learning Path or is clearly relabeled ("Certification Practice" or
similar) so its distinct purpose is visible in the name itself. This
satisfies the brief's "≤5-6 sections" target. **Confirmed in code** (route/
component structure); the merge judgment itself is a product recommendation,
not an observed fact.

## 3. The capstone-visibility problem, isolated

**Finding NAV-004 (P1 — trust/confusion).** This deserves its own callout
because it compounds two separate real bugs into one beginner-facing
symptom: (a) `has_unlocked_capstones` is computed from real role rank vs.
`CapstoneTemplate.role_level`, but all 3 live templates have `role_level =
NULL`, so the comparison is vacuously true for everyone (CUR-002); (b) the
nav only *hides* the tab when the flag is explicitly `false` — there is no
"locked but visible with an explanation" state, only "fully there" or
"fully gone." The combined effect, confirmed live: a student who logged in
five minutes ago can open "CompTIA A+ Module 1 Capstone: Hardware &
Troubleshooting" (week_number 4) and read its full deliverables and rubric
before doing anything else in the program. **Both observed live and
confirmed in code.**

## 4. Named flow transitions — traced against the 9 beginner questions

For each transition: *(1) what is this, (2) why does it matter, (3) is it
required or optional, (4) how long will it take, (5) how do I know I'm
finished, (6) is my progress saved, (7) did I pass, (8) what do I do next,
(9) am I waiting on the mentor, and if I'm stuck, what do I do?*

**Home → "This Week" quiz link → quiz taker → submit → review screen.**
1–4 answered implicitly by quiz metadata (title, and the quiz UI's own
question count) — adequate. 5: yes, a final score screen exists
(`QuizReviewScreen`, confirmed in code from prior session context). 6: yes,
`QuizAttempt` rows persist immediately. 7: yes, shown on the review screen.
8: **not answered** — after finishing the one Week 0 quiz, nothing tells the
student where Week 1 begins or that this quiz WAS the entirety of Week 0.
9: no mentor step exists for quizzes — this is never stated explicitly, so a
student cannot be sure a quiz doesn't also need mentor review. 10 (stuck):
no in-quiz help/hint affordance is documented in the reviewed component set.
**Verdict: weak on 8 and 9.**

**Learning Path → lesson → mark complete → next lesson.**
1–3: clear from lesson title/module grouping. 4: `estimated_minutes` exists
in the data model and is shown per lesson (confirmed in code) — good. 5:
lesson completion is an explicit action (`VideoWatch`/lesson-completion
tracking exists per CLAUDE.md's "done" list). 6: yes, persisted. 7: N/A,
lessons aren't graded. 8: the "next lesson" affordance exists within Learning
Path but is not cross-linked from Home's "Up Next" reliably for a first-time
user (see NAV-002). 9: no mentor step — correctly not implied. 10: no
in-lesson stuck-help affordance beyond static text. **Verdict: adequate
within the page, weak on connecting back to Home.**

**Tickets list → open ticket → run CLI/read scenario → write plain-English
explanation → submit → AI grade → mentor verify/reject.**
1–3: ticket difficulty and category are shown; "required" vs "optional" is
not visually distinguished from a certification quiz's optional status
anywhere the student can see — a ticket IS always meaningful work, but the
UI gives the student no vocabulary to know that (see NAV-005 below). 4: no
estimated-time field is surfaced for tickets in the reviewed API payloads.
5: submission is an explicit action. 6: yes. 7: **ambiguous by design** —
AI grading returns a score immediately, but that score is explicitly
`pending` until a mentor calls `verify-proof`; nothing in the student-facing
ticket flow (as far as the reviewed code shows) tells the student "your
score is provisional until your mentor confirms it." A beginner who sees a
7/10 AI score will reasonably believe they are done. 8: unclear until mentor
action. 9: this looked like a gap from static reading alone. **Correction after live
testing (Phase 9):** the per-submission feedback screen
(`TicketFeedback.jsx`) does explicitly show a **"Awaiting instructor
verification. XP and mastery update after proof is verified."** banner
whenever XP hasn't been granted yet, plus a "Resubmit" button once a mentor
marks the ticket `needs_revision`. The residual gap, downgraded from P1 to
P2 and tracked as **TICKET-004-adjacent** in the Ticket Review, is that the
bare `status` word shown on the Tickets *list* page (`pending`,
`needs_revision`) isn't glossed in plain language on that list itself — a
student must open the feedback screen to get the explanation. 10: hints
exist (≤4 per ticket, with an XP cost) and are a real stuck-affordance —
this works. **Verdict: strong on 1-6, 9-10; the original 7-8 concern about
"did I pass" is real (see TICKET-001 in the Ticket Review for a much bigger
version of this problem — the A+ unlock gate blocks tickets entirely for a
brand-new student, a P0 finding discovered via live testing).**

**Labs list → open lab → follow setup instructions → submit evidence
(screenshot) → (no further step observed in code).**
1–5: adequate — the lab template includes description, setup instructions,
and explicit success-criteria tasks. 6: yes. 7: **the code path awards no
XP for labs at all** (confirmed in Product Map, CUR-001) and defaults an
unset score to 10 — so "did I pass" is answered by a number that may not
reflect real evaluation. 8: unclear — no visible "what's next" hand-off
after lab submission was found in the reviewed router logic. 9: no mentor
review gate currently exists for labs (unlike tickets) — this is inconsistent
with the ticket flow and not explained anywhere. 10: hints exist per lab
(confirmed in the curriculum dump — e.g. Hardware Component Identification
has 2 hints). **Verdict: weak on 7-9**, and inconsistent with the (better)
ticket-review pattern.

**Capstones list → open capstone → (four-stage structure described in
lesson text, not obviously mirrored in the UI).** Not fully testable without
a live browser session on an unlocked account with real progress; the
underlying template data (title, description, deliverables, rubric,
estimated hours) is rich and well-structured (**Confirmed in code**), but
whether the *UI* walks a student through the four stages described in the
Week 24 "Capstone Briefing" lesson, or just presents one long form, is
**Not testable** in this environment.

## 5. Dead ends, conflicting states, and guessing points (P1/P2 findings)

- **NAV-006 (P2).** Quiz browsing (both required and the large optional/
  certification tail) shares one undifferentiated list surface per the
  Product Map §7 — a student cannot tell, without inspecting each quiz, which
  ones count toward anything. This is a "guessing point."
- **NAV-007 (P2).** Networking Labs and Terminal Practice both being visible,
  separately, with no cross-explanation of how they differ, is a duplication
  a beginner will not resolve on their own (see also Lab Review).
- **NAV-008 (P3).** "Study Tracker" as a label gives no hint that it is a
  distinct, certification-objective-driven catalog rather than a personal
  progress tracker (which "Progress" — not currently a separate nav item —
  would more naturally suggest). Naming confusion, not a functional bug.

## 6. Summary verdict for Phase 4

The single largest beginner-navigation risk is not any one broken button —
it is the combination of (a) no onboarding message at all, (b) a Week 0 that
visually looks like "almost nothing to do," (c) a fully-visible, fully-
functional Capstone tab on day one, and (d) ticket/lab completion states that
don't distinguish "submitted" from "confirmed by your mentor." None of these
are security or data problems; all four directly threaten the "does a
complete beginner know what to do next" goal that is the entire premise of
this review. They are elevated to P1 in Phase 16.
