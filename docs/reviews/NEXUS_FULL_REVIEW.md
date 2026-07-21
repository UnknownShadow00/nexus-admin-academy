# Nexus IT Academy — Full Platform Review

Date: 2026-07-21. This is the master synthesis document for the 17-phase
review. It summarizes and cross-references the 13 detailed phase documents
in this directory plus `NEXUS_FINDINGS.csv`; it does not restate their full
evidence. Read the individual documents for the underlying detail.

**Documents in this review:**
`NEXUS_PRODUCT_MAP.md` · `NEXUS_BEGINNER_NAVIGATION_REVIEW.md` ·
`NEXUS_WEEK_ZERO_REVIEW.md` · `NEXUS_24_WEEK_REVIEW.md` ·
`NEXUS_LESSON_REVIEW.md` · `NEXUS_QUIZ_REVIEW.md` · `NEXUS_TICKET_REVIEW.md` ·
`NEXUS_LAB_REVIEW.md` · `NEXUS_LEARNING_EFFECTIVENESS_REVIEW.md` ·
`NEXUS_ENGAGEMENT_REVIEW.md` · `NEXUS_ACCESSIBILITY_REVIEW.md` ·
`NEXUS_MENTOR_ADMIN_REVIEW.md` · `NEXUS_TECHNICAL_REVIEW.md` ·
`NEXUS_FINDINGS.csv` · `NEXUS_PRIORITIZED_ACTION_PLAN.md` ·
`NEXUS_BEGINNER_FLOW_MAP.md` · `NEXUS_PUBLISH_READINESS.md` ·
`NEXUS_CODEX_IMPLEMENTATION_HANDOFF.md`.

---

## Overall judgment

Nexus is a genuinely well-designed 24-week curriculum sitting on a mostly
solid technical platform, with one production bug (TICKET-001/TECH-001,
P0) that will actually block real students on day one or two, and one
significant content gap (ONBOARD-001, P1) that undermines the platform's
core mission for total beginners specifically. Neither is large to fix.
Everything else found is real but genuinely secondary. **Recommendation:
ready for five/six-student private launch, conditional on fixing those two
items first** — full detail and per-area breakdown in
`NEXUS_PUBLISH_READINESS.md`.

## What is already strong

- **The curriculum itself.** All 63 lessons, read in full, follow a
  deliberate, consistent template (plain-language explanation → job
  relevance → common mistakes → measurable outcomes) and explicitly
  cross-reference prior/future weeks by number — a level of coherence rare
  in from-scratch curricula. See `NEXUS_LESSON_REVIEW.md`.
- **The ticket-grading system.** Live-tested this session with 5
  deliberately varied submissions (strong/weak/unsafe/escalation-correct/
  incomplete) — the AI grader correctly discriminated quality every time
  (scores of 8, 1, 1, 7, 2 respectively), and the mentor verify/reject
  workflow and student-facing feedback screen both work exactly as
  designed. See `NEXUS_TICKET_REVIEW.md`.
- **Technical health.** 176/176 backend tests pass, Alembic is at head
  (0029), SQLite integrity and foreign-key checks are clean, npm audit
  reports 0 vulnerabilities, and the frontend builds cleanly — all
  re-verified fresh this session, not assumed from prior documentation. See
  `NEXUS_TECHNICAL_REVIEW.md`.
- **Security posture.** HTTPS redirect, CSP/HSTS/security headers, CSRF
  protection, and per-student AI rate limiting all confirmed live and
  functioning correctly this session.
- **Mentor tooling.** The review/reject/verify workflow and AI cost
  dashboard both work correctly and are well-suited to a single mentor
  managing a small cohort. See `NEXUS_MENTOR_ADMIN_REVIEW.md`.

## Biggest beginner problems

1. **No platform onboarding exists anywhere** (`ONBOARD-001`) — first login
   shows a name, four zeroes, and one quiz, with no welcome message and no
   explanation of how the platform works.
2. **The A+ unlock gate silently blocks all hands-on work** (`TICKET-001`) —
   a fresh student cannot submit Week 1's tickets until ~9 hours of
   unrelated video-watching, with zero in-app explanation of why.
3. **Capstones are fully visible and accessible on day one** (`CUR-002`/
   `NAV-004`) because all 3 capstone templates have `role_level = NULL`.
