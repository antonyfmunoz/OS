"""Tests for ExecutionRouter — routing, handlers, safety, integration."""

import sys
import types

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.execution_router import (
    BaseHandler,
    ExecutionRequest,
    ExecutionResult,
    ExecutionRouter,
    HandlerResolution,
    HumanInstructionHandler,
    LogHandler,
    NoOpHandler,
    DEFAULT_ACTION_HANDLERS,
    DEFAULT_TYPE_FALLBACK,
    resolve_handler,
)
from umh.runtime_engine.action_schema import (
    ActionType,
    ExecutableAction,
    to_executable_action,
)
from umh.runtime_engine.domain_adapter import (
    ActionPlan,
    ActionStep,
    DomainType,
    adapt_output,
)


# ─── Helpers ─────────────────────────────────────────────────────


def _make_action(
    action_id="abc123",
    action_type="TASK",
    action_name="follow_up",
    target="crm",
    intent="task: follow up targeting crm in business domain",
    payload=None,
    constraints=None,
    priority=0.8,
    confidence=0.85,
    domain="business",
    trace_id=None,
    explanation="test action",
):
    return ExecutableAction(
        action_id=action_id,
        action_type=action_type,
        action_name=action_name,
        target=target,
        intent=intent,
        payload=payload or {},
        constraints=constraints or {},
        priority=priority,
        confidence=confidence,
        domain=domain,
        trace_id=trace_id,
        explanation=explanation,
    )


class ExplodingHandler(BaseHandler):
    """Handler that always raises. For testing failure path."""

    name = "exploding"

    def execute(self, action):
        raise RuntimeError("handler exploded")


# ─── Test: Exact-match routing ───────────────────────────────────


class TestExactMatchRouting:
    def test_no_op_exact_match(self):
        action = _make_action(action_name="no_op", action_type="NO_OP")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.handler_name == "no_op"
        assert result.output == {"message": "no operation"}

    def test_log_exact_match(self):
        action = _make_action(action_name="log")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.handler_name == "log"
        assert result.output["logged_action"] == "log"
        assert result.output["domain"] == "business"

    def test_human_instruction_exact_match(self):
        action = _make_action(
            action_name="human_instruction", action_type="HUMAN_INSTRUCTION"
        )
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.handler_name == "human_instruction"
        assert "instruction" in result.output

    def test_action_id_preserved(self):
        action = _make_action(action_id="test_id_123")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.action_id == "test_id_123"


# ─── Test: Type fallback routing ─────────────────────────────────


class TestTypeFallbackRouting:
    def test_task_falls_back_to_log(self):
        action = _make_action(action_name="increase_exploration", action_type="TASK")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.handler_name == "log"

    def test_message_falls_back_to_human_instruction(self):
        action = _make_action(action_name="send_email", action_type="MESSAGE")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.handler_name == "human_instruction"

    def test_api_call_falls_back_to_log(self):
        action = _make_action(action_name="update_crm", action_type="API_CALL")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.handler_name == "log"

    def test_human_instruction_falls_back(self):
        action = _make_action(
            action_name="decide_pricing", action_type="HUMAN_INSTRUCTION"
        )
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.handler_name == "human_instruction"

    def test_no_op_type_falls_back(self):
        action = _make_action(action_name="some_unknown_no_op", action_type="NO_OP")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.handler_name == "no_op"


# ─── Test: Resolution inspection ─────────────────────────────────


class TestHandlerResolutionInspection:
    def test_exact_resolution(self):
        action = _make_action(action_name="no_op")
        resolution = resolve_handler(
            action, DEFAULT_ACTION_HANDLERS, DEFAULT_TYPE_FALLBACK
        )
        assert resolution.resolution_path == "exact"
        assert resolution.resolved_handler == "no_op"

    def test_type_fallback_resolution(self):
        action = _make_action(action_name="unknown_task", action_type="TASK")
        resolution = resolve_handler(
            action, DEFAULT_ACTION_HANDLERS, DEFAULT_TYPE_FALLBACK
        )
        assert resolution.resolution_path == "type_fallback"
        assert resolution.resolved_handler == "log"

    def test_none_resolution(self):
        action = _make_action(action_name="totally_unknown", action_type="UNKNOWN_TYPE")
        resolution = resolve_handler(
            action, DEFAULT_ACTION_HANDLERS, DEFAULT_TYPE_FALLBACK
        )
        assert resolution.resolution_path == "none"
        assert resolution.resolved_handler is None

    def test_resolution_to_dict(self):
        action = _make_action(action_name="no_op")
        resolution = resolve_handler(
            action, DEFAULT_ACTION_HANDLERS, DEFAULT_TYPE_FALLBACK
        )
        d = resolution.to_dict()
        assert d["action_name"] == "no_op"
        assert d["resolution_path"] == "exact"

    def test_get_resolution_method(self):
        action = _make_action(action_name="increase_exploration", action_type="TASK")
        router = ExecutionRouter()
        resolution = router.get_resolution(action)
        assert resolution.resolution_path == "type_fallback"


