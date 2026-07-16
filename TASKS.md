# TASKS.md — Nexus Backlog

Source: full project audit 2026-06-11 (see `docs/vision-gap-review.md` for the earlier review).
Priority order. Pick the top unchecked item unless told otherwise. Reference lines may drift — verify before editing.

---

## P0 — Broken / data-risk (fix before anything else)

- [x] **Fix Guacamole client URL encoding** — done 2026-07-06 (`fix/p0-batch`): `_client_identifier` builds `base64("{id}\0c\0{datasource}")`, datasource configurable via `GUACAMOLE_DATASOURCE` (default `postgresql`).
- [x] **Stop handing students the Guacamole admin token** — done 2026-07-06 (`fix/p0-batch`): per-lab-run user `lab-run-{id}` with READ on only its connection; user deleted in submit teardown and admin idle cleanup.
- [x] **Make VM provisioning async** — done 2026-07-06 (`fix/p0-batch`): start returns 202, FastAPI BackgroundTask provisions, `LabRun.vm_status`/`guac_url` persisted (migration `c7d8e9f0a1b2`), `GET /api/labs/{id}/vm-status`, LabPage polls every 3s with failed state + retry.
- [x] **Return existing VM connection info on page refresh** — done 2026-07-06 (`fix/p0-batch`): LabPage checks `vm-status` on load for in-progress runs and restores the iframe from the persisted `guac_url`.
- [ ] **Verify Railway persistence** — uploads write to local disk (`labs.py`, `tickets.py`, `evidence.py`); Railway FS is ephemeral. Mount a Railway volume for `UPLOAD_DIR` or move to Supabase Storage. Confirm prod `DATABASE_URL` points at Supabase, not SQLite.
- [x] **Remove `seed_students()` from `main.py`** — done 2026-07-06 (`fix/p0-batch`). NOTE: purge of ghost rows from existing DBs still pending; `seed.py` also has its own `seed_students(db)` content seeder (different accounts, not removed).
- [x] **Make `ai_service` import-safe** — done 2026-07-06 (`fix/p0-batch`): model validation moved into `call_ai()` (`_validate_model_config`), raises `AIServiceError` at call time.
- [x] **Seed passwords from env** — done 2026-07-06 (`fix/p0-batch`): `scripts/seed_users.py` reads `SEED_PASSWORD_MENTOR1`/`SEED_PASSWORD_STUDENT1..5`, refuses to run listing any missing vars.

## P1 — Security / correctness

- [ ] **Fix `allow_admin_or_student` bearer bypass** — `admin_auth.py` accepts any `Authorization: Bearer <anything>` without decoding. Decode the JWT or require `get_current_student` on `/api/study-tracker/curriculum`.
- [x] **Fix multi-select grading** — done 2026-07-06 (`fix/p0-batch`): `_is_answer_correct` compares exact sorted sets for multi-select in both submit and review paths; regression test added.
- [ ] **Harden admin session** — token is unsalted deterministic `sha256(password)` with no server-side expiry; comparisons are non-constant-time `==`; auth logs leak secret lengths. Use a random/signed token, `secrets.compare_digest`, drop the length logging.
- [ ] **Evidence upload limits + ownership** — `labs.py` evidence and `evidence.py` have no file-size cap (tickets has 5MB); `evidence.py` lets any student attach evidence to any ticket_id. Add size cap + ownership check. Note `EvidenceArtifact.submission_id` means ticket_id for tickets but lab_run_id for labs — document or fix.
- [ ] **Per-attempt quiz history** — retakes overwrite the single `QuizAttempt` row; "attempts" list is fiction and speed-flag evidence can be laundered by a slow retake. Insert a new row per attempt.
- [ ] **Remove localStorage-driven mentor admin shell** — `AdminAccessGate.jsx` renders admin pages when client-writable `selected_profile.is_mentor` is true. Contradicts "mentor cannot access admin panel". Backend already blocks the APIs; clean up the gate.

## P2 — Lighter / cheaper

- [x] **Swap AI to local Ollama** — done 2026-07-16 (`fix/p0-batch`) — make the chat-completions base URL configurable in `ai_service.py` (`AI_BASE_URL`), point at Ollama's OpenAI-compatible endpoint over Tailscale. Keep budget/rate-limit/logging plumbing. Calibrate grading prompts against known-good writeups on the chosen local model.
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
