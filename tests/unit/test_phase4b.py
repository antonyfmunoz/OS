"""Tests for Phase 4B: Computer Use Adapter Activation.

Verifies:
- Safe computer operations route through execute() and succeed
- Computer use adapter returns real data (screenshot, screen size, active window)
- Guard allows safe read-only computer operations
- Guard blocks mutation operations (click/type/key/scroll/drag)
- Unknown computer operations denied by guard
- Adapter returns requires_approval for mutation ops
- Environment enforcement: computer_use → local (REAL) only
- Observability: correct capability_type, adapter, execution_mode
- Existing LLM, shell, and file_read behavior unchanged
"""

import sys

sys.path.insert(0, "/opt/OS")

import tempfile
import os
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


class TestGuardComputerOperations:
    """Verify security guard allows safe and blocks risky computer ops."""

    def test_guard_allows_screenshot(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_screenshot", {})
        assert result.verdict == GuardVerdict.ALLOW

    def test_guard_allows_get_screen_size(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_get_screen_size", {})
        assert result.verdict == GuardVerdict.ALLOW

    def test_guard_allows_get_active_window(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_get_active_window", {})
        assert result.verdict == GuardVerdict.ALLOW

    def test_guard_requires_approval_click(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_click", {"x": 100, "y": 200})
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL

    def test_guard_requires_approval_type(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_type", {"text": "hello"})
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL

    def test_guard_requires_approval_key(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_key", {"key": "Return"})
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL

    def test_guard_requires_approval_scroll(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_scroll", {"direction": "down"})
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL

    def test_guard_requires_approval_drag(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_drag", {"x1": 0, "y1": 0, "x2": 100, "y2": 100})
        assert result.verdict == GuardVerdict.REQUIRES_APPROVAL

    def test_guard_denies_unknown_computer_op(self):
        from umh.security.execution_guard import GuardVerdict, check_execution

        result = check_execution("computer_teleport", {})
        assert result.verdict == GuardVerdict.DENY

    def test_guard_reason_mentions_read_only_for_safe(self):
        from umh.security.execution_guard import check_execution

        result = check_execution("computer_screenshot", {})
        assert "read-only" in result.reason.lower()

    def test_guard_reason_mentions_approval_for_mutation(self):
        from umh.security.execution_guard import check_execution

        result = check_execution("computer_click", {})
        assert "approval" in result.reason.lower()


class TestComputerUseAdapterReal:
    """Verify adapter executes real operations."""

    def test_screenshot_succeeds(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from umh.execution.environment import get_environment

        adapter = ComputerUseAdapter()
        env = get_environment("local")
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("width") > 0
        assert result.outputs.get("height") > 0
        assert len(result.outputs.get("image_base64", "")) > 0

    def test_screenshot_output_includes_adapter(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from umh.execution.environment import get_environment

        adapter = ComputerUseAdapter()
        env = get_environment("local")
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert result.outputs.get("adapter") == "computer_use_adapter"

    def test_screenshot_format_is_png(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from umh.execution.environment import get_environment

        adapter = ComputerUseAdapter()
        env = get_environment("local")
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert result.outputs.get("format") == "png"

    def test_get_screen_size_succeeds(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from umh.execution.environment import get_environment

        adapter = ComputerUseAdapter()
        env = get_environment("local")
        req = _make_request("computer_get_screen_size", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("width") > 0
        assert result.outputs.get("height") > 0
        assert "x" in result.outputs.get("text", "")

    def test_get_active_window_succeeds(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from umh.execution.environment import get_environment

        adapter = ComputerUseAdapter()
        env = get_environment("local")
        req = _make_request("computer_get_active_window", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("text") is not None
        assert result.outputs.get("adapter") == "computer_use_adapter"

    def test_mutation_returns_requires_approval(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from umh.execution.environment import get_environment

        adapter = ComputerUseAdapter()
        env = get_environment("local")
        req = _make_request("computer_click", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True
        assert result.outputs.get("adapter") == "computer_use_adapter"

    def test_unknown_computer_op_returns_not_implemented(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from umh.execution.environment import get_environment

        adapter = ComputerUseAdapter()
        env = get_environment("local")
        req = _make_request("computer_teleport", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("not_implemented") is True


class TestComputerUseEndToEnd:
    """Verify computer_use flows through the full execute() pipeline."""

    def test_screenshot_through_execute(self):
        from umh.execution.engine import execute

        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("adapter") == "computer_use_adapter"
        assert result.outputs.get("width") > 0

    def test_screen_size_through_execute(self):
        from umh.execution.engine import execute

        req = _make_request("computer_get_screen_size", ExecutionClass.SIDE_EFFECT)
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("width") > 0

    def test_active_window_through_execute(self):
        from umh.execution.engine import execute

        req = _make_request("computer_get_active_window", ExecutionClass.SIDE_EFFECT)
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_click_blocked_by_guard(self):
        from umh.execution.engine import execute

        req = _make_request(
            "computer_click", ExecutionClass.SIDE_EFFECT, inputs={"x": 100, "y": 200}
        )
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True
        assert "approval_id" in result.outputs

    def test_type_blocked_by_guard(self):
        from umh.execution.engine import execute

        req = _make_request("computer_type", ExecutionClass.SIDE_EFFECT, inputs={"text": "hello"})
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True
        assert "approval_id" in result.outputs

    def test_scroll_blocked_by_guard(self):
        from umh.execution.engine import execute

        req = _make_request("computer_scroll", ExecutionClass.SIDE_EFFECT)
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED


class TestComputerUseEnvironment:
    """Verify computer_use environment enforcement."""

    def test_computer_use_routes_to_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"

    def test_local_is_real(self):
        from umh.execution.environment import ExecutionMode, get_environment

        env = get_environment("local")
        assert env.execution_mode == ExecutionMode.REAL

    def test_computer_use_denied_in_sandbox(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("sandbox")
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY

    def test_computer_use_denied_in_container(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("container")
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY

    def test_computer_use_allowed_in_local(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("local")
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.ALLOW


class TestComputerUseObservability:
    """Verify observability captures correct fields for computer_use."""

    def test_observer_captures_computer_use_env(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        observer.on_request(req)

        pending = observer._pending[req.execution_id]
        env_id = pending[2]
        env_type = pending[3]
        exec_mode = pending[4]
        assert env_id == "local"
        assert env_type == "local"
        assert exec_mode == "real"

    def test_observer_classifies_computer_use(self):
        from umh.execution.observability import _classify_capability

        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        assert _classify_capability(req) == "computer_use"

    def test_event_has_correct_adapter(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="computer_screenshot",
            capability_type="computer_use",
            execution_class="side_effect",
            status="succeeded",
            adapter="computer_use_adapter",
            execution_mode="real",
        )
        d = event.to_dict()
        assert d["capability_type"] == "computer_use"
        assert d["adapter"] == "computer_use_adapter"
        assert d["execution_mode"] == "real"


class TestExistingBehaviorUnchanged4B:
    """Verify no regressions in existing capabilities."""

    def test_shell_command_still_works(self):
        from umh.execution.engine import execute

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"})
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_file_read_still_works(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"phase 4b test")
        os.close(fd)
        try:
            req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path})
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "phase 4b test"
        finally:
            os.unlink(path)

    def test_guard_still_blocks_shell_metacharacters(self):
        from umh.execution.engine import execute

        req = _make_request(
            "shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "echo $HOME"}
        )
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED

    def test_llm_path_unchanged(self):
        from umh.execution.engine import execute

        req = _make_request("utility", ExecutionClass.LLM_CALL, inputs={"prompt": "test"})
        with patch("umh.runtime_engine.model_router.call_with_fallback") as mock:
            mock_result = MagicMock()
            mock_result.output = "4b test"
            mock_result.provider = "test"
            mock_result.model = "test"
            mock_result.tokens_used = 0
            mock_result.input_tokens = 0
            mock_result.output_tokens = 0
            mock_result.cost_usd = 0.0
            mock.return_value = mock_result

            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED

    def test_browser_still_denied(self):
        from umh.execution.engine import execute

        req = _make_request(
            "browser_navigate", ExecutionClass.SIDE_EFFECT, inputs={"url": "https://example.com"}
        )
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED
