
## Go-live Day-1 + grader/smoke session update (2026-07-17)
DONE (verified on .101, see tasks/loop-log.md):
- [x] Day 1 of NEXUS_GO_LIVE_CHECKLIST.md — 24-week build deployed, fresh DB migrated+seeded, 98/98 tests, frontend built, service restarted, admin login + 25 modules verified
- [x] Real-AI grader calibration RUN against live Ollama (deepseek-r1:32b): **NEEDS TUNING** — strong=10 OK, weak=2 OK, unsafe=1 OK, malicious=1 OK, incomplete=6 (expected ≤5; its verification anchor correctly 0). One band miss; prompt/model tweak pending.
- [x] AI grader JSON parsing fixed: `extract_json_payload()` restored in ai_service (json_mode), `_strip_think_tags` belt-and-suspenders in ticket_grader — Ollama ignores `response_format: json_object`
- [x] Calibration script: 25s spacing between fixtures + self-reset of user-0 rate counters (8/day cap made re-runs impossible)
- [x] bcrypt pinned to 4.0.1 (passlib 1.7.4 incompatible with bcrypt≥4.1)
- [x] P0 "seed_students() phantom accounts" — REGRESSED in the 24-week pack's seed.py (shipped admin/admin123, alex/alex123... on every deploy); removed again, ghost rows purged, reseed verified clean
- [x] Quiz retake 500 fixed: `first_attempt_xp=None` vs NOT NULL DB column (migration 0002 vs model drift) — retakes write 0
- [x] NEW `PUT /api/admin/submissions/{id}/flag` + `/resolve-flag` — no endpoint could create the open-flag state `no_unresolved_flags` gates check for
- [x] Ticket submit response now includes `anchors`
- [x] Day-4 smoke test automated: `backend/scripts/day4_smoke_test.py` — **8/8 PASS** (login, week-plan, lesson→done, quiz retake/XP-once, hint cost+substitution, live AI grade 9/10, flag→gate block→resolve, evidence 413/200); smoke residue purged from DB

STILL OPEN from this session:
- [ ] Grader calibration "incomplete" fixture: final=6 vs expected ≤5 — tune prompt or EXPECTATIONS band, re-run until PASSED (checklist Day 3 blocker for AI grading trust)
- [ ] Nothing serves frontend/dist on .101 (backend :8000 only) — decide nginx vs compose frontend container before students need the UI from LAN

## Phase 1 status update (2026-07-10)
DONE (verified, tested — see tasks/loop-log.md for evidence):
- P0 #6 (app boots without AI env) and #7 (phantom seed removed + purge script)
- P1: multi-select set grading; per-attempt quiz history (uq_student_quiz dropped); study-tracker "Bearer anything" bypass closed; weak deterministic admin session replaced with random expiring sessions; evidence ownership + 10MB size cap (IDOR closed)
- Ollama/OpenAI-compatible AI config (AI_BASE_URL/AI_MODEL/AI_API_KEY) + calibration script (NOT yet run against live AI)
- Six-role ladder + Gate 1 & Gate 2 seeded, enforced, pass/fail tested
- Weeks 1-8 content fully seeded: 9 modules, 24 lessons, 9 quizzes/71 questions, 26 tickets incl. Simulations 1 & 2 with hints/anchors/parameters
- "This Week" dashboard (API + panel), ticket hint UI, drift fix (quizzes.status)

STILL OPEN (unchanged priority):
- Proxmox/Guacamole P0 set (encoding, admin token, sync provisioning, session recovery) — still blocks AUTO-VM only; Weeks 1-8 do not depend on it
- Real-AI grader calibration run (needs the Ollama VM)
- Weeks 9-24 content (Phase C onward)

# TASKS.md — Nexus Backlog

Source: full project audit 2026-06-11 (see `docs/vision-gap-review.md` for the earlier review).
Priority order. Pick the top unchecked item unless told otherwise. Reference lines may drift — verify before editing.

---

## P0 — Broken / data-risk (fix before anything else)

