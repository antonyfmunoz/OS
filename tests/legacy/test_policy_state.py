"""Tests for eos_ai.policy_state — behavioral memory / decision discipline layer."""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.policy_state import (
    CONSISTENCY_THRESHOLD,
    DAMPENING_FACTOR,
    EXPLORATION_RATE_THRESHOLD,
    MAX_HISTORY,
    MODE_FLIP_THRESHOLD,
    NO_DAMPENING,
    OSCILLATION_THRESHOLD,
    OVERRIDE_RATE_THRESHOLD,
    RECOVERY_STEPS,
    STABLE_SIGNALS,
    DampeningResult,
    PolicySignals,
    PolicyStateTracker,
    apply_policy_to_meta_control,
    compute_consistency_score,
    compute_dampening,
    compute_mode_flip_rate,
    compute_oscillation_score,
    get_policy_tracker,
    reset_policy_tracker,
)


# ═══════════════════════════════════════════════════════════════
# 1. Oscillation detection
# ═══════════════════════════════════════════════════════════════


class TestOscillationDetection:
    def test_empty_actions(self):
        assert compute_oscillation_score([]) == 0.0

    def test_two_actions(self):
        assert compute_oscillation_score(["a", "b"]) == 0.0

    def test_no_oscillation(self):
        assert compute_oscillation_score(["a", "a", "a", "a"]) == 0.0

    def test_constant_change_no_reversal(self):
        assert compute_oscillation_score(["a", "b", "c", "d"]) == 0.0

    def test_full_oscillation(self):
        score = compute_oscillation_score(["a", "b", "a", "b", "a"])
        assert score == 1.0

    def test_partial_oscillation(self):
        score = compute_oscillation_score(["a", "b", "a", "a", "a"])
        assert 0.0 < score < 1.0

    def test_three_way_oscillation(self):
        score = compute_oscillation_score(["a", "b", "a", "c", "a"])
        assert score > 0.0

    def test_bounded(self):
        for pattern in [
            ["a", "b", "a", "b", "a", "b"],
            ["x"] * 10,
            ["a", "b", "c"],
        ]:
            score = compute_oscillation_score(pattern)
            assert 0.0 <= score <= 1.0


# ═══════════════════════════════════════════════════════════════
# 2. Mode flip rate
# ═══════════════════════════════════════════════════════════════


class TestModeFlipRate:
    def test_empty(self):
        assert compute_mode_flip_rate([]) == 0.0

    def test_single_mode(self):
        assert compute_mode_flip_rate(["full"]) == 0.0

    def test_stable_modes(self):
        assert compute_mode_flip_rate(["full", "full", "full"]) == 0.0

    def test_constant_flipping(self):
        rate = compute_mode_flip_rate(["full", "adaptive", "full", "adaptive"])
        assert rate == 1.0

    def test_partial_flipping(self):
        rate = compute_mode_flip_rate(["full", "full", "adaptive", "adaptive"])
        assert 0.0 < rate < 1.0

    def test_bounded(self):
        rate = compute_mode_flip_rate(["minimal", "adaptive", "full", "minimal"])
        assert 0.0 <= rate <= 1.0


# ═══════════════════════════════════════════════════════════════
# 3. Consistency metric
# ═══════════════════════════════════════════════════════════════


class TestConsistencyScore:
    def test_empty(self):
        assert compute_consistency_score([]) == 1.0

    def test_single_pair(self):
        assert compute_consistency_score([("stable", "a")]) == 1.0

    def test_perfect_consistency(self):
        pairs = [("stable", "a"), ("stable", "a"), ("volatile", "b"), ("volatile", "b")]
        assert compute_consistency_score(pairs) == 1.0

    def test_zero_consistency(self):
        pairs = [("stable", "a"), ("stable", "b")]
        score = compute_consistency_score(pairs)
        assert score == 0.5

    def test_mixed_consistency(self):
        pairs = [
            ("stable", "a"),
            ("stable", "a"),
            ("stable", "b"),
            ("volatile", "c"),
            ("volatile", "c"),
        ]
        score = compute_consistency_score(pairs)
        assert 0.5 < score < 1.0

    def test_all_different_contexts(self):
        pairs = [("a", "x"), ("b", "y"), ("c", "z")]
        assert compute_consistency_score(pairs) == 1.0

    def test_bounded(self):
        pairs = [("a", "x"), ("a", "y"), ("a", "z"), ("a", "w")]
        score = compute_consistency_score(pairs)
        assert 0.0 <= score <= 1.0


