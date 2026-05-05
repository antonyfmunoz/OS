"""Tests for eos_ai.meta_control — governance layer for intelligence subsystem activation."""

import sys

sys.path.insert(0, "/opt/OS")

from dataclasses import dataclass

from umh.runtime_engine.meta_control import (
    ADAPTIVE_PERMISSIONS,
    FULL_PERMISSIONS,
    HIGH_AGREEMENT_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    HIGH_INSTABILITY_THRESHOLD,
    LOW_AGREEMENT_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    LOW_INSTABILITY_THRESHOLD,
    MAX_LOOKBACK_TURNS,
    MINIMAL_PERMISSIONS,
    NO_CONTROL_STATE,
    LayerPermissions,
    MetaControlState,
    compute_agreement_score,
    compute_confidence_level,
    compute_instability_score,
    compute_meta_control,
    permissions_for_mode,
    select_mode,
)


# ─── Helper: mock trace objects ───────────────────────────────


@dataclass
class MockTrace:
    """Lightweight trace stand-in with optional fields."""

    quality_score: float | None = None
    confidence: float | None = None
    calibration_confidence: float | None = None
    planner_confidence: float | None = None
    objective_arb_reward_weight: float | None = None
    strat_pattern_confidence: float | None = None
    context_type: str | None = None
    calibration_error: float | None = None


# ═══════════════════════════════════════════════════════════════
# 1. LayerPermissions data model
# ═══════════════════════════════════════════════════════════════


class TestLayerPermissions:
    def test_minimal_all_off(self):
        assert MINIMAL_PERMISSIONS.enabled_count() == 0
        assert MINIMAL_PERMISSIONS.enabled_names() == ()

    def test_adaptive_one_on(self):
        assert ADAPTIVE_PERMISSIONS.enabled_count() == 1
        assert ADAPTIVE_PERMISSIONS.enabled_names() == ("dynamic_adaptation",)

    def test_full_all_on(self):
        assert FULL_PERMISSIONS.enabled_count() == 5
        names = FULL_PERMISSIONS.enabled_names()
        assert "strategy_memory" in names
        assert "foresight" in names
        assert "planner_override" in names
        assert "dynamic_adaptation" in names
        assert "exploration_boost" in names

    def test_to_dict(self):
        d = MINIMAL_PERMISSIONS.to_dict()
        assert d["allow_strategy_memory"] is False
        assert d["allow_foresight"] is False
        assert d["allow_dynamic_adaptation"] is False

    def test_frozen(self):
        try:
            FULL_PERMISSIONS.allow_foresight = False  # type: ignore[misc]
            assert False, "Should not be mutable"
        except AttributeError:
            pass


# ═══════════════════════════════════════════════════════════════
# 2. MetaControlState data model
# ═══════════════════════════════════════════════════════════════


class TestMetaControlState:
    def test_no_control_state_defaults(self):
        assert NO_CONTROL_STATE.mode == "full"
        assert NO_CONTROL_STATE.confidence_level == 1.0
        assert NO_CONTROL_STATE.instability_score == 0.0
        assert NO_CONTROL_STATE.agreement_score == 1.0
        assert NO_CONTROL_STATE.permissions == FULL_PERMISSIONS

    def test_to_dict(self):
        d = NO_CONTROL_STATE.to_dict()
        assert d["mode"] == "full"
        assert d["enabled_count"] == 5
        assert "permissions" in d

    def test_frozen(self):
        try:
            NO_CONTROL_STATE.mode = "minimal"  # type: ignore[misc]
            assert False, "Should not be mutable"
        except AttributeError:
            pass


# ═══════════════════════════════════════════════════════════════
# 3. Agreement score computation
# ═══════════════════════════════════════════════════════════════


class TestAgreementScore:
    def test_empty_traces(self):
        assert compute_agreement_score([]) == 1.0

    def test_single_trace_single_signal(self):
        t = MockTrace(quality_score=0.8)
        assert compute_agreement_score([t]) == 1.0

    def test_perfect_agreement(self):
        traces = [MockTrace(quality_score=0.5, confidence=0.5) for _ in range(3)]
        score = compute_agreement_score(traces)
        assert score == 1.0

    def test_high_disagreement(self):
        traces = [
            MockTrace(quality_score=0.0, confidence=1.0),
            MockTrace(quality_score=1.0, confidence=0.0),
        ]
        score = compute_agreement_score(traces)
        assert score < 0.8

    def test_moderate_disagreement(self):
        traces = [
            MockTrace(quality_score=0.4, confidence=0.5),
            MockTrace(quality_score=0.6, confidence=0.5),
        ]
        score = compute_agreement_score(traces)
        assert 0.5 < score < 1.0

    def test_lookback_cap(self):
        old_traces = [MockTrace(quality_score=0.0, confidence=1.0) for _ in range(10)]
        recent_traces = [MockTrace(quality_score=0.5, confidence=0.5) for _ in range(5)]
        all_traces = old_traces + recent_traces
        score = compute_agreement_score(all_traces)
        score_recent = compute_agreement_score(recent_traces)
        assert score == score_recent

    def test_clamped_to_unit(self):
        traces = [MockTrace(quality_score=0.5, confidence=0.5)]
        score = compute_agreement_score(traces)
        assert 0.0 <= score <= 1.0


