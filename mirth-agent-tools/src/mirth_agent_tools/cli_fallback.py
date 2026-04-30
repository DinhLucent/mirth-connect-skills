from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .config import Settings
from .errors import MirthBlocked


def require_cli_fallback(settings: Settings) -> None:
    if not settings.enable_cli_fallback:
        raise MirthBlocked(
            "CLI fallback is disabled.",
            "The REST API endpoint is unavailable. Do you want to set MIRTH_ENABLE_CLI_FALLBACK=true and configure MIRTH_CLI_PATH?",
        )
    if not Path(settings.cli_path).exists():
        raise MirthBlocked(
            f"Mirth CLI not found at {settings.cli_path}",
            "Please set MIRTH_CLI_PATH to the mccommand executable on this Mirth server.",
        )


def run_cli_command(settings: Settings, command: str, timeout: int | None = None) -> dict[str, object]:
    require_cli_fallback(settings)
    args = [settings.cli_path, *shlex.split(command)]
    completed = subprocess.run(
        args,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout or settings.timeout,
    )
    return {
        "command": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
