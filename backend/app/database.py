import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nexus.db")

if DATABASE_URL.startswith("sqlite:///./"):
    db_name = DATABASE_URL.replace("sqlite:///./", "", 1)
    db_path = (Path(__file__).resolve().parents[1] / db_name).resolve()
    DATABASE_URL = f"sqlite:///{db_path.as_posix()}"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
