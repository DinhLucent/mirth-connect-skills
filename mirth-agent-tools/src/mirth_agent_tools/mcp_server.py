from __future__ import annotations

import sys
from typing import Any

from . import tools


def create_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the MCP extra first: python -m pip install -e '.[mcp]'") from exc

    server = FastMCP("mirth-agent-tools")

    @server.tool(name="mirth.health_check")
    def health_check() -> dict[str, Any]:
        return tools.health_check()

    @server.tool(name="mirth.discover_api")
    def discover_api() -> dict[str, Any]:
        return tools.discover()

    @server.tool(name="mirth.get_server_info")
    def get_server_info() -> dict[str, Any]:
        return tools.get_server_info()

    @server.tool(name="mirth.list_channels")
    def list_channels() -> dict[str, Any]:
        return tools.list_channels()

    @server.tool(name="mirth.get_channel")
    def get_channel(channel_id: str) -> dict[str, Any]:
        return tools.get_channel(channel_id)

    @server.tool(name="mirth.export_channel")
    def export_channel(channel_id: str) -> dict[str, Any]:
        return tools.export_channel(channel_id)

    @server.tool(name="mirth.import_channel")
    def import_channel(channel_xml: str, override: bool = True, deploy: bool = False, approval_token: str | None = None) -> dict[str, Any]:
        return tools.import_channel(channel_xml, override=override, deploy=deploy, approval_token=approval_token)

    @server.tool(name="mirth.update_channel")
    def update_channel(channel_id: str, channel_xml: str, override: bool = True, deploy: bool = False, approval_token: str | None = None) -> dict[str, Any]:
        return tools.update_channel(channel_id, channel_xml, override=override, deploy=deploy, approval_token=approval_token)

    @server.tool(name="mirth.delete_channel")
    def delete_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.delete_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.deploy_channel")
    def deploy_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.deploy_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.undeploy_channel")
    def undeploy_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.undeploy_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.redeploy_all")
    def redeploy_all(approval_token: str | None = None) -> dict[str, Any]:
        return tools.redeploy_all(approval_token=approval_token)

    @server.tool(name="mirth.start_channel")
    def start_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.start_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.stop_channel")
    def stop_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.stop_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.pause_channel")
    def pause_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.pause_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.resume_channel")
    def resume_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.resume_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.halt_channel")
    def halt_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.halt_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.get_channel_status")
    def get_channel_status(channel_id: str | None = None) -> dict[str, Any]:
        return tools.get_channel_status(channel_id)

    @server.tool(name="mirth.get_channel_statistics")
    def get_channel_statistics(channel_id: str | None = None) -> dict[str, Any]:
        return tools.get_channel_statistics(channel_id)

    @server.tool(name="mirth.get_messages")
    def get_messages(channel_id: str, limit: int = 20, include_content: bool = False, status: str | None = None) -> dict[str, Any]:
        return tools.get_messages(channel_id, limit=limit, include_content=include_content, status=status)

    @server.tool(name="mirth.get_message_count")
    def get_message_count(channel_id: str, status: str | None = None) -> dict[str, Any]:
        return tools.get_message_count(channel_id, status=status)

    @server.tool(name="mirth.remove_messages")
    def remove_messages(channel_id: str, status: str | None = None, approval_token: str | None = None) -> dict[str, Any]:
        return tools.remove_messages(channel_id, status=status, approval_token=approval_token)

    @server.tool(name="mirth.clear_statistics")
    def clear_statistics(channel_id: str | None = None, approval_token: str | None = None) -> dict[str, Any]:
        return tools.clear_statistics(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.list_code_templates")
    def list_code_templates() -> dict[str, Any]:
        return tools.list_code_templates()

    @server.tool(name="mirth.update_code_template")
    def update_code_template(code_template_id: str, code_template_xml: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.update_code_template(code_template_id, code_template_xml, approval_token=approval_token)

    @server.tool(name="mirth.list_extensions")
    def list_extensions() -> dict[str, Any]:
        return tools.list_extensions()

    @server.tool(name="mirth.get_extension_status")
    def get_extension_status(extension_name: str) -> dict[str, Any]:
        return tools.get_extension_status(extension_name)

    @server.tool(name="mirth.backup_all_channels")
    def backup_all_channels() -> dict[str, Any]:
        return tools.backup_all_channels()

    @server.tool(name="mirth.restore_channel")
    def restore_channel(backup_path: str, override: bool = True, deploy: bool = False, approval_token: str | None = None) -> dict[str, Any]:
        return tools.restore_channel(backup_path, override=override, deploy=deploy, approval_token=approval_token)

    @server.tool(name="mirth.diff_channel_xml")
    def diff_channel_xml(old_xml: str, new_xml: str) -> dict[str, Any]:
        return tools.diff_channel_xml(old_xml, new_xml)

    @server.tool(name="mirth.run_cli_command")
    def run_cli_command(command: str, approval_token: str | None = None) -> dict[str, Any]:
        return tools.run_cli_command(command, approval_token=approval_token)

    @server.tool(name="mirth.read_server_logs")
    def read_server_logs(log_path: str, tail_lines: int = 200) -> dict[str, Any]:
        return tools.read_server_logs(log_path, tail_lines=tail_lines)

    @server.tool(name="mirth.plan_operation")
    def plan_operation(
        operation: str,
        channel_id: str | None = None,
        deploy: bool = False,
        include_content: bool = False,
        status: str | None = None,
    ) -> dict[str, Any]:
        return tools.plan_operation(
            operation,
            channel_id=channel_id,
            deploy=deploy,
            include_content=include_content,
            status=status,
        )

    @server.tool(name="mirth.execute_operation")
    def execute_operation(
        plan: dict[str, Any],
        channel_xml: str | None = None,
        backup_path: str | None = None,
        code_template_id: str | None = None,
        code_template_xml: str | None = None,
        approval_token: str | None = None,
    ) -> dict[str, Any]:
        return tools.execute_operation(
            plan,
            channel_xml=channel_xml,
            backup_path=backup_path,
            code_template_id=code_template_id,
            code_template_xml=code_template_xml,
            approval_token=approval_token,
        )

    return server


def main() -> int:
    server = create_server()
    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
