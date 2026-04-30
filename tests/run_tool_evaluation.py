from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "mirth-agent-tools" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mirth_agent_tools import tools
from mirth_agent_tools.cli_fallback import validate_cli_command
from mirth_agent_tools.config import Settings
from mirth_agent_tools.errors import MirthBlocked

from metrics import ScenarioMeasurement, score_measurements, timed_call
from mock_mirth_server import SAMPLE_CHANNEL_ID, running_mock_mirth
from scenarios import SCENARIOS, Scenario


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Mirth skill tool effectiveness against a local mock API.")
    parser.add_argument("--iterations", type=int, default=5, help="Maximum iterations per repeated scenario.")
    parser.add_argument("--output", default="tests/reports/latest-tool-evaluation.json")
    args = parser.parse_args()

    scratch = ROOT / "tests" / ".tmp" / "tool-evaluation"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    report_path = ROOT / args.output
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with running_mock_mirth() as (base_url, state):
        settings = Settings(
            base_url=base_url,
            username="admin",
            password="admin",
            verify_tls=False,
            environment="test",
            full_access=True,
            allow_destructive=True,
            allow_prod_write=True,
            backup_dir=scratch / "backups",
            log_dir=scratch / "logs",
            redact_phi=True,
            max_message_content_chars=2000,
        )
        dry_run_settings = Settings(
            base_url="http://127.0.0.1:1",
            username="admin",
            password="admin",
            verify_tls=False,
            environment="test",
            full_access=True,
            allow_destructive=True,
            dry_run=True,
            backup_dir=scratch / "dry-run-backups",
            log_dir=scratch / "dry-run-logs",
        )
        measurements = [run_scenario(scenario, settings, dry_run_settings, state, args.iterations) for scenario in SCENARIOS]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": score_measurements(measurements),
        "scenarios": [item.as_dict() for item in measurements],
        "report_path": str(report_path),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"Report: {report_path}")

    failed = [item for item in measurements if not item.ok]
    if failed:
        print("Failed scenarios:")
        for item in failed:
            print(f"- {item.name}: {'; '.join(item.errors)}")
        return 1
    return 0


def run_scenario(
    scenario: Scenario,
    settings: Settings,
    dry_run_settings: Settings,
    state: Any,
    max_iterations: int,
) -> ScenarioMeasurement:
    iterations = min(scenario.iterations, max_iterations)
    durations: list[float] = []
    errors: list[str] = []
    details: dict[str, Any] = {}
    before_requests = len(state.request_log)

    for _ in range(iterations):
        try:
            _, duration_ms = timed_call(lambda: execute_scenario(scenario.name, settings, dry_run_settings, state, details))
            durations.append(duration_ms)
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    request_delta = len(state.request_log) - before_requests
    p95_ms = sorted(durations)[min(len(durations) - 1, int(round((len(durations) - 1) * 0.95)))] if durations else 0.0
    expected_max_requests = scenario.max_requests_per_iteration * iterations
    if request_delta > expected_max_requests:
        errors.append(f"request count {request_delta} exceeded expected {expected_max_requests}")
    if p95_ms > scenario.max_p95_ms:
        errors.append(f"p95 {p95_ms:.3f}ms exceeded {scenario.max_p95_ms:.3f}ms")

    return ScenarioMeasurement(
        name=scenario.name,
        category=scenario.category,
        iterations=iterations,
        ok=not errors,
        durations_ms=durations,
        request_count_delta=request_delta,
        errors=errors,
        details=details,
    )


def execute_scenario(
    name: str,
    settings: Settings,
    dry_run_settings: Settings,
    state: Any,
    details: dict[str, Any],
) -> None:
    scenario_map: dict[str, Callable[[], None]] = {
        "health_check": lambda: assert_tool_ok(tools.health_check(settings=settings)),
        "discover_api": lambda: assert_tool_ok(tools.discover(settings=settings)),
        "list_channels": lambda: assert_contains(assert_tool_ok(tools.list_channels(settings=settings)), SAMPLE_CHANNEL_ID),
        "get_channel": lambda: assert_contains(assert_tool_ok(tools.get_channel(SAMPLE_CHANNEL_ID, settings=settings)), SAMPLE_CHANNEL_ID),
        "status_and_statistics": lambda: (
            assert_contains(assert_tool_ok(tools.get_channel_status(SAMPLE_CHANNEL_ID, settings=settings)), "STARTED"),
            assert_contains(assert_tool_ok(tools.get_channel_statistics(SAMPLE_CHANNEL_ID, settings=settings)), "received"),
        ),
        "messages_metadata": lambda: assert_contains(
            assert_tool_ok(tools.get_messages(SAMPLE_CHANNEL_ID, include_content=False, settings=settings)),
            "<messageId>1</messageId>",
        ),
        "messages_content_redaction": lambda: check_redaction(settings),
        "deploy_backup_audit": lambda: check_deploy_backup_audit(settings, details),
        "update_backup_diff_audit": lambda: check_update_backup_diff_audit(settings, details),
        "remove_messages_counts": lambda: check_remove_messages(settings, state, details),
        "dry_run_no_http_write": lambda: check_dry_run_no_http(dry_run_settings, state, details),
        "plan_operation_local": lambda: check_plan_operation(details),
        "cli_whitelist_rejection": lambda: check_cli_whitelist(settings, details),
    }
    scenario_map[name]()


