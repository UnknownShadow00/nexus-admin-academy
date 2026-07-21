# Lesson Quality Review

Date: 2026-07-21. Phase 7. Evidence: full text of all 63 lessons across all
25 weeks, read directly from the live curriculum dump (not summarized by
Codex — every lesson's "Full summary / teaching text" and "Outcomes" block
was read in full by Claude). This is the single most content-heavy phase of
the review; the classification below is a direct product of that full read,
not a sample.

---

## 1. Overall quality verdict

The lesson content is **strong, and consistently so** — this is the most
positive finding in the entire review. Every one of the 63 lessons follows a
recognizable, deliberate template: a plain-language explanation of the
concept, a "why a junior needs this" framing tied to real job tickets, a
named common-mistakes list, and 2-3 measurable outcome statements. Nearly
every lesson explicitly cross-references specific earlier or later weeks by
number ("the Week 8 triage tree," "you'll meet this again in Week 16"),
which is unusual discipline for a from-scratch curriculum and is the
strongest evidence that this was designed as one coherent program rather
than assembled from disconnected units.

## 2. Classification of all 63 lessons

Using the requested categories (strong / too-short / too-long / too-advanced
/ vague / definitions-only / missing-demos / missing-examples / missing-
exercises / repetitive / outdated):

- **Strong (54 of 63, ~86%):** the large majority. Representative examples:
  Week 2 "Anatomy of a Good Ticket" (concrete bad-note rewrite exercise),
  Week 3 "Storage: Symptoms Before Specs" (symptom→cause table with explicit
  safety stop-points), Week 9 "Client-Side Network Triage Tree" (the
  strongest single lesson in the program — a complete, numbered, evidence-
  driven diagnostic method), Week 19-20's Linux lessons (deliberately mirror
  the Windows lessons' structure to reinforce transfer learning), Week 24's
  closing lessons (explicit "your method is portable" synthesis).
