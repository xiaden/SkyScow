"""Service-reserved caller metadata extraction for mutation entrypoints."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_INTERNAL_KEY = "__skyscow_internal"
_current_identity: ContextVar[dict[str, str] | None] = ContextVar("caller_identity", default=None)


def caller_identity_from_args(args: dict[str, Any]) -> dict[str, str] | None:
    """Extract only plugin-owned caller metadata; public fields are ignored."""
    metadata = args.get(_INTERNAL_KEY)
    identity = metadata.get("caller_identity") if isinstance(metadata, dict) else None
    if not isinstance(identity, dict):
        return None
    if not all(isinstance(identity.get(key), str) for key in ("agent", "session", "message")):
        return None
    return {key: identity[key] for key in ("agent", "session", "message")}


def set_caller_identity(args: dict[str, Any]) -> None:
    _current_identity.set(caller_identity_from_args(args))


def current_caller_identity() -> dict[str, str] | None:
    """Peek at service caller metadata without consuming it."""
    return _current_identity.get()


def take_caller_identity() -> dict[str, str] | None:
    identity = _current_identity.get()
    _current_identity.set(None)
    return identity
