import os
import sys
import time
from pathlib import Path

import redis
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT_DIR / ".env"
CONNECT_TIMEOUT_SECONDS = 3.0


def load_environment() -> None:
    env_file = Path(os.environ.get("ENV_FILE", DEFAULT_ENV_FILE))
    if env_file.exists():
        load_dotenv(env_file)


def is_redis_enabled() -> bool:
    return os.environ.get("LITELLM_ENABLE_REDIS", "true") in {
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
        "on",
        "ON",
    }


def main() -> int:
    load_environment()

    if not is_redis_enabled():
        print("Redis 未启用 (LITELLM_ENABLE_REDIS=false)，跳过 Redis 连通性检查。")
        return 0

    redis_url = os.environ.get("REDIS_URL")
    redis_host = os.environ.get("REDIS_HOST", "127.0.0.1")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    redis_password = os.environ.get("REDIS_PASSWORD") or None

    target_desc = redis_url if redis_url else f"{redis_host}:{redis_port}"
    print(f"正在尝试连接 Redis: {target_desc}")

    try:
        if redis_url:
            client = redis.from_url(redis_url, socket_timeout=CONNECT_TIMEOUT_SECONDS)
        else:
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                socket_timeout=CONNECT_TIMEOUT_SECONDS,
            )

        start = time.perf_counter()
        ping_ok = client.ping()
        elapsed_ms = (time.perf_counter() - start) * 1000

        if not ping_ok:
            print("❌ PING 响应失败", file=sys.stderr)
            return 1

        info = client.info("server")
        redis_version = info.get("redis_version", "unknown")
        print(f"✅ 连接成功！(版本: {redis_version}, 延迟: {elapsed_ms:.1f}ms)")

        # 写入与读取缓存自测
        test_key = "litellm:health_check:probe"
        client.set(test_key, "ok", ex=10)
        value = client.get(test_key)
        client.delete(test_key)

        if value == b"ok":
            print("✅ 缓存读写验证通过！")
        else:
            print(f"⚠️ 读写验证返回非预期值: {value}", file=sys.stderr)
            return 1

        return 0
    except Exception as exc:  # noqa: BLE001 - show original connectivity error to operator
        print(f"❌ Redis 连接失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
