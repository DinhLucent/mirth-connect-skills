from __future__ import annotations

from typing import Any

import pytest
import requests

from mirth_agent_tools.client import MirthClient
from mirth_agent_tools.errors import MirthBlocked


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "ok", headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {"content-type": "application/xml"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class FakeSession:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []
        self.auth = None
        self.verify = True
        self.headers: dict[str, str] = {}

    def request(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_request_sends_requested_with_header() -> None:
    client = MirthClient("https://mirth.local", "user", "pass", verify_tls=False)
    fake = FakeSession(FakeResponse(text="<api />"))
    fake.headers.update(client.session.headers)
    client.session = fake  # type: ignore[assignment]

    response = client._request("GET", "/api")

    assert response.text == "<api />"
    assert client.session.headers["X-Requested-With"] == "OpenAPI"
    assert fake.calls[0]["url"] == "https://mirth.local/api"
    assert fake.calls[0]["timeout"] == 30


def test_auth_error_becomes_blocked_question() -> None:
    client = MirthClient("https://mirth.local", "user", "pass")
    client.session = FakeSession(FakeResponse(status_code=403, text="forbidden"))  # type: ignore[assignment]

    with pytest.raises(MirthBlocked) as exc:
        client._request("GET", "/api/channels")

    assert "Auth/permission error 403" in str(exc.value)
    assert "Administrator/API account" in exc.value.user_question


def test_tls_error_becomes_blocked_question() -> None:
    client = MirthClient("https://mirth.local", "user", "pass")
    client.session = FakeSession(requests.exceptions.SSLError("bad cert"))  # type: ignore[assignment]

    with pytest.raises(MirthBlocked) as exc:
        client._request("GET", "/api")

    assert "TLS error" in str(exc.value)
    assert "MIRTH_VERIFY_TLS=false" in exc.value.user_question


def test_deploy_channel_uses_expected_endpoint() -> None:
    client = MirthClient("https://mirth.local", "user", "pass")
    fake = FakeSession(FakeResponse(text="deployed"))
    client.session = fake  # type: ignore[assignment]

    assert client.deploy_channel("abc") == "deployed"
    assert fake.calls[0]["method"] == "POST"
    assert fake.calls[0]["url"] == "https://mirth.local/api/channels/abc/_deploy"
    assert fake.calls[0]["params"] == {"returnErrors": "true"}
