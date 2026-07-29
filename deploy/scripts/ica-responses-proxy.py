#!/usr/bin/env python3
import contextlib
import http.client
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class ICAResponsesProxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ICAResponsesProxy/1.0"

    def do_GET(self) -> None:
        self.forward()

    def do_POST(self) -> None:
        self.forward()

    def do_PUT(self) -> None:
        self.forward()

    def do_PATCH(self) -> None:
        self.forward()

    def do_DELETE(self) -> None:
        self.forward()

    def forward(self) -> None:
        target_url = self.build_target_url()
        target = urlsplit(target_url)
        body = self.read_body()
        headers = self.build_headers()
        connection_cls = (
            http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
        )
        port = target.port
        netloc = target.hostname or ""
        timeout = float(os.environ.get("ICA_PROXY_TIMEOUT", "600"))

        try:
            conn = connection_cls(netloc, port=port, timeout=timeout)
            path = urlunsplit(("", "", target.path or "/", target.query, ""))
            conn.request(self.command, path, body=body, headers=headers)
            response = conn.getresponse()
            self.send_response(response.status, response.reason)
            self.copy_response_headers(response)
            self.end_headers()
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
            self.close_connection = True
            self.log_message(
                "%s %s -> %s %s", self.command, self.path, target.path, response.status
            )
        except Exception as exc:
            self.send_json_error(502, str(exc))
        finally:
            with contextlib.suppress(Exception):
                conn.close()

    def read_body(self) -> bytes | None:
        content_length = self.headers.get("Content-Length")
        if not content_length:
            return None
        return self.rfile.read(int(content_length))

    def build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
        authorization = self.headers.get("Authorization")
        if authorization:
            headers["Authorization"] = authorization
        elif os.environ.get("ICA_KEY"):
            headers["Authorization"] = f"Bearer {os.environ['ICA_KEY']}"
        return headers

    def build_target_url(self) -> str:
        target_base = os.environ["ICA_PROXY_TARGET_BASE"].rstrip("/")
        api_version = os.environ.get("ICA_RESPONSES_API_VERSION", "2025-03-01-preview")
        base = urlsplit(target_base)
        request = urlsplit(self.path)
        target_path = f"{base.path.rstrip('/')}/{request.path.lstrip('/')}"
        query = parse_qsl(base.query, keep_blank_values=True) + parse_qsl(
            request.query, keep_blank_values=True
        )
        if request.path.rstrip("/").endswith("/responses") and not any(
            key == "api-version" for key, _ in query
        ):
            query.append(("api-version", api_version))
        return urlunsplit(
            (
                base.scheme,
                base.netloc,
                target_path,
                urlencode(query, doseq=True),
                "",
            )
        )

    def copy_response_headers(self, response: http.client.HTTPResponse) -> None:
        for key, value in response.getheaders():
            lower = key.lower()
            if lower in HOP_BY_HOP_HEADERS or lower == "content-length":
                continue
            self.send_header(key, value)

    def send_json_error(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True


def main() -> int:
    target_base = os.environ.get("ICA_PROXY_TARGET_BASE")
    if not target_base:
        print("ERROR: ICA_PROXY_TARGET_BASE is required", file=sys.stderr)
        return 2
    host = os.environ.get("ICA_PROXY_HOST", "127.0.0.1")
    port = int(os.environ.get("ICA_PROXY_PORT", "4101"))
    server = ThreadingHTTPServer((host, port), ICAResponsesProxy)
    api_version = os.environ.get("ICA_RESPONSES_API_VERSION", "2025-03-01-preview")
    print(
        f"ICA responses proxy listening on http://{host}:{port} -> {target_base} "
        f"(responses api-version={api_version})",
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
