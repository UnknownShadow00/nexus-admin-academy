# Phase 8 — Practice Library & Labs

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** LIVE as temp student — inventoried each type via API and rendered the interactive ones.

## Inventory (live)
| Type | Route / API | Count | Completion tracked? | Notes |
|---|---|---|---|---|
| Guided Labs | `/labs` · `/api/labs` | **5** | Yes (0/5) | e.g., "Hardware Component Identification". |
| Networking Labs | `/cli-labs` · `/api/cli-labs` | **48** | **Yes (objectives + 0/48)** | Cisco IOS simulator; 3 compartments (Meet the CLI 18, Network Foundations 7, Switching 23). |
| Command Library | `/commands` · `/api/commands` | **50** | No (reference) | Static command reference (lsof, dig, …). |
| Terminal Practice | `/terminal` | sandbox | **No** | Free-form simulated PowerShell terminal + command-reference sidebar; "Copy session". |
| Support Tickets | `/tickets` · `/api/tickets` | **48** | Yes (passed) | AI-scored + mentor review; week-gated (fresh student sees none available). |
| Service Desk Lab | `/service-desk` | 5 scenarios | Yes | Flag/beta-gated for students → Phase 9. |
| Capstones | `/capstones` · `/api/capstones` | 3 (0 visible) | Yes | Gated until unlocked; fresh student sees 0. |

## Per-type assessment

**Networking Labs — the standout.** Rendered "Read the Switch Map" (Beginner, 7 min): scenario,
a working Cisco IOS simulator (`Switch>` prompt), Objectives (0/2, checkable), Topology panel
(Switch + PC-A/B/C with ports/VLANs), interface up/down states, contextual hint, Restart,
Progress ("In progress"), and a "Next:" chain. **Beginner-appropriate, well-scaffolded,
authoritative completion, purely frontend (no VM infra needed).** Ready for students.

**Guided Labs (5).** Small set; each is an evidence-based lab (Hardware ID, etc.). Works;
completion recorded. Thin coverage vs. 137 videos (Phase 5 point) — more early-week labs would help.

**Command Library (50).** Clean reference. Useful, but **overlaps Terminal Practice's sidebar**,
which lists the same kind of command reference.

**Terminal Practice.** Ungraded PowerShell sandbox for free play; **no completion/progress**.
Fine as a scratchpad, but it neither teaches a specific skill authoritatively nor records
anything — and its command sidebar duplicates Command Library.

**Support Tickets (48).** Real graded practice (AI scoring + mentor review), week-gated. Deep-dived
vs. Service Desk in Phase 9. Note the **dual-surfacing**: tickets and guided labs appear both as
My-Training week activities *and* as standalone Practice Library destinations.

**Capstones (3).** Gated milestones (W4/W8/W24); appropriately hidden until unlocked.

## Key issues

1. **CLI-trio overlap & naming (P2, from Phase 3).** Three command-line destinations —
   Networking Labs (structured/graded), Terminal Practice (ungraded sandbox), Command Library
   (reference) — with beginner-confusable names. **Terminal Practice + Command Library overlap
   most** (both are "here are commands to type"). Recommend: fold Command Library into Terminal
   Practice (one "Command Line" area: reference sidebar + practice terminal), and rename so
   "structured labs" vs "free practice" is obvious.
2. **Dual-surfacing of tickets/labs (P2/UX).** The same ticket/lab is reachable via My Training
   (in-week, authoritative for progression) and via Practice Library (standalone). Keep both, but
   make clear which drives weekly progress (My Training) vs. which is "extra reps" (Practice Library).
3. **Completion authority varies.** Networking Labs / Guided Labs / Tickets / Capstones record
   completion; Terminal Practice records nothing (by design). That's acceptable if the IA labels
   sandbox vs. graded — currently it doesn't.

## Does the student need catalog features?
Categories/difficulty/search **already exist where they matter** (Networking Labs compartments +
Beginner tags; Tickets difficulty/week/category; Terminal command categories). Per the plan's
guardrail, **do not** expand into an enterprise LMS catalog. The real need is **clarity/grouping
and naming**, not more filters. A light "recommended next practice" tied to the current week would
add value without bloat.

## Belongs in My Training vs Practice Library?
- **My Training** should remain the authoritative, sequenced home for the week's required
  tickets/labs/quizzes.
- **Practice Library** should be the "extra reps / browse" surface (Networking Labs, Command
  Line, standalone tickets/labs, Capstones). Current split is basically right; just clarify labels.

## Readiness
Guided Labs, Networking Labs, Command Library, Terminal Practice, Support Tickets, Capstones are
**functional and beginner-appropriate today**. Service Desk student-side readiness → Phase 9.

## Priorities
- P2/UX: merge/relabel the CLI trio; clarify sandbox-vs-graded; clarify dual-surfaced tickets/labs.
- P2/curriculum: add a few early-week guided labs (watch-vs-do balance).
- P3: optional "recommended practice for this week."
