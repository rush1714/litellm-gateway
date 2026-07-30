#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import http.client
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

DEFAULT_RESPONSES_API_VERSION = "2025-03-01-preview"
READ_CHUNK_SIZE = 65536

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class ProxyRequestError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def header_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token.strip().lower() for token in value.split(",") if token.strip()}


def is_responses_api_path(path: str) -> bool:
    """Return true when /responses is a path segment, not a substring."""
    request = urlsplit(path)
    return any(unquote(segment) == "responses" for segment in request.path.split("/") if segment)


def has_api_version(query: str) -> bool:
    return any(key == "api-version" for key, _ in parse_qsl(query, keep_blank_values=True))


def append_api_version(query: str, api_version: str) -> str:
    api_version_query = urlencode({"api-version": api_version})
    if not query:
        return api_version_query
    separator = "" if query.endswith("&") else "&"
    return f"{query}{separator}{api_version_query}"


def combine_queries(base_query: str, request_query: str) -> str:
    if base_query and request_query:
        return f"{base_query}&{request_query}"
    return base_query or request_query


def join_target_path(base_path: str, request_path: str) -> str:
    normalized_base = f"/{base_path.strip('/')}" if base_path.strip("/") else ""
    normalized_request = request_path if request_path.startswith("/") else f"/{request_path}"

    if not normalized_request or normalized_request == "/":
        return normalized_base or "/"
    request_includes_base = normalized_request == normalized_base or normalized_request.startswith(
        f"{normalized_base}/"
    )
    if normalized_base and request_includes_base:
        return normalized_request
    if not normalized_base:
        return normalized_request
    return f"{normalized_base.rstrip('/')}/{normalized_request.lstrip('/')}"


def has_header(headers: dict[str, str], name: str) -> bool:
    name = name.lower()
    return any(key.lower() == name for key in headers)


def target_host_header(target: object) -> str:
    hostname = target.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    return f"{hostname}:{target.port}" if target.port else hostname


def configured_timeout() -> float:
    value = os.environ.get("ICA_PROXY_TIMEOUT", "600")
    try:
        timeout = float(value)
    except ValueError as exc:
        raise ProxyRequestError(500, "ICA_PROXY_TIMEOUT must be a number") from exc
    if timeout <= 0:
        raise ProxyRequestError(500, "ICA_PROXY_TIMEOUT must be greater than zero")
    return timeout


class ICAResponsesProxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ICAResponsesProxy/1.0"

    def do_GET(self) -> None:
        self.forward()

    def do_HEAD(self) -> None:
        self.forward()

    def do_POST(self) -> None:
        self.forward()

    def do_PUT(self) -> None:
        self.forward()

    def do_PATCH(self) -> None:
        self.forward()

    def do_DELETE(self) -> None:
        self.forward()

    def do_OPTIONS(self) -> None:
        self.forward()

    def forward(self) -> None:
        conn: http.client.HTTPConnection | None = None
        response_started = False
        try:
            body = self.read_body()
            target_url = self.build_target_url()
            target = urlsplit(target_url)
            headers = self.build_headers(target, body)
            connection_cls = http.client.HTTPSConnection
            if target.scheme == "http":
                connection_cls = http.client.HTTPConnection
            timeout = configured_timeout()

            conn = connection_cls(target.hostname or "", port=target.port, timeout=timeout)
            path = urlunsplit(("", "", target.path or "/", target.query, ""))
            conn.request(self.command, path, body=body, headers=headers)
            response = conn.getresponse()

            self.send_response(response.status, response.reason)
            self.copy_response_headers(response)
            self.send_header("Connection", "close")
            self.end_headers()
            response_started = True

            if self.command != "HEAD":
                self.stream_response(response)
            self.close_connection = True
            self.log_message("%s %s -> %s %s", self.command, self.path, path, response.status)
        except ProxyRequestError as exc:
            if not response_started:
                self.send_json_error(exc.status, exc.message)
            else:
                self.log_error("proxy request error after response started: %s", exc.message)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception as exc:
            self.log_error("upstream proxy error: %s", exc)
            if not response_started:
                self.send_json_error(502, str(exc))
        finally:
            self.close_connection = True
            with contextlib.suppress(Exception):
                if conn is not None:
                    conn.close()

    def read_body(self) -> bytes | None:
        transfer_encoding = self.headers.get("Transfer-Encoding")
        if transfer_encoding and transfer_encoding.lower() != "identity":
            raise ProxyRequestError(
                501,
                "Transfer-Encoding is not supported by this proxy; send a Content-Length body",
            )

        content_lengths = self.headers.get_all("Content-Length", [])
        if not content_lengths:
            return None
        if len(set(content_lengths)) > 1:
            raise ProxyRequestError(400, "Conflicting Content-Length headers")

        try:
            content_length = int(content_lengths[-1])
        except ValueError as exc:
            raise ProxyRequestError(400, "Invalid Content-Length header") from exc
        if content_length < 0:
            raise ProxyRequestError(400, "Invalid Content-Length header")
        if content_length == 0:
            return b""
        return self.rfile.read(content_length)

    def build_headers(self, target: object, body: bytes | None) -> dict[str, str]:
        skipped_headers = {"host", "content-length", "expect", *HOP_BY_HOP_HEADERS}
        for value in self.headers.get_all("Connection", []):
            skipped_headers.update(header_tokens(value))

        headers: dict[str, str] = {}
        for key, value in self.headers.items():
            if key.lower() in skipped_headers:
                continue
            headers[key] = value

        if not has_header(headers, "Authorization") and os.environ.get("ICA_KEY"):
            headers["Authorization"] = f"Bearer {os.environ['ICA_KEY']}"
        if body is not None and not has_header(headers, "Content-Type"):
            headers["Content-Type"] = "application/json"
        if body is not None:
            headers["Content-Length"] = str(len(body))
        headers["Host"] = target_host_header(target)
        return headers

    def build_target_url(self) -> str:
        target_base = os.environ.get("ICA_PROXY_TARGET_BASE", "").strip()
        if not target_base:
            raise ProxyRequestError(500, "ICA_PROXY_TARGET_BASE is required")

        base = urlsplit(target_base)
        if base.scheme not in {"http", "https"} or not base.hostname:
            raise ProxyRequestError(500, "ICA_PROXY_TARGET_BASE must be an http(s) URL")
        try:
            _ = base.port
        except ValueError as exc:
            raise ProxyRequestError(500, "ICA_PROXY_TARGET_BASE has invalid port") from exc

        request = urlsplit(self.path)
        target_path = join_target_path(base.path, request.path or "/")
        query = combine_queries(base.query, request.query)
        api_version = os.environ.get("ICA_RESPONSES_API_VERSION", DEFAULT_RESPONSES_API_VERSION)
        if is_responses_api_path(request.path) and not has_api_version(query):
            query = append_api_version(query, api_version)

        return urlunsplit((base.scheme, base.netloc, target_path, query, ""))

    def copy_response_headers(self, response: http.client.HTTPResponse) -> None:
        response_headers = response.getheaders()
        skipped_headers = set(HOP_BY_HOP_HEADERS)
        for key, value in response_headers:
            if key.lower() == "connection":
                skipped_headers.update(header_tokens(value))

        for key, value in response_headers:
            if key.lower() in skipped_headers:
                continue
            self.send_header(key, value)

    def stream_response(self, response: http.client.HTTPResponse) -> None:
        while True:
            chunk = response.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            self.wfile.write(chunk)
            self.wfile.flush()

    def send_json_error(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(body)
        self.close_connection = True


def main() -> int:
    target_base = os.environ.get("ICA_PROXY_TARGET_BASE")
    if not target_base:
        print("ERROR: ICA_PROXY_TARGET_BASE is required", file=sys.stderr)
        return 2
    host = os.environ.get("ICA_PROXY_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("ICA_PROXY_PORT", "4101"))
        configured_timeout()
    except ProxyRequestError as exc:
        print(f"ERROR: {exc.message}", file=sys.stderr)
        return 2
    except ValueError:
        print("ERROR: ICA_PROXY_PORT must be an integer", file=sys.stderr)
        return 2

    api_version = os.environ.get("ICA_RESPONSES_API_VERSION", DEFAULT_RESPONSES_API_VERSION)
    try:
        server = ThreadingHTTPServer((host, port), ICAResponsesProxy)
    except OSError as exc:
        print(f"ERROR: failed to bind ICA proxy on {host}:{port}: {exc}", file=sys.stderr)
        return 2

    print(
        f"ICA responses proxy listening on http://{host}:{port} -> {target_base} "
        f"(responses api-version={api_version})",
        flush=True,
    )
    with server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("ICA responses proxy stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
