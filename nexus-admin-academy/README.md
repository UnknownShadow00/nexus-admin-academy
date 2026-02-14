# Nexus Admin Academy V1

AI-driven IT training platform for a trusted cohort of 5 students.

## Stack
- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: React 18 + Vite + Tailwind
- Database: PostgreSQL 15 (dev fallback supports SQLite)
- AI: Anthropic Claude (`claude-sonnet-4-20250514`)

## Project Structure
- `backend/` API, models, services, migrations
- `frontend/` student/admin web app

## Backend Setup
```bash
cd backend
python -m venv .venv
. .venv/bin/activate  # Linux
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` if backend is not `http://localhost:8000`.

## Implemented API Routes
- `POST /api/admin/quiz/generate`
- `POST /api/admin/tickets`
- `GET /api/admin/submissions`
- `GET /api/admin/submissions/{submission_id}`
- `PUT /api/admin/submissions/{submission_id}/override`
- `GET /api/quizzes`
- `GET /api/quizzes/{quiz_id}`
- `POST /api/quizzes/{quiz_id}/submit`
- `GET /api/tickets`
- `GET /api/tickets/{ticket_id}`
- `POST /api/tickets/{ticket_id}/submit`
- `GET /api/students/{student_id}/dashboard`
- `GET /api/leaderboard`

## Notes
- V1 assumes no auth for local trusted cohort.
- On startup, backend seeds 5 students if database is empty.
- If `ANTHROPIC_API_KEY` is missing, quiz generation and ticket grading use deterministic fallback logic.
