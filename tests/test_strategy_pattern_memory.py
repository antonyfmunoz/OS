"""Tests for eos/strategy_pattern_memory.py — action pattern learning and reuse."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import unittest

from umh.runtime_engine.strategy_pattern_memory import (
    MAX_BIAS,
    MAX_STRATEGIES,
    MAX_SEQUENCE_LENGTH,
    MIN_CONFIDENCE_FOR_BIAS,
    MIN_OUTCOME_THRESHOLD,
    MIN_SUCCESS_COUNT_FOR_BIAS,
    SIGNATURE_SIMILARITY_THRESHOLD,
    StrategyPatternMemory,
    StrategyRecord,
    StrategySignature,
    build_signature,
    compute_strategy_bias,
    signature_similarity,
    _uncertainty_bucket,
    _has_conflicting_strategies,
)


def _sig(
    ctx: str = "stable",
    mode: str = "default",
    unc: str = "low",
    risk: str = "low",
    signals: tuple[str, ...] = (),
) -> StrategySignature:
    return StrategySignature(
        context_type=ctx,
        objective_mode=mode,
        uncertainty_bucket=unc,
        risk_level=risk,
        dominant_signals=signals,
    )


def _record(
    sid: str = "test_1",
    sig: StrategySignature | None = None,
    seq: tuple[str, ...] = ("a1", "a2"),
    reward: float = 0.5,
    success: int = 3,
    failure: int = 1,
    confidence: float = 0.7,
) -> StrategyRecord:
    return StrategyRecord(
        strategy_id=sid,
        signature=sig or _sig(),
        action_sequence=seq,
        avg_reward=reward,
        success_count=success,
        failure_count=failure,
        confidence=confidence,
    )


# ─── Signature construction ──────────────────────────────────


class TestSignatureConstruction(unittest.TestCase):
    def test_default_signature(self):
        sig = build_signature()
        self.assertEqual(sig.context_type, "unknown")
        self.assertEqual(sig.objective_mode, "default")
        self.assertEqual(sig.uncertainty_bucket, "low")
        self.assertEqual(sig.risk_level, "low")

    def test_uncertainty_buckets(self):
        self.assertEqual(_uncertainty_bucket(0.0), "low")
        self.assertEqual(_uncertainty_bucket(0.1), "low")
        self.assertEqual(_uncertainty_bucket(0.3), "medium")
        self.assertEqual(_uncertainty_bucket(0.6), "high")

    def test_risk_buckets(self):
        sig_low = build_signature(risk_level=0.1)
        sig_med = build_signature(risk_level=0.4)
        sig_hi = build_signature(risk_level=0.8)
        self.assertEqual(sig_low.risk_level, "low")
        self.assertEqual(sig_med.risk_level, "medium")
        self.assertEqual(sig_hi.risk_level, "high")

    def test_dominant_signals_capped_to_3(self):
        sig = build_signature(dominant_signals=("a", "b", "c", "d", "e"))
        self.assertEqual(len(sig.dominant_signals), 3)

    def test_serialization(self):
        sig = build_signature(context_type="stable", objective_mode="adversarial")
        d = sig.to_dict()
        self.assertEqual(d["context_type"], "stable")
        self.assertEqual(d["objective_mode"], "adversarial")


# ─── Signature similarity ────────────────────────────────────


class TestSignatureSimilarity(unittest.TestCase):
    def test_identical_signatures(self):
        a = _sig()
        self.assertAlmostEqual(signature_similarity(a, a), 1.0, places=4)

    def test_completely_different(self):
        a = _sig(ctx="stable", mode="default", unc="low", risk="low")
        b = _sig(ctx="adversarial", mode="plateau", unc="high", risk="high")
        sim = signature_similarity(a, b)
        self.assertLess(sim, SIGNATURE_SIMILARITY_THRESHOLD)

    def test_partial_match(self):
        a = _sig(ctx="stable", mode="default", unc="low", risk="low")
        b = _sig(ctx="stable", mode="default", unc="medium", risk="low")
        sim = signature_similarity(a, b)
        self.assertGreater(sim, 0.5)

    def test_signal_overlap_increases_similarity(self):
        a = _sig(signals=("revenue", "cost"))
        b_overlap = _sig(signals=("revenue", "growth"))
        b_none = _sig(signals=("churn", "growth"))
        sim_overlap = signature_similarity(a, b_overlap)
        sim_none = signature_similarity(a, b_none)
        self.assertGreater(sim_overlap, sim_none)

    def test_symmetry(self):
        a = _sig(ctx="stable")
        b = _sig(ctx="volatile")
        self.assertAlmostEqual(
            signature_similarity(a, b), signature_similarity(b, a), places=6
        )


# ─── Memory store ────────────────────────────────────────────


class TestMemoryStore(unittest.TestCase):
    def test_empty_store(self):
        mem = StrategyPatternMemory()
        self.assertEqual(mem.size, 0)

    def test_record_and_retrieve(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        mem.record_outcome(sig, ("a1", "a2"), outcome_score=0.5)
        self.assertEqual(mem.size, 1)

    def test_below_threshold_not_stored(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        result = mem.record_outcome(sig, ("a1",), outcome_score=0.01)
        self.assertFalse(result)
        self.assertEqual(mem.size, 0)

    def test_merge_identical_signatures(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        mem.record_outcome(sig, ("a1",), outcome_score=0.5)
        mem.record_outcome(sig, ("a1",), outcome_score=0.6)
        self.assertEqual(mem.size, 1)

    def test_different_sequences_separate_records(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        mem.record_outcome(sig, ("a1",), outcome_score=0.5)
        mem.record_outcome(sig, ("a2",), outcome_score=0.5)
        self.assertEqual(mem.size, 2)

    def test_empty_sequence_not_stored(self):
        mem = StrategyPatternMemory()
        result = mem.record_outcome(_sig(), (), outcome_score=0.5)
        self.assertFalse(result)

    def test_sequence_capped(self):
        mem = StrategyPatternMemory()
        long_seq = tuple(f"a{i}" for i in range(10))
        mem.record_outcome(_sig(), long_seq, outcome_score=0.5)
        records = mem.all_records()
        self.assertLessEqual(len(records[0].action_sequence), MAX_SEQUENCE_LENGTH)


# ─── Bounded memory ──────────────────────────────────────────


class TestBoundedMemory(unittest.TestCase):
    def test_fifo_eviction(self):
        mem = StrategyPatternMemory(max_strategies=3)
        for i in range(5):
            sig = _sig(ctx=f"ctx_{i}")
            mem.record_outcome(sig, (f"a{i}",), outcome_score=0.5)
        self.assertLessEqual(mem.size, 3)

    def test_max_strategies_respected(self):
        mem = StrategyPatternMemory(max_strategies=MAX_STRATEGIES)
        for i in range(MAX_STRATEGIES + 10):
            sig = _sig(ctx=f"ctx_{i}")
            mem.record_outcome(sig, (f"a{i}",), outcome_score=0.5)
        self.assertLessEqual(mem.size, MAX_STRATEGIES)

    def test_oldest_evicted_first(self):
        mem = StrategyPatternMemory(max_strategies=2)
        sig0 = _sig(ctx="ctx_0")
        sig1 = _sig(ctx="ctx_1")
        sig2 = _sig(ctx="ctx_2")
        mem.record_outcome(sig0, ("a0",), outcome_score=0.5)
        mem.record_outcome(sig1, ("a1",), outcome_score=0.5)
        mem.record_outcome(sig2, ("a2",), outcome_score=0.5)
        records = mem.all_records()
        ids = [r.strategy_id for r in records]
        first_id = [
            r.strategy_id for r in records if r.signature.context_type == "ctx_0"
        ]
        self.assertEqual(len(first_id), 0)


# ─── Matching ────────────────────────────────────────────────


class TestMatching(unittest.TestCase):
    def test_exact_match(self):
        mem = StrategyPatternMemory()
        sig = _sig(ctx="stable", mode="default")
        mem.record_outcome(sig, ("a1",), outcome_score=0.5)
        matched = mem.find_matching(sig)
        self.assertEqual(len(matched), 1)

    def test_no_match_different_context(self):
        mem = StrategyPatternMemory()
        sig1 = _sig(ctx="stable", mode="default", unc="low", risk="low")
        sig2 = _sig(ctx="adversarial", mode="plateau", unc="high", risk="high")
        mem.record_outcome(sig1, ("a1",), outcome_score=0.5)
        matched = mem.find_matching(sig2)
        self.assertEqual(len(matched), 0)

    def test_partial_match_above_threshold(self):
        mem = StrategyPatternMemory()
        sig1 = _sig(ctx="stable", mode="default", unc="low", risk="low")
        sig2 = _sig(ctx="stable", mode="default", unc="medium", risk="low")
        mem.record_outcome(sig1, ("a1",), outcome_score=0.5)
        matched = mem.find_matching(sig2)
        self.assertGreater(len(matched), 0)

    def test_max_results_respected(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        for i in range(10):
            mem.record_outcome(sig, (f"a{i}",), outcome_score=0.5)
        matched = mem.find_matching(sig, max_results=2)
        self.assertLessEqual(len(matched), 2)


# ─── Bias computation ────────────────────────────────────────


class TestBiasComputation(unittest.TestCase):
    def test_no_strategies_no_bias(self):
        b = compute_strategy_bias("a1", [])
        self.assertAlmostEqual(b, 0.0, places=6)

    def test_matching_action_gets_positive_bias(self):
        rec = _record(seq=("a1", "a2"), confidence=0.8, success=5, failure=1)
        b = compute_strategy_bias("a1", [rec])
        self.assertGreater(b, 0.0)

    def test_non_matching_action_no_bias(self):
        rec = _record(seq=("a1", "a2"), confidence=0.8, success=5, failure=1)
        b = compute_strategy_bias("a3", [rec])
        self.assertAlmostEqual(b, 0.0, places=6)

    def test_bias_bounded(self):
        rec = _record(seq=("a1",), confidence=1.0, success=100, failure=0)
        b = compute_strategy_bias("a1", [rec])
        self.assertLessEqual(abs(b), MAX_BIAS)

    def test_low_confidence_no_bias(self):
        rec = _record(confidence=0.1, success=5, failure=1)
        b = compute_strategy_bias("a1", [rec])
        self.assertAlmostEqual(b, 0.0, places=6)

    def test_insufficient_success_no_bias(self):
        rec = _record(confidence=0.8, success=1, failure=0)
        b = compute_strategy_bias("a1", [rec])
        self.assertAlmostEqual(b, 0.0, places=6)

    def test_position_weighting(self):
        rec = _record(seq=("a1", "a2", "a3"), confidence=0.8, success=5, failure=1)
        b1 = compute_strategy_bias("a1", [rec])
        b2 = compute_strategy_bias("a2", [rec])
        self.assertGreater(b1, b2)


# ─── Safety gating ───────────────────────────────────────────


class TestSafetyGating(unittest.TestCase):
    def test_non_stable_context_no_bias(self):
        mem = StrategyPatternMemory()
        sig = _sig(ctx="stable")
        mem.record_outcome(sig, ("a1",), outcome_score=0.5)
        biases = mem.get_action_biases(
            query=sig, action_ids=("a1",), context_type="volatile"
        )
        self.assertEqual(biases, {})

    def test_stable_context_allows_bias(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        for _ in range(5):
            mem.record_outcome(sig, ("a1",), outcome_score=0.8)
        biases = mem.get_action_biases(
            query=sig, action_ids=("a1",), context_type="stable"
        )
        self.assertIsInstance(biases, dict)

    def test_conflicting_strategies_no_bias(self):
        rec1 = _record(sid="s1", seq=("a1",), confidence=0.8, success=5, failure=1)
        rec2 = _record(sid="s2", seq=("a2",), confidence=0.8, success=5, failure=1)
        self.assertTrue(_has_conflicting_strategies([rec1, rec2], ("a1", "a2")))

    def test_no_conflict_with_single_strategy(self):
        rec = _record(seq=("a1",), confidence=0.8)
        self.assertFalse(_has_conflicting_strategies([rec], ("a1",)))

    def test_no_conflict_when_confidence_gap(self):
        rec1 = _record(sid="s1", seq=("a1",), confidence=0.9)
        rec2 = _record(sid="s2", seq=("a2",), confidence=0.3)
        self.assertFalse(_has_conflicting_strategies([rec1, rec2], ("a1", "a2")))


# ─── Learning / EMA updates ──────────────────────────────────


class TestLearning(unittest.TestCase):
    def test_success_count_increments(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        mem.record_outcome(sig, ("a1",), outcome_score=0.5)
        mem.record_outcome(sig, ("a1",), outcome_score=0.6)
        mem.record_outcome(sig, ("a1",), outcome_score=0.7)
        records = mem.all_records()
        self.assertEqual(records[0].success_count, 3)

    def test_failure_count_increments(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        mem.record_outcome(sig, ("a1",), outcome_score=0.5)
        mem.record_outcome(sig, ("a1",), outcome_score=0.01)
        records = mem.all_records()
        self.assertEqual(records[0].failure_count, 1)

    def test_ema_updates_reward(self):
        mem = StrategyPatternMemory()
        sig = _sig()
        mem.record_outcome(sig, ("a1",), outcome_score=0.5)
        initial_reward = mem.all_records()[0].avg_reward
        mem.record_outcome(sig, ("a1",), outcome_score=0.9)
        updated_reward = mem.all_records()[0].avg_reward
        self.assertGreater(updated_reward, initial_reward)

    def test_win_rate_computation(self):
        rec = _record(success=3, failure=1)
        self.assertAlmostEqual(rec.win_rate(), 0.75, places=4)


# ─── Deterministic behavior ──────────────────────────────────


class TestDeterministicBehavior(unittest.TestCase):
    def test_same_inputs_same_output(self):
        mem1 = StrategyPatternMemory()
        mem2 = StrategyPatternMemory()
        sig = _sig()
        mem1.record_outcome(sig, ("a1",), outcome_score=0.5)
        mem2.record_outcome(sig, ("a1",), outcome_score=0.5)
        m1 = mem1.find_matching(sig)
        m2 = mem2.find_matching(sig)
        self.assertEqual(len(m1), len(m2))
        self.assertEqual(m1[0].strategy_id, m2[0].strategy_id)

    def test_record_serialization(self):
        rec = _record()
        d = rec.to_dict()
        self.assertIn("strategy_id", d)
        self.assertIn("win_rate", d)
        self.assertIn("action_sequence", d)

    def test_step_counter(self):
        mem = StrategyPatternMemory()
        mem.record_outcome(_sig(), ("a1",), outcome_score=0.5, step=10)
        self.assertEqual(mem.step, 10)


# ─── Trace integration ───────────────────────────────────────


class TestTraceIntegration(unittest.TestCase):
    def test_decision_trace_has_pattern_fields(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        t = DecisionTrace(
            turn_id=0,
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
            strat_pattern_match_found=True,
            strat_pattern_confidence=0.8,
            strat_pattern_bias_applied=True,
            strat_pattern_id="sp_test_1",
        )
        d = t.to_dict()
        self.assertTrue(d["strat_pattern_match_found"])
        self.assertAlmostEqual(d["strat_pattern_confidence"], 0.8, places=4)
        self.assertEqual(d["strat_pattern_id"], "sp_test_1")

    def test_trace_omits_pattern_when_none(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        t = DecisionTrace(
            turn_id=0,
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
        d = t.to_dict()
        self.assertNotIn("strat_pattern_match_found", d)

    def test_build_trace_accepts_pattern_params(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            strat_pattern_match_found=True,
            strat_pattern_confidence=0.7,
            strat_pattern_bias_applied=False,
            strat_pattern_id="sp_test_2",
        )
        self.assertTrue(trace.strat_pattern_match_found)
        self.assertEqual(trace.strat_pattern_id, "sp_test_2")

    def test_pattern_memory_trace_fields(self):
        mem = StrategyPatternMemory()
        fields = mem.get_trace_fields()
        self.assertIn("strat_pattern_count", fields)
        self.assertIn("strat_pattern_step", fields)


# ─── Reset behavior ──────────────────────────────────────────


class TestResetBehavior(unittest.TestCase):
    def test_reset_clears_all(self):
        mem = StrategyPatternMemory()
        mem.record_outcome(_sig(), ("a1",), outcome_score=0.5)
        mem.reset()
        self.assertEqual(mem.size, 0)
        self.assertEqual(mem.step, 0)


# ─── No regression ───────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_strategy_pattern_memory_imports(self):
        from umh.runtime_engine.strategy_pattern_memory import (
            StrategyPatternMemory,
            StrategySignature,
            StrategyRecord,
            build_signature,
            signature_similarity,
            compute_strategy_bias,
            get_strategy_pattern_memory,
            reset_strategy_pattern_memory,
        )

    def test_decision_trace_imports(self):
        from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

    def test_existing_strategy_memory_untouched(self):
        from umh.strategy.memory import (
            StrategyMemory,
            StrategyStats,
            get_strategy_memory,
            reset_strategy_memory,
        )

    def test_objective_arbitration_imports(self):
        from umh.runtime_engine.objective_arbitration import (
            ObjectiveArbiter,
            ObjectiveWeights,
            compute_weighted_score,
        )

    def test_multi_world_policy_imports(self):
        from umh.runtime_engine.multi_world_policy import evaluate_multi_world_policy


if __name__ == "__main__":
    unittest.main()