# ═══════════════════════════════════════════════════════════════
# 4. Instability score computation
# ═══════════════════════════════════════════════════════════════


class TestInstabilityScore:
    def test_empty_traces(self):
        assert compute_instability_score([]) == 0.0

    def test_stable_single_context(self):
        traces = [MockTrace(context_type="stable") for _ in range(5)]
        score = compute_instability_score(traces)
        assert score < 0.1

    def test_high_regime_volatility(self):
        types = ["stable", "adversarial", "stable", "adversarial", "stable"]
        traces = [MockTrace(context_type=t) for t in types]
        score = compute_instability_score(traces)
        assert score > 0.5

    def test_high_calibration_error(self):
        traces = [MockTrace(calibration_error=0.8) for _ in range(3)]
        score = compute_instability_score(traces)
        assert score > 0.5

    def test_quality_variance(self):
        traces = [
            MockTrace(quality_score=0.1),
            MockTrace(quality_score=0.9),
            MockTrace(quality_score=0.1),
        ]
        score = compute_instability_score(traces)
        assert score > 0.3

    def test_no_relevant_fields(self):
        traces = [MockTrace() for _ in range(3)]
        score = compute_instability_score(traces)
        assert score == 0.0

    def test_clamped_to_unit(self):
        traces = [
            MockTrace(context_type="a", calibration_error=1.0, quality_score=0.0),
            MockTrace(context_type="b", calibration_error=1.0, quality_score=1.0),
            MockTrace(context_type="a", calibration_error=1.0, quality_score=0.0),
        ]
        score = compute_instability_score(traces)
        assert 0.0 <= score <= 1.0

    def test_lookback_cap(self):
        old = [MockTrace(context_type="adversarial") for _ in range(10)]
        recent = [MockTrace(context_type="stable") for _ in range(MAX_LOOKBACK_TURNS)]
        all_traces = old + recent
        score_all = compute_instability_score(all_traces)
        score_recent = compute_instability_score(recent)
        assert score_all == score_recent


# ═══════════════════════════════════════════════════════════════
# 5. Confidence level computation
# ═══════════════════════════════════════════════════════════════


class TestConfidenceLevel:
    def test_empty_traces(self):
        assert compute_confidence_level([]) == 0.5

    def test_all_high_confidence(self):
        traces = [MockTrace(confidence=0.9) for _ in range(3)]
        assert compute_confidence_level(traces) == 0.9

    def test_all_low_confidence(self):
        traces = [MockTrace(confidence=0.2) for _ in range(3)]
        level = compute_confidence_level(traces)
        assert abs(level - 0.2) < 1e-6

    def test_no_confidence_field(self):
        traces = [MockTrace(quality_score=0.8) for _ in range(3)]
        assert compute_confidence_level(traces) == 0.5

    def test_lookback_cap(self):
        old = [MockTrace(confidence=0.1) for _ in range(10)]
        recent = [MockTrace(confidence=0.9) for _ in range(MAX_LOOKBACK_TURNS)]
        all_traces = old + recent
        level_all = compute_confidence_level(all_traces)
        level_recent = compute_confidence_level(recent)
        assert level_all == level_recent


# ═══════════════════════════════════════════════════════════════
# 6. Mode selection
# ═══════════════════════════════════════════════════════════════