# ═══════════════════════════════════════════════════════════════
# 4. PolicySignals data model
# ═══════════════════════════════════════════════════════════════


class TestPolicySignals:
    def test_stable_signals(self):
        assert STABLE_SIGNALS.is_stable
        assert not STABLE_SIGNALS.any_flag_active()

    def test_any_flag_active(self):
        s = PolicySignals(
            is_oscillating=True,
            is_over_exploring=False,
            is_overriding_too_much=False,
            is_mode_flipping=False,
            is_stable=False,
        )
        assert s.any_flag_active()

    def test_to_dict(self):
        d = STABLE_SIGNALS.to_dict()
        assert d["is_stable"] is True
        assert d["is_oscillating"] is False

    def test_all_flags(self):
        s = PolicySignals(
            is_oscillating=True,
            is_over_exploring=True,
            is_overriding_too_much=True,
            is_mode_flipping=True,
            is_stable=False,
        )
        assert s.any_flag_active()
        assert not s.is_stable


# ═══════════════════════════════════════════════════════════════
# 5. Dampening computation
# ═══════════════════════════════════════════════════════════════


class TestDampening:
    def test_no_dampening_when_stable(self):
        result = compute_dampening(STABLE_SIGNALS, 0.0, 1.0)
        assert result == NO_DAMPENING

    def test_oscillation_dampening(self):
        signals = PolicySignals(
            is_oscillating=True,
            is_over_exploring=False,
            is_overriding_too_much=False,
            is_mode_flipping=False,
            is_stable=False,
        )
        result = compute_dampening(signals, 0.8, 0.5)
        assert result.planner_confidence_scale < 1.0
        assert result.stability_weight_bonus > 0.0

    def test_over_exploring_dampening(self):
        signals = PolicySignals(
            is_oscillating=False,
            is_over_exploring=True,
            is_overriding_too_much=False,
            is_mode_flipping=False,
            is_stable=False,
        )
        result = compute_dampening(signals, 0.0, 1.0)
        assert result.exploration_boost_scale < 1.0

    def test_override_dampening(self):
        signals = PolicySignals(
            is_oscillating=False,
            is_over_exploring=False,
            is_overriding_too_much=True,
            is_mode_flipping=False,
            is_stable=False,
        )
        result = compute_dampening(signals, 0.0, 1.0)
        assert result.planner_confidence_scale < 1.0

    def test_mode_flip_dampening(self):
        signals = PolicySignals(
            is_oscillating=False,
            is_over_exploring=False,
            is_overriding_too_much=False,
            is_mode_flipping=True,
            is_stable=False,
        )
        result = compute_dampening(signals, 0.0, 1.0)
        assert result.mode_override == "adaptive"
        assert result.stability_weight_bonus > 0.0

    def test_dampening_bounded(self):
        signals = PolicySignals(
            is_oscillating=True,
            is_over_exploring=True,
            is_overriding_too_much=True,
            is_mode_flipping=True,
            is_stable=False,
        )
        result = compute_dampening(signals, 1.0, 0.0)
        assert result.planner_confidence_scale >= 0.3
        assert result.exploration_boost_scale >= 0.3
        assert result.stability_weight_bonus <= 0.3

    def test_to_dict(self):
        d = NO_DAMPENING.to_dict()
        assert d["planner_confidence_scale"] == 1.0
        assert "mode_override" not in d


# ═══════════════════════════════════════════════════════════════
# 6. PolicyStateTracker core
# ═══════════════════════════════════════════════════════════════


