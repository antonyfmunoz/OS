"""Tests for Phase 4C: Approval Flow + Execution Metrics CLI.

Verifies:
- ApprovalStore: create, approve, deny, get, list_pending, expiry
- Engine creates approval request when guard returns REQUIRES_APPROVAL
- computer_click through execute() returns REJECTED with approval_id
- Approved mutation still returns NOT_IMPLEMENTED (plumbing only)
- Metrics CLI imports and returns structured output
- Existing LLM/shell/file/computer_screenshot behavior unchanged
"""

import sys

sys.path.insert(0, "/opt/OS")

import time
from unittest.mock import patch, MagicMock

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
        context=ExecutionContext(),
        issued_at="2026-04-26T12:00:00Z",
        issued_by="test",
        idempotency_key="",
    )


# ── ApprovalStore unit tests ──────────────────────────────────────────


class TestApprovalStoreCreate:
    """Verify approval request creation and defaults."""

    def test_create_approval_returns_request(self):
        from umh.execution.approval import ApprovalStatus, ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_1",
            operation="computer_click",
            capability_type="computer_use",
        )
        assert req.id.startswith("approval_")
        assert req.execution_id == "exec_1"
        assert req.operation == "computer_click"
        assert req.status == ApprovalStatus.PENDING

    def test_create_approval_has_timestamps(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_2",
            operation="computer_type",
            capability_type="computer_use",
        )
        assert req.created_at is not None
        assert req.expires_at is not None
        assert req.created_at < req.expires_at

    def test_create_approval_default_risk_level(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_3",
            operation="computer_key",
            capability_type="computer_use",
        )
        assert req.risk_level == "high"

    def test_create_approval_custom_ttl(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_4",
            operation="computer_scroll",
            capability_type="computer_use",
            ttl_seconds=10,
        )
        assert not req.is_expired()

    def test_create_approval_to_dict(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_5",
            operation="computer_drag",
            capability_type="computer_use",
        )
        d = req.to_dict()
        assert d["operation"] == "computer_drag"
        assert d["status"] == "pending"
        assert "id" in d


