"""Tests for eos_ai.intent_compiler — intent → system compilation layer."""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.intent_compiler import (
    DEFAULT_COMPILED,
    DEFAULT_HORIZON,
    DEFAULT_RISK_TOLERANCE,
    EXPLORATION_WEIGHT_BOUNDS,
    NOVELTY_WEIGHT_BOUNDS,
    REWARD_WEIGHT_BOUNDS,
    RISK_WEIGHT_BOUNDS,
    STABILITY_WEIGHT_BOUNDS,
    CompiledIntent,
    IntentInput,
    compile_intent,
    extract_keywords,
    get_trace_fields,
    to_objective_weights,
)


# ─── Helpers ────────────────────────────────────────────────


def _w(compiled: CompiledIntent, key: str) -> float:
    return compiled.objective_weights[key]


def _in_bounds(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value <= bounds[1]


# ═══════════════════════════════════════════════════════════════
# 1. IntentInput data model
# ═══════════════════════════════════════════════════════════════


class TestIntentInput:
    def test_defaults(self):
        i = IntentInput(goal="grow my agency")
        assert i.time_horizon == DEFAULT_HORIZON
        assert i.risk_tolerance == DEFAULT_RISK_TOLERANCE
        assert i.constraints == ()
        assert i.priority_weights is None

    def test_to_dict(self):
        i = IntentInput(goal="grow", constraints=("low_risk",), time_horizon=10)
        d = i.to_dict()
        assert d["goal"] == "grow"
        assert d["time_horizon"] == 10
        assert "constraints" in d

    def test_to_dict_no_optional(self):
        i = IntentInput(goal="test")
        d = i.to_dict()
        assert "constraints" not in d
        assert "priority_weights" not in d


# ═══════════════════════════════════════════════════════════════
# 2. Keyword extraction
# ═══════════════════════════════════════════════════════════════


class TestKeywordExtraction:
    def test_single_keyword(self):
        assert extract_keywords("grow my agency") == ("grow",)

    def test_multiple_keywords(self):
        kws = extract_keywords("scale revenue fast")
        assert "scale" in kws
        assert "revenue" in kws
        assert "fast" in kws

    def test_no_keywords(self):
        assert extract_keywords("do something random") == ()

    def test_case_insensitive(self):
        assert extract_keywords("GROW") == ("grow",)

    def test_duplicates_removed(self):
        kws = extract_keywords("grow grow grow")
        assert kws == ("grow",)

    def test_punctuation_handled(self):
        kws = extract_keywords("scale, revenue. fast")
        assert "scale" in kws
        assert "revenue" in kws


# ═══════════════════════════════════════════════════════════════
# 3. Deterministic mapping
# ═══════════════════════════════════════════════════════════════


class TestDeterministicMapping:
    def test_growth_intent(self):
        c = compile_intent(IntentInput(goal="grow my agency"))
        assert _w(c, "reward") > 0.5
        assert c.exploration_policy > 0.0
        assert c.matched_keywords == ("grow",)

    def test_safety_intent(self):
        c = compile_intent(IntentInput(goal="safe conservative approach"))
        assert _w(c, "risk") > 0.3
        assert _w(c, "stability") > 0.3
        assert c.risk_profile < 0.5

    def test_optimize_intent(self):
        c = compile_intent(IntentInput(goal="optimize efficiency"))
        assert _w(c, "stability") > 0.3
        assert c.stability_bias > 0.3

    def test_explore_intent(self):
        c = compile_intent(IntentInput(goal="explore new opportunities"))
        assert _w(c, "exploration") > 0.0
        assert c.exploration_policy > 0.0

    def test_empty_goal(self):
        c = compile_intent(IntentInput(goal=""))
        assert c.objective_weights == DEFAULT_COMPILED.objective_weights

    def test_same_input_same_output(self):
        i = IntentInput(goal="scale revenue")
        c1 = compile_intent(i)
        c2 = compile_intent(i)
        assert c1.objective_weights == c2.objective_weights
        assert c1.risk_profile == c2.risk_profile


# ═══════════════════════════════════════════════════════════════
# 4. Conflict resolution
# ═══════════════════════════════════════════════════════════════


class TestConflictResolution:
    def test_opposing_intents_clamped(self):
        c = compile_intent(IntentInput(goal="aggressive conservative"))
        for key, bounds in [
            ("reward", REWARD_WEIGHT_BOUNDS),
            ("risk", RISK_WEIGHT_BOUNDS),
            ("stability", STABILITY_WEIGHT_BOUNDS),
            ("exploration", EXPLORATION_WEIGHT_BOUNDS),
            ("novelty", NOVELTY_WEIGHT_BOUNDS),
        ]:
            assert _in_bounds(_w(c, key), bounds), f"{key}={_w(c, key)} out of {bounds}"

    def test_constraint_overrides_goal(self):
        c_no_constraint = compile_intent(IntentInput(goal="explore experiment"))
        c_with_constraint = compile_intent(
            IntentInput(goal="explore experiment", constraints=("no_exploration",))
        )
        assert _w(c_with_constraint, "exploration") < _w(c_no_constraint, "exploration")

    def test_multiple_constraints(self):
        c = compile_intent(
            IntentInput(goal="grow", constraints=("low_risk", "stability_first"))
        )
        assert _w(c, "stability") >= STABILITY_WEIGHT_BOUNDS[0]
        assert c.risk_profile < 0.5


# ═══════════════════════════════════════════════════════════════
# 5. Weight normalization / clamping
# ═══════════════════════════════════════════════════════════════


class TestWeightNormalization:
    def test_all_weights_in_bounds(self):
        intents = [
            "grow scale revenue fast aggressive",
            "safe conservative reduce risk slow",
            "explore experiment innovate diversify",
            "optimize efficiency consistent focus stable",
        ]
        for goal in intents:
            c = compile_intent(IntentInput(goal=goal))
            assert _in_bounds(_w(c, "reward"), REWARD_WEIGHT_BOUNDS), (
                f"reward out of bounds for '{goal}'"
            )
            assert _in_bounds(_w(c, "risk"), RISK_WEIGHT_BOUNDS), (
                f"risk out of bounds for '{goal}'"
            )
            assert _in_bounds(_w(c, "stability"), STABILITY_WEIGHT_BOUNDS), (
                f"stability out of bounds for '{goal}'"
            )
            assert _in_bounds(_w(c, "exploration"), EXPLORATION_WEIGHT_BOUNDS), (
                f"exploration out of bounds for '{goal}'"
            )
            assert _in_bounds(_w(c, "novelty"), NOVELTY_WEIGHT_BOUNDS), (
                f"novelty out of bounds for '{goal}'"
            )

    def test_risk_profile_bounded(self):
        for goal in ["aggressive", "conservative"]:
            c = compile_intent(IntentInput(goal=goal))
            assert 0.0 <= c.risk_profile <= 1.0

    def test_exploration_policy_bounded(self):
        c = compile_intent(IntentInput(goal="explore experiment innovate"))
        assert 0.0 <= c.exploration_policy <= 1.0

    def test_stability_bias_bounded(self):
        c = compile_intent(IntentInput(goal="safe stable consistent conservative"))
        assert 0.0 <= c.stability_bias <= 1.0


# ═══════════════════════════════════════════════════════════════
# 6. Priority weights
# ═══════════════════════════════════════════════════════════════


class TestPriorityWeights:
    def test_multiplier_applied(self):
        c_base = compile_intent(IntentInput(goal="grow"))
        c_boosted = compile_intent(
            IntentInput(goal="grow", priority_weights={"reward": 1.5})
        )
        assert _w(c_boosted, "reward") >= _w(c_base, "reward")

    def test_multiplier_clamped(self):
        c = compile_intent(IntentInput(goal="grow", priority_weights={"reward": 100.0}))
        assert _in_bounds(_w(c, "reward"), REWARD_WEIGHT_BOUNDS)

    def test_zero_multiplier(self):
        c = compile_intent(
            IntentInput(goal="grow", priority_weights={"exploration": 0.0})
        )
        assert _w(c, "exploration") == EXPLORATION_WEIGHT_BOUNDS[0]


# ═══════════════════════════════════════════════════════════════
# 7. Horizon bias
# ═══════════════════════════════════════════════════════════════


class TestHorizonBias:
    def test_short_horizon_favors_reward(self):
        c_short = compile_intent(IntentInput(goal="grow", time_horizon=1))
        c_long = compile_intent(IntentInput(goal="grow", time_horizon=15))
        assert _w(c_short, "reward") >= _w(c_long, "reward")

    def test_long_horizon_favors_stability(self):
        c_short = compile_intent(IntentInput(goal="grow", time_horizon=1))
        c_long = compile_intent(IntentInput(goal="grow", time_horizon=15))
        assert _w(c_long, "stability") >= _w(c_short, "stability")

    def test_default_horizon_no_bias(self):
        c = compile_intent(IntentInput(goal="grow", time_horizon=5))
        assert c.horizon_bias == 5


# ═══════════════════════════════════════════════════════════════
# 8. Risk tolerance
# ═══════════════════════════════════════════════════════════════


class TestRiskTolerance:
    def test_low_tolerance(self):
        c = compile_intent(IntentInput(goal="grow", risk_tolerance=0.1))
        assert c.risk_profile < 0.5

    def test_high_tolerance(self):
        c = compile_intent(IntentInput(goal="grow", risk_tolerance=0.9))
        assert c.risk_profile > 0.5

    def test_clamped(self):
        c = compile_intent(IntentInput(goal="grow", risk_tolerance=2.0))
        assert 0.0 <= c.risk_profile <= 1.0


# ═══════════════════════════════════════════════════════════════
# 9. CompiledIntent data model
# ═══════════════════════════════════════════════════════════════


class TestCompiledIntent:
    def test_to_dict(self):
        c = compile_intent(IntentInput(goal="grow"))
        d = c.to_dict()
        assert "objective_weights" in d
        assert "risk_profile" in d
        assert "exploration_policy" in d
        assert "stability_bias" in d
        assert "horizon_bias" in d
        assert "matched_keywords" in d
        assert "intent_source" in d

    def test_default_compiled(self):
        assert DEFAULT_COMPILED.intent_source == "default"
        assert DEFAULT_COMPILED.matched_keywords == ()


# ═══════════════════════════════════════════════════════════════
# 10. ObjectiveWeights bridge
# ═══════════════════════════════════════════════════════════════


class TestObjectiveWeightsBridge:
    def test_conversion(self):
        c = compile_intent(IntentInput(goal="grow"))
        w = to_objective_weights(c)
        assert w is not None
        assert w.reward_weight == _w(c, "reward")
        assert w.risk_weight == _w(c, "risk")
        assert w.stability_weight == _w(c, "stability")
        assert w.exploration_weight == _w(c, "exploration")
        assert w.novelty_weight == _w(c, "novelty")

    def test_none_input(self):
        from umh.runtime_engine.intent_compiler import get_trace_fields

        fields = get_trace_fields(None)
        assert fields == {}


# ═══════════════════════════════════════════════════════════════
# 11. Trace integration
# ═══════════════════════════════════════════════════════════════


class TestTraceIntegration:
    def test_trace_fields_from_compiled(self):
        c = compile_intent(IntentInput(goal="scale revenue"))
        fields = get_trace_fields(c)
        assert fields["intent_source"] == "scale revenue"
        assert "intent_compiled_weights" in fields
        assert "intent_applied_biases" in fields
        assert "risk_profile" in fields["intent_applied_biases"]

    def test_trace_fields_added_to_decision_trace(self):
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
            intent_source="grow",
            intent_compiled_weights={"reward": 0.65},
            intent_applied_biases={"risk_profile": 0.5},
        )
        assert t.intent_source == "grow"
        d = t.to_dict()
        assert d["intent_source"] == "grow"
        assert d["intent_compiled_weights"] == {"reward": 0.65}

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
        assert t.intent_source is None
        d = t.to_dict()
        assert "intent_source" not in d

    def test_build_trace_passes_fields(self):
        from umh.runtime_engine.decision_trace import build_trace

        t = build_trace(
            turn_id=0,
            intent_source="grow",
            intent_compiled_weights={"reward": 0.6},
            intent_applied_biases={"stability_bias": 0.4},
        )
        assert t.intent_source == "grow"
        assert t.intent_compiled_weights == {"reward": 0.6}
        assert t.intent_applied_biases == {"stability_bias": 0.4}