class TestPolicyStateTracker:
    def test_initial_state(self):
        t = PolicyStateTracker()
        assert t.step == 0
        assert t.oscillation_score == 0.0
        assert t.consistency_score == 1.0
        assert t.override_rate == 0.0
        assert t.exploration_rate == 0.0
        assert t.stability_score == 1.0

    def test_record_turn(self):
        t = PolicyStateTracker()
        t.record_turn(action_id="a1", mode="full", context_type="stable")
        assert t.step == 1

    def test_bounded_history(self):
        t = PolicyStateTracker(max_history=5)
        for i in range(10):
            t.record_turn(action_id=f"a{i}", mode="full")
        assert t.step == 10

    def test_override_rate(self):
        t = PolicyStateTracker()
        t.record_turn(planner_override_used=True)
        t.record_turn(planner_override_used=True)
        t.record_turn(planner_override_used=False)
        assert abs(t.override_rate - 2 / 3) < 1e-6

    def test_exploration_rate(self):
        t = PolicyStateTracker()
        for _ in range(4):
            t.record_turn(exploration_used=True)
        t.record_turn(exploration_used=False)
        assert abs(t.exploration_rate - 0.8) < 1e-6


# ═══════════════════════════════════════════════════════════════
# 7. Signal computation
# ═══════════════════════════════════════════════════════════════


class TestSignalComputation:
    def test_stable_initial(self):
        t = PolicyStateTracker()
        signals = t.compute_signals()
        assert signals.is_stable

    def test_oscillation_flag(self):
        t = PolicyStateTracker()
        for action in ["a", "b", "a", "b", "a", "b", "a"]:
            t.record_turn(action_id=action, mode="full", context_type="stable")
        signals = t.compute_signals()
        assert signals.is_oscillating

    def test_mode_flipping_flag(self):
        t = PolicyStateTracker()
        for mode in ["full", "adaptive", "full", "adaptive", "full"]:
            t.record_turn(action_id="a", mode=mode, context_type="stable")
        signals = t.compute_signals()
        assert signals.is_mode_flipping

    def test_override_flag(self):
        t = PolicyStateTracker()
        for _ in range(5):
            t.record_turn(planner_override_used=True)
        signals = t.compute_signals()
        assert signals.is_overriding_too_much

    def test_exploration_flag(self):
        t = PolicyStateTracker()
        for _ in range(5):
            t.record_turn(exploration_used=True)
        signals = t.compute_signals()
        assert signals.is_over_exploring


# ═══════════════════════════════════════════════════════════════
# 8. Recovery logic
# ═══════════════════════════════════════════════════════════════


class TestRecovery:
    def test_not_recovered_initially(self):
        t = PolicyStateTracker()
        assert not t.is_recovered()

    def test_recovery_after_stable_steps(self):
        t = PolicyStateTracker()
        for _ in range(RECOVERY_STEPS + 5):
            t.record_turn(action_id="a", mode="full", context_type="stable")
        assert t.is_recovered()

    def test_recovery_resets_on_instability(self):
        t = PolicyStateTracker()
        for _ in range(RECOVERY_STEPS - 1):
            t.record_turn(action_id="a", mode="full", context_type="stable")
        for action in ["a", "b", "a", "b", "a", "b", "a"]:
            t.record_turn(action_id=action, mode="full", context_type="stable")
        assert not t.is_recovered()

    def test_stability_ema_tracks(self):
        t = PolicyStateTracker()
        t.record_turn(action_id="a", mode="full", context_type="stable")
        first_ema = t.stability_score
        for action in ["a", "b", "a", "b"]:
            t.record_turn(action_id=action, mode="full", context_type="stable")
        assert t.stability_score != first_ema


# ═══════════════════════════════════════════════════════════════
# 9. Meta-control integration
# ═══════════════════════════════════════════════════════════════


