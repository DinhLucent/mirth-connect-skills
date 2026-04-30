from __future__ import annotations

from .config import Settings
from .errors import MirthBlocked


def require_full_access(settings: Settings, approval_token: str | None = None) -> None:
    if not settings.full_access:
        raise MirthBlocked(
            "Full access is disabled.",
            "Do you want to set MIRTH_FULL_ACCESS=true so the agent can perform write operations?",
        )
    require_approval(settings, approval_token)


def require_destructive(settings: Settings, approval_token: str | None = None) -> None:
    if not settings.allow_destructive:
        raise MirthBlocked(
            "Destructive operations are disabled.",
            "This operation can delete or clear Mirth data. Do you want to set MIRTH_ALLOW_DESTRUCTIVE=true?",
        )
    require_approval(settings, approval_token)


def require_prod_write(settings: Settings) -> None:
    if settings.environment == "prod" and not settings.allow_prod_write:
        raise MirthBlocked(
            "Production write is disabled.",
            "This is production. Do you want to set MIRTH_ALLOW_PROD_WRITE=true for the agent?",
        )


def require_approval(settings: Settings, approval_token: str | None = None) -> None:
    if not settings.require_approval:
        return
    if not settings.approval_token:
        raise MirthBlocked(
            "Approval is required but MIRTH_APPROVAL_TOKEN is not configured.",
            "Please configure MIRTH_APPROVAL_TOKEN or disable MIRTH_REQUIRE_APPROVAL for this environment.",
        )
    if approval_token != settings.approval_token:
        raise MirthBlocked(
            "Approval token is missing or invalid.",
            "This write operation requires an approval token. Please provide the current approval token for this run.",
        )


def require_write_allowed(settings: Settings, approval_token: str | None = None) -> None:
    require_full_access(settings, approval_token)
    require_prod_write(settings)


def require_destructive_allowed(settings: Settings, approval_token: str | None = None) -> None:
    require_full_access(settings, approval_token)
    require_destructive(settings, approval_token)
    require_prod_write(settings)
