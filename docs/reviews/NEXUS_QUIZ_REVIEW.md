# Quiz Quality Review

Date: 2026-07-21. Phase 8. Evidence: full text of the Week 0 and Week 1 quiz
question sets (12 questions across 5 quizzes, read verbatim), the live admin
quiz-editorial-queue API response (quality scores and missing-explanation
counts across the optional/certification tail), and the system map's
progression logic (`students.py`: only `is_required + show_in_weekly_
checklist + answer_keys_validated` quizzes count toward progression).
**No hidden or unpublished quiz was opened, published, or modified during
this review**, per the brief's explicit constraint.

---

## 1. The two very different quiz populations

Nexus's 104 quizzes split into two populations that behave, and read,
completely differently:

**A. Required/gate/cumulative quizzes (25 total)** — original Nexus-authored
content, one per week, explicitly aligned to that week's tickets/lessons.
Sample evaluated in full: Week 0's "Ticketing Systems Quiz" (4 Qs) and Week
1's "Ticket Writing Fundamentals" (8 Qs). These are **scenario-based, not
memorization-based** — e.g. "An internal note reads: 'PC was broken, fixed
it.' What is the FIRST thing missing?" — every question has a full,
reasoned explanation tied to the program's own grading anchors
(investigation/root_cause/safe_fix_or_escalation/verification/
communication). **Verdict: strong.** This is the population that actually
counts toward progression.

**B. Optional/practice/certification/remediation quizzes (79 total)** —
overwhelmingly ExamCompass-scraped CompTIA A+/Network+ certification-bank
content. Sample evaluated in full: Week 1's four optional quizzes (Mobile
Device Connection Methods, Hardware Servicing, Accessories, Application
Support — 27 questions total). **Verdict: mixed to weak.** Roughly a third
of the questions sampled had a **blank explanation field** (visible directly
in the raw data — e.g. Questions 1, 4, 5 of the Connection Methods quiz have
empty `**Explanation:**` blocks). The live admin editorial queue confirms
this is systemic, not a sampling artifact: quizzes like "BIOS Quiz" (6 of 7
questions missing explanations, quality_score 57), "Power Supply Quiz" (7 of
12 missing, 57), and "Storage and RAID Troubleshooting Quiz" (15 of 18
missing, 57) are marked `editorial_status: needs_edit` and
`answer_keys_validated: false` — and are nonetheless `status: published,
active: True`, meaning students can open and attempt them today.

## 2. Is "hidden quizzes not published" actually true?

**No — this is a fact-check correction to the review brief.** The mechanism
is not visibility, it's progression weighting. `needs_edit`/unvalidated
quizzes are excluded from the required-progression calculation, but they are
not hidden from the student-facing quiz browser. A student who clicks into
one sees a real quiz, submits real answers, and gets scored — but for roughly
a third of the sampled questions, gets no explanation of why they were
right or wrong, and cannot fully trust the answer key is correct (it is
explicitly flagged `answer_keys_validated: false` in the admin queue). This
is **QUIZ-001 (P2)**: optional quizzes with unvalidated answers/missing
explanations are visible and attemptable by students, contradicting the
review brief's assumption and creating a real risk of a beginner memorizing
an unvalidated "correct" answer with no explanation to catch a bad key.

## 3. Fairness, guessability, and difficulty

The required-quiz sample (Weeks 0-1) shows well-constructed distractors —
wrong options represent plausible beginner misconceptions rather than
throwaway filler (e.g. Week 1 Q2's four resolution-note options each sound
plausible to someone who hasn't yet learned the internal/external-notes
distinction the lesson teaches). Multi-select questions ("select 3 answers")
are used appropriately for genuinely multi-part concepts. No answer-position
bias pattern was detectable in the small sample reviewed (Not testable at
full-corpus scale without a systematic answer-key export, which was out of
scope for a manual read).

## 4. Retake, mastery, and XP behavior (Confirmed in code, from the system
   map)

One `QuizAttempt` row is stored per attempt (no unique-attempt constraint);
mastery is computed as the best score across attempts; **XP is only granted
on the first attempt**. This is a sound design — it rewards a first honest
try without punishing later review attempts, and prevents XP-farming via
repeated retakes. No issue found here.

## 5. Remediation quiz effectiveness