# ═══════════════════════════════════════════════════════════════
# 12. Behavioral change verification
# ═══════════════════════════════════════════════════════════════


class TestBehavioralChange:
    def test_growth_vs_safety_differ(self):
        c_grow = compile_intent(IntentInput(goal="grow scale"))
        c_safe = compile_intent(IntentInput(goal="safe conservative"))
        assert _w(c_grow, "reward") > _w(c_safe, "reward")
        assert _w(c_safe, "risk") > _w(c_grow, "risk")

    def test_explore_vs_focus_differ(self):
        c_explore = compile_intent(IntentInput(goal="explore innovate"))
        c_focus = compile_intent(IntentInput(goal="focus consistent"))
        assert _w(c_explore, "exploration") > _w(c_focus, "exploration")
        assert c_explore.exploration_policy > c_focus.exploration_policy

    def test_aggressive_vs_conservative_differ(self):
        c_agg = compile_intent(IntentInput(goal="aggressive"))
        c_con = compile_intent(IntentInput(goal="conservative"))
        assert c_agg.risk_profile > c_con.risk_profile


# ═══════════════════════════════════════════════════════════════
# 13. Deterministic behavior
# ═══════════════════════════════════════════════════════════════


class TestDeterministic:
    def test_repeated_compilation(self):
        i = IntentInput(
            goal="grow revenue fast",
            constraints=("low_risk",),
            time_horizon=10,
            risk_tolerance=0.3,
        )
        results = [compile_intent(i) for _ in range(10)]
        for r in results[1:]:
            assert r.objective_weights == results[0].objective_weights
            assert r.risk_profile == results[0].risk_profile
            assert r.exploration_policy == results[0].exploration_policy
            assert r.stability_bias == results[0].stability_bias

    def test_keyword_extraction_deterministic(self):
        results = [extract_keywords("scale revenue fast") for _ in range(10)]
        assert all(r == results[0] for r in results)


