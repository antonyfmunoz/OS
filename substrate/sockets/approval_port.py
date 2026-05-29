"""
Approval port — substrate-layer abstraction for approval decisions.

Any channel (cockpit, Discord, API) can submit approval decisions
through this port without importing organism internals directly.
The concrete handler is registered at startup.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

_approval_fn: Optional[Callable] = None


def register_approval_handler(fn: Callable) -> None:
    """Register the concrete approval handler."""
    global _approval_fn
    _approval_fn = fn


def submit_approval(
    decision_id: str,
    approved: bool,
    reason: str = "",
    decided_by: str = "system",
) -> dict[str, Any]:
    """Submit an approval/denial decision through the registered handler."""
    if not _approval_fn:
        return {"success": False, "error": "no approval handler registered"}
    return _approval_fn(
        decision_id=decision_id,
        approved=approved,
        reason=reason,
        decided_by=decided_by,
    )


def get_approval_handler() -> Optional[Callable]:
    """Return the registered handler, or None."""
    return _approval_fn
