# Phase 6 — Lessons & Content Authoring

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** LIVE lesson fetches as temp student + source + read-only query of the seeded DB.

## Lesson system shape
- **64 lessons, all `status="published"`** (no drafts in use). Belong to legacy `Module`s
  (MOD-xxx). My Training references lessons by `content_ref` (e.g., Week 0 → lesson 64), so
  lessons are **live content**, not dead. Content sanitization is **safe**: `LessonPage` renders
  `summary` as **plain text** (`whitespace-pre-line`, no `dangerouslySetInnerHTML`); only
  `react-markdown` (safe-by-default) is used, for ticket previews.
- Data model (`models/learning.py`): Lesson has `title, video_url, summary, outcomes (JSON list),
  estimated_minutes, required_notes_template, status`.

## Content quality — better than expected
- Summary length: **min 51, median 1532, max 2704 chars.** Only **one stub lesson**: id 1
  **"CompTIA 6-Step Process" = 51 chars** ("Define, theorize, test, plan, verify, and document.")
  — yet it's a **required 45-min Week 0 lesson**. Needs real authoring.
- **`outcomes` (learning objectives) populated for 63/64 lessons** in the DB — the content *is*
  authored.

## The headline gap: authored objectives are never shown
The lesson GET endpoint (`lesson_notes.py::get_lesson`) returns only
`id, title, summary, video_url, module_code, module_title, is_orientation` — **it omits
`outcomes`.** `LessonPage.jsx` renders title + summary + notes, **no objectives block.** So every
lesson's learning objectives exist in data but are **invisible to students**. This is a
high-value, low-risk fix: serialize `outcomes` and render an "In this lesson you'll learn…" list.

## Gating & routing
- Direct lesson pages (`/lessons/:id`) are **access-gated**: `get_lesson` enforces
  `check_module_unlock(...)` → **403** for locked lessons (verified: lesson 22 → 403 for my fresh
  student, page rendered blocked). Good ownership/gating.
- **Dual gating systems:** lesson pages gate by **module unlock** (legacy `Module` graph) while
  My Training gates by **week**. Two independent unlock computations for the same content →
  risk of divergence (a lesson week-unlocked but module-locked, or vice versa). Consolidate → Phase 12.
- **Search bypasses lesson gating:** `/api/search/global` returned lesson 22's **full summary**
  to the same student who gets 403 on the lesson page. Content isn't secret, but it defeats the
  progression gate. Low severity → Phase 10.

## Notes
- One free-text note per lesson (`PUT /api/lessons/{id}/notes`), **auto-saves**, orientation
  lesson shows a reflective prompt ("Where will you look when you are unsure what comes next?").
  Useful in-context.
- **No central "My Notes" view** — notes live only on each lesson page, so they're **hard to find
  later**. Adding a notes index would materially help review/study.

## Dead / dormant code
- **Backend learning-path API is dead:** `GET /api/students/{id}/learning-path`
  (`students.py:429`) still exists and works, but **no frontend caller** — the frontend only
  redirects `/learning-path → /training`. Safe (auth+ownership guarded) but removable → Phase 12.
- **`lesson.video_url` is null for all 64 lessons** → `LessonPage`'s YouTube-embed path
  (`getYouTubeEmbedUrl(lesson.video_url)`) never fires. Videos live as separate curriculum
  activities, not embedded in lessons. Minor dead UI branch.

## Answers to the plan's lesson questions
- **Useful or placeholders?** Overwhelmingly useful (63/64 substantial). One stub (lesson 1).
- **Short reading companions to videos?** Effectively yes — lessons are text; videos are separate.
  There is **no 1:1 "each video has a lesson summary"** relationship; some weeks pair them loosely.
- **Objectives / vocabulary / examples / review checks?** Objectives are authored but **hidden**;
  vocabulary/worked-examples/review-checks are not a consistent structural part of the template.
- **Notes findable later?** No central index (see above).
- **Admin editor reliable?** Module Manager + Curriculum Editor exist (Phase 4); content validates.
- **Unreachable / missing-lesson references?** Curriculum validation `valid:true`; no broken refs found.
- **Backend learning-path API dead?** Yes (see above).

## Recommended standard lesson template (practical to maintain)
Adopt one structure, backed by fields that already exist:
1. **Objective** — surface `outcomes` (already authored). *(fix the serialization gap)*
2. **Why it matters** — 1–2 sentences (lead of `summary`).
3. **Key terms** — short glossary list.
4. **Main explanation** — body of `summary`.
5. **Worked example** — one concrete scenario.
6. **Common mistakes** — 2–3 bullets.
7. **Practice task** — link to the week's ticket/lab.
8. **Quick knowledge check** — link the paired quiz.
9. **Related video/quiz/lab** — cross-links.
10. **Notes prompt** — reuse `required_notes_template` (already in model, currently mostly unused).

## Priorities
- **P1 (easy win):** serialize + render lesson `outcomes` (objectives authored but hidden).
- P2: author lesson 1 (CompTIA 6-Step stub); add a central "My Notes" view.
- P2: consolidate module-unlock vs week-gate dual gating.
- P3: remove dead learning-path API + dead video-embed branch.
- Low/Phase 10: search leaks gated lesson summaries.
