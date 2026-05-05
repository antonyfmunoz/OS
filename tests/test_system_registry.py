"""Tests for eos_ai.system_registry + eos_ai.system_selector."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime_engine.system_registry import (
    CONTEXT_MATCH_THRESHOLD,
    EMA_ALPHA,
    MAX_TEMPLATES,
    SystemRegistry,
    SystemTemplate,
    _compute_template_id,
    _extract_action_types,
    _extract_domains,
    _result_credit,
    _result_success,
    context_match_score,
)
from umh.runtime_engine.system_selector import (
    MIN_COMPOSITE_SCORE,
    MIN_CONFIDENCE_FOR_SELECTION,
    MIN_USAGE_FOR_SELECTION,
    NO_SELECTION,
    SystemSelectionResult,
    select_system,
    _normalize_credit,
    _score_candidate,
)
from umh.runtime_engine.action_schema import ExecutableAction
from umh.runtime_engine.system_graph import SystemExecutionResult, SystemGraph, SystemNode


# ─── Helpers ───────────────────────────────────────────────────────


def _make_action(
    action_id: str = "a1",
    action_type: str = "TASK",
    domain: str = "business",
) -> ExecutableAction:
    return ExecutableAction(
        action_id=action_id,
        action_type=action_type,
        action_name="test_action",
        target=None,
        intent="task: test",
        payload={},
        constraints={},
        priority=0.5,
        confidence=0.8,
        domain=domain,
        trace_id=None,
        explanation=None,
    )


def _make_graph(
    actions: list[ExecutableAction] | None = None,
) -> SystemGraph:
    if actions is None:
        actions = [_make_action("a1"), _make_action("a2")]
    nodes = {}
    for i, a in enumerate(actions):
        nid = f"n_{i}_{a.action_id[:8]}"
        dep = (list(nodes.keys())[-1],) if nodes else ()
        nodes[nid] = SystemNode(
            node_id=nid,
            action=a,
            depends_on=dep,
            status="done",
        )
    entry = tuple(nid for nid, n in nodes.items() if not n.depends_on)
    last_nid = list(nodes.keys())[-1] if nodes else ()
    exit_n = (last_nid,) if last_nid else ()
    return SystemGraph(
        graph_id="g_test",
        nodes=nodes,
        entry_points=entry,
        exit_nodes=exit_n,
        status="completed",
    )


def _make_result(
    status: str = "completed",
    completed: int = 2,
    failed: int = 0,
    total: int = 2,
) -> SystemExecutionResult:
    return SystemExecutionResult(
        graph_id="g_test",
        completed_nodes=completed,
        failed_nodes=failed,
        blocked_nodes=0,
        total_nodes=total,
        outputs={},
        node_execution_order=(),
        node_statuses={},
        status=status,
    )


def _make_context(
    context_type: str = "business",
    uncertainty: str = "low",
    risk: str = "low",
) -> dict[str, str]:
    return {
        "context_type": context_type,
        "objective_mode": "default",
        "meta_control": "full",
        "uncertainty": uncertainty,
        "risk_level": risk,
    }


def _make_template(
    template_id: str = "t1",
    context: dict | None = None,
    success_rate: float = 0.8,
    avg_credit: float = 0.5,
    usage_count: int = 5,
    confidence: float = 0.33,
) -> SystemTemplate:
    return SystemTemplate(
        template_id=template_id,
        graph=_make_graph(),
        context_signature=context or _make_context(),
        action_types=("TASK",),
        success_rate=success_rate,
        avg_credit=avg_credit,
        usage_count=usage_count,
        confidence=confidence,
        domains={"business"},
    )


# ═══════════════════════════════════════════════════════════════════
# Context matching
# ═══════════════════════════════════════════════════════════════════


class TestContextMatching:
    def test_identical_contexts_perfect_match(self):
        ctx = _make_context()
        assert context_match_score(ctx, ctx) == 1.0

    def test_completely_different(self):
        a = {"a": "1", "b": "2"}
        b = {"a": "x", "b": "y"}
        assert context_match_score(a, b) == 0.0

    def test_partial_match(self):
        a = _make_context("business")
        b = _make_context("marketing")
        score = context_match_score(a, b)
        assert 0.0 < score < 1.0

    def test_empty_template_zero(self):
        assert context_match_score({"a": "1"}, {}) == 0.0

    def test_disjoint_keys(self):
        a = {"x": "1"}
        b = {"y": "2"}
        score = context_match_score(a, b)
        assert score == 0.0

    def test_superset_keys(self):
        a = {"a": "1", "b": "2", "c": "3"}
        b = {"a": "1", "b": "2"}
        score = context_match_score(a, b)
        assert score == pytest.approx(2.0 / 3.0, abs=0.01)


# ═══════════════════════════════════════════════════════════════════
# Template ID
# ═══════════════════════════════════════════════════════════════════


class TestTemplateId:
    def test_deterministic(self):
        ctx = _make_context()
        types = ("TASK",)
        id1 = _compute_template_id(ctx, types)
        id2 = _compute_template_id(ctx, types)
        assert id1 == id2

    def test_different_context_different_id(self):
        id1 = _compute_template_id(_make_context("a"), ("TASK",))
        id2 = _compute_template_id(_make_context("b"), ("TASK",))
        assert id1 != id2

    def test_different_types_different_id(self):
        ctx = _make_context()
        id1 = _compute_template_id(ctx, ("TASK",))
        id2 = _compute_template_id(ctx, ("API_CALL",))
        assert id1 != id2


# ═══════════════════════════════════════════════════════════════════
# Extract helpers
# ═══════════════════════════════════════════════════════════════════


class TestExtractHelpers:
    def test_extract_action_types(self):
        graph = _make_graph([_make_action("a1", "TASK"), _make_action("a2", "API_CALL")])
        types = _extract_action_types(graph)
        assert types == ("API_CALL", "TASK")

    def test_extract_domains(self):
        graph = _make_graph(
            [_make_action("a1", domain="x"), _make_action("a2", domain="y")]
        )
        domains = _extract_domains(graph)
        assert domains == {"x", "y"}

    def test_result_credit_perfect(self):
        result = _make_result(completed=3, failed=0, total=3)
        assert _result_credit(result) == 1.0

    def test_result_credit_mixed(self):
        result = _make_result(completed=2, failed=1, total=3)
        assert _result_credit(result) == pytest.approx(1.0 / 3.0, abs=0.01)

    def test_result_success_completed(self):
        assert _result_success(_make_result(status="completed")) is True

    def test_result_success_strong_partial(self):
        result = _make_result(status="partial", completed=3, total=4)
        assert _result_success(result) is True

    def test_result_success_weak_partial(self):
        result = _make_result(status="partial", completed=1, total=4)
        assert _result_success(result) is False

    def test_result_success_failed(self):
        assert _result_success(_make_result(status="failed")) is False


# ═══════════════════════════════════════════════════════════════════
# Registry — storage
# ═══════════════════════════════════════════════════════════════════


class TestRegistryStorage:
    def test_empty_registry(self):
        reg = SystemRegistry()
        assert reg.count == 0
        assert reg.get_all() == []

    def test_register_successful(self):
        reg = SystemRegistry()
        graph = _make_graph()
        result = _make_result(status="completed")
        tid = reg.register(graph, _make_context(), result)
        assert tid is not None
        assert reg.count == 1

    def test_register_rejected_on_failure(self):
        reg = SystemRegistry()
        graph = _make_graph()
        result = _make_result(status="failed")
        tid = reg.register(graph, _make_context(), result)
        assert tid is None
        assert reg.count == 0

    def test_register_updates_existing(self):
        reg = SystemRegistry()
        graph = _make_graph()
        ctx = _make_context()
        result = _make_result(status="completed")
        tid1 = reg.register(graph, ctx, result)
        tid2 = reg.register(graph, ctx, result)
        assert tid1 == tid2
        assert reg.count == 1
        template = reg.get(tid1)
        assert template.usage_count == 2

    def test_get_returns_none_for_missing(self):
        reg = SystemRegistry()
        assert reg.get("nonexistent") is None

    def test_reset_clears(self):
        reg = SystemRegistry()
        reg.register(_make_graph(), _make_context(), _make_result())
        reg.reset()
        assert reg.count == 0


# ═══════════════════════════════════════════════════════════════════
# Registry — update
# ═══════════════════════════════════════════════════════════════════


class TestRegistryUpdate:
    def test_update_existing(self):
        reg = SystemRegistry()
        tid = reg.register(_make_graph(), _make_context(), _make_result())
        assert reg.update_template(tid, credit=0.8, success=True)
        template = reg.get(tid)
        assert template.usage_count == 2

    def test_update_nonexistent(self):
        reg = SystemRegistry()
        assert reg.update_template("nope", credit=0.5, success=True) is False

    def test_ema_update_success_rate(self):
        reg = SystemRegistry()
        tid = reg.register(_make_graph(), _make_context(), _make_result())
        t1 = reg.get(tid)
        initial_sr = t1.success_rate
        reg.update_template(tid, credit=0.5, success=False)
        t2 = reg.get(tid)
        expected = (1.0 - EMA_ALPHA) * initial_sr + EMA_ALPHA * 0.0
        assert t2.success_rate == pytest.approx(expected, abs=0.01)

    def test_ema_update_credit(self):
        reg = SystemRegistry()
        tid = reg.register(_make_graph(), _make_context(), _make_result())
        t1 = reg.get(tid)
        initial_credit = t1.avg_credit
        reg.update_template(tid, credit=-0.5, success=True)
        t2 = reg.get(tid)
        expected = (1.0 - EMA_ALPHA) * initial_credit + EMA_ALPHA * (-0.5)
        assert t2.avg_credit == pytest.approx(expected, abs=0.01)

    def test_confidence_increases_with_usage(self):
        reg = SystemRegistry()
        tid = reg.register(_make_graph(), _make_context(), _make_result())
        c1 = reg.get(tid).confidence
        reg.update_template(tid, credit=0.5, success=True)
        c2 = reg.get(tid).confidence
        assert c2 > c1


# ═══════════════════════════════════════════════════════════════════
# Registry — find candidates
# ═══════════════════════════════════════════════════════════════════


class TestFindCandidates:
    def test_empty_registry_no_candidates(self):
        reg = SystemRegistry()
        assert reg.find_candidates(_make_context()) == []

    def test_exact_match_found(self):
        reg = SystemRegistry()
        ctx = _make_context()
        reg.register(_make_graph(), ctx, _make_result())
        candidates = reg.find_candidates(ctx)
        assert len(candidates) >= 1
        assert candidates[0][0] == 1.0

    def test_partial_match(self):
        reg = SystemRegistry()
        reg.register(_make_graph(), _make_context("business"), _make_result())
        candidates = reg.find_candidates(_make_context("marketing"))
        if candidates:
            assert candidates[0][0] < 1.0

    def test_below_threshold_excluded(self):
        reg = SystemRegistry()
        reg.register(
            _make_graph(),
            {"totally": "different", "keys": "here"},
            _make_result(),
        )
        candidates = reg.find_candidates(_make_context())
        assert len(candidates) == 0

    def test_sorted_by_match_score(self):
        reg = SystemRegistry()
        ctx1 = _make_context("business")
        ctx2 = _make_context("marketing")
        reg.register(
            _make_graph([_make_action("a1", "TASK")]),
            ctx1,
            _make_result(),
        )
        reg.register(
            _make_graph([_make_action("a2", "API_CALL")]),
            ctx2,
            _make_result(),
        )
        candidates = reg.find_candidates(_make_context("business"))
        if len(candidates) >= 2:
            assert candidates[0][0] >= candidates[1][0]


# ═══════════════════════════════════════════════════════════════════
# Registry — eviction
# ═══════════════════════════════════════════════════════════════════


class TestRegistryEviction:
    def test_evicts_at_max(self):
        reg = SystemRegistry()
        for i in range(MAX_TEMPLATES + 5):
            ctx = _make_context(f"type_{i}")
            graph = _make_graph([_make_action(f"a{i}", domain=f"d{i}")])
            reg.register(graph, ctx, _make_result())
        assert reg.count <= MAX_TEMPLATES


# ═══════════════════════════════════════════════════════════════════
# Selector — scoring
# ═══════════════════════════════════════════════════════════════════


class TestScoring:
    def test_normalize_credit_positive(self):
        assert _normalize_credit(1.0) == 1.0

    def test_normalize_credit_negative(self):
        assert _normalize_credit(-1.0) == 0.0

    def test_normalize_credit_zero(self):
        assert _normalize_credit(0.0) == 0.5

    def test_score_perfect_candidate(self):
        template = _make_template(
            success_rate=1.0, avg_credit=1.0, confidence=1.0
        )
        score = _score_candidate(1.0, template)
        assert score > 0.8

    def test_score_weak_candidate(self):
        template = _make_template(
            success_rate=0.1, avg_credit=-0.5, confidence=0.05
        )
        score = _score_candidate(0.4, template)
        assert score < 0.5

    def test_score_bounded(self):
        template = _make_template(success_rate=1.0, avg_credit=1.0, confidence=1.0)
        score = _score_candidate(1.0, template)
        assert 0.0 <= score <= 1.0


# ═══════════════════════════════════════════════════════════════════
# Selector — selection
# ═══════════════════════════════════════════════════════════════════


class TestSelection:
    def test_no_candidates_fallback(self):
        result = select_system(_make_context(), [])
        assert result.used_fallback is True
        assert result.selected_template_id is None
        assert result.reason == "no_candidates"

    def test_selects_best_candidate(self):
        t1 = _make_template("t1", success_rate=0.9, usage_count=5, confidence=0.33)
        t2 = _make_template("t2", success_rate=0.5, usage_count=5, confidence=0.33)
        candidates = [(0.8, t1), (0.8, t2)]
        result = select_system(_make_context(), candidates)
        assert result.selected_template_id == "t1"
        assert result.used_fallback is False

    def test_usage_threshold_filters(self):
        t = _make_template(usage_count=1, confidence=0.5)
        result = select_system(_make_context(), [(0.8, t)])
        assert result.used_fallback is True

    def test_confidence_threshold_filters(self):
        t = _make_template(usage_count=10, confidence=0.01)
        result = select_system(_make_context(), [(0.8, t)])
        assert result.used_fallback is True

    def test_low_composite_falls_back(self):
        t = _make_template(
            success_rate=0.0,
            avg_credit=-1.0,
            usage_count=5,
            confidence=0.33,
        )
        result = select_system(_make_context(), [(0.3, t)])
        assert result.used_fallback is True

    def test_deterministic_selection(self):
        t = _make_template(usage_count=5, confidence=0.33, success_rate=0.9)
        r1 = select_system(_make_context(), [(0.8, t)])
        r2 = select_system(_make_context(), [(0.8, t)])
        assert r1.selected_template_id == r2.selected_template_id
        assert r1.composite_score == r2.composite_score

    def test_no_selection_sentinel(self):
        assert NO_SELECTION.used_fallback is True
        assert NO_SELECTION.selected_template_id is None

    def test_result_to_dict(self):
        result = SystemSelectionResult(
            selected_template_id="t1",
            match_score=0.8,
            composite_score=0.65,
            used_fallback=False,
            reason="selected:t1",
        )
        d = result.to_dict()
        assert d["selected_template_id"] == "t1"
        assert d["used_fallback"] is False


# ═══════════════════════════════════════════════════════════════════
# Template serialization
# ═══════════════════════════════════════════════════════════════════


class TestTemplateSerialization:
    def test_to_dict(self):
        t = _make_template()
        d = t.to_dict()
        assert d["template_id"] == "t1"
        assert d["usage_count"] == 5
        assert "domains" in d

    def test_round_trip(self):
        t = _make_template()
        d = t.to_dict()
        d["graph"] = None
        t2 = SystemTemplate.from_dict(d)
        assert t2.template_id == t.template_id
        assert t2.success_rate == pytest.approx(t.success_rate, abs=0.001)
        assert t2.usage_count == t.usage_count

    def test_registry_to_dict(self):
        reg = SystemRegistry()
        reg.register(_make_graph(), _make_context(), _make_result())
        d = reg.to_dict()
        assert len(d) == 1


# ═══════════════════════════════════════════════════════════════════
# DecisionTrace integration
# ═══════════════════════════════════════════════════════════════════


class TestDecisionTraceIntegration:
    def test_new_fields_default_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        assert trace.system_template_used is None
        assert trace.system_match_score is None
        assert trace.system_source is None

    def test_new_fields_set(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            system_template_used="t1",
            system_match_score=0.85,
            system_source="template",
        )
        assert trace.system_template_used == "t1"
        assert trace.system_match_score == 0.85
        assert trace.system_source == "template"

    def test_to_dict_includes_when_set(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            system_template_used="t1",
            system_source="constructed",
        )
        d = trace.to_dict()
        assert d["system_template_used"] == "t1"
        assert d["system_source"] == "constructed"

    def test_to_dict_omits_when_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        d = trace.to_dict()
        assert "system_template_used" not in d
        assert "system_source" not in d


# ═══════════════════════════════════════════════════════════════════
# SessionInterface integration
# ═══════════════════════════════════════════════════════════════════


class TestSessionInterfaceIntegration:
    def test_accessor_default_none(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._last_system_selection = None
        assert iface.get_last_system_selection() is None

    def test_reset_clears_selection(self):
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
        iface._last_environment_route = None
        iface._last_adapter_result = None
        iface._last_system_selection = "something"
        iface._runtime = None
        iface._session_id = "test"
        iface.reset()
        assert iface._last_system_selection is None


# ═══════════════════════════════════════════════════════════════════
# End-to-end: registry + selector
# ═══════════════════════════════════════════════════════════════════


class TestEndToEnd:
    def test_register_then_select(self):
        reg = SystemRegistry()
        ctx = _make_context()
        graph = _make_graph()
        result = _make_result()

        for _ in range(MIN_USAGE_FOR_SELECTION + 1):
            reg.register(graph, ctx, result)

        candidates = reg.find_candidates(ctx)
        selection = select_system(ctx, candidates)
        assert selection.selected_template_id is not None
        assert selection.used_fallback is False

    def test_no_match_fallback(self):
        reg = SystemRegistry()
        reg.register(
            _make_graph(),
            {"x": "1", "y": "2"},
            _make_result(),
        )
        candidates = reg.find_candidates(_make_context())
        selection = select_system(_make_context(), candidates)
        assert selection.used_fallback is True

    def test_learning_improves_confidence(self):
        reg = SystemRegistry()
        ctx = _make_context()
        graph = _make_graph()
        result = _make_result()

        tid = reg.register(graph, ctx, result)
        c1 = reg.get(tid).confidence

        for _ in range(10):
            reg.update_template(tid, credit=0.8, success=True)
        c2 = reg.get(tid).confidence
        assert c2 > c1


# ═══════════════════════════════════════════════════════════════════
# No regression
# ═══════════════════════════════════════════════════════════════════


class TestNoRegression:
    def test_decision_trace_build_still_works(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        assert trace.turn_id == 1

    def test_system_graph_still_works(self):
        from umh.runtime_engine.system_graph import build_system_graph

        graph = build_system_graph([_make_action("a1")])
        assert len(graph.nodes) == 1

    def test_strategy_abstraction_context_still_works(self):
        from umh.runtime_engine.strategy_abstraction import extract_context_signature

        class FakeTrace:
            context_type = "business"
            objective_arb_mode = "default"
            meta_control_mode = "full"
            planner_uncertainty = 0.1
            calibration_risk_bias = 0.2

        sig = extract_context_signature(FakeTrace())
        assert sig["context_type"] == "business"
