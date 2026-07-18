# NEXUS GO-LIVE CHECKLIST — Day-by-Day

Format: small confirmatory steps. Each ☐ has a **VERIFY** line — paste that
output back to Claude/Claude Code if anything looks off before moving on.
Don't skip verifies; they're the difference between "deployed" and "hoping."

---

## DAY 1 — Deploy the new repo to .101 (nexus-services)

**Goal: the complete 24-week build running against your real database.**

☐ 1. Back up the current state first:
```bash
# on .101
cd /opt/apps/"IT TRAINING PROJECT CODE"/projects
cp -r nexus-admin-academy nexus-admin-academy.bak-$(date +%F)
pg_dump "$DATABASE_URL" > ~/nexus-pre-24wk-$(date +%F).sql   # if Postgres; skip for fresh DB
```
**VERIFY:** `ls -d nexus-admin-academy.bak-*` shows the backup folder.

☐ 2. Unzip `nexus-complete-24-weeks.zip` over the project (or into a fresh
folder and swap — your call, backup exists either way).
**VERIFY:** `ls backend/seed_phase_g.py` exists — that file only exists in the
new build.

☐ 3. Backend deps + env:
```bash
cd backend
pip install -r requirements.txt --break-system-packages
# .env must have: DATABASE_URL, JWT_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_API_KEY
# Do NOT set AI_* yet — the app boots fine without them (that's tested).
```
**VERIFY:** `python -c "from app.main import app; print('boots')"` prints `boots`.

☐ 4. Migrate + seed:
```bash
alembic upgrade head
python scripts/seed_users.py
python seed.py
python seed_curriculum.py
```
**VERIFY:** the seed summary line ends with
`phase_g={'modules': 2, 'lessons': 3, ...}` and no traceback.
Run `python seed.py` a SECOND time — counts should show 0 new
modules/tickets (idempotency proof).
**VERIFY:** `seed_curriculum.py` prints `Curriculum seeded successfully` and
`SELECT COUNT(*) FROM curriculum_videos` is non-zero (fresh-install proof: 62) —
Study Tracker shows nothing without this step.

☐ 5. Test suite on the real box:
```bash
python -m pytest tests/ -q
```
**VERIFY:** `112 passed, 0 failed` (count as of 2026-07-18; was 98 at go-live — +10 username-case, +2 study-tracker restore, +2 study-tracker auth regression). Anything else → stop, paste it back.

☐ 6. Frontend build + serve:
```bash
cd ../frontend && npm ci && npm run build
```
**VERIFY:** `✓ built` with no errors (chunk-size warning is fine/known).

☐ 7. Restart your services (docker compose / systemd — however you run it).
**VERIFY:** log into the web UI as admin; you can see modules MOD-000 → MOD-024.

**Day 1 done when:** admin login works, 25 modules visible, 112 tests green on .101 (98 at original go-live).

---

## DAY 2 — Finish GPU passthrough on VM 200 (AI-VM, .104)

**Goal: the RTX 5090 visible inside Ubuntu on VM 200.**
You were interrupted mid-start last time — resume exactly here.

⚠ **STANDING RULE: never `sudo reboot` inside VM 200. Always `qm stop 200`
then `qm start 200` from the Proxmox host.** (5090 has no FLR reset.)

☐ 1. From the Proxmox host, clean start:
```bash
qm stop 200
qm status 200        # wait for: stopped
qm start 200
```
**VERIFY:** `qm status 200` → `running`, and it STAYS running for 2+ minutes
(watch `journalctl -f` on the host for vfio errors). Last session it may have
already been working when Ctrl+C hit — this confirms it.

☐ 2. If it stays up, SSH in and check the GPU:
```bash
lspci | grep -i nvidia
```
**VERIFY:** the 5090 (and its audio function) listed. If the VM dies instead:
paste the host `journalctl` tail + `qm config 200` back to Claude before
changing anything.

☐ 3. NVIDIA driver inside the VM:
```bash
sudo apt update && sudo apt install -y nvidia-driver-570   # or current recommended
# then FROM THE HOST: qm stop 200 && qm start 200
nvidia-smi
```
**VERIFY:** `nvidia-smi` shows the RTX 5090 with driver + CUDA version.

**Day 2 done when:** `nvidia-smi` works and survives a host-side stop/start cycle.

