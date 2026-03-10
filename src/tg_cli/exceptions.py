"""Structured exception hierarchy for tg-cli."""

from __future__ import annotations


class TGCLIError(Exception):
    """Base exception for tg-cli."""


class NotAuthenticatedError(TGCLIError):
    """Raised when Telegram credentials are missing or session is invalid."""


class ChatNotFoundError(TGCLIError):
    """Raised when a chat cannot be resolved by name or ID."""


class SyncError(TGCLIError):
    """Raised when a sync operation fails."""
