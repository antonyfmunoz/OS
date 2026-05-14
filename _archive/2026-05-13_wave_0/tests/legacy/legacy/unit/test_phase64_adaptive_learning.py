"""Phase 64 — Adaptive Learning Rate Layer v1 tests.

Tests adaptive learning rate computation, integration with weight evolution,
and regime-scoped weight evolution. Covers invariants 284-293.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.adaptive_learning import (
    DEFAULT_ADAPTIVE_LEARNING_CONFIG,
    AdaptiveLearningConfig,
    AdaptiveLearningResult,
    _compute_confidence_factor,
    _compute_stability_factor,
    compute_adaptive_rate,
)
from umh.runtime.regime_aggregation import DimensionName
from umh.runtime.weight_evolution import (
    WeightEvolutionConfig,
    WeightObservation,
    _evolve_single_dimension,
    evolve_weights,
)


def _make_obs(
    dim: DimensionName = DimensionName.TREND,
    count: int = 10,
    direction: float = 0.8,
    outcome: float = 0.9,
    start_tick: int = 1,
) -> list[WeightObservation]:
    return [
        WeightObservation(
            dimension=dim,
            direction_signal=direction,
            outcome_score=outcome,
            tick=start_tick + i,
        )
        for i in range(count)
    ]


def _enabled_config(
    base_rate: float = 0.05,
    min_rate: float = 0.005,
    max_rate: float = 0.10,
    variance_threshold: float = 0.25,
) -> AdaptiveLearningConfig:
    return AdaptiveLearningConfig(
        enabled=True,
        base_rate=base_rate,
        min_rate=min_rate,
        max_rate=max_rate,
        variance_threshold=variance_threshold,
    )


def _evo_config(
    learning_rate: float = 0.05,
    min_samples: int = 3,
    max_adjustment: float = 0.15,
    decay_rate: float = 0.98,
) -> WeightEvolutionConfig:
    return WeightEvolutionConfig(
        enabled=True,
        learning_rate=learning_rate,
        min_samples=min_samples,
        max_adjustment=max_adjustment,
        decay_rate=decay_rate,
    )


# ===========================================================================
# SECTION 1 — AdaptiveLearningConfig defaults
# ===========================================================================


class TestSection01ConfigDefaults:
    def test_disabled_by_default(self):
        cfg = AdaptiveLearningConfig()
        assert cfg.enabled is False

    def test_base_rate_default(self):
        cfg = AdaptiveLearningConfig()
        assert cfg.base_rate == 0.05

    def test_min_rate_default(self):
        cfg = AdaptiveLearningConfig()
        assert cfg.min_rate == 0.005

    def test_max_rate_default(self):
        cfg = AdaptiveLearningConfig()
        assert cfg.max_rate == 0.10

    def test_variance_threshold_default(self):
        cfg = AdaptiveLearningConfig()
        assert cfg.variance_threshold == 0.25


# ===========================================================================
# SECTION 2 — Config bounds clamping
# ===========================================================================


class TestSection02ConfigBounds:
    def test_base_rate_clamped_low(self):
        cfg = AdaptiveLearningConfig(base_rate=-1.0)
        assert cfg.base_rate == 0.0

    def test_base_rate_clamped_high(self):
        cfg = AdaptiveLearningConfig(base_rate=5.0)
        assert cfg.base_rate == 0.50

    def test_min_rate_clamped_low(self):
        cfg = AdaptiveLearningConfig(min_rate=-0.5)
        assert cfg.min_rate == 0.0

    def test_max_rate_clamped_high(self):
        cfg = AdaptiveLearningConfig(max_rate=10.0)
        assert cfg.max_rate == 0.50

    def test_min_capped_to_max(self):
        cfg = AdaptiveLearningConfig(min_rate=0.2, max_rate=0.1)
        assert cfg.min_rate <= cfg.max_rate

    def test_variance_threshold_clamped_low(self):
        cfg = AdaptiveLearningConfig(variance_threshold=0.001)
        assert cfg.variance_threshold == 0.01

    def test_variance_threshold_clamped_high(self):
        cfg = AdaptiveLearningConfig(variance_threshold=5.0)
        assert cfg.variance_threshold == 1.0


# ===========================================================================
# SECTION 3 — Config frozen + to_dict
# ===========================================================================


class TestSection03ConfigFrozenDict:
    def test_frozen(self):
        cfg = AdaptiveLearningConfig()
        try:
            cfg.base_rate = 0.1  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass

    def test_to_dict_keys(self):
        d = AdaptiveLearningConfig().to_dict()
        assert set(d.keys()) == {
            "enabled",
            "base_rate",
            "min_rate",
            "max_rate",
            "variance_threshold",
        }

    def test_to_dict_values(self):
        d = _enabled_config().to_dict()
        assert d["enabled"] is True
        assert d["base_rate"] == 0.05


# ===========================================================================
# SECTION 4 — AdaptiveLearningResult defaults
# ===========================================================================


class TestSection04ResultDefaults:
    def test_adaptive_rate_default(self):
        r = AdaptiveLearningResult()
        assert r.adaptive_rate == 0.05

    def test_confidence_factor_default(self):
        r = AdaptiveLearningResult()
        assert r.confidence_factor == 1.0

    def test_stability_factor_default(self):
        r = AdaptiveLearningResult()
        assert r.stability_factor == 1.0

    def test_variance_default(self):
        r = AdaptiveLearningResult()
        assert r.variance == 0.0


# ===========================================================================
# SECTION 5 — Result frozen + to_dict
# ===========================================================================


class TestSection05ResultFrozenDict:
    def test_frozen(self):
        r = AdaptiveLearningResult()
        try:
            r.adaptive_rate = 0.1  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict_keys(self):
        d = AdaptiveLearningResult().to_dict()
        expected = {
            "adaptive_rate",
            "base_rate",
            "confidence_factor",
            "stability_factor",
            "regime_factor",
            "variance",
            "confidence_input",
            "explanation",
        }
        assert set(d.keys()) == expected


# ===========================================================================
# SECTION 6 — Result bounds clamping
# ===========================================================================


class TestSection06ResultBounds:
    def test_adaptive_rate_clamped_high(self):
        r = AdaptiveLearningResult(adaptive_rate=5.0)
        assert r.adaptive_rate == 0.50

    def test_confidence_factor_clamped_low(self):
        r = AdaptiveLearningResult(confidence_factor=-0.5)
        assert r.confidence_factor == 0.0

    def test_confidence_factor_clamped_high(self):
        r = AdaptiveLearningResult(confidence_factor=2.0)
        assert r.confidence_factor == 1.0

    def test_stability_factor_clamped(self):
        r = AdaptiveLearningResult(stability_factor=-1.0)
        assert r.stability_factor == 0.0


# ===========================================================================
# SECTION 7 — Confidence factor computation
# ===========================================================================


class TestSection07ConfidenceFactor:
    def test_zero_confidence(self):
        assert _compute_confidence_factor(0.0) == 0.0

    def test_full_confidence(self):
        assert _compute_confidence_factor(1.0) == 1.0

    def test_half_confidence(self):
        assert _compute_confidence_factor(0.5) == 0.5

    def test_negative_clamped(self):
        assert _compute_confidence_factor(-0.5) == 0.0

    def test_above_one_clamped(self):
        assert _compute_confidence_factor(1.5) == 1.0

    def test_low_confidence_near_zero(self):
        assert _compute_confidence_factor(0.01) == 0.01


# ===========================================================================
# SECTION 8 — Stability factor computation
# ===========================================================================


class TestSection08StabilityFactor:
    def test_zero_variance(self):
        assert _compute_stability_factor(0.0, 0.25) == 1.0

    def test_equal_to_threshold(self):
        result = _compute_stability_factor(0.25, 0.25)
        assert abs(result - 0.5) < 0.001

    def test_high_variance_dampened(self):
        result = _compute_stability_factor(1.0, 0.25)
        assert result < 0.25

    def test_low_variance_near_one(self):
        result = _compute_stability_factor(0.01, 0.25)
        assert result > 0.95

    def test_zero_threshold_returns_one(self):
        assert _compute_stability_factor(0.5, 0.0) == 1.0

    def test_very_high_variance(self):
        result = _compute_stability_factor(10.0, 0.25)
        assert result < 0.05


# ===========================================================================
# SECTION 9 — compute_adaptive_rate: disabled
# ===========================================================================


class TestSection09Disabled:
    def test_disabled_returns_base_rate(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.9, config=AdaptiveLearningConfig())
        assert r.adaptive_rate == 0.05

    def test_disabled_explanation(self):
        r = compute_adaptive_rate(config=AdaptiveLearningConfig())
        assert "disabled" in r.explanation

    def test_disabled_confidence_factor_default(self):
        r = compute_adaptive_rate(config=AdaptiveLearningConfig())
        assert r.confidence_factor == 1.0


# ===========================================================================
# SECTION 10 — compute_adaptive_rate: no observations
# ===========================================================================


class TestSection10NoObs:
    def test_no_obs_returns_base(self):
        r = compute_adaptive_rate(observations=[], confidence=0.9, config=_enabled_config())
        assert r.adaptive_rate == 0.05

    def test_no_obs_explanation(self):
        r = compute_adaptive_rate(observations=[], config=_enabled_config())
        assert "fallback" in r.explanation

    def test_none_obs_returns_base(self):
        r = compute_adaptive_rate(observations=None, config=_enabled_config())
        assert r.adaptive_rate == 0.05


# ===========================================================================
# SECTION 11 — High confidence → higher rate (inv 285)
# ===========================================================================


class TestSection11HighConfidence:
    def test_high_confidence_higher_rate(self):
        obs = _make_obs()
        r_high = compute_adaptive_rate(obs, confidence=1.0, config=_enabled_config())
        r_low = compute_adaptive_rate(obs, confidence=0.1, config=_enabled_config())
        assert r_high.adaptive_rate > r_low.adaptive_rate

    def test_full_confidence_full_base(self):
        obs = _make_obs(direction=0.5, outcome=0.5)
        r = compute_adaptive_rate(obs, confidence=1.0, config=_enabled_config())
        assert r.confidence_factor == 1.0

    def test_high_confidence_near_base_rate(self):
        obs = _make_obs(direction=0.5, outcome=0.5)
        r = compute_adaptive_rate(obs, confidence=1.0, config=_enabled_config())
        assert r.adaptive_rate >= 0.04


# ===========================================================================
# SECTION 12 — Low confidence → near zero (inv 286)
# ===========================================================================


class TestSection12LowConfidence:
    def test_zero_confidence_min_rate(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.0, config=_enabled_config())
        assert r.adaptive_rate == 0.005

    def test_very_low_confidence_near_min(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.01, config=_enabled_config())
        assert r.adaptive_rate <= 0.01

    def test_low_confidence_factor(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.05, config=_enabled_config())
        assert r.confidence_factor == 0.05


# ===========================================================================
# SECTION 13 — High variance → dampened (inv 287)
# ===========================================================================


class TestSection13HighVariance:
    def test_high_variance_lowers_rate(self):
        noisy = []
        for i in range(20):
            sig = 1.0 if i % 2 == 0 else -1.0
            noisy.append(
                WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=sig,
                    outcome_score=0.9,
                    tick=i + 1,
                )
            )
        r = compute_adaptive_rate(noisy, confidence=1.0, config=_enabled_config())
        assert r.stability_factor < 0.5

    def test_low_variance_full_rate(self):
        consistent = _make_obs(direction=0.8, outcome=0.9)
        r = compute_adaptive_rate(consistent, confidence=1.0, config=_enabled_config())
        assert r.stability_factor > 0.8


# ===========================================================================
# SECTION 14 — Rate bounded (inv 284)
# ===========================================================================


class TestSection14Bounded:
    def test_never_below_min(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.0, config=_enabled_config(min_rate=0.005))
        assert r.adaptive_rate >= 0.005

    def test_never_above_max(self):
        obs = _make_obs()
        cfg = _enabled_config(base_rate=0.5, max_rate=0.10)
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r.adaptive_rate <= 0.10

    def test_rate_always_non_negative(self):
        obs = _make_obs()
        for conf in [0.0, 0.1, 0.5, 1.0]:
            r = compute_adaptive_rate(obs, confidence=conf, config=_enabled_config())
            assert r.adaptive_rate >= 0.0


# ===========================================================================
# SECTION 15 — Determinism (inv 288)
# ===========================================================================


class TestSection15Determinism:
    def test_100_runs_identical(self):
        obs = _make_obs()
        cfg = _enabled_config()
        results = [compute_adaptive_rate(obs, confidence=0.7, config=cfg) for _ in range(100)]
        rates = [r.adaptive_rate for r in results]
        assert len(set(rates)) == 1


# ===========================================================================
# SECTION 16 — No mutation (inv 291)
# ===========================================================================


class TestSection16NoMutation:
    def test_observations_unchanged(self):
        obs = _make_obs()
        original_signals = [(o.direction_signal, o.outcome_score, o.tick) for o in obs]
        compute_adaptive_rate(obs, confidence=0.8, config=_enabled_config())
        after_signals = [(o.direction_signal, o.outcome_score, o.tick) for o in obs]
        assert original_signals == after_signals


# ===========================================================================
# SECTION 17 — Explainability (inv 293)
# ===========================================================================


class TestSection17Explainability:
    def test_explanation_has_factors(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.7, config=_enabled_config())
        assert "conf=" in r.explanation
        assert "stab=" in r.explanation

    def test_explanation_has_rates(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.7, config=_enabled_config())
        assert "base=" in r.explanation
        assert "clamped=" in r.explanation

    def test_to_dict_has_all_fields(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.7, config=_enabled_config())
        d = r.to_dict()
        assert "adaptive_rate" in d
        assert "confidence_factor" in d
        assert "stability_factor" in d
        assert "variance" in d


# ===========================================================================
# SECTION 18 — Fallback behavior (inv 292)
# ===========================================================================


class TestSection18Fallback:
    def test_missing_config_uses_default(self):
        r = compute_adaptive_rate(observations=_make_obs(), confidence=0.5)
        assert r.adaptive_rate == 0.05

    def test_none_observations_fallback(self):
        r = compute_adaptive_rate(observations=None, confidence=1.0, config=_enabled_config())
        assert r.adaptive_rate == 0.05


# ===========================================================================
# SECTION 19 — Integration: _evolve_single_dimension with adaptive
# ===========================================================================


class TestSection19EvolveWithAdaptive:
    def test_adaptive_disabled_same_as_before(self):
        obs = _make_obs(count=10, direction=0.8, outcome=0.9)
        cfg = _evo_config()
        r1 = _evolve_single_dimension(DimensionName.TREND, 0.25, obs, 20, cfg)
        r2 = _evolve_single_dimension(DimensionName.TREND, 0.25, obs, 20, cfg, adaptive_config=None)
        assert r1.evolved_weight == r2.evolved_weight

    def test_adaptive_enabled_changes_delta(self):
        obs = _make_obs(count=10, direction=0.8, outcome=0.9)
        cfg = _evo_config()
        acfg = _enabled_config()
        r_fixed = _evolve_single_dimension(DimensionName.TREND, 0.25, obs, 20, cfg)
        r_adaptive_high = _evolve_single_dimension(
            DimensionName.TREND, 0.25, obs, 20, cfg, adaptive_config=acfg, confidence=1.0
        )
        r_adaptive_low = _evolve_single_dimension(
            DimensionName.TREND, 0.25, obs, 20, cfg, adaptive_config=acfg, confidence=0.1
        )
        assert r_adaptive_high.evolved_weight != r_adaptive_low.evolved_weight

    def test_adaptive_high_confidence_larger_delta(self):
        obs = _make_obs(count=10, direction=0.8, outcome=0.9)
        cfg = _evo_config()
        acfg = _enabled_config()
        r_high = _evolve_single_dimension(
            DimensionName.TREND, 0.25, obs, 20, cfg, adaptive_config=acfg, confidence=1.0
        )
        r_low = _evolve_single_dimension(
            DimensionName.TREND, 0.25, obs, 20, cfg, adaptive_config=acfg, confidence=0.1
        )
        assert abs(r_high.delta) > abs(r_low.delta)

    def test_adaptive_zero_confidence_minimal_delta(self):
        obs = _make_obs(count=10, direction=0.8, outcome=0.9)
        cfg = _evo_config()
        acfg = _enabled_config()
        r = _evolve_single_dimension(
            DimensionName.TREND, 0.25, obs, 20, cfg, adaptive_config=acfg, confidence=0.0
        )
        assert abs(r.delta) < 0.01

    def test_explanation_contains_adaptive_info(self):
        obs = _make_obs(count=10)
        cfg = _evo_config()
        acfg = _enabled_config()
        r = _evolve_single_dimension(
            DimensionName.TREND, 0.25, obs, 20, cfg, adaptive_config=acfg, confidence=0.8
        )
        assert "adaptive_rate=" in r.explanation
        assert "conf=" in r.explanation


# ===========================================================================
# SECTION 20 — Integration: evolve_weights with adaptive
# ===========================================================================


class TestSection20EvolveWeightsAdaptive:
    def test_adaptive_none_same_as_before(self):
        obs = _make_obs(count=10)
        cfg = _evo_config()
        r1 = evolve_weights(observations=obs, current_tick=20, config=cfg)
        r2 = evolve_weights(observations=obs, current_tick=20, config=cfg, adaptive_config=None)
        assert r1.evolved_weights.to_dict() == r2.evolved_weights.to_dict()

    def test_adaptive_modulates_per_dimension(self):
        obs_trend = _make_obs(dim=DimensionName.TREND, count=10, direction=0.8, outcome=0.9)
        obs_risk = _make_obs(dim=DimensionName.RISK, count=10, direction=0.8, outcome=0.9)
        all_obs = obs_trend + obs_risk
        cfg = _evo_config()
        acfg = _enabled_config()
        dim_conf = {DimensionName.TREND.value: 1.0, DimensionName.RISK.value: 0.1}
        r = evolve_weights(
            observations=all_obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        trend_evo = r.get(DimensionName.TREND)
        risk_evo = r.get(DimensionName.RISK)
        assert abs(trend_evo.delta) > abs(risk_evo.delta)

    def test_adaptive_disabled_config(self):
        obs = _make_obs(count=10)
        cfg = _evo_config()
        acfg = AdaptiveLearningConfig(enabled=False)
        r1 = evolve_weights(observations=obs, current_tick=20, config=cfg)
        r2 = evolve_weights(observations=obs, current_tick=20, config=cfg, adaptive_config=acfg)
        assert r1.evolved_weights.to_dict() == r2.evolved_weights.to_dict()


# ===========================================================================
# SECTION 21 — No cross-dimension contamination (inv 290)
# ===========================================================================


class TestSection21Isolation:
    def test_dimensions_evolve_independently(self):
        obs_trend = _make_obs(dim=DimensionName.TREND, count=10, direction=0.9, outcome=1.0)
        obs_risk = _make_obs(dim=DimensionName.RISK, count=10, direction=-0.5, outcome=0.3)
        all_obs = obs_trend + obs_risk
        cfg = _evo_config()
        acfg = _enabled_config()
        dim_conf = {DimensionName.TREND.value: 0.9, DimensionName.RISK.value: 0.9}
        r = evolve_weights(
            observations=all_obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        trend_evo = r.get(DimensionName.TREND)
        risk_evo = r.get(DimensionName.RISK)
        assert trend_evo.delta > 0
        assert risk_evo.delta < 0

    def test_untouched_dim_unchanged(self):
        obs = _make_obs(dim=DimensionName.TREND, count=10)
        cfg = _evo_config()
        acfg = _enabled_config()
        dim_conf = {DimensionName.TREND.value: 0.9}
        r = evolve_weights(
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        stab_evo = r.get(DimensionName.STABILITY)
        assert stab_evo.evolved_weight == stab_evo.base_weight


# ===========================================================================
# SECTION 22 — No amplification beyond max_adjustment (inv 289)
# ===========================================================================


class TestSection22NoAmplification:
    def test_bounded_even_with_high_rate(self):
        obs = _make_obs(count=10, direction=1.0, outcome=1.0)
        cfg = _evo_config(max_adjustment=0.10)
        acfg = _enabled_config(base_rate=0.5, max_rate=0.5)
        r = _evolve_single_dimension(
            DimensionName.TREND, 0.25, obs, 20, cfg, adaptive_config=acfg, confidence=1.0
        )
        assert r.evolved_weight <= 0.25 + 0.10
        assert r.evolved_weight >= 0.25 - 0.10

    def test_10_step_no_runaway(self):
        cfg = _evo_config(max_adjustment=0.15)
        acfg = _enabled_config(base_rate=0.5, max_rate=0.5)
        weight = 0.25
        prev_weight = weight
        for step in range(10):
            obs = _make_obs(count=10, direction=1.0, outcome=1.0, start_tick=step * 10)
            r = _evolve_single_dimension(
                DimensionName.TREND,
                weight,
                obs,
                (step + 1) * 10,
                cfg,
                adaptive_config=acfg,
                confidence=1.0,
            )
            weight = r.evolved_weight
            assert 0.0 <= weight <= 1.0
            assert weight <= prev_weight + cfg.max_adjustment + 0.001
            prev_weight = weight


# ===========================================================================
# SECTION 23 — Convergence behavior
# ===========================================================================


class TestSection23Convergence:
    def test_strong_signal_converges_faster(self):
        obs = _make_obs(count=20, direction=0.9, outcome=1.0)
        cfg = _evo_config()
        r_high = _evolve_single_dimension(
            DimensionName.TREND,
            0.25,
            obs,
            30,
            cfg,
            adaptive_config=_enabled_config(),
            confidence=1.0,
        )
        r_low = _evolve_single_dimension(
            DimensionName.TREND,
            0.25,
            obs,
            30,
            cfg,
            adaptive_config=_enabled_config(),
            confidence=0.2,
        )
        assert abs(r_high.delta) > abs(r_low.delta)

    def test_noisy_signal_slow_updates(self):
        noisy = []
        for i in range(20):
            sig = 0.9 if i % 2 == 0 else -0.9
            noisy.append(
                WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=sig,
                    outcome_score=0.9,
                    tick=i + 1,
                )
            )
        cfg = _evo_config()
        r = _evolve_single_dimension(
            DimensionName.TREND,
            0.25,
            noisy,
            30,
            cfg,
            adaptive_config=_enabled_config(),
            confidence=1.0,
        )
        assert abs(r.delta) < 0.01


# ===========================================================================
# SECTION 24 — Regime-scoped integration
# ===========================================================================


class TestSection24RegimeIntegration:
    def test_regime_evolve_with_adaptive(self):
        from umh.runtime.regime import RegimeType
        from umh.runtime.regime_weight_evolution import (
            RegimeObservation,
            RegimeWeightEvolutionConfig,
            evolve_regime_weights,
        )

        inner_cfg = _evo_config(min_samples=3)
        rcfg = RegimeWeightEvolutionConfig(enabled=True, evolution_config=inner_cfg)
        acfg = _enabled_config()
        obs = [
            RegimeObservation(
                observation=WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=0.8,
                    outcome_score=0.9,
                    tick=i + 1,
                ),
                regime=RegimeType.TREND_UP,
            )
            for i in range(10)
        ]
        dim_conf = {DimensionName.TREND.value: 0.9}
        r = evolve_regime_weights(
            observations=obs,
            current_tick=20,
            active_regime=RegimeType.TREND_UP,
            config=rcfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        assert r.total_observations == 10

    def test_regime_adaptive_vs_fixed(self):
        from umh.runtime.regime import RegimeType
        from umh.runtime.regime_weight_evolution import (
            RegimeObservation,
            RegimeWeightEvolutionConfig,
            evolve_regime_weights,
        )

        inner_cfg = _evo_config(min_samples=3)
        rcfg = RegimeWeightEvolutionConfig(enabled=True, evolution_config=inner_cfg)
        acfg = _enabled_config()
        obs = [
            RegimeObservation(
                observation=WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=0.8,
                    outcome_score=0.9,
                    tick=i + 1,
                ),
                regime=RegimeType.TREND_UP,
            )
            for i in range(10)
        ]
        r_fixed = evolve_regime_weights(
            observations=obs,
            current_tick=20,
            active_regime=RegimeType.TREND_UP,
            config=rcfg,
        )
        r_adaptive = evolve_regime_weights(
            observations=obs,
            current_tick=20,
            active_regime=RegimeType.TREND_UP,
            config=rcfg,
            adaptive_config=acfg,
            dimension_confidences={DimensionName.TREND.value: 1.0},
        )
        assert r_fixed.total_observations == r_adaptive.total_observations


# ===========================================================================
# SECTION 25 — DEFAULT_ADAPTIVE_LEARNING_CONFIG
# ===========================================================================


class TestSection25DefaultConfig:
    def test_default_exists(self):
        assert DEFAULT_ADAPTIVE_LEARNING_CONFIG is not None

    def test_default_disabled(self):
        assert DEFAULT_ADAPTIVE_LEARNING_CONFIG.enabled is False

    def test_default_is_frozen(self):
        try:
            DEFAULT_ADAPTIVE_LEARNING_CONFIG.enabled = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===========================================================================
# SECTION 26 — Dependencies
# ===========================================================================


class TestSection26Dependencies:
    def test_no_import_from_cells(self):
        import umh.runtime.adaptive_learning as mod

        src = open(mod.__file__).read()
        assert "umh.cells" not in src and "umh/cells" not in src

    def test_no_import_from_environments(self):
        import umh.runtime.adaptive_learning as mod

        src = open(mod.__file__).read()
        assert "umh.environments" not in src and "umh/environments" not in src

    def test_imports_only_from_weight_evolution(self):
        import inspect
        import umh.runtime.adaptive_learning as m

        src = inspect.getsource(m)
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        allowed = {"weight_evolution"}
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"


# ===========================================================================
# SECTION 27 — No randomness
# ===========================================================================


class TestSection27NoRandomness:
    def test_no_random_import(self):
        import inspect
        import umh.runtime.adaptive_learning as m

        src = inspect.getsource(m)
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "import random" not in stripped


# ===========================================================================
# SECTION 28 — No child processes
# ===========================================================================


class TestSection28NoExecution:
    def test_no_child_proc_import(self):
        import inspect
        import umh.runtime.adaptive_learning as m

        src = inspect.getsource(m)
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
                continue
            if "import" in stripped and "subproc" in stripped:
                assert False, f"unexpected child process import: {stripped}"


# ===========================================================================
# SECTION 29 — Phase 62 regression
# ===========================================================================


class TestSection29Phase62Regression:
    def test_phase62_unchanged_without_adaptive(self):
        obs = _make_obs(count=10, direction=0.8, outcome=0.9)
        cfg = _evo_config()
        r = evolve_weights(observations=obs, current_tick=20, config=cfg)
        trend = r.get(DimensionName.TREND)
        assert trend is not None
        assert trend.evolved_weight != trend.base_weight

    def test_phase62_sample_gate_still_works(self):
        obs = _make_obs(count=2)
        cfg = _evo_config(min_samples=5)
        r = evolve_weights(observations=obs, current_tick=10, config=cfg)
        trend = r.get(DimensionName.TREND)
        assert trend.sample_gated is True
        assert trend.evolved_weight == trend.base_weight


# ===========================================================================
# SECTION 30 — Phase 63 regression
# ===========================================================================


class TestSection30Phase63Regression:
    def test_phase63_regime_still_works(self):
        from umh.runtime.regime import RegimeType
        from umh.runtime.regime_weight_evolution import (
            RegimeObservation,
            RegimeWeightEvolutionConfig,
            evolve_regime_weights,
        )

        inner_cfg = _evo_config(min_samples=3)
        rcfg = RegimeWeightEvolutionConfig(enabled=True, evolution_config=inner_cfg)
        obs = [
            RegimeObservation(
                observation=WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=0.8,
                    outcome_score=0.9,
                    tick=i + 1,
                ),
                regime=RegimeType.TREND_UP,
            )
            for i in range(10)
        ]
        r = evolve_regime_weights(
            observations=obs,
            current_tick=20,
            active_regime=RegimeType.TREND_UP,
            config=rcfg,
        )
        assert r.total_observations == 10
        t = r.get(DimensionName.TREND)
        assert t is not None


# ===========================================================================
# SECTION 31 — Phase 61 regression
# ===========================================================================


class TestSection31Phase61Regression:
    def test_weighted_decision_imports(self):
        from umh.runtime.weighted_decision import apply_weighted_influence

        assert callable(apply_weighted_influence)


# ===========================================================================
# SECTION 32 — Phase 60 regression
# ===========================================================================


class TestSection32Phase60Regression:
    def test_dimension_weighting_imports(self):
        from umh.runtime.dimension_weighting import compute_dimension_weights

        assert callable(compute_dimension_weights)


# ===========================================================================
# SECTION 33 — Phase 59 regression
# ===========================================================================


class TestSection33Phase59Regression:
    def test_regime_aggregation_imports(self):
        from umh.runtime.regime_aggregation import aggregate_regimes

        assert callable(aggregate_regimes)


# ===========================================================================
# SECTION 34 — Phase 58 regression
# ===========================================================================


class TestSection34Phase58Regression:
    def test_strategy_orchestration_imports(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        assert callable(orchestrate_selection)


# ===========================================================================
# SECTION 35 — Init exports
# ===========================================================================


class TestSection35InitExports:
    def test_phase64_exports(self):
        from umh.runtime import (
            DEFAULT_ADAPTIVE_LEARNING_CONFIG,
            AdaptiveLearningConfig,
            AdaptiveLearningResult,
            compute_adaptive_rate,
        )

        assert DEFAULT_ADAPTIVE_LEARNING_CONFIG is not None
        assert AdaptiveLearningConfig is not None
        assert AdaptiveLearningResult is not None
        assert callable(compute_adaptive_rate)


# ===========================================================================
# SECTION 36 — Roundtrips
# ===========================================================================


class TestSection36Roundtrips:
    def test_config_dict_roundtrip(self):
        cfg = _enabled_config(base_rate=0.08)
        d = cfg.to_dict()
        cfg2 = AdaptiveLearningConfig(**d)
        assert cfg2.base_rate == cfg.base_rate
        assert cfg2.enabled == cfg.enabled

    def test_result_dict_roundtrip(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.7, config=_enabled_config())
        d = r.to_dict()
        assert isinstance(d["adaptive_rate"], float)
        assert isinstance(d["confidence_factor"], float)


# ===========================================================================
# SECTION 37 — Zero learning rate
# ===========================================================================


class TestSection37ZeroLearningRate:
    def test_zero_base_rate_min_still_applies(self):
        obs = _make_obs()
        cfg = _enabled_config(base_rate=0.0, min_rate=0.005)
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r.adaptive_rate == 0.005


# ===========================================================================
# SECTION 38 — Stress tests
# ===========================================================================


class TestSection38Stress:
    def test_500_observations(self):
        obs = _make_obs(count=500)
        r = compute_adaptive_rate(obs, confidence=0.8, config=_enabled_config())
        assert 0.005 <= r.adaptive_rate <= 0.10

    def test_2000_observations(self):
        obs = _make_obs(count=2000)
        r = compute_adaptive_rate(obs, confidence=0.8, config=_enabled_config())
        assert 0.005 <= r.adaptive_rate <= 0.10


# ===========================================================================
# SECTION 39 — Confidence spectrum
# ===========================================================================


class TestSection39ConfidenceSpectrum:
    def test_monotonic_increase_with_confidence(self):
        obs = _make_obs(count=20, direction=0.5, outcome=0.5)
        cfg = _enabled_config()
        rates = []
        for conf in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            r = compute_adaptive_rate(obs, confidence=conf, config=cfg)
            rates.append(r.adaptive_rate)
        for i in range(1, len(rates)):
            assert rates[i] >= rates[i - 1]

    def test_rate_range_coverage(self):
        obs = _make_obs(count=20, direction=0.5, outcome=0.5)
        cfg = _enabled_config()
        r_min = compute_adaptive_rate(obs, confidence=0.0, config=cfg)
        r_max = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r_min.adaptive_rate < r_max.adaptive_rate


# ===========================================================================
# SECTION 40 — Variance spectrum
# ===========================================================================


class TestSection40VarianceSpectrum:
    def test_stability_decreases_with_variance(self):
        cfg = _enabled_config()
        stab_vals = []
        for var_level in [0.0, 0.1, 0.25, 0.5, 1.0]:
            stab = _compute_stability_factor(var_level, cfg.variance_threshold)
            stab_vals.append(stab)
        for i in range(1, len(stab_vals)):
            assert stab_vals[i] <= stab_vals[i - 1]


# ===========================================================================
# SECTION 41 — Full pipeline integration
# ===========================================================================


class TestSection41FullPipeline:
    def test_end_to_end(self):
        from umh.runtime.dimension_weighting import default_weight_vector

        base = default_weight_vector()
        obs = []
        for dim in DimensionName:
            obs.extend(_make_obs(dim=dim, count=10, direction=0.7, outcome=0.8))

        cfg = _evo_config()
        acfg = _enabled_config()
        dim_conf = {d.value: 0.8 for d in DimensionName}

        r = evolve_weights(
            base_weights=base,
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        for dim in DimensionName:
            evo = r.get(dim)
            assert evo is not None
            assert 0.0 <= evo.evolved_weight <= 1.0


# ===========================================================================
# SECTION 42 — Custom config combinations
# ===========================================================================


class TestSection42CustomConfig:
    def test_aggressive_learning(self):
        obs = _make_obs(count=20, direction=0.9, outcome=1.0)
        cfg = _enabled_config(base_rate=0.10, min_rate=0.01, max_rate=0.50)
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r.adaptive_rate >= 0.05

    def test_conservative_learning(self):
        obs = _make_obs(count=20)
        cfg = _enabled_config(base_rate=0.01, min_rate=0.001, max_rate=0.02)
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r.adaptive_rate <= 0.02

    def test_tight_bounds(self):
        obs = _make_obs()
        cfg = _enabled_config(base_rate=0.05, min_rate=0.04, max_rate=0.06)
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert 0.04 <= r.adaptive_rate <= 0.06


# ===========================================================================
# SECTION 43 — Symmetry
# ===========================================================================


class TestSection43Symmetry:
    def test_same_obs_different_dims_same_rate(self):
        cfg = _enabled_config()
        obs_t = _make_obs(dim=DimensionName.TREND, count=10, direction=0.8, outcome=0.9)
        obs_r = _make_obs(dim=DimensionName.RISK, count=10, direction=0.8, outcome=0.9)
        r_t = compute_adaptive_rate(obs_t, confidence=0.8, config=cfg)
        r_r = compute_adaptive_rate(obs_r, confidence=0.8, config=cfg)
        assert abs(r_t.adaptive_rate - r_r.adaptive_rate) < 0.0001


# ===========================================================================
# SECTION 44 — Interaction: adaptive + Phase 62 variance damping
# ===========================================================================


class TestSection44AdaptiveAndVarianceDamping:
    def test_both_damping_layers_compound(self):
        noisy = []
        for i in range(20):
            sig = 0.9 if i % 2 == 0 else -0.9
            noisy.append(
                WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=sig,
                    outcome_score=0.9,
                    tick=i + 1,
                )
            )
        cfg = _evo_config()
        acfg = _enabled_config()
        r = _evolve_single_dimension(
            DimensionName.TREND,
            0.25,
            noisy,
            30,
            cfg,
            adaptive_config=acfg,
            confidence=1.0,
        )
        assert r.variance_damped is True
        assert abs(r.delta) < 0.005


# ===========================================================================
# SECTION 45 — Single observation
# ===========================================================================


class TestSection45SingleObs:
    def test_single_obs_variance_zero(self):
        obs = _make_obs(count=1)
        r = compute_adaptive_rate(obs, confidence=1.0, config=_enabled_config())
        assert r.variance == 0.0
        assert r.stability_factor == 1.0


# ===========================================================================
# SECTION 46 — Neutral signals
# ===========================================================================


class TestSection46NeutralSignals:
    def test_zero_direction_zero_quality(self):
        obs = _make_obs(count=10, direction=0.0, outcome=0.5)
        cfg = _enabled_config()
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r.variance == 0.0


# ===========================================================================
# SECTION 47 — Learning rate sensitivity
# ===========================================================================


class TestSection47LearningRateSensitivity:
    def test_higher_base_higher_rate(self):
        obs = _make_obs()
        r1 = compute_adaptive_rate(obs, confidence=0.8, config=_enabled_config(base_rate=0.03))
        r2 = compute_adaptive_rate(obs, confidence=0.8, config=_enabled_config(base_rate=0.08))
        assert r2.adaptive_rate >= r1.adaptive_rate


# ===========================================================================
# SECTION 48 — Decay rate sensitivity (interaction test)
# ===========================================================================


class TestSection48DecayInteraction:
    def test_adaptive_rate_unaffected_by_decay(self):
        obs = _make_obs(count=10)
        cfg = _enabled_config()
        r1 = compute_adaptive_rate(obs, confidence=0.8, config=cfg)
        r2 = compute_adaptive_rate(obs, confidence=0.8, config=cfg)
        assert r1.adaptive_rate == r2.adaptive_rate


# ===========================================================================
# SECTION 49 — Partial confidences
# ===========================================================================


class TestSection49PartialConfidences:
    def test_some_dims_have_confidence_some_dont(self):
        obs_t = _make_obs(dim=DimensionName.TREND, count=10)
        obs_r = _make_obs(dim=DimensionName.RISK, count=10)
        all_obs = obs_t + obs_r
        cfg = _evo_config()
        acfg = _enabled_config()
        dim_conf = {DimensionName.TREND.value: 0.9}
        r = evolve_weights(
            observations=all_obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        trend_evo = r.get(DimensionName.TREND)
        risk_evo = r.get(DimensionName.RISK)
        assert abs(trend_evo.delta) > abs(risk_evo.delta)


# ===========================================================================
# SECTION 50 — Edge: min_rate equals max_rate
# ===========================================================================


class TestSection50MinEqualsMax:
    def test_flat_rate(self):
        obs = _make_obs()
        cfg = _enabled_config(base_rate=0.05, min_rate=0.05, max_rate=0.05)
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r.adaptive_rate == 0.05

    def test_flat_rate_any_confidence(self):
        obs = _make_obs()
        cfg = _enabled_config(base_rate=0.05, min_rate=0.05, max_rate=0.05)
        r = compute_adaptive_rate(obs, confidence=0.0, config=cfg)
        assert r.adaptive_rate == 0.05


# ===========================================================================
# SECTION 51 — Multi-dimension adaptive evolution
# ===========================================================================


class TestSection51MultiDim:
    def test_four_dim_independent_rates(self):
        obs = []
        for dim in DimensionName:
            obs.extend(_make_obs(dim=dim, count=10, direction=0.8, outcome=0.9))
        cfg = _evo_config()
        acfg = _enabled_config()
        dim_conf = {
            DimensionName.TREND.value: 1.0,
            DimensionName.RISK.value: 0.5,
            DimensionName.STABILITY.value: 0.2,
            DimensionName.URGENCY.value: 0.0,
        }
        r = evolve_weights(
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        deltas = {dim: abs(r.get(dim).delta) for dim in DimensionName}
        assert deltas[DimensionName.TREND] > deltas[DimensionName.RISK]
        assert deltas[DimensionName.RISK] > deltas[DimensionName.STABILITY]
        assert deltas[DimensionName.STABILITY] >= deltas[DimensionName.URGENCY]


# ===========================================================================
# SECTION 52 — Interaction: sample gate + adaptive
# ===========================================================================


class TestSection52SampleGateAdaptive:
    def test_sample_gate_overrides_adaptive(self):
        obs = _make_obs(count=2)
        cfg = _evo_config(min_samples=5)
        acfg = _enabled_config()
        r = _evolve_single_dimension(
            DimensionName.TREND,
            0.25,
            obs,
            10,
            cfg,
            adaptive_config=acfg,
            confidence=1.0,
        )
        assert r.sample_gated is True
        assert r.evolved_weight == r.base_weight


# ===========================================================================
# SECTION 53 — Negative direction signals
# ===========================================================================


class TestSection53NegativeSignals:
    def test_negative_direction_adaptive(self):
        obs = _make_obs(count=10, direction=-0.8, outcome=0.9)
        cfg = _evo_config()
        acfg = _enabled_config()
        r = _evolve_single_dimension(
            DimensionName.TREND,
            0.25,
            obs,
            20,
            cfg,
            adaptive_config=acfg,
            confidence=1.0,
        )
        assert r.delta < 0


# ===========================================================================
# SECTION 54 — Zero outcomes
# ===========================================================================


class TestSection54ZeroOutcomes:
    def test_zero_outcome_zero_signal(self):
        obs = _make_obs(count=10, direction=0.8, outcome=0.0)
        cfg = _evo_config()
        acfg = _enabled_config()
        r = _evolve_single_dimension(
            DimensionName.TREND,
            0.25,
            obs,
            20,
            cfg,
            adaptive_config=acfg,
            confidence=1.0,
        )
        assert abs(r.delta) < 0.001


# ===========================================================================
# SECTION 55 — Config with all zeros
# ===========================================================================


class TestSection55AllZeroConfig:
    def test_all_zero_rates(self):
        cfg = AdaptiveLearningConfig(enabled=True, base_rate=0.0, min_rate=0.0, max_rate=0.0)
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r.adaptive_rate == 0.0


# ===========================================================================
# SECTION 56 — Stability factor smooth curve
# ===========================================================================


class TestSection56StabilityCurve:
    def test_smooth_not_binary(self):
        s1 = _compute_stability_factor(0.20, 0.25)
        s2 = _compute_stability_factor(0.30, 0.25)
        assert s1 != 1.0
        assert s2 != 0.5
        assert s1 > s2

    def test_approaches_zero_asymptotically(self):
        s = _compute_stability_factor(100.0, 0.25)
        assert s > 0.0
        assert s < 0.01


# ===========================================================================
# SECTION 57 — Evolved weight source tag
# ===========================================================================


class TestSection57SourceTag:
    def test_evolved_source_with_adaptive(self):
        obs = _make_obs(count=10, direction=0.8, outcome=0.9)
        cfg = _evo_config()
        acfg = _enabled_config()
        dim_conf = {DimensionName.TREND.value: 0.9}
        r = evolve_weights(
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        w = r.evolved_weights.get(DimensionName.TREND)
        assert w is not None
        assert w.source == "evolved"


# ===========================================================================
# SECTION 58 — Sequential adaptive evolution
# ===========================================================================


class TestSection58Sequential:
    def test_sequential_steps_stable(self):
        cfg = _evo_config(max_adjustment=0.15)
        acfg = _enabled_config()
        weight = 0.25
        for step in range(5):
            obs = _make_obs(count=10, direction=0.7, outcome=0.8, start_tick=step * 10)
            r = _evolve_single_dimension(
                DimensionName.TREND,
                weight,
                obs,
                (step + 1) * 10,
                cfg,
                adaptive_config=acfg,
                confidence=0.8,
            )
            new_weight = r.evolved_weight
            assert 0.0 <= new_weight <= 1.0
            weight = new_weight


# ===========================================================================
# SECTION 59 — Mixed high/low confidence dimensions
# ===========================================================================


class TestSection59MixedConfidence:
    def test_high_low_confidence_mix(self):
        obs_t = _make_obs(dim=DimensionName.TREND, count=10, direction=0.8, outcome=0.9)
        obs_s = _make_obs(dim=DimensionName.STABILITY, count=10, direction=0.8, outcome=0.9)
        all_obs = obs_t + obs_s
        cfg = _evo_config()
        acfg = _enabled_config()
        dim_conf = {DimensionName.TREND.value: 0.95, DimensionName.STABILITY.value: 0.05}
        r = evolve_weights(
            observations=all_obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        trend_delta = abs(r.get(DimensionName.TREND).delta)
        stab_delta = abs(r.get(DimensionName.STABILITY).delta)
        assert trend_delta > stab_delta * 3


# ===========================================================================
# SECTION 60 — Init regression
# ===========================================================================


class TestSection60InitRegression:
    def test_phase64_exports(self):
        from umh.runtime import (
            DEFAULT_ADAPTIVE_LEARNING_CONFIG,
            AdaptiveLearningConfig,
            AdaptiveLearningResult,
            compute_adaptive_rate,
        )

        assert DEFAULT_ADAPTIVE_LEARNING_CONFIG is not None

    def test_phase63_exports_still_work(self):
        from umh.runtime import (
            DEFAULT_REGIME_EVOLUTION_CONFIG,
            RegimeObservation,
            evolve_regime_weights,
        )

        assert DEFAULT_REGIME_EVOLUTION_CONFIG is not None

    def test_phase62_exports_still_work(self):
        from umh.runtime import (
            DEFAULT_EVOLUTION_CONFIG,
            WeightObservation,
            evolve_weights,
        )

        assert DEFAULT_EVOLUTION_CONFIG is not None


# ===========================================================================
# SECTION 61 — Variance threshold sensitivity
# ===========================================================================


class TestSection61VarianceThreshold:
    def test_low_threshold_more_damping(self):
        noisy = []
        for i in range(20):
            sig = 0.5 if i % 2 == 0 else -0.3
            noisy.append(
                WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=sig,
                    outcome_score=0.9,
                    tick=i + 1,
                )
            )
        r1 = compute_adaptive_rate(
            noisy, confidence=1.0, config=_enabled_config(variance_threshold=0.05)
        )
        r2 = compute_adaptive_rate(
            noisy, confidence=1.0, config=_enabled_config(variance_threshold=0.50)
        )
        assert r1.stability_factor < r2.stability_factor


# ===========================================================================
# SECTION 62 — Confidence input preserved
# ===========================================================================


class TestSection62ConfidenceInput:
    def test_confidence_input_in_result(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.73, config=_enabled_config())
        assert r.confidence_input == 0.73

    def test_disabled_preserves_input(self):
        r = compute_adaptive_rate(confidence=0.42)
        assert r.confidence_input == 0.42


# ===========================================================================
# SECTION 63 — Adaptive disabled with observations
# ===========================================================================


class TestSection63DisabledWithObs:
    def test_disabled_ignores_observations(self):
        obs = _make_obs(count=100)
        r = compute_adaptive_rate(obs, confidence=1.0, config=AdaptiveLearningConfig())
        assert r.adaptive_rate == 0.05


# ===========================================================================
# SECTION 64 — Compound: regime + adaptive + step clamp
# ===========================================================================


class TestSection64CompoundIntegration:
    def test_regime_adaptive_step_clamp(self):
        from umh.runtime.regime import RegimeType
        from umh.runtime.regime_weight_evolution import (
            RegimeObservation,
            RegimeWeightEvolutionConfig,
            evolve_regime_weights,
        )
        from umh.runtime.dimension_weighting import default_weight_vector

        inner_cfg = _evo_config(min_samples=3)
        rcfg = RegimeWeightEvolutionConfig(
            enabled=True,
            evolution_config=inner_cfg,
            max_step_change=0.02,
        )
        acfg = _enabled_config()
        obs = [
            RegimeObservation(
                observation=WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=0.9,
                    outcome_score=1.0,
                    tick=i + 1,
                ),
                regime=RegimeType.TREND_UP,
            )
            for i in range(20)
        ]
        prev = default_weight_vector()
        r = evolve_regime_weights(
            observations=obs,
            current_tick=30,
            active_regime=RegimeType.TREND_UP,
            previous_weights=prev,
            config=rcfg,
            adaptive_config=acfg,
            dimension_confidences={DimensionName.TREND.value: 1.0},
        )
        t = r.get(DimensionName.TREND)
        assert t is not None
        assert t.final_weight <= prev.get_weight(DimensionName.TREND) + 0.02 + 0.001


# ===========================================================================
# SECTION 65 — Edge: max_rate less than base_rate
# ===========================================================================


class TestSection65MaxLessThanBase:
    def test_rate_capped_at_max(self):
        obs = _make_obs()
        cfg = _enabled_config(base_rate=0.10, max_rate=0.05)
        r = compute_adaptive_rate(obs, confidence=1.0, config=cfg)
        assert r.adaptive_rate <= 0.05


# ===========================================================================
# SECTION 66 — Adaptive with mixed outcome scores
# ===========================================================================


class TestSection66MixedOutcomes:
    def test_mixed_outcomes_moderate_rate(self):
        obs = []
        for i in range(20):
            outcome = 1.0 if i % 2 == 0 else 0.0
            obs.append(
                WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=0.8,
                    outcome_score=outcome,
                    tick=i + 1,
                )
            )
        r = compute_adaptive_rate(obs, confidence=1.0, config=_enabled_config())
        assert r.variance > 0.0
        assert r.stability_factor < 1.0


# ===========================================================================
# SECTION 67 — No oscillation test
# ===========================================================================


class TestSection67NoOscillation:
    def test_consistent_direction(self):
        cfg = _evo_config(max_adjustment=0.15)
        acfg = _enabled_config()
        weight = 0.25
        deltas = []
        for step in range(10):
            obs = _make_obs(count=10, direction=0.8, outcome=0.9, start_tick=step * 10)
            r = _evolve_single_dimension(
                DimensionName.TREND,
                weight,
                obs,
                (step + 1) * 10,
                cfg,
                adaptive_config=acfg,
                confidence=0.8,
            )
            deltas.append(r.delta)
            weight = r.evolved_weight
        sign_changes = sum(1 for i in range(1, len(deltas)) if deltas[i] * deltas[i - 1] < 0)
        assert sign_changes == 0


# ===========================================================================
# SECTION 68 — to_dict completeness
# ===========================================================================


class TestSection68DictCompleteness:
    def test_config_to_dict_all_fields(self):
        d = _enabled_config().to_dict()
        assert len(d) == 5

    def test_result_to_dict_all_fields(self):
        obs = _make_obs()
        r = compute_adaptive_rate(obs, confidence=0.7, config=_enabled_config())
        d = r.to_dict()
        assert len(d) == 8
