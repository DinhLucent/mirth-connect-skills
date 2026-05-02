from __future__ import annotations

import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

from .audit import write_audit_event
from .cli_fallback import run_cli_command as run_mccommand
from .client import MirthClient
from .config import Settings
from .discovery import discover_api
from .errors import MirthBlocked
from .redaction import redact_phi
from .safety import require_destructive_allowed, require_write_allowed
from .xml_utils import diff_xml

F = TypeVar("F", bound=Callable[..., dict[str, Any]])
BackupPath = str | Callable[[], str | None] | None


def tool_result(
    *,
    ok: bool,
    action: str,
    environment: str,
    data: Any = None,
    error: str | None = None,
    needs_user_input: bool = False,
    user_question: str | None = None,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "action": action,
        "environment": environment,
        "data": data,
        "error": error,
        "needs_user_input": needs_user_input,
        "user_question": user_question,
        "evidence": evidence or [],
    }


def make_client(settings: Settings | None = None) -> tuple[Settings, MirthClient]:
    active = settings or Settings.from_env()
    return active, MirthClient(**active.as_client_kwargs())


def run_tool(
    action: str,
    settings: Settings,
    fn: Callable[[MirthClient], Any],
    *,
    write: bool = False,
    audit_details: dict[str, Any] | None = None,
    channel_id: str | None = None,
    backup_path: BackupPath = None,
) -> dict[str, Any]:
    client = MirthClient(**settings.as_client_kwargs())
    if write and settings.dry_run:
        audit_path = write_audit_event(
            log_dir=settings.log_dir,
            environment=settings.environment,
            tool=action,
            actor=settings.actor,
            result="dry_run",
            channel_id=channel_id,
            backup_path=_resolve_backup_path(backup_path),
            details=audit_details,
        )
        return tool_result(
            ok=True,
            action=action,
            environment=settings.environment,
            data={"dry_run": True, "skipped": action},
            evidence=[f"Skipped {action} because MIRTH_DRY_RUN=true", f"Audit log: {audit_path}"],
        )
    try:
        data = fn(client)
        resolved_backup_path = _resolve_backup_path(backup_path)
        if not backup_path and isinstance(data, dict):
            detected_backup = data.get("backup_path") or data.get("backup_paths")
            if isinstance(detected_backup, list):
                resolved_backup_path = ",".join(str(path) for path in detected_backup)
            elif detected_backup:
                resolved_backup_path = str(detected_backup)
        if write:
            audit_path = write_audit_event(
                log_dir=settings.log_dir,
                environment=settings.environment,
                tool=action,
                actor=settings.actor,
                result="success",
                channel_id=channel_id,
                backup_path=resolved_backup_path,
                details=audit_details,
            )
            evidence = [f"Executed {action} through Mirth REST API", f"Audit log: {audit_path}"]
        else:
            evidence = [f"Executed {action} through Mirth REST API"]
        return tool_result(ok=True, action=action, environment=settings.environment, data=data, evidence=evidence)
    except MirthBlocked as exc:
        if write:
            write_audit_event(
                log_dir=settings.log_dir,
                environment=settings.environment,
                tool=action,
                actor=settings.actor,
                result="blocked",
                channel_id=channel_id,
                backup_path=_resolve_backup_path(backup_path),
                details={"error": str(exc)},
            )
        return tool_result(
            ok=False,
            action=action,
            environment=settings.environment,
            error=str(exc),
            needs_user_input=True,
            user_question=exc.user_question,
            evidence=exc.evidence,
        )
    except Exception as exc:
        if write:
            write_audit_event(
                log_dir=settings.log_dir,
                environment=settings.environment,
                tool=action,
                actor=settings.actor,
                result="error",
                channel_id=channel_id,
                backup_path=_resolve_backup_path(backup_path),
                details={"error": repr(exc)},
            )
        return tool_result(
            ok=False,
            action=action,
            environment=settings.environment,
            error=repr(exc),
            needs_user_input=True,
            user_question="The tool failed unexpectedly. Please provide the full tool/server log or allow health_check and discover_api first.",
        )


def _resolve_backup_path(backup_path: BackupPath) -> str | None:
    if callable(backup_path):
        return backup_path() or None
    return backup_path


