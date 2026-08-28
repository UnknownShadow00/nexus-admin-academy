# Nexus — Navigation Proposal

**Date:** 2026-07-23 · Baseline `15a9410` · From live desktop (1440×1000) + mobile (375×812) review.

## Principles
Keep the 4-item student IA and 5-group admin IA (both are already good). Changes are **grouping,
naming, and de-duplication** — not new top-level tabs. Do not give each drill its own tab.

## Student navigation

### Current
```
Home
My Training  ┬ Weekly Plan (default)
             ├ All Course Content
             └ Quiz Library
Practice Library ▾ ┬ Support Tickets
                   ├ [Service Desk Lab]   (only when flag on)
                   ├ Guided Labs
                   ├ Networking Labs
                   ├ Capstones            (hidden until unlocked)
                   ├ Command Library
                   └ Terminal Practice
Progress
```

### Recommended
```
Home                     ← trim duplicated Weekly Roadmap; keep tiles + "what's next" + Daily Review
My Training  ┬ Weekly Plan (default)      ← unchanged (strongest surface)
             ├ All Course Content
             └ Quiz Library
Practice   ▾ ┬ Support work
             │   ├ Support Tickets
             │   └ Service Desk Lab       ← once student-side is validated
             ├ Hands-on labs
             │   ├ Guided Labs
             │   └ Networking Labs
             ├ Command Line               ← MERGE Command Library + Terminal Practice
             │   (reference sidebar + practice terminal in one page)
             └ Capstones                  (surface only when unlocked, as today)
Progress                 ← add a mastery/avg-score view distinct from coverage %
```

### What changes and why
| Change | Why (beginner usability) |
|---|---|
| Rename "Practice Library" → "Practice" | Shorter, less "catalog"; it's a place to practice, not browse a store. |
| Group the 6–7 dropdown items into 3–4 labeled clusters | 7 flat items overwhelm; clusters map to *kinds* of practice. |
| **Merge Command Library into Terminal Practice** ("Command Line") | They duplicate a command reference; one page = reference + sandbox. |
| Rename the CLI items for clarity | "Networking Labs" (structured/graded) vs "Terminal Practice/Command Line" (free practice) confuse beginners. |
| Trim Weekly Roadmap on Home | It repeats on My Training and Progress. |
| Keep Service Desk flag-gated in nav | Correct; add it to "Support work" once validated. |

**Nothing is removed** from the student experience; the reduction is in *navigational surface*.

## Admin navigation

### Current
```
Dashboard
Learning Content ▾ (Modules/Lessons & Quizzes, Weekly Training, Study Curriculum, Job Relevance Tags, ExamCompass Import)
Students
Assessments & Labs ▾ (Ticket Review, Service Desk Lab, Labs & VM Assignments, Capstones)
System ▾ (AI Usage & Costs)
```

### Recommended
```
Dashboard          ← add a cohort panel: each student's current week, % complete, last-active, at-risk flag
Students           ← add per-student drill-down (week-by-week completion, recent submissions, quiz scores by topic)
Learning Content ▾ ┬ Content Editor        ← consolidate/clearly delineate Module Manager + Curriculum Editor + Weekly Training
                   ├ Job Relevance Tags
                   └ ExamCompass Import
Assessments & Labs ▾ (Ticket Review, Service Desk Lab, Labs [rename until VM ships], Capstones)
System ▾ ┬ AI Usage & Costs
         └ Admin Audit Log                 ← NEW: action attribution (who did what, when)
```

### What changes and why
| Change | Why |
|---|---|
| Dashboard gains cohort monitoring | The biggest admin gap: admins can't currently see per-student "what to do / done / stuck / overdue". |
| Students gains a drill-down | Same gap at the individual level. |
| Consolidate 3 content editors | Module Manager + Curriculum Editor + Weekly Training overlap; confusing for a solo operator. |
| Rename "Labs & VM Assignments" → "Labs" | VM integration is deferred; the name implies a shipped feature. |
| Add Admin Audit Log under System | Single shared admin + no action log = no accountability. |

## Route migrations / redirects
- **Keep** existing redirects: `/learning-path → /training`, `/study-tracker → /training/content`,
  `/admin/review → /admin/ticket-review`. Working and correct.
- **New:** if Command Library merges into Terminal Practice, redirect `/commands → /terminal`
  (or host the reference within `/terminal`).
- **Remove (backend):** dead `GET /api/students/{id}/learning-path` (no caller).
- **Search:** filter results to respect lesson/week gating (currently leaks gated summaries).

## Mobile considerations
- Mobile IA is already solid: hamburger drawer, no horizontal overflow, stacked cards, scrollable
  sub-tab strips. Keep.
- **Fix small touch targets on All Course Content** (video-watch toggles/chips < 24 px) — the one
  mobile tapping hazard.
- Ensure any merged "Command Line" page keeps the terminal usable at 375 px.

## Features to remove from primary navigation
- None outright. The recommended structure **reduces the Practice dropdown from 6–7 flat items to
  3–4 clusters** and merges the two overlapping CLI reference surfaces — that is the whole change.
