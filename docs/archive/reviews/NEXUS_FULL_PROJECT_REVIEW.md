# Nexus Learning — Full Project Review

**Date:** 2026-07-23 · **Baseline commit:** `15a94103d5b951913875cc5a054fda7b70bede32` (`15a9410`, `main`)
**Reviewer:** Claude Code · **Scope:** live + source review across 19 phases (see `phase-reports/`).
**Method:** genuine authenticated browser testing (Playwright/Chromium, desktop 1440×1000 + mobile
375×812) against `https://nexus.builtfromzero.fyi/`, plus full source/DB/migration/test inspection.
No production deploy, merge, push, flag change, or real-student modification occurred.

---

## 1. Executive summary
Nexus is a **well-built, coherent IT-training platform** that is genuinely ready to serve its five
beginner students, with a short list of polish items and two structural gaps worth addressing soon.
The student experience is a standout: a clean 4-item navigation, an excellent 25-week guided "My
Training" path with clear next-steps and understandable gating, a high-quality Cisco IOS networking
simulator, and a thoughtfully designed Service Desk lab. Security is strong for a private program —
every authorization and IDOR probe was blocked live, crypto/cookies/CSP are solid, and 238 backend
tests pass. The database schema is clean (integrity ok, all FKs cascade-safe) and seeds are idempotent.

The most valuable improvements are **not** bug fixes but **enablers**: give admins real per-student
monitoring (they currently can't see who's on track), add a CI pipeline (tests run only manually),
and finish the Service Desk student-side rollout. A handful of quick wins (surface authored lesson
objectives, silence the Service Desk 404 noise, add SQLite WAL) deliver outsized value. **No P0
issues exist; nothing blocks the five-student launch.**

## 2. Architecture map
React 18 + Vite SPA (`frontend/`) ↔ FastAPI + SQLAlchemy + Alembic (`backend/`) over JSON, SQLite in
prod. Split auth: student signed-JWT HttpOnly cookie; admin separate expiring server-side session
(`verify_admin`). 28 routers (all mounted), 30 models, 37 services, 47 migrations (head `0035`).
Middleware: CORS + origin-based CSRF + security headers. Production sits behind Cloudflare with the
backend apparently on Render. Full detail: `phase-reports/phase-02-architecture.md`.

## 3. Product strengths
- **My Training** — sequenced weekly path, clear "what's next", locked weeks with explicit
  prerequisites and time estimates. The best part of the product.
- **Networking Labs** — 48 Cisco IOS simulator labs with scenarios, objectives, topology, hints,
  and tracked completion; purely frontend (no VM infra). Excellent and ready.
- **Service Desk Lab (Phase 1A)** — 5 realistic tier-1 scenarios with enforced identity
  verification, critical-failure gating, immutable versions, and health checks. Strong design.
- **Assessment integrity** — no answer leakage, no IDOR, no XP double-award (all verified live);
  FSRS spaced-repetition loop from wrong answers.
- **Security** — bcrypt, HttpOnly/Secure/SameSite cookies, strict CSP + HSTS, airtight object
  ownership. **Database** — integrity ok, cascade-safe FKs, idempotent seeds.
- **Accessibility/responsive** — no mobile overflow, labeled controls, visible keyboard focus,
  full dark mode.

## 4. Major risks / technical debt (ranked)
1. **No per-student admin monitoring** — admins can't answer "what should each student do / what
   have they done / where are they stuck / what's overdue." Biggest gap for running the program.
2. **No CI** — 238 tests + e2e + audits run manually; regressions can merge unnoticed.
3. **Service Desk student-side never validated end-to-end** (flag-gated); must precede student use / 1B.
4. **Duplicated business logic** — progress/XP/mastery across 5+ modules; dual unlock systems
   (module vs week); 3 overlapping admin content editors → divergence risk over time.
5. **Docs vs hosting mismatch** — DEPLOYMENT.md describes self-host systemd/SQLite; prod appears to
   be Cloudflare/Render (affects backup/restore validity).

## 5. Student UX review (Phase 3)
Clean 4-item nav (Home, My Training, Practice Library, Progress). Beginners can always tell what to
do next. Graceful empty/locked/unavailable states. Issues: Practice Library breadth + confusable
CLI-trio names; Weekly Roadmap duplicated across Home/Training/Progress; `/service-desk` emits 404s
in its gated state.

