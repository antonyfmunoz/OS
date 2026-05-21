"""UMH Execution Approval — gating mechanism for risky operations.

Operations that return REQUIRES_APPROVAL from the security guard can
generate an ApprovalRequest. The request must be explicitly approved
before the operation can proceed.

Backed by pluggable storage: InMemoryApprovalBackend (tests) or
SQLiteApprovalBackend (production/CLI) for cross-process durability.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

_log = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CONSUMED = "consumed"


@dataclass
class ApprovalRequest:
    id: str
    execution_id: str
    operation: str
    capability_type: str
    risk_level: str
    inputs_summary: str
    created_at: str
    expires_at: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str = ""
    approved_by: str = ""

    def is_expired(self) -> bool:
        try:
            exp = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > exp
        except Exception:
            return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "operation": self.operation,
            "capability_type": self.capability_type,
            "risk_level": self.risk_level,
            "inputs_summary": self.inputs_summary,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "requested_by": self.requested_by,
            "approved_by": self.approved_by,
        }


class ApprovalStore:
    """Approval request store with pluggable backend. Thread-safe."""

    def __init__(self, backend=None) -> None:
        from umh.execution.approval_persistence import InMemoryApprovalBackend

        self._backend = backend if backend is not None else InMemoryApprovalBackend()
        self._lock = threading.Lock()

    def create_approval(
        self,
        execution_id: str,
        operation: str,
        capability_type: str,
        risk_level: str = "high",
        inputs_summary: str = "",
        ttl_seconds: int = 300,
        requested_by: str = "",
    ) -> ApprovalRequest:
        now = datetime.now(timezone.utc)
        req = ApprovalRequest(
            id=f"approval_{uuid.uuid4().hex[:12]}",
            execution_id=execution_id,
            operation=operation,
            capability_type=capability_type,
            risk_level=risk_level,
            inputs_summary=inputs_summary,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=ttl_seconds)).isoformat(),
            requested_by=requested_by,
        )
        with self._lock:
            self._backend.save(req)
        _log.info(
            "[ApprovalStore] created: id=%s op=%s ttl=%ds",
            req.id,
            operation,
            ttl_seconds,
        )
        from umh.events.stream import publish as _publish_event

        _publish_event(
            "approval.created",
            payload={
                "operation": operation,
                "capability_type": capability_type,
                "risk_level": risk_level,
            },
            actor_id=requested_by,
            execution_id=execution_id,
            approval_id=req.id,
        )
        return req

    def approve(self, approval_id: str, approved_by: str = "") -> ApprovalRequest | None:
        with self._lock:
            req = self._backend.get(approval_id)
            if req is None:
                return None
            if req.is_expired():
                req.status = ApprovalStatus.EXPIRED
                self._backend.update_status(approval_id, ApprovalStatus.EXPIRED)
                self._backend.increment_counter("expired")
                return req
            req.status = ApprovalStatus.APPROVED
            req.approved_by = approved_by
            self._backend.update_status(approval_id, ApprovalStatus.APPROVED)
            self._backend.update_actor(approval_id, "approved_by", approved_by)
            _log.info(
                "[ApprovalStore] approved: id=%s op=%s by=%s", req.id, req.operation, approved_by
            )

        from umh.events.stream import publish as _publish_event

        _publish_event(
            "approval.approved",
            payload={"operation": req.operation},
            actor_id=approved_by,
            execution_id=req.execution_id,
            approval_id=approval_id,
        )
        return req

    def deny(self, approval_id: str) -> ApprovalRequest | None:
        with self._lock:
            req = self._backend.get(approval_id)
            if req is None:
                return None
            req.status = ApprovalStatus.DENIED
            self._backend.update_status(approval_id, ApprovalStatus.DENIED)
            self._backend.increment_counter("denied")
            _log.info("[ApprovalStore] denied: id=%s op=%s", req.id, req.operation)

        from umh.events.stream import publish as _publish_event

        _publish_event(
            "approval.denied",
            payload={"operation": req.operation},
            actor_id="",
            execution_id=req.execution_id,
            approval_id=approval_id,
        )
        return req

    def consume(self, approval_id: str) -> ApprovalRequest | None:
        """Mark an approved request as consumed (single-use)."""
        should_publish = False
        with self._lock:
            req = self._backend.get(approval_id)
            if req is None:
                return None
            if req.is_expired():
                req.status = ApprovalStatus.EXPIRED
                self._backend.update_status(approval_id, ApprovalStatus.EXPIRED)
                self._backend.increment_counter("expired")
                return req
            if req.status != ApprovalStatus.APPROVED:
                return req
            req.status = ApprovalStatus.CONSUMED
            self._backend.update_status(approval_id, ApprovalStatus.CONSUMED)
            self._backend.increment_counter("consumed")
            _log.info("[ApprovalStore] consumed: id=%s op=%s", req.id, req.operation)
            should_publish = True

        if should_publish:
            from umh.events.stream import publish as _publish_event

            _publish_event(
                "approval.consumed",
                payload={"operation": req.operation},
                actor_id="",
                execution_id=req.execution_id,
                approval_id=approval_id,
            )
        return req

    def validate_for_execution(
        self,
        approval_id: str,
        operation: str,
        capability_type: str,
    ) -> tuple[bool, str]:
        """Validate that an approval matches the requested operation.

        Returns (is_valid, reason).
        """
        with self._lock:
            req = self._backend.get(approval_id)
            if req is None:
                return False, f"Approval {approval_id} not found"
            if req.is_expired():
                req.status = ApprovalStatus.EXPIRED
                self._backend.update_status(approval_id, ApprovalStatus.EXPIRED)
                self._backend.increment_counter("expired")
                return False, f"Approval {approval_id} has expired"
            if req.status == ApprovalStatus.CONSUMED:
                return False, f"Approval {approval_id} already consumed"
            if req.status != ApprovalStatus.APPROVED:
                return False, f"Approval {approval_id} status is {req.status.value}"
            if req.operation != operation:
                return False, f"Approval operation mismatch: {req.operation} != {operation}"
            if req.capability_type != capability_type:
                return (
                    False,
                    f"Approval capability mismatch: {req.capability_type} != {capability_type}",
                )
            return True, "Valid"

    def get(self, approval_id: str) -> ApprovalRequest | None:
        with self._lock:
            req = self._backend.get(approval_id)
            if req is not None and req.status == ApprovalStatus.PENDING and req.is_expired():
                req.status = ApprovalStatus.EXPIRED
                self._backend.update_status(approval_id, ApprovalStatus.EXPIRED)
                self._backend.increment_counter("expired")
            return req

    def list_pending(self) -> list[ApprovalRequest]:
        with self._lock:
            pending = self._backend.list_by_status(ApprovalStatus.PENDING)
            result = []
            for req in pending:
                if req.is_expired():
                    req.status = ApprovalStatus.EXPIRED
                    self._backend.update_status(req.id, ApprovalStatus.EXPIRED)
                    self._backend.increment_counter("expired")
                else:
                    result.append(req)
            return result

    def list_all(self) -> list[ApprovalRequest]:
        """Return all approval requests, updating expired status lazily."""
        with self._lock:
            all_reqs = self._backend.list_all()
            for req in all_reqs:
                if req.status == ApprovalStatus.PENDING and req.is_expired():
                    req.status = ApprovalStatus.EXPIRED
                    self._backend.update_status(req.id, ApprovalStatus.EXPIRED)
                    self._backend.increment_counter("expired")
            return all_reqs

    def get_counters(self) -> dict[str, int]:
        """Return approval lifecycle counters."""
        with self._lock:
            return self._backend.get_counters()

    def reset(self) -> None:
        with self._lock:
            self._backend.reset()


def _default_backend():
    """Select backend based on environment. SQLite for production, in-memory for tests."""
    from umh.execution.approval_persistence import (
        InMemoryApprovalBackend,
        SQLiteApprovalBackend,
    )

    if os.environ.get("UMH_APPROVAL_BACKEND") == "memory":
        return InMemoryApprovalBackend()
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("UMH_APPROVAL_BACKEND") == "test":
        return InMemoryApprovalBackend()
    return SQLiteApprovalBackend()


_store: ApprovalStore | None = None
_store_lock = threading.Lock()


def get_approval_store() -> ApprovalStore:
    """Return the process-global approval store (lazy-initialized)."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ApprovalStore(backend=_default_backend())
    return _store


def reset_approval_store(backend=None) -> ApprovalStore:
    """Replace the global store (useful for tests)."""
    global _store
    with _store_lock:
        _store = ApprovalStore(backend=backend)
    return _store
