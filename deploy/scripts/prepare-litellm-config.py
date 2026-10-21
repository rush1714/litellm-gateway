#!/usr/bin/env python3
import os
import sys
from pathlib import Path

import yaml


def is_truthy(value: str | None) -> bool:
    return value in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: prepare-litellm-config.py <source> <target>", file=sys.stderr)
        return 2

    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    config = yaml.safe_load(source.read_text())
    if not isinstance(config, dict):
        print(f"invalid LiteLLM config: {source}", file=sys.stderr)
        return 1

    if not is_truthy(os.environ.get("LITELLM_ENABLE_DATABASE", "true")):
        general_settings = config.get("general_settings") or {}
        if isinstance(general_settings, dict):
            general_settings.pop("database_url", None)
            config["general_settings"] = general_settings

    if not is_truthy(os.environ.get("LITELLM_ENABLE_REDIS", "true")):
        router_settings = config.get("router_settings") or {}
        if isinstance(router_settings, dict):
            for key in ["redis_host", "redis_port", "redis_password", "redis_url"]:
                router_settings.pop(key, None)
            if not router_settings:
                config.pop("router_settings", None)
        litellm_settings = config.get("litellm_settings") or {}
        if isinstance(litellm_settings, dict):
            litellm_settings.pop("cache", None)
            litellm_settings.pop("cache_params", None)
    elif not os.environ.get("REDIS_PASSWORD"):
        router_settings = config.get("router_settings") or {}
        if isinstance(router_settings, dict):
            router_settings.pop("redis_password", None)
        litellm_settings = config.get("litellm_settings") or {}
        if isinstance(litellm_settings, dict):
            cache_params = litellm_settings.get("cache_params") or {}
            if isinstance(cache_params, dict):
                cache_params.pop("password", None)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(config, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