## 6. Admin UX review (Phase 4)
Clean workflow IA; excellent content-integrity tooling ("References valid", 137/137 video mapping,
Service Desk health). Gaps: no per-student monitoring/drill-down; three overlapping content editors;
no admin audit log; single shared admin identity.

## 7. Navigation review
See `NEXUS_NAVIGATION_PROPOSAL.md`. Keep the 4-item student / 5-group admin IA; group the Practice
dropdown into 3–4 clusters, merge Command Library into Terminal Practice, add admin cohort
monitoring + audit log. No new top-level tabs.

## 8. Curriculum review
See `NEXUS_CURRICULUM_AUDIT.md`. 25 weeks / 296 activities, sound sequence, welcoming Week 0,
balanced required workload. Polish: dense weeks (25–27 activities) presentation; watch-heavy vs. 5
guided labs; "24-week" copy bug; one stub lesson; surface authored objectives. **Ready with polish.**

## 9. Lesson review (Phase 6)
64 lessons, all published, good content (median 1532 chars, 1 stub). Safe (plain-text rendering).
Key bug: authored `outcomes` (objectives) exist for 63/64 lessons but are never serialized/shown.
Dead: learning-path API + video-embed branch. No central notes view. Search leaks gated summaries.

## 10. Practice / lab review (Phase 8)
5 guided labs, 48 networking labs (standout), 50 command refs, terminal sandbox (no completion), 48
tickets, 3 capstones. Merge/relabel the CLI trio; clarify sandbox-vs-graded and dual-surfaced
tickets/labs; don't build an enterprise catalog.

## 11. Support Tickets vs Service Desk (Phase 9)
Distinct, complementary skills (AI-graded written comms vs deterministic safe procedure); no data
conflict. All 5 SD scenarios well-designed. Naming confuses beginners. Student-side SD not validated
live (flag-gated) — do that before student exposure and before Phase 1B.

## 12. Security (Phase 10)
Strong. All IDOR/authorization probes blocked live; bcrypt, secure cookies, strict CSP/HSTS,
server-side hidden facts, bounded uploads, npm audit clean, 45 security tests pass. Findings: no
app-level login rate-limit (Cloudflare mitigates); no admin audit log; search-gating bypass (low).
**No P0/P1 security defect.**

## 13. Database / seeds / migrations (Phase 11)
Excellent: 55 tables, all FKs cascade-safe, integrity ok, 121 indexes, 39 unique constraints.
Migrations reversible except 5 stub downgrades. Seeds idempotent; scenario versions immutable.
Finding: add SQLite WAL + busy_timeout. Postgres only when concurrency triggers hit.

## 14. Code quality (Phase 12)
Clean (0 TODO markers, 238 tests pass). Smells: oversized `training_service.py` (870) /
`commandEngine.js` (930) / `students.py` (719); N+1 in the dead learning-path endpoint; duplicated
progress/XP/mastery + dual gating + 3 editors. Ten prioritized refactors listed; **no rewrite**.

## 15. Performance (Phase 13)
Lean runtime (5 API calls / 788 ms / 0 duplicates on home; `/health` 200; code-split admin routes;
ErrorBoundary). Fix: split the 1 MB entry bundle; address Render cold-start. Cloudflare beacon CSP
warning is harmless — do not weaken CSP.

## 16. Accessibility (Phase 14)
Good: 0 mobile overflow, labeled controls, visible focus, dark mode, status not color-only. Fix
small touch targets on All Course Content (mobile); add reduced-motion; add automated contrast + a
manual screen-reader pass.

## 17. Testing (Phase 15)
228 tests + 6 real-journey e2e; strong security/gating/service-desk/idempotency coverage. Gaps:
no tests for search/flashcards/evidence/resources/commands; migrations not tested both ways. **Add CI.**

## 18. Deployment (Phase 16)
Live app matches the baseline (routes/nav/gating/isolation); no stale deploy or prod-only errors.
Reconcile self-host docs vs Cloudflare/Render reality and verify the backup/restore runbook.

---

## 19. Prioritized findings
Each finding is stated once. IDs map to `NEXUS_IMPLEMENTATION_BACKLOG.md`.

### P0 — Immediate security / data-loss / production-failure risk
**None found.**

