from __future__ import annotations

from .config import Settings
from .errors import MirthBlocked


def require_full_access(settings: Settings) -> None:
    if not settings.full_access:
        raise MirthBlocked(
            "Full access is disabled.",
            "Do you want to set MIRTH_FULL_ACCESS=true so the agent can perform write operations?",
        )


def require_destructive(settings: Settings) -> None:
    if not settings.allow_destructive:
        raise MirthBlocked(
            "Destructive operations are disabled.",
            "This operation can delete or clear Mirth data. Do you want to set MIRTH_ALLOW_DESTRUCTIVE=true?",
        )


def require_prod_write(settings: Settings) -> None:
    if settings.environment == "prod" and not settings.allow_prod_write:
        raise MirthBlocked(
            "Production write is disabled.",
            "This is production. Do you want to set MIRTH_ALLOW_PROD_WRITE=true for the agent?",
        )


def require_write_allowed(settings: Settings) -> None:
    require_full_access(settings)
    require_prod_write(settings)


def require_destructive_allowed(settings: Settings) -> None:
    require_full_access(settings)
    require_destructive(settings)
    require_prod_write(settings)