# ═══════════════════════════════════════════════════════════════
# 14. No regression
# ═══════════════════════════════════════════════════════════════


class TestNoRegression:
    def test_empty_goal_safe(self):
        c = compile_intent(IntentInput(goal=""))
        assert c.intent_source == ""
        assert c.matched_keywords == ()

    def test_unknown_words_safe(self):
        c = compile_intent(IntentInput(goal="xyzzy flurbo zorp"))
        assert c.matched_keywords == ()
        assert c.objective_weights == DEFAULT_COMPILED.objective_weights

    def test_unknown_constraint_ignored(self):
        c = compile_intent(IntentInput(goal="grow", constraints=("nonexistent",)))
        c2 = compile_intent(IntentInput(goal="grow"))
        assert c.objective_weights == c2.objective_weights

    def test_extreme_risk_tolerance(self):
        c = compile_intent(IntentInput(goal="grow", risk_tolerance=-5.0))
        assert 0.0 <= c.risk_profile <= 1.0

    def test_extreme_horizon(self):
        c = compile_intent(IntentInput(goal="grow", time_horizon=1000))
        assert c.horizon_bias == 1000
        for key, bounds in [
            ("reward", REWARD_WEIGHT_BOUNDS),
            ("risk", RISK_WEIGHT_BOUNDS),
            ("stability", STABILITY_WEIGHT_BOUNDS),
            ("exploration", EXPLORATION_WEIGHT_BOUNDS),
            ("novelty", NOVELTY_WEIGHT_BOUNDS),
        ]:
            assert _in_bounds(_w(c, key), bounds)
