"""Tests for eos_ai.action_synthesis — action space shaping layer."""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.action_synthesis import (
    CONFIDENCE_LOW_THRESHOLD,
    CONTEXT_STABILITY_REQUIRED,
    MAX_NEW_CANDIDATES,
    MIN_BASE_CANDIDATES,
    NO_SYNTHESIS,
    NO_TRACE,
    PLATEAU_VARIANCE_THRESHOLD,
    PLATEAU_WINDOW,
    REGIME_STRENGTH_THRESHOLD,
    RISK_HIGH_THRESHOLD,
    SEED_SCORE_FLOOR,
    SYNTHESIS_COOLDOWN,
    UNCERTAINTY_GATE,
    SynthesisMemory,
    SynthesisResult,
    SynthesisTraceFields,
    SynthesizedAction,
    check_safety_gate,
    check_synthesis_triggers,
    expand_candidate_set,
    extract_trace_fields,
    synthesize_actions,
    _combine_actions,
    _detect_high_risk_across_all,
    _detect_low_confidence,
    _detect_plateau,
    _detect_regime_stagnation,
    _mutate_action,
    _seed_novel_action,
)


# ─── Test data builders ──────────────────────────────────────────


def _make_scores(*pairs: tuple[str, float]) -> dict[str, float]:
    return {name: score for name, score in pairs}


def _make_causal_stats(
    actions: list[str],
    context: str = "stable",
    count: int = 15,
) -> dict:
    stats = {}
    for i, action in enumerate(actions):
        key = f"{context}|{action}"
        stats[key] = {
            "context_type": context,
            "action": action,
            "count": count,
            "ema_reward_delta": 0.1 * (1 + i * 0.5),
            "ema_objective_delta": 0.1 * (1 + i * 0.3),
            "positive_count": int(count * 0.7),
            "ema_variance": 0.01,
        }
    return stats


def _flat_reward_history(
    n: int = PLATEAU_WINDOW + 5, value: float = 0.5
) -> list[float]:
    """Reward history that triggers plateau detection."""
    return [value] * n


def _improving_reward_history(n: int = 20) -> list[float]:
    """Reward history that does NOT trigger plateau detection."""
    return [0.3 + 0.03 * i for i in range(n)]


# ─── Trigger detection ───────────────────────────────────────────


class TestTriggerDetection(unittest.TestCase):
    def test_low_confidence_triggers(self) -> None:
        self.assertTrue(_detect_low_confidence(0.1))
        self.assertTrue(_detect_low_confidence(CONFIDENCE_LOW_THRESHOLD - 0.01))

    def test_normal_confidence_does_not_trigger(self) -> None:
        self.assertFalse(_detect_low_confidence(CONFIDENCE_LOW_THRESHOLD))
        self.assertFalse(_detect_low_confidence(0.9))

    def test_all_high_risk_triggers(self) -> None:
        scores = {"a": 0.6, "b": 0.7, "c": 0.8}
        self.assertTrue(_detect_high_risk_across_all(scores))

    def test_mixed_risk_does_not_trigger(self) -> None:
        scores = {"a": 0.2, "b": 0.7}
        self.assertFalse(_detect_high_risk_across_all(scores))

    def test_empty_risk_does_not_trigger(self) -> None:
        self.assertFalse(_detect_high_risk_across_all({}))

    def test_plateau_detected(self) -> None:
        history = _flat_reward_history()
        self.assertTrue(_detect_plateau(history))

    def test_improving_not_plateau(self) -> None:
        history = _improving_reward_history()
        self.assertFalse(_detect_plateau(history))

    def test_short_history_not_plateau(self) -> None:
        history = [0.5] * (PLATEAU_WINDOW - 1)
        self.assertFalse(_detect_plateau(history))

    def test_regime_stagnation_triggers(self) -> None:
        self.assertTrue(_detect_regime_stagnation(True, REGIME_STRENGTH_THRESHOLD))
        self.assertTrue(_detect_regime_stagnation(True, 0.8))

    def test_inactive_regime_does_not_trigger(self) -> None:
        self.assertFalse(_detect_regime_stagnation(False, 0.8))

    def test_weak_regime_does_not_trigger(self) -> None:
        self.assertFalse(_detect_regime_stagnation(True, 0.1))