4. **Week 1 has zero lessons but two graded tickets** (`LESSON-001`) — the
   only place in the entire 25-week program where students are tested
   before being taught.

## Biggest learning problems

- Group Policy (Week 16), subnetting (Week 10), Active Directory (Week 14),
  and PowerShell (Week 17) are each taught well but practiced thinly — one
  ticket for some of the program's hardest concepts.
- Labs carry no XP and no mentor-review gate, unlike tickets — real hands-on
  effort currently goes unrewarded and unverified in a way tickets are not.
- Evidence (screenshots) is not actually content-validated and is not even
  required for submission — "proof of work" is currently closer to an
  honor system than a verified gate.

## Biggest mentor problems

- The mentor's own dogfooding activity (a ticket + 2 lab starts) is
  currently visible in the shared squad-activity feed and should be cleared
  or confirmed hidden from students before Week 0.
- No stalled-student or failed-quiz signal is surfaced directly in the
  admin overview — a mentor has to infer these manually. Low-urgency
  pre-launch (no real activity exists yet), but worth adding before it
  matters.

## Current technical issues (verified against the current build only)

- The A+ unlock gate (see above) — the only P0/P1-severity technical issue.
- Rate-limit rejections surface as generic 500s instead of proper 429s.
- A dead `grade_now` request field.
- Evidence-validation schema/implementation mismatch on `must_contain_text`
  for screenshots.
- No regressions of any kind versus the last known-good checkpoint (176
  tests, Alembic 0029, clean integrity/FK/npm audit) — all re-verified
  fresh, not assumed.

## Before Week 0 (short ordered list)

1. Fix the A+ unlock gate (`TICKET-001`/`TECH-001`).
2. Add Week 0 platform onboarding (`ONBOARD-001`, bundled with `NAV-001/
   002/003`).
3. Fix the capstone role-gate data (`CUR-002`/`NAV-004`).
4. Write the missing Week 1 lesson (`LESSON-001`).
5. Clear the mentor's dogfooding activity from the squad feed (`ADMIN-003`).

Full detail, sequencing, and every remaining item: see
`NEXUS_PRIORITIZED_ACTION_PLAN.md`.

## Can wait

Everything in that plan's "During Weeks 1-4," "After the first cohort
begins," and "Future work" sections — lab XP/evidence hardening, quiz
labeling, nav consolidation, accessibility polish, additional tickets/labs
for thin-practice weeks, mentor-digest automation, and automated Proxmox/
Guacamole VM labs (correctly still disabled, no action needed until a real
infrastructure smoke test passes).

## Test results (this session, live)

- **Live student journey:** logged in as a disposable student, walked the
  dashboard/learning-path/week-plan/tickets/quizzes/labs/capstones/study-
  tracker/commands/leaderboard/promotion-status APIs — all 200 OK; traced
  the actual first-login experience against the rendered component source.
- **Live admin journey:** logged in as the real admin session, reviewed all
  11 admin surfaces, and **actually drove the reject-proof → needs_revision
  → resubmit → verify-proof → XP-granted state machine end to end** on a
  real submission, not just read the endpoints.
- **Backend tests:** `python -m pytest tests/ -q` → **176 passed**, 0
  failed.
- **Frontend build:** `npm run build` → success, 1983 modules, one
  pre-existing (non-blocking) bundle-size advisory.
- **Dependency audit:** `npm audit` → **0 vulnerabilities**.
- **Database checks:** `PRAGMA integrity_check` → `ok`; `PRAGMA
  foreign_key_check` → **0 violations**.
- **Temp-account cleanup:** performed after this document was written — see
  the final response for confirmation, including the A+ unlock threshold
  being restored to its original production value of 40% after live ticket
  testing required temporarily lowering it to 0%.

## Recommended first implementation phase

**One tightly focused task: fix the A+ Study Tracker unlock gate
(`TICKET-001`/`TECH-001`) so it does not silently block Week 1's tickets.**
This is the single highest-leverage fix available — it is small (a
one-line admin-setting change, or a small, well-scoped UI addition per
`NEXUS_CODEX_IMPLEMENTATION_HANDOFF.md` Task 1), it is the only finding in
this entire review that would actually stop a real student from doing their
assigned Week 1 work rather than merely confusing them, and fixing it does
not depend on or block any other recommended fix. **No fix has been
implemented as part of this review.** Await project-owner approval of the
Prioritized Action Plan before directing Codex to change any production
code.
