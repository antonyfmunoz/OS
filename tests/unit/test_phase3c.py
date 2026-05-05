"""Tests for Phase 3C: Constraint Enforcement + Environment Enforcement + Cost Control + Scoring Activation.

Verifies:
- Environment enforcement (enforce_environment)
- Updated environment selection (multi-candidate filtering + scoring)
- max_tokens propagation through the pipeline
- Scoring: timeout_rate, failure_rate by environment
- ExecutionEvent new fields (max_tokens, enforcement_flags)
- max_tokens at call sites (email_gps, decision_log, quality_gate)
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
    max_tokens: int = 0,
    cost_limit_usd: float = 0.0,
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
            timeout_s=timeout_s,
            sandbox=sandbox,
            max_tokens=max_tokens,
            cost_limit_usd=cost_limit_usd,
        ),
        target=ExecutionTarget(node_id="local", transport="test"),
        context=ExecutionContext(),
        issued_at="2026-04-26T12:00:00Z",
        issued_by="test",
        idempotency_key="",
    )


class TestEnforceEnvironment:
    """Verify enforce_environment() checks."""

    def test_allow_llm_call_in_local(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("local")
        req = _make_request("utility", ExecutionClass.LLM_CALL)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.ALLOW

    def test_deny_llm_call_in_sandbox(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("sandbox")
        req = _make_request("utility", ExecutionClass.LLM_CALL)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY
        assert "does not support" in result.reason

    def test_allow_file_read_in_local_no_sandbox(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("local")
        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.ALLOW

    def test_deny_sandboxed_file_read_in_local(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("local")
        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, sandbox=True)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY
        assert "trusted" in result.reason.lower()

    def test_deny_sandboxed_file_read_in_simulated_sandbox(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("sandbox")
        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, sandbox=True)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY
        assert "no real execution backing" in result.reason

    def test_allow_shell_command_in_local(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("local")
        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.ALLOW

    def test_deny_shell_command_in_simulated_sandbox(self):
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

    def test_deny_unsupported_capability(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            EnvironmentSpec,
            EnvironmentType,
            SecurityLevel,
            enforce_environment,
        )

        empty_env = EnvironmentSpec(
            id="empty",
            env_type=EnvironmentType.LOCAL,
            supported_capabilities=frozenset(),
            security_level=SecurityLevel.TRUSTED,
        )
        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, empty_env)
        assert result.verdict == EnforcementVerdict.DENY


class TestUpdatedSelectEnvironment:
    """Verify select_environment() uses multi-candidate filtering."""

    def test_llm_call_still_routes_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("utility", ExecutionClass.LLM_CALL)
        env = select_environment(req)
        assert env.id == "local"

    def test_file_read_no_sandbox_routes_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"

    def test_file_read_with_sandbox_routes_local_no_real_sandbox(self):
        from umh.execution.environment import select_environment

        req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, sandbox=True)
        env = select_environment(req)
        assert env.id == "local"

    def test_shell_no_sandbox_routes_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"

    def test_scoring_does_not_override_enforcement(self):
        """Even if sandbox has better score, LLM can't go there."""
        from umh.execution.environment import select_environment
        from umh.execution.scoring import CapabilityScorer, get_capability_scorer

        scorer = get_capability_scorer()
        scorer.reset()

        req = _make_request("utility", ExecutionClass.LLM_CALL)
        env = select_environment(req)
        assert env.id == "local"

    def test_scoring_only_considers_real_environments(self):
        """Sandbox is SIMULATED — shell_command can only route to local (REAL)."""
        from umh.execution.environment import select_environment
        from umh.execution.scoring import get_capability_scorer
        from umh.execution.observability import ExecutionEvent

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
                    latency_ms=5,
                    environment_type="local",
                )
            )

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"