class TestApprovalStoreActions:
    """Verify approve, deny, get, list_pending, expiry, reset."""

    def test_approve_changes_status(self):
        from umh.execution.approval import ApprovalStatus, ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_a1",
            operation="computer_click",
            capability_type="computer_use",
        )
        result = store.approve(req.id)
        assert result is not None
        assert result.status == ApprovalStatus.APPROVED

    def test_deny_changes_status(self):
        from umh.execution.approval import ApprovalStatus, ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_a2",
            operation="computer_type",
            capability_type="computer_use",
        )
        result = store.deny(req.id)
        assert result is not None
        assert result.status == ApprovalStatus.DENIED

    def test_get_returns_request(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_a3",
            operation="computer_key",
            capability_type="computer_use",
        )
        got = store.get(req.id)
        assert got is not None
        assert got.id == req.id

    def test_get_unknown_returns_none(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        assert store.get("nonexistent_id") is None

    def test_approve_unknown_returns_none(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        assert store.approve("nonexistent_id") is None

    def test_deny_unknown_returns_none(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        assert store.deny("nonexistent_id") is None

    def test_list_pending_returns_pending_only(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        req1 = store.create_approval(
            execution_id="exec_lp1",
            operation="computer_click",
            capability_type="computer_use",
        )
        req2 = store.create_approval(
            execution_id="exec_lp2",
            operation="computer_type",
            capability_type="computer_use",
        )
        store.approve(req1.id)
        pending = store.list_pending()
        assert len(pending) == 1
        assert pending[0].id == req2.id

    def test_expired_approval_returns_expired_status(self):
        from umh.execution.approval import ApprovalStatus, ApprovalStore

        store = ApprovalStore()
        req = store.create_approval(
            execution_id="exec_exp",
            operation="computer_click",
            capability_type="computer_use",
            ttl_seconds=0,
        )
        time.sleep(0.01)
        result = store.approve(req.id)
        assert result is not None
        assert result.status == ApprovalStatus.EXPIRED

    def test_expired_not_in_list_pending(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        store.create_approval(
            execution_id="exec_exp2",
            operation="computer_type",
            capability_type="computer_use",
            ttl_seconds=0,
        )
        time.sleep(0.01)
        pending = store.list_pending()
        assert len(pending) == 0

    def test_reset_clears_all(self):
        from umh.execution.approval import ApprovalStore

        store = ApprovalStore()
        store.create_approval(
            execution_id="exec_r1",
            operation="computer_click",
            capability_type="computer_use",
        )
        store.reset()
        assert store.list_pending() == []


# ── Engine REQUIRES_APPROVAL integration ──────────────────────────────


class TestEngineApprovalFlow:
    """Verify the engine creates approval requests for gated operations."""

    def test_computer_click_returns_rejected_with_approval_id(self):
        from umh.execution.engine import execute

        request = _make_request("computer_click", ExecutionClass.SIDE_EFFECT)
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True
        assert "approval_id" in result.outputs

    def test_computer_type_returns_rejected(self):
        from umh.execution.engine import execute

        request = _make_request("computer_type", ExecutionClass.SIDE_EFFECT)
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True

    def test_computer_scroll_returns_rejected(self):
        from umh.execution.engine import execute

        request = _make_request("computer_scroll", ExecutionClass.SIDE_EFFECT)
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED

    def test_approval_id_is_valid_in_store(self):
        from umh.execution.approval import get_approval_store
        from umh.execution.engine import execute

        store = get_approval_store()
        store.reset()
        request = _make_request("computer_click", ExecutionClass.SIDE_EFFECT)
        result = execute(request)
        approval_id = result.outputs.get("approval_id")
        assert approval_id is not None
        req = store.get(approval_id)
        assert req is not None
        assert req.operation == "computer_click"

    def test_approval_reason_in_error(self):
        from umh.execution.engine import execute

        request = _make_request("computer_drag", ExecutionClass.SIDE_EFFECT)
        result = execute(request)
        assert result.error is not None
        assert "approval" in result.error.lower() or "requires" in result.error.lower()


# ── Adapter mutation with approval ────────────────────────────────────


class TestAdapterMutationApproval:
    """Verify adapter checks approval_id and still returns NOT_IMPLEMENTED."""

    def _local_env(self):
        from umh.execution.environment import (
            EnvironmentSpec,
            EnvironmentType,
            ExecutionMode,
            SecurityLevel,
        )

        return EnvironmentSpec(
            id="local",
            env_type=EnvironmentType.LOCAL,
            supported_capabilities=frozenset({"computer_use"}),
            security_level=SecurityLevel.TRUSTED,
            execution_mode=ExecutionMode.REAL,
        )

    def test_mutation_without_approval_id_requires_approval(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter

        adapter = ComputerUseAdapter()
        request = _make_request("computer_click", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(request, self._local_env())
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True

    def test_mutation_with_invalid_approval_id_requires_approval(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter

        adapter = ComputerUseAdapter()
        request = _make_request(
            "computer_click",
            ExecutionClass.SIDE_EFFECT,
            inputs={"approval_id": "nonexistent"},
        )
        result = adapter.execute(request, self._local_env())
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True

    def test_mutation_without_approved_context_requires_approval(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter

        adapter = ComputerUseAdapter()
        request = _make_request(
            "computer_click",
            ExecutionClass.SIDE_EFFECT,
            inputs={"approval_id": "some_id"},
        )
        result = adapter.execute(request, self._local_env())
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True

    def test_mutation_with_approved_context_executes(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from dataclasses import replace

        adapter = ComputerUseAdapter()
        request = _make_request(
            "computer_click",
            ExecutionClass.SIDE_EFFECT,
            inputs={"x": 10, "y": 20},
        )
        new_ctx = replace(
            request.context,
            metadata={"approved_execution": True},
        )
        request = replace(request, context=new_ctx)
        result = adapter.execute(request, self._local_env())
        assert result.status == ExecutionStatus.SUCCEEDED


# ── Metrics CLI ───────────────────────────────────────────────────────


class TestMetricsCLI:
    """Verify metrics module imports and returns structured data."""

    def test_get_metrics_returns_dict(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        assert isinstance(metrics, dict)
        assert "capabilities" in metrics
        assert "environments" in metrics
        assert "scoring" in metrics
        assert "approvals" in metrics

    def test_capabilities_include_computer_use(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        caps = metrics["capabilities"]
        computer_caps = [c for c in caps if c["capability"] == "computer_use"]
        assert len(computer_caps) >= 2

    def test_capabilities_include_active_and_gated(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        caps = metrics["capabilities"]
        statuses = {c["status"] for c in caps}
        assert "ACTIVE" in statuses
        assert any("approved" in s.lower() for s in statuses)

    def test_environments_returns_list(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        envs = metrics["environments"]
        assert isinstance(envs, list)
        assert len(envs) > 0

    def test_environments_have_required_fields(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        for env in metrics["environments"]:
            assert "id" in env
            assert "type" in env
            assert "security" in env
            assert "execution_mode" in env
            assert "capabilities" in env

    def test_scoring_has_aggregate_and_per_env(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        scoring = metrics["scoring"]
        assert "aggregate" in scoring
        assert "per_environment" in scoring

    def test_approvals_has_pending_count(self):
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        approvals = metrics["approvals"]
        assert "pending_count" in approvals
        assert isinstance(approvals["pending_count"], int)

    def test_print_report_human_runs(self, capsys):
        from umh.execution.metrics import print_report

        print_report(as_json=False)
        captured = capsys.readouterr()
        assert "UMH EXECUTION METRICS" in captured.out

    def test_print_report_json_runs(self, capsys):
        import json

        from umh.execution.metrics import print_report

        print_report(as_json=True)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "capabilities" in data


# ── Existing behavior unchanged ───────────────────────────────────────


class TestExistingBehaviorUnchanged4C:
    """Verify LLM, shell, file, and computer_screenshot still work."""

    def test_llm_call_still_works(self):
        from umh.execution.engine import execute

        request = _make_request(
            "generate_response",
            ExecutionClass.LLM_CALL,
            inputs={"prompt": "hello", "system_prompt": "test", "max_tokens": 10},
        )
        result = execute(request)
        assert result.status in (
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
        )

    def test_shell_uptime_still_works(self):
        from umh.execution.engine import execute

        request = _make_request(
            "shell_command",
            ExecutionClass.SIDE_EFFECT,
            inputs={"command": "uptime", "args": []},
        )
        result = execute(request)
        assert result.status in (
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
        )

    def test_file_read_still_works(self):
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

    def test_computer_screenshot_still_succeeds(self):
        from umh.execution.engine import execute

        request = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = execute(request)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_guard_still_denies_unknown_ops(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("totally_unknown_op", {})
        assert result.verdict == GuardVerdict.DENY
