# Mirth Agent Tools

Full-access Mirth Connect tool server for AI agents. It uses Mirth REST API first, prefers XML for channel operations, writes backups before write/destructive actions, and returns actionable questions when blocked.

## Install

```powershell
cd D:\MyProject\MirthSkills\mirth-agent-tools
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` or export the same environment variables before running tools.

## Local CLI

```powershell
mirth-agent-tools health_check
mirth-agent-tools list_channels
mirth-agent-tools export_channel --channel-id <id>
mirth-agent-tools deploy_channel --channel-id <id>
mirth-agent-tools get_messages --channel-id <id> --limit 10
```

All tool results use this shape:

```json
{
  "ok": true,
  "action": "mirth.health_check",
  "environment": "dev",
  "data": {},
  "error": null,
  "needs_user_input": false,
  "user_question": null,
  "evidence": []
}
```

## MCP Server

If the `mcp` package is installed:

```powershell
python -m pip install -e ".[mcp]"
mirth-agent-mcp
```

The server exposes the same controlled tool functions from `mirth_agent_tools.tools`.

## Safety Model

Write operations require `MIRTH_FULL_ACCESS=true`.

Destructive operations require `MIRTH_ALLOW_DESTRUCTIVE=true`.

Production write operations require both `MIRTH_ENV=prod` and `MIRTH_ALLOW_PROD_WRITE=true`.

Before channel update/import/delete/deploy/undeploy/redeploy-all and message/statistics destructive actions, the tool creates the best available backup or pre-action snapshot. Write/destructive actions are appended to `logs/audit.jsonl`.

## Tests

```powershell
python -m pytest
```
