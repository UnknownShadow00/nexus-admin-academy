# Phase 3 — Student Navigation & Information Architecture

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** LIVE. Logged in as throwaway student `zz_review_tmp_...` (id 8). Swept all 12
student destinations at desktop **1440×1000** and mobile **375×812** (Playwright/Chromium).
Screenshots + console-error capture in session scratchpad. All routes returned HTTP 200.

## Primary navigation (as rendered)

`Home` · `My Training` · `Practice Library ▾` · `Progress` — exactly the four intended
top-level items. Practice Library dropdown: Support Tickets, Guided Labs, Networking Labs,
Capstones, Command Library, Terminal Practice (Service Desk Lab spliced in only when the
`serviceDeskAvailable` flag is on; Capstones hidden until `has_unlocked_capstones`).

## Per-destination findings

| Destination | Route | Renders | Purpose clear? | Notes |
|---|---|---|---|---|
| Home | `/` | ✅ | ✅ | Dashboard: "Begin Your IT Training" hero, XP/streak/quizzes/tickets tiles, Daily Review, Up Next. Overlaps the Weekly Roadmap shown on My Training + Progress. |
| My Training | `/training` | ✅ | ✅ | **Strongest page.** Sub-tabs Weekly Plan / All Course Content / Quiz Library. Current-week hero with next action + Start Training; locked-week roadmap with explicit prerequisites and time estimates. |
| All Course Content | `/training/content` | ✅ | ✅ | CompTIA A+ video catalog by exam domain, job-relevance tags (Job Critical/Know It/Awareness), per-video Take Quiz, in-page search+filter. A parallel "browse everything" view of the same videos the Weekly Plan sequences. |
| Quiz Library | `/quizzes` | ✅ | ✅ | Reachable as a My Training sub-tab; not a primary nav item. Empty-state for fresh student. |
| Progress | `/progress` | ✅ | ✅ | Comprehensive: overall completion, per-type tiles (Videos 0/137, Quizzes 0/28, Required Practice 0/29, Guided Labs 0/5, Tickets 0/48, **Weeks 0/25**), Rank Progress, Capstone Readiness, Weekly Roadmap. |
| Support Tickets | `/tickets` | ✅ | ⚠ | Empty-state ("Available Tickets"). Distinction vs Service Desk not explained here → Phase 9. |
| Guided Labs | `/labs` | ✅ | ✅ | Empty-state ("Lab Exercises"). |
| Networking Labs | `/cli-labs` | ✅ | ⚠ | Naming overlaps Terminal Practice/Command Library (see below). |
| Capstones | `/capstones` | ✅ | ✅ | Hidden from nav until unlocked; direct route renders empty-state gracefully. |
| Command Library | `/commands` | ✅ | ✅ | Real content (reference list). |
| Terminal Practice | `/terminal` | ✅ | ⚠ | Real content; name overlaps the other two CLI destinations. |
| Service Desk Lab | `/service-desk` | ⚠ | n/a | For a normal new student it is **flag/beta-gated**: page shows "Service Desk Lab is unavailable" + "Return to Nexus". Graceful, BUT it fires **4× 404 console errors** on the availability probe. Not in this student's nav. Needs beta enrollment to review (Phase 9). |

Console errors: none anywhere except `/service-desk` (the 404 probes) and the ubiquitous,
known-harmless Cloudflare beacon CSP warning.

## Answers to the 12 questions

1. **Distinct primary purposes?** Yes — Home (dashboard), My Training (guided path), Practice
   Library (drills), Progress (metrics). No redundant top-level tab.
2. **My Training vs Practice Library obvious?** Mostly. My Training = sequenced weekly journey;
   Practice Library = standalone drills. Reasonable, though Practice Library's breadth blurs it.
3. **Support Tickets vs Service Desk Lab obvious?** **No** — both are "simulated support," names
   don't disambiguate, and Service Desk is gated-off for normal students. → Phase 9.
4. **Too many secondary destinations?** Somewhat. Practice Library holds 6–7 items, including a
   **CLI trio** (Networking Labs, Command Library, Terminal Practice) whose names beginners will
   conflate, plus two lab types (Guided vs Networking).
5. **Same content through different pages?** The **Weekly Roadmap** repeats on Home, My Training,
   and Progress. The A+ video set appears both as Weekly Plan and All Course Content (by design).
6. **Can a beginner tell what to do next?** **Yes, strongly.** Home hero "Start Training",
   My Training "Next: Course Lesson — …", Progress "Continue Training" all point to the same next step.
7. **Home = useful dashboard or duplicate?** Useful (stat tiles, Daily Review, Up Next) but its
   Weekly Roadmap block duplicates My Training. Trim overlap rather than remove Home.
8. **Progress meaningful?** Yes — accurate, consistent counts; rank + capstone readiness.
9. **Locked activities understandable?** Yes — "🔒 Locked" + "Complete Week N — <title> first."
10. **Back/refresh/direct links/mobile consistent?** Yes — every route works via direct URL and
    reload; mobile uses a hamburger drawer; retired routes redirect (`/learning-path→/training`,
    `/study-tracker→/training/content`).
11. **Dead links / misleading cards / unreachable routes?** None found for students. Gated pages
    degrade gracefully (Service Desk "unavailable", Capstones hidden-until-unlocked).
12. **Retired features still referenced?** **No** — global search for "learning path" returns
    empty; no stale Learning Path links in nav/search. Retired routes 301-style redirect.

## Proposed student navigation

**Current:** Home · My Training (Weekly Plan / All Course Content / Quiz Library) · Practice
Library ▾ (Support Tickets, [Service Desk Lab], Guided Labs, Networking Labs, Capstones,
Command Library, Terminal Practice) · Progress.

**Recommended (keep 4 top-level items; reduce dropdown sprawl + fix CLI naming):**
- **Home** — trim the duplicated Weekly Roadmap; keep tiles + "what's next" + Daily Review.
- **My Training** — unchanged (Weekly Plan default; All Course Content; Quiz Library).
- **Practice** (rename from "Practice Library" — shorter, less "catalog"-y), grouped:
  - *Support work:* Support Tickets, Service Desk Lab (once ready)
  - *Hands-on labs:* Guided Labs, Networking Labs
  - *Command line:* Command Library (reference) + Terminal Practice (drill) — **rename** so the
    distinction is obvious to a beginner (e.g. "Command Reference" vs "Terminal Practice").
  - Capstones (surface only when unlocked, as today).
- **Progress** — unchanged.

**What moves / changes:** nothing leaves; the change is grouping the 6–7 Practice items into 3–4
labeled clusters and renaming the CLI trio for clarity. **Do not** give each drill its own top-level
tab. Reconcile Support Tickets vs Service Desk naming after Phase 9.

## Strengths
Clean 4-item IA; excellent guided "next step"; graceful empty/locked/unavailable states;
consistent cross-page metrics; working search with no retired-feature leakage; solid mobile.

## Issues to carry forward
- P2/UX: Practice Library breadth + confusable CLI-trio names.
- P2/UX: Weekly Roadmap duplicated across Home/My Training/Progress.
- P1-candidate: `/service-desk` emits 404 console errors in its unavailable state (verify in
  Phase 9/13 whether the probe should 200 with `{available:false}`).
- Cross-ref: Support Tickets vs Service Desk clarity → Phase 9.
