import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import Base, SessionLocal, engine
from app.models import Student
from app.routers import admin, quizzes, students, tickets

LOG_PATH = "/var/log/nexus.log"


class APIError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def configure_logging() -> None:
    handlers = []
    try:
        handlers.append(logging.FileHandler(LOG_PATH))
    except OSError:
        handlers.append(logging.FileHandler("nexus.log"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
    )


def seed_students() -> None:
    default_students = [
        ("Alex", "alex@nexus.local"),
        ("Jordan", "jordan@nexus.local"),
        ("Sam", "sam@nexus.local"),
        ("Taylor", "taylor@nexus.local"),
        ("Riley", "riley@nexus.local"),
    ]

    db = SessionLocal()
    try:
        if db.query(Student).count() == 0:
            for name, email in default_students:
                db.add(Student(name=name, email=email, total_xp=0))
            db.commit()
    finally:
        db.close()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Nexus Admin Academy API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(APIError)
    async def api_error_handler(_: Request, exc: APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "message": exc.message, "code": exc.code},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "message": str(exc.detail), "code": "HTTP_ERROR"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": str(exc.errors()), "code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(_: Request, exc: Exception):
        logging.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "Internal server error", "code": "INTERNAL_ERROR"},
        )

    @app.get("/health")
    def healthcheck():
        return {"ok": True, "timestamp": datetime.utcnow().isoformat() + "Z"}

    app.include_router(admin.router)
    app.include_router(quizzes.router)
    app.include_router(tickets.router)
    app.include_router(students.router)

    return app


app = create_app()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_students()
