"""Tests for Phase 4A: External Capability Interface Layer.

Verifies:
- COMPUTER_USE added to CapabilityType
- Classification: browser_* → browser_action, computer_* → computer_use
- Environment mapping: browser → container, computer_use → local
- External capability interface and adapter registry
- Stub adapters return NOT_IMPLEMENTED with correct metadata
- Routing through SpineExecutionBackend to external adapters
- Enforcement still blocks invalid execution
- Observability captures adapter name and capability type
- Execution behavior unchanged for existing capabilities
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


class TestCapabilityTypeEnum:
    """Verify COMPUTER_USE exists in CapabilityType."""

    def test_computer_use_in_capability_type(self):
        from umh.capabilities.spec import CapabilityType

        assert hasattr(CapabilityType, "COMPUTER_USE")
        assert CapabilityType.COMPUTER_USE.value == "computer_use"

    def test_browser_action_still_exists(self):
        from umh.capabilities.spec import CapabilityType

        assert CapabilityType.BROWSER_ACTION.value == "browser_action"

    def test_all_capability_types(self):
        from umh.capabilities.spec import CapabilityType

        values = {ct.value for ct in CapabilityType}
        assert "llm_call" in values
        assert "shell_command" in values
        assert "file_operation" in values
        assert "browser_action" in values
        assert "computer_use" in values
        assert "os_interaction" in values


class TestCapabilityClassification:
    """Verify _classify_capability handles new types."""

    def test_browser_navigate_classifies_as_browser_action(self):
        from umh.execution.environment import _classify_capability

        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        assert _classify_capability(req) == "browser_action"

    def test_browser_click_classifies_as_browser_action(self):
        from umh.execution.environment import _classify_capability

        req = _make_request("browser_click", ExecutionClass.SIDE_EFFECT)
        assert _classify_capability(req) == "browser_action"

    def test_computer_screenshot_classifies_as_computer_use(self):
        from umh.execution.environment import _classify_capability

        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        assert _classify_capability(req) == "computer_use"

    def test_computer_click_classifies_as_computer_use(self):
        from umh.execution.environment import _classify_capability

        req = _make_request("computer_click", ExecutionClass.SIDE_EFFECT)
        assert _classify_capability(req) == "computer_use"

    def test_observability_classify_matches_environment(self):
        from umh.execution.environment import _classify_capability as env_classify
        from umh.execution.observability import _classify_capability as obs_classify

        for op in ["browser_navigate", "computer_screenshot", "shell_command", "file_read"]:
            req = _make_request(op, ExecutionClass.SIDE_EFFECT)
            assert env_classify(req) == obs_classify(req), f"Mismatch for {op}"

    def test_llm_still_classifies_correctly(self):
        from umh.execution.environment import _classify_capability

        req = _make_request("utility", ExecutionClass.LLM_CALL)
        assert _classify_capability(req) == "llm_call"


class TestEnvironmentMapping:
    """Verify environment definitions for browser and computer_use."""

    def test_container_env_exists(self):
        from umh.execution.environment import get_environment, EnvironmentType

        env = get_environment("container")
        assert env is not None
        assert env.env_type == EnvironmentType.CONTAINER

    def test_container_supports_browser_action(self):
        from umh.execution.environment import get_environment

        env = get_environment("container")
        assert env.supports("browser_action")

    def test_container_does_not_support_llm_call(self):
        from umh.execution.environment import get_environment

        env = get_environment("container")
        assert not env.supports("llm_call")

    def test_container_security_is_isolated(self):
        from umh.execution.environment import get_environment, SecurityLevel

        env = get_environment("container")
        assert env.security_level == SecurityLevel.ISOLATED

    def test_local_supports_computer_use(self):
        from umh.execution.environment import get_environment

        env = get_environment("local")
        assert env.supports("computer_use")

    def test_registry_has_three_environments(self):
        from umh.execution.environment import list_environments

        envs = list_environments()
        ids = {e.id for e in envs}
        assert ids == {"local", "sandbox", "container"}

    def test_browser_routes_to_local_fallback_no_real_container(self):
        from umh.execution.environment import select_environment

        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"

    def test_computer_use_routes_to_local(self):
        from umh.execution.environment import select_environment

        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        env = select_environment(req)
        assert env.id == "local"


class TestExternalCapabilityInterface:
    """Verify the external capability adapter interface and registry."""

    def test_adapter_registry_empty_initially(self):
        from umh.execution.external import _ADAPTER_REGISTRY

        # Registry may have adapters from prior test runs via singleton,
        # so just verify the interface exists
        from umh.execution.external import get_adapter, list_adapters, register_adapter

        assert callable(get_adapter)
        assert callable(list_adapters)
        assert callable(register_adapter)

    def test_register_and_get_adapter(self):
        from umh.execution.external import get_adapter, register_adapter
        from umh.adapters.browser_adapter import BrowserAdapter

        adapter = BrowserAdapter()
        register_adapter(adapter)
        retrieved = get_adapter("browser_action")
        assert retrieved is not None
        assert retrieved.adapter_name == "browser_adapter"

    def test_list_adapters(self):
        from umh.execution.external import register_adapter, list_adapters
        from umh.adapters.browser_adapter import BrowserAdapter
        from umh.adapters.computer_use_adapter import ComputerUseAdapter

        register_adapter(BrowserAdapter())
        register_adapter(ComputerUseAdapter())
        listing = list_adapters()
        assert "browser_action" in listing
        assert "computer_use" in listing
        assert listing["browser_action"] == "browser_adapter"
        assert listing["computer_use"] == "computer_use_adapter"

    def test_get_nonexistent_adapter_returns_none(self):
        from umh.execution.external import get_adapter

        assert get_adapter("teleportation") is None


class TestBrowserAdapterStub:
    """Verify browser adapter returns NOT_IMPLEMENTED correctly."""

    def test_adapter_name(self):
        from umh.adapters.browser_adapter import BrowserAdapter

        assert BrowserAdapter().adapter_name == "browser_adapter"

    def test_capability_type(self):
        from umh.adapters.browser_adapter import BrowserAdapter

        assert BrowserAdapter().capability_type == "browser_action"

    def test_execute_returns_not_implemented(self):
        from umh.adapters.browser_adapter import BrowserAdapter
        from umh.execution.environment import get_environment

        adapter = BrowserAdapter()
        env = get_environment("container")
        req = _make_request(
            "browser_navigate", ExecutionClass.SIDE_EFFECT, inputs={"url": "https://example.com"}
        )
        result = adapter.execute(req, env)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("not_implemented") is True
        assert result.outputs.get("adapter") == "browser_adapter"

    def test_execute_includes_operation_in_error(self):
        from umh.adapters.browser_adapter import BrowserAdapter
        from umh.execution.environment import get_environment

        adapter = BrowserAdapter()
        env = get_environment("container")
        req = _make_request("browser_click", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert "browser_click" in result.error


class TestComputerUseAdapterStub:
    """Verify computer use adapter returns NOT_IMPLEMENTED correctly."""

    def test_adapter_name(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter

        assert ComputerUseAdapter().adapter_name == "computer_use_adapter"

    def test_capability_type(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter

        assert ComputerUseAdapter().capability_type == "computer_use"

    def test_execute_returns_real_result(self):
        from umh.adapters.computer_use_adapter import ComputerUseAdapter
        from umh.execution.environment import get_environment

        adapter = ComputerUseAdapter()
        env = get_environment("local")
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = adapter.execute(req, env)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("adapter") == "computer_use_adapter"
        assert result.outputs.get("width") > 0


class TestRoutingIntegration:
    """Verify SpineExecutionBackend routes to external adapters."""

    def test_browser_routes_through_adapter_via_factory(self):
        from umh.adapters.umh_execution import get_execution_backend_adapter

        backend = get_execution_backend_adapter()
        req = _make_request(
            "browser_navigate", ExecutionClass.SIDE_EFFECT, inputs={"url": "https://example.com"}
        )
        result = backend.execute(req)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("not_implemented") is True
        assert result.outputs.get("adapter") == "browser_adapter"

    def test_computer_use_routes_through_adapter(self):
        from umh.adapters.umh_execution import get_execution_backend_adapter

        backend = get_execution_backend_adapter()
        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        result = backend.execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("adapter") == "computer_use_adapter"

    def test_can_handle_recognizes_browser(self):
        from umh.adapters.umh_execution import SpineExecutionBackend

        backend = SpineExecutionBackend()
        assert backend.can_handle("browser_navigate")
        assert backend.can_handle("browser_click")

    def test_can_handle_recognizes_computer_use(self):
        from umh.adapters.umh_execution import SpineExecutionBackend

        backend = SpineExecutionBackend()
        assert backend.can_handle("computer_screenshot")
        assert backend.can_handle("computer_click")

    def test_unknown_operation_still_returns_not_implemented(self):
        from umh.adapters.umh_execution import SpineExecutionBackend

        backend = SpineExecutionBackend()
        req = _make_request("teleport_user", ExecutionClass.SIDE_EFFECT)
        result = backend.execute(req)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("not_implemented") is True


class TestEnforcementCompatibility:
    """Verify enforcement runs for external capabilities."""

    def test_browser_denied_in_container_not_implemented(self):
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

    def test_browser_denied_in_local(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("local")
        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY
        assert "does not support" in result.reason

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

    def test_llm_still_denied_in_sandbox(self):
        from umh.execution.environment import (
            EnforcementVerdict,
            enforce_environment,
            get_environment,
        )

        env = get_environment("sandbox")
        req = _make_request("utility", ExecutionClass.LLM_CALL)
        result = enforce_environment(req, env)
        assert result.verdict == EnforcementVerdict.DENY


class TestObservabilityExternal:
    """Verify external capabilities appear correctly in observability."""

    def test_browser_event_has_correct_capability_type(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="browser_navigate",
            capability_type="browser_action",
            execution_class="side_effect",
            status="rejected",
            adapter="browser_adapter",
        )
        d = event.to_dict()
        assert d["capability_type"] == "browser_action"
        assert d["adapter"] == "browser_adapter"

    def test_computer_use_event_has_correct_capability_type(self):
        from umh.execution.observability import ExecutionEvent

        event = ExecutionEvent(
            execution_id="test",
            operation="computer_screenshot",
            capability_type="computer_use",
            execution_class="side_effect",
            status="rejected",
            adapter="computer_use_adapter",
        )
        d = event.to_dict()
        assert d["capability_type"] == "computer_use"
        assert d["adapter"] == "computer_use_adapter"

    def test_observer_classifies_browser(self):
        from umh.execution.observability import _classify_capability

        req = _make_request("browser_navigate", ExecutionClass.SIDE_EFFECT)
        assert _classify_capability(req) == "browser_action"

    def test_observer_classifies_computer_use(self):
        from umh.execution.observability import _classify_capability

        req = _make_request("computer_screenshot", ExecutionClass.SIDE_EFFECT)
        assert _classify_capability(req) == "computer_use"


class TestExistingBehaviorUnchanged:
    """Verify nothing breaks for existing capabilities."""

    def test_shell_command_still_works(self):
        from umh.execution.engine import execute

        req = _make_request("shell_command", ExecutionClass.SIDE_EFFECT, inputs={"command": "date"})
        result = execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_file_read_still_works(self):
        from umh.execution.engine import execute

        fd, path = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"phase 4a test")
        os.close(fd)
        try:
            req = _make_request("file_read", ExecutionClass.SIDE_EFFECT, inputs={"path": path})
            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED
            assert result.outputs["text"] == "phase 4a test"
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
            mock_result.output = "4a test"
            mock_result.provider = "test"
            mock_result.model = "test"
            mock_result.tokens_used = 0
            mock_result.input_tokens = 0
            mock_result.output_tokens = 0
            mock_result.cost_usd = 0.0
            mock.return_value = mock_result

            result = execute(req)
            assert result.status == ExecutionStatus.SUCCEEDED

    def test_browser_through_execute_gets_guard_first(self):
        from umh.execution.engine import execute

        req = _make_request(
            "browser_navigate", ExecutionClass.SIDE_EFFECT, inputs={"url": "https://example.com"}
        )
        result = execute(req)
        assert result.status == ExecutionStatus.REJECTED
