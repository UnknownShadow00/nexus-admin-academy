# Nexus Admin Academy

CompTIA A+ training platform — Professor Messer video curriculum, quizzes, XP progression, and admin course management.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, React Router 6, Tailwind CSS, Axios, Lucide React, xterm.js |
| Backend | FastAPI, SQLAlchemy 2, Alembic, PostgreSQL |
| Auth | JWT (python-jose), passlib |
| Testing | Playwright (E2E) |

## Project Structure

```
nexus-admin-academy/
├── backend/
│   └── app/
│       ├── main.py         # FastAPI entry point
│       ├── models/         # SQLAlchemy models
│       ├── routers/        # API route handlers
│       └── schemas/        # Pydantic schemas
└── frontend/
    └── src/
        ├── components/     # Reusable UI components
        ├── hooks/          # Custom React hooks
        ├── pages/          # Route-level page components
        └── services/       # Axios API clients
```

## Dev Start

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev
```

## Environment Variables

```
# Backend (.env)
DATABASE_URL=
ADMIN_SECRET_KEY=
ANTHROPIC_API_KEY=

# Frontend (.env)
VITE_API_URL=
```

## Key Rules

- All database queries must use parameterized queries — no string concatenation
- JWT tokens must not be stored in localStorage — use httpOnly cookies or memory
- Alembic migrations required for any schema change — never alter tables directly
- Frontend API calls go through `src/services/` — never call Axios directly in components
- Tailwind only — no inline styles, no CSS modules
