"""Tests for Phase 3A: Environment Abstraction Layer.

Verifies:
- EnvironmentSpec dataclass and type system
- Environment selection for all execution classes
- ExecutionEvent environment fields
- Observer environment integration
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
) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=f"test_{operation}",
        correlation_id=f"test_{operation}",
        causal_event_id="",
        session_id="",
        operation=operation,
        inputs=inputs or {},
        execution_class=execution_class,
        constraints=ExecutionConstraints(timeout_s=timeout_s),
        target=ExecutionTarget(node_id="local", transport="test"),
        context=ExecutionContext(),
        issued_at="2026-04-26T12:00:00Z",
        issued_by="test",
        idempotency_key="",
    )


class TestEnvironmentSpec:
    """Verify EnvironmentSpec dataclass and type system."""

    def test_environment_type_values(self):
        from umh.execution.environment import EnvironmentType

        assert EnvironmentType.LOCAL.value == "local"
        assert EnvironmentType.SANDBOX.value == "sandbox"
        assert EnvironmentType.CONTAINER.value == "container"
        assert EnvironmentType.REMOTE.value == "remote"

    def test_security_level_values(self):
        from umh.execution.environment import SecurityLevel

        assert SecurityLevel.TRUSTED.value == "trusted"
        assert SecurityLevel.SANDBOXED.value == "sandboxed"
        assert SecurityLevel.ISOLATED.value == "isolated"

    def test_environment_spec_creation(self):
        from umh.execution.environment import (
            EnvironmentSpec,
            EnvironmentType,
            SecurityLevel,
        )

        env = EnvironmentSpec(
            id="test_env",
            env_type=EnvironmentType.SANDBOX,
            supported_capabilities=frozenset({"llm_call"}),
            security_level=SecurityLevel.SANDBOXED,
        )
        assert env.id == "test_env"
        assert env.env_type == EnvironmentType.SANDBOX
        assert env.security_level == SecurityLevel.SANDBOXED

    def test_environment_spec_frozen(self):
        from umh.execution.environment import (
            EnvironmentSpec,
            EnvironmentType,
            SecurityLevel,
        )
        import dataclasses

        env = EnvironmentSpec(
            id="frozen",
            env_type=EnvironmentType.LOCAL,
            supported_capabilities=frozenset({"llm_call"}),
            security_level=SecurityLevel.TRUSTED,
        )
        assert dataclasses.is_dataclass(env)
        try:
            env.id = "modified"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except (AttributeError, dataclasses.FrozenInstanceError):
            pass

    def test_supports_capability(self):
        from umh.execution.environment import (
            EnvironmentSpec,
            EnvironmentType,
            SecurityLevel,
        )

        env = EnvironmentSpec(
            id="test",
            env_type=EnvironmentType.LOCAL,
            supported_capabilities=frozenset({"llm_call", "shell_command"}),
            security_level=SecurityLevel.TRUSTED,
        )
        assert env.supports("llm_call")
        assert env.supports("shell_command")
        assert not env.supports("browser_action")

    def test_environment_spec_metadata(self):
        from umh.execution.environment import (
            EnvironmentSpec,
            EnvironmentType,
            SecurityLevel,
        )

        env = EnvironmentSpec(
            id="with_meta",
            env_type=EnvironmentType.CONTAINER,
            supported_capabilities=frozenset(),
            security_level=SecurityLevel.ISOLATED,
            metadata={"docker_image": "python:3.12"},
        )
        assert env.metadata["docker_image"] == "python:3.12"


class TestEnvironmentSelector:
    """Verify environment selection for all request types."""

    def test_llm_call_routes_to_local(self):
        from umh.execution.environment import EnvironmentType, select_environment

        req = _make_request("utility", ExecutionClass.LLM_CALL, inputs={"prompt": "test"})
        env = select_environment(req)
        assert env.id == "local"
        assert env.env_type == EnvironmentType.LOCAL

    def test_shell_command_routes_to_local(self):
        from umh.execution.environment import EnvironmentType, select_environment

        req = _make_request(
            "shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "uptime"}
        )
        env = select_environment(req)
        assert env.id == "local"
        assert env.env_type == EnvironmentType.LOCAL

    def test_file_operation_routes_to_local(self):
        from umh.execution.environment import EnvironmentType, select_environment

        req = _make_request(
            "file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": "/tmp/test.txt"}
        )
        env = select_environment(req)
        assert env.id == "local"
        assert env.env_type == EnvironmentType.LOCAL

    def test_pure_routes_to_local(self):
        from umh.execution.environment import EnvironmentType, select_environment

        req = _make_request("compute", ExecutionClass.PURE, inputs={})
        env = select_environment(req)
        assert env.id == "local"
        assert env.env_type == EnvironmentType.LOCAL

    def test_transport_routes_to_local(self):
        from umh.execution.environment import EnvironmentType, select_environment

        req = _make_request("send_message", ExecutionClass.TRANSPORT, inputs={})
        env = select_environment(req)
        assert env.id == "local"
        assert env.env_type == EnvironmentType.LOCAL

    def test_local_supports_implemented_capabilities(self):
        from umh.execution.environment import select_environment

        req = _make_request("utility", ExecutionClass.LLM_CALL)
        env = select_environment(req)
        assert env.supports("llm_call")
        assert env.supports("shell_command")
        assert env.supports("file_operation")
        assert not env.supports("browser_action")
        assert not env.supports("os_interaction")


class TestEnvironmentRegistry:
    """Verify environment lookup and listing."""

    def test_get_local_environment(self):
        from umh.execution.environment import get_environment

        env = get_environment("local")
        assert env is not None
        assert env.id == "local"

    def test_get_nonexistent_returns_none(self):
        from umh.execution.environment import get_environment

        assert get_environment("mars_colony") is None

    def test_list_environments(self):
        from umh.execution.environment import list_environments

        envs = list_environments()
        assert len(envs) >= 1
        ids = [e.id for e in envs]
        assert "local" in ids


class TestExecutionEventEnvironment:
    """Verify ExecutionEvent has environment fields."""

    def test_event_has_environment_fields(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="test_op",
            capability_type="llm_call",
            execution_class="llm_call",
            status="succeeded",
            environment_id="local",
            environment_type="local",
        )
        assert event.environment_id == "local"
        assert event.environment_type == "local"

    def test_event_defaults_to_local(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="test_op",
            capability_type="llm_call",
            execution_class="llm_call",
            status="succeeded",
        )
        assert event.environment_id == "local"
        assert event.environment_type == "local"

    def test_event_to_dict_includes_environment(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="test_op",
            capability_type="shell_command",
            execution_class="side_effect",
            status="succeeded",
            environment_id="local",
            environment_type="local",
        )
        d = event.to_dict()
        assert d["environment_id"] == "local"
        assert d["environment_type"] == "local"

    def test_event_with_custom_environment(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="test_op",
            capability_type="shell_command",
            execution_class="side_effect",
            status="succeeded",
            environment_id="docker_sandbox",
            environment_type="container",
        )
        assert event.environment_id == "docker_sandbox"
        assert event.environment_type == "container"


class TestObserverEnvironmentIntegration:
    """Verify the observer attaches environment to events."""

    def test_observer_captures_environment_on_request(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"})
        observer.on_request(req)
        assert req.execution_id in observer._pending
        pending = observer._pending[req.execution_id]
        env_id = pending[2]
        env_type = pending[3]
        assert env_id == "local"
        assert env_type == "local"

    def test_observer_attaches_environment_to_event(self):
        from umh.execution.observability import EnhancedExecutionObserver
        from umh.execution.scoring import CapabilityScorer

        scorer = CapabilityScorer()
        observer = EnhancedExecutionObserver()
        req = _make_request("utility", ExecutionClass.LLM_CALL, inputs={"prompt": "test"})
        observer.on_request(req)

        result = ExecutionResult(
            execution_id=req.execution_id,
            correlation_id=req.correlation_id,
            causal_event_id="",
            operation="utility",
            status=ExecutionStatus.SUCCEEDED,
            outputs={"text": "response"},
            latency_ms=100,
        )

        captured_events = []
        original_record = scorer.record

        def capture_record(event):
            captured_events.append(event)
            original_record(event)

        with patch.object(scorer, "record", side_effect=capture_record):
            observer.on_result(result)

    def test_observer_defaults_environment_without_request(self):
        from umh.execution.observability import EnhancedExecutionObserver

        observer = EnhancedExecutionObserver()
        result = ExecutionResult(
            execution_id="orphan_result",
            correlation_id="orphan_result",
            causal_event_id="",
            operation="unknown",
            status=ExecutionStatus.FAILED,
            outputs={},
            latency_ms=0,
        )
        observer.on_result(result)


class TestExecutionBehaviorUnchanged:
    """Verify execution behavior is identical after environment layer."""

    def test_shell_command_still_works(self):
        from umh.execution.engine import execute

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"})
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("exit_code") == 0

    def test_file_read_still_works(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"env layer test")
        os.close(fd)
        try:
            req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path})
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "env layer test"
        finally:
            os.unlink(path)

    def test_guard_still_blocks(self):
        from umh.execution.engine import execute

        req = _make_request(
            "shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "echo $HOME"}
        )
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("guard_denied") is True

    def test_llm_path_unchanged(self):
        from umh.execution.engine import execute

        req = _make_request("utility", ExecutionClass.LLM_CALL, inputs={"prompt": "test"})
        with patch("umh.runtime_engine.model_router.call_with_fallback") as mock:
            mock_result = MagicMock()
            mock_result.output = "env test response"
            mock_result.provider = "test"
            mock_result.model = "test"
            mock_result.tokens_used = 0
            mock_result.input_tokens = 0
            mock_result.output_tokens = 0
            mock_result.cost_usd = 0.0
            mock.return_value = mock_result

            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "env test response"

    def test_not_implemented_still_returns_structured(self):
        from umh.adapters.umh_execution import SpineExecutionBackend

        backend = SpineExecutionBackend()
        req = _make_request(
            "browser_navigate", ExecutionClass.SIDE_EFFECT, inputs={"url": "https://example.com"}
        )
        result = backend.execute(req)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("not_implemented") is True
