# Phase 13 — Performance & Reliability

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** Frontend build analysis + LIVE network measurement as temp student.

## Frontend delivery
- **Code splitting: yes.** 17 `React.lazy` routes; admin pages ship as separate chunks
  (ModuleManager 38 kB, AdminServiceDeskPage 17.6 kB, BookmarkletPage 17.2 kB, etc.).
- **But the main chunk is large:** `index-*.js` **1,006 kB raw / 282 kB gzip** (Vite warns >500 kB).
  Student-facing pages + vendor libs are eager-loaded in the entry bundle; only admin/some heavy
  pages are lazy. 282 kB gzip is acceptable for a training app but trimmable.
  - *Fix:* manual vendor chunk (`react`, `react-dom`, router, markdown) + lazy-load the heavier
    student pages (Terminal, CLI labs already 12.9 kB split). Target entry < ~180 kB gzip.
- **CSS:** 64 kB / 10.8 kB gzip — fine. Build time 2.4s.

## Runtime request behavior (live, student home)
- **5 API calls, 788 ms, ZERO duplicate requests:** `/auth/me`, `/api/students/8/check-in`,
  `/api/students/8/stats`, `/api/training`, `/api/flashcards/due`. Lean and non-redundant — no
  request storms, no N+1 at the network layer.
- The `api.js` `request()` wrapper adds retries + backend warm-up, which is sensible given Render.

## Reliability primitives
- **ErrorBoundary** (`components/ErrorBoundary.jsx`) wired at `main.jsx` root.
- **Loading states** on ~15 pages (spinner/skeleton/isLoading).
- **Health endpoint:** `GET /health` → 200 `{ok:true, timestamp}` (note: `/api/health` is 404 — use
  `/health`). Good for uptime monitoring; make sure the monitor targets `/health`.

## Harmless warnings (do NOT "fix" by weakening security)
- **Cloudflare beacon CSP warning:** the strict `connect-src 'self'` intentionally blocks
  `static.cloudflareinsights.com/beacon.min.js`. Expected; **do not** relax CSP for analytics.
- **Unauthenticated `/auth/me` → 401:** expected behavior, not an error.

## Real (minor) issues
- **1 MB main bundle** (above) — split for faster first paint. P2.
- **Render cold start:** the login page states "first load can take up to 30 seconds while the
  backend wakes on Render." That's a **hosting choice** (free/idle-spindown tier) and a genuine
  first-visit UX hit; it also **contradicts the documented self-hosted systemd deployment**
  (reconcile in Phase 16). *Options:* a warm-ping/keep-alive, a paid always-on tier, or actually
  moving to the documented self-host. P2 (UX/infra).
- **`/service-desk` unavailable-state 404 console errors** (Phase 3/9) — reliability noise. P1-ish.

## Not observed (good)
- No duplicate requests, no obvious render thrash on the pages measured, no console errors beyond
  the known Cloudflare beacon. Images/videos are external (YouTube embeds via CSP frame-src) — no
  heavy local media pipeline.

## Priorities
- P2: split the entry bundle; address Render cold-start (keep-alive or self-host);
  point monitoring at `/health`.
- P1 (cross-ref): `/service-desk` 404 probe noise.
- Do not weaken CSP for the Cloudflare beacon.
