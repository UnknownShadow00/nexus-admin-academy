import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_ADMIN_USERNAME = "shadowgarden"
DEFAULT_ADMIN_PASSWORD = "IloveIT"


@lru_cache(maxsize=1)
def load_env() -> None:
    # backend/app/config.py -> backend/.env
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
    os.environ.setdefault("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME)
    os.environ.setdefault("ADMIN_PASSWORD", os.getenv("ADMIN_SECRET_KEY") or DEFAULT_ADMIN_PASSWORD)
