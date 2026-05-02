# Mirth Connect Skills

Codex skill and Python tool server for operating Mirth Connect through controlled REST API tools, XML backup/restore, audit logs, rollback support, MCP, and CLI fallback.

Designed for agent-assisted Mirth operations: inspect, export, update, deploy, start/stop channels, read statistics and messages, with structured user prompts when credentials, permissions, endpoints, or safety gates block an action.

> Mirth Connect is a healthcare integration engine. Treat this repository as operational tooling: use a dedicated Mirth account, keep audit logs, and avoid returning raw PHI unless explicitly required.

## Features

- **Codex skill** for Mirth Connect operator workflows.
- **Python package** with REST-first Mirth client and local CLI.
- **MCP server** with ToolAnnotations (readOnlyHint/destructiveHint) and full docstrings for LLM agent discovery.
- **XML-first** channel export/import/update for version compatibility.
- **Backup-before-write** and rollback helpers for all write operations.
- **Audit trail** (JSONL) for write and destructive actions.
- **PHI redaction** for HL7 PID segments, email, phone, SSN, MRN, DOB.
- **Safety gates** for full access, destructive actions, production writes, and approval tokens.
- **Plan/Execute two-phase** workflow for safe operation planning.
- **CLI fallback** with command allowlist when REST API is unavailable.
- **Local test suite** with mock Mirth REST API and sandbox installer checks.

## Requirements

- Node.js 18 or newer.
- Python 3.10 or newer.
- Mirth Connect reachable over REST API, usually at `https://localhost:8443`.
- A dedicated Mirth user with permissions for the operations the agent performs.

## Quickstart

Full Mirth operator install:

```bash
npx github:DinhLucent/mirth-connect-skills full
```

This installs:

- Codex skill into `.agents/skills/mirth-connect-operator`
- Python tool server into `.mirth/mirth-agent-tools`
- Python dependencies with optional MCP extra
- Local `.env` from `.env.example`
- `.mirth/.gitignore` to protect credentials, backups, and logs

Then configure and verify:

```bash
cd .mirth/mirth-agent-tools
# Edit .env with your Mirth URL and credentials
mirth-agent-tools health_check
```

## Skill-Only Install

Using the shared Skills CLI (`mattpocock/skills` compatible):

```bash
npx skills@latest add DinhLucent/mirth-connect-skills
```

Non-interactive Codex install:

```bash
npx skills@latest add DinhLucent/mirth-connect-skills --agent codex --skill mirth-connect-operator -y --copy
```

This installs skill instructions only (no Python tools, MCP, or `.env`). Use the full installer for operational access.

## Tool-Server Install

```bash
# Minimal: skill + tool files only
npx github:DinhLucent/mirth-connect-skills init

# Full: skill + tools + pip install + MCP + .env
npx github:DinhLucent/mirth-connect-skills init --install-python --install-mcp --create-env

# Under hidden project folder
npx github:DinhLucent/mirth-connect-skills init --mirth-dir .mirth --install-python --install-mcp --create-env

# Global user install
npx github:DinhLucent/mirth-connect-skills init --global

# Admin install
npx github:DinhLucent/mirth-connect-skills init --admin
```

Global npm install:

```bash
npm install -g github:DinhLucent/mirth-connect-skills
mirth-connect-skills init --global
```

## Install Locations

| Scope | Skill Path | Tool Path |
|-------|-----------|-----------|
| Project | `.agents/skills/mirth-connect-operator` | `mirth-agent-tools` or `.mirth/mirth-agent-tools` |
| User/Global | `~/.agents/skills/mirth-connect-operator` | `~/.agents/tools/mirth-agent-tools` |
| Admin | `/etc/codex/skills/mirth-connect-operator` | -- |
| Legacy Codex | `.codex/skills/mirth-connect-operator` | -- |

## MCP Server

The MCP server exposes 34 tools with proper `ToolAnnotations` for client-side safety classification:

```bash
python -m pip install -e ".[mcp]"
mirth-agent-mcp
```

Tools are categorized by safety tier:

| Tier | Annotation | Examples |
|------|-----------|----------|
| **Read-only** | `readOnlyHint=true` | health_check, list_channels, get_messages, plan_operation |
| **Write** | `readOnlyHint=false` | deploy_channel, update_channel, import_channel |
| **Destructive** | `destructiveHint=true` | delete_channel, redeploy_all, remove_messages |

Every tool includes a comprehensive docstring describing purpose, parameters, safety requirements, and audit behavior.

## Safety Model

Write operations are gated by environment flags:

- `MIRTH_FULL_ACCESS=true` enables write-capable tools.
- `MIRTH_ALLOW_DESTRUCTIVE=true` enables delete, clear, remove, and redeploy-all.
- `MIRTH_ALLOW_PROD_WRITE=true` required when `MIRTH_ENV=prod`.
- `MIRTH_REQUIRE_APPROVAL=true` + `MIRTH_APPROVAL_TOKEN` for approval-gated workflows.
- `MIRTH_DRY_RUN=true` logs the action without executing.
- `MIRTH_REDACT_PHI=true` redacts PHI from message content.
- `MIRTH_ALLOWED_HOSTS` restricts allowed Mirth API hosts.

When blocked, tools return `needs_user_input=true` with a specific `user_question` for the operator.

## CLI Options

```text
mirth-connect-skills init [options]
mirth-connect-skills full [options]

Options:
  --target <dir>        Install into specific project directory
  --global              Install into user's Codex skill/tool locations
  --admin               Install into /etc/codex/skills
  --legacy-codex        Also install into older .codex/skills location
  --force               Overwrite existing destination folders
  --skip-tools          Install only the Codex skill
  --install-python      Run pip install inside tool server
  --install-mcp         Add MCP extra to pip install
  --create-env          Copy .env.example to .env
  --mirth-dir <dir>     Install tools under <dir>/mirth-agent-tools
  --dot-mirth           Alias for --mirth-dir .mirth
```

## Repository Layout

```text
mirth-connect-skills/
  bin/                         npx installer
  mirth-connect-operator/      Codex skill instructions and agent metadata
  mirth-agent-tools/           Python REST/MCP/CLI tool server
    src/mirth_agent_tools/
      client.py                Mirth REST API client
      mcp_server.py            MCP server with ToolAnnotations
      tools.py                 Tool functions with safety gates
      safety.py                Layered access control
      audit.py                 JSONL audit trail
      redaction.py             PHI redaction (HL7, email, phone, SSN)
      config.py                Environment-based configuration
      discovery.py             API endpoint auto-discovery
      cli_fallback.py          mccommand CLI fallback
      xml_utils.py             Channel XML parsing and diff
    tests/                     Unit tests
  scripts/                     Local audit and check runners
  tests/                       Tool effectiveness evaluation suite
```

## Local Testing

```bash
npm run check            # Full local check suite
npm run eval:tools       # Tool effectiveness against mock Mirth API
npm run sandbox:test     # Installer sandbox checks
```

## License

MIT License. See [LICENSE](LICENSE).

This project is not affiliated with, endorsed by, or sponsored by NextGen Healthcare. Mirth and Mirth Connect are trademarks of their respective owners.
