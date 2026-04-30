from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import MirthBlocked


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    base_url: str
    username: str
    password: str
    verify_tls: bool = True
    environment: str = "dev"
    full_access: bool = False
    allow_destructive: bool = False
    allow_prod_write: bool = False
    enable_cli_fallback: bool = False
    cli_path: str = "/opt/mirthconnect/mccommand"
    backup_dir: Path = Path("backups")
    log_dir: Path = Path("logs")
    actor: str = "ai_mirth_agent"
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "Settings":
        base_url = os.getenv("MIRTH_BASE_URL", "").strip()
        username = os.getenv("MIRTH_USERNAME", "").strip()
        password = os.getenv("MIRTH_PASSWORD", "")

        missing = [
            name
            for name, value in {
                "MIRTH_BASE_URL": base_url,
                "MIRTH_USERNAME": username,
                "MIRTH_PASSWORD": password,
            }.items()
            if not value
        ]
        if missing:
            raise MirthBlocked(
                f"Missing required environment variables: {', '.join(missing)}",
                "Please provide MIRTH_BASE_URL, MIRTH_USERNAME, and MIRTH_PASSWORD for the Mirth server.",
            )

        return cls(
            base_url=base_url,
            username=username,
            password=password,
            verify_tls=_env_bool("MIRTH_VERIFY_TLS", True),
            environment=os.getenv("MIRTH_ENV", "dev").strip().lower() or "dev",
            full_access=_env_bool("MIRTH_FULL_ACCESS", False),
            allow_destructive=_env_bool("MIRTH_ALLOW_DESTRUCTIVE", False),
            allow_prod_write=_env_bool("MIRTH_ALLOW_PROD_WRITE", False),
            enable_cli_fallback=_env_bool("MIRTH_ENABLE_CLI_FALLBACK", False),
            cli_path=os.getenv("MIRTH_CLI_PATH", "/opt/mirthconnect/mccommand"),
            backup_dir=Path(os.getenv("MIRTH_BACKUP_DIR", "backups")),
            log_dir=Path(os.getenv("MIRTH_LOG_DIR", "logs")),
            actor=os.getenv("MIRTH_ACTOR", "ai_mirth_agent"),
            timeout=int(os.getenv("MIRTH_TIMEOUT", "30")),
        )

    def as_client_kwargs(self) -> dict[str, object]:
        return {
            "base_url": self.base_url,
            "username": self.username,
            "password": self.password,
            "verify_tls": self.verify_tls,
            "timeout": self.timeout,
        }
