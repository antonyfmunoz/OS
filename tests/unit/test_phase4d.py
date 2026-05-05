"""Tests for Phase 4D: Approved Execution Path + Guard Bypass Layer.

Verifies:
- Approved mutations execute through the full pipeline (SUCCEEDED)
- Non-approved mutations still return REQUIRES_APPROVAL
- Invalid approvals (wrong op, expired, consumed) are DENIED
- Replay attack prevention (same approval_id reused → DENIED)
- Guard integrity (non-mutation ops unaffected, unknown ops DENY)
- Approval lifecycle counters (consumed/denied/expired)
- Observability: approval_id and approved_execution in events
- Existing LLM/shell/file/screenshot behavior unchanged
"""

import sys

sys.path.insert(0, "/opt/OS")

import time

from umh.execution.contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget,
)


def _make_request(
    operation: str,
    execution_class: ExecutionClass,
    inputs: dict | None = None,
    timeout_s: int = 10,
    sandbox: bool = False,
    metadata: dict | None = None,
) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=f"test_{operation}",
        correlation_id=f"test_{operation}",
        causal_event_id="",
        session_id="",
        operation=operation,
        inputs=inputs or {},
        execution_class=execution_class,
        constraints=ExecutionConstraints(timeout_s=timeout_s, sandbox=sandbox),
        target=ExecutionTarget(node_id="local", transport="test"),
        context=ExecutionContext(metadata=metadata or {}),
        issued_at="2026-04-26T12:00:00Z",
        issued_by="test",
        idempotency_key="",
    )


def _approve_and_execute(operation: str, inputs: dict | None = None) -> ExecutionResult:
    """Helper: create approval → approve → execute with approval_id."""
    from umh.execution.approval import get_approval_store
    from umh.execution.engine import execute

    store = get_approval_store()

    # Step 1: execute without approval → get approval_id
    request1 = _make_request(operation, ExecutionClass.SIDE_EFFECT, inputs=inputs or {})
    result1 = execute(request1)
    assert result1.status == ExecutionStatus.REJECTED
    approval_id = result1.outputs.get("approval_id")
    assert approval_id is not None

    # Step 2: approve it
    approved = store.approve(approval_id)
    assert approved is not None

    # Step 3: execute with approval_id
    exec_inputs = dict(inputs or {})
    exec_inputs["approval_id"] = approval_id
    request2 = _make_request(operation, ExecutionClass.SIDE_EFFECT, inputs=exec_inputs)
    return execute(request2), approval_id


# ── A. Approved Path ─────────────────────────────────────────────────


class TestApprovedExecution:
    """Verify approved mutations execute and return SUCCEEDED."""

    def test_approved_click_succeeds(self):
        from umh.execution.approval import get_approval_store

        get_approval_store().reset()
        result, _ = _approve_and_execute("computer_click", {"x": 100, "y": 200})
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("x") == 100
        assert result.outputs.get("y") == 200

    def test_approved_type_succeeds(self):
        from umh.execution.approval import get_approval_store

        get_approval_store().reset()
        result, _ = _approve_and_execute("computer_type", {"text": "hello"})
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("chars_typed") == 5

    def test_approved_key_succeeds(self):
        from umh.execution.approval import get_approval_store

        get_approval_store().reset()
        result, _ = _approve_and_execute("computer_key", {"key": "Return"})
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("key") == "Return"

    def test_approved_scroll_succeeds(self):
        from umh.execution.approval import get_approval_store

        get_approval_store().reset()
        result, _ = _approve_and_execute("computer_scroll", {"direction": "down", "clicks": 2})
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("direction") == "down"
        assert result.outputs.get("clicks") == 2

    def test_approved_drag_succeeds(self):
        from umh.execution.approval import get_approval_store

        get_approval_store().reset()
        result, _ = _approve_and_execute(
            "computer_drag", {"x1": 10, "y1": 20, "x2": 100, "y2": 200}
        )
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("x2") == 100

    def test_approved_click_has_adapter_field(self):
        from umh.execution.approval import get_approval_store

        get_approval_store().reset()
        result, _ = _approve_and_execute("computer_click", {"x": 50, "y": 50})
        assert result.outputs.get("adapter") == "computer_use_adapter"


# ── B. Non-approved Path ─────────────────────────────────────────────


class TestNonApprovedPath:
    """Verify mutations without approval still return REQUIRES_APPROVAL."""

    def test_click_without_approval_returns_requires_approval(self):
        from umh.execution.engine import execute

        request = _make_request(
            "computer_click", ExecutionClass.SIDE_EFFECT, inputs={"x": 10, "y": 20}
        )
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True
        assert "approval_id" in result.outputs

    def test_type_without_approval_returns_requires_approval(self):
        from umh.execution.engine import execute

        request = _make_request(
            "computer_type", ExecutionClass.SIDE_EFFECT, inputs={"text": "test"}
        )
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True


