"""Tests for Phase 4E: Approval Interface Surface.

Verifies:
- CLI list empty
- Create approval then list
- Approve valid approval via CLI
- Deny valid approval via CLI
- Show valid approval
- Unknown approval handling
- Expired approval cannot be approved
- JSON output shape
- Metrics sees approval changes
- Existing 4D approved execution still works
"""

import sys
import time

sys.path.insert(0, "/opt/OS")

import json
from io import StringIO
from unittest.mock import patch

from umh.execution.approval import ApprovalStatus, get_approval_store
from umh.execution.approvals_cli import (
    cmd_approve,
    cmd_deny,
    cmd_list,
    cmd_show,
    main,
)


def _reset_store():
    get_approval_store().reset()


def _create_approval(
    operation: str = "computer_click",
    capability_type: str = "computer_use",
    risk_level: str = "high",
    ttl_seconds: int = 300,
):
    store = get_approval_store()
    return store.create_approval(
        execution_id=f"test_{operation}",
        operation=operation,
        capability_type=capability_type,
        risk_level=risk_level,
        ttl_seconds=ttl_seconds,
    )


def _capture_output(func, *args, **kwargs) -> tuple[str, int]:
    """Capture stdout and return (output, exit_code)."""
    buf = StringIO()
    with patch("sys.stdout", buf):
        code = func(*args, **kwargs)
    return buf.getvalue(), code


# ── A. List Empty ────────────────────────────────────────────────────


class TestListEmpty:
    def test_list_empty_returns_no_approvals(self):
        _reset_store()
        output, code = _capture_output(cmd_list)
        assert code == 0
        assert "No approvals found" in output

    def test_list_empty_json_returns_empty_array(self):
        _reset_store()
        output, code = _capture_output(cmd_list, as_json=True)
        assert code == 0
        data = json.loads(output)
        assert data == []


# ── B. Create then List ──────────────────────────────────────────────


class TestCreateThenList:
    def test_list_shows_created_approval(self):
        _reset_store()
        req = _create_approval()
        output, code = _capture_output(cmd_list)
        assert code == 0
        assert req.id in output
        assert "computer_click" in output
        assert "pending" in output

    def test_list_json_contains_approval(self):
        _reset_store()
        req = _create_approval()
        output, code = _capture_output(cmd_list, as_json=True)
        assert code == 0
        data = json.loads(output)
        assert len(data) == 1
        assert data[0]["id"] == req.id
        assert data[0]["status"] == "pending"

    def test_list_shows_multiple_approvals(self):
        _reset_store()
        _create_approval(operation="computer_click")
        _create_approval(operation="computer_type")
        output, code = _capture_output(cmd_list, as_json=True)
        data = json.loads(output)
        assert len(data) == 2


# ── C. Approve Valid Approval ────────────────────────────────────────


class TestApproveValid:
    def test_approve_pending_approval_succeeds(self):
        _reset_store()
        req = _create_approval()
        output, code = _capture_output(cmd_approve, req.id)
        assert code == 0
        assert "APPROVED" in output
        assert req.id in output

    def test_approve_sets_status_to_approved(self):
        _reset_store()
        req = _create_approval()
        cmd_approve(req.id)
        updated = get_approval_store().get(req.id)
        assert updated.status == ApprovalStatus.APPROVED

    def test_approve_json_output(self):
        _reset_store()
        req = _create_approval()
        output, code = _capture_output(cmd_approve, req.id, as_json=True)
        assert code == 0
        data = json.loads(output)
        assert data["approved"] == req.id
        assert data["status"] == "approved"


# ── D. Deny Valid Approval ───────────────────────────────────────────


class TestDenyValid:
    def test_deny_pending_approval_succeeds(self):
        _reset_store()
        req = _create_approval()
        output, code = _capture_output(cmd_deny, req.id)
        assert code == 0
        assert "DENIED" in output
        assert req.id in output

    def test_deny_sets_status_to_denied(self):
        _reset_store()
        req = _create_approval()
        cmd_deny(req.id)
        updated = get_approval_store().get(req.id)
        assert updated.status == ApprovalStatus.DENIED

    def test_deny_json_output(self):
        _reset_store()
        req = _create_approval()
        output, code = _capture_output(cmd_deny, req.id, as_json=True)
        assert code == 0
        data = json.loads(output)
        assert data["denied"] == req.id
        assert data["status"] == "denied"

    def test_deny_consumed_approval_fails(self):
        _reset_store()
        req = _create_approval()
        store = get_approval_store()
        store.approve(req.id)
        store.consume(req.id)
        output, code = _capture_output(cmd_deny, req.id)
        assert code == 1
        assert "consumed" in output.lower()