- **Too-short (Week 0's only lesson, 1 of 63):** "CompTIA 6-Step Process" is
  three sentences plus three outcome bullets — noticeably thinner than every
  other lesson in the program, and it is also the very first thing every
  student ever reads. See Week 0 Review.
- **Vague / definitions-only (0 found):** none of the 63 lessons are bare
  definition lists — even the most conceptual lessons (e.g. Week 22's cloud
  service models) tie every definition to a "why a junior needs this" line.
- **Missing-exercises (a meaningful minority, ~6 lessons):** Weeks 10
  (subnetting), 12 (routing/services), 14 (AD foundations), 16 (GPO), 17
  (PowerShell), and 21 (production Linux) each present a "GUIDED PRACTICE" or
  "PRACTICE" pointer to CLI labs or a worksheet, but the lesson text itself
  contains no worked example a student can check their own reasoning
  against before attempting the linked ticket — consistent with the "thin
  hands-on reinforcement" finding in the 24-Week Review.
- **Too-advanced-for-position (2 lessons):** Week 16 Lesson 1 (GPO/LSDOU
  precedence with Enforced/Block Inheritance modifiers) and Week 12 Lesson 3
  (DHCP relay/NAT/firewall/VPN/wireless in one lesson) each pack more
  simultaneous new concepts than the surrounding weeks' lessons, without a
  proportionate increase in guided practice.
- **Repetitive (0 problematic; intentional repetition only):** the
  recurring "account lifecycle" pattern (Week 6 desktop → Week 7 desktop-in-
  practice → Week 14 AD → Week 22 Entra ID) is repeated by design, each time
  with a genuinely new wrinkle (domain scope, then cloud/MFA/sign-in-log
  differences) — this is spaced repetition working as intended, not filler.
- **Outdated (0 found):** no lesson text references deprecated tooling or
  incorrect procedure as far as reviewed; command syntax (ipconfig, dig,
  systemctl, Get-ADUser, etc.) is current.
- **Missing-demos (Not testable):** whether video/screen-capture
  demonstrations accompany each lesson beyond the linked Professor Messer/
  YouTube video-tracker entries could not be verified without a live
  browser session against the actual video attachments per lesson.

## 3. Beginner-language check

Technical vocabulary is consistently introduced with a plain-language
gloss on first use within a lesson (e.g., DNS is glossed as "a wrong
address-book setting" in Week 2's user-facing-language example; APIPA is
explicitly tied to "DHCP failed" every time it recurs). This is a genuine
strength for a zero-background cohort — the writing does not assume prior
IT vocabulary, only prior lessons within the program itself.

## 4. Length and structure

Estimated lesson minutes range from 45 (short conceptual lessons) to 120
(dense hands-on lessons like Week 4 Lesson 3 "Command-Line Diagnostics" and
Week 17 Lesson 2 "PowerShell"). No lesson exceeds what its content
complexity would justify; the 120-minute lessons are appropriately the ones
with the most named commands/tools to practice, not padded.

## 5. Connections to quizzes/tickets/labs

Nearly every lesson explicitly names the ticket(s) or lab(s) that exercise
its content in the same week (e.g., Week 3 Lesson 2 names ticket "W2 'Desktop
won't turn on'" directly in the lesson text). The one clear break in this
pattern is **Week 1, which has 0 lessons but 2 tickets and a required
quiz** — the lesson-to-assessment linkage that works everywhere else in the
program is structurally absent for the very first graded tickets a student
ever attempts. This is the same finding as CUR/24-Week-Review's Week 1 gap,
restated here from the lesson-quality angle: **students are tested/ticketed
in Week 1 before any lesson teaches the material.**

## 6. Workplace relevance

Every lesson ties back to a "why a junior needs this" or "COMMON MISTAKES"
section grounded in real job scenarios, not exam trivia — this is a
consistent strength across all 63 lessons and is one of the clearest signals
that this curriculum was designed by someone with real help-desk/network-
admin experience (consistent with the mentor's stated background).

## 7. ADHD/dyslexia accessibility of lesson text

**Positive:** heavy use of short labeled sections (ALL-CAPS lead-ins like
"THE DECISION:", "SAFETY:", "COMMON MISTAKES:"), bulleted symptom→cause
tables, and numbered sequential steps — this structure is generally
favorable for ADHD/dyslexic readers versus dense prose, since it lets a
reader scan for the relevant subsection rather than parse a wall of text
top-to-bottom.
**Risk:** several lessons (e.g. Week 12 Lesson 3, Week 17 Lesson 2) are
long, single-block paragraphs under each ALL-CAPS header rather than further
broken into bullets — the labeling helps navigation but the paragraphs
themselves would benefit from shorter sentences and more line breaks. This
is a Phase 13 (Accessibility Review) finding as much as a lesson-quality
one; noted here and not duplicated in full there.
**Not testable:** actual rendered typography, line length, and contrast in
the live Learning Path UI — this assessment covers only the source text.

## 8. Are students taught before tested? (the central Phase 7 question)

**Yes, with one significant exception.** Across 24 of the 25 weeks, lesson
content demonstrably precedes and directly informs that week's required
quiz and tickets. **Week 1 is the exception**: 0 lessons, 1 required quiz, 2
tickets. This is flagged as **LESSON-001 (P1)** and cross-referenced from
the 24-Week Review and Week 0 Review — three separate phases converging on
the same underlying gap is a strong signal this is the single most
consequential curriculum-structure fix available.

## 9. Summary findings carried to Phase 16

- **LESSON-001 (P1) — SUPERSEDED, see `NEXUS_FINDINGS.csv`:** this finding's
  premise was false. Live verification during the Pre-Week-0 Launch Readiness
  Sprint (2026-07-21) found `MOD-001`'s two lessons ("Anatomy of a Good
  Ticket", "Meet the Command Line") were already being served as Week 1
  content by `/api/students/me/week-plan?week=1` — the "0 lessons" reading
  came from the curriculum-dump script's own ad-hoc week headers, not the
  live week-derivation logic. The real defect found in its place was a
  cosmetic-only Learning Path lock on `MOD-001` (fixed via migration
  `0030_week_gating_data_fixes.py`). No new lesson was written.
- **LESSON-002 (P2):** Week 0's single lesson is markedly thinner than the
  other 62 — bring it in line with the program's normal depth, or accept its
  brevity but pair it with the Week 0 onboarding fix instead of curriculum
  depth.
- **LESSON-003 (P3):** Weeks 10, 12, 14, 16, 17, 21 would benefit from one
  worked example embedded directly in the lesson text (not just a pointer to
  a separate CLI lab), especially for the two hardest concepts in the
  program (subnetting, GPO precedence).
- **LESSON-004 (P4):** Long single-paragraph blocks in a handful of dense
  lessons (Week 12 L3, Week 17 L2) could be reformatted into shorter, more
  scannable bullets for ADHD/dyslexia readability — low cost, low risk,
  quality-of-life improvement.
