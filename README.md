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
mirth-agent-tools health_check
```

Global npm install is also supported:

```bash
npm install -g github:DinhLucent/mirth-connect-skills
mirth-connect-skills init --global
```

## npx Options

```bash
mirth-connect-skills init [--target <dir>] [--global] [--force] [--skip-tools] [--install-python]
```

- Project install copies the skill to `.codex/skills/mirth-connect-operator` and tools to `mirth-agent-tools`.
- Global install copies the skill to `$CODEX_HOME/skills/mirth-connect-operator` and tools to `$CODEX_HOME/mirth-agent-tools`.
- `--force` overwrites existing destination folders.
- `--skip-tools` installs only the Codex skill.
- `--install-python` runs `python -m pip install -e ".[dev]"` inside the installed tool server.

## Components

- `mirth-connect-operator/`: Codex skill instructions.
- `mirth-agent-tools/`: Python package exposing Mirth REST tools, MCP server, local CLI, backups, audit logs, and tests.

See [mirth-agent-tools/README.md](mirth-agent-tools/README.md) for tool usage.
