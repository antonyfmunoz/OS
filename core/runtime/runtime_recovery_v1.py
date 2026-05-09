"""Runtime Recovery v1 for the UMH substrate layer.

Structured recovery for failed runtime executions. Handles
worker crashes, timeout, adapter failures, and connectivity
loss. Recovery follows governance — no unsupervised retry of
high-risk operations.

UMH substrate subsystem. Phase 96.8AE.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class FailureType(str, Enum):
    WORKER_CRASH = "worker_crash"
    TIMEOUT = "timeout"
    ADAPTER_FAILURE = "adapter_failure"
    CONNECTIVITY_LOSS = "connectivity_loss"
    GOVERNANCE_BLOCK = "governance_block"
    ENVIRONMENT_UNAVAILABLE = "environment_unavailable"
    UNKNOWN = "unknown"


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    REQUEUE = "requeue"
    ESCALATE = "escalate"
    ABANDON = "abandon"
    WAIT_RECONNECT = "wait_reconnect"


AUTOMATIC_RETRY_FAILURES = frozenset(
    {
        FailureType.TIMEOUT,
        FailureType.CONNECTIVITY_LOSS,
    }
)

ESCALATION_REQUIRED_FAILURES = frozenset(
    {
        FailureType.GOVERNANCE_BLOCK,
        FailureType.ENVIRONMENT_UNAVAILABLE,
    }
)

MAX_RETRY_ATTEMPTS = 3


@dataclass
class FailureRecord:
    """Record of a runtime failure."""

    failure_id: str
    packet_id: str
    dispatch_id: str
    worker_id: str
    failure_type: FailureType
    error_message: str = ""
    timestamp: str = ""
    attempt_number: int = 1
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.failure_id:
            self.failure_id = f"FAIL-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "packet_id": self.packet_id,
            "dispatch_id": self.dispatch_id,
            "worker_id": self.worker_id,
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "attempt_number": self.attempt_number,
            "notes": self.notes,
        }


@dataclass
class RecoveryDecision:
    """Decision on how to handle a failure."""

    decision_id: str
    failure_id: str
    packet_id: str
    strategy: RecoveryStrategy
    reason: str = ""
    retry_after_seconds: int = 0
    requires_founder: bool = False
    timestamp: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.decision_id:
            self.decision_id = f"RECOVERY-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "failure_id": self.failure_id,
            "packet_id": self.packet_id,
            "strategy": self.strategy.value,
            "reason": self.reason,
            "retry_after_seconds": self.retry_after_seconds,
            "requires_founder": self.requires_founder,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


class RuntimeRecoveryEngine:
    """Evaluates failures and produces recovery decisions.

    Automatic retry only for safe, transient failures.
    Escalation for governance or environment issues.
    Abandon after max retries exhausted.
    """

    def __init__(self, max_retries: int = MAX_RETRY_ATTEMPTS) -> None:
        self._max_retries = max_retries
        self._failure_history: dict[str, list[FailureRecord]] = {}

    def record_failure(self, failure: FailureRecord) -> None:
        if failure.packet_id not in self._failure_history:
            self._failure_history[failure.packet_id] = []
        self._failure_history[failure.packet_id].append(failure)

    def evaluate(self, failure: FailureRecord) -> RecoveryDecision:
        self.record_failure(failure)
        attempts = len(self._failure_history.get(failure.packet_id, []))

        if failure.failure_type in ESCALATION_REQUIRED_FAILURES:
            return RecoveryDecision(
                decision_id="",
                failure_id=failure.failure_id,
                packet_id=failure.packet_id,
                strategy=RecoveryStrategy.ESCALATE,
                reason=f"failure_type_requires_escalation: {failure.failure_type.value}",
                requires_founder=True,
            )

        if attempts > self._max_retries:
            return RecoveryDecision(
                decision_id="",
                failure_id=failure.failure_id,
                packet_id=failure.packet_id,
                strategy=RecoveryStrategy.ABANDON,
                reason=f"max_retries_exhausted: {attempts}/{self._max_retries}",
            )

        if failure.failure_type in AUTOMATIC_RETRY_FAILURES:
            return RecoveryDecision(
                decision_id="",
                failure_id=failure.failure_id,
                packet_id=failure.packet_id,
                strategy=RecoveryStrategy.RETRY,
                reason=f"transient_failure_retry: attempt {attempts}/{self._max_retries}",
                retry_after_seconds=min(30 * attempts, 300),
            )

        if failure.failure_type == FailureType.WORKER_CRASH:
            return RecoveryDecision(
                decision_id="",
                failure_id=failure.failure_id,
                packet_id=failure.packet_id,
                strategy=RecoveryStrategy.REQUEUE,
                reason="worker_crashed_requeue_for_new_worker",
                retry_after_seconds=10,
            )

        if failure.failure_type == FailureType.ADAPTER_FAILURE:
            if attempts <= 1:
                return RecoveryDecision(
                    decision_id="",
                    failure_id=failure.failure_id,
                    packet_id=failure.packet_id,
                    strategy=RecoveryStrategy.RETRY,
                    reason="adapter_failure_single_retry",
                    retry_after_seconds=15,
                )
            return RecoveryDecision(
                decision_id="",
                failure_id=failure.failure_id,
                packet_id=failure.packet_id,
                strategy=RecoveryStrategy.ESCALATE,
                reason="adapter_failure_persists",
                requires_founder=True,
            )

        return RecoveryDecision(
            decision_id="",
            failure_id=failure.failure_id,
            packet_id=failure.packet_id,
            strategy=RecoveryStrategy.ESCALATE,
            reason=f"unknown_failure_type: {failure.failure_type.value}",
            requires_founder=True,
        )

    def get_failure_count(self, packet_id: str) -> int:
        return len(self._failure_history.get(packet_id, []))

    def get_failure_history(self, packet_id: str) -> list[FailureRecord]:
        return self._failure_history.get(packet_id, [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_retries": self._max_retries,
            "tracked_packets": len(self._failure_history),
            "total_failures": sum(len(v) for v in self._failure_history.values()),
        }
