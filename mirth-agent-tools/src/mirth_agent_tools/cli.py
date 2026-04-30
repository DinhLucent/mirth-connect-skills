from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import tools


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mirth-agent-tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health_check")
    subparsers.add_parser("discover_api")
    subparsers.add_parser("get_server_info")
    subparsers.add_parser("list_channels")
    subparsers.add_parser("backup_all_channels")
    subparsers.add_parser("list_code_templates")
    subparsers.add_parser("list_extensions")

    _channel_cmd(subparsers, "get_channel")
    _channel_cmd(subparsers, "export_channel")
    for name in ("delete_channel", "deploy_channel", "undeploy_channel", "start_channel", "stop_channel", "pause_channel", "resume_channel", "halt_channel"):
        _add_approval(_channel_cmd(subparsers, name))
    _channel_cmd(subparsers, "get_channel_status", required=False)
    _channel_cmd(subparsers, "get_channel_statistics", required=False)

    update = _channel_cmd(subparsers, "update_channel")
    update.add_argument("--xml-file", required=True)
    update.add_argument("--deploy", action="store_true")
    update.add_argument("--no-override", action="store_true")
    _add_approval(update)

    import_cmd = subparsers.add_parser("import_channel")
    import_cmd.add_argument("--xml-file", required=True)
    import_cmd.add_argument("--deploy", action="store_true")
    import_cmd.add_argument("--no-override", action="store_true")
    _add_approval(import_cmd)

    restore = subparsers.add_parser("restore_channel")
    restore.add_argument("--backup-path", required=True)
    restore.add_argument("--deploy", action="store_true")
    restore.add_argument("--no-override", action="store_true")
    _add_approval(restore)

    redeploy = subparsers.add_parser("redeploy_all")
    redeploy.set_defaults(command="redeploy_all")
    _add_approval(redeploy)

    messages = _channel_cmd(subparsers, "get_messages")
    messages.add_argument("--limit", type=int, default=20)
    messages.add_argument("--include-content", action="store_true")
    messages.add_argument("--status")

    count = _channel_cmd(subparsers, "get_message_count")
    count.add_argument("--status")

    remove = _channel_cmd(subparsers, "remove_messages")
    remove.add_argument("--status")
    _add_approval(remove)

    clear = _channel_cmd(subparsers, "clear_statistics", required=False)
    _add_approval(clear)

    code_template = subparsers.add_parser("update_code_template")
    code_template.add_argument("--code-template-id", required=True)
    code_template.add_argument("--xml-file", required=True)
    _add_approval(code_template)

    extension = subparsers.add_parser("get_extension_status")
    extension.add_argument("--extension-name", required=True)

    diff = subparsers.add_parser("diff_channel_xml")
    diff.add_argument("--old-xml-file", required=True)
    diff.add_argument("--new-xml-file", required=True)

    cli = subparsers.add_parser("run_cli_command")
    cli.add_argument("mccommand_args")
    _add_approval(cli)

    logs = subparsers.add_parser("read_server_logs")
    logs.add_argument("--log-path", required=True)
    logs.add_argument("--tail-lines", type=int, default=200)

    plan = subparsers.add_parser("plan_operation")
    plan.add_argument("operation")
    plan.add_argument("--channel-id")
    plan.add_argument("--deploy", action="store_true")
    plan.add_argument("--include-content", action="store_true")
    plan.add_argument("--status")

    execute = subparsers.add_parser("execute_operation")
    execute.add_argument("--plan-file", required=True)
    execute.add_argument("--xml-file")
    execute.add_argument("--backup-path")
    execute.add_argument("--code-template-id")
    execute.add_argument("--code-template-xml-file")
    _add_approval(execute)

    args = parser.parse_args(argv)
    result = _dispatch(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def _channel_cmd(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], name: str, required: bool = True) -> argparse.ArgumentParser:
    cmd = subparsers.add_parser(name)
    cmd.add_argument("--channel-id", required=required)
    return cmd


def _add_approval(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--approval-token")
    return parser


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    command = args.command
    if command == "health_check":
        return tools.health_check()
    if command == "discover_api":
        return tools.discover()
    if command == "get_server_info":
        return tools.get_server_info()
    if command == "list_channels":
        return tools.list_channels()
    if command == "get_channel":
        return tools.get_channel(args.channel_id)
    if command == "export_channel":
        return tools.export_channel(args.channel_id)
    if command == "import_channel":
        return tools.import_channel(_read(args.xml_file), override=not args.no_override, deploy=args.deploy, approval_token=args.approval_token)
    if command == "update_channel":
        return tools.update_channel(args.channel_id, _read(args.xml_file), override=not args.no_override, deploy=args.deploy, approval_token=args.approval_token)
    if command == "delete_channel":
        return tools.delete_channel(args.channel_id, approval_token=args.approval_token)
    if command == "deploy_channel":
        return tools.deploy_channel(args.channel_id, approval_token=args.approval_token)
    if command == "undeploy_channel":
        return tools.undeploy_channel(args.channel_id, approval_token=args.approval_token)
    if command == "redeploy_all":
        return tools.redeploy_all(approval_token=args.approval_token)
    if command in {"start_channel", "stop_channel", "pause_channel", "resume_channel", "halt_channel"}:
        return getattr(tools, command)(args.channel_id, approval_token=args.approval_token)
    if command == "get_channel_status":
        return tools.get_channel_status(args.channel_id)
    if command == "get_channel_statistics":
        return tools.get_channel_statistics(args.channel_id)
    if command == "get_messages":
        return tools.get_messages(args.channel_id, limit=args.limit, include_content=args.include_content, status=args.status)
    if command == "get_message_count":
        return tools.get_message_count(args.channel_id, status=args.status)
    if command == "remove_messages":
        return tools.remove_messages(args.channel_id, status=args.status, approval_token=args.approval_token)
    if command == "clear_statistics":
        return tools.clear_statistics(args.channel_id, approval_token=args.approval_token)
    if command == "list_code_templates":
        return tools.list_code_templates()
    if command == "update_code_template":
        return tools.update_code_template(args.code_template_id, _read(args.xml_file), approval_token=args.approval_token)
    if command == "list_extensions":
        return tools.list_extensions()
    if command == "get_extension_status":
        return tools.get_extension_status(args.extension_name)
    if command == "backup_all_channels":
        return tools.backup_all_channels()
    if command == "restore_channel":
        return tools.restore_channel(args.backup_path, override=not args.no_override, deploy=args.deploy, approval_token=args.approval_token)
    if command == "diff_channel_xml":
        return tools.diff_channel_xml(_read(args.old_xml_file), _read(args.new_xml_file))
    if command == "run_cli_command":
        return tools.run_cli_command(args.mccommand_args, approval_token=args.approval_token)
    if command == "read_server_logs":
        return tools.read_server_logs(args.log_path, tail_lines=args.tail_lines)
    if command == "plan_operation":
        return tools.plan_operation(args.operation, channel_id=args.channel_id, deploy=args.deploy, include_content=args.include_content, status=args.status)
    if command == "execute_operation":
        return tools.execute_operation(
            json.loads(_read(args.plan_file)),
            channel_xml=_read(args.xml_file) if args.xml_file else None,
            backup_path=args.backup_path,
            code_template_id=args.code_template_id,
            code_template_xml=_read(args.code_template_xml_file) if args.code_template_xml_file else None,
            approval_token=args.approval_token,
        )
    raise ValueError(f"Unsupported command: {command}")


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