# ─── Test: Unhandled path ────────────────────────────────────────


class TestUnhandledPath:
    def test_unknown_type_and_name(self):
        action = _make_action(action_name="mystery", action_type="TELEPORT")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "unhandled"
        assert result.handler_name is None
        assert result.output is None
        assert "No handler resolved" in result.error
        assert "mystery" in result.error

    def test_empty_handlers(self):
        action = _make_action()
        router = ExecutionRouter(handlers={}, type_fallback={})
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "unhandled"

    def test_type_fallback_points_to_missing_handler(self):
        action = _make_action(action_name="unknown", action_type="TASK")
        router = ExecutionRouter(
            handlers={},
            type_fallback={"TASK": "nonexistent_handler"},
        )
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "unhandled"


# ─── Test: Handler failure path ──────────────────────────────────


class TestHandlerFailure:
    def test_exception_caught(self):
        action = _make_action(action_name="exploding")
        router = ExecutionRouter(
            handlers={"exploding": ExplodingHandler()},
            type_fallback={},
        )
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "failed"
        assert result.handler_name == "exploding"
        assert result.output is None
        assert "handler exploded" in result.error

    def test_failure_preserves_action_id(self):
        action = _make_action(action_name="exploding", action_id="fail_id")
        router = ExecutionRouter(
            handlers={"exploding": ExplodingHandler()},
            type_fallback={},
        )
        result = router.route(ExecutionRequest(action=action))
        assert result.action_id == "fail_id"


# ─── Test: Built-in handlers ────────────────────────────────────


class TestBuiltInHandlers:
    def test_no_op_handler(self):
        handler = NoOpHandler()
        output = handler.execute(_make_action())
        assert output == {"message": "no operation"}
        assert handler.name == "no_op"

    def test_log_handler(self):
        handler = LogHandler()
        action = _make_action(
            action_name="test_action", target="crm", domain="business"
        )
        output = handler.execute(action)
        assert output["logged_action"] == "test_action"
        assert output["target"] == "crm"
        assert output["domain"] == "business"
        assert handler.name == "log"

    def test_human_instruction_handler(self):
        handler = HumanInstructionHandler()
        action = _make_action(intent="task: follow up", target="team")
        output = handler.execute(action)
        assert output["instruction"] == "task: follow up"
        assert output["target"] == "team"
        assert handler.name == "human_instruction"

    def test_human_instruction_no_target_defaults_to_human(self):
        handler = HumanInstructionHandler()
        action = _make_action(target=None)
        output = handler.execute(action)
        assert output["target"] == "human"

    def test_base_handler_raises(self):
        handler = BaseHandler()
        try:
            handler.execute(_make_action())
            assert False, "should have raised"
        except NotImplementedError:
            pass


# ─── Test: Determinism ──────────────────────────────────────────


class TestDeterminism:
    def test_same_action_same_result(self):
        action = _make_action()
        router = ExecutionRouter()
        r1 = router.route(ExecutionRequest(action=action))
        r2 = router.route(ExecutionRequest(action=action))
        assert r1.to_dict() == r2.to_dict()

    def test_same_resolution_twice(self):
        action = _make_action(action_name="unknown_task", action_type="TASK")
        res1 = resolve_handler(action, DEFAULT_ACTION_HANDLERS, DEFAULT_TYPE_FALLBACK)
        res2 = resolve_handler(action, DEFAULT_ACTION_HANDLERS, DEFAULT_TYPE_FALLBACK)
        assert res1.to_dict() == res2.to_dict()


# ─── Test: Serialization ────────────────────────────────────────


class TestSerialization:
    def test_execution_result_to_dict(self):
        result = ExecutionResult(
            action_id="a1",
            action_name="test",
            handler_name="log",
            status="success",
            output={"logged_action": "test"},
            error=None,
        )
        d = result.to_dict()
        assert d["action_id"] == "a1"
        assert d["status"] == "success"
        assert d["error"] is None

    def test_execution_result_roundtrip(self):
        result = ExecutionResult(
            action_id="a1",
            action_name="test",
            handler_name="log",
            status="success",
            output={"key": "value"},
            error=None,
        )
        d = result.to_dict()
        restored = ExecutionResult.from_dict(d)
        assert restored.action_id == result.action_id
        assert restored.status == result.status

    def test_execution_request_to_dict(self):
        action = _make_action()
        req = ExecutionRequest(action=action)
        d = req.to_dict()
        assert "action" in d
        assert d["action"]["action_id"] == "abc123"

    def test_handler_resolution_to_dict(self):
        res = HandlerResolution(
            action_name="test",
            action_type="TASK",
            resolved_handler="log",
            resolution_path="type_fallback",
        )
        d = res.to_dict()
        assert d["resolution_path"] == "type_fallback"