# ── C. Invalid Approval ──────────────────────────────────────────────


class TestInvalidApproval:
    """Verify invalid approvals are rejected at the engine level."""

    def test_wrong_operation_denied(self):
        from umh.execution.approval import get_approval_store
        from umh.execution.engine import execute

        store = get_approval_store()
        store.reset()

        # Create approval for click
        approval = store.create_approval(
            execution_id="test_wrong_op",
            operation="computer_click",
            capability_type="computer_use",
        )
        store.approve(approval.id)

        # Try to use it for type
        request = _make_request(
            "computer_type",
            ExecutionClass.SIDE_EFFECT,
            inputs={"text": "hack", "approval_id": approval.id},
        )
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("approval_invalid") is True
        assert "mismatch" in result.outputs.get("reason", "").lower()

    def test_expired_approval_denied(self):
        from umh.execution.approval import get_approval_store
        from umh.execution.engine import execute

        store = get_approval_store()
        store.reset()

        approval = store.create_approval(
            execution_id="test_expired",
            operation="computer_click",
            capability_type="computer_use",
            ttl_seconds=0,
        )
        store.approve(approval.id)
        time.sleep(0.01)

        request = _make_request(
            "computer_click",
            ExecutionClass.SIDE_EFFECT,
            inputs={"x": 10, "y": 20, "approval_id": approval.id},
        )
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("approval_invalid") is True
        assert "expired" in result.outputs.get("reason", "").lower()

    def test_nonexistent_approval_denied(self):
        from umh.execution.engine import execute

        request = _make_request(
            "computer_click",
            ExecutionClass.SIDE_EFFECT,
            inputs={"x": 10, "y": 20, "approval_id": "approval_nonexistent"},
        )
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("approval_invalid") is True
        assert "not found" in result.outputs.get("reason", "").lower()

    def test_pending_approval_denied(self):
        from umh.execution.approval import get_approval_store
        from umh.execution.engine import execute

        store = get_approval_store()
        store.reset()

        # Create but do NOT approve
        approval = store.create_approval(
            execution_id="test_pending",
            operation="computer_click",
            capability_type="computer_use",
        )

        request = _make_request(
            "computer_click",
            ExecutionClass.SIDE_EFFECT,
            inputs={"x": 10, "y": 20, "approval_id": approval.id},
        )
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("approval_invalid") is True
        assert "pending" in result.outputs.get("reason", "").lower()

    def test_wrong_capability_denied(self):
        from umh.execution.approval import get_approval_store
        from umh.execution.engine import execute

        store = get_approval_store()
        store.reset()

        approval = store.create_approval(
            execution_id="test_wrong_cap",
            operation="computer_click",
            capability_type="browser_action",
        )
        store.approve(approval.id)

        request = _make_request(
            "computer_click",
            ExecutionClass.SIDE_EFFECT,
            inputs={"x": 10, "y": 20, "approval_id": approval.id},
        )
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("approval_invalid") is True
        assert "mismatch" in result.outputs.get("reason", "").lower()


# ── D. Replay Attack Prevention ──────────────────────────────────────


class TestReplayPrevention:
    """Verify consumed approvals cannot be reused."""

    def test_consumed_approval_cannot_be_reused(self):
        from umh.execution.approval import get_approval_store
        from umh.execution.engine import execute

        store = get_approval_store()
        store.reset()

        # First execution: succeeds
        result1, approval_id = _approve_and_execute("computer_click", {"x": 10, "y": 20})
        assert result1.status == ExecutionStatus.SUCCEEDED

        # Second execution with same approval_id: DENIED
        request2 = _make_request(
            "computer_click",
            ExecutionClass.SIDE_EFFECT,
            inputs={"x": 10, "y": 20, "approval_id": approval_id},
        )
        result2 = execute(request2)
        assert result2.status == ExecutionStatus.REJECTED
        assert result2.outputs.get("approval_invalid") is True
        assert "consumed" in result2.outputs.get("reason", "").lower()

    def test_approval_status_is_consumed_after_execution(self):
        from umh.execution.approval import ApprovalStatus, get_approval_store

        store = get_approval_store()
        store.reset()

        _, approval_id = _approve_and_execute("computer_click", {"x": 5, "y": 5})
        req = store.get(approval_id)
        assert req is not None
        assert req.status == ApprovalStatus.CONSUMED


# ── E. Guard Integrity ───────────────────────────────────────────────


