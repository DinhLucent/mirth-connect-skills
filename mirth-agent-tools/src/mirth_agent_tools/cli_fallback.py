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


def validate_cli_command(settings: Settings, command: str) -> list[str]:
    args = shlex.split(command)
    if not args:
        raise MirthBlocked(
            "Empty Mirth CLI command.",
            "Please provide a whitelisted mccommand action such as export, import, deploy, undeploy, status, or help.",
        )
    action = args[0]
    if action not in settings.cli_allowed_commands:
        allowed = ", ".join(settings.cli_allowed_commands)
        raise MirthBlocked(
            f"Mirth CLI command is not allowlisted: {action}",
            f"Please use one of the allowlisted CLI commands ({allowed}) or update MIRTH_CLI_ALLOWED_COMMANDS deliberately.",
        )
    return args


def run_cli_command(settings: Settings, command: str, timeout: int | None = None) -> dict[str, object]:
    validated_args = validate_cli_command(settings, command)
    require_cli_fallback(settings)
    args = [settings.cli_path, *validated_args]
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
