"""Tests for SessionInterface — deterministic outputs, correct flow, explanations, state tracking."""

import sys
import types
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.session_interface import (
    DecisionOutput,
    Explanation,
    InterfaceState,
    LayerContribution,
    SessionInterface,
    _build_explanation,
    _compute_risk_score,
)


# ─── Fixtures ─────────────────────────────────────────────────────


def _make_trace(**overrides):
    """Build a mock DecisionTrace with sensible defaults."""
    defaults = {
        "turn_id": 1,
        "strategies_considered": ("balanced", "aggressive"),
        "strategy_scores": {"balanced": 0.8, "aggressive": 0.6},
        "selected_strategy": "balanced",
        "quality_score": 0.75,
        "confidence": 0.82,
        "signals": {},
        "attributed_signals": {},
        "horizon": {},
        "directives_applied": (),
        "model_used": "gemini/gemini-2.5-flash",
        "latency_ms": 250,
        "tokens_used": {"input": 100, "output": 200, "total": 300},
        "was_enhanced": False,
        "control_decision": None,
        "meta_control_mode": "adaptive",
        "meta_control_agreement": 0.85,
        "meta_control_instability": 0.12,
        "meta_control_permissions": {
            "allow_strategy_memory": False,
            "allow_dynamic_adaptation": True,
        },
        "blended_goals": None,
        "blended_primary_goal_id": None,
        "blended_entropy": None,
        "exploration_rate": None,
        "exploration_reason": None,
        "final_influence_score": None,
        "simulated_best_action_id": None,
        "simulated_best_improvement": None,
        "calibration_confidence": None,
    }
    defaults.update(overrides)
    trace = types.SimpleNamespace(**defaults)
    return trace


def _make_control_decision(intervene=False, reason="no_intervention"):
    return types.SimpleNamespace(intervene=intervene, reason=reason)


def _make_spine_result(
    text="Test response", model="gemini/gemini-2.5-flash", latency=250
):
    result = MagicMock()
    result.__str__ = lambda self: text
    result.model_used = model
    result.latency_ms = latency
    result.tokens_used = {"input": 100, "output": 200, "total": 300}
    result.cost_usd = 0.001
    return result


# ─── Test: Explanation builder ──────��─────────────────────────────


