"""Configuration. Values come from environment variables (.env is loaded if present)."""
from __future__ import annotations

import os
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"


def _load_dotenv() -> None:
    """Minimal .env loader (no external dependency): KEY=VALUE per line."""
    for candidate in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    # --- database: MySQL 8 in docker-compose, SQLite fallback for local runs ---
    DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{(DATA_DIR / 'kjds.db').as_posix()}"

    # --- auth ---
    JWT_SECRET = os.getenv("JWT_SECRET", "kjds-demo-secret-change-me")
    JWT_ALGORITHM = "HS256"
    JWT_TTL_HOURS = _int("JWT_TTL_HOURS", 24 * 7)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

    # --- AI (SiliconFlow) ---
    EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "https://api.siliconflow.cn/v1")
    EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
    EMBED_MODEL = os.getenv("EMBED_MODEL", "Qwen/Qwen3-Embedding-8B")
    CHAT_BASE_URL = os.getenv("CHAT_BASE_URL") or EMBED_BASE_URL
    CHAT_API_KEY = os.getenv("CHAT_API_KEY") or EMBED_API_KEY
    CHAT_MODEL = os.getenv("CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    AI_TIMEOUT = _int("AI_TIMEOUT", 60)
    AI_MAX_TOKENS = _int("AI_MAX_TOKENS", 700)

    # --- misc ---
    SEED_FILE = os.getenv("SEED_FILE") or str(BASE_DIR / "seed" / "products.json")
    PAGE_SIZE_DEFAULT = _int("PAGE_SIZE_DEFAULT", 18)
    PAGE_SIZE_MAX = _int("PAGE_SIZE_MAX", 60)
    RECOMMEND_LIMIT = _int("RECOMMEND_LIMIT", 5)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    UPLOAD_DIR = pathlib.Path(os.getenv("UPLOAD_DIR") or (BASE_DIR / "static" / "uploads"))
