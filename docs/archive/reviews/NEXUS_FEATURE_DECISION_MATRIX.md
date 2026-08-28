# Nexus — Feature-by-Feature Decision Matrix

**Date:** 2026-07-23 · Baseline `15a9410` · Derived from live + source review (Phases 1–16).
Classifications: **Keep / Improve / Merge / Rename / Hide / Remove later / Postpone / Investigate**.
Effort: XS/S/M/L/XL. Priority: P0–P3 / Future.

## Student-facing features

| Feature | Current purpose | Quality | Student value | Admin value | Overlap | Recommendation | Reason | Priority | Effort | Dependencies |
|---|---|---|---|---|---|---|---|---|---|---|
| Home dashboard | Landing + next step + tiles + Daily Review | Good | High | Low | Weekly Roadmap dup on Training/Progress | **Improve** | Remove duplicated roadmap; keep tiles/next-step | P2 | S | — |
| My Training (Weekly Plan) | Sequenced 25-week guided path | Excellent | High | Med | Authoritative home for weekly work | **Keep** | Strongest feature; clear next-step, gating | P3 | — | — |
| All Course Content | A+ video catalog by domain | Good | Med | Low | Same videos as Weekly Plan | **Keep** | Useful "browse/review" view; sub-tab of Training | P3 | — | — |
| Quiz Library | Browse/take quizzes | Good | Med | Low | Sub-tab of My Training | **Keep** | Already consolidated under Learn | P3 | — | — |
| Progress | Completion/rank/capstone metrics | Good | High | Med | Roadmap dup | **Improve** | Separate coverage vs mastery; trim roadmap dup | P2 | S | assessment metrics |
| Lessons | Text reading companions | Good (1 stub) | High | Med | — | **Improve** | Surface authored `outcomes`; author lesson 1; add notes index | P1 | S | outcomes serialization |
| Notes | Per-lesson auto-save notes | OK | Med | Low | — | **Improve** | Add central "My Notes" view (hard to find later) | P2 | S | — |
| Support Tickets | AI-graded ITIL writeups | Good | High | High | Service Desk (naming) | **Keep** | Teaches written comms/diagnosis; distinct from SD | P3 | — | AI service |
| Service Desk Lab | Deterministic tier-1 sims | Strong (1A) | High | High | Support Tickets (naming) | **Keep** | Excellent design; teaches safe procedure | P1 (finish rollout) | M | flag, e2e walkthrough |
| Guided Labs | Evidence-based hands-on labs | OK (only 5) | High | Med | Networking Labs (label) | **Improve** | Add early-week labs (watch-vs-do balance) | P2 | M | content authoring |
| Networking Labs (CLI) | 48 Cisco IOS sim labs | Excellent | High | Med | Terminal/Command (naming) | **Keep + Rename** | Standout; clarify vs the other CLI areas | P3 | S | — |
| Command Library | 50-command reference | OK | Med | Low | Terminal Practice sidebar | **Merge** | Fold into Terminal Practice (dup reference) | P2 | S | — |
| Terminal Practice | Ungraded PowerShell sandbox | OK | Med | Low | Command Library | **Merge/Rename** | Combine with Command Library as one "Command Line" area | P2 | S | — |
| Capstones | Gated milestone projects | OK | High | Med | — | **Keep** | Role/progression-gated; appropriate | P3 | — | progression |
| Global Search | Cross-content search | Good | Med | Low | — | **Improve** | Respect lesson gating (leaks gated summaries) | P3 | S | gating |
| Flashcards / Daily Review | FSRS spaced repetition | Good | High | Low | — | **Keep** | Strong learning loop from wrong answers | P3 | — | — |
| Orientation (Week 0) | Onboarding | Good | High | Med | — | **Keep** | Welcoming, gentle; fix "24-week" copy | P3 | XS | — |

## Admin-facing features