def health_check(settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.health_check", active, lambda client: client.health_check())


def discover(settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.discover_api", active, discover_api)


def get_server_info(settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.get_server_info", active, lambda client: client.get_server_info())


def list_channels(settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.list_channels", active, lambda client: client.list_channels())


def get_channel(channel_id: str, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.get_channel", active, lambda client: client.get_channel_xml(channel_id))


def export_channel(channel_id: str, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.export_channel", active, lambda client: client.get_channel_xml(channel_id))


def import_channel(
    channel_xml: str,
    override: bool = True,
    deploy: bool = False,
    approval_token: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()
    backup_holder: dict[str, str] = {}

    def _run(client: MirthClient) -> dict[str, Any]:
        require_write_allowed(active, approval_token)
        pre_backup = client.backup_all_channels(active.backup_dir)
        backup_holder["path"] = ",".join(str(path) for path in pre_backup)
        response = client.import_channel_xml(channel_xml, override=override)
        deployed = None
        if deploy:
            deployed = client.redeploy_all()
        return {"response": response, "backup_paths": [str(path) for path in pre_backup], "deploy_response": deployed}

    return run_tool(
        "mirth.import_channel",
        active,
        _run,
        write=True,
        backup_path=lambda: backup_holder.get("path"),
        audit_details={"override": override, "deploy": deploy},
    )


def update_channel(
    channel_id: str,
    channel_xml: str,
    override: bool = True,
    deploy: bool = False,
    approval_token: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()
    backup_holder: dict[str, str] = {}

    def _run(client: MirthClient) -> dict[str, Any]:
        require_write_allowed(active, approval_token)
        old_xml = client.get_channel_xml(channel_id)
        backup = client.backup_channel(channel_id, active.backup_dir)
        backup_holder["path"] = str(backup)
        response = client.update_channel_xml(channel_id, channel_xml, override=override)
        deployed = client.deploy_channel(channel_id) if deploy else None
        return {
            "response": response,
            "backup_path": str(backup),
            "diff": diff_xml(old_xml, channel_xml),
            "deploy_response": deployed,
        }

    return run_tool(
        "mirth.update_channel",
        active,
        _run,
        write=True,
        channel_id=channel_id,
        backup_path=lambda: backup_holder.get("path"),
        audit_details={"override": override, "deploy": deploy},
    )


def delete_channel(channel_id: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    backup_holder: dict[str, str] = {}

    def _run(client: MirthClient) -> dict[str, Any]:
        require_destructive_allowed(active, approval_token)
        backup = client.backup_channel(channel_id, active.backup_dir)
        backup_holder["path"] = str(backup)
        undeploy_response = client.undeploy_channel(channel_id)
        delete_response = client.delete_channel(channel_id)
        return {"backup_path": str(backup), "undeploy_response": undeploy_response, "delete_response": delete_response}

    return run_tool("mirth.delete_channel", active, _run, write=True, channel_id=channel_id, backup_path=lambda: backup_holder.get("path"))


def deploy_channel(channel_id: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    backup_holder: dict[str, str] = {}

    def _run(client: MirthClient) -> dict[str, Any]:
        require_write_allowed(active, approval_token)
        backup = client.backup_channel(channel_id, active.backup_dir)
        backup_holder["path"] = str(backup)
        response = client.deploy_channel(channel_id)
        return {"backup_path": str(backup), "response": response}

    return run_tool("mirth.deploy_channel", active, _run, write=True, channel_id=channel_id, backup_path=lambda: backup_holder.get("path"))


def undeploy_channel(channel_id: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    backup_holder: dict[str, str] = {}

    def _run(client: MirthClient) -> dict[str, Any]:
        require_write_allowed(active, approval_token)
        backup = client.backup_channel(channel_id, active.backup_dir)
        backup_holder["path"] = str(backup)
        response = client.undeploy_channel(channel_id)
        return {"backup_path": str(backup), "response": response}

    return run_tool("mirth.undeploy_channel", active, _run, write=True, channel_id=channel_id, backup_path=lambda: backup_holder.get("path"))


def redeploy_all(approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    backup_holder: dict[str, str] = {}

    def _run(client: MirthClient) -> dict[str, Any]:
        require_destructive_allowed(active, approval_token)
        backups = client.backup_all_channels(active.backup_dir)
        backup_holder["path"] = ",".join(str(path) for path in backups)
        response = client.redeploy_all()
        return {"backup_paths": [str(path) for path in backups], "response": response}

    return run_tool("mirth.redeploy_all", active, _run, write=True, backup_path=lambda: backup_holder.get("path"))


def channel_lifecycle_action(
    action_name: str,
    channel_id: str,
    approval_token: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()
    action_map = {
        "start": "_start",
        "stop": "_stop",
        "pause": "_pause",
        "resume": "_resume",
        "halt": "_halt",
    }
    if action_name not in action_map:
        return tool_result(
            ok=False,
            action=f"mirth.{action_name}_channel",
            environment=active.environment,
            error=f"Unsupported lifecycle action: {action_name}",
            needs_user_input=True,
            user_question="Please choose one of start, stop, pause, resume, or halt.",
        )

    def _run(client: MirthClient) -> str:
        require_write_allowed(active, approval_token)
        return client.channel_action(channel_id, action_map[action_name])

    return run_tool(f"mirth.{action_name}_channel", active, _run, write=True, channel_id=channel_id)


def start_channel(channel_id: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    return channel_lifecycle_action("start", channel_id, approval_token, settings)


def stop_channel(channel_id: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    return channel_lifecycle_action("stop", channel_id, approval_token, settings)


def pause_channel(channel_id: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    return channel_lifecycle_action("pause", channel_id, approval_token, settings)


def resume_channel(channel_id: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    return channel_lifecycle_action("resume", channel_id, approval_token, settings)


def halt_channel(channel_id: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    return channel_lifecycle_action("halt", channel_id, approval_token, settings)


def get_channel_status(channel_id: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    if channel_id:
        return run_tool("mirth.get_channel_status", active, lambda client: client.get_channel_status(channel_id))
    return run_tool("mirth.get_channel_status", active, lambda client: client.get_channel_statuses())


def get_channel_statistics(channel_id: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.get_channel_statistics", active, lambda client: client.get_channel_statistics(channel_id))


def get_messages(
    channel_id: str,
    limit: int = 20,
    include_content: bool = False,
    status: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()
    result = run_tool(
        "mirth.get_messages",
        active,
        lambda client: client.get_messages(channel_id, limit=limit, include_content=include_content, status=status),
    )
    if result.get("ok") and include_content and active.redact_phi and isinstance(result.get("data"), str):
        result["data"] = redact_phi(result["data"], active.max_message_content_chars)
        result["evidence"].append("Redacted/truncated message content according to MIRTH_REDACT_PHI settings")
    return result


def get_message_count(channel_id: str, status: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.get_message_count", active, lambda client: client.get_message_count(channel_id, status=status))


def remove_messages(
    channel_id: str,
    status: str | None = None,
    approval_token: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()

    def _run(client: MirthClient) -> dict[str, Any]:
        require_destructive_allowed(active, approval_token)
        count_before = client.get_message_count(channel_id, status=status)
        response = client.remove_messages(channel_id, status=status)
        count_after = client.get_message_count(channel_id, status=status)
        return {"count_before": count_before, "response": response, "count_after": count_after}

    return run_tool("mirth.remove_messages", active, _run, write=True, channel_id=channel_id, audit_details={"status": status})


def clear_statistics(
    channel_id: str | None = None,
    approval_token: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()

    def _run(client: MirthClient) -> dict[str, Any]:
        require_destructive_allowed(active, approval_token)
        before = client.get_channel_statistics(channel_id)
        response = client.clear_statistics(channel_id)
        return {"statistics_before": before, "response": response}

    return run_tool("mirth.clear_statistics", active, _run, write=True, channel_id=channel_id)


def list_code_templates(settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.list_code_templates", active, lambda client: client.list_code_templates())


def update_code_template(
    code_template_id: str,
    code_template_xml: str,
    approval_token: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()

    def _run(client: MirthClient) -> str:
        require_write_allowed(active, approval_token)
        return client.update_code_template(code_template_id, code_template_xml)

    return run_tool("mirth.update_code_template", active, _run, write=True, audit_details={"code_template_id": code_template_id})


def list_extensions(settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.list_extensions", active, lambda client: client.list_extensions())


def get_extension_status(extension_name: str, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool("mirth.get_extension_status", active, lambda client: client.get_extension_status(extension_name))


def backup_all_channels(settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return run_tool(
        "mirth.backup_all_channels",
        active,
        lambda client: [str(path) for path in client.backup_all_channels(active.backup_dir)],
    )


def restore_channel(
    backup_path: str,
    override: bool = True,
    deploy: bool = False,
    approval_token: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()

    def _run(client: MirthClient) -> dict[str, Any]:
        require_write_allowed(active, approval_token)
        response = client.restore_channel(backup_path, override=override)
        deployed = client.redeploy_all() if deploy else None
        return {"response": response, "deploy_response": deployed}

    return run_tool("mirth.restore_channel", active, _run, write=True, backup_path=backup_path, audit_details={"deploy": deploy})


def diff_channel_xml(old_xml: str, new_xml: str, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    return tool_result(
        ok=True,
        action="mirth.diff_channel_xml",
        environment=active.environment,
        data={"diff": diff_xml(old_xml, new_xml)},
        evidence=["Computed local XML diff"],
    )


def run_cli_command(command: str, approval_token: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    def _run(_: MirthClient) -> dict[str, object]:
        require_write_allowed(active, approval_token)
        return run_mccommand(active, command)

    return run_tool("mirth.run_cli_command", active, _run, write=True)


def read_server_logs(log_path: str | Path, tail_lines: int = 200, settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()

    def _read(_: MirthClient) -> dict[str, Any]:
        path = Path(log_path)
        if not path.exists():
            raise MirthBlocked(
                f"Log file not found: {path}",
                "Please provide the absolute path to the Mirth server log file or mount it into this workspace.",
            )
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return {"path": str(path), "lines": lines[-tail_lines:]}

    return run_tool("mirth.read_server_logs", active, _read)


def plan_operation(
    operation: str,
    channel_id: str | None = None,
    deploy: bool = False,
    include_content: bool = False,
    status: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    active = settings
    environment = active.environment if active else os.getenv("MIRTH_ENV", "dev")
    operation = operation.strip()
    write_ops = {
        "import_channel",
        "update_channel",
        "deploy_channel",
        "undeploy_channel",
        "start_channel",
        "stop_channel",
        "pause_channel",
        "resume_channel",
        "halt_channel",
        "update_code_template",
        "restore_channel",
    }
    destructive_ops = {"delete_channel", "redeploy_all", "remove_messages", "clear_statistics"}

    plans: dict[str, list[str]] = {
        "deploy_channel": ["health_check", "discover_api", "get_channel", "backup_channel", "get_channel_status", "deploy_channel", "get_channel_status"],
        "undeploy_channel": ["health_check", "discover_api", "get_channel", "backup_channel", "undeploy_channel", "get_channel_status"],
        "update_channel": ["health_check", "discover_api", "get_channel", "backup_channel", "diff_channel_xml", "update_channel", "deploy_channel optional", "get_channel_status"],
        "import_channel": ["health_check", "discover_api", "backup_all_channels", "import_channel", "redeploy_all optional"],
        "delete_channel": ["health_check", "discover_api", "get_channel", "backup_channel", "undeploy_channel", "delete_channel"],
        "redeploy_all": ["health_check", "discover_api", "backup_all_channels", "redeploy_all", "get_channel_status"],
        "remove_messages": ["health_check", "discover_api", "get_message_count", "remove_messages", "get_message_count"],
        "clear_statistics": ["health_check", "discover_api", "get_channel_statistics", "clear_statistics", "get_channel_statistics"],
        "start_channel": ["health_check", "get_channel_status", "start_channel", "get_channel_status"],
        "stop_channel": ["health_check", "get_channel_status", "stop_channel", "get_channel_status"],
        "pause_channel": ["health_check", "get_channel_status", "pause_channel", "get_channel_status"],
        "resume_channel": ["health_check", "get_channel_status", "resume_channel", "get_channel_status"],
        "halt_channel": ["health_check", "get_channel_status", "halt_channel", "get_channel_status"],
        "get_messages": ["health_check", "get_message_count", "get_messages metadata-first"],
    }
    if operation not in plans:
        return tool_result(
            ok=False,
            action="mirth.plan_operation",
            environment=environment,
            error=f"Unsupported operation: {operation}",
            needs_user_input=True,
            user_question=f"Please choose one of: {', '.join(sorted(plans))}.",
        )

    needs_channel = operation not in {"import_channel", "redeploy_all"}
    if needs_channel and not channel_id:
        return tool_result(
            ok=False,
            action="mirth.plan_operation",
            environment=environment,
            error="Missing channel_id.",
            needs_user_input=True,
            user_question="Please provide the Mirth channel_id for this operation.",
        )

    destructive = operation in destructive_ops
    write = destructive or operation in write_ops
    requires_approval = write and (environment == "prod" or destructive or bool(active and active.require_approval))
    plan = {
        "operation": operation,
        "environment": environment,
        "channel_id": channel_id,
        "parameters": {
            "deploy": deploy,
            "include_content": include_content,
            "status": status,
        },
        "prechecks": plans[operation],
        "write": write,
        "destructive": destructive,
        "requires_approval": requires_approval,
        "dry_run": bool(active and active.dry_run),
        "rollback": _rollback_plan(operation, channel_id),
    }
    return tool_result(
        ok=True,
        action="mirth.plan_operation",
        environment=environment,
        data=plan,
        evidence=["Generated local operation plan; no Mirth API call was made"],
    )


def execute_operation(
    plan: dict[str, Any],
    channel_xml: str | None = None,
    backup_path: str | None = None,
    code_template_id: str | None = None,
    code_template_xml: str | None = None,
    approval_token: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    operation = str(plan.get("operation", "")).strip()
    channel_id = plan.get("channel_id")
    parameters = plan.get("parameters") or {}
    deploy = bool(parameters.get("deploy", False))
    status = parameters.get("status")
    include_content = bool(parameters.get("include_content", False))

    if operation == "deploy_channel":
        return deploy_channel(str(channel_id), approval_token=approval_token, settings=settings)
    if operation == "undeploy_channel":
        return undeploy_channel(str(channel_id), approval_token=approval_token, settings=settings)
    if operation == "update_channel":
        if channel_xml is None:
            return _missing_execute_input("mirth.execute_operation", "channel_xml is required for update_channel.")
        return update_channel(str(channel_id), channel_xml, deploy=deploy, approval_token=approval_token, settings=settings)
    if operation == "import_channel":
        if channel_xml is None:
            return _missing_execute_input("mirth.execute_operation", "channel_xml is required for import_channel.")
        return import_channel(channel_xml, deploy=deploy, approval_token=approval_token, settings=settings)
    if operation == "delete_channel":
        return delete_channel(str(channel_id), approval_token=approval_token, settings=settings)
    if operation == "redeploy_all":
        return redeploy_all(approval_token=approval_token, settings=settings)
    if operation == "remove_messages":
        return remove_messages(str(channel_id), status=status, approval_token=approval_token, settings=settings)
    if operation == "clear_statistics":
        return clear_statistics(str(channel_id) if channel_id else None, approval_token=approval_token, settings=settings)
    _lifecycle_dispatch = {
        "start_channel": start_channel,
        "stop_channel": stop_channel,
        "pause_channel": pause_channel,
        "resume_channel": resume_channel,
        "halt_channel": halt_channel,
    }
    if operation in _lifecycle_dispatch:
        return _lifecycle_dispatch[operation](str(channel_id), approval_token=approval_token, settings=settings)
    if operation == "get_messages":
        return get_messages(str(channel_id), include_content=include_content, status=status, settings=settings)
    if operation == "restore_channel":
        if backup_path is None:
            return _missing_execute_input("mirth.execute_operation", "backup_path is required for restore_channel.")
        return restore_channel(backup_path, deploy=deploy, approval_token=approval_token, settings=settings)
    if operation == "update_code_template":
        if code_template_id is None or code_template_xml is None:
            return _missing_execute_input("mirth.execute_operation", "code_template_id and code_template_xml are required.")
        return update_code_template(code_template_id, code_template_xml, approval_token=approval_token, settings=settings)

    return tool_result(
        ok=False,
        action="mirth.execute_operation",
        environment=os.getenv("MIRTH_ENV", "dev"),
        error=f"Unsupported operation: {operation}",
        needs_user_input=True,
        user_question="Please generate a plan with mirth.plan_operation before execution.",
    )


def _rollback_plan(operation: str, channel_id: str | None) -> dict[str, Any] | None:
    if operation in {"deploy_channel", "undeploy_channel", "update_channel", "delete_channel"}:
        return {"type": "restore_channel", "channel_id": channel_id, "backup_path": "returned by execution backup_path"}
    if operation in {"import_channel", "redeploy_all"}:
        return {"type": "restore_channel", "backup_path": "choose one of returned backup_paths"}
    return None


def _missing_execute_input(action: str, message: str) -> dict[str, Any]:
    return tool_result(
        ok=False,
        action=action,
        environment=os.getenv("MIRTH_ENV", "dev"),
        error=message,
        needs_user_input=True,
        user_question=message,
    )


def _standardize_entrypoint(action: str) -> Callable[[F], F]:
    def _decorate(fn: F) -> F:
        @wraps(fn)
        def _wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
            try:
                return fn(*args, **kwargs)
            except MirthBlocked as exc:
                return tool_result(
                    ok=False,
                    action=action,
                    environment=os.getenv("MIRTH_ENV", "dev"),
                    error=str(exc),
                    needs_user_input=True,
                    user_question=exc.user_question,
                    evidence=exc.evidence,
                )
            except Exception as exc:
                return tool_result(
                    ok=False,
                    action=action,
                    environment=os.getenv("MIRTH_ENV", "dev"),
                    error=repr(exc),
                    needs_user_input=True,
                    user_question="The tool failed before it could contact Mirth. Please check local configuration and logs.",
                )

        return cast(F, _wrapped)

    return _decorate


health_check = _standardize_entrypoint("mirth.health_check")(health_check)
discover = _standardize_entrypoint("mirth.discover_api")(discover)
get_server_info = _standardize_entrypoint("mirth.get_server_info")(get_server_info)
list_channels = _standardize_entrypoint("mirth.list_channels")(list_channels)
get_channel = _standardize_entrypoint("mirth.get_channel")(get_channel)
export_channel = _standardize_entrypoint("mirth.export_channel")(export_channel)
import_channel = _standardize_entrypoint("mirth.import_channel")(import_channel)
update_channel = _standardize_entrypoint("mirth.update_channel")(update_channel)
delete_channel = _standardize_entrypoint("mirth.delete_channel")(delete_channel)
deploy_channel = _standardize_entrypoint("mirth.deploy_channel")(deploy_channel)
undeploy_channel = _standardize_entrypoint("mirth.undeploy_channel")(undeploy_channel)
redeploy_all = _standardize_entrypoint("mirth.redeploy_all")(redeploy_all)
channel_lifecycle_action = _standardize_entrypoint("mirth.channel_lifecycle_action")(channel_lifecycle_action)
start_channel = _standardize_entrypoint("mirth.start_channel")(start_channel)
stop_channel = _standardize_entrypoint("mirth.stop_channel")(stop_channel)
pause_channel = _standardize_entrypoint("mirth.pause_channel")(pause_channel)
resume_channel = _standardize_entrypoint("mirth.resume_channel")(resume_channel)
halt_channel = _standardize_entrypoint("mirth.halt_channel")(halt_channel)
get_channel_status = _standardize_entrypoint("mirth.get_channel_status")(get_channel_status)
get_channel_statistics = _standardize_entrypoint("mirth.get_channel_statistics")(get_channel_statistics)
get_messages = _standardize_entrypoint("mirth.get_messages")(get_messages)
get_message_count = _standardize_entrypoint("mirth.get_message_count")(get_message_count)
remove_messages = _standardize_entrypoint("mirth.remove_messages")(remove_messages)
clear_statistics = _standardize_entrypoint("mirth.clear_statistics")(clear_statistics)
list_code_templates = _standardize_entrypoint("mirth.list_code_templates")(list_code_templates)
update_code_template = _standardize_entrypoint("mirth.update_code_template")(update_code_template)
list_extensions = _standardize_entrypoint("mirth.list_extensions")(list_extensions)
get_extension_status = _standardize_entrypoint("mirth.get_extension_status")(get_extension_status)
backup_all_channels = _standardize_entrypoint("mirth.backup_all_channels")(backup_all_channels)
restore_channel = _standardize_entrypoint("mirth.restore_channel")(restore_channel)
diff_channel_xml = _standardize_entrypoint("mirth.diff_channel_xml")(diff_channel_xml)
run_cli_command = _standardize_entrypoint("mirth.run_cli_command")(run_cli_command)
read_server_logs = _standardize_entrypoint("mirth.read_server_logs")(read_server_logs)
plan_operation = _standardize_entrypoint("mirth.plan_operation")(plan_operation)
execute_operation = _standardize_entrypoint("mirth.execute_operation")(execute_operation)