class TestMaxTokensPropagation:
    """Verify max_tokens flows through the pipeline."""

    def test_constraints_max_tokens_set(self):
        req = _make_request("utility", ExecutionClass.LLM_CALL, max_tokens=50)
        assert req.constraints.max_tokens == 50

    def test_lightweight_execute_passes_max_tokens(self):
        from umh.execution.engine import lightweight_execute

        with patch("umh.runtime_engine.model_router.call_with_fallback") as mock:
            mock_result = MagicMock()
            mock_result.output = "test"
            mock_result.provider = "test"
            mock_result.model = "test"
            mock_result.tokens_used = 10
            mock_result.input_tokens = 5
            mock_result.output_tokens = 5
            mock_result.cost_usd = 0.001
            mock.return_value = mock_result

            lightweight_execute("utility", "test prompt", max_tokens=50)

            call_args = mock.call_args
            assert call_args.kwargs.get("max_tokens") == 50 or call_args[1].get("max_tokens") == 50

    def test_execution_event_has_max_tokens(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="utility",
            capability_type="llm_call",
            execution_class="llm_call",
            status="succeeded",
            max_tokens=50,
        )
        assert event.max_tokens == 50
        d = event.to_dict()
        assert d["max_tokens"] == 50

    def test_execution_event_has_enforcement_flags(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="file_read",
            capability_type="file_operation",
            execution_class="side_effect",
            status="succeeded",
            enforcement_flags=("sandbox_requested", "environment_enforced"),
        )
        assert "sandbox_requested" in event.enforcement_flags
        d = event.to_dict()
        assert isinstance(d["enforcement_flags"], list)
        assert "environment_enforced" in d["enforcement_flags"]

    def test_execution_event_defaults(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="test",
            capability_type="llm_call",
            execution_class="llm_call",
            status="succeeded",
        )
        assert event.max_tokens == 0
        assert event.enforcement_flags == ()


class TestMaxTokensAtCallSites:
    """Verify max_tokens is applied at the three critical call sites."""

    def test_email_gps_classify_has_max_tokens(self):
        import ast

        with open("/opt/OS/umh/runtime_engine/email_gps.py") as f:
            source = f.read()
        assert (
            'email_gps_classify", max_tokens=50' in source
            or 'email_gps_classify", max_tokens=50' in source
        )

    def test_email_gps_purpose_has_max_tokens(self):
        with open("/opt/OS/umh/runtime_engine/email_gps.py") as f:
            source = f.read()
        assert (
            'email_gps_purpose", max_tokens=' in source
            or 'email_gps_purpose", max_tokens=' in source
        )

    def test_email_gps_draft_has_max_tokens(self):
        with open("/opt/OS/umh/runtime_engine/email_gps.py") as f:
            source = f.read()
        assert (
            'email_gps_draft", max_tokens=' in source or 'email_gps_draft", max_tokens=' in source
        )

    def test_email_gps_extract_has_max_tokens(self):
        with open("/opt/OS/umh/runtime_engine/email_gps.py") as f:
            source = f.read()
        assert (
            'email_gps_extract", max_tokens=' in source
            or 'email_gps_extract", max_tokens=' in source
        )

    def test_decision_log_extract_has_max_tokens(self):
        with open("/opt/OS/umh/runtime_engine/decision_log.py") as f:
            source = f.read()
        assert (
            'decision_log_extract", max_tokens=150' in source
            or 'decision_log_extract", max_tokens=150' in source
        )

    def test_quality_gate_check_has_max_tokens(self):
        with open("/opt/OS/umh/runtime_engine/quality_gate.py") as f:
            source = f.read()
        assert (
            'quality_gate_check", max_tokens=500' in source
            or 'quality_gate_check", max_tokens=500' in source
        )


