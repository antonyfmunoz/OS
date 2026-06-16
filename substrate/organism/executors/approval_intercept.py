"""Approval Intercepts — runtime human-in-the-loop governance for executors.

Execution reaches a checkpoint → ApprovalInterceptRequest created →
telemetry emitted → execution paused → operator decides via cockpit →
execution resumes or fails. No restart. No work duplication.

Components:
  - ApprovalInterceptStatus: canonical status enum
  - ApprovalInterceptRequest: immutable request record
  - ApprovalInterceptStore: bounded in-memory store with threading.Event
  - ApprovalInterceptService: service layer (request, await, approve, reject)

Design constraints:
  - Uses threading.Event for synchronous blocking (executor lifecycle is sync)
  - Intercepts NEVER hang — configurable timeout with auto-expiry
  - In-memory only for this phase (no Redis, no DB)
  - Thread-safe via threading.Lock
  - Telemetry integration via optional emitter

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Status Enum
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ApprovalInterceptStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Approval Intercept Request
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


_DEFAULT_TIMEOUT_SECONDS = 900.0  # 15 minutes


@dataclass
class ApprovalInterceptRequest:
    """A runtime approval intercept — blocks execution until decided."""

    approval_id: str = field(
        default_factory=lambda: f"apvl-{uuid4().hex[:12]}"
    )
    execution_id: str = ""
    request_id: str = ""
    executor_type: str = ""
    operation: str = ""
    risk_class: str = ""
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    requested_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    status: str = ApprovalInterceptStatus.PENDING.value
    decided_by: str = ""
    decided_at: float = 0.0
    rejection_reason: str = ""

    def __post_init__(self) -> None:
        if self.expires_at == 0.0:
            self.expires_at = self.requested_at + _DEFAULT_TIMEOUT_SECONDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "execution_id": self.execution_id,
            "request_id": self.request_id,
            "executor_type": self.executor_type,
            "operation": self.operation,
            "risk_class": self.risk_class,
            "reason": self.reason,
            "details": self.details,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "rejection_reason": self.rejection_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalInterceptRequest:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @property
    def is_pending(self) -> bool:
        return self.status == ApprovalInterceptStatus.PENDING.value

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        return time.time() - self.requested_at


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# In-Memory Store
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MAX_INTERCEPTS = 1000


class ApprovalInterceptStore:
    """Bounded in-memory store for approval intercepts.

    Each intercept has a threading.Event that the executor thread
    waits on. Approve/reject/expire sets the event to unblock.
    """

    def __init__(self, max_intercepts: int = _MAX_INTERCEPTS) -> None:
        self._lock = threading.Lock()
        self._intercepts: dict[str, ApprovalInterceptRequest] = {}
        self._events: dict[str, threading.Event] = {}
        self._max = max_intercepts

    def create(self, intercept: ApprovalInterceptRequest) -> ApprovalInterceptRequest:
        """Store a new intercept and create its blocking event."""
        with self._lock:
            if len(self._intercepts) >= self._max:
                self._evict_oldest()
            self._intercepts[intercept.approval_id] = intercept
            self._events[intercept.approval_id] = threading.Event()
            return intercept

    def get(self, approval_id: str) -> ApprovalInterceptRequest | None:
        with self._lock:
            return self._intercepts.get(approval_id)

    def approve(
        self,
        approval_id: str,
        decided_by: str = "operator",
    ) -> ApprovalInterceptRequest | None:
        """Approve an intercept and unblock the waiting executor."""
        with self._lock:
            intercept = self._intercepts.get(approval_id)
            if not intercept:
                return None
            if intercept.status != ApprovalInterceptStatus.PENDING.value:
                return None
            if intercept.is_expired:
                intercept.status = ApprovalInterceptStatus.EXPIRED.value
                self._unblock(approval_id)
                return None

            intercept.status = ApprovalInterceptStatus.APPROVED.value
            intercept.decided_by = decided_by
            intercept.decided_at = time.time()
            self._unblock(approval_id)
            return intercept

    def reject(
        self,
        approval_id: str,
        reason: str = "",
        decided_by: str = "operator",
    ) -> ApprovalInterceptRequest | None:
        """Reject an intercept and unblock the waiting executor."""
        with self._lock:
            intercept = self._intercepts.get(approval_id)
            if not intercept:
                return None
            if intercept.status != ApprovalInterceptStatus.PENDING.value:
                return None

            intercept.status = ApprovalInterceptStatus.REJECTED.value
            intercept.decided_by = decided_by
            intercept.decided_at = time.time()
            intercept.rejection_reason = reason
            self._unblock(approval_id)
            return intercept

    def expire(self, approval_id: str) -> ApprovalInterceptRequest | None:
        """Mark an intercept as expired and unblock."""
        with self._lock:
            intercept = self._intercepts.get(approval_id)
            if not intercept:
                return None
            if intercept.status != ApprovalInterceptStatus.PENDING.value:
                return None

            intercept.status = ApprovalInterceptStatus.EXPIRED.value
            self._unblock(approval_id)
            return intercept

    def list_pending(self) -> list[ApprovalInterceptRequest]:
        """All pending intercepts, with auto-expiry of stale ones."""
        with self._lock:
            self._expire_stale()
            return [
                i for i in self._intercepts.values()
                if i.status == ApprovalInterceptStatus.PENDING.value
            ]

    def list_all(self) -> list[ApprovalInterceptRequest]:
        with self._lock:
            self._expire_stale()
            return list(self._intercepts.values())

    def wait_for_decision(
        self,
        approval_id: str,
        timeout: float | None = None,
    ) -> ApprovalInterceptRequest | None:
        """Block until the intercept is decided or times out.

        Called by the executor thread. Returns the intercept with
        its final status, or None if not found.
        """
        event = None
        intercept = None
        with self._lock:
            event = self._events.get(approval_id)
            intercept = self._intercepts.get(approval_id)

        if not event or not intercept:
            return None

        if timeout is None:
            timeout = max(0, intercept.expires_at - time.time())

        event.wait(timeout=timeout)

        with self._lock:
            intercept = self._intercepts.get(approval_id)
            if intercept and intercept.status == ApprovalInterceptStatus.PENDING.value:
                intercept.status = ApprovalInterceptStatus.EXPIRED.value
                self._unblock(approval_id)
            return intercept

    def clear(self) -> None:
        with self._lock:
            for event in self._events.values():
                event.set()
            self._intercepts.clear()
            self._events.clear()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._intercepts)

    @property
    def pending_count(self) -> int:
        with self._lock:
            self._expire_stale()
            return sum(
                1 for i in self._intercepts.values()
                if i.status == ApprovalInterceptStatus.PENDING.value
            )

    def _unblock(self, approval_id: str) -> None:
        """Set the event to unblock the waiting thread. Must hold lock."""
        event = self._events.get(approval_id)
        if event:
            event.set()

    def _expire_stale(self) -> None:
        """Auto-expire pending intercepts past their deadline. Must hold lock."""
        for intercept in self._intercepts.values():
            if (
                intercept.status == ApprovalInterceptStatus.PENDING.value
                and intercept.is_expired
            ):
                intercept.status = ApprovalInterceptStatus.EXPIRED.value
                self._unblock(intercept.approval_id)

    def _evict_oldest(self) -> None:
        """Remove the oldest decided intercept to make room. Must hold lock."""
        decided = [
            i for i in self._intercepts.values()
            if i.status != ApprovalInterceptStatus.PENDING.value
        ]
        if not decided:
            return
        decided.sort(key=lambda i: i.requested_at)
        oldest = decided[0]
        del self._intercepts[oldest.approval_id]
        self._events.pop(oldest.approval_id, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Approval Intercept Service
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ApprovalInterceptService:
    """Service layer for runtime approval intercepts.

    Executors call request_approval() → await_decision().
    Cockpit calls approve() or reject().
    """

    def __init__(
        self,
        store: ApprovalInterceptStore | None = None,
        telemetry_emitter: Any | None = None,
    ) -> None:
        self._store = store or ApprovalInterceptStore()
        self._telemetry = telemetry_emitter

    @property
    def store(self) -> ApprovalInterceptStore:
        return self._store

    def _tel(
        self,
        event_type: str,
        intercept: ApprovalInterceptRequest,
        **payload: Any,
    ) -> None:
        """Emit telemetry. Never raises."""
        if not self._telemetry:
            return
        try:
            self._telemetry.emit(
                event_type,
                execution_id=intercept.execution_id,
                request_id=intercept.request_id,
                executor_type=intercept.executor_type,
                operation=intercept.operation,
                status=intercept.status,
                payload={
                    "approval_id": intercept.approval_id,
                    **payload,
                },
            )
        except Exception:
            logger.debug("Intercept telemetry emit failed", exc_info=True)

    def request_approval(
        self,
        *,
        execution_id: str,
        request_id: str = "",
        executor_type: str = "",
        operation: str = "",
        risk_class: str = "",
        reason: str = "",
        details: dict[str, Any] | None = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> ApprovalInterceptRequest:
        """Create a new approval intercept.

        Called by the executor when it hits a governance checkpoint.
        """
        intercept = ApprovalInterceptRequest(
            execution_id=execution_id,
            request_id=request_id or execution_id,
            executor_type=executor_type,
            operation=operation,
            risk_class=risk_class,
            reason=reason,
            details=details or {},
            expires_at=time.time() + timeout_seconds,
        )
        self._store.create(intercept)
        self._tel("approval_requested", intercept, reason=reason, risk_class=risk_class)
        logger.info(
            "Approval intercept %s created for %s: %s",
            intercept.approval_id, execution_id, reason,
        )
        return intercept

    def await_decision(
        self,
        approval_id: str,
        timeout: float | None = None,
    ) -> ApprovalInterceptRequest | None:
        """Block until decision is made or timeout. Returns final state."""
        self._tel_by_id("execution_paused", approval_id, message="Waiting for operator")
        result = self._store.wait_for_decision(approval_id, timeout=timeout)
        if result:
            if result.status == ApprovalInterceptStatus.EXPIRED.value:
                self._tel("approval_expired", result, message="Timed out waiting for operator")
            elif result.status == ApprovalInterceptStatus.APPROVED.value:
                self._tel("execution_resumed", result, message="Operator approved")
            elif result.status == ApprovalInterceptStatus.REJECTED.value:
                self._tel("execution_resumed", result, message="Operator rejected")
        return result

    def approve(
        self,
        approval_id: str,
        operator_id: str = "operator",
    ) -> ApprovalInterceptRequest | None:
        """Approve an intercept. Unblocks the waiting executor."""
        result = self._store.approve(approval_id, decided_by=operator_id)
        if result:
            self._tel(
                "approval_granted", result,
                operator_id=operator_id,
                decision="approved",
            )
            logger.info("Intercept %s approved by %s", approval_id, operator_id)
        return result

    def reject(
        self,
        approval_id: str,
        reason: str = "",
        operator_id: str = "operator",
    ) -> ApprovalInterceptRequest | None:
        """Reject an intercept. Unblocks the waiting executor."""
        result = self._store.reject(approval_id, reason=reason, decided_by=operator_id)
        if result:
            self._tel(
                "approval_rejected", result,
                operator_id=operator_id,
                decision="rejected",
                reason=reason,
            )
            logger.info("Intercept %s rejected by %s: %s", approval_id, operator_id, reason)
        return result

    def get(self, approval_id: str) -> ApprovalInterceptRequest | None:
        return self._store.get(approval_id)

    def pending(self) -> list[ApprovalInterceptRequest]:
        return self._store.list_pending()

    def all_intercepts(self) -> list[ApprovalInterceptRequest]:
        return self._store.list_all()

    def _tel_by_id(self, event_type: str, approval_id: str, **payload: Any) -> None:
        intercept = self._store.get(approval_id)
        if intercept:
            self._tel(event_type, intercept, **payload)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Risk Classification for Operations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_HIGH_RISK_COMMANDS: frozenset[str] = frozenset({
    "git push",
    "git push --force",
    "git push -f",
    "git branch -D",
    "git branch -d",
    "git reset --hard",
    "rm -rf",
    "rm -r",
    "rmdir",
})

_CRITICAL_PATTERNS: list[str] = [
    "--force",
    "-f ",
    "rm -rf",
    "rm -r ",
    "DROP TABLE",
    "DROP DATABASE",
    "TRUNCATE",
    "pkill",
    "kill -9",
    "systemctl stop",
    "docker rm",
    "docker rmi",
]


def classify_operation_risk(operation: str, params: dict[str, Any]) -> str:
    """Classify risk for a workstation operation.

    Returns: 'low', 'medium', 'high', or 'critical'.
    """
    if operation in ("read_file", "list_directory"):
        return "low"

    if operation == "write_file":
        path = params.get("path", "")
        if any(p in path.lower() for p in (".env", "credentials", "secrets")):
            return "critical"
        return "medium"

    if operation == "create_worktree":
        return "low"

    if operation == "run_command":
        cmd = params.get("command", "")
        cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd) if cmd else ""
        cmd_lower = cmd_str.lower().strip()

        for pattern in _CRITICAL_PATTERNS:
            if pattern.lower() in cmd_lower:
                return "critical"

        for high_cmd in _HIGH_RISK_COMMANDS:
            if cmd_lower.startswith(high_cmd):
                return "high"

        if any(kw in cmd_lower for kw in ("rm ", "delete", "remove")):
            return "high"

        return "medium"

    return "medium"


def requires_approval(risk_class: str) -> bool:
    """Check if a risk class requires operator approval."""
    return risk_class in ("high", "critical")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_singleton: ApprovalInterceptService | None = None


def get_approval_intercept_service() -> ApprovalInterceptService:
    """Get the global approval intercept service singleton."""
    global _singleton
    if _singleton is None:
        try:
            from substrate.organism.executors.execution_telemetry import (
                get_telemetry_emitter,
            )
            emitter = get_telemetry_emitter()
        except Exception:
            emitter = None
        _singleton = ApprovalInterceptService(telemetry_emitter=emitter)
    return _singleton


def reset_approval_intercept_service() -> None:
    """Reset the singleton (for testing)."""
    global _singleton
    _singleton = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gate 3 — Approval Policies & Decisions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ApprovalScope(str, Enum):
    EXECUTION = "execution"
    PLAN = "plan"
    ACTION = "action"


@dataclass
class ApprovalPolicy:
    """Declarative policy governing when approval is required."""

    policy_id: str = ""
    name: str = ""
    risk_threshold: str = "medium"
    auto_approve_below: str = "medium"
    scope: ApprovalScope = ApprovalScope.PLAN

    def requires_approval(self, risk_class: str) -> bool:
        risk_order = {"safe": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        threshold_level = risk_order.get(self.risk_threshold, 2)
        risk_level = risk_order.get(risk_class, 2)
        return risk_level >= threshold_level

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "risk_threshold": self.risk_threshold,
            "auto_approve_below": self.auto_approve_below,
            "scope": self.scope.value
            if isinstance(self.scope, ApprovalScope) else self.scope,
        }


@dataclass
class ApprovalDecision:
    """Record of an approval or rejection decision."""

    decision_id: str = field(
        default_factory=lambda: f"adec-{uuid4().hex[:12]}"
    )
    work_id: str = ""
    policy_id: str = ""
    status: str = "approved"
    decided_by: str = "operator"
    decided_at: float = field(default_factory=time.time)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "work_id": self.work_id,
            "policy_id": self.policy_id,
            "status": self.status,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "reason": self.reason,
        }


# Seed policies — LOW auto-approves, MEDIUM+ requires operator
DEFAULT_APPROVAL_POLICIES: list[ApprovalPolicy] = [
    ApprovalPolicy(
        policy_id="pol-default-plan",
        name="Default Plan Policy",
        risk_threshold="medium",
        auto_approve_below="medium",
        scope=ApprovalScope.PLAN,
    ),
    ApprovalPolicy(
        policy_id="pol-default-execution",
        name="Default Execution Policy",
        risk_threshold="medium",
        auto_approve_below="medium",
        scope=ApprovalScope.EXECUTION,
    ),
    ApprovalPolicy(
        policy_id="pol-default-action",
        name="Default Action Policy",
        risk_threshold="low",
        auto_approve_below="low",
        scope=ApprovalScope.ACTION,
    ),
]


class ApprovalPolicyRegistry:
    """In-memory registry of approval policies."""

    def __init__(self) -> None:
        self._policies: dict[str, ApprovalPolicy] = {}
        for p in DEFAULT_APPROVAL_POLICIES:
            self._policies[p.policy_id] = p

    def get(self, policy_id: str) -> ApprovalPolicy | None:
        return self._policies.get(policy_id)

    def for_scope(self, scope: ApprovalScope) -> ApprovalPolicy | None:
        for p in self._policies.values():
            if p.scope == scope:
                return p
        return None

    def register(self, policy: ApprovalPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def all_policies(self) -> list[ApprovalPolicy]:
        return list(self._policies.values())

    def evaluate(self, risk_class: str, scope: ApprovalScope) -> tuple[bool, str]:
        """Returns (requires_approval, policy_id)."""
        policy = self.for_scope(scope)
        if policy is None:
            return True, ""
        return policy.requires_approval(risk_class), policy.policy_id
