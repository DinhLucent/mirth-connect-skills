# Tool Effectiveness Tests

This folder contains local evaluation scripts for the Mirth Connect skill tools.

Run:

```bash
npm run eval:tools
```

The suite starts a local mock Mirth REST API, executes the real Python tool layer, measures latency/request counts, and verifies behavior that matters for agent use:

- tool-result protocol shape
- API discovery and read tools
- backup and audit behavior for write tools
- destructive guard behavior
- dry-run behavior
- PHI redaction on message content
- local operation planning
- CLI fallback whitelist rejection

Generated JSON reports are written to `tests/reports/` and are ignored by git.

Installer sandbox checks create isolated project folders under `tests/.sandboxes/`, verify default install, `.mirth` runtime install, full dry-run, legacy skill-only install, force/idempotency behavior, package contents, and invalid-option paths, then remove the sandboxes by default.

```bash
npm run sandbox:test
```

Use `node tests/run_sandbox_checks.js --keep` when you want to inspect generated sandboxes manually.
