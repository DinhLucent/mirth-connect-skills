from __future__ import annotations


class MirthBlocked(Exception):
    """Raised when a tool needs explicit user help to continue."""

    def __init__(self, message: str, user_question: str, evidence: list[str] | None = None):
        super().__init__(message)
        self.user_question = user_question
        self.evidence = evidence or []


class MirthConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""
