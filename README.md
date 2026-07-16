# Nexus Admin Academy

Nexus Admin Academy is a CompTIA A+ training platform where students progress through Professor Messer videos, complete quizzes, and earn XP, while admins manage curriculum content and quiz imports from ExamCompass.

## Prerequisites
- Python 3.11+
- Node.js 18+
- SQLite (the default) or PostgreSQL

## Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Review these values in `backend/.env`:
- `DATABASE_URL` (defaults to the local SQLite database shown in the template)
- `JWT_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_API_KEY`
- `AI_BASE_URL` (Ollama base URL, default `http://192.168.0.104:11434/v1`) and `AI_MODEL` (default `deepseek-r1:32b`)
- `SEED_PASSWORD_MENTOR1` and `SEED_PASSWORD_STUDENT1`..`SEED_PASSWORD_STUDENT5` (required by `scripts/seed_users.py`)

The copied template also documents CORS, logging, upload storage, Proxmox, and Guacamole settings. Proxmox and Guacamole values are only required for VM-backed labs.

Run database setup and seed data:
```bash
alembic upgrade head
python scripts/seed_users.py
python seed_curriculum.py
```

Start the backend:
```bash
uvicorn app.main:app --reload
```

## Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
```

Set these values in `frontend/.env`:
- `VITE_API_URL`

Start the frontend:
```bash
npm run dev
```

## Bookmarklet Import and Quiz Title Matching
The admin bookmarklet runs on ExamCompass quiz pages, extracts questions/answers, and posts them to `/api/admin/quiz/bookmarklet-import`. For study-tracker linking to work reliably, each imported quiz title must match the expected `quiz_title` values from `seed_curriculum.py` exactly.

## Important Admin Note
`ADMIN_USERNAME` and `ADMIN_PASSWORD` are required for admin login. `ADMIN_API_KEY` is the separate header-based access key.
