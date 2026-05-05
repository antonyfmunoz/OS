"""Tests for eos_ai.system_graph — multi-step execution graph."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime_engine.system_graph import (
    MAX_NODES,
    SystemExecutionResult,
    SystemGraph,
    SystemNode,
    build_system_graph,
    execute_system_graph,
    _actions_are_independent,
    _compute_graph_id,
    _detect_dependencies,
    _has_cycle,
    _topological_sort,
)
from umh.runtime_engine.action_schema import ExecutableAction
from umh.runtime_engine.execution_router import (
    BaseHandler,
    ExecutionRequest,
    ExecutionResult,
    ExecutionRouter,
)


# ─── Helpers ───────────────────────────────────────────────────────


def _make_action(
    action_id: str = "a1",
    domain: str = "business",
    target: str | None = None,
    action_name: str = "test_action",
    action_type: str = "TASK",
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


class SuccessHandler(BaseHandler):
    name = "always_success"

    def execute(self, action: object) -> dict:
        return {"result": "ok", "action_id": getattr(action, "action_id", "")}


class FailHandler(BaseHandler):
    name = "always_fail"

    def execute(self, action: object) -> dict:
        raise RuntimeError("intentional failure")


class ConditionalRouter:
    """A fake router that fails specific action IDs."""

    def __init__(self, fail_ids: set[str] | None = None):
        self._fail_ids = fail_ids or set()

    def route(self, request: ExecutionRequest) -> ExecutionResult:
        action = request.action
        aid = getattr(action, "action_id", "")
        aname = getattr(action, "action_name", "")
        if aid in self._fail_ids:
            return ExecutionResult(
                action_id=aid,
                action_name=aname,
                handler_name="conditional",
                status="failed",
                output=None,
                error="forced failure",
            )
        return ExecutionResult(
            action_id=aid,
            action_name=aname,
            handler_name="conditional",
            status="success",
            output={"result": "ok"},
            error=None,
        )


# ═══════════════════════════════════════════════════════════════════
# Graph construction
# ═══════════════════════════════════════════════════════════════════


class TestGraphConstruction:
    def test_empty_plan(self):
        graph = build_system_graph([])
        assert graph.status == "completed"
        assert len(graph.nodes) == 0
        assert graph.entry_points == ()
        assert graph.exit_nodes == ()

    def test_single_action(self):
        action = _make_action("a1")
        graph = build_system_graph([action])
        assert len(graph.nodes) == 1
        node = list(graph.nodes.values())[0]
        assert node.status == "ready"
        assert node.depends_on == ()
        assert graph.entry_points == (node.node_id,)
        assert graph.exit_nodes == (node.node_id,)

    def test_linear_chain_same_domain(self):
        a1 = _make_action("a1", domain="business")
        a2 = _make_action("a2", domain="business")
        a3 = _make_action("a3", domain="business")
        graph = build_system_graph([a1, a2, a3])
        assert len(graph.nodes) == 3
        nodes = list(graph.nodes.values())
        assert nodes[0].depends_on == ()
        assert len(nodes[1].depends_on) > 0
        assert len(nodes[2].depends_on) > 0

    def test_independent_different_domains(self):
        a1 = _make_action("a1", domain="business")
        a2 = _make_action("a2", domain="marketing")
        graph = build_system_graph([a1, a2])
        assert len(graph.nodes) == 2
        nodes = list(graph.nodes.values())
        assert nodes[0].depends_on == ()
        assert nodes[1].depends_on == ()
        assert len(graph.entry_points) == 2

    def test_mixed_dependencies(self):
        a1 = _make_action("a1", domain="business")
        a2 = _make_action("a2", domain="marketing")
        a3 = _make_action("a3", domain="business")
        graph = build_system_graph([a1, a2, a3])
        nodes = list(graph.nodes.values())
        assert nodes[0].depends_on == ()
        assert nodes[1].depends_on == ()
        assert len(nodes[2].depends_on) > 0

    def test_graph_has_deterministic_id(self):
        a1 = _make_action("a1")
        a2 = _make_action("a2")
        g1 = build_system_graph([a1, a2])
        g2 = build_system_graph([a1, a2])
        assert g1.graph_id == g2.graph_id

    def test_different_actions_different_id(self):
        g1 = build_system_graph([_make_action("a1")])
        g2 = build_system_graph([_make_action("a2")])
        assert g1.graph_id != g2.graph_id

    def test_max_nodes_truncation(self):
        actions = [_make_action(f"a{i}") for i in range(MAX_NODES + 5)]
        graph = build_system_graph(actions)
        assert len(graph.nodes) == MAX_NODES

    def test_entry_and_exit_identification(self):
        a1 = _make_action("a1", domain="x")
        a2 = _make_action("a2", domain="y")
        a3 = _make_action("a3", domain="z")
        graph = build_system_graph([a1, a2, a3])
        assert len(graph.entry_points) >= 1
        assert len(graph.exit_nodes) >= 1

    def test_graph_status_starts_pending(self):
        graph = build_system_graph([_make_action("a1")])
        assert graph.status == "pending"


# ═══════════════════════════════════════════════════════════════════
# Dependency detection
# ═══════════════════════════════════════════════════════════════════


class TestDependencyDetection:
    def test_independent_actions(self):
        a = _make_action("a1", domain="x")
        b = _make_action("a2", domain="y")
        assert _actions_are_independent(a, b) is True

    def test_same_domain_dependent(self):
        a = _make_action("a1", domain="x")
        b = _make_action("a2", domain="x")
        assert _actions_are_independent(a, b) is False

    def test_empty_domain_dependent(self):
        a = _make_action("a1", domain="")
        b = _make_action("a2", domain="")
        assert _actions_are_independent(a, b) is False

    def test_detect_linear_deps(self):
        actions = [_make_action(f"a{i}", domain="x") for i in range(3)]
        deps = _detect_dependencies(actions)
        assert deps[0] == ()
        assert 0 in deps[1]
        assert len(deps[2]) > 0

    def test_detect_parallel_deps(self):
        actions = [
            _make_action("a1", domain="x"),
            _make_action("a2", domain="y"),
            _make_action("a3", domain="z"),
        ]
        deps = _detect_dependencies(actions)
        assert deps[0] == ()
        assert deps[1] == ()
        assert deps[2] == ()

    def test_single_action_no_deps(self):
        deps = _detect_dependencies([_make_action("a1")])
        assert deps[0] == ()


# ═══════════════════════════════════════════════════════════════════
# Topological sort
# ═══════════════════════════════════════════════════════════════════


class TestTopologicalSort:
    def test_linear_chain(self):
        deps = {"a": (), "b": ("a",), "c": ("b",)}
        order = _topological_sort(deps)
        assert order == ("a", "b", "c")

    def test_parallel_nodes(self):
        deps = {"a": (), "b": (), "c": ()}
        order = _topological_sort(deps)
        assert set(order) == {"a", "b", "c"}
        assert len(order) == 3

    def test_diamond_shape(self):
        deps = {"a": (), "b": ("a",), "c": ("a",), "d": ("b", "c")}
        order = _topological_sort(deps)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_cycle_raises(self):
        deps = {"a": ("b",), "b": ("a",)}
        with pytest.raises(ValueError, match="Cycle"):
            _topological_sort(deps)

    def test_single_node(self):
        order = _topological_sort({"a": ()})
        assert order == ("a",)

    def test_empty_graph(self):
        order = _topological_sort({})
        assert order == ()


# ═══════════════════════════════════════════════════════════════════
# Cycle detection
# ═══════════════════════════════════════════════════════════════════


class TestCycleDetection:
    def test_no_cycle(self):
        assert _has_cycle({"a": (), "b": ("a",)}) is False

    def test_self_cycle(self):
        assert _has_cycle({"a": ("a",)}) is True

    def test_two_node_cycle(self):
        assert _has_cycle({"a": ("b",), "b": ("a",)}) is True

    def test_three_node_cycle(self):
        assert _has_cycle({"a": ("c",), "b": ("a",), "c": ("b",)}) is True

    def test_no_cycle_diamond(self):
        deps = {"a": (), "b": ("a",), "c": ("a",), "d": ("b", "c")}
        assert _has_cycle(deps) is False


# ═══════════════════════════════════════════════════════════════════
# Execution
# ═══════════════════════════════════════════════════════════════════


class TestExecution:
    def test_execute_empty_graph(self):
        graph = build_system_graph([])
        result = execute_system_graph(graph, ExecutionRouter())
        assert result.status == "completed"
        assert result.total_nodes == 0

    def test_execute_single_success(self):
        action = _make_action("a1")
        graph = build_system_graph([action])
        router = ConditionalRouter()
        result = execute_system_graph(graph, router)
        assert result.status == "completed"
        assert result.completed_nodes == 1
        assert result.failed_nodes == 0

    def test_execute_linear_chain(self):
        actions = [_make_action(f"a{i}", domain="x") for i in range(3)]
        graph = build_system_graph(actions)
        router = ConditionalRouter()
        result = execute_system_graph(graph, router)
        assert result.status == "completed"
        assert result.completed_nodes == 3
        assert len(result.node_execution_order) == 3

    def test_execute_parallel_success(self):
        a1 = _make_action("a1", domain="x")
        a2 = _make_action("a2", domain="y")
        graph = build_system_graph([a1, a2])
        router = ConditionalRouter()
        result = execute_system_graph(graph, router)
        assert result.status == "completed"
        assert result.completed_nodes == 2

    def test_execute_deterministic_outputs(self):
        actions = [_make_action(f"a{i}", domain="x") for i in range(2)]
        graph = build_system_graph(actions)
        router = ConditionalRouter()
        r1 = execute_system_graph(graph, router)
        r2 = execute_system_graph(graph, router)
        assert r1.node_execution_order == r2.node_execution_order
        assert r1.status == r2.status

    def test_execution_order_respects_dependencies(self):
        a1 = _make_action("a1", domain="x")
        a2 = _make_action("a2", domain="x")
        a3 = _make_action("a3", domain="x")
        graph = build_system_graph([a1, a2, a3])
        router = ConditionalRouter()
        result = execute_system_graph(graph, router)
        order = result.node_execution_order
        nids = list(graph.nodes.keys())
        assert order.index(nids[0]) < order.index(nids[1])
        assert order.index(nids[1]) < order.index(nids[2])


# ═══════════════════════════════════════════════════════════════════
# Failure propagation
# ═══════════════════════════════════════════════════════════════════


class TestFailurePropagation:
    def test_first_node_failure_blocks_chain(self):
        a1 = _make_action("a1", domain="x")
        a2 = _make_action("a2", domain="x")
        graph = build_system_graph([a1, a2])
        router = ConditionalRouter(fail_ids={"a1"})
        result = execute_system_graph(graph, router)
        assert result.failed_nodes >= 1
        assert result.blocked_nodes >= 1
        assert result.status == "partial" or result.status == "failed"

    def test_middle_node_failure(self):
        a1 = _make_action("a1", domain="x")
        a2 = _make_action("a2", domain="x")
        a3 = _make_action("a3", domain="x")
        graph = build_system_graph([a1, a2, a3])
        router = ConditionalRouter(fail_ids={"a2"})
        result = execute_system_graph(graph, router)
        assert result.completed_nodes >= 1
        assert result.failed_nodes >= 1

    def test_parallel_branch_failure_doesnt_block_other(self):
        a1 = _make_action("a1", domain="x")
        a2 = _make_action("a2", domain="y")
        graph = build_system_graph([a1, a2])
        router = ConditionalRouter(fail_ids={"a1"})
        result = execute_system_graph(graph, router)
        assert result.completed_nodes >= 1
        assert result.failed_nodes >= 1
        assert result.status == "partial"

    def test_all_nodes_fail(self):
        a1 = _make_action("a1", domain="x")
        a2 = _make_action("a2", domain="y")
        graph = build_system_graph([a1, a2])
        router = ConditionalRouter(fail_ids={"a1", "a2"})
        result = execute_system_graph(graph, router)
        assert result.failed_nodes == 2
        assert result.status == "failed"

    def test_partial_completion_status(self):
        a1 = _make_action("a1", domain="x")
        a2 = _make_action("a2", domain="x")
        a3 = _make_action("a3", domain="y")
        graph = build_system_graph([a1, a2, a3])
        router = ConditionalRouter(fail_ids={"a1"})
        result = execute_system_graph(graph, router)
        assert result.status == "partial"


# ═══════════════════════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════════════════════


class TestSerialization:
    def test_node_to_dict(self):
        action = _make_action("a1")
        node = SystemNode(
            node_id="n1",
            action=action,
            depends_on=("n0",),
            status="ready",
        )
        d = node.to_dict()
        assert d["node_id"] == "n1"
        assert d["depends_on"] == ["n0"]
        assert d["status"] == "ready"

    def test_graph_to_dict(self):
        graph = build_system_graph([_make_action("a1")])
        d = graph.to_dict()
        assert "graph_id" in d
        assert d["node_count"] == 1
        assert "entry_points" in d
        assert "exit_nodes" in d

    def test_result_to_dict(self):
        result = SystemExecutionResult(
            graph_id="g1",
            completed_nodes=1,
            failed_nodes=0,
            blocked_nodes=0,
            total_nodes=1,
            outputs={"n1": {"ok": True}},
            node_execution_order=("n1",),
            node_statuses={"n1": "done"},
            status="completed",
        )
        d = result.to_dict()
        assert d["graph_id"] == "g1"
        assert d["status"] == "completed"

    def test_empty_graph_to_dict(self):
        graph = build_system_graph([])
        d = graph.to_dict()
        assert d["node_count"] == 0
        assert d["status"] == "completed"


# ═══════════════════════════════════════════════════════════════════
# DecisionTrace integration
# ═══════════════════════════════════════════════════════════════════


class TestDecisionTraceIntegration:
    def test_new_fields_default_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        assert trace.system_graph_id is None
        assert trace.system_node_execution_order is None
        assert trace.system_node_statuses is None
        assert trace.system_status is None

    def test_new_fields_set(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            system_graph_id="g1",
            system_node_execution_order=("n1", "n2"),
            system_node_statuses={"n1": "done", "n2": "done"},
            system_status="completed",
        )
        assert trace.system_graph_id == "g1"
        assert trace.system_node_execution_order == ("n1", "n2")
        assert trace.system_node_statuses == {"n1": "done", "n2": "done"}
        assert trace.system_status == "completed"

    def test_to_dict_includes_fields(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            system_graph_id="g1",
            system_status="completed",
        )
        d = trace.to_dict()
        assert d["system_graph_id"] == "g1"
        assert d["system_status"] == "completed"

    def test_to_dict_omits_when_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        d = trace.to_dict()
        assert "system_graph_id" not in d
        assert "system_status" not in d


# ═══════════════════════════════════════════════════════════════════
# SessionInterface integration
# ═══════════════════════════════════════════════════════════════════


class TestSessionInterfaceIntegration:
    def test_get_last_system_result_none_default(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._last_system_result = None
        assert iface.get_last_system_result() is None

    def test_reset_clears_system_result(self):
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
        iface._last_system_result = "something"
        iface._runtime = None
        iface._session_id = "test"
        iface.reset()
        assert iface._last_system_result is None


# ═══════════════════════════════════════════════════════════════════
# No regression
# ═══════════════════════════════════════════════════════════════════


class TestNoRegression:
    def test_decision_trace_build_still_works(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        assert trace.turn_id == 1

    def test_execution_router_still_works(self):
        action = _make_action("a1")
        router = ExecutionRouter()
        result = router.route(ExecutionRequest(action=action))
        assert result.status in ("success", "unhandled")

    def test_action_schema_still_works(self):
        from umh.runtime_engine.action_schema import classify_action_type, ActionType

        assert classify_action_type("send email") == ActionType.MESSAGE


# ═══════════════════════════════════════════════════════════════════
# Graph ID determinism
# ═══════════════════════════════════════════════════════════════════


class TestGraphIdDeterminism:
    def test_same_actions_same_id(self):
        id1 = _compute_graph_id(("a1", "a2"))
        id2 = _compute_graph_id(("a1", "a2"))
        assert id1 == id2

    def test_different_actions_different_id(self):
        id1 = _compute_graph_id(("a1", "a2"))
        id2 = _compute_graph_id(("a3", "a4"))
        assert id1 != id2

    def test_order_matters(self):
        id1 = _compute_graph_id(("a1", "a2"))
        id2 = _compute_graph_id(("a2", "a1"))
        assert id1 != id2
