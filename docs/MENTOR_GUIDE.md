# Nexus IT Academy — Mentor Guide

This guide is for Abdi (or any mentor) running the cohort through Phase A and B.
It assumes you're a capable IT person but not necessarily a developer. Where a
command is needed, it's spelled out.

## What's built and ready

The complete seed currently contains 35 curriculum modules with lessons,
required quizzes, guided labs, live Service Desk scenarios, networking CLI
labs, and capstones across stable storage weeks 0 through 34. The Week 1–8 foundation includes the
first two promotion gates. Everything below can run **without** automated VM
provisioning—on students' own Windows machines or a VM cloned by hand. The VM
application code is repaired, but real Proxmox/Guacamole infrastructure still
requires an end-to-end acceptance test before cohort use.

## First-time setup (once)

```bash
# from the repo root
cd backend
pip install -r requirements.txt          # first time only

# point at your database (SQLite is active in production; PostgreSQL is supported)
export DATABASE_URL="sqlite:///./nexus.db"   # example for a local trial

alembic upgrade head                      # create/upgrade all tables
python scripts/seed_users.py              # create the 5 student + mentor accounts
python seed.py                            # load roles, gates, and the base curriculum
python seed_curriculum.py                 # required Study Tracker catalog
```

Re-running `python seed.py` is safe: it updates content in place and never
duplicates or wipes student work. Run it again whenever content is updated.

If you're upgrading an older database that had the original 5 roles, the seed
migrates those rows to the new six-role ladder automatically and keeps every
student pointed at the right role. If phantom students (Alex, Jordan, Sam,
Taylor, Riley) exist from an old build:

```bash
python scripts/purge_ghost_students.py        # dry run — shows what it would remove
python scripts/purge_ghost_students.py --yes  # actually remove them
```

## AI grading (optional but recommended)

Ticket write-ups are graded against the five-anchor rubric. This works best with
AI, but the platform runs fine without it — submissions are saved and you grade
them manually from the admin review queue.

To enable AI grading with your Ollama GPU VM (or any OpenAI-compatible endpoint):

```bash
export AI_BASE_URL="http://<ollama-vm-ip>:11434/v1"
export AI_MODEL="llama3.1:70b"        # whatever you're serving
# AI_API_KEY is not needed for local Ollama
```

Before trusting it on real students, calibrate:

```bash
python scripts/calibrate_grader.py
```

This runs the grader against five known-quality fixtures (strong, weak,
incomplete, unsafe, malicious) and prints whether each lands in the expected
score band. If a fixture is out of band, adjust the model or prompt and re-run.
**The script talks to your real endpoint — if AI isn't configured it says so
and produces no scores, rather than pretending.** The malicious fixture also
checks that a prompt-injection attempt inside a student submission doesn't
hijack the grade.

## Your weekly rhythm (about 2 hours)

The platform does the heavy lifting; your time goes where judgment is needed.

1. **Spot-check ~2 graded tickets per student.** AI (or your own first pass)
   pre-grades; you confirm or override. Overriding is one click in the admin
   ticket review and is final.
2. **Leave flags where needed.** A comment on a submission becomes a *mentor
   flag* that blocks the student's gate until you re-review it. Use this for
   "redo the verification section — no evidence." It's your quality rail.
3. **Watch the two simulations.** Simulation 1 (Week 4) and Simulation 2
   (Week 8) are the gate checkpoints. Read the student's priority ordering and
   their handling of the misleading / escalation / security tickets. This is
   where you see whether competence is real.
4. **Clear remediations.** A student who misses a gate gets a targeted list, not
   a restart. Re-issue the weak-area tickets (they're parametrized, so the
   values differ) and re-review.

## How the gates actually decide

Each gate reads live student data — no manual tallying. A student is eligible
when every requirement is met:

- required lessons complete (measured by submitted lesson notes)
- quiz mastery ≥ 70% in the phase's domains
- the required count of verified tickets at the required difficulties
- the practical checkpoint (the week's simulation) passed within the hint and
  score limits
- no unresolved mentor flags

You'll see each requirement's live status on the student's promotion view.
Promote when it shows eligible. Nothing auto-promotes — the decision stays
yours.

## Manual VM labs (when you want hands-on beyond the student's own PC)

Until the automated VM pipeline is signed off, clone a template in Proxmox by
hand and give the student access over your Headscale network (RDP for Windows,
SSH for Linux). The lab records in the platform (setup, break, hints, model
solution, reset) work fine as your operating notes for a hand-run lab. Nothing
in Gate 1 or Gate 2 depends on automated provisioning, so a flaky pipeline never
blocks a student's progress.

## What to tell students on day one

- This is a workplace simulation; the ticket write-up is the graded product.
- Escalating correctly is a win, not a failure.
- Verify with evidence — "it works now" without proof doesn't pass.
- Their tickets are individually parametrized; copying won't work and isn't the
  point.
- Hints cost XP but a finished ticket beats a blank one.

## If something breaks

- **App won't start** and mentions AI config: it shouldn't — the app boots
  without AI now. If it does, check `DATABASE_URL` is set.
- **A student sees the wrong week** on This Week: their current week is derived
  from their earliest incomplete gated module; once they submit notes for the
  overdue lessons it advances.
- **AI grading returns 503:** AI isn't configured or the endpoint is down.
  Submissions are still saved; grade from the review queue or fix `AI_BASE_URL`.
- **Test the whole install is healthy:** from `backend/`, run
  `python -m pytest tests/ -q` — a green run means the platform logic is intact.
