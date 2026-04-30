from __future__ import annotations

import re
from typing import Any

from .client import MirthClient
from .errors import MirthBlocked


COMMON_ENDPOINTS = [
    "GET /api",
    "GET /api/server/info",
    "GET /api/channels",
    "GET /api/channels/statuses",
    "GET /api/channels/statistics",
    "POST /api/channels/{channelId}/_deploy",
    "POST /api/channels/{channelId}/_undeploy",
    "POST /api/channels/_redeployAll",
    "POST /api/channels/{channelId}/_start",
    "POST /api/channels/{channelId}/_stop",
    "POST /api/channels/{channelId}/_pause",
    "POST /api/channels/{channelId}/_resume",
    "POST /api/channels/{channelId}/_halt",
    "GET /api/channels/{channelId}/messages",
    "GET /api/channels/{channelId}/messages/count",
    "DELETE /api/channels/{channelId}/messages",
    "GET /api/codeTemplates",
    "GET /api/extensions",
]


def discover_api(client: MirthClient) -> dict[str, Any]:
    docs = client.api_docs()
    routes = sorted(set(_extract_routes(docs)))
    return {
        "docs_preview": docs[:1000],
        "detected_routes": routes,
        "common_endpoint_map": COMMON_ENDPOINTS,
        "note": "Use detected_routes first; common_endpoint_map is only a fallback map for known Mirth versions.",
    }


def endpoint_available(discovery: dict[str, Any], path_fragment: str) -> bool:
    routes = discovery.get("detected_routes") or []
    return any(path_fragment in route for route in routes)


def ask_for_api_docs(path: str) -> MirthBlocked:
    return MirthBlocked(
        f"Missing endpoint discovery for {path}",
        f"I cannot confirm endpoint {path} from this server. Please send the /api docs export or enable CLI fallback.",
    )


def _extract_routes(text: str) -> list[str]:
    patterns = [
        r"\b(?:GET|POST|PUT|DELETE|PATCH)\s+/api/[A-Za-z0-9_{}./-]+",
        r'["\'](/api/[A-Za-z0-9_{}./-]+)["\']',
    ]
    routes: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            routes.append(match.group(0).strip("\"'"))
    return routes
