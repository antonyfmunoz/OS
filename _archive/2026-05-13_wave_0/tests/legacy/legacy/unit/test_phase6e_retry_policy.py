"""Tests for Phase 6E: Retry Policy + Failure Classification.

Test classes:
1. TestFailureClassification — classify_failure maps error signals correctly
2. TestRetryPolicy — should_retry + backoff logic under various policies
3. TestStepRetryCount — TaskStep.retry_count tracking and serialisation
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6e")
os.environ["UMH_TASK_BACKEND"] = "memory"

import pytest

from umh.orchestrator.retry import (
    DEFAULT_RETRY_POLICY,
    STRICT_RETRY_POLICY,
    FailureType,
    RetryPolicy,
    classify_failure,
    get_backoff_delay,
    should_retry,
)
from umh.orchestrator.task import TaskStep, StepStatus
from umh.orchestrator.task_store import get_task_store, reset_task_store
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    execute_task,
    get_task,
    reset_tasks,
)


# ── TestFailureClassification ────────────────────────────────────────


class TestFailureClassification:
    """classify_failure correctly maps result dicts to FailureType."""

    def test_transient_timeout(self):
        result = {"error": "Request timed out after 30s", "outputs": {}}
        assert classify_failure(result) == FailureType.TRANSIENT

    def test_transient_connection(self):
        result = {"error": "connection refused by upstream", "outputs": {}}
        assert classify_failure(result) == FailureType.TRANSIENT

    def test_permanent_not_found(self):
        result = {"error": "Operation not found: foobar", "outputs": {}}
        assert classify_failure(result) == FailureType.PERMANENT

    def test_permanent_invalid(self):
        result = {"error": "invalid input schema", "outputs": {}}
        assert classify_failure(result) == FailureType.PERMANENT

    def test_permanent_unsupported(self):
        result = {"error": "unsupported execution class", "outputs": {}}
        assert classify_failure(result) == FailureType.PERMANENT

    def test_guard_denied(self):
        result = {"error": "Guard denied: risk too high", "outputs": {}}
        assert classify_failure(result) == FailureType.GUARD_DENIED

    def test_guard_not_allowed(self):
        result = {"error": "Action not allowed by policy", "outputs": {}}
        assert classify_failure(result) == FailureType.GUARD_DENIED

    def test_approval_required(self):
        result = {
            "error": None,
            "outputs": {"requires_approval": True, "approval_id": "apr_123"},
        }
        assert classify_failure(result) == FailureType.APPROVAL_REQUIRED

    def test_approval_takes_priority_over_error(self):
        """Even if error contains 'timeout', approval flag wins."""
        result = {
            "error": "timeout",
            "outputs": {"requires_approval": True, "approval_id": "apr_456"},
        }
        assert classify_failure(result) == FailureType.APPROVAL_REQUIRED

    def test_unknown_default(self):
        result = {"error": "something completely unexpected", "outputs": {}}
        assert classify_failure(result) == FailureType.UNKNOWN

    def test_no_error_no_outputs(self):
        result = {"outputs": {}}
        assert classify_failure(result) == FailureType.UNKNOWN

    def test_none_error(self):
        result = {"error": None, "outputs": {}}
        assert classify_failure(result) == FailureType.UNKNOWN


# ── TestRetryPolicy ──────────────────────────────────────────────────


class TestRetryPolicy:
    """should_retry and get_backoff_delay honour policy rules."""

    def test_should_retry_true_for_transient(self):
        assert should_retry(FailureType.TRANSIENT, attempt=1, policy=DEFAULT_RETRY_POLICY)

    def test_should_retry_false_for_permanent(self):
        assert not should_retry(FailureType.PERMANENT, attempt=1, policy=DEFAULT_RETRY_POLICY)

    def test_should_retry_false_for_guard(self):
        assert not should_retry(FailureType.GUARD_DENIED, attempt=1, policy=DEFAULT_RETRY_POLICY)

    def test_should_retry_false_for_approval(self):
        assert not should_retry(
            FailureType.APPROVAL_REQUIRED, attempt=1, policy=DEFAULT_RETRY_POLICY
        )

    def test_should_retry_false_for_unknown(self):
        assert not should_retry(FailureType.UNKNOWN, attempt=1, policy=DEFAULT_RETRY_POLICY)

    def test_should_retry_false_when_max_exceeded(self):
        """attempt >= max_attempts means no retry."""
        assert not should_retry(FailureType.TRANSIENT, attempt=2, policy=DEFAULT_RETRY_POLICY)

    def test_should_retry_false_at_exact_max(self):
        assert not should_retry(FailureType.TRANSIENT, attempt=2, policy=DEFAULT_RETRY_POLICY)

    def test_strict_policy_never_retries(self):
        """STRICT_RETRY_POLICY has max_attempts=1, so even attempt=0 at the boundary."""
        assert not should_retry(FailureType.TRANSIENT, attempt=1, policy=STRICT_RETRY_POLICY)

    def test_custom_policy_retries_unknown(self):
        policy = RetryPolicy(
            max_attempts=3,
            backoff_seconds=2.0,
            retryable_types=(FailureType.TRANSIENT, FailureType.UNKNOWN),
        )
        assert should_retry(FailureType.UNKNOWN, attempt=1, policy=policy)
        assert should_retry(FailureType.UNKNOWN, attempt=2, policy=policy)
        assert not should_retry(FailureType.UNKNOWN, attempt=3, policy=policy)

    def test_backoff_linear(self):
        assert get_backoff_delay(1, DEFAULT_RETRY_POLICY) == 5.0
        assert get_backoff_delay(2, DEFAULT_RETRY_POLICY) == 10.0
        assert get_backoff_delay(3, DEFAULT_RETRY_POLICY) == 15.0

    def test_backoff_capped_at_60(self):
        policy = RetryPolicy(max_attempts=100, backoff_seconds=10.0)
        assert get_backoff_delay(7, policy) == 60.0  # 10*7=70 → capped at 60
        assert get_backoff_delay(100, policy) == 60.0

    def test_backoff_zero_attempt(self):
        assert get_backoff_delay(0, DEFAULT_RETRY_POLICY) == 0.0


# ── TestStepRetryCount ───────────────────────────────────────────────


class TestStepRetryCount:
    """TaskStep.retry_count field persists across serialisation."""

    def test_default_retry_count_is_zero(self):
        step = TaskStep(operation="test_op")
        assert step.retry_count == 0

    def test_step_tracks_retry_count(self):
        step = TaskStep(operation="test_op")
        step.retry_count = 3
        assert step.retry_count == 3

    def test_retry_count_in_to_dict(self):
        step = TaskStep(operation="test_op")
        step.retry_count = 2
        d = step.to_dict()
        assert "retry_count" in d
        assert d["retry_count"] == 2

    def test_retry_count_zero_in_to_dict(self):
        step = TaskStep(operation="test_op")
        d = step.to_dict()
        assert d["retry_count"] == 0

    def test_retry_count_roundtrips_through_store(self):
        """Save a task with retry_count set, reload it, verify it survives."""
        reset_task_store()
        reset_tasks()

        step = TaskStep(operation="roundtrip_op", id="step_rt_01")
        step.retry_count = 5

        task = Task(
            steps=[step],
            id="task_rt_01",
            issued_by="test",
            status=TaskStatus.PENDING,
        )

        store = get_task_store()
        store.save(task)

        loaded = store.get("task_rt_01")
        assert loaded is not None
        assert loaded.steps[0].retry_count == 5

        # Also check the dict form
        task_dict = loaded.to_dict()
        assert task_dict["steps"][0]["retry_count"] == 5

        reset_task_store()
        reset_tasks()
