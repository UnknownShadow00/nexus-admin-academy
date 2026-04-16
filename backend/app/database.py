import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import load_env

load_env()


def normalize_database_url(url: str | None) -> str:
    normalized = (url or "sqlite:///./nexus.db").strip()
    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", "postgresql+psycopg://", 1)
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
    return normalized


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))

if DATABASE_URL.startswith("sqlite:///./"):
    db_name = DATABASE_URL.replace("sqlite:///./", "", 1)
    db_path = (Path(__file__).resolve().parents[1] / db_name).resolve()
    DATABASE_URL = f"sqlite:///{db_path.as_posix()}"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine_kwargs = {"future": True, "connect_args": connect_args}
if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
