from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterator
from urllib.parse import parse_qs, urlparse


SAMPLE_CHANNEL_ID = "sample-channel-id"
SAMPLE_CHANNEL_NAME = "Sample Channel"


@dataclass
class MockMirthState:
    channel_xml: str = (
        '<channel version="4.5.0">'
        f"<id>{SAMPLE_CHANNEL_ID}</id>"
        f"<name>{SAMPLE_CHANNEL_NAME}</name>"
        "<description>Mock channel</description>"
        "</channel>"
    )
    request_log: list[dict[str, str]] = field(default_factory=list)
    deployments: int = 0
    undeployments: int = 0
    starts: int = 0
    stops: int = 0
    messages_removed: int = 0
    statistics_cleared: int = 0

    def record(self, method: str, path: str, query: str) -> None:
        self.request_log.append({"method": method, "path": path, "query": query})


class MockMirthHandler(BaseHTTPRequestHandler):
    server_version = "MockMirth/0.1"

    def do_GET(self) -> None:
        self._route("GET")

    def do_POST(self) -> None:
        self._route("POST")

    def do_PUT(self) -> None:
        self._route("PUT")

    def do_DELETE(self) -> None:
        self._route("DELETE")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _route(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parsed.query
        state: MockMirthState = self.server.state  # type: ignore[attr-defined]
        state.record(method, path, query)

        if method == "GET" and path == "/api":
            self._send_text(
                "\n".join(
                    [
                        "GET /api/channels",
                        "GET /api/channels/{channelId}",
                        "PUT /api/channels/{channelId}",
                        "POST /api/channels/{channelId}/_deploy",
                        "GET /api/channels/{channelId}/messages",
                        "GET /api/channels/{channelId}/messages/count",
                    ]
                )
            )
            return

        if method == "GET" and path == "/api/server/info":
            self._send_xml("<serverInfo><version>4.5.0</version><status>OK</status></serverInfo>")
            return

        if method == "GET" and path == "/api/channels":
            self._send_xml(f"<list>{state.channel_xml}</list>")
            return

        if method == "POST" and path == "/api/channels":
            state.channel_xml = self._read_body()
            self._send_xml("<response>imported</response>")
            return

        if method == "GET" and path == "/api/channels/statuses":
            self._send_xml(f"<statuses><channelStatus><channelId>{SAMPLE_CHANNEL_ID}</channelId><state>STARTED</state></channelStatus></statuses>")
            return

        if method == "GET" and path == "/api/channels/statistics":
            self._send_xml("<statistics><received>10</received><sent>9</sent><error>1</error></statistics>")
            return

        if method == "DELETE" and path == "/api/channels/statistics":
            state.statistics_cleared += 1
            self._send_xml("<response>statistics cleared</response>")
            return

        channel_prefix = f"/api/channels/{SAMPLE_CHANNEL_ID}"

        if method == "GET" and path == channel_prefix:
            self._send_xml(state.channel_xml)
            return

        if method == "PUT" and path == channel_prefix:
            state.channel_xml = self._read_body()
            self._send_xml("<response>updated</response>")
            return

        if method == "DELETE" and path == channel_prefix:
            self._send_xml("<response>deleted</response>")
            return

        if method == "POST" and path == f"{channel_prefix}/_deploy":
            state.deployments += 1
            self._send_xml("<response>deployed</response>")
            return

        if method == "POST" and path == f"{channel_prefix}/_undeploy":
            state.undeployments += 1
            self._send_xml("<response>undeployed</response>")
            return

        if method == "POST" and path in {f"{channel_prefix}/_start", f"{channel_prefix}/_resume"}:
            state.starts += 1
            self._send_xml("<response>started</response>")
            return

        if method == "POST" and path in {f"{channel_prefix}/_stop", f"{channel_prefix}/_pause", f"{channel_prefix}/_halt"}:
            state.stops += 1
            self._send_xml("<response>stopped</response>")
            return

        if method == "POST" and path == "/api/channels/_redeployAll":
            state.deployments += 1
            self._send_xml("<response>redeployed</response>")
            return

        if method == "GET" and path == f"{channel_prefix}/status":
            self._send_xml("<channelStatus><state>STARTED</state></channelStatus>")
            return

        if method == "GET" and path == f"{channel_prefix}/statistics":
            self._send_xml("<statistics><received>10</received><sent>9</sent><error>1</error></statistics>")
            return

        if method == "DELETE" and path == f"{channel_prefix}/statistics":
            state.statistics_cleared += 1
            self._send_xml("<response>statistics cleared</response>")
            return

        if method == "GET" and path == f"{channel_prefix}/messages/count":
            self._send_xml("<long>3</long>")
            return

        if method == "GET" and path == f"{channel_prefix}/messages":
            params = parse_qs(query)
            include_content = params.get("includeContent", ["false"])[0] == "true"
            content = (
                "PID|1||12345||Doe^Jane||19700101||||123 Main St||555-123-4567|||123-45-6789"
                if include_content
                else ""
            )
            self._send_xml(
                "<messages><message><messageId>1</messageId><status>RECEIVED</status>"
                f"<content>{content}</content></message></messages>"
            )
            return

        if method == "DELETE" and path == f"{channel_prefix}/messages":
            state.messages_removed += 1
            self._send_xml("<response>messages removed</response>")
            return

        if method == "GET" and path == "/api/codeTemplates":
            self._send_xml("<codeTemplates><codeTemplate><id>template-1</id></codeTemplate></codeTemplates>")
            return

        if method == "GET" and path == "/api/extensions":
            self._send_xml("<extensions><extension><name>mock</name></extension></extensions>")
            return

        self._send_text(f"not found: {method} {path}", status=404)

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length).decode("utf-8") if length else ""

    def _send_xml(self, body: str, status: int = 200) -> None:
        self._send(body, status, "application/xml")

    def _send_text(self, body: str, status: int = 200) -> None:
        self._send(body, status, "text/plain")

    def _send(self, body: str, status: int, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


@contextlib.contextmanager
def running_mock_mirth() -> Iterator[tuple[str, MockMirthState]]:
    state = MockMirthState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockMirthHandler)
    server.state = state  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
