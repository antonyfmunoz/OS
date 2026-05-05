"""Tests for Phase 4A.5: Environment Execution Reality Stabilization.

Verifies:
- ExecutionMode enum exists with REAL, SIMULATED, NOT_IMPLEMENTED
- Local environment is REAL
- Sandbox environment is SIMULATED
- Container environment is NOT_IMPLEMENTED
- requires_real_execution() helper logic
- Enforcement denies non-REAL environments for real execution
- Scoring ignores NOT_IMPLEMENTED environments
- Selection handles 0 valid candidates via fallback
- Observability captures execution_mode
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
    max_tokens: int = 0,
) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=f"test_{operation}",
        correlation_id=f"test_{operation}",
        causal_event_id="",
        session_id="",
        operation=operation,
        inputs=inputs or {},
        execution_class=execution_class,
        constraints=ExecutionConstraints(
            timeout_s=timeout_s, sandbox=sandbox, max_tokens=max_tokens
        ),
        target=ExecutionTarget(node_id="local", transport="test"),
        context=ExecutionContext(),
        issued_at="2026-04-26T12:00:00Z",
        issued_by="test",
        idempotency_key="",
    )


class TestExecutionModeEnum:
    """Verify ExecutionMode enum exists with correct values."""

    def test_real_mode_exists(self):
        from umh.execution.environment import ExecutionMode

        assert ExecutionMode.REAL.value == "real"

    def test_simulated_mode_exists(self):
        from umh.execution.environment import ExecutionMode

        assert ExecutionMode.SIMULATED.value == "simulated"

    def test_not_implemented_mode_exists(self):
        from umh.execution.environment import ExecutionMode

        assert ExecutionMode.NOT_IMPLEMENTED.value == "not_implemented"

    def test_all_modes_present(self):
        from umh.execution.environment import ExecutionMode

        values = {m.value for m in ExecutionMode}
        assert values == {"real", "simulated", "not_implemented"}


class TestEnvironmentExecutionModes:
    """Verify each registered environment has correct execution mode."""

    def test_local_is_real(self):
        from umh.execution.environment import ExecutionMode, get_environment

        env = get_environment("local")
        assert env.execution_mode == ExecutionMode.REAL

    def test_sandbox_is_simulated(self):
        from umh.execution.environment import ExecutionMode, get_environment

        env = get_environment("sandbox")
        assert env.execution_mode == ExecutionMode.SIMULATED

    def test_container_is_not_implemented(self):
        from umh.execution.environment import ExecutionMode, get_environment

        env = get_environment("container")
        assert env.execution_mode == ExecutionMode.NOT_IMPLEMENTED

    def test_environment_spec_default_is_real(self):
        from umh.execution.environment import (
            EnvironmentSpec,
            EnvironmentType,
            ExecutionMode,
            SecurityLevel,
        )

        env = EnvironmentSpec(
            id="test",
            env_type=EnvironmentType.LOCAL,
            supported_capabilities=frozenset({"llm_call"}),
            security_level=SecurityLevel.TRUSTED,
        )
        assert env.execution_mode == ExecutionMode.REAL


class TestRequiresRealExecution:
    """Verify the requires_real_execution helper."""

    def test_shell_command_requires_real(self):
        from umh.execution.environment import requires_real_execution

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        assert requires_real_execution(req) is True

    def test_file_read_requires_real(self):
        from umh.execution.environment import requires_real_execution

        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT)
        assert requires_real_execution(req) is True

    def test_llm_call_requires_real(self):
        from umh.execution.environment import requires_real_execution

        req = _make_request("utility", ExecutionClass.LLM_CALL)
        assert requires_real_execution(req) is True

    def test_browser_action_requires_real(self):
        from umh.execution.environment import requires_real_execution

        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        assert requires_real_execution(req) is True

    def test_computer_use_requires_real(self):
        from umh.execution.environment import requires_real_execution

        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        assert requires_real_execution(req) is True

    def test_pure_requires_real_by_default(self):
        from umh.execution.environment import requires_real_execution

        req = _make_request("compute", ExecutionClass.PURE)
        assert requires_real_execution(req) is True

    def test_pure_dry_run_does_not_require_real(self):
        from umh.execution.environment import requires_real_execution

        req = _make_request("compute", ExecutionClass.PURE, inputs={"dry_run": True})
        assert requires_real_execution(req) is False

    def test_file_write_requires_real(self):
        from umh.execution.environment import requires_real_execution

        req = _make_request("file_write", ExecutionClass.SIDE_EFFECT)
        assert requires_real_execution(req) is True


class TestEnforcementExecutionMode:
    """Verify enforcement denies non-REAL environments for real execution."""

    def test_deny_shell_in_simulated_sandbox(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("sandbox")
        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY
        assert "no real execution backing" in result.reason

    def test_deny_browser_in_not_implemented_container(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("container")
        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY
        assert "no real execution backing" in result.reason

    def test_allow_shell_in_real_local(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("local")
        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.ALLOW

    def test_allow_llm_in_real_local(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("local")
        req = _make_request("utility", ExecutionClass.LLM_CALL)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.ALLOW

    def test_deny_file_read_in_simulated_sandbox(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("sandbox")
        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY

    def test_allow_pure_dry_run_in_simulated(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            EnvironmentSpec,
            EnvironmentType,
            ExecutionMode,
            SecurityLevel,
            enforce_environment,
        )

        sim_env = EnvironmentSpec(
            id="sim_test",
            env_type=EnvironmentType.SANDBOX,
            supported_capabilities=frozenset({"pure"}),
            security_level=SecurityLevel.SANDBOXED,
            execution_mode=ExecutionMode.SIMULATED,
        )
        req = _make_request("compute", ExecutionClass.PURE, inputs={"dry_run": True})
        result = enforce_environment(req, sim_env)
        assert result.verdict == EnforcementVerdict.ALLOW

    def test_deny_reason_includes_mode(self):
        from umh.execution.environment import enforce_environment, get_environment

        env = get_environment("container")
        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert "not_implemented" in result.reason


class TestSelectionWithExecutionMode:
    """Verify select_environment filters by execution mode."""

    def test_browser_no_valid_env_falls_back_to_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"

    def test_shell_routes_to_local_only(self):
        from umh.execution.environment import select_environment

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"

    def test_file_read_sandboxed_routes_to_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"

    def test_llm_still_routes_to_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("utility", ExecutionClass.LLM_CALL)
        env = select_environment(req)
        assert env.id == "local"

    def test_computer_use_routes_to_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"


class TestScoringExecutionMode:
    """Verify scoring does not reward NOT_IMPLEMENTED environments."""

    def test_not_implemented_env_excluded_from_scoring(self):
        from umh.execution.environment import (
            ExecutionMode,
            select_environment,
        )
        from umh.execution.scoring import get_capability_scorer
        from umh.execution.observability import ExecutionEvent

        scorer = get_capability_scorer()
        scorer.reset()

        for i in range(10):
            scorer.record(
                ExecutionEvent(
                    execution_id=f"t{i}",
                    operation="browser_navigate",
                    capability_type="browser_action",
                    execution_class="side_effect",
                    status="succeeded",
                    latency_ms=1,
                    environment_type="container",
                )
            )

        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.execution_mode != ExecutionMode.NOT_IMPLEMENTED

    def test_simulated_env_excluded_from_scoring_for_real_exec(self):
        from umh.execution.scoring import get_capability_scorer
        from umh.execution.observability import ExecutionEvent
        from umh.execution.environment import select_environment

        scorer = get_capability_scorer()
        scorer.reset()

        for i in range(10):
            scorer.record(
                ExecutionEvent(
                    execution_id=f"t{i}",
                    operation="shell_command",
                    capability_type="shell_command",
                    execution_class="side_effect",
                    status="succeeded",
                    latency_ms=1,
                    environment_type="sandbox",
                )
            )

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"

    def test_real_env_stats_still_tracked(self):
        from umh.execution.scoring import get_capability_scorer
        from umh.execution.observability import ExecutionEvent

        scorer = get_capability_scorer()
        scorer.reset()

        scorer.record(
            ExecutionEvent(
                execution_id="t1",
                operation="shell_command",
                capability_type="shell_command",
                execution_class="side_effect",
                status="succeeded",
                latency_ms=5,
                environment_type="local",
            )
        )

        stats = scorer.get_env_stats("shell_command", "local")
        assert stats.total_calls == 1
        assert stats.success_rate == 1.0


class TestObservabilityExecutionMode:
    """Verify execution_mode appears in events and observer."""

    def test_event_has_execution_mode_field(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="shell_command",
            capability_type="shell_command",
            execution_class="side_effect",
            status="succeeded",
            execution_mode="real",
        )
        assert event.execution_mode == "real"

    def test_event_to_dict_includes_execution_mode(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="shell_command",
            capability_type="shell_command",
            execution_class="side_effect",
            status="succeeded",
            execution_mode="simulated",
        )
        d = event.to_dict()
        assert d["execution_mode"] == "simulated"

    def test_event_default_execution_mode_is_real(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="test",
            capability_type="test",
            execution_class="side_effect",
            status="succeeded",
        )
        assert event.execution_mode == "real"

    def test_observer_captures_execution_mode(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"})
        observer.on_request(req)

        pending = observer._pending[req.execution_id]
        exec_mode = pending[4]
        assert exec_mode == "real"

    def test_observer_browser_falls_back_to_local_real(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        observer.on_request(req)

        pending = observer._pending[req.execution_id]
        exec_mode = pending[4]
        assert exec_mode == "real"


class TestExistingBehaviorUnchanged4A5:
    """Verify no regressions in working execution paths."""

    def test_shell_command_still_works(self):
        from umh.execution.engine import execute

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"})
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_file_read_still_works(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"phase 4a5 test")
        os.close(fd)
        try:
            req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path})
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "phase 4a5 test"
        finally:
            os.unlink(path)

    def test_guard_still_blocks_metacharacters(self):
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
            mock_result.output = "4a5 test"
            mock_result.provider = "test"
            mock_result.model = "test"
            mock_result.tokens_used = 0
            mock_result.input_tokens = 0
            mock_result.output_tokens = 0
            mock_result.cost_usd = 0.0
            mock.return_value = mock_result

            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED

    def test_browser_still_denied_by_guard(self):
        from umh.execution.engine import execute

        req = _make_request(
            "browser_navigate", ExecutionClass.SIDE_EFFECT, inputs={"url": "https://example.com"}
        )
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED

    def test_sandbox_flag_does_not_break_file_read(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"sandbox reality test")
        os.close(fd)
        try:
            req = _make_request(
                "file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path}, sandbox=True
            )
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "sandbox reality test"
        finally:
            os.unlink(path)
