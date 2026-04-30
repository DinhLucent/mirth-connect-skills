# Mirth Connect Skills

Codex skill plus Python tool server for full-access Mirth Connect operations through REST API, XML backups, audit logs, rollback, MCP, and CLI fallback.

## Install With npx

Install into the current project:

```bash
npx github:DinhLucent/mirth-connect-skills init
```

Install globally for Codex:

```bash
npx github:DinhLucent/mirth-connect-skills init --global
```

After install, configure Mirth credentials:

```bash
cp mirth-agent-tools/.env.example mirth-agent-tools/.env
cd mirth-agent-tools
python -m pip install -e ".[dev]"
# optional MCP server support:
python -m pip install -e ".[mcp]"
mirth-agent-tools health_check
```

Global npm install is also supported:

```bash
npm install -g github:DinhLucent/mirth-connect-skills
mirth-connect-skills init --global
```

## npx Options

```bash
mirth-connect-skills init [--target <dir>] [--global] [--admin] [--force] [--legacy-codex] [--skip-tools] [--install-python] [--install-mcp]
```

- Project install copies the skill to `.agents/skills/mirth-connect-operator` and tools to `mirth-agent-tools`.
- Global install copies the skill to `~/.agents/skills/mirth-connect-operator` and tools to `~/.agents/tools/mirth-agent-tools`.
- Admin install copies the skill to `/etc/codex/skills/mirth-connect-operator`.
- `--legacy-codex` also copies the skill to the older `.codex/skills` location.
- `--force` overwrites existing destination folders.
- `--skip-tools` installs only the Codex skill.
- `--install-python` runs `python -m pip install -e ".[dev]"` inside the installed tool server.
- `--install-mcp` adds the optional MCP extra to `--install-python`.

## Components

- `mirth-connect-operator/`: Codex skill instructions.
- `mirth-agent-tools/`: Python package exposing Mirth REST tools, MCP server, local CLI, backups, audit logs, and tests.

## Local Testing And Audit

This repository does not include GitHub Actions CI. Run the local batch check instead:

```bash
npm run check
```

That runs formatting/newline audit, Python compile, editable install with `dev,mcp`, pytest, npx dry-run, and npm pack dry-run.

To run only the skill tool effectiveness evaluation:

```bash
npm run eval:tools
```

The evaluation starts a local mock Mirth REST API, runs the real Python tools against it, measures latency and request counts, checks backup/audit/redaction behavior, and writes a JSON report under `tests/reports/`.

See [mirth-agent-tools/README.md](mirth-agent-tools/README.md) for tool usage.