class TestBuildExplanation:
    def test_no_trace_returns_fallback(self):
        expl = _build_explanation(None, None, None)
        assert "No trace available" in expl.summary
        assert expl.contributing_layers == ()
        assert expl.confidence_rationale == "unknown"

    def test_strategy_selection_layer(self):
        trace = _make_trace()
        expl = _build_explanation(trace, None, None)
        layer_names = [lc.layer_name for lc in expl.contributing_layers]
        assert "strategy_selection" in layer_names
        strat_layer = next(
            lc
            for lc in expl.contributing_layers
            if lc.layer_name == "strategy_selection"
        )
        assert "balanced" in strat_layer.detail
        assert strat_layer.influence == 0.8

    def test_control_layer_no_intervention(self):
        trace = _make_trace()
        ctrl = _make_control_decision(intervene=False, reason="stable")
        expl = _build_explanation(trace, None, ctrl)
        layer_names = [lc.layer_name for lc in expl.contributing_layers]
        assert "control_layer" in layer_names
        ctrl_layer = next(
            lc for lc in expl.contributing_layers if lc.layer_name == "control_layer"
        )
        assert ctrl_layer.influence == 0.0
        assert "No intervention" in ctrl_layer.detail

    def test_control_layer_intervention(self):
        trace = _make_trace()
        ctrl = _make_control_decision(intervene=True, reason="low_quality_streak")
        expl = _build_explanation(trace, None, ctrl)
        ctrl_layer = next(
            lc for lc in expl.contributing_layers if lc.layer_name == "control_layer"
        )
        assert ctrl_layer.influence == 1.0
        assert "Intervened" in ctrl_layer.detail

    def test_goal_blending_layer(self):
        trace = _make_trace(
            blended_goals=(("goal_a", 0.7), ("goal_b", 0.3)),
            blended_primary_goal_id="goal_a",
            blended_entropy=0.45,
        )
        expl = _build_explanation(trace, None, None)
        layer_names = [lc.layer_name for lc in expl.contributing_layers]
        assert "goal_blending" in layer_names
        goal_layer = next(
            lc for lc in expl.contributing_layers if lc.layer_name == "goal_blending"
        )
        assert "goal_a" in goal_layer.detail
        assert goal_layer.influence == 0.45

    def test_exploration_layer(self):
        trace = _make_trace(exploration_rate=0.15, exploration_reason="high entropy")
        expl = _build_explanation(trace, None, None)
        layer_names = [lc.layer_name for lc in expl.contributing_layers]
        assert "exploration" in layer_names

    def test_meta_control_layer(self):
        trace = _make_trace(meta_control_mode="minimal", meta_control_agreement=0.4)
        expl = _build_explanation(trace, None, None)
        layer_names = [lc.layer_name for lc in expl.contributing_layers]
        assert "meta_control" in layer_names

    def test_summary_includes_strategy_and_mode(self):
        trace = _make_trace()
        expl = _build_explanation(trace, None, None)
        assert "balanced" in expl.summary
        assert "adaptive" in expl.summary

    def test_confidence_rationale(self):
        trace = _make_trace(confidence=0.9, calibration_confidence=0.85)
        expl = _build_explanation(trace, None, None)
        assert "0.90" in expl.confidence_rationale or "0.9" in expl.confidence_rationale
        assert "Calibrated" in expl.confidence_rationale

    def test_to_dict_roundtrip(self):
        trace = _make_trace()
        expl = _build_explanation(trace, None, None)
        d = expl.to_dict()
        assert isinstance(d["summary"], str)
        assert isinstance(d["contributing_layers"], list)
        assert isinstance(d["confidence_rationale"], str)
        assert isinstance(d["risk_rationale"], str)


# ─── Test: Risk score computation ─────────────────────────────────


class TestComputeRiskScore:
    def test_high_confidence_low_risk(self):
        trace = _make_trace(
            confidence=0.95, meta_control_instability=0.05, quality_score=0.9
        )
        risk = _compute_risk_score(trace)
        assert risk < 0.15

    def test_low_confidence_high_risk(self):
        trace = _make_trace(
            confidence=0.2, meta_control_instability=0.8, quality_score=0.3
        )
        risk = _compute_risk_score(trace)
        assert risk > 0.6

    def test_risk_clamped_0_to_1(self):
        trace = _make_trace(
            confidence=1.0, meta_control_instability=0.0, quality_score=1.0
        )
        assert _compute_risk_score(trace) == 0.0

        trace2 = _make_trace(
            confidence=0.0, meta_control_instability=1.0, quality_score=0.0
        )
        assert _compute_risk_score(trace2) == 1.0

    def test_deterministic(self):
        trace = _make_trace(
            confidence=0.6, meta_control_instability=0.3, quality_score=0.7
        )
        r1 = _compute_risk_score(trace)
        r2 = _compute_risk_score(trace)
        assert r1 == r2


# ─── Test: Data types ──��──────────────────────────────────────────


