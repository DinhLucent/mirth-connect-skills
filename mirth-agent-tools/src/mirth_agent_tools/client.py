from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from .errors import MirthBlocked
from .xml_utils import diff_xml


class MirthClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_tls: bool = True,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.verify = verify_tls
        self.session.headers.update(
            {
                "X-Requested-With": "OpenAPI",
                "Accept": "application/xml, application/json, text/plain, */*",
            }
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: str | bytes | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.exceptions.SSLError as exc:
            raise MirthBlocked(
                f"TLS error: {exc}",
                "Is this Mirth server using a self-signed certificate? If this is dev, set MIRTH_VERIFY_TLS=false.",
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise MirthBlocked(
                f"Connection error: {exc}",
                "I cannot reach Mirth. Please check MIRTH_BASE_URL, port 8443, VPN/firewall, and whether Mirth is running.",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise MirthBlocked(
                f"Timeout: {exc}",
                "The Mirth API timed out. Should I increase MIRTH_TIMEOUT or should you check server load/network access?",
            ) from exc

        if response.status_code in (401, 403):
            raise MirthBlocked(
                f"Auth/permission error {response.status_code}: {response.text[:500]}",
                "The configured Mirth account is missing permission or has invalid credentials. Please provide an Administrator/API account or grant the agent account the needed rights.",
            )

        if response.status_code == 404:
            raise MirthBlocked(
                f"Endpoint not found: {method} {path}",
                f"Endpoint {path} does not exist on this Mirth version. Please provide the /api docs export or enable CLI fallback.",
            )

        response.raise_for_status()
        return response

    def health_check(self) -> dict[str, Any]:
        response = self._request("GET", "/api")
        return {
            "reachable": True,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "body_preview": response.text[:500],
        }

    def api_docs(self) -> str:
        response = self._request("GET", "/api")
        return response.text

    def get_server_info(self) -> str:
        response = self._request("GET", "/api/server/info")
        return response.text

    def list_channels(self) -> str:
        response = self._request("GET", "/api/channels", headers={"Accept": "application/xml"})
        return response.text

    def get_channel_xml(self, channel_id: str) -> str:
        response = self._request("GET", f"/api/channels/{channel_id}", headers={"Accept": "application/xml"})
        return response.text

    def import_channel_xml(self, channel_xml: str, override: bool = True) -> str:
        response = self._request(
            "POST",
            "/api/channels",
            params={"override": str(override).lower()},
            data=channel_xml.encode("utf-8"),
            headers={
                "Content-Type": "application/xml",
                "Accept": "application/xml, application/json",
            },
        )
        return response.text

    def update_channel_xml(self, channel_id: str, channel_xml: str, override: bool = True) -> str:
        response = self._request(
            "PUT",
            f"/api/channels/{channel_id}",
            params={"override": str(override).lower()},
            data=channel_xml.encode("utf-8"),
            headers={
                "Content-Type": "application/xml",
                "Accept": "application/xml, application/json",
            },
        )
        return response.text

    def delete_channel(self, channel_id: str) -> str:
        response = self._request("DELETE", f"/api/channels/{channel_id}")
        return response.text

    def deploy_channel(self, channel_id: str, return_errors: bool = True) -> str:
        response = self._request(
            "POST",
            f"/api/channels/{channel_id}/_deploy",
            params={"returnErrors": str(return_errors).lower()},
        )
        return response.text

    def undeploy_channel(self, channel_id: str, return_errors: bool = True) -> str:
        response = self._request(
            "POST",
            f"/api/channels/{channel_id}/_undeploy",
            params={"returnErrors": str(return_errors).lower()},
        )
        return response.text

    def redeploy_all(self, return_errors: bool = True) -> str:
        response = self._request(
            "POST",
            "/api/channels/_redeployAll",
            params={"returnErrors": str(return_errors).lower()},
        )
        return response.text

    def channel_action(self, channel_id: str, action: str) -> str:
        allowed = {"_start", "_stop", "_pause", "_resume", "_halt"}
        if action not in allowed:
            raise ValueError(f"Unsupported channel action: {action}")
        response = self._request("POST", f"/api/channels/{channel_id}/{action}")
        return response.text

    def get_channel_status(self, channel_id: str) -> str:
        response = self._request("GET", f"/api/channels/{channel_id}/status")
        return response.text

    def get_channel_statuses(self, include_undeployed: bool = True) -> str:
        response = self._request(
            "GET",
            "/api/channels/statuses",
            params={"includeUndeployed": str(include_undeployed).lower()},
        )
        return response.text

    def get_channel_statistics(self, channel_id: str | None = None) -> str:
        path = f"/api/channels/{channel_id}/statistics" if channel_id else "/api/channels/statistics"
        response = self._request("GET", path)
        return response.text

    def clear_statistics(self, channel_id: str | None = None) -> str:
        if channel_id:
            response = self._request("DELETE", f"/api/channels/{channel_id}/statistics")
        else:
            response = self._request("DELETE", "/api/channels/statistics")
        return response.text

    def get_messages(
        self,
        channel_id: str,
        limit: int = 20,
        include_content: bool = False,
        status: str | None = None,
    ) -> str:
        params: dict[str, Any] = {
            "limit": limit,
            "includeContent": str(include_content).lower(),
        }
        if status:
            params["status"] = status
        response = self._request("GET", f"/api/channels/{channel_id}/messages", params=params)
        return response.text

    def get_message_count(self, channel_id: str, status: str | None = None) -> str:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        response = self._request("GET", f"/api/channels/{channel_id}/messages/count", params=params)
        return response.text

    def remove_messages(self, channel_id: str, status: str | None = None) -> str:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        response = self._request("DELETE", f"/api/channels/{channel_id}/messages", params=params)
        return response.text

    def list_code_templates(self) -> str:
        response = self._request("GET", "/api/codeTemplates", headers={"Accept": "application/xml"})
        return response.text

    def update_code_template(self, code_template_id: str, code_template_xml: str) -> str:
        response = self._request(
            "PUT",
            f"/api/codeTemplates/{code_template_id}",
            data=code_template_xml.encode("utf-8"),
            headers={
                "Content-Type": "application/xml",
                "Accept": "application/xml, application/json",
            },
        )
        return response.text

    def list_extensions(self) -> str:
        response = self._request("GET", "/api/extensions")
        return response.text

    def get_extension_status(self, extension_name: str) -> str:
        response = self._request("GET", f"/api/extensions/{extension_name}/status")
        return response.text

    def backup_channel(self, channel_id: str, backup_dir: str | Path = "backups") -> Path:
        xml = self.get_channel_xml(channel_id)
        target_dir = Path(backup_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = target_dir / f"{channel_id}-{ts}.xml"
        path.write_text(xml, encoding="utf-8")
        return path

    def backup_all_channels(self, backup_dir: str | Path = "backups") -> list[Path]:
        from .xml_utils import parse_channel_list

        channels_xml = self.list_channels()
        paths: list[Path] = []
        for channel in parse_channel_list(channels_xml):
            if channel.id:
                paths.append(self.backup_channel(channel.id, backup_dir))
        return paths

    def restore_channel(self, backup_path: str | Path, override: bool = True) -> str:
        xml = Path(backup_path).read_text(encoding="utf-8")
        return self.import_channel_xml(xml, override=override)

    @staticmethod
    def diff_xml(old_xml: str, new_xml: str) -> str:
        return diff_xml(old_xml, new_xml)
