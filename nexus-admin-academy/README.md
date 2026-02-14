# Nexus Admin Academy V1

AI-driven IT training platform for a trusted cohort of 5 students.

## Stack
- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: React 18 + Vite + Tailwind
- Database: PostgreSQL 15 (local dev defaults to SQLite)
- AI: OpenRouter (`mistralai/mistral-large`)

## Project Structure
- `backend/` API, models, services, migrations
- `frontend/` student/admin web app

## Backend Setup
```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` if backend is not `http://localhost:8000`.

## Required Environment Variables
Backend (`backend/.env`):
```env
DATABASE_URL=sqlite:///./nexus.db
ADMIN_SECRET_KEY=change_me
APP_LOG_PATH=./nexus.log
UPLOAD_DIR=./uploads/screenshots

OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=mistralai/mistral-large
OPENROUTER_SITE_URL=http://localhost:3000
OPENROUTER_SITE_NAME=Nexus Admin Academy
COST_PER_1K_TOKENS=0.003
```

Frontend (`frontend/.env`):
```env
VITE_API_URL=http://localhost:8000
VITE_ADMIN_KEY=change_me
```

## Implemented API Routes
- `POST /api/admin/quiz/generate`
- `POST /api/admin/tickets`
- `POST /api/admin/tickets/bulk-generate`
- `POST /api/admin/tickets/bulk-publish`
- `POST /api/admin/tickets/bulk`
- `GET /api/admin/ai-usage`
- `GET /api/admin/submissions`
- `GET /api/admin/submissions/{submission_id}`
- `PUT /api/admin/submissions/{submission_id}/override`
- `GET /api/admin/review`
- `GET /api/admin/students/overview`
- `GET /api/admin/students/{student_id}/activity`
- `POST /api/admin/resources`
- `DELETE /api/admin/resources/{resource_id}`
- `GET /api/quizzes`
- `GET /api/quizzes/{quiz_id}`
- `POST /api/quizzes/{quiz_id}/submit`
- `GET /api/tickets`
- `GET /api/tickets/{ticket_id}`
- `POST /api/tickets/uploads`
- `POST /api/tickets/{ticket_id}/submit`
- `GET /api/resources`
- `GET /api/students/{student_id}/dashboard`
- `GET /api/leaderboard`

## Notes
- Admin routes require `X-Admin-Key` and must match `ADMIN_SECRET_KEY`.
- On startup, backend seeds 5 students if database is empty.
- AI calls are logged in `ai_usage_logs` with token/cost data.
