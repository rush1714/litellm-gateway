import importlib.util
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PROXY_PATH = ROOT_DIR / "deploy" / "scripts" / "ica-responses-proxy.py"

spec = importlib.util.spec_from_file_location("ica_responses_proxy", PROXY_PATH)
assert spec is not None
proxy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proxy)


@contextmanager
def patched_env(**updates: str) -> Iterator[None]:
    original = {key: os.environ.get(key) for key in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def build_target_url(path: str) -> str:
    handler = object.__new__(proxy.ICAResponsesProxy)
    handler.path = path
    return handler.build_target_url()


def assert_proxy_error(path: str, status: int, message: str) -> None:
    try:
        build_target_url(path)
    except proxy.ProxyRequestError as exc:
        assert exc.status == status
        assert exc.message == message
    else:
        raise AssertionError("expected ProxyRequestError")


def main() -> int:
    assert proxy.is_responses_api_path("/responses")
    assert proxy.is_responses_api_path("/responses/input_tokens")
    assert proxy.is_responses_api_path("/ica/v1/responses/input_tokens")
    assert proxy.is_responses_api_path("/ica/v1/responses?trace=1")
    assert proxy.is_responses_api_path("/ica/v1/responses#fragment")
    assert proxy.is_responses_api_path("/ica/v1/%72esponses/input_tokens")
    assert not proxy.is_responses_api_path("/chat/completions")
    assert not proxy.is_responses_api_path("/notresponses/input_tokens")
    assert not proxy.is_responses_api_path("/responses-v2/input_tokens")
    assert not proxy.is_responses_api_path("/ica/v1/Responses/input_tokens")

    assert proxy.join_target_path("/ica/v1", "/responses") == "/ica/v1/responses"
    assert proxy.join_target_path("/ica/v1/", "/responses") == "/ica/v1/responses"
    assert proxy.join_target_path("/ica/v1", "/ica/v1/responses") == "/ica/v1/responses"
    assert proxy.join_target_path("", "/responses") == "/responses"
    assert proxy.join_target_path("/ica/v1", "/") == "/ica/v1"

    with patched_env(
        ICA_PROXY_TARGET_BASE="https://api.example.test/ica/v1",
        ICA_RESPONSES_API_VERSION="2025-03-01-preview",
    ):
        target = build_target_url("/responses")
        assert target == "https://api.example.test/ica/v1/responses?api-version=2025-03-01-preview"

        target = build_target_url("/responses/input_tokens")
        assert target == (
            "https://api.example.test/ica/v1/responses/input_tokens?api-version=2025-03-01-preview"
        )

        target = build_target_url("/responses/input_tokens?api-version=existing")
        assert (
            target == "https://api.example.test/ica/v1/responses/input_tokens?api-version=existing"
        )

        target = build_target_url("/responses/input_tokens?foo=&bar=baz")
        assert target == (
            "https://api.example.test/ica/v1/responses/input_tokens"
            "?foo=&bar=baz&api-version=2025-03-01-preview"
        )

        target = build_target_url("/chat/completions")
        assert target == "https://api.example.test/ica/v1/chat/completions"

        target = build_target_url("/ica/v1/responses")
        assert target == "https://api.example.test/ica/v1/responses?api-version=2025-03-01-preview"

    with patched_env(
        ICA_PROXY_TARGET_BASE="https://api.example.test/ica/v1?subscription-key=abc",
        ICA_RESPONSES_API_VERSION="2025-03-01-preview",
    ):
        target = build_target_url("/responses?foo=bar")
        assert target == (
            "https://api.example.test/ica/v1/responses"
            "?subscription-key=abc&foo=bar&api-version=2025-03-01-preview"
        )

        target = build_target_url("/responses?api-version=existing&foo=bar")
        assert target == (
            "https://api.example.test/ica/v1/responses"
            "?subscription-key=abc&api-version=existing&foo=bar"
        )

    with patched_env(ICA_PROXY_TARGET_BASE="ftp://api.example.test/ica/v1"):
        assert_proxy_error("/responses", 500, "ICA_PROXY_TARGET_BASE must be an http(s) URL")

    with patched_env(ICA_PROXY_TARGET_BASE=""):
        assert_proxy_error("/responses", 500, "ICA_PROXY_TARGET_BASE is required")

    print("ICA responses proxy tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