class TestGuardIntegrity:
    """Verify guard behavior is unchanged for non-mutation operations."""

    def test_screenshot_still_allowed(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_screenshot", {})
        assert result.verdict == GuardVerdict.ALLOW

    def test_unknown_computer_op_still_denied(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_unknown_thing", {})
        assert result.verdict == GuardVerdict.DENY

    def test_unknown_op_still_denied(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("totally_unknown", {})
        assert result.verdict == GuardVerdict.DENY

    def test_mutation_without_approval_still_requires_approval(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_click", {})
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL

    def test_mutation_with_approved_flag_allows(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_click", {}, approved_execution=True)
        assert result.verdict == GuardVerdict.ALLOW

    def test_approved_flag_does_not_bypass_unknown_ops(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_unknown_thing", {}, approved_execution=True)
        assert result.verdict == GuardVerdict.DENY

    def test_approved_flag_does_not_affect_shell(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("shell_command", {"command": "uptime"}, approved_execution=True)
        assert result.verdict == GuardVerdict.ALLOW

    def test_approved_flag_does_not_affect_browser(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("browser_navigate", {}, approved_execution=True)
        assert result.verdict == GuardVerdict.DENY


# ── Approval Lifecycle Counters ──────────────────────────────────────


class TestApprovalCounters:
    """Verify approval lifecycle counters track correctly."""

    def test_consumed_counter_increments(self):
        from umh.execution.approval import get_approval_store

        store = get_approval_store()
        store.reset()
        _approve_and_execute("computer_click", {"x": 1, "y": 1})
        counters = store.get_counters()
        assert counters["consumed"] == 1

    def test_denied_counter_increments(self):
        from umh.execution.approval import get_approval_store

        store = get_approval_store()
        store.reset()
        approval = store.create_approval(
            execution_id="test_deny_counter",
            operation="computer_click",
            capability_type="computer_use",
        )
        store.deny(approval.id)
        counters = store.get_counters()
        assert counters["denied"] == 1

    def test_expired_counter_increments(self):
        from umh.execution.approval import get_approval_store

        store = get_approval_store()
        store.reset()
        store.create_approval(
            execution_id="test_expire_counter",
            operation="computer_click",
            capability_type="computer_use",
            ttl_seconds=0,
        )
        time.sleep(0.01)
        store.list_pending()
        counters = store.get_counters()
        assert counters["expired"] >= 1

    def test_reset_clears_counters(self):
        from umh.execution.approval import get_approval_store

        store = get_approval_store()
        store.reset()
        counters = store.get_counters()
        assert counters["consumed"] == 0
        assert counters["denied"] == 0
        assert counters["expired"] == 0


# ── Observability ────────────────────────────────────────────────────


class TestApprovalObservability:
    """Verify ExecutionEvent includes approval fields."""

    def test_event_has_approval_fields(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test_obs",
            operation="computer_click",
            capability_type="computer_use",
            execution_class="side_effect",
            status="succeeded",
            approval_id="approval_abc123",
            approved_execution=True,
        )
        d = event.to_dict()
        assert d["approval_id"] == "approval_abc123"
        assert d["approved_execution"] is True

    def test_event_defaults_no_approval(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test_obs2",
            operation="computer_screenshot",
            capability_type="computer_use",
            execution_class="side_effect",
            status="succeeded",
        )
        d = event.to_dict()
        assert d["approval_id"] is None
        assert d["approved_execution"] is False


# ── Metrics CLI Extension ────────────────────────────────────────────


class TestMetricsExtension:
    """Verify metrics CLI includes approval counters."""

    def test_metrics_include_approval_counters(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        approvals = metrics["approvals"]
        assert "approvals_consumed" in approvals
        assert "approvals_denied" in approvals
        assert "approvals_expired" in approvals

    def test_metrics_computer_use_mutation_status_updated(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        caps = metrics["capabilities"]
        mutation_cap = [
            c for c in caps if c["capability"] == "computer_use" and "click" in c["operations"]
        ]
        assert len(mutation_cap) == 1
        assert "approved" in mutation_cap[0]["status"].lower()


# ── F. Existing Behavior Unchanged ───────────────────────────────────


class TestExistingBehaviorUnchanged4D:
    """Verify LLM, shell, file, and screenshot still work."""

    def test_llm_call_unchanged(self):
        from umh.execution.engine import execute

        request = _make_request(
            "generate_response",
            ExecutionClass.LLM_CALL,
            inputs={"prompt": "hi", "system_prompt": "test", "max_tokens": 10},
        )
        result = execute(request)
        assert result.status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED)

    def test_shell_uptime_unchanged(self):
        from umh.execution.engine import execute

        request = _make_request(
            "shell_command",
            ExecutionClass.SIDE_EFFECT,
            inputs={"command": "uptime", "args": []},
        )
        result = execute(request)
        assert result.status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED)

    def test_computer_screenshot_unchanged(self):
        from umh.execution.engine import execute

        request = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = execute(request)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_guard_still_denies_unknown(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("totally_unknown_op", {})
        assert result.verdict == GuardVerdict.DENY

    def test_file_read_in_sandbox_still_works(self):
        from umh.execution.engine import execute

        request = _make_request(
            "file_read",
            ExecutionClass.SIDE_EFFECT,
            inputs={"path": "/opt/OS/data/test_read.tmp"},
        )
        result = execute(request)
        assert result.status in (
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
        )
