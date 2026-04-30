from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_audit_event(
    *,
    log_dir: Path,
    environment: str,
    tool: str,
    actor: str,
    result: str,
    channel_id: str | None = None,
    backup_path: str | None = None,
    details: dict[str, Any] | None = None,
) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    audit_path = log_dir / "audit.jsonl"
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": environment,
        "tool": tool,
        "channel_id": channel_id,
        "backup_path": backup_path,
        "actor": actor,
        "result": result,
        "details": details or {},
    }
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")
    return audit_path
