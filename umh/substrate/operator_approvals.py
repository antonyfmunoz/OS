"""
Operator approvals — deterministic approval/permission handling.

Provides:
- Clean approval request builder with stable correlation keys
- Response handler (approve/reject) with deterministic outcomes
- Duplicate suppression (one pending request per correlation key)
- Timeout/expiry behavior with clean terminal responses
- Queryable approval state

This is the operator-facing layer around the existing permission flow.
It does NOT redesign orchestration — it adds a clean presentation layer.

Design rules (substrate conventions):
- Additive only. No hot-path imports.
- Bounded store (max 100 pending requests).
- Thread-safe via lock.
- Deterministic: same inputs → same approval request.
- No LLM calls. No transport side effects.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

_LOG_PREFIX = "[substrate.operator_approvals]"
_DEFAULT_TIMEOUT_S = 300  # 5 minutes
_MAX_PENDING = 100


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utcnow_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _approval_id() -> str:
    return f"appr_{uuid.uuid4().hex[:12]}"


# ─── Status enum ────────────────────────────────────────────────────────────


class ApprovalStatus(str, Enum):
    """Lifecycle status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# ─── Approval request ──────────────────────────────────────────────────────


@dataclass
class ApprovalRequest:
    """One approval request awaiting operator response.

    Immutable after creation except for status/resolution fields.
    """

    approval_id: str
    correlation_id: str
    title: str
    reason: str
    context: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    timeout_s: int = _DEFAULT_TIMEOUT_S
    created_at: str = field(default_factory=_utcnow)
    created_ts: float = field(default_factory=_utcnow_ts)
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
            ApprovalStatus.CANCELLED,
        )

    @property
    def is_expired(self) -> bool:
        if self.status != ApprovalStatus.PENDING:
            return False
        age = _utcnow_ts() - self.created_ts
        return age > self.timeout_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "correlation_id": self.correlation_id,
            "title": self.title,
            "reason": self.reason,
            "context": dict(self.context),
            "status": self.status.value,
            "timeout_s": self.timeout_s,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "resolution_detail": self.resolution_detail,
            "metadata": dict(self.metadata),
        }


# ─── Builder ────────────────────────────────────────────────────────────────


def build_approval_request(
    *,
    correlation_id: str,
    title: str,
    reason: str,
    context: dict[str, Any] | None = None,
    timeout_s: int = _DEFAULT_TIMEOUT_S,
    metadata: dict[str, Any] | None = None,
) -> ApprovalRequest:
    """Create a new ApprovalRequest.

    Args:
        correlation_id: Stable key linking this approval to the pending task/intent.
        title: Short display title for the approval prompt.
        reason: Why operator approval is needed.
        context: Additional context for the approval decision.
        timeout_s: Seconds before the request expires.
    """
    return ApprovalRequest(
        approval_id=_approval_id(),
        correlation_id=correlation_id,
        title=title,
        reason=reason,
        context=context or {},
        timeout_s=timeout_s,
        metadata=metadata or {},
    )


# ─── Response helpers ───────────────────────────────────────────────────────


def approve(
    request: ApprovalRequest,
    *,
    resolved_by: str = "operator",
    detail: str = "",
) -> ApprovalRequest:
    """Mark an approval request as approved."""
    if request.is_terminal:
        _log(f"approve ignored: {request.approval_id} already {request.status.value}")
        return request
    request.status = ApprovalStatus.APPROVED
    request.resolved_at = _utcnow()
    request.resolved_by = resolved_by
    request.resolution_detail = detail
    _log(f"approved: {request.approval_id} by={resolved_by}")
    return request


def reject(
    request: ApprovalRequest,
    *,
    resolved_by: str = "operator",
    detail: str = "",
) -> ApprovalRequest:
    """Mark an approval request as rejected."""
    if request.is_terminal:
        _log(f"reject ignored: {request.approval_id} already {request.status.value}")
        return request
    request.status = ApprovalStatus.REJECTED
    request.resolved_at = _utcnow()
    request.resolved_by = resolved_by
    request.resolution_detail = detail
    _log(f"rejected: {request.approval_id} by={resolved_by}")
    return request


def expire(request: ApprovalRequest) -> ApprovalRequest:
    """Mark an approval request as expired."""
    if request.is_terminal:
        return request
    request.status = ApprovalStatus.EXPIRED
    request.resolved_at = _utcnow()
    request.resolution_detail = f"Timed out after {request.timeout_s}s"
    _log(f"expired: {request.approval_id}")
    return request


def cancel(
    request: ApprovalRequest,
    *,
    detail: str = "",
) -> ApprovalRequest:
    """Mark an approval request as cancelled."""
    if request.is_terminal:
        return request
    request.status = ApprovalStatus.CANCELLED
    request.resolved_at = _utcnow()
    request.resolution_detail = detail or "Cancelled"
    _log(f"cancelled: {request.approval_id}")
    return request


# ─── Operator-facing response text ─────────────────────────────────────────