class TestDataTypes:
    def test_layer_contribution_to_dict(self):
        lc = LayerContribution(layer_name="test", influence=0.55555, detail="detail")
        d = lc.to_dict()
        assert d["layer_name"] == "test"
        assert d["influence"] == round(0.55555, 4)
        assert d["detail"] == "detail"

    def test_decision_output_to_dict(self):
        expl = Explanation(
            summary="test",
            contributing_layers=(),
            confidence_rationale="high",
            risk_rationale="low",
        )
        output = DecisionOutput(
            action="do something",
            confidence=0.88,
            risk_score=0.12,
            explanation=expl,
            contributing_layers=("strategy_selection",),
            turn_id=1,
            model_used="test",
            latency_ms=100,
        )
        d = output.to_dict()
        assert d["action"] == "do something"
        assert d["confidence"] == 0.88
        assert d["risk_score"] == 0.12
        assert d["turn_id"] == 1
        assert isinstance(d["explanation"], dict)
        assert d["contributing_layers"] == ["strategy_selection"]

    def test_interface_state_to_dict(self):
        state = InterfaceState(
            mode="adaptive",
            policy_flags={"allow_strategy_memory": True},
            stability_score=0.88,
            intent_weights={"reward": 0.5, "risk": 0.3},
            turn_count=5,
            session_id="test-123",
            total_cost_usd=0.025,
        )
        d = state.to_dict()
        assert d["mode"] == "adaptive"
        assert d["stability_score"] == 0.88
        assert d["turn_count"] == 5
        assert "reward" in d["intent_weights"]

    def test_decision_output_is_frozen(self):
        expl = Explanation(
            summary="x",
            contributing_layers=(),
            confidence_rationale="",
            risk_rationale="",
        )
        output = DecisionOutput(
            action="a",
            confidence=0.5,
            risk_score=0.5,
            explanation=expl,
            contributing_layers=(),
            turn_id=1,
            model_used="x",
            latency_ms=0,
        )
        try:
            output.action = "modified"
            assert False, "Should not allow mutation"
        except AttributeError:
            pass


# ─── Test: SessionInterface (unit, mocked) ────────────────────────


