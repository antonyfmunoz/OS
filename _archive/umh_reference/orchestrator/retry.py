"""UMH Retry Policy — failure classification and retry logic.

Pure decision module. Classifies execution failures and determines whether
a step should be retried based on configurable policies. No execution side
effects — this module never calls execute() or touches the task store.

Usage:
    from umh.orchestrator.retry import (
        classify_failure, should_retry, get_backoff_delay,
        FailureType, RetryPolicy, DEFAULT_RETRY_POLICY,
    )

    ftype = classify_failure(result_dict)
    if should_retry(ftype, attempt=1, policy=DEFAULT_RETRY_POLICY):
        delay = get_backoff_delay(attempt=1, policy=DEFAULT_RETRY_POLICY)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

_MAX_BACKOFF_SECONDS = 60.0


class FailureType(str, Enum):
    """Classification of an execution failure."""

    TRANSIENT = "transient"  # timeout, temporary adapter failure
    PERMANENT = "permanent"  # bad input, missing operation
    APPROVAL_REQUIRED = "approval_required"  # not a failure
    GUARD_DENIED = "guard_denied"  # security guard blocked
    UNKNOWN = "unknown"  # unclassified


@dataclass
class RetryPolicy:
    """Configurable retry behaviour for task steps."""

    max_attempts: int = 1
    backoff_seconds: float = 5.0
    retryable_types: tuple[FailureType, ...] = (FailureType.TRANSIENT,)


DEFAULT_RETRY_POLICY = RetryPolicy(max_attempts=2, backoff_seconds=5.0)
STRICT_RETRY_POLICY = RetryPolicy(max_attempts=1)  # no retry


def classify_failure(result_dict: dict) -> FailureType:
    """Classify a failure from an ExecutionResult.to_dict() payload.

    Inspects outputs and error string to determine the failure category.
    """
    outputs = result_dict.get("outputs", {})

    # Approval takes priority — it is not really a failure.
    if outputs.get("requires_approval"):
        return FailureType.APPROVAL_REQUIRED

    error = (result_dict.get("error") or "").lower()

    # Guard / permission denial
    if any(kw in error for kw in ("guard", "denied", "not allowed")):
        return FailureType.GUARD_DENIED

    # Transient / retriable signals
    if any(kw in error for kw in ("timeout", "timed out", "connection")):
        return FailureType.TRANSIENT

    # Permanent / non-retriable signals
    if any(kw in error for kw in ("not found", "invalid", "unsupported")):
        return FailureType.PERMANENT

    return FailureType.UNKNOWN


def should_retry(failure_type: FailureType, attempt: int, policy: RetryPolicy) -> bool:
    """Decide whether to retry given the failure type, attempt number, and policy."""
    if failure_type not in policy.retryable_types:
        return False
    if attempt >= policy.max_attempts:
        return False
    return True


def get_backoff_delay(attempt: int, policy: RetryPolicy) -> float:
    """Calculate backoff delay in seconds, capped at 60s.

    Uses linear backoff: ``policy.backoff_seconds * attempt``.
    """
    delay = policy.backoff_seconds * attempt
    return min(delay, _MAX_BACKOFF_SECONDS)