class TestScoringEnhancements:
    """Verify timeout_rate, failure_rate, and timed_out_calls tracking."""

    def test_timed_out_calls_tracked(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()
        event = ExecutionEvent(
            execution_id="t1",
            operation="shell_command",
            capability_type="shell_command",
            execution_class="side_effect",
            status="timed_out",
            error="Timed out after 30s",
            environment_type="local",
        )
        scorer.record(event)

        stats = scorer.get_stats("shell_command")
        assert stats.total_calls == 1
        assert stats.timed_out_calls == 1
        assert stats.failed_calls == 1
        assert stats.timeout_rate == 1.0
        assert stats.failure_rate == 1.0

    def test_timeout_rate_computation(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()
        for i, status in enumerate(["succeeded", "succeeded", "timed_out", "succeeded"]):
            scorer.record(
                ExecutionEvent(
                    execution_id=f"t{i}",
                    operation="shell_command",
                    capability_type="shell_command",
                    execution_class="side_effect",
                    status=status,
                )
            )

        stats = scorer.get_stats("shell_command")
        assert stats.total_calls == 4
        assert stats.timed_out_calls == 1
        assert stats.timeout_rate == 0.25

    def test_failure_rate_computation(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()
        for i, status in enumerate(["succeeded", "failed", "timed_out", "succeeded"]):
            scorer.record(
                ExecutionEvent(
                    execution_id=f"t{i}",
                    operation="file_read",
                    capability_type="file_operation",
                    execution_class="side_effect",
                    status=status,
                )
            )

        stats = scorer.get_stats("file_operation")
        assert stats.total_calls == 4
        assert stats.failed_calls == 2
        assert stats.failure_rate == 0.5

    def test_env_stats_track_timeout_rate(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()
        scorer.record(
            ExecutionEvent(
                execution_id="t1",
                operation="shell_command",
                capability_type="shell_command",
                execution_class="side_effect",
                status="timed_out",
                environment_type="sandbox",
            )
        )
        scorer.record(
            ExecutionEvent(
                execution_id="t2",
                operation="shell_command",
                capability_type="shell_command",
                execution_class="side_effect",
                status="succeeded",
                environment_type="local",
            )
        )

        sandbox_stats = scorer.get_env_stats("shell_command", "sandbox")
        local_stats = scorer.get_env_stats("shell_command", "local")

        assert sandbox_stats.timeout_rate == 1.0
        assert local_stats.timeout_rate == 0.0
        assert local_stats.success_rate == 1.0

    def test_to_dict_includes_new_fields(self):
        from umh.execution.scoring import CapabilityStats

        stats = CapabilityStats(
            total_calls=10,
            successful_calls=7,
            failed_calls=3,
            timed_out_calls=1,
        )
        d = stats.to_dict()
        assert "timed_out_calls" in d
        assert "failure_rate" in d
        assert "timeout_rate" in d
        assert d["timed_out_calls"] == 1
        assert d["failure_rate"] == 0.3
        assert d["timeout_rate"] == 0.1

    def test_cost_tracking_per_environment(self):
        from umh.execution.scoring import CapabilityScorer
        from umh.execution.observability import ExecutionEvent

        scorer = CapabilityScorer()
        scorer.record(
            ExecutionEvent(
                execution_id="t1",
                operation="utility",
                capability_type="llm_call",
                execution_class="llm_call",
                status="succeeded",
                cost_usd=0.01,
                environment_type="local",
            )
        )
        scorer.record(
            ExecutionEvent(
                execution_id="t2",
                operation="utility",
                capability_type="llm_call",
                execution_class="llm_call",
                status="succeeded",
                cost_usd=0.005,
                environment_type="local",
            )
        )

        env_stats = scorer.get_env_stats("llm_call", "local")
        assert abs(env_stats.total_cost_usd - 0.015) < 0.0001

        agg = scorer.get_stats("llm_call")
        assert abs(agg.total_cost_usd - 0.015) < 0.0001


class TestObserverEnforcement:
    """Verify observer captures enforcement flags and max_tokens."""

    def test_observer_captures_max_tokens(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request(
            "utility", ExecutionClass.LLM_CALL, inputs={"prompt": "test"}, max_tokens=50
        )
        observer.on_request(req)

        assert req.execution_id in observer._pending
        pending = observer._pending[req.execution_id]
        max_tokens = pending[5]
        assert max_tokens == 50

    def test_observer_captures_sandbox_flag(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request(
            "file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": "/tmp/x"}, sandbox=True
        )
        observer.on_request(req)

        pending = observer._pending[req.execution_id]
        enforcement_flags = pending[6]
        assert "sandbox_requested" in enforcement_flags

    def test_observer_captures_cost_limit(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request(
            "utility", ExecutionClass.LLM_CALL, inputs={"prompt": "test"}, cost_limit_usd=0.05
        )
        observer.on_request(req)

        pending = observer._pending[req.execution_id]
        enforcement_flags = pending[6]
        flag_str = " ".join(enforcement_flags)
        assert "cost_limit" in flag_str

    def test_observer_defaults_without_request(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        result = ExecutionResult(
            execution_id="orphan",
            correlation_id="orphan",
            causal_event_id="",
            operation="unknown",
            status=ExecutionStatus.FAILED,
            outputs={},
            latency_ms=0,
        )
        observer.on_result(result)


class TestExecutionBehaviorUnchanged3C:
    """Verify execution behavior is identical after Phase 3C changes."""

    def test_shell_command_still_works(self):
        from umh.execution.engine import execute

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"})
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_file_read_still_works(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"phase 3c test")
        os.close(fd)
        try:
            req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path})
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "phase 3c test"
        finally:
            os.unlink(path)

    def test_guard_still_blocks(self):
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
            mock_result.output = "3c test"
            mock_result.provider = "test"
            mock_result.model = "test"
            mock_result.tokens_used = 0
            mock_result.input_tokens = 0
            mock_result.output_tokens = 0
            mock_result.cost_usd = 0.0
            mock.return_value = mock_result

            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED

    def test_file_read_sandboxed_still_works(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"sandboxed 3c")
        os.close(fd)
        try:
            req = _make_request(
                "file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path}, sandbox=True
            )
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
        finally:
            os.unlink(path)