class TestModeSelection:
    def test_high_instability_forces_minimal(self):
        assert select_mode(confidence=0.9, instability=0.7, agreement=0.9) == "minimal"

    def test_low_agreement_forces_minimal(self):
        assert select_mode(confidence=0.9, instability=0.1, agreement=0.3) == "minimal"

    def test_low_confidence_forces_minimal(self):
        assert select_mode(confidence=0.3, instability=0.1, agreement=0.9) == "minimal"

    def test_stable_high_agreement_high_conf_gives_full(self):
        assert select_mode(confidence=0.8, instability=0.2, agreement=0.8) == "full"

    def test_moderate_gives_adaptive(self):
        assert select_mode(confidence=0.5, instability=0.4, agreement=0.5) == "adaptive"

    def test_boundary_instability_at_threshold(self):
        assert (
            select_mode(
                confidence=0.8,
                instability=HIGH_INSTABILITY_THRESHOLD + 0.01,
                agreement=0.8,
            )
            == "minimal"
        )

    def test_boundary_instability_below_threshold(self):
        result = select_mode(
            confidence=0.8,
            instability=HIGH_INSTABILITY_THRESHOLD - 0.01,
            agreement=0.8,
        )
        assert result != "minimal"

    def test_boundary_agreement_at_threshold(self):
        assert (
            select_mode(
                confidence=0.8,
                instability=0.1,
                agreement=LOW_AGREEMENT_THRESHOLD - 0.01,
            )
            == "minimal"
        )

    def test_full_requires_all_three_conditions(self):
        assert select_mode(confidence=0.8, instability=0.2, agreement=0.5) == "adaptive"
        assert select_mode(confidence=0.5, instability=0.2, agreement=0.8) == "adaptive"
        assert select_mode(confidence=0.8, instability=0.5, agreement=0.8) == "adaptive"


# ═══════════════════════════════════════════════════════════════
# 7. Permissions from mode
# ═══════════════════════════════════════════════════════════════


class TestPermissionsForMode:
    def test_minimal(self):
        assert permissions_for_mode("minimal") == MINIMAL_PERMISSIONS

    def test_adaptive(self):
        assert permissions_for_mode("adaptive") == ADAPTIVE_PERMISSIONS

    def test_full(self):
        assert permissions_for_mode("full") == FULL_PERMISSIONS

    def test_unknown_defaults_to_full(self):
        assert permissions_for_mode("unknown") == FULL_PERMISSIONS


# ═══════════════════════════════════════════════════════════════
# 8. Main entry point
# ═══════════════════════════════════════════════════════════════


class TestComputeMetaControl:
    def test_empty_traces_returns_adaptive(self):
        state = compute_meta_control([])
        assert state.mode == "adaptive"
        assert state.permissions == ADAPTIVE_PERMISSIONS

    def test_stable_traces_return_full(self):
        traces = [MockTrace(confidence=0.9, quality_score=0.8) for _ in range(5)]
        state = compute_meta_control(traces)
        assert state.mode == "full"

    def test_unstable_traces_return_minimal(self):
        types = ["a", "b", "a", "b", "a"]
        traces = [
            MockTrace(context_type=t, calibration_error=0.9, confidence=0.2)
            for t in types
        ]
        state = compute_meta_control(traces)
        assert state.mode == "minimal"
        assert state.permissions == MINIMAL_PERMISSIONS

    def test_moderate_traces_return_adaptive(self):
        traces = [MockTrace(confidence=0.5, quality_score=0.5) for _ in range(5)]
        state = compute_meta_control(traces)
        assert state.mode == "adaptive"

    def test_state_fields_populated(self):
        traces = [MockTrace(confidence=0.5, quality_score=0.6) for _ in range(3)]
        state = compute_meta_control(traces)
        assert state.confidence_level is not None
        assert state.instability_score is not None
        assert state.agreement_score is not None
        assert state.mode in ("minimal", "adaptive", "full")


# ═══════════════════════════════════════════════════════════════
# 9. Deterministic behavior
# ═══════════════════════════════════════════════════════════════


class TestDeterministicBehavior:
    def test_same_input_same_output(self):
        traces = [
            MockTrace(confidence=0.6, quality_score=0.7, context_type="stable")
            for _ in range(3)
        ]
        s1 = compute_meta_control(traces)
        s2 = compute_meta_control(traces)
        assert s1.mode == s2.mode
        assert s1.confidence_level == s2.confidence_level
        assert s1.instability_score == s2.instability_score
        assert s1.agreement_score == s2.agreement_score

    def test_no_randomness_in_agreement(self):
        traces = [MockTrace(quality_score=0.5, confidence=0.5)]
        scores = [compute_agreement_score(traces) for _ in range(10)]
        assert all(s == scores[0] for s in scores)

    def test_no_randomness_in_instability(self):
        traces = [MockTrace(context_type="stable", calibration_error=0.1)]
        scores = [compute_instability_score(traces) for _ in range(10)]
        assert all(s == scores[0] for s in scores)


# ═══════════════════════════════════════════════════════════════
# 10. Trace integration
# ═══════════════════════════════════════════════════════════════