class TestSessionInterfaceUnit:
    def _make_interface(self):
        """Build a SessionInterface with mocked internals."""
        iface = SessionInterface.__new__(SessionInterface)
        iface._session_id = "test-session"
        iface._ctx = MagicMock()
        iface._ctx.org_id = "org-123"
        iface._decisions = []
        iface._intent = None
        iface._control_enabled = True
        iface._calibration_enabled = True
        iface._convergence_enabled = True
        iface._persist_memory = False

        # Mock runtime
        runtime = MagicMock()
        runtime.stats = MagicMock()
        runtime.stats.turns = 0
        runtime.stats.total_cost_usd = 0.0
        runtime.stats.decision_traces = []
        runtime.set_intent = MagicMock(return_value=None)
        runtime.get_calibrated_thresholds = MagicMock(return_value=None)
        runtime.get_last_trace = MagicMock(return_value=None)
        runtime.get_last_control_decision = MagicMock(return_value=None)
        runtime._compiled_intent = None

        # Mock builder
        builder = MagicMock()
        builder.build = MagicMock(return_value=MagicMock())

        iface._runtime = runtime
        iface._builder = builder
        return iface

    def test_get_state_before_step(self):
        iface = self._make_interface()
        state = iface.get_state()
        assert state.mode == "full"
        assert state.turn_count == 0
        assert state.stability_score == 1.0
        assert state.session_id == "test-session"

    def test_get_state_uninitialized(self):
        iface = SessionInterface.__new__(SessionInterface)
        iface._session_id = "uninit"
        iface._ctx = None
        iface._decisions = []
        iface._intent = None
        iface._runtime = None
        iface._builder = None
        iface._control_enabled = True
        iface._calibration_enabled = True
        iface._convergence_enabled = True
        iface._persist_memory = False

        state = iface.get_state()
        assert state.mode == "uninitialized"

    def test_get_last_decision_none_before_step(self):
        iface = self._make_interface()
        assert iface.get_last_decision() is None

    def test_step_returns_decision_output(self):
        iface = self._make_interface()

        # Configure mock to return a spine result
        spine_result = _make_spine_result("Action: focus on outreach")
        iface._runtime.run = MagicMock(return_value=spine_result)
        iface._runtime.stats.turns = 1

        trace = _make_trace()
        iface._runtime.get_last_trace = MagicMock(return_value=trace)

        output = iface.step("What should I focus on?")

        assert isinstance(output, DecisionOutput)
        assert "focus on outreach" in output.action
        assert output.confidence == 0.82
        assert output.turn_id == 1
        assert isinstance(output.explanation, Explanation)
        assert len(output.contributing_layers) > 0

    def test_step_accumulates_decisions(self):
        iface = self._make_interface()
        spine_result = _make_spine_result("Response")
        iface._runtime.run = MagicMock(return_value=spine_result)
        iface._runtime.stats.turns = 1

        trace = _make_trace()
        iface._runtime.get_last_trace = MagicMock(return_value=trace)

        iface.step("msg 1")
        iface._runtime.stats.turns = 2
        iface.step("msg 2")

        assert len(iface._decisions) == 2
        last = iface.get_last_decision()
        assert last is iface._decisions[-1]

    def test_set_intent_delegates_to_runtime(self):
        iface = self._make_interface()
        intent = MagicMock()
        iface.set_intent(intent)
        iface._runtime.set_intent.assert_called_once_with(intent)

    def test_reset_clears_decisions(self):
        iface = self._make_interface()

        # Add a fake decision
        expl = Explanation(
            summary="x",
            contributing_layers=(),
            confidence_rationale="",
            risk_rationale="",
        )
        iface._decisions.append(
            DecisionOutput(
                action="a",
                confidence=0.5,
                risk_score=0.5,
                explanation=expl,
                contributing_layers=(),
                turn_id=1,
                model_used="x",
                latency_ms=0,
            )
        )
        assert len(iface._decisions) == 1

        iface.reset()
        assert len(iface._decisions) == 0
        assert iface._intent is None

    def test_step_with_control_intervention(self):
        iface = self._make_interface()
        spine_result = _make_spine_result("Controlled response")
        iface._runtime.run = MagicMock(return_value=spine_result)
        iface._runtime.stats.turns = 1

        trace = _make_trace(
            confidence=0.3, meta_control_instability=0.7, quality_score=0.4
        )
        ctrl = _make_control_decision(intervene=True, reason="quality_streak")
        iface._runtime.get_last_trace = MagicMock(return_value=trace)
        iface._runtime.get_last_control_decision = MagicMock(return_value=ctrl)

        output = iface.step("test")
        assert output.risk_score > 0.5
        assert "control_layer" in output.contributing_layers

    def test_step_with_goal_blending(self):
        iface = self._make_interface()
        spine_result = _make_spine_result("Goal-blended response")
        iface._runtime.run = MagicMock(return_value=spine_result)
        iface._runtime.stats.turns = 1

        trace = _make_trace(
            blended_goals=(("revenue", 0.6), ("stability", 0.4)),
            blended_primary_goal_id="revenue",
            blended_entropy=0.5,
        )
        iface._runtime.get_last_trace = MagicMock(return_value=trace)

        output = iface.step("growth question")
        assert "goal_blending" in output.contributing_layers

    def test_get_state_reflects_meta_control_mode(self):
        iface = self._make_interface()
        trace = _make_trace(meta_control_mode="minimal", meta_control_instability=0.6)
        iface._runtime.get_last_trace = MagicMock(return_value=trace)

        state = iface.get_state()
        assert state.mode == "minimal"
        assert state.stability_score == 0.4

    def test_get_state_reflects_intent_weights(self):
        iface = self._make_interface()
        compiled = types.SimpleNamespace(
            objective_weights={"reward": 0.6, "risk": 0.2, "stability": 0.2}
        )
        iface._runtime._compiled_intent = compiled

        state = iface.get_state()
        assert state.intent_weights["reward"] == 0.6


# ─── Test: Determinism ──────────���─────────────────────────────────


class TestDeterminism:
    def test_same_inputs_same_output(self):
        """The explanation builder is deterministic for identical traces."""
        trace = _make_trace()
        ctrl = _make_control_decision()
        e1 = _build_explanation(trace, None, ctrl)
        e2 = _build_explanation(trace, None, ctrl)
        assert e1.summary == e2.summary
        assert e1.contributing_layers == e2.contributing_layers
        assert e1.confidence_rationale == e2.confidence_rationale
        assert e1.risk_rationale == e2.risk_rationale

    def test_risk_score_deterministic_across_calls(self):
        trace = _make_trace(
            confidence=0.7, meta_control_instability=0.2, quality_score=0.8
        )
        scores = [_compute_risk_score(trace) for _ in range(100)]
        assert len(set(scores)) == 1


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
