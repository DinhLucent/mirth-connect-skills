---
name: mirth-connect-operator
description: Operate Mirth Connect with full-access REST API and CLI fallback workflows. Use when Codex needs to inspect, export, import, update, deploy, start/stop, read messages/statistics, manage code templates/extensions, backup, rollback, or troubleshoot Mirth Connect channels through controlled tools.
---

# Mirth Connect Full-Access Operator

## Purpose

Operate Mirth Connect through controlled tool calls, not the Administrator GUI.

Use the Mirth REST API first. Use Mirth CLI fallback only when REST is unavailable and fallback is explicitly enabled.

## First Steps

1. Run `mirth.health_check`.
2. Run `mirth.discover_api`.
3. Detect server/version details when available.
4. Prefer XML for channel export/import/update.
5. Always send `X-Requested-With`.

Never assume a route exists on the target Mirth version. Discovery evidence should guide endpoint choice.

## Full Access Rules

Write operations require `MIRTH_FULL_ACCESS=true`.

Destructive operations require `MIRTH_ALLOW_DESTRUCTIVE=true`.

Production writes require:

- `MIRTH_ENV=prod`
- `MIRTH_ALLOW_PROD_WRITE=true`

If a required flag is disabled, return a tool result with `needs_user_input=true` and a direct question asking whether to enable the flag.

## Backup Rules

Before these actions, create a backup or pre-action snapshot when technically possible:

- update/import/delete channel
- deploy/undeploy/redeploy all
- remove messages
- clear statistics

Return backup paths in tool data. Write an audit event for every write/destructive operation.

## Blocked Action Protocol

When blocked, do not guess silently. Return:

- `ok=false`
- exact error reason
- `needs_user_input=true`
- a specific `user_question`
- relevant evidence

Ask for user help on:

- connection/VPN/firewall/server down
- TLS self-signed certificate
- 401/403 credentials or permissions
- 404 missing endpoint/version mismatch
- ambiguous channel name or missing channel id
- production write disabled
- destructive mode disabled
- missing CLI path when fallback is needed

## PHI Handling

When reading messages, default to metadata only. Only request raw content with `include_content=true` when the user explicitly asks for message content or the task requires it.

When echoing message content back to the user, mask obvious PHI where possible.