class TestTraceIntegration:
    def test_trace_fields_added(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        t = DecisionTrace(
            turn_id=0,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.5,
            confidence=0.5,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            meta_control_mode="adaptive",
            meta_control_agreement=0.8,
            meta_control_instability=0.2,
            meta_control_enabled_layers=("dynamic_adaptation",),
        )
        assert t.meta_control_mode == "adaptive"
        assert t.meta_control_agreement == 0.8
        assert t.meta_control_instability == 0.2
        assert t.meta_control_enabled_layers == ("dynamic_adaptation",)

    def test_trace_to_dict_includes_fields(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        t = DecisionTrace(
            turn_id=0,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.5,
            confidence=0.5,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            meta_control_mode="full",
            meta_control_agreement=0.95,
            meta_control_instability=0.05,
            meta_control_enabled_layers=("strategy_memory", "foresight"),
        )
        d = t.to_dict()
        assert d["meta_control_mode"] == "full"
        assert d["meta_control_agreement"] == round(0.95, 6)
        assert d["meta_control_instability"] == round(0.05, 6)
        assert d["meta_control_enabled_layers"] == ["strategy_memory", "foresight"]

    def test_trace_fields_none_by_default(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        t = DecisionTrace(
            turn_id=0,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.5,
            confidence=0.5,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
        )
        assert t.meta_control_mode is None
        assert t.meta_control_agreement is None
        d = t.to_dict()
        assert "meta_control_mode" not in d

    def test_build_trace_passes_fields(self):
        from umh.runtime_engine.decision_trace import build_trace

        t = build_trace(
            turn_id=0,
            meta_control_mode="minimal",
            meta_control_agreement=0.3,
            meta_control_instability=0.7,
            meta_control_enabled_layers=(),
        )
        assert t.meta_control_mode == "minimal"
        assert t.meta_control_agreement == 0.3
        assert t.meta_control_instability == 0.7
        assert t.meta_control_enabled_layers == ()


# ═══════════════════════════════════════════════════════════════
# 11. Gating behavior
# ═══════════════════════════════════════════════════════════════


class TestGatingBehavior:
    def test_minimal_gates_all_layers(self):
        p = permissions_for_mode("minimal")
        assert not p.allow_strategy_memory
        assert not p.allow_foresight
        assert not p.allow_planner_override
        assert not p.allow_dynamic_adaptation
        assert not p.allow_exploration_boost

    def test_adaptive_allows_only_dynamic_adaptation(self):
        p = permissions_for_mode("adaptive")
        assert not p.allow_strategy_memory
        assert not p.allow_foresight
        assert not p.allow_planner_override
        assert p.allow_dynamic_adaptation
        assert not p.allow_exploration_boost

    def test_full_allows_all(self):
        p = permissions_for_mode("full")
        assert p.allow_strategy_memory
        assert p.allow_foresight
        assert p.allow_planner_override
        assert p.allow_dynamic_adaptation
        assert p.allow_exploration_boost

    def test_unstable_input_minimal_permissions(self):
        types = ["a", "b", "c", "d", "e"]
        traces = [
            MockTrace(context_type=t, calibration_error=0.9, confidence=0.2)
            for t in types
        ]
        state = compute_meta_control(traces)
        assert state.permissions.enabled_count() == 0

    def test_stable_input_full_permissions(self):
        traces = [MockTrace(confidence=0.9, quality_score=0.8) for _ in range(5)]
        state = compute_meta_control(traces)
        assert state.permissions.enabled_count() == 5


# ═══════════════════════════════════════════════════════════════
# 12. No regression
# ═══════════════════════════════════════════════════════════════


class TestNoRegression:
    def test_empty_traces_safe(self):
        state = compute_meta_control([])
        assert state.mode == "adaptive"
        assert state.permissions == ADAPTIVE_PERMISSIONS

    def test_single_trace_safe(self):
        state = compute_meta_control([MockTrace(confidence=0.5)])
        assert state.mode in ("minimal", "adaptive", "full")

    def test_all_none_fields(self):
        traces = [MockTrace() for _ in range(5)]
        state = compute_meta_control(traces)
        assert state.mode in ("minimal", "adaptive", "full")

    def test_extreme_values_safe(self):
        traces = [
            MockTrace(
                quality_score=100.0,
                confidence=100.0,
                calibration_error=100.0,
            )
        ]
        state = compute_meta_control(traces)
        assert 0.0 <= state.instability_score <= 1.0
        assert 0.0 <= state.agreement_score <= 1.0

    def test_negative_values_safe(self):
        traces = [
            MockTrace(
                quality_score=-1.0,
                confidence=-1.0,
                calibration_error=-1.0,
            )
        ]
        state = compute_meta_control(traces)
        assert state.mode in ("minimal", "adaptive", "full")
