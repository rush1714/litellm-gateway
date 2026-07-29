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


def append_csv_env(current: str | None, extra: str) -> str:
    if not current:
        return extra
    current_parts = [part.strip() for part in current.split(",") if part.strip()]
    extra_parts = [part.strip() for part in extra.split(",") if part.strip()]
    for part in extra_parts:
        if part not in current_parts:
            current_parts.append(part)
    return ",".join(current_parts)


@lru_cache
def get_settings() -> Settings:
    env_file = Path(os.environ.get("ENV_FILE", DEFAULT_ENV_FILE))
    if env_file.exists():
        load_dotenv(env_file)

    no_proxy_default = "localhost,127.0.0.1,::1"
    os.environ["NO_PROXY"] = append_csv_env(os.environ.get("NO_PROXY"), no_proxy_default)
    os.environ["no_proxy"] = append_csv_env(os.environ.get("no_proxy"), no_proxy_default)

    return Settings(
        database_enabled=_is_enabled(os.environ.get("LITELLM_ENABLE_DATABASE")),
        database_url=os.environ.get("DATABASE_URL"),
        host=os.environ.get("USAGE_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("USAGE_API_PORT", "4010")),
    )