| Feature | Current purpose | Quality | Student value | Admin value | Overlap | Recommendation | Reason | Priority | Effort | Dependencies |
|---|---|---|---|---|---|---|---|---|---|---|
| Admin Dashboard | Ops home + content widgets | OK | — | Med | — | **Improve** | Add cohort monitoring panel (current week/%/at-risk) | P1 | M | student stats |
| Student management | Roster + CRUD | OK | — | High | — | **Improve** | Add per-student drill-down (week/completion/struggling) | P1 | M | progress data |
| Module Manager | Edit modules/lessons/quizzes | Good | — | High | Curriculum/Weekly Training | **Merge/Clarify** | 3 overlapping content editors | P2 | M | — |
| Curriculum Editor | Edit study curriculum | Good (heavy) | — | High | Module/Weekly Training | **Merge/Clarify** | Consolidate or delineate roles | P2 | M | — |
| Weekly Training | Curriculum weeks + validation | Excellent | — | High | Module/Curriculum | **Keep** | "References valid", video mapping — best content tool | P3 | — | — |
| Job Relevance Tags | Tag job-critical content | OK | — | Med | — | **Keep** | Small utility under Learning Content | P3 | — | — |
| ExamCompass Import | Bookmarklet quiz import | OK | — | Med | — | **Keep** | Dev/admin content tool | P3 | — | — |
| Ticket Review | Grade queue | Good | — | High | — | **Keep** | Clean master-detail | P3 | — | — |
| Service Desk admin | Scenarios/health/replay/grades/beta | Strong | — | High | — | **Keep** | Well-built; health monitoring | P3 | — | — |
| Labs & VM Assignments | Lab templates + VM (deferred) | Partial | — | Med | — | **Rename/Investigate** | Rename until VM ships; VM code dormant | P2 | S | VM deferred |
| Capstone admin | Templates | OK | — | Med | — | **Keep** | — | P3 | — | — |
| AI Usage & Costs | AI cost dashboard | OK | — | Med | — | **Keep** | Useful if AI grading used | P3 | — | AI service |
| Admin audit log | (missing) | — | — | High | — | **Investigate/Add** | No action attribution; single shared admin | P2 | M | — |

## Platform / infrastructure

| Feature | Purpose | Quality | Recommendation | Reason | Priority | Effort |
|---|---|---|---|---|---|---|
| Auth (student JWT / admin session) | AuthN/Z | Strong | **Keep + Improve** | Add login rate-limit/lockout | P2 | S |
| CSP/CSRF/headers | Security | Strong | **Keep** | Strict CSP; don't weaken for beacon | P3 | — |
| SQLite | Data store | Good | **Improve** | Add WAL + busy_timeout; Postgres only when triggered | P2 | XS |
| Migrations/seeds | Schema/content | Strong | **Keep** | Idempotent, reversible (5 stub downgrades noted) | P3 | — |
| CI pipeline | (missing) | — | **Add** | No `.github/workflows`; tests run manually | P1 | M |
| Deployment docs | Runbook | Good but stale | **Improve** | Reconcile self-host docs vs Cloudflare/Render reality | P2 | S |
| Frontend bundle | Delivery | OK | **Improve** | Split 1MB entry bundle | P2 | S |

## Deferred (do NOT build now — state prerequisite + value required)

| Feature | Recommendation | Reason |
|---|---|---|
| Proxmox/Guacamole/VM integration | **Postpone** | Dormant code exists; needs infra + clear value; not for 5 students |
| Real AD integration | **Postpone** | Service Desk simulates this well enough for tier-1 training |
| Calls / voicemail | **Postpone** | Out of scope for the program |
| AI expansion | **Postpone** | Keep manual fallback; only expand with budget/eval controls |
| PostgreSQL migration | **Postpone** | Only when SQLite triggers hit (multi-worker / >20–50 concurrent / lock errors) |
| Service Desk Phase 1B | **Postpone** | Start only after end-to-end flag-on walkthrough + 1A must-fixes |

## Highest-priority actions (from this matrix)
1. **P1** Surface lesson `outcomes` (hidden objectives).
2. **P1** Fix `/service-desk` unavailable-state 404s.
3. **P1** Add admin cohort monitoring + per-student drill-down.
4. **P1** Add CI pipeline.
5. **P2** Merge CLI trio (Terminal + Command Library); clarify Support Tickets vs Service Desk.
