# Nexus Admin Academy

Nexus Admin Academy is a CompTIA A+ training platform where students progress through Professor Messer videos, complete quizzes, and earn XP, while admins manage curriculum content and quiz imports from ExamCompass.

## Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL

## Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Set these values in `backend/.env`:
- `DATABASE_URL`
- `ADMIN_SECRET_KEY`
- `ANTHROPIC_API_KEY`

Run database setup and seed data:
```bash
alembic upgrade head
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
```

Set these values in `frontend/.env`:
- `VITE_API_URL`
- `VITE_ADMIN_KEY`

Start the frontend:
```bash
npm run dev
```

## Bookmarklet Import and Quiz Title Matching
The admin bookmarklet runs on ExamCompass quiz pages, extracts questions/answers, and posts them to `/api/admin/quiz/bookmarklet-import`. For study-tracker linking to work reliably, each imported quiz title must match the expected `quiz_title` values from `seed_curriculum.py` exactly.

## Important Admin Note
`ADMIN_SECRET_KEY` must be set. If it is missing or empty, admin-protected routes will return `500` errors.
