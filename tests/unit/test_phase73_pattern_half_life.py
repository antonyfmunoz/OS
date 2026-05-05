"""Phase 73 — Pattern-Specific Half-Life Layer v1.

Tests for per-pattern half-life adjustment based on pattern reliability.
Covers: config, noise/reliability computation, multiplier selection,
half-life clamping, temporal integration, invariants 373-382,
backward compatibility, regression, and the Phase 61 import whitelist fix.

Target: 160–220 tests.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime.pattern_half_life import (
    PatternHalfLifeConfig,
    PatternHalfLifeResult,
    compute_all_pattern_half_lives,
    compute_pattern_half_life,
    compute_pattern_noise,
    compute_pattern_reliability,
)
from umh.runtime.pattern_temporal import (
    TemporalPatternConfig,
    TemporalWeightingResult,
    apply_temporal_weights,
    compute_decay_factor,
)
from umh.runtime.adaptive_half_life import (
    AdaptiveHalfLifeConfig,
    AdaptiveHalfLifeResult,
    compute_adaptive_half_life,
)
from umh.runtime.regime_half_life import (
    RegimeHalfLifeConfig,
    RegimeHalfLifeResult,
    compute_regime_half_life,
)
from umh.runtime.regime import RegimeType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg(**kw) -> PatternHalfLifeConfig:
    kw.setdefault("enabled", True)
    return PatternHalfLifeConfig(**kw)


def _temporal_config(**kw) -> TemporalPatternConfig:
    kw.setdefault("enabled", True)
    return TemporalPatternConfig(**kw)


def _stable_scores(n: int = 20) -> list[float]:
    """Consistent scores -> high reliability."""
    return [0.8] * n


def _noisy_scores(n: int = 20) -> list[float]:
    """Alternating extremes -> high noise."""
    return [0.0 if i % 2 == 0 else 1.0 for i in range(n)]


def _moderate_scores(n: int = 20) -> list[float]:
    """Moderate variance -> neutral."""
    return [0.4 + (i % 3) * 0.1 for i in range(n)]


# ===========================================================================
# SECTION 1 — PatternHalfLifeConfig
# ===========================================================================


class TestPatternHalfLifeConfig:
    def test_defaults(self):
        cfg = PatternHalfLifeConfig()
        assert cfg.enabled is False
        assert cfg.min_samples == 10
        assert cfg.base_multiplier == 1.0
        assert cfg.reliable_multiplier == 1.5
        assert cfg.noisy_multiplier == 0.6
        assert cfg.min_half_life == 10
        assert cfg.max_half_life == 250
        assert cfg.reliability_threshold == 0.70
        assert cfg.noise_threshold == 0.30

    def test_min_samples_clamped(self):
        cfg = PatternHalfLifeConfig(min_samples=0)
        assert cfg.min_samples >= 1

    def test_multiplier_clamped_low(self):
        cfg = PatternHalfLifeConfig(base_multiplier=-1.0)
        assert cfg.base_multiplier >= 0.01

    def test_multiplier_clamped_high(self):
        cfg = PatternHalfLifeConfig(reliable_multiplier=100.0)
        assert cfg.reliable_multiplier <= 10.0

    def test_min_half_life_clamped(self):
        cfg = PatternHalfLifeConfig(min_half_life=0)
        assert cfg.min_half_life >= 1

    def test_max_floors_to_min(self):
        cfg = PatternHalfLifeConfig(min_half_life=100, max_half_life=50)
        assert cfg.max_half_life >= cfg.min_half_life

    def test_threshold_clamped(self):
        cfg = PatternHalfLifeConfig(reliability_threshold=2.0, noise_threshold=-1.0)
        assert 0.0 <= cfg.reliability_threshold <= 1.0
        assert 0.0 <= cfg.noise_threshold <= 1.0

    def test_frozen(self):
        cfg = PatternHalfLifeConfig()
        with pytest.raises(AttributeError):
            cfg.enabled = True  # type: ignore[misc]

    def test_to_dict(self):
        cfg = _cfg()
        d = cfg.to_dict()
        assert "enabled" in d
        assert "min_samples" in d
        assert "base_multiplier" in d
        assert "reliable_multiplier" in d
        assert "noisy_multiplier" in d
        assert "min_half_life" in d
        assert "max_half_life" in d
        assert "reliability_threshold" in d
        assert "noise_threshold" in d

    def test_to_dict_all_keys(self):
        d = _cfg().to_dict()
        expected = {
            "enabled",
            "min_samples",
            "base_multiplier",
            "reliable_multiplier",
            "noisy_multiplier",
            "min_half_life",
            "max_half_life",
            "reliability_threshold",
            "noise_threshold",
        }
        assert set(d.keys()) == expected


# ===========================================================================
# SECTION 2 — Noise and Reliability
# ===========================================================================


class TestPatternNoise:
    def test_constant_scores_zero_noise(self):
        assert compute_pattern_noise([0.5] * 20) == 0.0

    def test_max_variance_noise_one(self):
        scores = [0.0] * 10 + [1.0] * 10
        noise = compute_pattern_noise(scores)
        assert noise == pytest.approx(1.0, abs=0.01)

    def test_alternating_high_noise(self):
        noise = compute_pattern_noise(_noisy_scores(20))
        assert noise > 0.8

    def test_moderate_noise(self):
        noise = compute_pattern_noise(_moderate_scores(20))
        assert 0.0 < noise < 0.5

    def test_single_value_zero(self):
        assert compute_pattern_noise([0.5]) == 0.0

    def test_empty_zero(self):
        assert compute_pattern_noise([]) == 0.0

    def test_bounded_zero_one(self):
        for scores in [[0.1, 0.9, 0.1, 0.9], [0.5, 0.5], [0.0, 1.0]]:
            n = compute_pattern_noise(scores)
            assert 0.0 <= n <= 1.0

    def test_two_values(self):
        noise = compute_pattern_noise([0.0, 1.0])
        assert noise == pytest.approx(1.0, abs=0.01)

    def test_nearly_constant(self):
        scores = [0.5 + 0.001 * i for i in range(20)]
        noise = compute_pattern_noise(scores)
        assert noise < 0.01


class TestPatternReliability:
    def test_constant_scores_full_reliability(self):
        assert compute_pattern_reliability([0.8] * 20) == 1.0

    def test_max_noise_zero_reliability(self):
        scores = [0.0] * 10 + [1.0] * 10
        r = compute_pattern_reliability(scores)
        assert r == pytest.approx(0.0, abs=0.01)

    def test_reliability_plus_noise_equals_one(self):
        scores = _moderate_scores(20)
        n = compute_pattern_noise(scores)
        r = compute_pattern_reliability(scores)
        assert n + r == pytest.approx(1.0, abs=1e-10)

    def test_single_value(self):
        assert compute_pattern_reliability([0.5]) == 1.0

    def test_empty(self):
        assert compute_pattern_reliability([]) == 1.0

    def test_bounded(self):
        r = compute_pattern_reliability(_noisy_scores(20))
        assert 0.0 <= r <= 1.0


# ===========================================================================
# SECTION 3 — Disabled / Fallback
# ===========================================================================


class TestDisabledConfig:
    def test_disabled_returns_base(self):
        r = compute_pattern_half_life("p1", _stable_scores(), 50)
        assert r.pattern_half_life == 50
        assert r.used_fallback is True
        assert "disabled" in r.explanation

    def test_disabled_explicit(self):
        cfg = PatternHalfLifeConfig(enabled=False)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.pattern_half_life == 50
        assert r.used_fallback is True

    def test_insufficient_samples(self):
        cfg = _cfg(min_samples=10)
        r = compute_pattern_half_life("p1", [0.5] * 5, 50, cfg)
        assert r.pattern_half_life == 50
        assert r.used_fallback is True
        assert "insufficient" in r.explanation

    def test_empty_scores(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", [], 50, cfg)
        assert r.used_fallback is True

    def test_none_config_disabled(self):
        r = compute_pattern_half_life("p1", _stable_scores(), 50, None)
        assert r.used_fallback is True


# ===========================================================================
# SECTION 4 — Multiplier Selection
# ===========================================================================


class TestMultiplierSelection:
    def test_reliable_gets_reliable_multiplier(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.multiplier == cfg.reliable_multiplier
        assert "reliable" in r.explanation

    def test_noisy_gets_noisy_multiplier(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _noisy_scores(), 50, cfg)
        assert r.multiplier == cfg.noisy_multiplier
        assert "noisy" in r.explanation

    def test_neutral_gets_base_multiplier(self):
        cfg = _cfg(min_samples=5, reliability_threshold=0.999, noise_threshold=0.999)
        scores = [
            0.3,
            0.5,
            0.7,
            0.3,
            0.5,
            0.7,
            0.3,
            0.5,
            0.7,
            0.3,
            0.5,
            0.7,
            0.3,
            0.5,
            0.7,
            0.3,
            0.5,
            0.7,
            0.3,
            0.5,
        ]
        r = compute_pattern_half_life("p1", scores, 50, cfg)
        assert r.multiplier == cfg.base_multiplier
        assert r.explanation == "neutral"

    def test_reliability_threshold_boundary(self):
        cfg = _cfg(min_samples=2, reliability_threshold=0.99)
        scores = [0.5] * 20
        r = compute_pattern_half_life("p1", scores, 50, cfg)
        assert r.multiplier == cfg.reliable_multiplier

    def test_noise_threshold_boundary(self):
        scores = _noisy_scores(20)
        noise = compute_pattern_noise(scores)
        cfg = _cfg(min_samples=2, noise_threshold=noise - 0.01, reliability_threshold=0.999)
        r = compute_pattern_half_life("p1", scores, 50, cfg)
        assert r.multiplier == cfg.noisy_multiplier


# ===========================================================================
# SECTION 5 — Half-Life Computation
# ===========================================================================


class TestHalfLifeComputation:
    def test_reliable_longer(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.pattern_half_life > 50

    def test_noisy_shorter(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _noisy_scores(), 50, cfg)
        assert r.pattern_half_life < 50

    def test_base_multiplier_preserves(self):
        cfg = _cfg(min_samples=5, reliability_threshold=0.99, noise_threshold=0.99)
        r = compute_pattern_half_life("p1", _moderate_scores(), 50, cfg)
        assert r.pattern_half_life == 50

    def test_computation_formula(self):
        cfg = _cfg(min_samples=5, reliable_multiplier=2.0)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.pattern_half_life == 100

    def test_different_base(self):
        cfg = _cfg(min_samples=5)
        r1 = compute_pattern_half_life("p1", _stable_scores(), 30, cfg)
        r2 = compute_pattern_half_life("p1", _stable_scores(), 80, cfg)
        assert r1.pattern_half_life < r2.pattern_half_life


# ===========================================================================
# SECTION 6 — Clamping (inv 373, 382)
# ===========================================================================


class TestClamping:
    def test_min_enforced(self):
        cfg = _cfg(min_samples=5, noisy_multiplier=0.01, min_half_life=10)
        r = compute_pattern_half_life("p1", _noisy_scores(), 5, cfg)
        assert r.pattern_half_life >= cfg.min_half_life

    def test_max_enforced(self):
        cfg = _cfg(min_samples=5, reliable_multiplier=10.0, max_half_life=100)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.pattern_half_life <= cfg.max_half_life

    def test_min_equals_max(self):
        cfg = _cfg(min_samples=5, min_half_life=50, max_half_life=50)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.pattern_half_life == 50

    def test_extreme_multiplier_bounded(self):
        cfg = _cfg(min_samples=5, reliable_multiplier=10.0, min_half_life=5, max_half_life=300)
        r = compute_pattern_half_life("p1", _stable_scores(), 100, cfg)
        assert cfg.min_half_life <= r.pattern_half_life <= cfg.max_half_life


# ===========================================================================
# SECTION 7 — Invariant 373: Pattern-specific half-life bounded
# ===========================================================================


class TestInvariant373Bounded:
    def test_all_patterns_bounded(self):
        cfg = _cfg(min_samples=5)
        for scores in [_stable_scores(), _noisy_scores(), _moderate_scores()]:
            r = compute_pattern_half_life("p", scores, 50, cfg)
            assert cfg.min_half_life <= r.pattern_half_life <= cfg.max_half_life

    def test_extreme_base_bounded(self):
        cfg = _cfg(min_samples=5, min_half_life=10, max_half_life=200)
        r = compute_pattern_half_life("p", _stable_scores(), 1000, cfg)
        assert r.pattern_half_life <= 200


# ===========================================================================
# SECTION 8 — Invariant 374: Low-sample fallback
# ===========================================================================


class TestInvariant374LowSampleFallback:
    def test_below_min_samples(self):
        cfg = _cfg(min_samples=10)
        r = compute_pattern_half_life("p1", [0.5] * 5, 50, cfg)
        assert r.used_fallback is True
        assert r.pattern_half_life == 50

    def test_exactly_min_samples(self):
        cfg = _cfg(min_samples=10)
        r = compute_pattern_half_life("p1", [0.5] * 10, 50, cfg)
        assert r.used_fallback is False

    def test_above_min_samples(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", [0.5] * 20, 50, cfg)
        assert r.used_fallback is False


# ===========================================================================
# SECTION 9 — Invariant 375: Reliable patterns longer memory
# ===========================================================================


class TestInvariant375ReliableLonger:
    def test_reliable_gt_base(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.pattern_half_life > 50

    def test_reliable_multiplier_applied(self):
        cfg = _cfg(min_samples=5, reliable_multiplier=2.0)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.multiplier == 2.0


# ===========================================================================
# SECTION 10 — Invariant 376: Noisy patterns shorter memory
# ===========================================================================


class TestInvariant376NoisyShorter:
    def test_noisy_lt_base(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _noisy_scores(), 50, cfg)
        assert r.pattern_half_life < 50

    def test_noisy_multiplier_applied(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _noisy_scores(), 50, cfg)
        assert r.multiplier == cfg.noisy_multiplier


# ===========================================================================
# SECTION 11 — Invariant 377: No mutation
# ===========================================================================


class TestInvariant377NoMutation:
    def test_scores_unchanged(self):
        scores = [0.5, 0.6, 0.7, 0.8] * 5
        original = list(scores)
        cfg = _cfg(min_samples=5)
        compute_pattern_half_life("p1", scores, 50, cfg)
        assert scores == original

    def test_config_unchanged(self):
        cfg = _cfg(min_samples=5)
        d_before = cfg.to_dict()
        compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert cfg.to_dict() == d_before


# ===========================================================================
# SECTION 12 — Invariant 378: Deterministic
# ===========================================================================


class TestInvariant378Deterministic:
    def test_repeat_identical(self):
        cfg = _cfg(min_samples=5)
        scores = _moderate_scores(20)
        r1 = compute_pattern_half_life("p1", scores, 50, cfg)
        r2 = compute_pattern_half_life("p1", scores, 50, cfg)
        assert r1.pattern_half_life == r2.pattern_half_life
        assert r1.multiplier == r2.multiplier
        assert r1.reliability == r2.reliability

    def test_hundred_repeats(self):
        cfg = _cfg(min_samples=5)
        scores = _stable_scores()
        results = [compute_pattern_half_life("p1", scores, 50, cfg) for _ in range(100)]
        assert all(r.pattern_half_life == results[0].pattern_half_life for r in results)


# ===========================================================================
# SECTION 13 — Invariant 379: Missing stats neutral fallback
# ===========================================================================


class TestInvariant379MissingStats:
    def test_empty_scores(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", [], 50, cfg)
        assert r.used_fallback is True
        assert r.pattern_half_life == 50

    def test_single_score(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", [0.5], 50, cfg)
        assert r.used_fallback is True


# ===========================================================================
# SECTION 14 — Invariant 380: Explainable
# ===========================================================================


class TestInvariant380Explainable:
    def test_result_has_all_fields(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        assert r.pattern_key == "p1"
        assert r.base_half_life == 50
        assert r.pattern_half_life > 0
        assert r.multiplier > 0
        assert r.sample_count == 20
        assert 0.0 <= r.reliability <= 1.0
        assert 0.0 <= r.noise <= 1.0
        assert r.used_fallback is False
        assert len(r.explanation) > 0

    def test_disabled_has_explanation(self):
        r = compute_pattern_half_life("p1", _stable_scores(), 50)
        assert "disabled" in r.explanation

    def test_to_dict_complete(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        d = r.to_dict()
        expected_keys = {
            "pattern_key",
            "base_half_life",
            "pattern_half_life",
            "multiplier",
            "sample_count",
            "reliability",
            "noise",
            "used_fallback",
            "explanation",
        }
        assert set(d.keys()) == expected_keys


# ===========================================================================
# SECTION 15 — Invariant 381: No scoring feedback loop
# ===========================================================================


class TestInvariant381NoScoringFeedback:
    def test_no_scoring_imports(self):
        import inspect
        import umh.runtime.pattern_half_life as m

        src = inspect.getsource(m)
        forbidden = [
            "from umh.runtime.outcome",
            "from umh.runtime.feedback",
            "from umh.runtime.attribution",
            "from umh.runtime.exploration",
            "from umh.runtime.strategy_orchestrator",
        ]
        for f in forbidden:
            assert f not in src, f"forbidden import found: {f}"

    def test_same_scores_same_result(self):
        cfg = _cfg(min_samples=5)
        r1 = compute_pattern_half_life("p1", [0.9] * 20, 50, cfg)
        r2 = compute_pattern_half_life("p1", [0.1] * 20, 50, cfg)
        assert r1.reliability == r2.reliability
        assert r1.multiplier == r2.multiplier


# ===========================================================================
# SECTION 16 — Invariant 382: No pattern exceeds min/max
# ===========================================================================


class TestInvariant382MinMax:
    def test_all_regimes_bounded(self):
        cfg = _cfg(min_samples=5, min_half_life=15, max_half_life=150)
        for base in [5, 50, 500]:
            for scores in [_stable_scores(), _noisy_scores(), _moderate_scores()]:
                r = compute_pattern_half_life("p", scores, base, cfg)
                assert cfg.min_half_life <= r.pattern_half_life <= cfg.max_half_life

    def test_tiny_base_respects_min(self):
        cfg = _cfg(min_samples=5, min_half_life=10)
        r = compute_pattern_half_life("p", _noisy_scores(), 1, cfg)
        assert r.pattern_half_life >= 10

    def test_huge_base_respects_max(self):
        cfg = _cfg(min_samples=5, max_half_life=200)
        r = compute_pattern_half_life("p", _stable_scores(), 1000, cfg)
        assert r.pattern_half_life <= 200


# ===========================================================================
# SECTION 17 — Batch computation
# ===========================================================================


class TestBatchComputation:
    def test_all_pattern_half_lives(self):
        cfg = _cfg(min_samples=5)
        keys = ["p1", "p2", "p3"]
        scores_map = {
            "p1": _stable_scores(),
            "p2": _noisy_scores(),
            "p3": _moderate_scores(),
        }
        results = compute_all_pattern_half_lives(keys, scores_map, 50, cfg)
        assert len(results) == 3
        assert results[0].pattern_key == "p1"
        assert results[1].pattern_key == "p2"
        assert results[2].pattern_key == "p3"

    def test_missing_key_fallback(self):
        cfg = _cfg(min_samples=5)
        results = compute_all_pattern_half_lives(["p1"], {}, 50, cfg)
        assert len(results) == 1
        assert results[0].used_fallback is True

    def test_batch_deterministic(self):
        cfg = _cfg(min_samples=5)
        keys = ["a", "b"]
        sm = {"a": _stable_scores(), "b": _noisy_scores()}
        r1 = compute_all_pattern_half_lives(keys, sm, 50, cfg)
        r2 = compute_all_pattern_half_lives(keys, sm, 50, cfg)
        for a, b in zip(r1, r2):
            assert a.pattern_half_life == b.pattern_half_life


# ===========================================================================
# SECTION 18 — PatternHalfLifeResult dataclass
# ===========================================================================


class TestPatternHalfLifeResult:
    def test_defaults(self):
        r = PatternHalfLifeResult()
        assert r.pattern_key == ""
        assert r.base_half_life == 50
        assert r.pattern_half_life == 50
        assert r.multiplier == 1.0
        assert r.sample_count == 0
        assert r.reliability == 0.0
        assert r.noise == 0.0
        assert r.used_fallback is True
        assert r.explanation == ""

    def test_frozen(self):
        r = PatternHalfLifeResult()
        with pytest.raises(AttributeError):
            r.pattern_half_life = 100  # type: ignore[misc]

    def test_to_dict_roundtrip(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
        d = r.to_dict()
        assert d["pattern_key"] == "p1"
        assert d["base_half_life"] == 50
        assert d["pattern_half_life"] == r.pattern_half_life
        assert isinstance(d["multiplier"], float)
        assert isinstance(d["reliability"], float)
        assert isinstance(d["noise"], float)


# ===========================================================================
# SECTION 19 — Temporal Integration
# ===========================================================================


class TestTemporalIntegration:
    def test_pattern_hl_overrides_global(self):
        tcfg = _temporal_config(half_life=50)
        pcfg = _cfg(min_samples=5, reliable_multiplier=2.0)
        phr = compute_pattern_half_life("p1", _stable_scores(), 50, pcfg)
        assert phr.pattern_half_life == 100

        result = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[50],
            similarities=[1.0],
            config=tcfg,
            pattern_half_life_results=[phr],
        )
        assert result.applied is True
        assert result.pattern_applied is True

    def test_pattern_hl_not_applied_when_fallback(self):
        tcfg = _temporal_config(half_life=50)
        phr = PatternHalfLifeResult(
            pattern_key="p1",
            base_half_life=50,
            pattern_half_life=50,
            used_fallback=True,
        )
        result = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[50],
            similarities=[1.0],
            config=tcfg,
            pattern_half_life_results=[phr],
        )
        assert result.pattern_applied is False

    def test_pattern_hl_with_regime(self):
        tcfg = _temporal_config(half_life=50)
        regime_r = RegimeHalfLifeResult(
            final_half_life=75,
            base_half_life=50,
            volatility_half_life=50,
            applied=True,
            regime="stable",
            regime_category="stable",
        )
        phr = compute_pattern_half_life("p1", _stable_scores(), 75, _cfg(min_samples=5))

        result = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[50],
            similarities=[1.0],
            config=tcfg,
            regime_result=regime_r,
            pattern_half_life_results=[phr],
        )
        assert result.regime_applied is True
        assert result.pattern_applied is True

    def test_no_pattern_hl_default_behavior(self):
        tcfg = _temporal_config(half_life=50)
        r1 = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[10],
            similarities=[1.0],
            config=tcfg,
        )
        r2 = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[10],
            similarities=[1.0],
            config=tcfg,
            pattern_half_life_results=None,
        )
        assert r1.weights == r2.weights
        assert r1.pattern_applied is False
        assert r2.pattern_applied is False

    def test_multiple_patterns_different_hl(self):
        tcfg = _temporal_config(half_life=50)
        pcfg = _cfg(min_samples=5, reliable_multiplier=2.0, noisy_multiplier=0.5)

        phr_reliable = compute_pattern_half_life("p1", _stable_scores(), 50, pcfg)
        phr_noisy = compute_pattern_half_life("p2", _noisy_scores(), 50, pcfg)

        result = apply_temporal_weights(
            raw_weights=[0.8, 0.8],
            pattern_keys=["p1", "p2"],
            pattern_ages=[30, 30],
            similarities=[1.0, 1.0],
            config=tcfg,
            pattern_half_life_results=[phr_reliable, phr_noisy],
        )
        assert result.applied is True
        assert result.pattern_applied is True
        assert result.weights[0] > result.weights[1]

    def test_pattern_hl_length_mismatch_ignored(self):
        tcfg = _temporal_config(half_life=50)
        result = apply_temporal_weights(
            raw_weights=[0.8, 0.7],
            pattern_keys=["p1", "p2"],
            pattern_ages=[10, 20],
            similarities=[1.0, 1.0],
            config=tcfg,
            pattern_half_life_results=[PatternHalfLifeResult()],
        )
        assert result.pattern_applied is False

    def test_pattern_applied_in_to_dict(self):
        r = TemporalWeightingResult(pattern_applied=True)
        d = r.to_dict()
        assert "pattern_applied" in d
        assert d["pattern_applied"] is True


# ===========================================================================
# SECTION 20 — End-to-End Full Stack
# ===========================================================================


class TestEndToEnd:
    def test_full_stack_reliable(self):
        adaptive_r = AdaptiveHalfLifeResult(
            computed_half_life=60, base_half_life=50, volatility=0.2, applied=True
        )
        regime_r = compute_regime_half_life(
            adaptive_result=adaptive_r,
            regime_type=RegimeType.STABLE,
            config=RegimeHalfLifeConfig(enabled=True, base_half_life=50),
        )
        pcfg = _cfg(min_samples=5, reliable_multiplier=1.5)
        phr = compute_pattern_half_life("p1", _stable_scores(), regime_r.final_half_life, pcfg)

        tcfg = _temporal_config(half_life=50)
        result = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[20],
            similarities=[1.0],
            config=tcfg,
            adaptive_result=adaptive_r,
            regime_result=regime_r,
            pattern_half_life_results=[phr],
        )
        assert result.applied is True
        assert result.adaptive_applied is True
        assert result.regime_applied is True
        assert result.pattern_applied is True

    def test_full_stack_noisy(self):
        pcfg = _cfg(min_samples=5, noisy_multiplier=0.4)
        phr = compute_pattern_half_life("p1", _noisy_scores(), 50, pcfg)
        assert phr.pattern_half_life < 50

        tcfg = _temporal_config(half_life=50)
        result = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[40],
            similarities=[1.0],
            config=tcfg,
            pattern_half_life_results=[phr],
        )
        assert result.applied is True
        assert result.pattern_applied is True

    def test_full_stack_deterministic(self):
        pcfg = _cfg(min_samples=5)
        phr = compute_pattern_half_life("p1", _stable_scores(), 50, pcfg)
        tcfg = _temporal_config(half_life=50)

        results = []
        for _ in range(50):
            r = apply_temporal_weights(
                raw_weights=[0.8],
                pattern_keys=["p1"],
                pattern_ages=[20],
                similarities=[1.0],
                config=tcfg,
                pattern_half_life_results=[phr],
            )
            results.append(r.weights[0])
        assert len(set(results)) == 1


# ===========================================================================
# SECTION 21 — Multiplier Sweep
# ===========================================================================


class TestMultiplierSweep:
    def test_increasing_reliable_multiplier(self):
        results = []
        for mult in [1.0, 1.5, 2.0, 3.0]:
            cfg = _cfg(min_samples=5, reliable_multiplier=mult)
            r = compute_pattern_half_life("p1", _stable_scores(), 50, cfg)
            results.append(r.pattern_half_life)
        for i in range(len(results) - 1):
            assert results[i] <= results[i + 1]

    def test_decreasing_noisy_multiplier(self):
        results = []
        for mult in [0.8, 0.6, 0.4, 0.2]:
            cfg = _cfg(min_samples=5, noisy_multiplier=mult)
            r = compute_pattern_half_life("p1", _noisy_scores(), 50, cfg)
            results.append(r.pattern_half_life)
        for i in range(len(results) - 1):
            assert results[i] >= results[i + 1]


# ===========================================================================
# SECTION 22 — Edge Cases
# ===========================================================================


class TestEdgeCases:
    def test_all_zeros(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", [0.0] * 20, 50, cfg)
        assert r.noise == 0.0
        assert r.reliability == 1.0

    def test_all_ones(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", [1.0] * 20, 50, cfg)
        assert r.noise == 0.0
        assert r.reliability == 1.0

    def test_base_half_life_one(self):
        cfg = _cfg(min_samples=5)
        r = compute_pattern_half_life("p1", _noisy_scores(), 1, cfg)
        assert r.pattern_half_life >= cfg.min_half_life

    def test_base_half_life_large(self):
        cfg = _cfg(min_samples=5, max_half_life=500)
        r = compute_pattern_half_life("p1", _stable_scores(), 300, cfg)
        assert r.pattern_half_life <= 500

    def test_exactly_min_samples(self):
        cfg = _cfg(min_samples=10)
        r = compute_pattern_half_life("p1", [0.5] * 10, 50, cfg)
        assert r.used_fallback is False

    def test_one_below_min_samples(self):
        cfg = _cfg(min_samples=10)
        r = compute_pattern_half_life("p1", [0.5] * 9, 50, cfg)
        assert r.used_fallback is True


# ===========================================================================
# SECTION 23 — Import Tests
# ===========================================================================


class TestImports:
    def test_import_from_pattern_half_life(self):
        from umh.runtime.pattern_half_life import (
            PatternHalfLifeConfig,
            PatternHalfLifeResult,
            compute_all_pattern_half_lives,
            compute_pattern_half_life,
            compute_pattern_noise,
            compute_pattern_reliability,
        )

        assert PatternHalfLifeConfig is not None
        assert PatternHalfLifeResult is not None

    def test_import_from_runtime_init(self):
        from umh.runtime import (
            PatternHalfLifeConfig,
            PatternHalfLifeResult,
            compute_all_pattern_half_lives,
            compute_pattern_half_life,
            compute_pattern_noise,
            compute_pattern_reliability,
        )

        assert PatternHalfLifeConfig is not None

    def test_temporal_result_has_pattern_applied(self):
        r = TemporalWeightingResult()
        assert hasattr(r, "pattern_applied")
        assert r.pattern_applied is False

    def test_no_forbidden_imports(self):
        import inspect
        import umh.runtime.pattern_half_life as m

        src = inspect.getsource(m)
        forbidden = [
            "from umh.runtime.outcome",
            "from umh.runtime.feedback",
            "from umh.runtime.cell",
            "from umh.runtime.environment",
            "from umh.runtime.adapter",
            "import subprocess",
            "import os",
        ]
        for f in forbidden:
            assert f not in src, f"forbidden: {f}"


# ===========================================================================
# SECTION 24 — Backward Compatibility
# ===========================================================================


class TestBackwardCompat:
    def test_no_pattern_hl_arg(self):
        tcfg = _temporal_config(half_life=50)
        r = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[10],
            similarities=[1.0],
            config=tcfg,
        )
        assert r.applied is True
        assert r.pattern_applied is False

    def test_adaptive_only(self):
        adaptive_r = AdaptiveHalfLifeResult(computed_half_life=80, base_half_life=50, applied=True)
        tcfg = _temporal_config(half_life=50)
        r = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[10],
            similarities=[1.0],
            config=tcfg,
            adaptive_result=adaptive_r,
        )
        assert r.adaptive_applied is True
        assert r.pattern_applied is False

    def test_regime_only(self):
        regime_r = RegimeHalfLifeResult(
            final_half_life=75, base_half_life=50, volatility_half_life=50, applied=True
        )
        tcfg = _temporal_config(half_life=50)
        r = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[10],
            similarities=[1.0],
            config=tcfg,
            regime_result=regime_r,
        )
        assert r.regime_applied is True
        assert r.pattern_applied is False

    def test_disabled_temporal_unchanged(self):
        r = apply_temporal_weights(
            raw_weights=[0.8, 0.6],
            pattern_keys=["p1", "p2"],
            pattern_ages=[10, 20],
            similarities=[1.0, 0.9],
        )
        assert r.applied is False
        assert r.weights == (0.8, 0.6)

    def test_decay_factor_unchanged(self):
        assert compute_decay_factor(0, 50) == 1.0
        assert compute_decay_factor(50, 50) == pytest.approx(0.5, abs=0.01)

    def test_floor_still_works(self):
        tcfg = _temporal_config(half_life=5, min_weight=0.1)
        r = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[100],
            similarities=[1.0],
            config=tcfg,
        )
        assert r.weights[0] >= 0.1 * 1.0

    def test_temporal_result_default_pattern(self):
        r = TemporalWeightingResult()
        assert r.pattern_applied is False
        d = r.to_dict()
        assert d["pattern_applied"] is False


# ===========================================================================
# SECTION 25 — Phase 61 Import Whitelist
# ===========================================================================


class TestPhase61ImportWhitelist:
    def test_whitelist_passes(self):
        import inspect
        import umh.runtime.strategy_orchestrator as m

        src = inspect.getsource(m)
        allowed = {
            "feedback_selection",
            "regime_aggregation",
            "dimension_weighting",
            "weighted_decision",
            "dimension_interactions",
            "pattern_aggregation",
            "pattern_influence",
            "pattern_matching",
        }
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"

    def test_whitelist_narrow(self):
        allowed = {
            "feedback_selection",
            "regime_aggregation",
            "dimension_weighting",
            "weighted_decision",
            "dimension_interactions",
            "pattern_aggregation",
            "pattern_influence",
            "pattern_matching",
        }
        assert len(allowed) == 8


# ===========================================================================
# SECTION 26 — Regression Tests
# ===========================================================================


class TestRegression:
    def test_aggregation_module_importable(self):
        from umh.runtime.pattern_aggregation import (
            PatternAggregationResult,
            compute_pattern_aggregation,
        )

        assert PatternAggregationResult is not None
        assert compute_pattern_aggregation is not None

    def test_aggregation_disabled_returns_neutral(self):
        from umh.runtime.pattern_aggregation import compute_pattern_aggregation

        r = compute_pattern_aggregation(pattern_result=None)
        assert r.applied is False
        assert r.final_factor == 1.0

    def test_neutral_when_disabled(self):
        r = apply_temporal_weights(
            raw_weights=[0.8],
            pattern_keys=["p1"],
            pattern_ages=[10],
            similarities=[1.0],
        )
        assert r.applied is False

    def test_factor_bounded(self):
        for age in range(0, 200, 10):
            d = compute_decay_factor(age, 50)
            assert 0.0 <= d <= 1.0

    def test_adaptive_half_life_still_works(self):
        cfg = AdaptiveHalfLifeConfig(enabled=True, base_half_life=50)
        r = compute_adaptive_half_life([0.5, 0.6, 0.7, 0.5, 0.6] * 4, cfg)
        assert r.applied is True
        assert r.computed_half_life >= cfg.min_half_life

    def test_regime_half_life_still_works(self):
        cfg = RegimeHalfLifeConfig(enabled=True, base_half_life=50)
        r = compute_regime_half_life(regime_type=RegimeType.STABLE, config=cfg)
        assert r.applied is True
        assert r.final_half_life > 50


# ===========================================================================
# SECTION 27 — Parameter Sweep
# ===========================================================================


class TestParameterSweep:
    def test_base_half_life_sweep(self):
        cfg = _cfg(min_samples=5)
        prev = 0
        for base in [10, 30, 50, 100, 200]:
            r = compute_pattern_half_life("p1", _stable_scores(), base, cfg)
            assert r.pattern_half_life >= prev
            prev = r.pattern_half_life

    def test_min_samples_sweep(self):
        scores = [0.5] * 15
        for ms in [5, 10, 15, 20]:
            cfg = _cfg(min_samples=ms)
            r = compute_pattern_half_life("p1", scores, 50, cfg)
            if ms <= 15:
                assert r.used_fallback is False
            else:
                assert r.used_fallback is True

    def test_threshold_sweep(self):
        scores = _moderate_scores(20)
        noise = compute_pattern_noise(scores)
        reliability = compute_pattern_reliability(scores)

        for rt in [0.3, 0.5, 0.7, 0.9]:
            for nt in [0.1, 0.3, 0.5, 0.7]:
                cfg = _cfg(
                    min_samples=5,
                    reliability_threshold=rt,
                    noise_threshold=nt,
                )
                r = compute_pattern_half_life("p1", scores, 50, cfg)
                if reliability >= rt:
                    assert r.multiplier == cfg.reliable_multiplier
                elif noise >= nt:
                    assert r.multiplier == cfg.noisy_multiplier
                else:
                    assert r.multiplier == cfg.base_multiplier

    def test_bounds_sweep(self):
        cfg_base = _cfg(min_samples=5)
        for mn, mx in [(5, 50), (10, 100), (20, 200), (50, 500)]:
            cfg = _cfg(min_samples=5, min_half_life=mn, max_half_life=mx)
            for scores in [_stable_scores(), _noisy_scores()]:
                r = compute_pattern_half_life("p", scores, 50, cfg)
                assert mn <= r.pattern_half_life <= mx


# ===========================================================================
# SECTION 28 — Temporal New Field Tests
# ===========================================================================


class TestTemporalResultNewField:
    def test_default_false(self):
        r = TemporalWeightingResult()
        assert r.pattern_applied is False

    def test_set_true(self):
        r = TemporalWeightingResult(pattern_applied=True)
        assert r.pattern_applied is True

    def test_to_dict_includes_pattern_applied(self):
        r = TemporalWeightingResult(pattern_applied=True)
        d = r.to_dict()
        assert d["pattern_applied"] is True

    def test_frozen(self):
        r = TemporalWeightingResult()
        with pytest.raises(AttributeError):
            r.pattern_applied = True  # type: ignore[misc]