- [ ] **Fix Guacamole client URL encoding** — `guacamole_service.py:get_token_url` builds `base64("c/{conn_id}")`; Guacamole expects `base64("{identifier}\0c\0{datasource}")` (NUL-separated, datasource e.g. `postgresql`). Iframe is broken until this is fixed.
- [ ] **Stop handing students the Guacamole admin token** — `get_token_url` authenticates as `GUACAMOLE_ADMIN_USER` and embeds that token in the student URL. Create a per-student (or per-assignment) Guacamole user via REST, grant it only its own connection, return that user's token.
- [ ] **Make VM provisioning async** — `labs.py:_provision_vm` blocks the worker up to 120s+ (`proxmox_service.get_vm_ip` poll) vs the frontend's 30s axios timeout. Return `202 provisioning` immediately, move clone/start/IP-wait to a background task, add `GET /api/labs/{id}/vm-status` for the frontend to poll, render iframe when `running`.
- [ ] **Return existing VM connection info from `GET /labs/{id}`** — `guacUrl` lives only in React state (`LabPage.jsx`); page refresh during `in_progress` locks the student out of their running VM.
- [ ] **Verify Railway persistence** — uploads write to local disk (`labs.py`, `tickets.py`, `evidence.py`); Railway FS is ephemeral. Mount a Railway volume for `UPLOAD_DIR` or move to Supabase Storage. Confirm prod `DATABASE_URL` points at Supabase, not SQLite.
- [ ] **Remove `seed_students()` from `main.py`** — creates 5 phantom students (Alex/Jordan/Sam/Taylor/Riley, no credentials) on empty DB; pollutes leaderboard/squad/cohort stats. `scripts/seed_users.py` is the only seeder. Purge ghost rows from existing DBs.
- [ ] **Make `ai_service` import-safe** — module-level `raise` when `OPENROUTER_MODEL` unset kills app boot (import chain: main → tickets → ticket_grader → ai_service). Move the check into `call_ai()`.

## P1 — Security / correctness

- [ ] **Fix `allow_admin_or_student` bearer bypass** — `admin_auth.py` accepts any `Authorization: Bearer <anything>` without decoding. Decode the JWT or require `get_current_student` on `/api/study-tracker/curriculum`.
- [ ] **Fix multi-select grading** — `quizzes.py:submit_quiz`: single-letter answer to a multi-select question is graded `in correct_letters` → full credit for partial answer. Always compare as sets when `is_multi_select`.
- [ ] **Harden admin session** — token is unsalted deterministic `sha256(password)` with no server-side expiry; comparisons are non-constant-time `==`; auth logs leak secret lengths. Use a random/signed token, `secrets.compare_digest`, drop the length logging.
- [ ] **Evidence upload limits + ownership** — `labs.py` evidence and `evidence.py` have no file-size cap (tickets has 5MB); `evidence.py` lets any student attach evidence to any ticket_id. Add size cap + ownership check. Note `EvidenceArtifact.submission_id` means ticket_id for tickets but lab_run_id for labs — document or fix.
- [ ] **Per-attempt quiz history** — retakes overwrite the single `QuizAttempt` row; "attempts" list is fiction and speed-flag evidence can be laundered by a slow retake. Insert a new row per attempt.
- [ ] **Remove localStorage-driven mentor admin shell** — `AdminAccessGate.jsx` renders admin pages when client-writable `selected_profile.is_mentor` is true. Contradicts "mentor cannot access admin panel". Backend already blocks the APIs; clean up the gate.

## P2 — Lighter / cheaper

- [ ] **Swap AI to local Ollama** — make the chat-completions base URL configurable in `ai_service.py` (`AI_BASE_URL`), point at Ollama's OpenAI-compatible endpoint over Tailscale. Keep budget/rate-limit/logging plumbing. Calibrate grading prompts against known-good writeups on the chosen local model.
- [ ] **Move Playwright out of prod requirements** — only used for occasional admin scraping; bloats the Railway image. `requirements-dev.txt` or run locally.
- [ ] **Linked clones** — `proxmox_service.clone_template` uses `full=1`; use linked clones for seconds-fast, disk-cheap provisioning.
- [ ] **Lazy-load admin routes** — `React.lazy` the 11 admin pages; kills the >500kB bundle warning.
- [ ] **`datetime.utcnow()` sweep** — rate_limiter, activity_service, admin_content, students, tickets; replace with `datetime.now(timezone.utc)` before Supabase cutover. Also `ai_service._today_window()` uses local time for the daily budget window.

