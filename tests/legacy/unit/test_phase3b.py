"""Tests for Phase 3B: Environment Activation (Scoring + Sandbox Routing).

Verifies:
- Sandbox environment definition and properties
- Conditional routing: sandboxed file ops → sandbox env
- Environment-aware scoring: composite keying + backward compatibility
- Observer pipeline feeds environment_type to scorer
- Execution behavior unchanged
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


class TestSandboxEnvironmentDefinition:
    """Verify the sandbox environment is properly defined."""

    def test_sandbox_env_exists_in_registry(self):
        from umh.execution.environment import get_environment

        env = get_environment("sandbox")
        assert env is not None
        assert env.id == "sandbox"

    def test_sandbox_env_type(self):
        from umh.execution.environment import EnvironmentType, get_environment

        env = get_environment("sandbox")
        assert env.env_type == EnvironmentType.SANDBOX

    def test_sandbox_security_level(self):
        from umh.execution.environment import SecurityLevel, get_environment

        env = get_environment("sandbox")
        assert env.security_level == SecurityLevel.SANDBOXED

    def test_sandbox_supports_file_operation(self):
        from umh.execution.environment import get_environment

        env = get_environment("sandbox")
        assert env.supports("file_operation")

    def test_sandbox_supports_shell_command(self):
        from umh.execution.environment import get_environment

        env = get_environment("sandbox")
        assert env.supports("shell_command")

    def test_sandbox_does_not_support_llm_call(self):
        from umh.execution.environment import get_environment

        env = get_environment("sandbox")
        assert not env.supports("llm_call")

    def test_registry_lists_both_environments(self):
        from umh.execution.environment import list_environments

        envs = list_environments()
        ids = [e.id for e in envs]
        assert "local" in ids
        assert "sandbox" in ids
        assert len(envs) >= 2


class TestConditionalRouting:
    """Verify select_environment() routes based on sandbox constraint."""

    def test_file_read_no_sandbox_routes_local(self):
        from umh.execution.environment import EnvironmentType, select_environment

        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, sandbox=False)
        env = select_environment(req)
        assert env.id == "local"
        assert env.env_type == EnvironmentType.LOCAL

    def test_file_read_with_sandbox_routes_local_no_real_backing(self):
        from umh.execution.environment import select_environment

        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"

    def test_file_list_with_sandbox_routes_local_no_real_backing(self):
        from umh.execution.environment import select_environment

        req = _make_request("file_list", ExecutionClass.SIDE_EFFECT, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"

    def test_file_stat_with_sandbox_routes_local_no_real_backing(self):
        from umh.execution.environment import select_environment

        req = _make_request("file_stat", ExecutionClass.SIDE_EFFECT, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"

    def test_file_write_with_sandbox_routes_local_no_real_backing(self):
        from umh.execution.environment import select_environment

        req = _make_request("file_write", ExecutionClass.SIDE_EFFECT, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"

    def test_file_delete_with_sandbox_routes_local_no_real_backing(self):
        from umh.execution.environment import select_environment

        req = _make_request("file_delete", ExecutionClass.SIDE_EFFECT, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"

    def test_shell_command_with_sandbox_stays_local(self):
        from umh.execution.environment import select_environment

        req = _make_request(
            "shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"}, sandbox=True
        )
        env = select_environment(req)
        assert env.id == "local"

    def test_llm_call_with_sandbox_stays_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("utility", ExecutionClass.LLM_CALL, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"

    def test_pure_with_sandbox_stays_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("compute", ExecutionClass.PURE, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"


class TestEnvironmentAwareScoring:
    """Verify CapabilityScorer records per-environment stats."""

    def test_record_populates_env_stats(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()
        event = ExecutionEvent(
            execution_id="t1",
            operation="file_read",
            capability_type="file_operation",
            execution_class="side_effect",
            status="succeeded",
            latency_ms=5,
            environment_id="local",
            environment_type="local",
        )
        scorer.record(event)

        env_stats = scorer.get_env_stats("file_operation", "local")
        assert env_stats.total_calls == 1
        assert env_stats.successful_calls == 1

    def test_env_stats_separate_by_environment(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()

        local_event = ExecutionEvent(
            execution_id="t1",
            operation="file_read",
            capability_type="file_operation",
            execution_class="side_effect",
            status="succeeded",
            latency_ms=3,
            environment_type="local",
        )
        sandbox_event = ExecutionEvent(
            execution_id="t2",
            operation="file_read",
            capability_type="file_operation",
            execution_class="side_effect",
            status="succeeded",
            latency_ms=10,
            environment_type="sandbox",
        )

        scorer.record(local_event)
        scorer.record(sandbox_event)

        local_stats = scorer.get_env_stats("file_operation", "local")
        sandbox_stats = scorer.get_env_stats("file_operation", "sandbox")

        assert local_stats.total_calls == 1
        assert local_stats.avg_latency_ms == 3.0
        assert sandbox_stats.total_calls == 1
        assert sandbox_stats.avg_latency_ms == 10.0

    def test_aggregate_stats_unchanged(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()

        for i, env in enumerate(["local", "sandbox", "local"]):
            event = ExecutionEvent(
                execution_id=f"t{i}",
                operation="file_read",
                capability_type="file_operation",
                execution_class="side_effect",
                status="succeeded",
                latency_ms=10,
                environment_type=env,
            )
            scorer.record(event)

        agg = scorer.get_stats("file_operation")
        assert agg.total_calls == 3
        assert agg.successful_calls == 3

    def test_get_env_stats_empty_returns_default(self):
        from umh.execution.scoring import CapabilityScorer

        scorer = CapabilityScorer()
        stats = scorer.get_env_stats("file_operation", "container")
        assert stats.total_calls == 0
        assert stats.success_rate == 0.0

    def test_get_all_env_stats_keys_format(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()

        for cap, env in [("llm_call", "local"), ("file_operation", "sandbox")]:
            event = ExecutionEvent(
                execution_id=f"t_{cap}_{env}",
                operation="test",
                capability_type=cap,
                execution_class="side_effect",
                status="succeeded",
                latency_ms=1,
                environment_type=env,
            )
            scorer.record(event)

        all_env = scorer.get_all_env_stats()
        assert "llm_call:local" in all_env
        assert "file_operation:sandbox" in all_env

    def test_reset_clears_env_stats(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()
        event = ExecutionEvent(
            execution_id="t1",
            operation="file_read",
            capability_type="file_operation",
            execution_class="side_effect",
            status="succeeded",
            latency_ms=5,
            environment_type="sandbox",
        )
        scorer.record(event)
        assert scorer.get_env_stats("file_operation", "sandbox").total_calls == 1

        scorer.reset()
        assert scorer.get_env_stats("file_operation", "sandbox").total_calls == 0
        assert scorer.get_stats("file_operation").total_calls == 0

    def test_env_stats_track_failures_separately(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()

        local_ok = ExecutionEvent(
            execution_id="t1",
            operation="file_read",
            capability_type="file_operation",
            execution_class="side_effect",
            status="succeeded",
            environment_type="local",
        )
        sandbox_fail = ExecutionEvent(
            execution_id="t2",
            operation="file_read",
            capability_type="file_operation",
            execution_class="side_effect",
            status="failed",
            error="sandbox denied",
            environment_type="sandbox",
        )

        scorer.record(local_ok)
        scorer.record(sandbox_fail)

        assert scorer.get_env_stats("file_operation", "local").success_rate == 1.0
        assert scorer.get_env_stats("file_operation", "sandbox").success_rate == 0.0
        assert scorer.get_env_stats("file_operation", "sandbox").last_error == "sandbox denied"
        assert scorer.get_stats("file_operation").success_rate == 0.5

    def test_env_stats_cost_accumulation(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()

        for i, (env, cost) in enumerate([("local", 0.01), ("local", 0.02), ("sandbox", 0.005)]):
            event = ExecutionEvent(
                execution_id=f"t{i}",
                operation="utility",
                capability_type="llm_call",
                execution_class="llm_call",
                status="succeeded",
                cost_usd=cost,
                environment_type=env,
            )
            scorer.record(event)

        local = scorer.get_env_stats("llm_call", "local")
        sandbox = scorer.get_env_stats("llm_call", "sandbox")
        agg = scorer.get_stats("llm_call")

        assert abs(local.total_cost_usd - 0.03) < 0.0001
        assert abs(sandbox.total_cost_usd - 0.005) < 0.0001
        assert abs(agg.total_cost_usd - 0.035) < 0.0001


class TestObserverEnvironmentPipeline:
    """Verify observer feeds correct environment_type through to scorer."""

    def test_sandboxed_request_observer_captures_local_env_no_real_sandbox(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request(
            "file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": "/tmp/test"}, sandbox=True
        )
        observer.on_request(req)

        assert req.execution_id in observer._pending
        pending = observer._pending[req.execution_id]
        env_id = pending[2]
        env_type = pending[3]
        assert env_id == "local"
        assert env_type == "local"

    def test_non_sandboxed_request_observer_captures_local_env(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request(
            "file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": "/tmp/test"}, sandbox=False
        )
        observer.on_request(req)

        pending = observer._pending[req.execution_id]
        env_id = pending[2]
        env_type = pending[3]
        assert env_id == "local"
        assert env_type == "local"

    def test_shell_command_sandboxed_stays_local_in_observer(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request(
            "shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"}, sandbox=True
        )
        observer.on_request(req)

        pending = observer._pending[req.execution_id]
        env_id = pending[2]
        env_type = pending[3]
        assert env_id == "local"
        assert env_type == "local"


class TestExecutionBehaviorUnchanged3B:
    """Verify execution behavior is identical after Phase 3B changes."""

    def test_shell_command_still_works(self):
        from umh.execution.engine import execute

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"})
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_file_read_still_works(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"phase 3b test")
        os.close(fd)
        try:
            req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path})
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "phase 3b test"
        finally:
            os.unlink(path)

    def test_guard_still_blocks_metacharacters(self):
        from umh.execution.engine import execute

        req = _make_request(
            "shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "echo $HOME"}
        )
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED

    def test_sandbox_flag_does_not_alter_file_read_behavior(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"sandbox flag test")
        os.close(fd)
        try:
            req = _make_request(
                "file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path}, sandbox=True
            )
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "sandbox flag test"
        finally:
            os.unlink(path)

    def test_llm_path_unchanged(self):
        from umh.execution.engine import execute

        req = _make_request("utility", ExecutionClass.LLM_CALL, inputs={"prompt": "test"})
        with patch("umh.runtime_engine.model_router.call_with_fallback") as mock:
            mock_result = MagicMock()
            mock_result.output = "3b test"
            mock_result.provider = "test"
            mock_result.model = "test"
            mock_result.tokens_used = 0
            mock_result.input_tokens = 0
            mock_result.output_tokens = 0
            mock_result.cost_usd = 0.0
            mock.return_value = mock_result

            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