# ─── Test: Custom handler registration ──────────────────────────


class TestCustomHandlers:
    def test_custom_handler_exact_match(self):
        class MyHandler(BaseHandler):
            name = "custom"

            def execute(self, action):
                return {"custom": True}

        router = ExecutionRouter(
            handlers={"my_action": MyHandler()},
            type_fallback={},
        )
        action = _make_action(action_name="my_action")
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.output == {"custom": True}
        assert result.handler_name == "custom"


# ─── Test: Domain adapter → action schema → router integration ──


class TestFullPipelineIntegration:
    def test_business_action_routes(self):
        decision = types.SimpleNamespace(
            action="increase exploration and follow up",
            confidence=0.8,
            risk_score=0.3,
        )
        plan = adapt_output(decision, DomainType.BUSINESS)
        assert len(plan.steps) > 0

        norm = to_executable_action(plan, "business", 0.8)
        action = norm.executable_action

        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status == "success"
        assert result.action_id == action.action_id

    def test_all_domains_route_safely(self):
        router = ExecutionRouter()
        for domain in DomainType:
            decision = types.SimpleNamespace(
                action="optimize and stabilize",
                confidence=0.7,
                risk_score=0.4,
            )
            plan = adapt_output(decision, domain)
            if plan.steps:
                norm = to_executable_action(plan, domain.value, 0.7)
                result = router.route(ExecutionRequest(action=norm.executable_action))
                assert result.status in ("success", "unhandled")

    def test_empty_plan_routes_to_no_op(self):
        decision = types.SimpleNamespace(action="", confidence=0.5, risk_score=0.5)
        plan = adapt_output(decision, DomainType.BUSINESS)
        norm = to_executable_action(plan, "business", 0.5)
        assert norm.executable_action.action_type == "NO_OP"

        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=norm.executable_action))
        assert result.status == "success"
        assert result.handler_name == "no_op"


# ─── Test: DecisionTrace enrichment ─────────────────────────────


class TestDecisionTraceEnrichment:
    def test_trace_has_execution_fields(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        trace = DecisionTrace(
            turn_id=1,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.0,
            confidence=0.0,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            execution_status="success",
            execution_handler="log",
            execution_resolution_path="type_fallback",
            execution_error=None,
        )
        assert trace.execution_status == "success"
        assert trace.execution_handler == "log"
        assert trace.execution_resolution_path == "type_fallback"
        assert trace.execution_error is None

    def test_trace_to_dict_includes_execution(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        trace = DecisionTrace(
            turn_id=1,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.0,
            confidence=0.0,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            execution_status="failed",
            execution_handler="exploding",
            execution_resolution_path="exact",
            execution_error="boom",
        )
        d = trace.to_dict()
        assert d["execution_status"] == "failed"
        assert d["execution_handler"] == "exploding"
        assert d["execution_resolution_path"] == "exact"
        assert d["execution_error"] == "boom"

    def test_trace_omits_execution_when_none(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        trace = DecisionTrace(
            turn_id=1,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.0,
            confidence=0.0,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
        )
        d = trace.to_dict()
        assert "execution_status" not in d
        assert "execution_handler" not in d

    def test_build_trace_with_execution_fields(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            execution_status="success",
            execution_handler="log",
            execution_resolution_path="type_fallback",
            execution_error=None,
        )
        assert trace.execution_status == "success"
        assert trace.execution_handler == "log"


# ─── Test: SessionInterface integration ──────────────────────────


class TestSessionInterfaceIntegration:
    def test_get_last_execution_result_none_default(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._session_id = "test"
        iface._decisions = []
        iface._intent = None
        iface._runtime = None
        iface._builder = None
        iface._last_adapted_input = None
        iface._last_executable_action = None
        iface._last_execution_result = None
        iface._ctx = None
        iface._control_enabled = True
        iface._calibration_enabled = True
        iface._convergence_enabled = True
        iface._persist_memory = False
        assert iface.get_last_execution_result() is None

    def test_reset_clears_execution_result(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._session_id = "test"
        iface._decisions = []
        iface._intent = None
        iface._runtime = None
        iface._builder = None
        iface._last_adapted_input = None
        iface._last_executable_action = None
        iface._last_execution_result = "something"
        iface._ctx = None
        iface._control_enabled = True
        iface._calibration_enabled = True
        iface._convergence_enabled = True
        iface._persist_memory = False
        iface.reset()
        assert iface._last_execution_result is None


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
