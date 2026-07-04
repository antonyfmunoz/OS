"""Approval port — substrate-layer trust boundary for approval decisions.

Any channel (cockpit, Discord, API) submits approval decisions through this
port without importing organism internals directly. The concrete handler — the
canonical approval authority — is registered at startup.

WP-P1-007: this is a human-governance trust boundary, so it is typed and
**fail-closed**. When no handler is registered, ``submit_approval`` RAISES
``ApprovalPortUnavailable`` rather than silently no-oping or returning a soft
error dict. A trust boundary that quietly swallows a decision is worse than one
that loudly refuses: the caller must know the decision did not land.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


class ApprovalPortUnavailable(RuntimeError):
    """Raised when an approval decision is submitted but no handler is wired.

    Fail-closed: the operation must not proceed as if approved (or denied) when
    the authority behind the port is absent.
    """


class ApprovalPortRequest(BaseModel):
    """Typed request crossing the approval trust boundary."""

    decision_id: str = Field(min_length=1, max_length=200)
    approved: bool
    reason: str = Field(default="", max_length=600)
    decided_by: str = Field(default="system", max_length=120)
    surface: str = Field(default="", max_length=80)


class ApprovalPortResponse(BaseModel):
    """Typed response from the approval authority."""

    success: bool
    decision_id: str = ""
    state: str = ""
    detail: str = ""


# The concrete handler: (ApprovalPortRequest) -> ApprovalPortResponse | dict.
_approval_fn: Optional[Callable[[ApprovalPortRequest], Any]] = None


def register_approval_handler(fn: Callable[[ApprovalPortRequest], Any]) -> None:
    """Register the concrete approval handler (the canonical authority)."""
    global _approval_fn
    _approval_fn = fn


def submit_approval(
    decision_id: str,
    approved: bool,
    reason: str = "",
    decided_by: str = "system",
    surface: str = "",
) -> ApprovalPortResponse:
    """Submit an approval/denial decision through the registered handler.

    Fail-closed: raises ``ApprovalPortUnavailable`` if no handler is registered.
    The handler may return an ``ApprovalPortResponse`` or a plain dict (coerced).
    """
    if _approval_fn is None:
        raise ApprovalPortUnavailable(
            f"no approval handler registered — decision {decision_id!r} refused (fail-closed)"
        )
    request = ApprovalPortRequest(
        decision_id=decision_id,
        approved=approved,
        reason=reason,
        decided_by=decided_by,
        surface=surface,
    )
    result = _approval_fn(request)
    if isinstance(result, ApprovalPortResponse):
        return result
    if isinstance(result, dict):
        return ApprovalPortResponse(
            success=bool(result.get("success", False)),
            decision_id=str(result.get("decision_id", decision_id)),
            state=str(result.get("state", "")),
            detail=str(result.get("detail", result.get("error", ""))),
        )
    # A handler that returns None/garbage is treated as a failed decision, not
    # a silent success — fail-closed.
    return ApprovalPortResponse(
        success=False, decision_id=decision_id, detail="handler returned no result"
    )


def get_approval_handler() -> Optional[Callable[[ApprovalPortRequest], Any]]:
    """Return the registered handler, or None."""
    return _approval_fn