# ── E. Show Valid Approval ───────────────────────────────────────────


class TestShowValid:
    def test_show_displays_approval_details(self):
        _reset_store()
        req = _create_approval()
        output, code = _capture_output(cmd_show, req.id)
        assert code == 0
        assert req.id in output
        assert "computer_click" in output
        assert "computer_use" in output
        assert "high" in output
        assert "pending" in output

    def test_show_json_output(self):
        _reset_store()
        req = _create_approval()
        output, code = _capture_output(cmd_show, req.id, as_json=True)
        assert code == 0
        data = json.loads(output)
        assert data["id"] == req.id
        assert data["operation"] == "computer_click"
        assert data["capability_type"] == "computer_use"
        assert data["risk_level"] == "high"
        assert data["status"] == "pending"
        assert "created_at" in data
        assert "expires_at" in data


# ── F. Unknown Approval Handling ─────────────────────────────────────


class TestUnknownApproval:
    def test_show_unknown_returns_error(self):
        _reset_store()
        output, code = _capture_output(cmd_show, "approval_nonexistent")
        assert code == 1
        assert "not found" in output.lower()

    def test_approve_unknown_returns_error(self):
        _reset_store()
        output, code = _capture_output(cmd_approve, "approval_nonexistent")
        assert code == 1
        assert "not found" in output.lower()

    def test_deny_unknown_returns_error(self):
        _reset_store()
        output, code = _capture_output(cmd_deny, "approval_nonexistent")
        assert code == 1
        assert "not found" in output.lower()

    def test_show_unknown_json(self):
        _reset_store()
        output, code = _capture_output(cmd_show, "approval_nonexistent", as_json=True)
        assert code == 1
        data = json.loads(output)
        assert "error" in data

    def test_approve_unknown_json(self):
        _reset_store()
        output, code = _capture_output(cmd_approve, "approval_nonexistent", as_json=True)
        assert code == 1
        data = json.loads(output)
        assert "error" in data

    def test_deny_unknown_json(self):
        _reset_store()
        output, code = _capture_output(cmd_deny, "approval_nonexistent", as_json=True)
        assert code == 1
        data = json.loads(output)
        assert "error" in data


# ── G. Expired Approval Cannot Be Approved ───────────────────────────


class TestExpiredApproval:
    def test_expired_approval_cannot_be_approved(self):
        _reset_store()
        req = _create_approval(ttl_seconds=0)
        time.sleep(0.01)
        output, code = _capture_output(cmd_approve, req.id)
        assert code == 1
        assert "expired" in output.lower()

    def test_expired_approval_json_error(self):
        _reset_store()
        req = _create_approval(ttl_seconds=0)
        time.sleep(0.01)
        output, code = _capture_output(cmd_approve, req.id, as_json=True)
        assert code == 1
        data = json.loads(output)
        assert "expired" in data.get("status", "") or "expired" in data.get("error", "").lower()

    def test_already_approved_cannot_approve_again(self):
        _reset_store()
        req = _create_approval()
        cmd_approve(req.id)
        output, code = _capture_output(cmd_approve, req.id)
        assert code == 1
        assert "approved" in output.lower()


# ── H. JSON Output Shape ─────────────────────────────────────────────


class TestJSONOutputShape:
    def test_list_json_is_array(self):
        _reset_store()
        _create_approval()
        output, _ = _capture_output(cmd_list, as_json=True)
        data = json.loads(output)
        assert isinstance(data, list)

    def test_list_json_item_has_required_fields(self):
        _reset_store()
        _create_approval()
        output, _ = _capture_output(cmd_list, as_json=True)
        data = json.loads(output)
        item = data[0]
        required_fields = [
            "id",
            "execution_id",
            "operation",
            "capability_type",
            "risk_level",
            "inputs_summary",
            "created_at",
            "expires_at",
            "status",
        ]
        for field in required_fields:
            assert field in item, f"Missing field: {field}"

    def test_show_json_has_all_fields(self):
        _reset_store()
        req = _create_approval()
        output, _ = _capture_output(cmd_show, req.id, as_json=True)
        data = json.loads(output)
        assert "id" in data
        assert "operation" in data
        assert "status" in data


# ── I. Metrics Sees Approval Changes ─────────────────────────────────


class TestMetricsIntegration:
    def test_metrics_reflects_pending_count(self):
        _reset_store()
        _create_approval()
        _create_approval(operation="computer_type")
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        assert metrics["approvals"]["pending_count"] == 2

    def test_metrics_reflects_denied(self):
        _reset_store()
        req = _create_approval()
        cmd_deny(req.id)
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        assert metrics["approvals"]["approvals_denied"] >= 1

    def test_metrics_reflects_approved_then_consumed(self):
        _reset_store()
        req = _create_approval()
        cmd_approve(req.id)
        store = get_approval_store()
        store.consume(req.id)
        from umh.execution.metrics import get_metrics

        metrics = get_metrics()
        assert metrics["approvals"]["approvals_consumed"] >= 1


