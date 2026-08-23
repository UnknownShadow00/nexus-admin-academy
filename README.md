# Nexus Admin Academy

Nexus IT Academy (Nexus Admin Academy) is a private, self-hosted training platform that runs like a simulated IT workplace. Complete-beginner students progress through a six-role career ladder (Trainee → Support Technician I/II → Network Support Technician → Junior Systems Technician → Junior Infrastructure Administrator) by working realistic tickets, labs, and simulations — not by memorizing exam objectives. The 35-module curriculum uses stable storage week numbers 0 through 34; see `docs/STUDENT_GUIDE.md` and `docs/MENTOR_GUIDE.md`.


> **Documentation verified 2026-07-22.** The active production architecture is
> self-hosted on `nexus-services`: a systemd-managed FastAPI backend using
> SQLite, an nginx frontend container, Cloudflare HTTPS, persistent local
> uploads/backups, and local Ollama AI. Railway/Supabase plans are historical.
> Key guides:
> [Student Guide](docs/STUDENT_GUIDE.md) ·
> [Mentor Guide](docs/MENTOR_GUIDE.md) ·
> [Authoring / Config / Security](docs/AUTHORING_CONFIG_SECURITY.md) ·
> [My Training Architecture](docs/MY_TRAINING.md).

## Prerequisites
- Python 3.11+
- Node.js 18+
- SQLite (default) or PostgreSQL

## Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Set these values in `backend/.env`:
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_API_KEY`
- `AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY` (AI grading — OpenAI-compatible or local Ollama). **The app boots fine without any AI config**; grading falls back to manual. Legacy `OPENROUTER_*` vars still work. Full list: `docs/AUTHORING_CONFIG_SECURITY.md`.

Run database setup and seed data:
```bash
alembic upgrade head
python scripts/seed_users.py
python seed.py            # roles, gates, and all 25 weeks of content (idempotent)
python seed_curriculum.py # All Course Content video/quiz catalog (required; idempotent)
```

Start the backend:
```bash
uvicorn app.main:app --reload
```

## Frontend Setup
```bash
cd frontend
npm install
```

Set these values in `frontend/.env`:
- `VITE_API_URL`

Start the frontend:
```bash
npm run dev
```

## ExamCompass Scraping Setup

ExamCompass scraping is an admin/development tool and is intentionally excluded
from production dependencies. Install the development dependencies and Chromium
before using the scraper:

```bash
cd backend
pip install -r requirements-dev.txt
playwright install chromium
```

## Bookmarklet Import and Quiz Title Matching
The admin bookmarklet runs on ExamCompass quiz pages, extracts questions/answers, and posts them to `/api/admin/quiz/bookmarklet-import`. For study-tracker linking to work reliably, each imported quiz title must match the expected `quiz_title` values from `seed_curriculum.py` exactly.

## Important Admin Note
`ADMIN_PASSWORD` or `ADMIN_API_KEY` must be set for admin access. VM-backed labs also require the Proxmox and Guacamole environment variables documented in `CLAUDE.md`.

## Verified Fresh Seed

The migration chain is preserved through `0032_my_training`. Both
`seed.py` and `seed_curriculum.py` are idempotent, and the release verification
checks a fresh schema plus a second seed pass for duplicate creation.

The current release is ready for a manual-VM cohort. Automated VM delivery
remains disabled until a real Proxmox/Guacamole isolation and lifecycle test
passes.

## Documentation

- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — production deployment, backup,
  restore, and smoke checks.
- [`docs/AUTHORING_CONFIG_SECURITY.md`](docs/AUTHORING_CONFIG_SECURITY.md) —
  content authoring, environment variables, and security controls.
- [`docs/MENTOR_GUIDE.md`](docs/MENTOR_GUIDE.md) — mentor operations.
- [`docs/STUDENT_GUIDE.md`](docs/STUDENT_GUIDE.md) — student workflow.
- [`docs/MY_TRAINING.md`](docs/MY_TRAINING.md) — weekly curriculum architecture,
  completion rules, administration, and deployment notes.
- [`TASKS.md`](TASKS.md) — current roadmap only.