def assert_tool_ok(result: dict[str, Any]) -> Any:
    required = {"ok", "action", "environment", "data", "error", "needs_user_input", "user_question", "evidence"}
    missing = required - set(result)
    if missing:
        raise AssertionError(f"tool result missing keys: {sorted(missing)}")
    if not result["ok"]:
        raise AssertionError(f"{result['action']} failed: {result['error']}")
    return result["data"]


def assert_contains(value: Any, expected: str) -> None:
    if expected not in str(value):
        raise AssertionError(f"expected {expected!r} in {str(value)[:500]!r}")


def check_redaction(settings: Settings) -> None:
    data = assert_tool_ok(tools.get_messages(SAMPLE_CHANNEL_ID, include_content=True, settings=settings))
    text = str(data)
    for forbidden in ("Doe^Jane", "19700101", "555-123-4567", "123-45-6789"):
        if forbidden in text:
            raise AssertionError(f"PHI was not redacted: {forbidden}")
    assert_contains(text, "[REDACTED")


def check_deploy_backup_audit(settings: Settings, details: dict[str, Any]) -> None:
    data = assert_tool_ok(tools.deploy_channel(SAMPLE_CHANNEL_ID, settings=settings))
    backup_path = Path(data["backup_path"])
    audit_path = settings.log_dir / "audit.jsonl"
    if not backup_path.exists():
        raise AssertionError(f"missing backup: {backup_path}")
    if not audit_path.exists():
        raise AssertionError(f"missing audit log: {audit_path}")
    details["deploy_backup_path"] = str(backup_path)
    details["audit_path"] = str(audit_path)


def check_update_backup_diff_audit(settings: Settings, details: dict[str, Any]) -> None:
    new_xml = (
        '<channel version="4.5.0">'
        f"<id>{SAMPLE_CHANNEL_ID}</id>"
        "<name>Sample Channel Updated</name>"
        "<description>Updated by evaluation</description>"
        "</channel>"
    )
    data = assert_tool_ok(tools.update_channel(SAMPLE_CHANNEL_ID, new_xml, settings=settings))
    if "Sample Channel Updated" not in data["diff"]:
        raise AssertionError("update diff did not include changed channel name")
    backup_path = Path(data["backup_path"])
    if not backup_path.exists():
        raise AssertionError(f"missing update backup: {backup_path}")
    details["update_backup_path"] = str(backup_path)


def check_remove_messages(settings: Settings, state: Any, details: dict[str, Any]) -> None:
    before = state.messages_removed
    data = assert_tool_ok(tools.remove_messages(SAMPLE_CHANNEL_ID, settings=settings))
    if state.messages_removed != before + 1:
        raise AssertionError("mock server did not record message removal")
    assert_contains(data["count_before"], "3")
    assert_contains(data["count_after"], "3")
    details["messages_removed"] = state.messages_removed


def check_dry_run_no_http(settings: Settings, state: Any, details: dict[str, Any]) -> None:
    before = len(state.request_log)
    data = assert_tool_ok(tools.deploy_channel(SAMPLE_CHANNEL_ID, settings=settings))
    after = len(state.request_log)
    if after != before:
        raise AssertionError("dry-run write unexpectedly called HTTP API")
    if data.get("dry_run") is not True:
        raise AssertionError("dry-run tool result did not report dry_run=true")
    details["dry_run_skipped"] = data["skipped"]


def check_plan_operation(details: dict[str, Any]) -> None:
    data = assert_tool_ok(tools.plan_operation("deploy_channel", channel_id=SAMPLE_CHANNEL_ID))
    if data["operation"] != "deploy_channel":
        raise AssertionError("plan_operation returned the wrong operation")
    if "backup_channel" not in data["prechecks"]:
        raise AssertionError("plan_operation did not include backup precheck")
    details["plan_requires_approval"] = data["requires_approval"]


def check_cli_whitelist(settings: Settings, details: dict[str, Any]) -> None:
    try:
        validate_cli_command(settings, "shell rm -rf /")
    except MirthBlocked as exc:
        details["cli_rejection"] = str(exc)
        return
    raise AssertionError("CLI whitelist accepted a disallowed command")


if __name__ == "__main__":
    raise SystemExit(main())
