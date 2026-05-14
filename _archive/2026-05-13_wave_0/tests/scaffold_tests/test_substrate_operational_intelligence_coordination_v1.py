"""Tests for Phase 96.8CA — Substrate Operational Intelligence Coordination.

Tests: contracts, lifecycle, synthesis, relevance arbitration,
routing, reasoning composition, context compression, awareness,
intent anchoring, observability, replay, boundary policies,
continuity bridges, canonical coordinator, constraint verification.
"""

from __future__ import annotations

import sys
import tempfile
import shutil

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from core.intelligence.operational_intelligence_contracts_v1 import (
    OperationalIntelligenceState,
    IntelligenceContextWindow,
    IntelligenceSynthesisState,
    RelevanceScore,
    OperationalFocusState,
    ContextPriorityState,
    IntelligenceRoutingState,
    IntelligenceCoordinationReceipt,
    OperationalReasoningState,
    ContextCompressionState,
    IntelligenceProjectionState,
    OperationalSignalCluster,
    IntentAnchorState,
    CognitiveConstraintState,
    OperationalAwarenessState,
    IntelligenceLifecycleState,
    IntelligenceEventType,
    RelevanceClass,
    SignalSource,
    ReasoningType,
    _now_iso,
    _new_id,
)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── Contract Tests ──────────────────────────────────────────────


class TestOperationalIntelligenceState:
    def test_defaults(self):
        s = OperationalIntelligenceState()
        assert s.state_id.startswith("oist-")
        assert s.lifecycle == "inactive"

    def test_to_dict(self):
        s = OperationalIntelligenceState()
        d = s.to_dict()
        assert "state_id" in d


class TestIntelligenceContextWindow:
    def test_defaults(self):
        w = IntelligenceContextWindow()
        assert w.window_id.startswith("ictx-")
        assert w.max_signals == 50

    def test_to_dict(self):
        w = IntelligenceContextWindow()
        d = w.to_dict()
        assert d["max_signals"] == 50


class TestIntelligenceSynthesisState:
    def test_defaults(self):
        s = IntelligenceSynthesisState()
        assert s.synthesis_id.startswith("isyn-")

    def test_to_dict(self):
        s = IntelligenceSynthesisState(sources=["ingress"])
        assert s.to_dict()["sources"] == ["ingress"]


class TestRelevanceScore:
    def test_defaults(self):
        r = RelevanceScore()
        assert r.score_id.startswith("rscore-")
        assert r.relevance_class == "standard"

    def test_to_dict(self):
        r = RelevanceScore(score=0.8)
        assert r.to_dict()["score"] == 0.8


class TestOperationalFocusState:
    def test_defaults(self):
        f = OperationalFocusState()
        assert f.focus_id.startswith("ofoc-")
        assert f.focus_source == "operator"


class TestContextPriorityState:
    def test_defaults(self):
        p = ContextPriorityState()
        assert p.priority_id.startswith("cpri-")
        assert p.set_by == "operator"


class TestIntelligenceRoutingState:
    def test_defaults(self):
        r = IntelligenceRoutingState()
        assert r.routing_id.startswith("iroute-")

    def test_to_dict(self):
        r = IntelligenceRoutingState(source_layer="ingress", target_layer="cognition")
        d = r.to_dict()
        assert d["source_layer"] == "ingress"


class TestIntelligenceCoordinationReceipt:
    def test_defaults(self):
        r = IntelligenceCoordinationReceipt()
        assert r.receipt_id.startswith("icrcpt-")

    def test_to_dict(self):
        r = IntelligenceCoordinationReceipt(operation="synthesize")
        assert r.to_dict()["operation"] == "synthesize"


class TestOperationalReasoningState:
    def test_defaults(self):
        r = OperationalReasoningState()
        assert r.reasoning_id.startswith("orsn-")
        assert r.set_by == "operator"

    def test_to_dict(self):
        r = OperationalReasoningState(conclusion="healthy")
        assert r.to_dict()["conclusion"] == "healthy"


class TestContextCompressionState:
    def test_defaults(self):
        c = ContextCompressionState()
        assert c.compression_id.startswith("ccomp-")

    def test_to_dict(self):
        c = ContextCompressionState(original_size=10, compressed_size=5)
        d = c.to_dict()
        assert d["original_size"] == 10


class TestIntelligenceProjectionState:
    def test_defaults(self):
        p = IntelligenceProjectionState()
        assert p.projection_id.startswith("iproj-")

    def test_to_dict(self):
        p = IntelligenceProjectionState(confidence=0.9)
        assert p.to_dict()["confidence"] == 0.9


class TestOperationalSignalCluster:
    def test_defaults(self):
        c = OperationalSignalCluster()
        assert c.cluster_id.startswith("osclust-")

    def test_to_dict(self):
        c = OperationalSignalCluster(source="resilience")
        assert c.to_dict()["source"] == "resilience"


class TestIntentAnchorState:
    def test_defaults(self):
        a = IntentAnchorState()
        assert a.anchor_id.startswith("ianch-")
        assert a.set_by == "operator"
        assert a.validated is False

    def test_to_dict(self):
        a = IntentAnchorState(operator_intent="test")
        assert a.to_dict()["operator_intent"] == "test"