def format_resolution_response(request: ApprovalRequest) -> str:
    """Format a clean operator-facing response for a resolved approval.

    Returns a short Discord-appropriate message.
    """
    if request.status == ApprovalStatus.APPROVED:
        return f"✅ **Approved** — {request.title}\n• Proceeding with action"
    if request.status == ApprovalStatus.REJECTED:
        return f"🚫 **Rejected** — {request.title}\n• Action cancelled"
    if request.status == ApprovalStatus.EXPIRED:
        return (
            f"⏰ **Expired** — {request.title}\n"
            f"• No response received within {request.timeout_s}s\n"
            f"• Action cancelled"
        )
    if request.status == ApprovalStatus.CANCELLED:
        return (
            f"🔄 **Cancelled** — {request.title}\n"
            f"• {request.resolution_detail or 'Action withdrawn'}"
        )
    return f"❓ **{request.status.value}** — {request.title}"


# ─── Store (thread-safe, bounded) ──────────────────────────────────────────


class ApprovalStore:
    """Thread-safe bounded store for approval requests.

    Keyed by approval_id. Indexed by correlation_id for deduplication.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_id: dict[str, ApprovalRequest] = {}
        self._by_correlation: dict[str, str] = {}  # correlation_id → approval_id

    def submit(self, request: ApprovalRequest) -> ApprovalRequest | None:
        """Submit a new approval request.

        Returns the request if accepted, or None if a pending request
        already exists for this correlation_id (duplicate suppression).
        """
        with self._lock:
            # Check for existing pending request with same correlation
            existing_id = self._by_correlation.get(request.correlation_id)
            if existing_id:
                existing = self._by_id.get(existing_id)
                if existing and not existing.is_terminal:
                    # Check if expired
                    if existing.is_expired:
                        expire(existing)
                    else:
                        _log(
                            f"duplicate suppressed: correlation={request.correlation_id} "
                            f"existing={existing_id}"
                        )
                        return None

            # Expire stale requests
            self._expire_stale()

            # Enforce capacity
            self._enforce_capacity()

            self._by_id[request.approval_id] = request
            self._by_correlation[request.correlation_id] = request.approval_id

            _log(
                f"submitted: id={request.approval_id} "
                f"correlation={request.correlation_id} title={request.title!r}"
            )
            return request

    def resolve(
        self,
        approval_id: str,
        *,
        action: str,
        resolved_by: str = "operator",
        detail: str = "",
    ) -> ApprovalRequest | None:
        """Resolve an approval request by ID.

        Args:
            approval_id: The approval to resolve.
            action: "approve" or "reject".
            resolved_by: Who resolved it.
            detail: Additional detail.

        Returns the updated request, or None if not found.
        """
        with self._lock:
            request = self._by_id.get(approval_id)
            if request is None:
                _log(f"resolve failed: {approval_id} not found")
                return None

            # Check for expiry first
            if request.is_expired:
                expire(request)
                return request

            if action == "approve":
                approve(request, resolved_by=resolved_by, detail=detail)
            elif action == "reject":
                reject(request, resolved_by=resolved_by, detail=detail)
            else:
                _log(f"resolve: unknown action {action!r} for {approval_id}")
                return None

            return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID."""
        with self._lock:
            req = self._by_id.get(approval_id)
            if req and req.status == ApprovalStatus.PENDING and req.is_expired:
                expire(req)
            return req

    def get_by_correlation(self, correlation_id: str) -> ApprovalRequest | None:
        """Get the most recent approval for a correlation ID."""
        with self._lock:
            approval_id = self._by_correlation.get(correlation_id)
            if not approval_id:
                return None
            req = self._by_id.get(approval_id)
            if req and req.status == ApprovalStatus.PENDING and req.is_expired:
                expire(req)
            return req

    def get_pending(self) -> list[ApprovalRequest]:
        """Get all non-expired pending requests."""
        with self._lock:
            self._expire_stale()
            return [
                r for r in self._by_id.values() if r.status == ApprovalStatus.PENDING
            ]

    def stats(self) -> dict[str, int]:
        """Diagnostic stats."""
        with self._lock:
            self._expire_stale()
            counts: dict[str, int] = {}
            for r in self._by_id.values():
                k = r.status.value
                counts[k] = counts.get(k, 0) + 1
            counts["total"] = len(self._by_id)
            return counts

    def _expire_stale(self) -> None:
        """Expire any pending requests past their timeout."""
        for req in self._by_id.values():
            if req.status == ApprovalStatus.PENDING and req.is_expired:
                expire(req)

    def _enforce_capacity(self) -> None:
        """Remove oldest terminal requests to stay under capacity."""
        if len(self._by_id) <= _MAX_PENDING:
            return
        # Remove oldest terminal entries
        terminal = sorted(
            ((aid, r) for aid, r in self._by_id.items() if r.is_terminal),
            key=lambda x: x[1].created_at,
        )
        to_remove = len(self._by_id) - _MAX_PENDING
        for aid, req in terminal[:to_remove]:
            del self._by_id[aid]
            if self._by_correlation.get(req.correlation_id) == aid:
                del self._by_correlation[req.correlation_id]

    def reset_for_tests(self) -> None:
        """Clear all state."""
        with self._lock:
            self._by_id.clear()
            self._by_correlation.clear()


# ─── Module-level singleton ─────────────────────────────────────────────────

_store = ApprovalStore()


def get_approval_store() -> ApprovalStore:
    """Return the process-level approval store."""
    return _store


def reset_for_tests() -> None:
    """Test helper."""
    _store.reset_for_tests()


__all__ = [
    "ApprovalStatus",
    "ApprovalRequest",
    "ApprovalStore",
    "build_approval_request",
    "approve",
    "reject",
    "expire",
    "cancel",
    "format_resolution_response",
    "get_approval_store",
    "reset_for_tests",
]