### P1 — Serious bug or major student/admin blocker
| # | Finding | Evidence | Blocks student use? | Blocks beta? | Blocks 1B? |
|---|---|---|---|---|---|
| P1-1 (NB-1) | Lesson `outcomes` authored (63/64) but never serialized/rendered → objectives invisible | Phase 6 live API + source | No | No | No |
| P1-2 (NB-2) | `/service-desk` gated state fires 4× 404 console errors | Phase 3/9/13 live | No | Yes (polish) | Yes |
| P1-3 (NB-3) | No per-student admin monitoring (current week/completion/struggling/overdue) | Phase 4 live | No | No | No |
| P1-4 (NB-4) | No CI pipeline — tests run manually | Phase 15 | No | No | No |
| P1-5 (NB-5) | Service Desk student-side never validated end-to-end (flag-gated) | Phase 9 | No | Yes | **Yes** |

### P2 — Important usability / maintainability / curriculum
Login rate-limiting (NB-6) · admin audit log (NB-7) · merge CLI trio (NB-8) · SQLite WAL/busy_timeout
(NB-9) · consolidate progress/XP/mastery (NB-10) · consolidate 3 content editors (NB-11) · split
entry bundle (NB-12) · attempted-vs-passed + coverage-vs-mastery (NB-13) · curriculum polish:
lesson 1, dense weeks, early labs (NB-14) · central My Notes (NB-15) · reconcile deploy docs (NB-16)
· mobile touch targets (NB-17) · tests for search/flashcards/evidence (NB-18) · Weekly Roadmap
duplication · dual module/week gating (NB-22). **(16 items.)**

### P3 — Useful improvement
"24-week" copy (NB-19) · search gating (NB-20) · quiz answer explanations (NB-21) · remove dead
learning-path API + video branch (NB-23) · reduced-motion (NB-24) · magic-byte upload + header
de-dup (NB-25) · Week-0 Document Types ordering (NB-26) · pip-audit in CI · automated contrast checks.
**(9 items.)**

### Future — valuable but not yet appropriate
Service Desk 1B scenarios · My Training ↔ Service Desk integration · more guided labs · PostgreSQL
migration (only when triggered) · VM/Proxmox/Guacamole integration · AI expansion. **(6 items.)**

**Totals: P0 = 0 · P1 = 5 · P2 = 16 · P3 = 9 · Future = 6.**

---

## 20. Roadmap (small private program)

### Immediate stabilization (before more students/features)
- NB-1 surface lesson objectives · NB-2 fix Service Desk 404s · NB-9 SQLite WAL/busy_timeout ·
  NB-13 fix "Great work!"/coverage labels · NB-19 "24-week" copy. *(All XS/S, low risk.)*

### Next 30 days (reduce confusion/risk)
- NB-4 CI pipeline · NB-3 admin cohort monitoring + drill-down · NB-5 Service Desk end-to-end
  walkthrough · NB-6 login rate-limiting · NB-8 merge CLI trio · NB-16 reconcile deploy docs.

### Next 60 days (curriculum, practice, admin)
- NB-7 admin audit log · NB-14 curriculum polish (lesson 1, dense weeks, early labs) · NB-17 mobile
  touch targets · NB-18 add missing tests · NB-11 consolidate content editors · NB-15 My Notes.

### Next 90 days (careful expansion)
- NB-10 consolidate progress/XP/mastery · NB-22 unify gating · NB-12 bundle split · NB-21 quiz
  explanations · begin **Service Desk Phase 1B** (only after NB-5 + NB-2).

### Long term (state prerequisite + measurable value each)
- More Service Desk scenarios · My Training ↔ Service Desk progression integration · richer reporting
  · more guided labs · **PostgreSQL** (only when SQLite triggers hit: multi-worker / >20–50
  concurrent / lock errors) · optional VM integration & AI assistance **only** with infra, budget,
  and eval/guardrail prerequisites — not because they sound impressive.

---

## 21. Final recommendation
**Launch to the five students.** Nexus is stable, secure, and pedagogically sound. Do the five
immediate-stabilization quick wins first (a day or two of work), then invest the next month in the
two real enablers — **admin monitoring** and **CI** — plus the **Service Desk end-to-end
walkthrough** before exposing Service Desk to students or starting Phase 1B. Resist premature
expansion (VMs, AI, Postgres); the platform's strength is its focused simplicity.

*Companion deliverables:* `NEXUS_FEATURE_DECISION_MATRIX.md`, `NEXUS_IMPLEMENTATION_BACKLOG.md`,
`NEXUS_CURRICULUM_AUDIT.md`, `NEXUS_NAVIGATION_PROPOSAL.md`, `NEXUS_REVIEW_EVIDENCE.md`, and the
per-phase reports in `phase-reports/`.
