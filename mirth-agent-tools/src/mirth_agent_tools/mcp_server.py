from __future__ import annotations

import sys
from typing import Any

from . import tools


def _try_import_annotations() -> type | None:
    """Return ToolAnnotations class if available, else None."""
    try:
        from mcp.types import ToolAnnotations
        return ToolAnnotations
    except (ImportError, AttributeError):
        return None


def _make_annotation(*, read_only: bool = True, destructive: bool = False) -> dict[str, Any]:
    """Build @server.tool kwargs for ToolAnnotations when the MCP SDK supports it."""
    cls = _try_import_annotations()
    if cls is None:
        return {}
    return {"annotations": cls(readOnlyHint=read_only, destructiveHint=destructive)}


READONLY = dict(read_only=True, destructive=False)
WRITE = dict(read_only=False, destructive=False)
DESTRUCTIVE = dict(read_only=False, destructive=True)


def create_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the MCP extra first: python -m pip install -e '.[mcp]'") from exc

    server = FastMCP("mirth-agent-tools")

    # ── Read-only tools ──────────────────────────────────────────────

    @server.tool(name="mirth.health_check", **_make_annotation(**READONLY))
    def health_check() -> dict[str, Any]:
        """Check Mirth Connect server reachability and basic API health.

        Returns connection status, HTTP status code, and content type.
        Use this first to confirm the agent can reach Mirth before any other operation.
        """
        return tools.health_check()

    @server.tool(name="mirth.discover_api", **_make_annotation(**READONLY))
    def discover_api() -> dict[str, Any]:
        """Discover available REST API endpoints on the connected Mirth server.

        Returns detected routes and a common endpoint fallback map.
        Use after health_check to confirm which operations this Mirth version supports.
        """
        return tools.discover()

    @server.tool(name="mirth.get_server_info", **_make_annotation(**READONLY))
    def get_server_info() -> dict[str, Any]:
        """Get Mirth Connect server version, OS, JVM, and database information.

        Returns the raw server info XML from /api/server/info.
        """
        return tools.get_server_info()

    @server.tool(name="mirth.list_channels", **_make_annotation(**READONLY))
    def list_channels() -> dict[str, Any]:
        """List all channels configured on the Mirth server.

        Returns channel XML containing id, name, and configuration for every channel.
        Use this to discover channel IDs before channel-specific operations.
        """
        return tools.list_channels()

    @server.tool(name="mirth.get_channel", **_make_annotation(**READONLY))
    def get_channel(channel_id: str) -> dict[str, Any]:
        """Get the full XML configuration of a single Mirth channel.

        Args:
            channel_id: The UUID of the channel to retrieve.

        Returns the complete channel XML including source, destinations, and transformers.
        """
        return tools.get_channel(channel_id)

    @server.tool(name="mirth.export_channel", **_make_annotation(**READONLY))
    def export_channel(channel_id: str) -> dict[str, Any]:
        """Export a channel's XML configuration (same as get_channel, named for clarity).

        Args:
            channel_id: The UUID of the channel to export.

        Returns the complete channel XML for backup or transfer purposes.
        """
        return tools.export_channel(channel_id)

    @server.tool(name="mirth.get_channel_status", **_make_annotation(**READONLY))
    def get_channel_status(channel_id: str | None = None) -> dict[str, Any]:
        """Get deployment and runtime status for one or all channels.

        Args:
            channel_id: Optional UUID. If omitted, returns statuses for all channels.

        Returns status XML showing deployed/undeployed, started/stopped/paused state.
        """
        return tools.get_channel_status(channel_id)

    @server.tool(name="mirth.get_channel_statistics", **_make_annotation(**READONLY))
    def get_channel_statistics(channel_id: str | None = None) -> dict[str, Any]:
        """Get message processing statistics (received, filtered, sent, errored) for one or all channels.

        Args:
            channel_id: Optional UUID. If omitted, returns statistics for all channels.
        """
        return tools.get_channel_statistics(channel_id)

    @server.tool(name="mirth.get_messages", **_make_annotation(**READONLY))
    def get_messages(channel_id: str, limit: int = 20, include_content: bool = False, status: str | None = None) -> dict[str, Any]:
        """Retrieve recent messages from a channel's message history.

        Args:
            channel_id: The UUID of the channel.
            limit: Maximum number of messages to return (default 20).
            include_content: If true, include message content (PHI will be redacted if MIRTH_REDACT_PHI=true).
            status: Optional filter by message status (e.g. RECEIVED, SENT, ERROR).

        Message content is redacted/truncated according to MIRTH_REDACT_PHI and MIRTH_MAX_MESSAGE_CONTENT_CHARS.
        """
        return tools.get_messages(channel_id, limit=limit, include_content=include_content, status=status)

    @server.tool(name="mirth.get_message_count", **_make_annotation(**READONLY))
    def get_message_count(channel_id: str, status: str | None = None) -> dict[str, Any]:
        """Get the total message count for a channel, optionally filtered by status.

        Args:
            channel_id: The UUID of the channel.
            status: Optional message status filter (e.g. RECEIVED, SENT, ERROR).
        """
        return tools.get_message_count(channel_id, status=status)

    @server.tool(name="mirth.list_code_templates", **_make_annotation(**READONLY))
    def list_code_templates() -> dict[str, Any]:
        """List all code template libraries and templates on the Mirth server.

        Returns code template XML. Code templates contain reusable JavaScript/Java functions
        shared across channels.
        """
        return tools.list_code_templates()

    @server.tool(name="mirth.list_extensions", **_make_annotation(**READONLY))
    def list_extensions() -> dict[str, Any]:
        """List all installed Mirth Connect extensions (plugins, connectors, data types).

        Returns extension metadata. Use get_extension_status for individual extension details.
        """
        return tools.list_extensions()

    @server.tool(name="mirth.get_extension_status", **_make_annotation(**READONLY))
    def get_extension_status(extension_name: str) -> dict[str, Any]:
        """Get the status of a specific Mirth extension.

        Args:
            extension_name: Name of the extension to query.
        """
        return tools.get_extension_status(extension_name)

    @server.tool(name="mirth.diff_channel_xml", **_make_annotation(**READONLY))
    def diff_channel_xml(old_xml: str, new_xml: str) -> dict[str, Any]:
        """Compute a unified diff between two channel XML strings.

        Args:
            old_xml: The original channel XML.
            new_xml: The modified channel XML.

        Returns a unified diff showing added/removed/changed lines. No Mirth API call is made.
        """
        return tools.diff_channel_xml(old_xml, new_xml)

    @server.tool(name="mirth.read_server_logs", **_make_annotation(**READONLY))
    def read_server_logs(log_path: str, tail_lines: int = 200) -> dict[str, Any]:
        """Read the tail of a Mirth server log file.

        Args:
            log_path: Absolute path to the Mirth log file on the local filesystem.
            tail_lines: Number of lines to return from the end of the file (default 200).

        The log file must be accessible from the agent's filesystem.
        """
        return tools.read_server_logs(log_path, tail_lines=tail_lines)

    @server.tool(name="mirth.plan_operation", **_make_annotation(**READONLY))
    def plan_operation(
        operation: str,
        channel_id: str | None = None,
        deploy: bool = False,
        include_content: bool = False,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Generate a safe execution plan for a Mirth operation without making any API calls.

        Args:
            operation: The operation to plan (e.g. deploy_channel, update_channel, delete_channel).
            channel_id: The channel UUID (required for most operations).
            deploy: Whether to deploy after write operations.
            include_content: Whether to include message content for get_messages.
            status: Message status filter for message operations.

        Returns a structured plan with prechecks, safety classification, rollback strategy,
        and approval requirements. Use execute_operation to run the plan.
        """
        return tools.plan_operation(
            operation,
            channel_id=channel_id,
            deploy=deploy,
            include_content=include_content,
            status=status,
        )

    # ── Write tools (require MIRTH_FULL_ACCESS=true) ─────────────────

    @server.tool(name="mirth.import_channel", **_make_annotation(**WRITE))
    def import_channel(channel_xml: str, override: bool = True, deploy: bool = False, approval_token: str | None = None) -> dict[str, Any]:
        """Import a channel from XML into the Mirth server.

        Args:
            channel_xml: Complete channel XML to import.
            override: If true, overwrite existing channel with same ID (default true).
            deploy: If true, redeploy all channels after import.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true. Creates a full backup of all channels before import.
        Audit: Logged to audit.jsonl.
        """
        return tools.import_channel(channel_xml, override=override, deploy=deploy, approval_token=approval_token)

    @server.tool(name="mirth.update_channel", **_make_annotation(**WRITE))
    def update_channel(channel_id: str, channel_xml: str, override: bool = True, deploy: bool = False, approval_token: str | None = None) -> dict[str, Any]:
        """Update an existing channel's XML configuration.

        Args:
            channel_id: The UUID of the channel to update.
            channel_xml: The new complete channel XML.
            override: If true, override revision conflicts (default true).
            deploy: If true, deploy the channel after update.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true. Creates backup and returns a diff of changes.
        Audit: Logged to audit.jsonl.
        """
        return tools.update_channel(channel_id, channel_xml, override=override, deploy=deploy, approval_token=approval_token)

    @server.tool(name="mirth.deploy_channel", **_make_annotation(**WRITE))
    def deploy_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        """Deploy a channel so it starts processing messages.

        Args:
            channel_id: The UUID of the channel to deploy.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true. Creates backup before deploy.
        Audit: Logged to audit.jsonl.
        """
        return tools.deploy_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.undeploy_channel", **_make_annotation(**WRITE))
    def undeploy_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        """Undeploy a channel to stop it from processing messages.

        Args:
            channel_id: The UUID of the channel to undeploy.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true. Creates backup before undeploy.
        Audit: Logged to audit.jsonl.
        """
        return tools.undeploy_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.start_channel", **_make_annotation(**WRITE))
    def start_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        """Start a deployed channel so it begins accepting messages.

        Args:
            channel_id: The UUID of the channel to start.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true.
        """
        return tools.start_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.stop_channel", **_make_annotation(**WRITE))
    def stop_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        """Stop a running channel so it stops accepting new messages.

        Args:
            channel_id: The UUID of the channel to stop.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true.
        """
        return tools.stop_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.pause_channel", **_make_annotation(**WRITE))
    def pause_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        """Pause a running channel. The channel remains deployed but stops processing.

        Args:
            channel_id: The UUID of the channel to pause.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true.
        """
        return tools.pause_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.resume_channel", **_make_annotation(**WRITE))
    def resume_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        """Resume a paused channel so it continues processing messages.

        Args:
            channel_id: The UUID of the channel to resume.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true.
        """
        return tools.resume_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.halt_channel", **_make_annotation(**WRITE))
    def halt_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        """Force-halt a channel immediately, interrupting any in-flight messages.

        Args:
            channel_id: The UUID of the channel to halt.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true. Use stop_channel for graceful shutdown.
        """
        return tools.halt_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.update_code_template", **_make_annotation(**WRITE))
    def update_code_template(code_template_id: str, code_template_xml: str, approval_token: str | None = None) -> dict[str, Any]:
        """Update a code template library entry on the Mirth server.

        Args:
            code_template_id: The UUID of the code template to update.
            code_template_xml: The new code template XML.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true.
        Audit: Logged to audit.jsonl.
        """
        return tools.update_code_template(code_template_id, code_template_xml, approval_token=approval_token)

    @server.tool(name="mirth.backup_all_channels", **_make_annotation(**READONLY))
    def backup_all_channels() -> dict[str, Any]:
        """Create a local XML backup of every channel on the Mirth server.

        Backups are saved to the configured MIRTH_BACKUP_DIR with timestamped filenames.
        This is a read-only operation (reads channels, writes to local disk only).
        """
        return tools.backup_all_channels()

    @server.tool(name="mirth.restore_channel", **_make_annotation(**WRITE))
    def restore_channel(backup_path: str, override: bool = True, deploy: bool = False, approval_token: str | None = None) -> dict[str, Any]:
        """Restore a channel from a local XML backup file.

        Args:
            backup_path: Path to the backup XML file on the local filesystem.
            override: If true, overwrite existing channel with same ID (default true).
            deploy: If true, redeploy all channels after restore.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true.
        Audit: Logged to audit.jsonl.
        """
        return tools.restore_channel(backup_path, override=override, deploy=deploy, approval_token=approval_token)

    @server.tool(name="mirth.run_cli_command", **_make_annotation(**WRITE))
    def run_cli_command(command: str, approval_token: str | None = None) -> dict[str, Any]:
        """Run a Mirth mccommand CLI command as fallback when REST API is unavailable.

        Args:
            command: The mccommand action and arguments (e.g. 'export -c channelId').
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true and MIRTH_ENABLE_CLI_FALLBACK=true.
        Only commands in MIRTH_CLI_ALLOWED_COMMANDS are permitted.
        """
        return tools.run_cli_command(command, approval_token=approval_token)

    # ── Destructive tools (require MIRTH_ALLOW_DESTRUCTIVE=true) ─────

    @server.tool(name="mirth.delete_channel", **_make_annotation(**DESTRUCTIVE))
    def delete_channel(channel_id: str, approval_token: str | None = None) -> dict[str, Any]:
        """Delete a channel from the Mirth server.

        Args:
            channel_id: The UUID of the channel to delete.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true AND MIRTH_ALLOW_DESTRUCTIVE=true.
        The channel is undeployed and backed up before deletion.
        Audit: Logged to audit.jsonl.
        """
        return tools.delete_channel(channel_id, approval_token=approval_token)

    @server.tool(name="mirth.redeploy_all", **_make_annotation(**DESTRUCTIVE))
    def redeploy_all(approval_token: str | None = None) -> dict[str, Any]:
        """Redeploy all channels on the Mirth server.

        Args:
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true AND MIRTH_ALLOW_DESTRUCTIVE=true.
        All channels are backed up before redeployment. This briefly interrupts all message processing.
        Audit: Logged to audit.jsonl.
        """
        return tools.redeploy_all(approval_token=approval_token)

    @server.tool(name="mirth.remove_messages", **_make_annotation(**DESTRUCTIVE))
    def remove_messages(channel_id: str, status: str | None = None, approval_token: str | None = None) -> dict[str, Any]:
        """Remove messages from a channel's message store.

        Args:
            channel_id: The UUID of the channel.
            status: Optional status filter — only remove messages with this status.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true AND MIRTH_ALLOW_DESTRUCTIVE=true.
        Returns message count before and after removal.
        Audit: Logged to audit.jsonl.
        """
        return tools.remove_messages(channel_id, status=status, approval_token=approval_token)

    @server.tool(name="mirth.clear_statistics", **_make_annotation(**DESTRUCTIVE))
    def clear_statistics(channel_id: str | None = None, approval_token: str | None = None) -> dict[str, Any]:
        """Clear message processing statistics for one or all channels.

        Args:
            channel_id: Optional UUID. If omitted, clears statistics for all channels.
            approval_token: Required when MIRTH_REQUIRE_APPROVAL=true.

        Safety: Requires MIRTH_FULL_ACCESS=true AND MIRTH_ALLOW_DESTRUCTIVE=true.
        Returns statistics snapshot before clearing.
        Audit: Logged to audit.jsonl.
        """
        return tools.clear_statistics(channel_id, approval_token=approval_token)

    # ── Orchestration tool ───────────────────────────────────────────

    @server.tool(name="mirth.execute_operation", **_make_annotation(**WRITE))
    def execute_operation(
        plan: dict[str, Any],
        channel_xml: str | None = None,
        backup_path: str | None = None,
        code_template_id: str | None = None,
        code_template_xml: str | None = None,
        approval_token: str | None = None,
    ) -> dict[str, Any]:
        """Execute a previously generated operation plan from plan_operation.

        Args:
            plan: The plan dict returned by mirth.plan_operation.
            channel_xml: Channel XML for import/update operations.
            backup_path: Backup file path for restore operations.
            code_template_id: Code template UUID for update_code_template.
            code_template_xml: Code template XML for update_code_template.
            approval_token: Required when the plan indicates requires_approval=true.

        Safety: The plan determines whether write/destructive gates apply.
        Always call plan_operation first and review the plan before executing.
        """
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
