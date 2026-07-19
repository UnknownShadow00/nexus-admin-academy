# Nexus Admin Academy

Nexus IT Academy (Nexus Admin Academy) is a private, self-hosted training platform that runs like a simulated IT workplace. Complete-beginner students progress through a six-role career ladder (Trainee → Support Technician I/II → Network Support Technician → Junior Systems Technician → Junior Infrastructure Administrator) by working realistic tickets, labs, and simulations — not by memorizing exam objectives. The 24-week curriculum is seeded; see `docs/STUDENT_GUIDE.md` and `docs/MENTOR_GUIDE.md`.


> **Documentation verified 2026-07-19.** The active production architecture is
> self-hosted on `nexus-services`: a systemd-managed FastAPI backend using
> SQLite, an nginx frontend container, Cloudflare HTTPS, persistent local
> uploads/backups, and local Ollama AI. Railway/Supabase plans are historical.
> Key guides:
> [Student Guide](docs/STUDENT_GUIDE.md) ·
> [Mentor Guide](docs/MENTOR_GUIDE.md) ·
> [Authoring / Config / Security](docs/AUTHORING_CONFIG_SECURITY.md).

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
python seed.py            # roles, gates, and all 24 weeks of content (idempotent)
python seed_curriculum.py # Study Tracker video/quiz curriculum (required — Study Tracker is empty without it; idempotent)
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

On 2026-07-19, a fresh migration through `0028` followed by both seeders
produced 25 modules, 63 lessons, 25 quizzes, 189 questions, 48 tickets, 5 lab
templates, 48 networking CLI labs, 3 capstones, and 62 Study Tracker videos.
Running all seed commands a second time left every count unchanged.

## Production release status

The 2026-07-19 verification on `.101` passed 154 backend tests, the frontend
build/audit, migrations, seeds, networking CLI checks, remote-AI calibration,
student onboarding, ticket grading, evidence security, and the complete
manual-lab smoke path. Five legacy orphaned methodology rows were repaired with
the dry-run-first script in `backend/scripts/repair_orphaned_student_data.py`;
SQLite application connections now enforce foreign keys. Additional production
content is documented read-only in `docs/PRODUCTION_CONTENT_INVENTORY.md`.
The project is ready for a manual-VM cohort. Automated VM labs remain disabled
pending a real Proxmox/Guacamole staging test.
