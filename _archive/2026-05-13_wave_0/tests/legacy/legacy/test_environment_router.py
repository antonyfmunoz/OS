"""Tests for runtime.environment_router + runtime.execution_adapters."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime_engine.environment_router import (
    DOMAIN_ENVIRONMENT_HINTS,
    TARGET_OVERRIDES,
    TYPE_ROUTES,
    ExecutionEnvironment,
    EnvironmentRoute,
    NO_ROUTE,
    resolve_environment,
)
from umh.runtime_engine.execution_adapters import (
    DEFAULT_ADAPTERS,
    AdapterResult,
    BaseExecutionAdapter,
    HumanAdapter,
    LocalAdapter,
    MockAPIAdapter,
    NoOpAdapter,
    ToolAdapter,
    execute_with_environment,
    get_adapter,
    NO_ADAPTER_RESULT,
)
from umh.runtime_engine.action_schema import ExecutableAction


# ─── Helpers ───────────────────────────────────────────────────────


def _make_action(
    action_id: str = "a1",
    action_type: str = "TASK",
    action_name: str = "test_action",
    target: str | None = None,
    domain: str = "business",
) -> ExecutableAction:
    return ExecutableAction(
        action_id=action_id,
        action_type=action_type,
        action_name=action_name,
        target=target,
        intent=f"task: {action_name}",
        payload={},
        constraints={},
        priority=0.5,
        confidence=0.8,
        domain=domain,
        trace_id=None,
        explanation=None,
    )


# ═══════════════════════════════════════════════════════════════════
# Environment resolution — type-based routing
# ═══════════════════════════════════════════════════════════════════


class TestTypeRouting:
    def test_task_routes_to_local(self):
        action = _make_action(action_type="TASK")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.LOCAL
        assert route.adapter_name == "local"

    def test_api_call_routes_to_api(self):
        action = _make_action(action_type="API_CALL")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.API
        assert route.adapter_name == "mock_api"

    def test_message_routes_to_human(self):
        action = _make_action(action_type="MESSAGE")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.HUMAN
        assert route.adapter_name == "human"

    def test_human_instruction_routes_to_human(self):
        action = _make_action(action_type="HUMAN_INSTRUCTION")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.HUMAN

    def test_no_op_routes_to_local(self):
        action = _make_action(action_type="NO_OP")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.LOCAL
        assert route.adapter_name == "no_op"

    def test_unknown_type_fallback(self):
        action = _make_action(action_type="WEIRD_TYPE")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.UNKNOWN
        assert route.adapter_name == "no_op"
        assert route.confidence == 0.0

    def test_empty_type_fallback(self):
        action = _make_action(action_type="")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.UNKNOWN


# ═══════════════════════════════════════════════════════════════════
# Target overrides
# ═══════════════════════════════════════════════════════════════════


class TestTargetOverrides:
    def test_self_target_routes_local(self):
        action = _make_action(action_type="MESSAGE", target="self")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.LOCAL
        assert "target_override" in route.reason

    def test_human_target_routes_human(self):
        action = _make_action(action_type="TASK", target="human")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.HUMAN
        assert "target_override" in route.reason

    def test_target_override_takes_priority(self):
        action = _make_action(action_type="API_CALL", target="self")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.LOCAL
        assert route.confidence == 0.9


# ═══════════════════════════════════════════════════════════════════
# Domain hints
# ═══════════════════════════════════════════════════════════════════


class TestDomainHints:
    def test_automation_domain_routes_to_tool(self):
        action = _make_action(domain="automation", action_type="TASK")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.TOOL
        assert "domain_hint" in route.reason

    def test_integration_domain_routes_to_api(self):
        action = _make_action(domain="integration", action_type="TASK")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.API

    def test_domain_hint_priority_over_type(self):
        action = _make_action(domain="automation", action_type="TASK")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.TOOL

    def test_target_override_beats_domain_hint(self):
        action = _make_action(domain="automation", target="self")
        route = resolve_environment(action)
        assert route.environment == ExecutionEnvironment.LOCAL


# ═══════════════════════════════════════════════════════════════════
# Route determinism
# ═══════════════════════════════════════════════════════════════════


class TestRouteDeterminism:
    def test_same_action_same_route(self):
        action = _make_action(action_type="API_CALL")
        r1 = resolve_environment(action)
        r2 = resolve_environment(action)
        assert r1.environment == r2.environment
        assert r1.adapter_name == r2.adapter_name
        assert r1.reason == r2.reason

    def test_route_to_dict(self):
        route = EnvironmentRoute(
            environment=ExecutionEnvironment.LOCAL,
            adapter_name="local",
            confidence=0.8,
            reason="type_route:TASK",
        )
        d = route.to_dict()
        assert d["environment"] == "LOCAL"
        assert d["adapter_name"] == "local"

    def test_no_route_sentinel(self):
        assert NO_ROUTE.environment == ExecutionEnvironment.UNKNOWN
        assert NO_ROUTE.confidence == 0.0


# ═══════════════════════════════════════════════════════════════════
# Adapter selection
# ═══════════════════════════════════════════════════════════════════


class TestAdapterSelection:
    def test_get_local_adapter(self):
        adapter = get_adapter("local")
        assert adapter.name == "local"
        assert isinstance(adapter, LocalAdapter)

    def test_get_human_adapter(self):
        adapter = get_adapter("human")
        assert adapter.name == "human"
        assert isinstance(adapter, HumanAdapter)

    def test_get_mock_api_adapter(self):
        adapter = get_adapter("mock_api")
        assert adapter.name == "mock_api"
        assert isinstance(adapter, MockAPIAdapter)

    def test_get_tool_adapter(self):
        adapter = get_adapter("tool")
        assert adapter.name == "tool"
        assert isinstance(adapter, ToolAdapter)

    def test_get_no_op_adapter(self):
        adapter = get_adapter("no_op")
        assert adapter.name == "no_op"
        assert isinstance(adapter, NoOpAdapter)

    def test_unknown_name_falls_back_to_no_op(self):
        adapter = get_adapter("nonexistent_adapter")
        assert isinstance(adapter, NoOpAdapter)

    def test_custom_registry(self):
        custom = {"my_adapter": LocalAdapter()}
        adapter = get_adapter("my_adapter", adapters=custom)
        assert isinstance(adapter, LocalAdapter)


# ═══════════════════════════════════════════════════════════════════
# Adapter execution
# ═══════════════════════════════════════════════════════════════════


class TestAdapterExecution:
    def test_local_adapter_succeeds(self):
        action = _make_action(action_type="TASK")
        adapter = LocalAdapter()
        result = adapter.execute(action)
        assert result.success is True
        assert result.output["executed_locally"] is True
        assert result.environment == ExecutionEnvironment.LOCAL

    def test_human_adapter_never_auto_executes(self):
        action = _make_action(action_type="MESSAGE", target="team")
        adapter = HumanAdapter()
        result = adapter.execute(action)
        assert result.success is True
        assert result.output["auto_executed"] is False
        assert result.output["requires_human"] is True

    def test_mock_api_adapter_simulates(self):
        action = _make_action(action_type="API_CALL", target="crm")
        adapter = MockAPIAdapter()
        result = adapter.execute(action)
        assert result.success is True
        assert result.output["simulated"] is True
        assert result.environment == ExecutionEnvironment.API

    def test_tool_adapter_simulates(self):
        action = _make_action(domain="automation")
        adapter = ToolAdapter()
        result = adapter.execute(action)
        assert result.success is True
        assert result.output["tool_executed"] is True
        assert result.output["simulated"] is True

    def test_no_op_adapter_always_succeeds(self):
        action = _make_action(action_type="WEIRD")
        adapter = NoOpAdapter()
        result = adapter.execute(action)
        assert result.success is True
        assert result.output["no_op"] is True

    def test_adapter_result_to_dict(self):
        result = AdapterResult(
            success=True,
            output={"key": "value"},
            error=None,
            latency_ms=5,
            environment=ExecutionEnvironment.LOCAL,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["environment"] == "LOCAL"

    def test_no_adapter_result_sentinel(self):
        assert NO_ADAPTER_RESULT.success is False
        assert NO_ADAPTER_RESULT.error == "no_adapter"


# ═══════════════════════════════════════════════════════════════════
# Can-handle checks
# ═══════════════════════════════════════════════════════════════════


class TestCanHandle:
    def test_local_handles_task(self):
        action = _make_action(action_type="TASK")
        assert LocalAdapter().can_handle(action) is True

    def test_local_handles_no_op(self):
        action = _make_action(action_type="NO_OP")
        assert LocalAdapter().can_handle(action) is True

    def test_local_rejects_api_call(self):
        action = _make_action(action_type="API_CALL")
        assert LocalAdapter().can_handle(action) is False

    def test_human_handles_message(self):
        action = _make_action(action_type="MESSAGE")
        assert HumanAdapter().can_handle(action) is True

    def test_human_handles_human_instruction(self):
        action = _make_action(action_type="HUMAN_INSTRUCTION")
        assert HumanAdapter().can_handle(action) is True

    def test_mock_api_handles_api_call(self):
        action = _make_action(action_type="API_CALL")
        assert MockAPIAdapter().can_handle(action) is True

    def test_tool_handles_automation_domain(self):
        action = _make_action(domain="automation")
        assert ToolAdapter().can_handle(action) is True

    def test_no_op_handles_anything(self):
        action = _make_action(action_type="ANYTHING")
        assert NoOpAdapter().can_handle(action) is True

    def test_base_handles_nothing(self):
        action = _make_action()
        assert BaseExecutionAdapter().can_handle(action) is False


# ═══════════════════════════════════════════════════════════════════
# Unified execute_with_environment
# ═══════════════════════════════════════════════════════════════════


class TestExecuteWithEnvironment:
    def test_task_end_to_end(self):
        action = _make_action(action_type="TASK")
        route, result = execute_with_environment(action)
        assert route.environment == ExecutionEnvironment.LOCAL
        assert result.success is True

    def test_api_call_end_to_end(self):
        action = _make_action(action_type="API_CALL")
        route, result = execute_with_environment(action)
        assert route.environment == ExecutionEnvironment.API
        assert result.output["simulated"] is True

    def test_human_end_to_end(self):
        action = _make_action(action_type="MESSAGE")
        route, result = execute_with_environment(action)
        assert route.environment == ExecutionEnvironment.HUMAN
        assert result.output["requires_human"] is True

    def test_unknown_type_falls_back_safely(self):
        action = _make_action(action_type="BIZARRE")
        route, result = execute_with_environment(action)
        assert route.environment == ExecutionEnvironment.UNKNOWN
        assert result.success is True
        assert result.output["no_op"] is True

    def test_adapter_exception_handled(self):
        class FailAdapter(BaseExecutionAdapter):
            name = "fail"

            def execute(self, action: object) -> AdapterResult:
                raise RuntimeError("boom")

        route, result = execute_with_environment(
            _make_action(action_type="TASK"),
            adapters={"local": FailAdapter(), "no_op": NoOpAdapter()},
        )
        assert result.success is False
        assert "boom" in result.error

    def test_custom_adapters_used(self):
        class CustomLocal(BaseExecutionAdapter):
            name = "custom_local"

            def execute(self, action: object) -> AdapterResult:
                return AdapterResult(
                    success=True,
                    output={"custom": True},
                    error=None,
                    latency_ms=0,
                    environment=ExecutionEnvironment.LOCAL,
                )

        action = _make_action(action_type="TASK")
        route, result = execute_with_environment(
            action, adapters={"local": CustomLocal(), "no_op": NoOpAdapter()}
        )
        assert result.output["custom"] is True


# ═══════════════════════════════════════════════════════════════════
# Safety guarantees
# ═══════════════════════════════════════════════════════════════════


class TestSafety:
    def test_api_never_real(self):
        action = _make_action(action_type="API_CALL")
        _, result = execute_with_environment(action)
        assert result.output["simulated"] is True

    def test_human_never_auto_executed(self):
        action = _make_action(action_type="MESSAGE")
        _, result = execute_with_environment(action)
        assert result.output["auto_executed"] is False

    def test_unknown_route_no_op(self):
        action = _make_action(action_type="UNDEFINED")
        route, _ = execute_with_environment(action)
        assert route.adapter_name == "no_op"


# ═══════════════════════════════════════════════════════════════════
# DecisionTrace integration
# ═══════════════════════════════════════════════════════════════════


class TestDecisionTraceIntegration:
    def test_new_fields_default_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        assert trace.environment is None
        assert trace.adapter_used is None
        assert trace.adapter_result_status is None
        assert trace.adapter_latency is None

    def test_new_fields_set(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            environment="LOCAL",
            adapter_used="local",
            adapter_result_status=True,
            adapter_latency=5,
        )
        assert trace.environment == "LOCAL"
        assert trace.adapter_used == "local"
        assert trace.adapter_result_status is True
        assert trace.adapter_latency == 5

    def test_to_dict_includes_when_set(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            environment="API",
            adapter_used="mock_api",
        )
        d = trace.to_dict()
        assert d["environment"] == "API"
        assert d["adapter_used"] == "mock_api"

    def test_to_dict_omits_when_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        d = trace.to_dict()
        assert "environment" not in d
        assert "adapter_used" not in d


# ═══════════════════════════════════════════════════════════════════
# SessionInterface integration
# ═══════════════════════════════════════════════════════════════════


class TestSessionInterfaceIntegration:
    def test_accessors_default_none(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._last_environment_route = None
        iface._last_adapter_result = None
        assert iface.get_last_environment_route() is None
        assert iface.get_last_adapter_result() is None

    def test_reset_clears_environment_state(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._decisions = []
        iface._intent = None
        iface._last_executable_action = None
        iface._last_execution_result = None
        iface._last_execution_feedback = None
        iface._last_feedback_observation = None
        iface._last_credit_result = None
        iface._last_strategy_bias = None
        iface._last_system_result = None
        iface._last_environment_route = "route"
        iface._last_adapter_result = "result"
        iface._runtime = None
        iface._session_id = "test"
        iface.reset()
        assert iface._last_environment_route is None
        assert iface._last_adapter_result is None


# ═══════════════════════════════════════════════════════════════════
# System graph integration
# ═══════════════════════════════════════════════════════════════════


class TestSystemGraphIntegration:
    def test_graph_nodes_execute_through_environment(self):
        from umh.runtime_engine.system_graph import build_system_graph, execute_system_graph

        a1 = _make_action("a1", action_type="TASK", domain="x")
        a2 = _make_action("a2", action_type="API_CALL", domain="y")

        graph = build_system_graph([a1, a2])

        class EnvRouter:
            def route(self, request):
                action = request.action
                _, result = execute_with_environment(action)
                from umh.runtime_engine.execution_router import ExecutionResult

                return ExecutionResult(
                    action_id=getattr(action, "action_id", ""),
                    action_name=getattr(action, "action_name", ""),
                    handler_name=result.environment.value,
                    status="success" if result.success else "failed",
                    output=result.output,
                    error=result.error,
                )

        result = execute_system_graph(graph, EnvRouter())
        assert result.status == "completed"
        assert result.completed_nodes == 2


# ═══════════════════════════════════════════════════════════════════
# No regression
# ═══════════════════════════════════════════════════════════════════


class TestNoRegression:
    def test_decision_trace_build_still_works(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        assert trace.turn_id == 1

    def test_execution_router_still_works(self):
        from umh.runtime_engine.execution_router import ExecutionRequest, ExecutionRouter

        action = _make_action("a1")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status in ("success", "unhandled")

    def test_system_graph_still_works(self):
        from umh.runtime_engine.system_graph import build_system_graph

        graph = build_system_graph([_make_action("a1")])
        assert len(graph.nodes) == 1

    def test_action_schema_still_works(self):
        from umh.runtime_engine.action_schema import classify_action_type, ActionType

        assert classify_action_type("send email") == ActionType.MESSAGE