class TestCognitiveConstraintState:
    def test_defaults(self):
        c = CognitiveConstraintState()
        assert c.constraint_id.startswith("ccnst-")
        assert c.within_bounds is True

    def test_to_dict(self):
        c = CognitiveConstraintState(max_context_window=100)
        assert c.to_dict()["max_context_window"] == 100


class TestOperationalAwarenessState:
    def test_defaults(self):
        a = OperationalAwarenessState()
        assert a.awareness_id.startswith("oaware-")
        assert a.replay_integrity is True

    def test_to_dict(self):
        a = OperationalAwarenessState(active_subsystems=["spine"])
        assert a.to_dict()["active_subsystems"] == ["spine"]


# ── Enum Tests ──────────────────────────────────────────────────


class TestEnums:
    def test_lifecycle_state_count(self):
        assert len(IntelligenceLifecycleState) == 11

    def test_event_type_count(self):
        assert len(IntelligenceEventType) == 10

    def test_relevance_class_count(self):
        assert len(RelevanceClass) == 5

    def test_signal_source_count(self):
        assert len(SignalSource) == 9

    def test_reasoning_type_count(self):
        assert len(ReasoningType) == 5


# ── Lifecycle Tests ─────────────────────────────────────────────


class TestIntelligenceLifecycleEngine:
    def test_initial_state(self, tmp_dir):
        from core.intelligence.intelligence_lifecycle_engine_v1 import (
            IntelligenceLifecycleEngine,
        )
        e = IntelligenceLifecycleEngine(state_dir=tmp_dir)
        assert e.current_state == "inactive"

    def test_valid_transition(self, tmp_dir):
        from core.intelligence.intelligence_lifecycle_engine_v1 import (
            IntelligenceLifecycleEngine,
        )
        e = IntelligenceLifecycleEngine(state_dir=tmp_dir)
        assert e.transition(IntelligenceLifecycleState.OBSERVING) is True
        assert e.current_state == "observing"

    def test_invalid_transition(self, tmp_dir):
        from core.intelligence.intelligence_lifecycle_engine_v1 import (
            IntelligenceLifecycleEngine,
        )
        e = IntelligenceLifecycleEngine(state_dir=tmp_dir)
        assert e.transition(IntelligenceLifecycleState.SYNTHESIZING) is False

    def test_full_pipeline(self, tmp_dir):
        from core.intelligence.intelligence_lifecycle_engine_v1 import (
            IntelligenceLifecycleEngine,
        )
        e = IntelligenceLifecycleEngine(state_dir=tmp_dir)
        assert e.transition(IntelligenceLifecycleState.OBSERVING)
        assert e.transition(IntelligenceLifecycleState.SYNTHESIZING)
        assert e.transition(IntelligenceLifecycleState.CONTEXTUALIZING)
        assert e.transition(IntelligenceLifecycleState.PRIORITIZING)
        assert e.transition(IntelligenceLifecycleState.COMPRESSING)
        assert e.transition(IntelligenceLifecycleState.PROJECTING)
        assert e.transition(IntelligenceLifecycleState.VALIDATING)
        assert e.transition(IntelligenceLifecycleState.OBSERVING)
        assert e.current_state == "observing"

    def test_terminal_state(self, tmp_dir):
        from core.intelligence.intelligence_lifecycle_engine_v1 import (
            IntelligenceLifecycleEngine,
        )
        e = IntelligenceLifecycleEngine(state_dir=tmp_dir)
        e.transition(IntelligenceLifecycleState.SUSPENDED)
        e.transition(IntelligenceLifecycleState.ARCHIVED)
        assert e.transition(IntelligenceLifecycleState.INACTIVE) is False

    def test_can_transition(self, tmp_dir):
        from core.intelligence.intelligence_lifecycle_engine_v1 import (
            IntelligenceLifecycleEngine,
        )
        e = IntelligenceLifecycleEngine(state_dir=tmp_dir)
        assert e.can_transition(IntelligenceLifecycleState.OBSERVING) is True
        assert e.can_transition(IntelligenceLifecycleState.PROJECTING) is False

    def test_stats(self, tmp_dir):
        from core.intelligence.intelligence_lifecycle_engine_v1 import (
            IntelligenceLifecycleEngine,
        )
        e = IntelligenceLifecycleEngine(state_dir=tmp_dir)
        e.transition(IntelligenceLifecycleState.OBSERVING)
        assert e.get_stats()["total_transitions"] == 1


# ── Synthesis Tests ─────────────────────────────────────────────