---

## DAY 3 — Ollama live + grader calibration

**Goal: AI grading trusted, not assumed.**

☐ 1. Install Ollama on VM 200 and pull your model:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:70b     # or your chosen model
```
**VERIFY:** `nvidia-smi` during a test prompt shows GPU memory in use
(proves it's not CPU-only).

☐ 2. Expose it on the LAN (systemd override: `OLLAMA_HOST=0.0.0.0`).
**VERIFY:** from .101:
`curl http://<vm200-ip>:11434/v1/models` returns JSON with your model.

☐ 3. Wire Nexus to it — on .101, add to backend `.env`:
```
AI_BASE_URL=http://<vm200-ip>:11434/v1
AI_MODEL=llama3.1:70b
```
(no AI_API_KEY needed for local Ollama). Restart the backend.

☐ 4. **CALIBRATE — this has never been run against a live model:**
```bash
cd backend && python scripts/calibrate_grader.py
```
**VERIFY:** all five fixtures print `OK` and it says `Calibration PASSED`.
- strong → 8-10, weak → ≤5, incomplete → verification ≤1, unsafe → ≤4,
  **malicious → ≤3** (the injection test — this one matters most).
- `NEEDS TUNING` → try a different model size or paste the scores back to
  Claude for a prompt adjustment. **Do not put students on AI grading until
  this passes.**

**Day 3 done when:** calibration PASSED, printed output saved into loop-log.

---

## DAY 4 — End-to-end smoke test as a student

**Goal: walk the actual student path before any student does.**

☐ 1. Log in as a test student account (from seed_users).
**VERIFY:** "This Week" panel shows Week 1 with lessons/quiz/labs/tickets.

☐ 2. Read a lesson, submit lesson notes.
**VERIFY:** the lesson flips to done on the week panel.

☐ 3. Take the "Ticket Writing Fundamentals" quiz — deliberately retake it.
**VERIFY:** both attempts appear in history; best score kept; XP only from
attempt one.

☐ 4. Open the DNS ticket, reveal ONE hint.
**VERIFY:** cost was shown BEFORE reveal; hint text has your student-specific
values substituted (no `{{PLACEHOLDER}}` visible).

☐ 5. Submit a real writeup on that ticket (write a decent one).
**VERIFY:** AI grading returns anchors + feedback in ~seconds; score is sane
for what you wrote. Then check the admin review queue shows it.

☐ 6. As admin: leave a flag on the submission, check the student's promotion
status shows the gate blocked; resolve the flag, status clears.
**VERIFY:** gate requirement flips as expected.

☐ 7. Evidence upload: try a >10MB file (should 413) and a normal screenshot
(should attach).

**Day 4 done when:** the full loop — lesson → quiz → hint → ticket → AI grade
→ mentor review → gate math — works with your hands on it.

---

## DAY 5 — Cohort prep + launch

☐ 1. Create/verify the 5 real student accounts; delete/disable any test ones.
☐ 2. Skim `docs/STUDENT_GUIDE.md` and `docs/MENTOR_GUIDE.md` — they're the
day-one handouts. Adjust anything that doesn't match your setup.
☐ 3. Post the Student Guide + login info to the Discord.
☐ 4. Schedule the Week-1 kickoff call (guide's day-one talking points:
tickets are the product, escalation is a win, verification is mandatory,
hints cost XP, tickets are individually parametrized).
☐ 5. Backups: confirm nightly `pg_dump` (or Supabase backups) actually runs,
and `UPLOAD_DIR` is on persistent storage.
**VERIFY:** restore one table from last night's dump to a scratch DB — the
Week-17 lesson applies to you too: an untested backup is a hope.
☐ 6. Update loop-log.md: deployment date, calibration results, launch date.

**Day 5 done when:** students have credentials, kickoff is scheduled, backups
are proven restorable.

---

## PARKED (do not block launch on these)
- Proxmox/Guacamole AUTO-VM P0s — manual-VM paths cover Weeks 13-24; revisit
  around Week 10 of the cohort at the earliest.
- learn-routing CLI engine — Packet Tracer fallback stands for Week 11.
- Interactive Ollama-roleplay tickets, Ludus break-fix pipeline, monthly
  research pipeline — post-launch enhancements.
- Frontend lint/E2E harness — new scope, only if it starts hurting.
