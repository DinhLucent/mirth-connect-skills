# Mirth Connect Skills

Codex skill and Python tool server for operating Mirth Connect through controlled REST API tools, XML backup/restore, audit logs, rollback support, MCP, and CLI fallback.

This project is designed for agent-assisted Mirth operations where the agent can inspect, export, update, deploy, start/stop channels, read statistics/messages, and ask for specific user input when credentials, permissions, endpoints, or safety gates block an action.

> Mirth Connect is a healthcare integration engine. Treat this repository as operational tooling: use a dedicated Mirth account, keep audit logs, and avoid returning raw PHI unless explicitly required.

## Features

- Codex skill for Mirth Connect operator workflows.
- Python package with REST-first Mirth client and local CLI.
- Optional MCP server for exposing tools to agent runtimes.
- XML-first channel export/import/update for version compatibility.
- Backup and rollback helpers before write operations.
- Audit logs for write and destructive actions.
- Safety gates for full access, destructive actions, and production writes.
- Local npx installer for project, user, admin, and legacy Codex locations.
- Local test and effectiveness evaluation suite with a mock Mirth REST API.

## Requirements

- Node.js 18 or newer.
- Python 3.10 or newer.
- Mirth Connect reachable over REST API, usually at `https://localhost:8443`.
- A dedicated Mirth user with the permissions needed for the operations you want the agent to perform.

## Quickstart

For a full Mirth operator install, use this repository's installer:

```bash
npx github:DinhLucent/mirth-connect-skills full
```

That installs:

- the Codex skill into `.agents/skills/mirth-connect-operator`
- the Python tool server into `.mirth/mirth-agent-tools`
- Python package dependencies with the optional MCP extra
- a local `.mirth/mirth-agent-tools/.env` copied from `.env.example`
- `.mirth/.gitignore` to keep `.env`, backups, and logs out of git

Then edit `.mirth/mirth-agent-tools/.env` with your Mirth URL and credentials:

```bash
cd .mirth/mirth-agent-tools
mirth-agent-tools health_check
```

## Skill-Only Install

The shared Skills CLI flow used by repositories such as `mattpocock/skills` is supported:

```bash
npx skills@latest add DinhLucent/mirth-connect-skills
```

For a non-interactive Codex install:

```bash
npx skills@latest add DinhLucent/mirth-connect-skills --agent codex --skill mirth-connect-operator -y --copy
```

This installs the Codex skill instructions only. It does not install `mirth-agent-tools`, Python dependencies, MCP runtime, or `.env`. For full-access operation, use `npx github:DinhLucent/mirth-connect-skills full`.

## Full Tool-Server Install

Install the skill and Python tools into the current project without running pip:

```bash
npx github:DinhLucent/mirth-connect-skills init
```

Install everything in one command:

```bash
npx github:DinhLucent/mirth-connect-skills init --install-python --install-mcp --create-env
```

Install the tool runtime under a hidden project folder:

```bash
npx github:DinhLucent/mirth-connect-skills init --mirth-dir .mirth --install-python --install-mcp --create-env
```

Install globally for the current user:

```bash
npx github:DinhLucent/mirth-connect-skills init --global
```

Install in the admin skill location:

```bash
npx github:DinhLucent/mirth-connect-skills init --admin
```

Global npm install is also supported:

```bash
npm install -g github:DinhLucent/mirth-connect-skills
mirth-connect-skills init --global
```

## Install Locations

- Project install: `.agents/skills/mirth-connect-operator`
- User/global install: `~/.agents/skills/mirth-connect-operator`
- Admin install: `/etc/codex/skills/mirth-connect-operator`
- Legacy Codex fallback: `.codex/skills/mirth-connect-operator` with `--legacy-codex`

The installer copies the Python tools to `mirth-agent-tools` for plain project `init` installs, `.mirth/mirth-agent-tools` for project `full` installs, or `~/.agents/tools/mirth-agent-tools` for user/global installs. Use `--mirth-dir <dir>` to choose a different hidden project runtime directory. When a project-local runtime directory is used, the installer writes `<dir>/.gitignore` so credentials and runtime logs are not committed accidentally.

## Configure Mirth Tools

After installation, configure credentials and install the Python package:

```bash
cd mirth-agent-tools
cp .env.example .env
python -m pip install -e ".[dev]"
```

For MCP support:

```bash
python -m pip install -e ".[mcp]"
```

Run a basic health check:

```bash
mirth-agent-tools health_check
```

## npx Options

```bash
mirth-connect-skills init [--target <dir>] [--global] [--admin] [--force] [--legacy-codex] [--skip-tools] [--install-python] [--install-mcp] [--create-env] [--mirth-dir <dir>]
mirth-connect-skills full [--target <dir>] [--global] [--admin] [--force] [--legacy-codex] [--python <cmd>] [--mirth-dir <dir>]
```

- `--target <dir>` installs into a specific project directory.
- `--global` installs into the current user's Codex skill and tool locations.
- `--admin` installs into `/etc/codex/skills/mirth-connect-operator`.
- `--legacy-codex` also installs the skill into the older `.codex/skills` location.
- `--force` overwrites existing destination folders.
- `--skip-tools` installs only the Codex skill.
- `--install-python` runs `python -m pip install -e ".[dev]"` inside the installed tool server.
- `--install-mcp` adds the optional MCP extra to `--install-python`.
- `--create-env` copies `.env.example` to `.env` if `.env` does not exist.
- `--mirth-dir <dir>` installs project-local tools under `<dir>/mirth-agent-tools`; `full` defaults to `.mirth`.
- `--dot-mirth` is an alias for `--mirth-dir .mirth`.

## Repository Layout

```text
mirth-connect-skills/
  bin/                         npx installer
  mirth-connect-operator/      Codex skill instructions and agent metadata
  mirth-agent-tools/           Python REST/MCP/CLI tool server
  scripts/                     Local audit and check runners
  tests/                       Tool effectiveness evaluation suite
```

## Safety Model

The tools are intentionally full-access capable, but write operations are gated by environment flags:

- `MIRTH_FULL_ACCESS=true` enables write-capable tools.
- `MIRTH_ALLOW_DESTRUCTIVE=true` enables delete, clear, remove, and redeploy-all style operations.
- `MIRTH_ALLOW_PROD_WRITE=true` is required before writing when `MIRTH_ENV=prod`.

When blocked by auth, TLS, missing endpoints, ambiguous channels, permissions, or disabled safety flags, tools return a structured result with `needs_user_input=true` and a specific question for the user.

Message content is metadata-only by default. Raw message content should be requested deliberately, and PHI redaction is applied before returning content where possible.

## Local Testing And Audit

This repository does not include GitHub Actions CI. Run the local batch check instead:

```bash
npm run check
```

That runs:

- formatting and install-path audit
- Python `compileall`
- editable Python install with `dev,mcp`
- Python unit tests
- tool effectiveness evaluation against a mock Mirth REST API
- npx installer dry-run
- `npm pack --dry-run`

Run only the effectiveness evaluation:

```bash
npm run eval:tools
```

The evaluation starts a local mock Mirth REST API, runs the real Python tools against it, measures latency and request counts, checks backup/audit/redaction behavior, and writes a JSON report under `tests/reports/`.

## License

MIT License. See [LICENSE](LICENSE).

This project is not affiliated with, endorsed by, or sponsored by NextGen Healthcare. Mirth and Mirth Connect are trademarks of their respective owners.