class TestIntelligenceSynthesisEngine:
    def test_synthesize(self, tmp_dir):
        from core.intelligence.intelligence_synthesis_engine_v1 import (
            IntelligenceSynthesisEngine,
        )
        e = IntelligenceSynthesisEngine(state_dir=tmp_dir)
        state = e.synthesize(
            {"ingress": [{"id": "s1"}], "resilience": [{"id": "s2"}]},
            operator_intent="test",
        )
        assert state.signal_count == 2
        assert "ingress" in state.sources
        assert state.operator_intent == "test"

    def test_synthesis_hash_deterministic(self, tmp_dir):
        from core.intelligence.intelligence_synthesis_engine_v1 import (
            IntelligenceSynthesisEngine,
        )
        e = IntelligenceSynthesisEngine(state_dir=tmp_dir)
        s1 = e.synthesize({"ingress": [{"id": "s1"}]}, "intent")
        s2 = e.synthesize({"ingress": [{"id": "s1"}]}, "intent")
        assert s1.synthesis_hash == s2.synthesis_hash

    def test_cluster_signals(self, tmp_dir):
        from core.intelligence.intelligence_synthesis_engine_v1 import (
            IntelligenceSynthesisEngine,
        )
        e = IntelligenceSynthesisEngine(state_dir=tmp_dir)
        cluster = e.cluster_signals(
            [{"id": "s1"}, {"id": "s2"}], source="resilience", cluster_type="pressure",
        )
        assert len(cluster.signal_ids) == 2

    def test_unknown_sources_filtered(self, tmp_dir):
        from core.intelligence.intelligence_synthesis_engine_v1 import (
            IntelligenceSynthesisEngine,
        )
        e = IntelligenceSynthesisEngine(state_dir=tmp_dir)
        state = e.synthesize({"unknown_source": [{"id": "s1"}]})
        assert state.signal_count == 0

    def test_get_latest(self, tmp_dir):
        from core.intelligence.intelligence_synthesis_engine_v1 import (
            IntelligenceSynthesisEngine,
        )
        e = IntelligenceSynthesisEngine(state_dir=tmp_dir)
        assert e.get_latest_synthesis() is None
        e.synthesize({"ingress": [{"id": "s1"}]})
        assert e.get_latest_synthesis() is not None

    def test_stats(self, tmp_dir):
        from core.intelligence.intelligence_synthesis_engine_v1 import (
            IntelligenceSynthesisEngine,
        )
        e = IntelligenceSynthesisEngine(state_dir=tmp_dir)
        e.synthesize({"ingress": [{"id": "s1"}]})
        assert e.get_stats()["total_syntheses"] == 1


# ── Relevance Tests ─────────────────────────────────────────────


class TestRelevanceArbitrationEngine:
    def test_score_signal(self, tmp_dir):
        from core.intelligence.operational_relevance_arbitration_engine_v1 import (
            OperationalRelevanceArbitrationEngine,
        )
        e = OperationalRelevanceArbitrationEngine(state_dir=tmp_dir)
        score = e.score_signal("s1", source="resilience", severity=0.8)
        assert score.score > 0.0
        assert score.relevance_class in ("critical", "high", "standard")

    def test_noise_suppression(self, tmp_dir):
        from core.intelligence.operational_relevance_arbitration_engine_v1 import (
            OperationalRelevanceArbitrationEngine,
        )
        e = OperationalRelevanceArbitrationEngine(state_dir=tmp_dir)
        score = e.score_signal("s1", source="observability", severity=0.0, recency=0.0)
        assert score.relevance_class in ("noise", "low")

    def test_focus_bonus(self, tmp_dir):
        from core.intelligence.operational_relevance_arbitration_engine_v1 import (
            OperationalRelevanceArbitrationEngine,
        )
        e = OperationalRelevanceArbitrationEngine(state_dir=tmp_dir)
        s1 = e.score_signal("s1", source="resilience", severity=0.5)
        s2 = e.score_signal("s2", source="resilience", severity=0.5,
                            operator_focus="resilience")
        assert s2.score > s1.score

    def test_priority_signals(self, tmp_dir):
        from core.intelligence.operational_relevance_arbitration_engine_v1 import (
            OperationalRelevanceArbitrationEngine,
        )
        e = OperationalRelevanceArbitrationEngine(state_dir=tmp_dir)
        e.score_signal("s1", source="resilience", severity=0.9)
        e.score_signal("s2", source="ingress", severity=0.3)
        top = e.get_priority_signals(1)
        assert top[0].signal_id == "s1"

    def test_set_focus(self, tmp_dir):
        from core.intelligence.operational_relevance_arbitration_engine_v1 import (
            OperationalRelevanceArbitrationEngine,
        )
        e = OperationalRelevanceArbitrationEngine(state_dir=tmp_dir)
        f = e.set_focus("scaling", set_by="operator")
        assert f.active_focus == "scaling"

    def test_build_priority_state(self, tmp_dir):
        from core.intelligence.operational_relevance_arbitration_engine_v1 import (
            OperationalRelevanceArbitrationEngine,
        )
        e = OperationalRelevanceArbitrationEngine(state_dir=tmp_dir)
        e.score_signal("s1", source="resilience", severity=0.8)
        ps = e.build_priority_state()
        assert ps.set_by == "operator"
        assert len(ps.ordered_signals) >= 1

    def test_stats(self, tmp_dir):
        from core.intelligence.operational_relevance_arbitration_engine_v1 import (
            OperationalRelevanceArbitrationEngine,
        )
        e = OperationalRelevanceArbitrationEngine(state_dir=tmp_dir)
        e.score_signal("s1", source="resilience", severity=0.5)
        assert e.get_stats()["total_scored"] == 1