class TestMetaControlIntegration:
    def test_no_change_when_stable(self):
        t = PolicyStateTracker()
        for _ in range(3):
            t.record_turn(action_id="a", mode="full", context_type="stable")
        result = apply_policy_to_meta_control("full", t)
        assert result == "full"

    def test_downgrade_on_oscillation(self):
        t = PolicyStateTracker()
        for action in ["a", "b", "a", "b", "a", "b", "a"]:
            t.record_turn(action_id=action, mode="full", context_type="stable")
        result = apply_policy_to_meta_control("full", t)
        assert result == "adaptive"

    def test_downgrade_on_mode_flipping(self):
        t = PolicyStateTracker()
        for mode in ["full", "adaptive", "full", "adaptive", "full"]:
            t.record_turn(action_id="a", mode=mode, context_type="stable")
        result = apply_policy_to_meta_control("full", t)
        assert result == "adaptive"

    def test_no_downgrade_for_minimal(self):
        t = PolicyStateTracker()
        for action in ["a", "b", "a", "b", "a"]:
            t.record_turn(action_id=action, mode="full", context_type="stable")
        result = apply_policy_to_meta_control("minimal", t)
        assert result == "minimal"

    def test_recovery_allows_full(self):
        t = PolicyStateTracker()
        for mode in ["full", "adaptive", "full", "adaptive"]:
            t.record_turn(action_id="a", mode=mode, context_type="stable")
        for _ in range(RECOVERY_STEPS + 5):
            t.record_turn(action_id="a", mode="full", context_type="stable")
        result = apply_policy_to_meta_control("full", t)
        assert result == "full"


# ═══════════════════════════════════════════════════════════════
# 10. Dampening behavior
# ═══════════════════════════════════════════════════════════════


class TestDampeningBehavior:
    def test_no_dampening_stable(self):
        t = PolicyStateTracker()
        for _ in range(3):
            t.record_turn(action_id="a", mode="full", context_type="stable")
        d = t.compute_dampening()
        assert d == NO_DAMPENING

    def test_dampening_on_oscillation(self):
        t = PolicyStateTracker()
        for action in ["a", "b", "a", "b", "a", "b", "a"]:
            t.record_turn(action_id=action, mode="full", context_type="stable")
        d = t.compute_dampening()
        assert d.planner_confidence_scale < 1.0

    def test_dampening_reduces_exploration(self):
        t = PolicyStateTracker()
        for _ in range(5):
            t.record_turn(exploration_used=True)
        d = t.compute_dampening()
        assert d.exploration_boost_scale < 1.0

    def test_dampening_does_not_over_suppress(self):
        t = PolicyStateTracker()
        for action in ["a", "b", "a", "b", "a"]:
            t.record_turn(
                action_id=action,
                mode="full",
                planner_override_used=True,
                exploration_used=True,
            )
        d = t.compute_dampening()
        assert d.planner_confidence_scale >= 0.3
        assert d.exploration_boost_scale >= 0.3


# ═══════════════════════════════════════════════════════════════
# 11. Trace integration
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
            policy_oscillation_score=0.3,
            policy_consistency_score=0.8,
            policy_flags={"is_stable": True},
        )
        assert t.policy_oscillation_score == 0.3
        assert t.policy_consistency_score == 0.8
        assert t.policy_flags == {"is_stable": True}

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
            policy_oscillation_score=0.5,
            policy_consistency_score=0.7,
            policy_flags={"is_oscillating": True},
        )
        d = t.to_dict()
        assert d["policy_oscillation_score"] == round(0.5, 6)
        assert d["policy_consistency_score"] == round(0.7, 6)
        assert d["policy_flags"] == {"is_oscillating": True}

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
        assert t.policy_oscillation_score is None
        d = t.to_dict()
        assert "policy_oscillation_score" not in d

    def test_build_trace_passes_fields(self):
        from umh.runtime_engine.decision_trace import build_trace

        t = build_trace(
            turn_id=0,
            policy_oscillation_score=0.2,
            policy_consistency_score=0.9,
            policy_flags={"is_stable": True},
        )
        assert t.policy_oscillation_score == 0.2
        assert t.policy_consistency_score == 0.9
        assert t.policy_flags == {"is_stable": True}

    def test_get_trace_fields(self):
        t = PolicyStateTracker()
        t.record_turn(action_id="a", mode="full", context_type="stable")
        fields = t.get_trace_fields()
        assert "policy_oscillation_score" in fields
        assert "policy_consistency_score" in fields
        assert "policy_stability_ema" in fields
        assert "policy_flags" in fields