Remediation-purpose quizzes exist in the catalog (17, per the Product Map)
but are explicitly "visible only after explicit assignment or a failed
required quiz in the same week" per the quiz-organization documentation
already in the repo (`docs/QUIZ_IMPLEMENTATION_RESULTS.md`, referenced in
CLAUDE.md's July 19 session note). This design is sound in principle; actual
remediation-quiz *content* quality was not sampled in this pass (none
appeared in the Week 0/1 curriculum dump sections reviewed) — **Not
testable** without deliberately failing a required quiz on the disposable
account, which was not done in this pass to avoid generating extra grading
noise ahead of final cleanup.

## 6. Gate-quiz meaningfulness

Each of the 5 promotion-gate roles requires one specific week's required
quiz (Week 4, 8, 12, 17, 24 respectively) as one of several gate criteria
(alongside lesson completion, domain mastery thresholds, verified-ticket
counts by difficulty, and a named practical-checkpoint ticket). The gate
quizzes are drawn from the same well-constructed required-quiz population as
the general weekly quizzes — no evidence of a separate, weaker "gate quiz"
tier. **Verdict: meaningful**, assuming the underlying required quiz for
that week is itself strong, which the sample supports.

## 7. Unsafe recommendations, outdated language, duplicates

None found in the sample reviewed. No safety-relevant wrong-answer-as-
correct issue was detected in the required-quiz sample. The optional/
certification tail's content (mobile device servicing, USB/connector types,
etc.) is standard CompTIA A+ material with no unsafe procedural content
identified.

## 8. Summary findings carried to Phase 16

- **QUIZ-001 (P2):** ~79 optional/certification quizzes are published and
  attemptable with a meaningful fraction (confirmed via the live editorial
  queue) marked `needs_edit`/`answer_keys_validated: false` and missing
  explanations on many questions. Recommend either (a) gating these behind
  an explicit "practice — answers not yet verified" label visible to
  students, or (b) running the existing `apply_quiz_answer_corrections.py`
  correction pass (already built and dry-run-safe per CLAUDE.md) before
  cohort launch.
- **QUIZ-002 (P3):** No systematic answer-position-bias or duplicate-
  question audit was performed at full-104-quiz scale — recommend an
  automated pass (script, not manual read) if time allows before or shortly
  after launch, since this is mechanical work well suited to a script rather
  than further manual review.
- **QUIZ-003 (P4):** Consider trimming the optional certification-quiz count
  per week where it's heavily stacked (Weeks 3 and 7 in particular, per the
  24-Week Review) — not a quality defect, but a volume/overwhelm risk for a
  beginner who doesn't understand these are optional (ties to NAV-006).

---

## Phase 7 live-verification addendum (Pre-Week-0 Launch Sprint, 2026-07-21)

**QUIZ-001 as originally written above is corrected: NOT PRESENT.** The
original finding was produced by reading the admin-only editorial-queue API
and the raw curriculum-content-dump script, both of which intentionally
surface every quiz — including unvalidated ones — for content-review
purposes. Neither reflects what a student can actually reach. This addendum
replaces that inference with three live tests performed this session against
a disposable student account:

1. `GET /api/quizzes` (student list) did **not** include quiz id 26 (a known
   `needs_edit`, `answer_keys_validated: false` certification quiz) among its
   28 results.
2. Direct `GET /api/quizzes/26` returned `404 {"error": "Quiz not found"}`.
3. Direct `POST /api/quizzes/26/submit` with a full valid payload also
   returned `404`.

Code confirms this is systematic, not a lucky sample: `quiz_visibility.py`'s
`student_visible_quiz_filters()` requires `status=published AND
is_active=True AND editorial_status=validated AND answer_keys_validated=True`,
and is applied uniformly at every student-facing route (list, detail, submit,
review) in `quizzes.py`. There is no direct-URL or direct-ID bypass.

**Precise inventory (live `nexus.db`, queried directly, 2026-07-21):**

| Category | Count | Student-visible? |
|---|---|---|
| Total quizzes | 104 | — |
| Required/gate/cumulative, validated (counts toward progression) | 25 | Yes — exactly one per Week 0-24 |
| Optional/practice, validated (visible, does not affect progression) | 3 | Yes |
| **Student-visible total** | **28** | — |
| Certification, not validated | 29 | **No** |
| Practice, not validated | 30 | **No** |
| Remediation (any validation state) | 17 | **No** (unless explicitly assigned or unlocked by a failed required quiz — not tested this pass) |
| Draft / inactive | 5 | **No** |
| **Hidden/unvalidated total** | **76** | — |
| Any unvalidated quiz visible via list or detail | 0 | confirmed |
| Any unvalidated quiz attemptable via direct URL/ID | 0 | confirmed |

The quality issues documented in Section 1 above (missing explanations,
`needs_edit` status on much of the certification tail) are still real and
still worth fixing — but they affect content-review priority, not launch
safety, since students cannot reach that content today. QUIZ-001 is
downgraded from "P2, confirmed present" to **not a launch blocker**; the
underlying content-quality work (QUIZ-002/QUIZ-003) remains a legitimate,
non-blocking post-launch improvement.

No bulk answer-correction or publish process was run as part of this
correction, per the sprint's explicit constraint — this addendum only
documents verified live behavior.
