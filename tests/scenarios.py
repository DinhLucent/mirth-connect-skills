from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    category: str
    iterations: int = 1
    max_p95_ms: float = 500.0
    max_requests_per_iteration: int = 5


SCENARIOS = [
    Scenario("health_check", "read", iterations=5, max_requests_per_iteration=1),
    Scenario("discover_api", "read", iterations=3, max_requests_per_iteration=1),
    Scenario("list_channels", "read", iterations=5, max_requests_per_iteration=1),
    Scenario("get_channel", "read", iterations=5, max_requests_per_iteration=1),
    Scenario("status_and_statistics", "read", iterations=3, max_requests_per_iteration=2),
    Scenario("messages_metadata", "read", iterations=3, max_requests_per_iteration=1),
    Scenario("messages_content_redaction", "privacy", iterations=1, max_requests_per_iteration=1),
    Scenario("deploy_backup_audit", "write", iterations=1, max_requests_per_iteration=2),
    Scenario("update_backup_diff_audit", "write", iterations=1, max_requests_per_iteration=3),
    Scenario("remove_messages_counts", "destructive", iterations=1, max_requests_per_iteration=3),
    Scenario("dry_run_no_http_write", "safety", iterations=1, max_requests_per_iteration=0),
    Scenario("plan_operation_local", "planning", iterations=5, max_requests_per_iteration=0),
    Scenario("cli_whitelist_rejection", "safety", iterations=1, max_requests_per_iteration=0),
]
