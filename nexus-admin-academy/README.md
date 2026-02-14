# Nexus Admin Academy (Phase 2)

AI-driven IT training platform for a trusted cohort. Phase 2 adds integrity hardening (XP ledger, anti-farming), resource library, admin review workflows, and richer student/admin UX.

## Tech Stack
- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: React 18 + Vite + Tailwind
- Database: PostgreSQL 15
- AI: Anthropic Claude (`claude-sonnet-4-20250514`)

## Backend Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

## Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Required Environment Variables
### Backend (`backend/.env`)
- `ANTHROPIC_API_KEY`
- `DATABASE_URL`
- `ADMIN_SECRET_KEY`
- `UPLOAD_DIR`
- `APP_LOG_PATH`

### Frontend (`frontend/.env`)
- `VITE_API_URL`
- `VITE_ADMIN_KEY`

## Phase 2 Highlights
- XP ledger table (`xp_ledger`) with transaction-safe XP award/adjustment service.
- Quiz retake policy: unlimited retakes, XP only on first attempt.
- Strict quiz generation validation (exactly 10 unique questions, schema checks, one retry).
- Ticket submission enhancements:
  - optional screenshot uploads (validated file size/type, UUID names)
  - collaborators + XP split multipliers
  - lock after grading
- Admin protection on all `/api/admin/*` routes via `X-ADMIN-KEY`.
- Resources library APIs + frontend page.
- Admin review queue, student activity overview, and bulk ticket generation/publish.
- Dark mode toggle (`localStorage`), toast notifications, loading/empty states.

## API Response Envelope
Success:
```json
{ "success": true, "data": {} }
```
Error:
```json
{ "success": false, "error": "Human-readable message", "code": "ERROR_CODE" }
```

## Key Routes
### Student
- `GET /api/students/{student_id}/dashboard`
- `GET /api/leaderboard`
- `GET /api/quizzes`
- `GET /api/quizzes/{quiz_id}`
- `POST /api/quizzes/{quiz_id}/submit`
- `GET /api/tickets`
- `GET /api/tickets/{ticket_id}`
- `POST /api/tickets/uploads`
- `POST /api/tickets/{ticket_id}/submit`
- `GET /api/resources`

### Admin (requires `X-ADMIN-KEY`)
- `POST /api/admin/quiz/generate`
- `POST /api/admin/tickets`
- `POST /api/admin/tickets/bulk-generate`
- `POST /api/admin/tickets/bulk-publish`
- `GET /api/admin/submissions`
- `GET /api/admin/submissions/{submission_id}`
- `PUT /api/admin/submissions/{submission_id}/override`
- `GET /api/admin/review`
- `PUT /api/admin/review/{submission_id}`
- `GET /api/admin/students/overview`
- `GET /api/admin/students/{student_id}/activity`
- `POST /api/admin/resources`
- `DELETE /api/admin/resources/{resource_id}`

## Validation/Build Checks Run
- Backend Python syntax parse check passed.
- Frontend production build (`npm run build`) passed.