class TestCheckTriggers(unittest.TestCase):
    def test_no_triggers_returns_false(self) -> None:
        active, reason = check_synthesis_triggers()
        self.assertFalse(active)
        self.assertEqual(reason, "")

    def test_single_trigger_activates(self) -> None:
        active, reason = check_synthesis_triggers(planner_confidence=0.1)
        self.assertTrue(active)
        self.assertIn("low_confidence", reason)

    def test_multiple_triggers_combined(self) -> None:
        active, reason = check_synthesis_triggers(
            planner_confidence=0.1,
            reward_history=_flat_reward_history(),
        )
        self.assertTrue(active)
        self.assertIn("low_confidence", reason)
        self.assertIn("performance_plateau", reason)


# ─── Safety gating ───────────────────────────────────────────────


class TestSafetyGating(unittest.TestCase):
    def test_stable_context_passes(self) -> None:
        gate = check_safety_gate("stable", 0.5, -10, 0)
        self.assertIsNone(gate)

    def test_unstable_context_blocked(self) -> None:
        gate = check_safety_gate("volatile", 0.5, -10, 0)
        self.assertIsNotNone(gate)
        self.assertIn("context_not_stable", gate)

    def test_high_uncertainty_blocked(self) -> None:
        gate = check_safety_gate("stable", 0.9, -10, 0)
        self.assertIsNotNone(gate)
        self.assertIn("uncertainty_too_high", gate)

    def test_cooldown_blocks(self) -> None:
        gate = check_safety_gate("stable", 0.5, 0, 2)
        self.assertIsNotNone(gate)
        self.assertIn("cooldown", gate)

    def test_cooldown_elapsed_passes(self) -> None:
        gate = check_safety_gate("stable", 0.5, 0, SYNTHESIS_COOLDOWN)
        self.assertIsNone(gate)


# ─── Mutation ────────────────────────────────────────────────────


class TestMutation(unittest.TestCase):
    def test_creates_mutated_variant(self) -> None:
        scores = _make_scores(("outreach", 0.5), ("content", 0.3))
        result = _mutate_action("outreach", 0.5, scores)
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "mut_outreach")
        self.assertEqual(result.strategy_type, "mutation")
        self.assertEqual(result.strategy_origin, ("outreach",))

    def test_mutated_score_below_original(self) -> None:
        scores = _make_scores(("outreach", 0.5), ("content", 0.3))
        result = _mutate_action("outreach", 0.5, scores)
        self.assertIsNotNone(result)
        self.assertLess(result.estimated_score, 0.5)

    def test_zero_score_returns_none(self) -> None:
        scores = _make_scores(("dead", 0.0))
        result = _mutate_action("dead", 0.0, scores)
        self.assertIsNone(result)

    def test_duplicate_mutation_returns_none(self) -> None:
        scores = _make_scores(("outreach", 0.5), ("mut_outreach", 0.3))
        result = _mutate_action("outreach", 0.5, scores)
        self.assertIsNone(result)

    def test_mutated_score_never_below_floor(self) -> None:
        scores = _make_scores(("tiny", 0.001), ("tinier", 0.0001))
        result = _mutate_action("tiny", 0.001, scores)
        if result is not None:
            self.assertGreaterEqual(result.estimated_score, SEED_SCORE_FLOOR)


# ─── Combination ─────────────────────────────────────────────────


class TestCombination(unittest.TestCase):
    def test_creates_combined_variant(self) -> None:
        scores = _make_scores(("a", 0.5), ("b", 0.3))
        result = _combine_actions("a", 0.5, "b", 0.3, scores)
        self.assertIsNotNone(result)
        self.assertEqual(result.strategy_type, "combination")
        self.assertEqual(len(result.strategy_origin), 2)
        self.assertIn("a", result.strategy_origin)
        self.assertIn("b", result.strategy_origin)

    def test_combined_name_is_deterministic(self) -> None:
        scores = _make_scores(("a", 0.5), ("b", 0.3))
        r1 = _combine_actions("a", 0.5, "b", 0.3, scores)
        r2 = _combine_actions("b", 0.3, "a", 0.5, scores)
        self.assertEqual(r1.action, r2.action)

    def test_combined_score_between_parents(self) -> None:
        scores = _make_scores(("high", 0.8), ("low", 0.2))
        result = _combine_actions("high", 0.8, "low", 0.2, scores)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.estimated_score, 0.2)
        self.assertLessEqual(result.estimated_score, 0.8)

    def test_both_zero_returns_none(self) -> None:
        scores = _make_scores(("a", 0.0), ("b", 0.0))
        result = _combine_actions("a", 0.0, "b", 0.0, scores)
        self.assertIsNone(result)

    def test_duplicate_combo_returns_none(self) -> None:
        scores = _make_scores(("a", 0.5), ("b", 0.3), ("combo_a_b", 0.4))
        result = _combine_actions("a", 0.5, "b", 0.3, scores)
        self.assertIsNone(result)