## P3 — Maintainability / cleanup

- [ ] Pydantic schemas for admin CRUD (`admin_content.py` takes raw dicts everywhere)
- [ ] Replace `python-jose` with PyJWT; delete the fallback crypto shims in `auth_service.py`
- [ ] Delete dead code: `SelectProfile.jsx`, `components/Dashboard.jsx`, `QuizList.jsx`, `Leaderboard.jsx`, `tmp_bookmarklet.js`
- [ ] Fix hardcoded `week_number = 1` in `students.py` stats
- [ ] Prune old `AIRateLimit` rows (unbounded growth)
- [ ] Unify on `httpx` (guacamole_service still uses `requests`)
- [ ] Weekly mentor digest: `/api/admin/weekly-summary` + scheduled Discord post (n8n or GitHub Actions)

## P4 — Sidecar deployment (on Proxmox, outside this repo)

Deploy in teaching-value order; document config in CLAUDE.md when done.
- [ ] Apache Guacamole (required for VM labs) + real end-to-end lab smoke test
- [ ] Scheduler calls `DELETE /api/admin/vms/cleanup?idle_hours=2` on cadence
- [ ] GLPI (student work-ticketing; consider Nexus↔GLPI scenario sync later)
- [ ] Gitea (runbook wikis — capstone portfolio artifact)
- [ ] n8n (cleanup schedule, Discord bridge, weekly reports)
- [ ] Netdata / Uptime Kuma — as student lab content, not maintained infra

## Content backlog (highest job-readiness value)

### CLI lesson packs (SwitchLab courses — source MD in `references/lesson-drafts/`)

- [x] **Step framework** — 6 step types (explanation, multiple-choice, observe, forward-decision, hex-input, frame-builder), StepPanel + widgets, validator rules (2026-07-02)
- [x] **Engine: ping/ARP/MAC table** — PC ping with ARP transcript, dynamic MAC learning, `show mac address-table`, static MAC entries (2026-07-02)
- [x] **Learn Network Foundations pack** — 7 labs converted from `learn-network-foundations.md`, registered frontend+backend seed (2026-07-02)
- [x] **CLI Labs page: collapsible topic sections** — compartments collapsed by default with per-topic progress (2026-07-02)
- [ ] **Wave 2 — Learn Switching pack** (44 labs from `learn-switching.md`): engine needs trunking (802.1Q, native VLAN, allowed list), STP/Rapid PVST+ (root election, PortFast, BPDU Guard), EtherChannel/LACP, 2-switch topologies. Convert per section A–H; exams have no hints.
- [ ] **Wave 3 — Learn Routing pack** (23 labs from `learn-routing.md`): engine needs router device type, IPv4/VLSM host config, SVIs, static/default routes, OSPF, IPv6 (statics, SLAAC, EUI-64), L3 EtherChannel.

- [ ] **Active Directory lab template family** — Windows Server (AD DS) + domain-joined client: password resets, lockouts, group membership, GPO, share access. Biggest help-desk skill gap in current content.
- [ ] Parametrized ticket variants per student (reuse `break_script`-style JSON) — anti-answer-sharing
- [ ] Escalation-type tickets (correct answer = clean escalation note)
- [ ] Grade `commands_used` field; occasional "write the email to the user" communication grading
- [ ] Anki deck export of missed questions (`genanki`)

---

## Done (audit-confirmed 2026-06-11)

- [x] P2 quiz speed-flag admin view (`admin_content.py` flagged endpoint + QuizEditorPage)
- [x] P3 Proxmox/Guacamole application layer (models, services, lab start/submit wiring, idle cleanup endpoint) — code complete, has P0 bugs above, never smoke-tested against real infra
- [x] FSRS-style flashcards (SM-2 algorithm), lesson notes, quiz timing capture
