import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from prisma import Prisma

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT_DIR / ".env"
QUERY_TIMEOUT_SECONDS = 5.0


def load_environment() -> None:
    env_file = Path(os.environ.get("ENV_FILE", DEFAULT_ENV_FILE))
    if env_file.exists():
        load_dotenv(env_file)

    no_proxy_default = "localhost,127.0.0.1,::1"
    os.environ["NO_PROXY"] = append_csv_env(os.environ.get("NO_PROXY"), no_proxy_default)
    os.environ["no_proxy"] = append_csv_env(os.environ.get("no_proxy"), no_proxy_default)


def append_csv_env(current: str | None, extra: str) -> str:
    if not current:
        return extra
    current_parts = [part.strip() for part in current.split(",") if part.strip()]
    extra_parts = [part.strip() for part in extra.split(",") if part.strip()]
    for part in extra_parts:
        if part not in current_parts:
            current_parts.append(part)
    return ",".join(current_parts)


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Fill in DATABASE_URL in .env."
        )
    return database_url


def mask_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url

    scheme, rest = database_url.split("://", 1)
    _credentials, host_and_path = rest.split("@", 1)
    return f"{scheme}://***:***@{host_and_path}"


async def main() -> int:
    load_environment()

    try:
        database_url = get_database_url()
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    db = Prisma(datasource={"url": database_url})

    try:
        print(f"正在尝试连接: {mask_database_url(database_url)}")
        await asyncio.wait_for(db.connect(), timeout=QUERY_TIMEOUT_SECONDS)
        print("✅ 连接成功！")

        result = await db.query_raw("SELECT 1 as num")
        print(f"查询结果: {result}")
        return 0
    except Exception as exc:  # noqa: BLE001 - show original connectivity error to operator
        print(f"❌ 错误: {exc}", file=sys.stderr)
        return 1
    finally:
        if db.is_connected():
            await db.disconnect()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