# ─── Exploration seed ────────────────────────────────────────────


class TestExplorationSeed(unittest.TestCase):
    def test_seeds_from_causal_memory(self) -> None:
        existing = ["outreach", "content"]
        scores = _make_scores(("outreach", 0.5), ("content", 0.3))
        causal = _make_causal_stats(["outreach", "content", "research"])
        result = _seed_novel_action(existing, scores, causal)
        self.assertIsNotNone(result)
        self.assertEqual(result.strategy_type, "seed")
        self.assertEqual(result.action, "research")

    def test_seeds_deterministic_name_without_memory(self) -> None:
        existing = ["a", "b"]
        scores = _make_scores(("a", 0.5), ("b", 0.3))
        result = _seed_novel_action(existing, scores, None)
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "seed_2")
        self.assertEqual(result.estimated_score, SEED_SCORE_FLOOR)

    def test_no_duplicate_seed(self) -> None:
        existing = ["a", "b"]
        scores = _make_scores(("a", 0.5), ("b", 0.3), ("seed_2", 0.1))
        result = _seed_novel_action(existing, scores, None)
        self.assertIsNone(result)


# ─── Core synthesis ──────────────────────────────────────────────


class TestSynthesizeActions(unittest.TestCase):
    def test_no_trigger_returns_inactive(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.9,
        )
        self.assertFalse(result.active)

    def test_low_confidence_triggers_synthesis(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        self.assertTrue(result.active)
        self.assertGreater(result.synthesis_produced, 0)

    def test_bounded_to_max_candidates(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b", "c"],
            strategy_scores={"a": 0.5, "b": 0.3, "c": 0.2},
            planner_confidence=0.1,
            current_step=100,
        )
        self.assertLessEqual(len(result.new_actions), MAX_NEW_CANDIDATES)

    def test_unstable_context_blocks(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            context_type="volatile",
            current_step=100,
        )
        self.assertFalse(result.active)
        self.assertIn("gated", result.trigger_reason)

    def test_high_uncertainty_blocks(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            uncertainty=0.9,
            current_step=100,
        )
        self.assertFalse(result.active)

    def test_cooldown_blocks(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            last_synthesis_step=98,
            current_step=100,
        )
        self.assertFalse(result.active)

    def test_insufficient_base_candidates_blocks(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a"],
            strategy_scores={"a": 0.5},
            planner_confidence=0.1,
            current_step=100,
        )
        self.assertFalse(result.active)

    def test_plateau_triggers_synthesis(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            reward_history=_flat_reward_history(),
            current_step=100,
        )
        self.assertTrue(result.active)

    def test_regime_stagnation_triggers(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            regime_active=True,
            regime_strength=0.5,
            current_step=100,
        )
        self.assertTrue(result.active)

    def test_all_high_risk_triggers(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            risk_scores={"a": 0.6, "b": 0.7},
            current_step=100,
        )
        self.assertTrue(result.active)


# ─── Candidate expansion ────────────────────────────────────────


class TestExpandCandidateSet(unittest.TestCase):
    def test_expands_with_new_actions(self) -> None:
        actions = ["a", "b"]
        scores = {"a": 0.5, "b": 0.3}
        synth_result = synthesize_actions(
            candidate_actions=actions,
            strategy_scores=scores,
            planner_confidence=0.1,
            current_step=100,
        )
        expanded_actions, expanded_scores = expand_candidate_set(
            actions, scores, synth_result
        )
        self.assertGreater(len(expanded_actions), len(actions))
        self.assertGreater(len(expanded_scores), len(scores))

    def test_inactive_synthesis_no_change(self) -> None:
        actions = ["a", "b"]
        scores = {"a": 0.5, "b": 0.3}
        expanded_actions, expanded_scores = expand_candidate_set(
            actions, scores, NO_SYNTHESIS
        )
        self.assertEqual(expanded_actions, actions)
        self.assertEqual(expanded_scores, scores)

    def test_no_input_mutation(self) -> None:
        actions = ["a", "b"]
        scores = {"a": 0.5, "b": 0.3}
        original_actions = list(actions)
        original_scores = dict(scores)

        synth_result = synthesize_actions(
            candidate_actions=actions,
            strategy_scores=scores,
            planner_confidence=0.1,
            current_step=100,
        )
        expand_candidate_set(actions, scores, synth_result)

        self.assertEqual(actions, original_actions)
        self.assertEqual(scores, original_scores)


# ─── Memory integration ─────────────────────────────────────────


class TestSynthesisMemory(unittest.TestCase):
    def test_records_generation(self) -> None:
        mem = SynthesisMemory()
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        mem.record_generation(result, 100)
        self.assertGreater(mem.generated_count, 0)
        self.assertEqual(mem.last_synthesis_step, 100)

    def test_records_selection(self) -> None:
        mem = SynthesisMemory()
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        if result.active and result.new_actions:
            synth_action = result.new_actions[0].action
            mem.record_generation(result, 100)
            mem.record_selection(synth_action, result)
            self.assertEqual(mem.selected_count, 1)

    def test_non_synth_selection_not_counted(self) -> None:
        mem = SynthesisMemory()
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        mem.record_generation(result, 100)
        mem.record_selection("a", result)
        self.assertEqual(mem.selected_count, 0)

    def test_success_rate(self) -> None:
        mem = SynthesisMemory()
        mem.generated_count = 10
        mem.selected_count = 3
        self.assertAlmostEqual(mem.success_rate(), 0.3)

    def test_success_rate_by_type(self) -> None:
        mem = SynthesisMemory()
        mem.mutation_attempts = 5
        mem.mutation_successes = 2
        self.assertAlmostEqual(mem.success_rate("mutation"), 0.4)

    def test_snapshot_restore_roundtrip(self) -> None:
        mem = SynthesisMemory()
        mem.generated_count = 10
        mem.selected_count = 3
        mem.mutation_attempts = 5
        mem.mutation_successes = 2
        mem.last_synthesis_step = 42

        data = mem.snapshot()
        mem2 = SynthesisMemory()
        mem2.restore(data)

        self.assertEqual(mem2.generated_count, 10)
        self.assertEqual(mem2.selected_count, 3)
        self.assertEqual(mem2.mutation_attempts, 5)
        self.assertEqual(mem2.mutation_successes, 2)
        self.assertEqual(mem2.last_synthesis_step, 42)

    def test_inactive_synthesis_not_recorded(self) -> None:
        mem = SynthesisMemory()
        mem.record_generation(NO_SYNTHESIS, 0)
        self.assertEqual(mem.generated_count, 0)


# ─── Trace fields ───────────────────────────────────────────────


class TestTraceFields(unittest.TestCase):
    def test_no_synthesis_returns_no_trace(self) -> None:
        trace = extract_trace_fields(NO_SYNTHESIS, None)
        self.assertFalse(trace.strategy_generated)
        self.assertEqual(trace.strategy_type, "none")
        self.assertFalse(trace.strategy_selected)

    def test_synthesized_selected(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        if result.active and result.new_actions:
            synth_action = result.new_actions[0].action
            trace = extract_trace_fields(result, synth_action)
            self.assertTrue(trace.strategy_generated)
            self.assertTrue(trace.strategy_selected)
            self.assertNotEqual(trace.strategy_type, "none")

    def test_synthesized_not_selected(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        if result.active:
            trace = extract_trace_fields(result, "a")
            self.assertTrue(trace.strategy_generated)
            self.assertFalse(trace.strategy_selected)

    def test_trace_to_dict(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        if result.active and result.new_actions:
            synth_action = result.new_actions[0].action
            trace = extract_trace_fields(result, synth_action)
            d = trace.to_dict()
            self.assertIn("strategy_generated", d)
            self.assertIn("strategy_type", d)
            self.assertIn("strategy_origin", d)
            self.assertIn("strategy_selected", d)


# ─── No explosion of candidates ─────────────────────────────────


class TestBoundedBehavior(unittest.TestCase):
    def test_repeated_synthesis_respects_bound(self) -> None:
        """Even with strong triggers, output is bounded."""
        for _ in range(10):
            result = synthesize_actions(
                candidate_actions=["a", "b", "c", "d", "e"],
                strategy_scores={"a": 0.5, "b": 0.3, "c": 0.2, "d": 0.1, "e": 0.05},
                planner_confidence=0.05,
                risk_scores={"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.6, "e": 0.9},
                reward_history=_flat_reward_history(),
                regime_active=True,
                regime_strength=0.8,
                current_step=100,
            )
            self.assertLessEqual(len(result.new_actions), MAX_NEW_CANDIDATES)

    def test_synthesized_actions_have_valid_names(self) -> None:
        result = synthesize_actions(
            candidate_actions=["outreach", "content"],
            strategy_scores={"outreach": 0.5, "content": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        for action in result.new_actions:
            self.assertIsInstance(action.action, str)
            self.assertGreater(len(action.action), 0)
            self.assertIn(action.strategy_type, ("mutation", "combination", "seed"))

    def test_all_generated_scores_positive(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        for action in result.new_actions:
            self.assertGreater(action.estimated_score, 0.0)


# ─── Integration with planner/risk ──────────────────────────────


class TestIntegrationWithPlanner(unittest.TestCase):
    def test_expanded_set_works_with_evaluate_trajectories(self) -> None:
        """Synthesized actions can be passed to the planner."""
        from umh.runtime_engine.action_planner import evaluate_trajectories

        actions = ["a", "b"]
        scores = {"a": 0.5, "b": 0.3}

        result = synthesize_actions(
            candidate_actions=actions,
            strategy_scores=scores,
            planner_confidence=0.1,
            current_step=100,
        )
        expanded_actions, expanded_scores = expand_candidate_set(
            actions, scores, result
        )

        causal_stats = _make_causal_stats(expanded_actions)
        planner_result = evaluate_trajectories(
            candidate_actions=expanded_actions,
            context_type="stable",
            causal_stats=causal_stats,
            strategy_scores=expanded_scores,
        )
        self.assertIsNotNone(planner_result)

    def test_expanded_set_works_with_risk_model(self) -> None:
        """Synthesized actions can be passed to the risk model."""
        from umh.runtime_engine.risk_model import assess_actions

        actions = ["a", "b"]
        scores = {"a": 0.5, "b": 0.3}

        result = synthesize_actions(
            candidate_actions=actions,
            strategy_scores=scores,
            planner_confidence=0.1,
            current_step=100,
        )
        expanded_actions, expanded_scores = expand_candidate_set(
            actions, scores, result
        )

        assessment = assess_actions(
            actions=expanded_actions,
            expected_rewards=expanded_scores,
        )
        self.assertIsNotNone(assessment)
        self.assertEqual(len(assessment.estimates), len(expanded_actions))


# ─── No regression ───────────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_existing_planner_unaffected_without_synthesis(self) -> None:
        """When synthesis is inactive, planner behavior is unchanged."""
        from umh.runtime_engine.action_planner import evaluate_trajectories

        actions = ["alpha", "beta", "gamma"]
        causal = _make_causal_stats(actions)
        scores = {"alpha": 0.8, "beta": 0.5, "gamma": 0.2}

        result = evaluate_trajectories(
            candidate_actions=actions,
            context_type="stable",
            causal_stats=causal,
            strategy_scores=scores,
        )

        self.assertIsNotNone(result)
        for action in actions:
            if action in result.trajectory_scores:
                self.assertIsInstance(result.trajectory_scores[action], float)

    def test_risk_model_unaffected_without_synthesis(self) -> None:
        from umh.runtime_engine.risk_model import assess_actions

        actions = ["x", "y"]
        scores = {"x": 0.4, "y": 0.6}

        assessment = assess_actions(actions=actions, expected_rewards=scores)
        self.assertIsNotNone(assessment)
        self.assertFalse(assessment.any_blocked)


# ─── Determinism ─────────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_same_outputs(self) -> None:
        """Synthesis must be deterministic — no randomness."""
        kwargs = dict(
            candidate_actions=["a", "b", "c"],
            strategy_scores={"a": 0.5, "b": 0.3, "c": 0.1},
            planner_confidence=0.1,
            risk_scores={"a": 0.6, "b": 0.7, "c": 0.8},
            reward_history=_flat_reward_history(),
            regime_active=True,
            regime_strength=0.5,
            current_step=100,
        )
        results = [synthesize_actions(**kwargs).to_dict() for _ in range(5)]
        for i in range(1, len(results)):
            self.assertEqual(results[0], results[i])


# ─── Serialization ──────────────────────────────────────────────


class TestSerialization(unittest.TestCase):
    def test_synthesis_result_to_dict(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        d = result.to_dict()
        self.assertIn("active", d)
        self.assertIn("new_actions", d)
        self.assertIn("trigger_reason", d)

    def test_synthesized_action_to_dict(self) -> None:
        result = synthesize_actions(
            candidate_actions=["a", "b"],
            strategy_scores={"a": 0.5, "b": 0.3},
            planner_confidence=0.1,
            current_step=100,
        )
        if result.new_actions:
            d = result.new_actions[0].to_dict()
            self.assertIn("action", d)
            self.assertIn("strategy_type", d)
            self.assertIn("strategy_origin", d)


if __name__ == "__main__":
    unittest.main()
