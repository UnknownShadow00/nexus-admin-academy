import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_ADMIN_USERNAME = "shadowgarden"
DEFAULT_ADMIN_PASSWORD = "IloveIT"
PRODUCTION_ENVIRONMENTS = {"production", "prod", "staging"}


def is_production_environment() -> bool:
    raw = (
        os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("FASTAPI_ENV")
        or os.getenv("VERCEL_ENV")
        or ""
    ).strip().lower()
    return raw in PRODUCTION_ENVIRONMENTS or bool(os.getenv("RENDER_SERVICE_ID"))


def use_secure_cookies() -> bool:
    cookie_secure = (os.getenv("COOKIE_SECURE") or "").strip().lower()
    if cookie_secure in {"1", "true", "yes", "on"}:
        return True
    if cookie_secure in {"0", "false", "no", "off"}:
        return False
    return is_production_environment()


@lru_cache(maxsize=1)
def load_env() -> None:
    # backend/app/config.py -> backend/.env
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    if not is_production_environment():
        os.environ.setdefault("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME)
        os.environ.setdefault("ADMIN_PASSWORD", os.getenv("ADMIN_SECRET_KEY") or DEFAULT_ADMIN_PASSWORD)