# ═══════════════════════════════════════════════════════════════
# 12. Deterministic behavior
# ═══════════════════════════════════════════════════════════════


class TestDeterministicBehavior:
    def test_same_input_same_output(self):
        actions = ["a", "b", "a", "b", "a"]
        s1 = compute_oscillation_score(actions)
        s2 = compute_oscillation_score(actions)
        assert s1 == s2

    def test_consistency_deterministic(self):
        pairs = [("a", "x"), ("a", "y"), ("b", "z")]
        s1 = compute_consistency_score(pairs)
        s2 = compute_consistency_score(pairs)
        assert s1 == s2

    def test_tracker_deterministic(self):
        def run_tracker():
            t = PolicyStateTracker()
            for action in ["a", "b", "a", "c"]:
                t.record_turn(action_id=action, mode="full", context_type="stable")
            return t.oscillation_score, t.consistency_score, t.stability_score

        r1 = run_tracker()
        r2 = run_tracker()
        assert r1 == r2


# ═══════════════════════════════════════════════════════════════
# 13. Singleton
# ═══════════════════════════════════════════════════════════════


class TestSingleton:
    def test_get_returns_same(self):
        reset_policy_tracker()
        t1 = get_policy_tracker()
        t2 = get_policy_tracker()
        assert t1 is t2
        reset_policy_tracker()

    def test_reset_clears(self):
        reset_policy_tracker()
        t1 = get_policy_tracker()
        t1.record_turn(action_id="a")
        reset_policy_tracker()
        t2 = get_policy_tracker()
        assert t2.step == 0


# ═══════════════════════════════════════════════════════════════
# 14. Reset behavior
# ═══════════════════════════════════════════════════════════════


class TestResetBehavior:
    def test_reset_clears_all(self):
        t = PolicyStateTracker()
        for action in ["a", "b", "a"]:
            t.record_turn(action_id=action, mode="full", context_type="stable")
        t.reset()
        assert t.step == 0
        assert t.oscillation_score == 0.0
        assert t.consistency_score == 1.0
        assert t.stability_score == 1.0
        assert t.override_rate == 0.0
        assert t.exploration_rate == 0.0


# ═══════════════════════════════════════════════════════════════
# 15. No regression
# ═══════════════════════════════════════════════════════════════


class TestNoRegression:
    def test_empty_tracker_safe(self):
        t = PolicyStateTracker()
        signals = t.compute_signals()
        assert signals.is_stable
        d = t.compute_dampening()
        assert d == NO_DAMPENING

    def test_single_turn_safe(self):
        t = PolicyStateTracker()
        t.record_turn(action_id="a", mode="full")
        signals = t.compute_signals()
        assert signals.is_stable

    def test_none_action_safe(self):
        t = PolicyStateTracker()
        t.record_turn(action_id=None, mode="full")
        assert t.oscillation_score == 0.0

    def test_extreme_history_safe(self):
        t = PolicyStateTracker()
        for i in range(100):
            t.record_turn(
                action_id=f"a{i % 2}",
                mode="full" if i % 2 == 0 else "adaptive",
                context_type="stable",
                planner_override_used=True,
                exploration_used=True,
            )
        signals = t.compute_signals()
        assert isinstance(signals.is_stable, bool)
        assert 0.0 <= t.oscillation_score <= 1.0
        assert 0.0 <= t.consistency_score <= 1.0

    def test_apply_to_meta_control_preserves_minimal(self):
        t = PolicyStateTracker()
        assert apply_policy_to_meta_control("minimal", t) == "minimal"
