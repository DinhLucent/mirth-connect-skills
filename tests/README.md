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
