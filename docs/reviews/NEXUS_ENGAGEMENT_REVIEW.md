# Motivation & Engagement Review

Date: 2026-07-21. Phase 12. Evidence: `XPLedger`/level system and
`WeeklyDomainLead`/leaderboard logic from the system map, `StudentHome.jsx`,
the live `leaderboard` API response, the promotion-gate structure, and the
Ticket/Lab reviews' findings on XP inconsistency between tickets and labs.

---

## 1. XP: learning signal or clicking signal?

**Mixed, trending toward learning signal — but undermined by an
inconsistency.** XP is earned via first quiz attempts and mentor-verified
tickets (real, graded work), which is the right design — it cannot currently
be farmed by repeated quiz retakes (only first attempt grants XP) or by
spam-submitting tickets (resubmission overwrites, doesn't stack). **However,
labs currently grant zero XP at all** (Lab Review, CUR-001) — meaning a
student who spends real effort on the 5 lab exercises gets no XP-visible
reward for it, while the exact same effort on a ticket does. A beginner
optimizing for the visible reward signal (XP, streak, leaderboard rank) has
a rational reason to deprioritize labs, which is the opposite of what the
"hands-on skill development" goal of this whole review wants.

## 2. Leaderboard risk: domination or discouragement?

**Real risk in a 5-6 person cohort, currently unmitigated.** `WeeklyDomainLead`
recomputes a weekly per-domain leader; live data shows all 6 real students
at 0 XP currently, so no live discouragement signal exists *yet* — but the
structural risk is real: in a cohort this small (5-6 named friends who all
know each other), a leaderboard makes relative standing immediately
personal and visible in a way it wouldn't be in a 200-person bootcamp. One
student pulling ahead early (plausible given real-life time differences
between 5 working adults) could discourage the others before the platform's
own pacing intends any of them to feel behind. **Finding ENGAGE-001 (P3):**
consider whether the current cohort size makes a leaderboard net-positive or
net-risky, and whether a "personal-best" or "on-pace" framing would serve
this specific 5-6-person group better than relative ranking.

## 3. Does XP's purpose read clearly to a beginner?

**No — this restates ONBOARD-001/NAV finding from a different angle.**
Nothing explains that XP and Role are two separate systems (Product Map
§4), so a student watching their XP number go up has no way to connect that
number to the very real, more consequential Role/Promotion-Gate system that
actually reflects job-readiness. XP risks being read as "the score" when
the gates are the more meaningful measure.

## 4. Is 24 weeks manageable, motivation-wise?

**Structurally yes** — the program's own pacing (weekly required quiz +
tickets, 5 promotion gates spread every ~4-5 weeks, 3 capstones at roughly
the ¼/½/end marks) gives regular, achievable milestones rather than one
distant 24-week finish line. This is good design for sustained motivation
over a long program.

## 5. Growth visibility

**Good in principle, currently invisible in practice for a fresh student.**
The stat cards on Home (XP, streak, quizzes done, tickets passed) are the
right instrumentation, but for a brand-new student showing all zeroes with
no context (Navigation Review, NAV-001), "growth visibility" doesn't start
functioning until well after the first login — there's no early "you're
making progress" signal in the first day or two, which is exactly when
motivation is most fragile for a total beginner.

## 6. Boredom and overwhelm points

**Overwhelm:** Weeks 3 and 7's stacked optional-certification quizzes (24-
Week Review) are the clearest overwhelm risk — a motivated beginner trying
to "complete everything visible" hits a wall of 12-13 extra quizzes with no
signal they're optional. **Boredom:** none of the reviewed lesson content
reads as filler or repetitive-without-purpose (Lesson Review); the
spaced-repetition design (same skill, escalating platform) is more likely to
read as satisfying ("I already know this part") than boring.

## 7. What will actually keep 5 friends engaged?

Given this is a small, known cohort of friends being personally mentored
(not an anonymous platform), the strongest engagement lever available is
almost certainly **the mentor relationship and Discord coordination**
(explicitly named in the project's stack/comms), not the gamification
layer. The XP/streak/leaderboard system is a reasonable secondary layer but
should not be relied on as the primary motivation mechanism for this
specific cohort — recommend the mentor's weekly call and Discord check-ins
carry more of the motivational weight than the in-app gamification, which
should be treated as a supporting signal, not the main one.

## 8. Summary findings

- **ENGAGE-001 (P3):** Reassess whether a competitive leaderboard is net-
  positive for a 5-6-person cohort of friends, vs. a personal-progress
  framing.
- **ENGAGE-002 (P2, restates CUR-001):** Labs granting no XP creates a
  reward-signal mismatch that could steer beginners away from hands-on
  practice — fix this alongside the Lab Review's XP finding.
- **ENGAGE-003 (P2, restates ONBOARD-001):** XP-vs-Role confusion is an
  engagement problem as much as a navigation problem — a student who
  doesn't understand what actually matters (Role) may over-focus on what's
  most visible (XP).