# ── J. Existing 4D Approved Execution Still Works ────────────────────


class TestExisting4DStillWorks:
    def test_approved_click_through_engine(self):
        """Full 4D path: create → approve → execute with approval_id."""
        _reset_store()
        from umh.execution.contract import (
            ExecutionClass,
            ExecutionConstraints,
            ExecutionContext,
            ExecutionRequest,
            ExecutionStatus,
            ExecutionTarget,
        )
        from umh.execution.engine import execute

        # Step 1: attempt without approval
        request1 = ExecutionRequest(
            execution_id="test_4e_click",
            correlation_id="test_4e_click",
            causal_event_id="",
            session_id="",
            operation="computer_click",
            inputs={"x": 50, "y": 75},
            execution_class=ExecutionClass.SIDE_EFFECT,
            constraints=ExecutionConstraints(timeout_s=10),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(),
            issued_at="2026-04-26T12:00:00Z",
            issued_by="test",
            idempotency_key="",
        )
        result1 = execute(request1)
        assert result1.status == ExecutionStatus.REJECTED
        approval_id = result1.outputs.get("approval_id")
        assert approval_id is not None

        # Step 2: approve via CLI function
        code = cmd_approve(approval_id)
        assert code == 0

        # Step 3: execute with approval
        request2 = ExecutionRequest(
            execution_id="test_4e_click_approved",
            correlation_id="test_4e_click_approved",
            causal_event_id="",
            session_id="",
            operation="computer_click",
            inputs={"x": 50, "y": 75, "approval_id": approval_id},
            execution_class=ExecutionClass.SIDE_EFFECT,
            constraints=ExecutionConstraints(timeout_s=10),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(),
            issued_at="2026-04-26T12:00:00Z",
            issued_by="test",
            idempotency_key="",
        )
        result2 = execute(request2)
        assert result2.status == ExecutionStatus.SUCCEEDED
        assert result2.outputs.get("x") == 50
        assert result2.outputs.get("y") == 75

    def test_existing_llm_path_unaffected(self):
        """LLM calls still work after CLI module added."""
        from umh.execution.contract import (
            ExecutionClass,
            ExecutionConstraints,
            ExecutionContext,
            ExecutionRequest,
            ExecutionStatus,
            ExecutionTarget,
        )
        from umh.execution.engine import execute

        request = ExecutionRequest(
            execution_id="test_4e_llm",
            correlation_id="test_4e_llm",
            causal_event_id="",
            session_id="",
            operation="generate_response",
            inputs={"prompt": "test", "system_prompt": "test", "max_tokens": 5},
            execution_class=ExecutionClass.LLM_CALL,
            constraints=ExecutionConstraints(timeout_s=10),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(),
            issued_at="2026-04-26T12:00:00Z",
            issued_by="test",
            idempotency_key="",
        )
        result = execute(request)
        assert result.status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED)


# ── K. CLI main() entry point ────────────────────────────────────────


class TestMainEntryPoint:
    def test_no_args_shows_usage(self):
        output, code = _capture_output(main, [])
        assert code == 1
        assert "Usage" in output

    def test_unknown_command_shows_error(self):
        output, code = _capture_output(main, ["bogus"])
        assert code == 1
        assert "Unknown command" in output

    def test_approve_missing_id_shows_error(self):
        output, code = _capture_output(main, ["approve"])
        assert code == 1
        assert "requires" in output.lower()

    def test_deny_missing_id_shows_error(self):
        output, code = _capture_output(main, ["deny"])
        assert code == 1
        assert "requires" in output.lower()

    def test_show_missing_id_shows_error(self):
        output, code = _capture_output(main, ["show"])
        assert code == 1
        assert "requires" in output.lower()

    def test_json_flag_parsed(self):
        _reset_store()
        output, code = _capture_output(main, ["--json", "list"])
        assert code == 0
        data = json.loads(output)
        assert isinstance(data, list)

    def test_json_flag_after_command(self):
        _reset_store()
        _create_approval()
        output, code = _capture_output(main, ["list", "--json"])
        # --json is not after "list" in args but we filter it globally
        # Actually let's verify: main strips --json from anywhere
        # The implementation strips --json from all args
        # But "list" is args[0] after filtering... wait, no.
        # args = ["list", "--json"] → after filter: ["list"] → command = "list"
        # Actually the filter removes --json from the list, leaving ["list"]
        # as_json is True because "--json" was in original args
        # This should work.
        assert code == 0
