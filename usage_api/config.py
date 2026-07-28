import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseModel):
    database_enabled: bool = True
    database_url: str | None = None
    host: str = "127.0.0.1"
    port: int = Field(default=4010, ge=1, le=65535)


def _is_enabled(value: str | None) -> bool:
    return value in {None, "1", "true", "TRUE", "yes", "YES", "on", "ON"}


@lru_cache
def get_settings() -> Settings:
    env_file = Path(os.environ.get("ENV_FILE", DEFAULT_ENV_FILE))
    if env_file.exists():
        load_dotenv(env_file)

    return Settings(
        database_enabled=_is_enabled(os.environ.get("LITELLM_ENABLE_DATABASE")),
        database_url=os.environ.get("DATABASE_URL"),
        host=os.environ.get("USAGE_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("USAGE_API_PORT", "4010")),
    )