# ── Routing Tests ───────────────────────────────────────────────


class TestIntelligenceRoutingEngine:
    def test_valid_route(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        r = e.route("ingress", "cognition", ["s1"])
        assert r is not None
        assert r.source_layer == "ingress"

    def test_self_route_denied(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        assert e.route("ingress", "ingress", ["s1"]) is None

    def test_unknown_layer_denied(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        assert e.route("unknown", "cognition", ["s1"]) is None

    def test_cycle_prevention(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        r = e.route("ingress", "cognition", ["s1"],
                     routing_chain=["ingress", "cognition"])
        assert r is None

    def test_max_depth_enforcement(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
            MAX_ROUTING_DEPTH,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        chain = ["a", "b", "c", "d", "e"][:MAX_ROUTING_DEPTH]
        r = e.route("ingress", "cognition", ["s1"], routing_chain=chain)
        assert r is None

    def test_fanout_bounded(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
            MAX_ROUTING_FANOUT,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        r = e.route("ingress", "cognition", [f"s{i}" for i in range(10)])
        assert len(r.signal_ids) == MAX_ROUTING_FANOUT

    def test_routing_hash_deterministic(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        r1 = e.route("ingress", "cognition", ["s1"])
        r2 = e.route("ingress", "cognition", ["s1"])
        assert r1.routing_hash == r2.routing_hash

    def test_get_routes(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        e.route("ingress", "cognition", ["s1"])
        assert len(e.get_routes_from("ingress")) == 1
        assert len(e.get_routes_to("cognition")) == 1

    def test_stats(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        e.route("ingress", "cognition", ["s1"])
        e.route("ingress", "ingress", ["s1"])
        stats = e.get_stats()
        assert stats["total_routes"] == 1
        assert stats["total_denied"] == 1


# ── Reasoning Tests ─────────────────────────────────────────────


class TestReasoningCompositionEngine:
    def test_compose(self, tmp_dir):
        from core.intelligence.operational_reasoning_composition_engine_v1 import (
            OperationalReasoningCompositionEngine,
        )
        e = OperationalReasoningCompositionEngine(state_dir=tmp_dir)
        r = e.compose("pressure_analysis", ["s1"], "moderate pressure", 0.7)
        assert r.reasoning_type == "pressure_analysis"
        assert r.set_by == "operator"

    def test_unknown_type_defaults(self, tmp_dir):
        from core.intelligence.operational_reasoning_composition_engine_v1 import (
            OperationalReasoningCompositionEngine,
        )
        e = OperationalReasoningCompositionEngine(state_dir=tmp_dir)
        r = e.compose("unknown_type", ["s1"], "test")
        assert r.reasoning_type == "operational_status"

    def test_confidence_bounded(self, tmp_dir):
        from core.intelligence.operational_reasoning_composition_engine_v1 import (
            OperationalReasoningCompositionEngine,
        )
        e = OperationalReasoningCompositionEngine(state_dir=tmp_dir)
        r = e.compose("pressure_analysis", [], "test", confidence=5.0)
        assert r.confidence == 1.0

    def test_get_by_type(self, tmp_dir):
        from core.intelligence.operational_reasoning_composition_engine_v1 import (
            OperationalReasoningCompositionEngine,
        )
        e = OperationalReasoningCompositionEngine(state_dir=tmp_dir)
        e.compose("pressure_analysis", [], "a")
        e.compose("risk_assessment", [], "b")
        assert len(e.get_by_type("pressure_analysis")) == 1

    def test_lineage(self, tmp_dir):
        from core.intelligence.operational_reasoning_composition_engine_v1 import (
            OperationalReasoningCompositionEngine,
        )
        e = OperationalReasoningCompositionEngine(state_dir=tmp_dir)
        e.compose("pressure_analysis", [], "a")
        lineage = e.get_lineage()
        assert len(lineage) == 1

    def test_stats(self, tmp_dir):
        from core.intelligence.operational_reasoning_composition_engine_v1 import (
            OperationalReasoningCompositionEngine,
        )
        e = OperationalReasoningCompositionEngine(state_dir=tmp_dir)
        e.compose("pressure_analysis", [], "test")
        assert e.get_stats()["total_compositions"] == 1


# ── Compression Tests ───────────────────────────────────────────


class TestContextCompressionEngine:
    def test_add_signal(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        assert e.add_signal({"id": "s1"}) is True

    def test_window_full(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
            MAX_CONTEXT_WINDOW,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        for i in range(MAX_CONTEXT_WINDOW):
            assert e.add_signal({"id": f"s{i}"}) is True
        assert e.add_signal({"id": "overflow"}) is False

    def test_compress(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        for i in range(10):
            e.add_signal({"id": f"s{i}"})
        state = e.compress({"s0": 0.9, "s1": 0.05, "s5": 0.8})
        assert state.original_size == 10
        assert state.discarded_signals >= 1

    def test_needs_compression(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
            MAX_CONTEXT_WINDOW,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        assert e.needs_compression() is False
        for i in range(int(MAX_CONTEXT_WINDOW * 0.85)):
            e.add_signal({"id": f"s{i}"})
        assert e.needs_compression() is True

    def test_compression_hash_deterministic(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        for i in range(5):
            e.add_signal({"id": f"s{i}"})
        s1 = e.compress()
        e.reset_window()
        for i in range(5):
            e.add_signal({"id": f"s{i}"})
        s2 = e.compress()
        assert s1.compression_hash == s2.compression_hash

    def test_reset_window(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        e.add_signal({"id": "s1"})
        e.reset_window()
        assert e.get_window().current_size == 0

    def test_stats(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        assert e.get_stats()["current_window_size"] == 0


# ── Awareness Tests ─────────────────────────────────────────────


class TestOperationalAwarenessEngine:
    def test_update_subsystems(self, tmp_dir):
        from core.intelligence.operational_awareness_engine_v1 import (
            OperationalAwarenessEngine,
        )
        e = OperationalAwarenessEngine(state_dir=tmp_dir)
        e.update_subsystems(["spine", "scaling"])
        aw = e.get_awareness()
        assert len(aw.active_subsystems) == 2

    def test_update_pressure(self, tmp_dir):
        from core.intelligence.operational_awareness_engine_v1 import (
            OperationalAwarenessEngine,
        )
        e = OperationalAwarenessEngine(state_dir=tmp_dir)
        e.update_pressure(["high_queue"])
        assert len(e.get_awareness().pressure_signals) == 1

    def test_update_risks(self, tmp_dir):
        from core.intelligence.operational_awareness_engine_v1 import (
            OperationalAwarenessEngine,
        )
        e = OperationalAwarenessEngine(state_dir=tmp_dir)
        e.update_continuity_risks(["session_gap"])
        assert "session_gap" in e.get_awareness().continuity_risks

    def test_project(self, tmp_dir):
        from core.intelligence.operational_awareness_engine_v1 import (
            OperationalAwarenessEngine,
        )
        e = OperationalAwarenessEngine(state_dir=tmp_dir)
        e.update_subsystems(["spine"])
        e.update_continuity_risks(["gap"])
        proj = e.project()
        assert proj.confidence < 1.0
        assert "gap" in proj.projected_risks

    def test_projection_confidence_degrades(self, tmp_dir):
        from core.intelligence.operational_awareness_engine_v1 import (
            OperationalAwarenessEngine,
        )
        e = OperationalAwarenessEngine(state_dir=tmp_dir)
        p1 = e.project()
        e.update_continuity_risks(["r1", "r2", "r3"])
        p2 = e.project()
        assert p2.confidence < p1.confidence

    def test_stats(self, tmp_dir):
        from core.intelligence.operational_awareness_engine_v1 import (
            OperationalAwarenessEngine,
        )
        e = OperationalAwarenessEngine(state_dir=tmp_dir)
        e.update_subsystems(["spine"])
        assert e.get_stats()["total_updates"] == 1


# ── Intent Anchoring Tests ──────────────────────────────────────


class TestIntentAnchoringEngine:
    def test_anchor(self, tmp_dir):
        from core.intelligence.intent_anchoring_engine_v1 import (
            IntentAnchoringEngine,
        )
        e = IntentAnchoringEngine(state_dir=tmp_dir)
        a = e.anchor("build initiate arena", set_by="operator")
        assert a.validated is True
        assert a.set_by == "operator"

    def test_non_operator_rejected(self, tmp_dir):
        from core.intelligence.intent_anchoring_engine_v1 import (
            IntentAnchoringEngine,
        )
        e = IntentAnchoringEngine(state_dir=tmp_dir)
        with pytest.raises(ValueError):
            e.anchor("test", set_by="substrate")

    def test_get_active_intent(self, tmp_dir):
        from core.intelligence.intent_anchoring_engine_v1 import (
            IntentAnchoringEngine,
        )
        e = IntentAnchoringEngine(state_dir=tmp_dir)
        e.anchor("build", set_by="operator")
        assert e.get_active_intent() == "build"

    def test_lineage_tracking(self, tmp_dir):
        from core.intelligence.intent_anchoring_engine_v1 import (
            IntentAnchoringEngine,
        )
        e = IntentAnchoringEngine(state_dir=tmp_dir)
        a1 = e.anchor("intent_1", set_by="operator")
        a2 = e.anchor("intent_2", set_by="operator")
        assert a1.anchor_id in a2.lineage

    def test_validate_against_intent(self, tmp_dir):
        from core.intelligence.intent_anchoring_engine_v1 import (
            IntentAnchoringEngine,
        )
        e = IntentAnchoringEngine(state_dir=tmp_dir)
        e.anchor("build", set_by="operator")
        assert e.validate_against_intent("some_action") is True

    def test_stats(self, tmp_dir):
        from core.intelligence.intent_anchoring_engine_v1 import (
            IntentAnchoringEngine,
        )
        e = IntentAnchoringEngine(state_dir=tmp_dir)
        e.anchor("test", set_by="operator")
        stats = e.get_stats()
        assert stats["total_anchors"] == 1


# ── Observability Tests ──────────────────────────────────────────


class TestIntelligenceObservabilityPipeline:
    def test_emit_all_event_types(self, tmp_dir):
        from core.intelligence.intelligence_observability_pipeline_v1 import (
            IntelligenceObservabilityPipeline,
        )
        p = IntelligenceObservabilityPipeline(state_dir=tmp_dir)
        p.emit_intelligence_synthesized()
        p.emit_relevance_scored()
        p.emit_context_compressed()
        p.emit_operational_awareness_updated()
        p.emit_intent_anchor_validated()
        p.emit_intelligence_route_created()
        p.emit_reasoning_composed()
        p.emit_intelligence_boundary_denied()
        p.emit_cognition_window_regulated()
        p.emit_operational_projection_updated()
        assert p.get_stats()["total_events"] == 10

    def test_event_file_map_dynamic(self):
        from core.intelligence.intelligence_observability_pipeline_v1 import (
            EVENT_FILE_MAP,
        )
        assert len(EVENT_FILE_MAP) == 10

    def test_stats_counts(self, tmp_dir):
        from core.intelligence.intelligence_observability_pipeline_v1 import (
            IntelligenceObservabilityPipeline,
        )
        p = IntelligenceObservabilityPipeline(state_dir=tmp_dir)
        p.emit_intelligence_synthesized()
        p.emit_intelligence_synthesized()
        assert p.get_stats()["event_counts"]["intelligence_synthesized"] == 2


# ── Replay Tests ─────────────────────────────────────────────────


class TestIntelligenceReplayValidator:
    def test_validate_all_checks(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
            REPLAY_CHECKS,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        inputs = {c: {"test": True} for c in REPLAY_CHECKS}
        outputs = {c: {"result": True} for c in REPLAY_CHECKS}
        results = v.run_all_checks(inputs, outputs)
        assert len(results) == 6
        assert all(r.deterministic for r in results)

    def test_individual_check(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        r = v.validate_synthesis({"a": 1}, {"b": 2})
        assert r.deterministic is True
        assert r.check_name == "synthesis"

    def test_hash_stability(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        r1 = v.validate_relevance_scoring({"x": 1}, {"y": 2})
        r2 = v.validate_relevance_scoring({"x": 1}, {"y": 2})
        assert r1.input_hash == r2.input_hash
        assert r1.output_hash == r2.output_hash

    def test_all_six_methods(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        v.validate_synthesis({}, {})
        v.validate_relevance_scoring({}, {})
        v.validate_intelligence_routing({}, {})
        v.validate_reasoning_composition({}, {})
        v.validate_context_compression({}, {})
        v.validate_awareness_projection({}, {})
        assert v.get_stats()["total_validations"] == 6

    def test_stats(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        v.validate_synthesis({}, {})
        stats = v.get_stats()
        assert stats["total_passes"] == 1


# ── Boundary Policy Tests ────────────────────────────────────────


class TestIntelligenceBoundaryPolicies:
    def test_limits_count(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            INTELLIGENCE_LIMITS,
        )
        assert len(INTELLIGENCE_LIMITS) == 10

    def test_forbidden_count(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            FORBIDDEN_INTELLIGENCE_ACTIONS,
        )
        assert len(FORBIDDEN_INTELLIGENCE_ACTIONS) == 10

    def test_enforce_context_window(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            enforce_context_window,
        )
        assert enforce_context_window(50) is True
        assert enforce_context_window(51) is False

    def test_enforce_reasoning_depth(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            enforce_reasoning_depth,
        )
        assert enforce_reasoning_depth(5) is True
        assert enforce_reasoning_depth(6) is False

    def test_enforce_routing_depth(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            enforce_routing_depth,
        )
        assert enforce_routing_depth(5) is True
        assert enforce_routing_depth(6) is False

    def test_enforce_routing_fanout(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            enforce_routing_fanout,
        )
        assert enforce_routing_fanout(3) is True
        assert enforce_routing_fanout(4) is False

    def test_cap_override(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            cap_override,
        )
        assert cap_override(10, 5) == 5
        assert cap_override(3, 5) == 3

    def test_is_forbidden(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("autonomous_reasoning") is True
        assert is_forbidden("legitimate_action") is False

    def test_get_all(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            get_all_limits,
            get_all_forbidden,
        )
        assert len(get_all_limits()) == 10
        assert len(get_all_forbidden()) == 10


# ── Continuity Bridge Tests ──────────────────────────────────────


class TestIntelligenceContinuityBridges:
    def test_cognition_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            CognitionIntelligenceBridge,
        )
        b = CognitionIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(focus="test")
        assert r["bridge_type"] == "cognition_intelligence"

    def test_workflows_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            WorkflowsIntelligenceBridge,
        )
        b = WorkflowsIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(workflow_id="wf1")
        assert r["bridge_type"] == "workflows_intelligence"

    def test_operations_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            OperationsIntelligenceBridge,
        )
        b = OperationsIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(campaign_id="c1")
        assert r["bridge_type"] == "operations_intelligence"

    def test_resilience_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            ResilienceIntelligenceBridge,
        )
        b = ResilienceIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(instability_score=0.3)
        assert r["bridge_type"] == "resilience_intelligence"

    def test_environments_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            EnvironmentsIntelligenceBridge,
        )
        b = EnvironmentsIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(environment_id="vps")
        assert r["bridge_type"] == "environments_intelligence"

    def test_scaling_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            ScalingIntelligenceBridge,
        )
        b = ScalingIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(pressure_score=0.5)
        assert r["bridge_type"] == "scaling_intelligence"

    def test_sessions_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            SessionsIntelligenceBridge,
        )
        b = SessionsIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(session_id="s1")
        assert r["bridge_type"] == "sessions_intelligence"

    def test_replay_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            ReplayIntelligenceBridge,
        )
        b = ReplayIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(total_validations=5)
        assert r["bridge_type"] == "replay_intelligence"

    def test_observability_bridge(self, tmp_dir):
        from core.intelligence.intelligence_continuity_bridges_v1 import (
            ObservabilityIntelligenceBridge,
        )
        b = ObservabilityIntelligenceBridge(state_dir=tmp_dir)
        r = b.capture(total_events=10)
        assert r["bridge_type"] == "observability_intelligence"


# ── Coordinator Tests ────────────────────────────────────────────


class TestCanonicalOperationalIntelligenceCoordinator:
    def test_anchor_intent(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        a = c.anchor_intent("build initiate arena")
        assert a["validated"] is True
        assert a["set_by"] == "operator"

    def test_synthesize(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        syn = c.synthesize(
            {"ingress": [{"id": "s1"}], "resilience": [{"id": "s2"}]},
            operator_intent="test",
        )
        assert syn["signal_count"] == 2

    def test_score_relevance(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        score = c.score_relevance("s1", source="resilience", severity=0.8)
        assert score["score"] > 0

    def test_route_intelligence(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        r = c.route_intelligence("ingress", "cognition", ["s1"])
        assert r is not None
        assert r["routing_hash"] != ""

    def test_route_denied(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        assert c.route_intelligence("ingress", "ingress", ["s1"]) is None

    def test_compose_reasoning(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        r = c.compose_reasoning("pressure_analysis", ["s1"], "moderate", 0.7)
        assert r["set_by"] == "operator"

    def test_context_and_compress(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        for i in range(10):
            c.add_context_signal({"id": f"s{i}"})
        comp = c.compress_context({"s0": 0.9, "s1": 0.05})
        assert comp["original_size"] == 10

    def test_update_awareness(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        aw = c.update_awareness(subsystems=["spine", "scaling"])
        assert len(aw["active_subsystems"]) == 2

    def test_project(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        c.update_awareness(risks=["gap"])
        proj = c.project()
        assert "projected_risks" in proj

    def test_set_focus(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        f = c.set_focus("resilience")
        assert f["active_focus"] == "resilience"

    def test_get_health(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        h = c.get_health()
        assert h["lifecycle_state"] == "inactive"

    def test_get_stats(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        stats = c.get_stats()
        assert "lifecycle" in stats
        assert "synthesis" in stats
        assert "relevance" in stats
        assert "routing" in stats
        assert "reasoning" in stats
        assert "compression" in stats
        assert "awareness" in stats
        assert "intent" in stats
        assert "observability" in stats

    def test_receipts(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        c.synthesize({"ingress": [{"id": "s1"}]})
        receipts = c.get_recent_receipts()
        assert len(receipts) >= 1

    def test_get_context_window(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        w = c.get_context_window()
        assert w["max_signals"] == 50

    def test_get_reasoning_lineage(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        c.compose_reasoning("pressure_analysis", [], "test")
        assert len(c.get_reasoning_lineage()) == 1

    def test_get_intent_lineage(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        c.anchor_intent("build")
        assert len(c.get_intent_lineage()) == 1


# ── Constraint Verification Tests ────────────────────────────────


class TestConstraintVerification:
    def test_no_autonomous_reasoning(self):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator.__new__(
            CanonicalOperationalIntelligenceCoordinator,
        )
        for attr in ["auto_reason", "self_reason", "autonomous_think"]:
            assert not hasattr(c, attr)

    def test_no_self_authored_goals(self):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator.__new__(
            CanonicalOperationalIntelligenceCoordinator,
        )
        for attr in ["create_objective", "set_goal", "generate_goal",
                      "create_goal", "self_direct"]:
            assert not hasattr(c, attr)

    def test_no_hidden_planning(self):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator.__new__(
            CanonicalOperationalIntelligenceCoordinator,
        )
        for attr in ["auto_plan", "hidden_plan", "internal_plan"]:
            assert not hasattr(c, attr)

    def test_no_recursive_cognition_loops(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        r = e.route("ingress", "cognition", ["s1"],
                     routing_chain=["ingress", "cognition"])
        assert r is None

    def test_no_uncontrolled_context_expansion(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
            MAX_CONTEXT_WINDOW,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        for i in range(MAX_CONTEXT_WINDOW):
            e.add_signal({"id": f"s{i}"})
        assert e.add_signal({"id": "overflow"}) is False

    def test_deterministic_synthesis_replay(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        inp = {"sources": ["ingress"], "count": 5}
        out = {"hash": "abc123"}
        r1 = v.validate_synthesis(inp, out)
        r2 = v.validate_synthesis(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_deterministic_routing_replay(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        inp = {"source": "ingress", "target": "cognition"}
        out = {"routed": True}
        r1 = v.validate_intelligence_routing(inp, out)
        r2 = v.validate_intelligence_routing(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_deterministic_reasoning_replay(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        inp = {"type": "pressure", "inputs": ["s1"]}
        out = {"conclusion": "moderate"}
        r1 = v.validate_reasoning_composition(inp, out)
        r2 = v.validate_reasoning_composition(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_deterministic_relevance_replay(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        inp = {"signal": "s1", "source": "resilience"}
        out = {"score": 0.8}
        r1 = v.validate_relevance_scoring(inp, out)
        r2 = v.validate_relevance_scoring(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_deterministic_compression_replay(self, tmp_dir):
        from core.intelligence.intelligence_replay_validator_v1 import (
            IntelligenceReplayValidator,
        )
        v = IntelligenceReplayValidator(state_dir=tmp_dir)
        inp = {"size": 10, "threshold": 0.2}
        out = {"compressed": 8}
        r1 = v.validate_context_compression(inp, out)
        r2 = v.validate_context_compression(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_operator_intent_anchoring(self, tmp_dir):
        from core.intelligence.intent_anchoring_engine_v1 import (
            IntentAnchoringEngine,
        )
        e = IntentAnchoringEngine(state_dir=tmp_dir)
        with pytest.raises(ValueError):
            e.anchor("self-directed goal", set_by="substrate")

    def test_no_cognition_owned_execution(self):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator.__new__(
            CanonicalOperationalIntelligenceCoordinator,
        )
        for attr in ["execute", "dispatch", "run_command", "invoke",
                      "run_workflow"]:
            assert not hasattr(c, attr)

    def test_no_hidden_prioritization_mutation(self, tmp_dir):
        from core.intelligence.operational_relevance_arbitration_engine_v1 import (
            OperationalRelevanceArbitrationEngine,
        )
        e = OperationalRelevanceArbitrationEngine(state_dir=tmp_dir)
        ps = e.build_priority_state(set_by="operator")
        assert ps.set_by == "operator"

    def test_no_governance_bypass(self):
        from core.intelligence.intelligence_boundary_policies_v1 import (
            FORBIDDEN_INTELLIGENCE_ACTIONS,
            is_forbidden,
        )
        for action in FORBIDDEN_INTELLIGENCE_ACTIONS:
            assert is_forbidden(action) is True

    def test_no_execution_outside_spine(self):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator.__new__(
            CanonicalOperationalIntelligenceCoordinator,
        )
        for attr in ["execute", "run_command", "dispatch", "invoke"]:
            assert not hasattr(c, attr)

    def test_no_hidden_intelligence_state(self, tmp_dir):
        from core.intelligence.canonical_operational_intelligence_coordinator_v1 import (
            CanonicalOperationalIntelligenceCoordinator,
        )
        c = CanonicalOperationalIntelligenceCoordinator(state_dir=tmp_dir)
        stats = c.get_stats()
        assert len(stats) == 9

    def test_bounded_cognition_windows(self, tmp_dir):
        from core.intelligence.context_compression_engine_v1 import (
            ContextCompressionEngine,
            MAX_CONTEXT_WINDOW,
        )
        e = ContextCompressionEngine(state_dir=tmp_dir)
        assert e.get_window().max_signals == MAX_CONTEXT_WINDOW

    def test_bounded_signal_clustering(self, tmp_dir):
        from core.intelligence.intelligence_synthesis_engine_v1 import (
            IntelligenceSynthesisEngine,
            MAX_CLUSTERS,
        )
        e = IntelligenceSynthesisEngine(state_dir=tmp_dir)
        for i in range(MAX_CLUSTERS + 5):
            e.cluster_signals([{"id": f"s{i}"}], source="test")
        assert len(e.get_clusters()) <= MAX_CLUSTERS

    def test_bounded_reasoning_composition(self, tmp_dir):
        from core.intelligence.operational_reasoning_composition_engine_v1 import (
            OperationalReasoningCompositionEngine,
            MAX_REASONING_DEPTH,
        )
        e = OperationalReasoningCompositionEngine(state_dir=tmp_dir)
        r = e.compose("pressure_analysis",
                       [f"i{i}" for i in range(20)], "test")
        assert len(r.inputs) <= MAX_REASONING_DEPTH

    def test_replay_safe_traversal(self, tmp_dir):
        from core.intelligence.intelligence_routing_engine_v1 import (
            IntelligenceRoutingEngine,
        )
        e = IntelligenceRoutingEngine(state_dir=tmp_dir)
        r1 = e.route("ingress", "cognition", ["s1"])
        r2 = e.route("ingress", "cognition", ["s1"])
        assert r1.routing_hash == r2.routing_hash
