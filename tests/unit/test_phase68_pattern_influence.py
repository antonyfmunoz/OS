"""Phase 68 — Pattern Influence Layer v1 tests.

Tests bounded pattern-based scoring adjustment: gating logic, signal
computation, safety clamping, determinism, isolation, and orchestrator
integration. Covers invariants 323-333.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.pattern_influence import (
    PatternInfluenceConfig,
    PatternInfluenceResult,
    _FACTOR_CEILING,
    _FACTOR_FLOOR,
    compute_pattern_influence,
)
from umh.runtime.pattern_matching import (
    PatternMatch,
    PatternResult,
)
from umh.runtime.pattern_memory import (
    PatternKey,
    PatternMemory,
    PatternRecord,
    PatternStats,
    RiskLevel,
    StabilityLevel,
    TrendDirection,
    UrgencyLevel,
)
from umh.runtime.strategy_orchestrator import (
    StrategyCandidate,
    StrategyOrchestrationPolicy,
    StrategySelectionResult,
    orchestrate_selection,
)


# ── Helpers ──────────────────────────────────────────────────────


def _key(
    trend: TrendDirection = TrendDirection.UP,
    risk: RiskLevel = RiskLevel.LOW,
    stability: StabilityLevel = StabilityLevel.HIGH,
    urgency: UrgencyLevel = UrgencyLevel.LOW,
) -> PatternKey:
    return PatternKey(
        trend_direction=trend,
        risk_level=risk,
        stability_level=stability,
        urgency_level=urgency,
    )


def _stats(
    key: PatternKey | None = None,
    count: int = 20,
    avg_score: float = 0.8,
    success_rate: float = 0.75,
) -> PatternStats:
    return PatternStats(
        key=key or _key(),
        count=count,
        avg_score=avg_score,
        success_rate=success_rate,
    )


def _match(
    similarity: float = 1.0,
    sample_size: int = 20,
    stats: PatternStats | None = None,
    key: PatternKey | None = None,
) -> PatternMatch:
    return PatternMatch(
        matched_key=key or _key(),
        similarity=similarity,
        stats=stats or _stats(key=key or _key()),
        sample_size=sample_size,
    )


def _pattern_result(
    matched: bool = True,
    best_match: PatternMatch | None = None,
    confidence: float = 0.8,
) -> PatternResult:
    bm = best_match or _match()
    return PatternResult(
        matched=matched,
        best_match=bm,
        all_matches=(bm,),
        query_key=_key(),
        confidence=confidence,
        total_patterns_searched=1,
        explanation="test",
    )


def _enabled_config(**overrides) -> PatternInfluenceConfig:
    defaults = {
        "enabled": True,
        "min_samples": 10,
        "min_confidence": 0.6,
        "max_adjustment": 0.10,
        "similarity_threshold": 0.75,
    }
    defaults.update(overrides)
    return PatternInfluenceConfig(**defaults)


# ── GATING TESTS ─────────────────────────────────────────────────


class TestGatingDisabled:
    def test_disabled_returns_neutral(self):
        cfg = PatternInfluenceConfig(enabled=False)
        r = compute_pattern_influence(
            pattern_result=_pattern_result(),
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied
        assert "disabled" in r.reason_if_not_applied

    def test_default_config_disabled(self):
        cfg = PatternInfluenceConfig()
        assert not cfg.enabled
        r = compute_pattern_influence(
            pattern_result=_pattern_result(),
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied


class TestGatingLowSamples:
    def test_below_min_samples_neutral(self):
        cfg = _enabled_config(min_samples=20)
        pr = _pattern_result(best_match=_match(sample_size=10))
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied
        assert "sample_size" in r.reason_if_not_applied

    def test_exact_min_samples_passes(self):
        cfg = _enabled_config(min_samples=20)
        pr = _pattern_result(best_match=_match(sample_size=20))
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.applied


class TestGatingLowConfidence:
    def test_below_min_confidence_neutral(self):
        cfg = _enabled_config(min_confidence=0.8)
        pr = _pattern_result(confidence=0.5)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied
        assert "confidence" in r.reason_if_not_applied

    def test_exact_min_confidence_passes(self):
        cfg = _enabled_config(min_confidence=0.6)
        pr = _pattern_result(confidence=0.6)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.applied


class TestGatingLowSimilarity:
    def test_below_similarity_threshold_neutral(self):
        cfg = _enabled_config(similarity_threshold=0.9)
        pr = _pattern_result(best_match=_match(similarity=0.75))
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied
        assert "similarity" in r.reason_if_not_applied

    def test_exact_similarity_threshold_passes(self):
        cfg = _enabled_config(similarity_threshold=0.75)
        pr = _pattern_result(best_match=_match(similarity=0.75))
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.applied


# ── BASIC INFLUENCE TESTS ────────────────────────────────────────


class TestBasicInfluence:
    def test_valid_pattern_applies_influence(self):
        stats = _stats(avg_score=0.8)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.applied
        assert r.factor > 1.0
        assert r.sample_size == 20
        assert r.confidence == 0.8

    def test_pattern_below_baseline_reduces(self):
        stats = _stats(avg_score=0.4)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.applied
        assert r.factor < 1.0

    def test_pattern_equal_baseline_neutral(self):
        stats = _stats(avg_score=0.5)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.applied
        assert r.factor == 1.0

    def test_contributing_key_reported(self):
        stats = _stats(avg_score=0.8)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.contributing_pattern_key != ""


# ── BOUNDS TESTS ─────────────────────────────────────────────────


class TestBounds:
    def test_capped_at_max_adjustment(self):
        stats = _stats(avg_score=1.0)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config(max_adjustment=0.05)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.0,
            config=cfg,
        )
        assert r.applied
        assert r.factor == 1.05

    def test_never_exceeds_ceiling(self):
        stats = _stats(avg_score=1.0)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config(max_adjustment=0.20)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.0,
            config=cfg,
        )
        assert r.factor <= _FACTOR_CEILING

    def test_never_below_floor(self):
        stats = _stats(avg_score=0.0)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config(max_adjustment=0.20)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=1.0,
            config=cfg,
        )
        assert r.factor >= _FACTOR_FLOOR

    def test_exact_floor_value(self):
        assert _FACTOR_FLOOR == 0.9

    def test_exact_ceiling_value(self):
        assert _FACTOR_CEILING == 1.1

    def test_negative_adjustment_clamped(self):
        stats = _stats(avg_score=0.0)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config(max_adjustment=0.05)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=1.0,
            config=cfg,
        )
        assert r.factor == 0.95


# ── SAFETY TESTS ─────────────────────────────────────────────────


class TestSafety:
    def test_cannot_flip_clearly_better_candidate(self):
        """A candidate with score 0.9 vs 0.5 — pattern should not flip winner."""
        stats = _stats(avg_score=0.6)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()

        r_high = compute_pattern_influence(pattern_result=pr, candidate_score=0.9, config=cfg)
        r_low = compute_pattern_influence(pattern_result=pr, candidate_score=0.5, config=cfg)

        final_high = 0.9 * r_high.factor
        final_low = 0.5 * r_low.factor
        assert final_high > final_low

    def test_small_differences_only_nudged(self):
        """Close candidates get nudged, not flipped."""
        stats = _stats(avg_score=0.72)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()

        r = compute_pattern_influence(pattern_result=pr, candidate_score=0.70, config=cfg)
        assert 0.9 <= r.factor <= 1.1

    def test_max_adjustment_config_bounded(self):
        cfg = PatternInfluenceConfig(enabled=True, max_adjustment=0.50)
        assert cfg.max_adjustment == 0.2


# ── NEUTRAL / MISSING TESTS ─────────────────────────────────────


class TestNeutral:
    def test_no_pattern_result_neutral(self):
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=None,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied

    def test_no_match_neutral(self):
        pr = PatternResult(matched=False)
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied

    def test_no_best_match_neutral(self):
        pr = PatternResult(matched=True, best_match=None)
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied

    def test_no_stats_neutral(self):
        m = PatternMatch(matched_key=_key(), similarity=1.0, sample_size=20, stats=None)
        pr = _pattern_result(best_match=m)
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.factor == 1.0
        assert not r.applied

    def test_default_config_returns_neutral(self):
        r = compute_pattern_influence(
            pattern_result=_pattern_result(),
            candidate_score=0.5,
        )
        assert r.factor == 1.0
        assert not r.applied


# ── DETERMINISM TESTS ────────────────────────────────────────────


class TestDeterminism:
    def test_repeat_runs_identical(self):
        stats = _stats(avg_score=0.8)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()

        results = []
        for _ in range(50):
            r = compute_pattern_influence(
                pattern_result=pr,
                candidate_score=0.5,
                config=cfg,
            )
            results.append(r.factor)

        assert len(set(results)) == 1


# ── ISOLATION TESTS ──────────────────────────────────────────────


class TestIsolation:
    def test_no_mutation_of_pattern_memory(self):
        mem = PatternMemory()
        k = _key()
        for i in range(15):
            mem.append(PatternRecord(key=k, outcome_score=0.7, confidence=0.8, timestamp=i))

        records_before = mem.size
        from umh.runtime.pattern_matching import match_pattern

        pr = match_pattern(query_key=k, memory=mem)
        cfg = _enabled_config()
        compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert mem.size == records_before

    def test_no_mutation_of_pattern_result(self):
        stats = _stats(avg_score=0.8)
        m = _match(stats=stats)
        pr = _pattern_result(best_match=m)
        original_confidence = pr.confidence
        cfg = _enabled_config()
        compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert pr.confidence == original_confidence


# ── CONFIG TESTS ─────────────────────────────────────────────────


class TestConfig:
    def test_default_config_values(self):
        cfg = PatternInfluenceConfig()
        assert not cfg.enabled
        assert cfg.min_samples == 10
        assert cfg.min_confidence == 0.6
        assert cfg.max_adjustment == 0.10
        assert cfg.similarity_threshold == 0.75

    def test_min_samples_floor(self):
        cfg = PatternInfluenceConfig(enabled=True, min_samples=0)
        assert cfg.min_samples == 1

    def test_to_dict(self):
        cfg = _enabled_config()
        d = cfg.to_dict()
        assert d["enabled"] is True
        assert d["min_samples"] == 10

    def test_result_to_dict(self):
        r = PatternInfluenceResult(
            factor=1.05,
            applied=True,
            contributing_pattern_key="('up', 'low', 'high', 'low')",
            sample_size=20,
            confidence=0.8,
        )
        d = r.to_dict()
        assert d["factor"] == 1.05
        assert d["applied"] is True
        assert d["sample_size"] == 20


# ── EXPLAINABILITY TESTS ────────────────────────────────────────


class TestExplainability:
    def test_applied_result_has_all_fields(self):
        stats = _stats(avg_score=0.8)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert r.applied
        assert r.contributing_pattern_key != ""
        assert r.sample_size > 0
        assert r.confidence > 0
        assert r.reason_if_not_applied == ""

    def test_gated_result_has_reason(self):
        cfg = _enabled_config(min_confidence=0.99)
        pr = _pattern_result(confidence=0.5)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert not r.applied
        assert r.reason_if_not_applied != ""
        assert r.contributing_pattern_key == ""


# ── STRATEGY CANDIDATE TESTS ────────────────────────────────────


class TestStrategyCandidatePatternFactor:
    def test_pattern_factor_in_final_score(self):
        c = StrategyCandidate(
            strategy_id="A",
            base_score=1.0,
            regime_factor=1.0,
            feedback_factor=1.0,
            weight_factor=1.0,
            interaction_factor=1.0,
            pattern_factor=1.05,
        )
        assert abs(c.final_score - 1.05) < 1e-6

    def test_pattern_factor_default_neutral(self):
        c = StrategyCandidate(strategy_id="A", base_score=1.0)
        assert c.pattern_factor == 1.0
        assert c.final_score == 1.0

    def test_pattern_factor_clamped_high(self):
        c = StrategyCandidate(strategy_id="A", base_score=1.0, pattern_factor=2.0)
        assert c.pattern_factor == 1.1

    def test_pattern_factor_clamped_low(self):
        c = StrategyCandidate(strategy_id="A", base_score=1.0, pattern_factor=0.5)
        assert c.pattern_factor == 0.9

    def test_pattern_factor_in_to_dict(self):
        c = StrategyCandidate(strategy_id="A", base_score=1.0, pattern_factor=1.05)
        d = c.to_dict()
        assert "pattern_factor" in d
        assert d["pattern_factor"] == 1.05


# ── ORCHESTRATOR INTEGRATION TESTS ──────────────────────────────


class TestOrchestratorIntegration:
    def test_pattern_disabled_no_effect(self):
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=_pattern_result(),
            pattern_influence_config=PatternInfluenceConfig(enabled=False),
        )
        assert r.selected_strategy == "A"
        assert not r.used_pattern
        assert r.pattern_winner == "A"

    def test_pattern_enabled_applies(self):
        stats = _stats(avg_score=0.85)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.used_pattern
        for c in r.candidates:
            assert c.pattern_factor != 0.0

    def test_pattern_no_config_no_effect(self):
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
        )
        assert not r.used_pattern
        for c in r.candidates:
            assert c.pattern_factor == 1.0

    def test_pattern_factor_in_selection_result(self):
        stats = _stats(avg_score=0.85)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        d = r.to_dict()
        assert "used_pattern" in d
        assert "pattern_winner" in d

    def test_pattern_result_attached(self):
        stats = _stats(avg_score=0.85)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.pattern_influence_result is not None
        assert r.pattern_influence_result.applied

    def test_pattern_in_explanation(self):
        stats = _stats(avg_score=0.85)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert "pattern" in r.explanation.lower()

    def test_pattern_does_not_break_regime(self):
        stats = _stats(avg_score=0.85)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A", "B"],
            base_scores=[0.8, 0.7],
            regime_factors=[1.1, 0.9],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.used_regime
        assert r.base_winner == "A"

    def test_all_six_factors_compose(self):
        stats = _stats(avg_score=0.85)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = orchestrate_selection(
            strategy_ids=["A"],
            base_scores=[0.8],
            regime_factors=[1.05],
            feedback_factors=[1.0],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        c = r.candidates[0]
        expected = (
            c.base_score
            * c.regime_factor
            * c.feedback_factor
            * c.weight_factor
            * c.interaction_factor
            * c.pattern_factor
        )
        assert abs(c.final_score - expected) < 1e-9


# ── EDGE CASE TESTS ─────────────────────────────────────────────


class TestEdgeCases:
    def test_zero_candidate_score(self):
        stats = _stats(avg_score=0.8)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.0,
            config=cfg,
        )
        assert r.applied
        assert r.factor == 1.1

    def test_high_candidate_score(self):
        stats = _stats(avg_score=0.0)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=1.0,
            config=cfg,
        )
        assert r.applied
        assert r.factor == 0.9

    def test_very_small_max_adjustment(self):
        stats = _stats(avg_score=1.0)
        pr = _pattern_result(best_match=_match(stats=stats))
        cfg = _enabled_config(max_adjustment=0.01)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.0,
            config=cfg,
        )
        assert r.factor == 1.01

    def test_multiple_gates_fail_first_wins(self):
        cfg = _enabled_config(min_samples=100, min_confidence=0.99, similarity_threshold=0.99)
        pr = _pattern_result(
            best_match=_match(sample_size=5, similarity=0.5),
            confidence=0.3,
        )
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.5,
            config=cfg,
        )
        assert not r.applied
        assert "sample_size" in r.reason_if_not_applied


# ── FULL E2E WITH REAL MEMORY ────────────────────────────────────


class TestEndToEnd:
    def test_full_pipeline_with_real_memory(self):
        mem = PatternMemory()
        k = _key()
        for i in range(20):
            mem.append(PatternRecord(key=k, outcome_score=0.85, confidence=0.9, timestamp=i))

        from umh.runtime.pattern_matching import match_pattern

        pr = match_pattern(query_key=k, memory=mem, min_similarity=0.5, min_samples=10)
        assert pr.matched

        cfg = _enabled_config()
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.7,
            config=cfg,
        )
        assert r.applied
        assert r.factor > 1.0
        assert r.sample_size == 20

    def test_full_pipeline_insufficient_data(self):
        mem = PatternMemory()
        k = _key()
        for i in range(3):
            mem.append(PatternRecord(key=k, outcome_score=0.85, confidence=0.9, timestamp=i))

        from umh.runtime.pattern_matching import match_pattern

        pr = match_pattern(query_key=k, memory=mem, min_similarity=0.5, min_samples=10)

        cfg = _enabled_config(min_samples=10)
        r = compute_pattern_influence(
            pattern_result=pr,
            candidate_score=0.7,
            config=cfg,
        )
        assert not r.applied

    def test_orchestrator_e2e_with_pattern(self):
        mem = PatternMemory()
        k = _key()
        for i in range(25):
            mem.append(PatternRecord(key=k, outcome_score=0.85, confidence=0.9, timestamp=i))

        from umh.runtime.pattern_matching import match_pattern

        pr = match_pattern(query_key=k, memory=mem, min_similarity=0.5, min_samples=10)
        cfg = _enabled_config()

        r = orchestrate_selection(
            strategy_ids=["X", "Y"],
            base_scores=[0.6, 0.55],
            pattern_result=pr,
            pattern_influence_config=cfg,
        )
        assert r.used_pattern
        assert r.selected_strategy == "X"
        assert r.pattern_influence_result is not None
        assert r.pattern_influence_result.applied
