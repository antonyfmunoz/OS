"""Phase 63 — Regime-scoped weight evolution tests.

Tests regime-conditioned temporal evolution of dimension weights.
Per-regime learning, blending, step-change clamping, and isolation.

Invariants 274-283.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.dimension_weighting import (
    DEFAULT_WEIGHT_VECTOR,
    DimensionWeight,
    DimensionWeightVector,
    WeightingConfig,
    default_weight_vector,
)
from umh.runtime.regime import RegimeType
from umh.runtime.regime_aggregation import DimensionName, DirectionCategory
from umh.runtime.weight_evolution import (
    DEFAULT_EVOLUTION_CONFIG,
    DimensionEvolution,
    WeightEvolutionConfig,
    WeightEvolutionResult,
    WeightObservation,
    evolve_weights,
)
from umh.runtime.regime_weight_evolution import (
    DEFAULT_REGIME_EVOLUTION_CONFIG,
    RegimeDimensionEvolution,
    RegimeObservation,
    RegimeWeightEvolutionConfig,
    RegimeWeightEvolutionResult,
    _apply_step_change_clamp,
    _compute_blend_factor,
    _is_neutral_regime,
    evolve_regime_weights,
)


def _make_regime_obs(
    dim: DimensionName,
    regime: RegimeType,
    count: int,
    direction: float = 1.0,
    outcome: float = 1.0,
    start_tick: int = 0,
) -> list[RegimeObservation]:
    return [
        RegimeObservation(
            observation=WeightObservation(
                dimension=dim,
                direction_signal=direction,
                outcome_score=outcome,
                tick=start_tick + i,
            ),
            regime=regime,
        )
        for i in range(count)
    ]


def _enabled_config(
    min_samples: int = 5,
    max_adjustment: float = 0.15,
    learning_rate: float = 0.05,
    decay_rate: float = 0.98,
    max_step_change: float = 0.05,
    blend_scale: float = 2.0,
) -> RegimeWeightEvolutionConfig:
    return RegimeWeightEvolutionConfig(
        enabled=True,
        evolution_config=WeightEvolutionConfig(
            enabled=True,
            decay_rate=decay_rate,
            learning_rate=learning_rate,
            min_samples=min_samples,
            max_adjustment=max_adjustment,
        ),
        max_step_change=max_step_change,
        blend_scale=blend_scale,
    )


class TestSection01ConfigDefaults:
    def test_default_enabled(self):
        assert RegimeWeightEvolutionConfig().enabled is False

    def test_default_max_step_change(self):
        assert RegimeWeightEvolutionConfig().max_step_change == 0.05

    def test_default_blend_scale(self):
        assert RegimeWeightEvolutionConfig().blend_scale == 2.0

    def test_default_evolution_config(self):
        c = RegimeWeightEvolutionConfig()
        assert c.evolution_config.enabled is False
        assert c.evolution_config.decay_rate == 0.98

    def test_default_constant(self):
        c = DEFAULT_REGIME_EVOLUTION_CONFIG
        assert c.enabled is False
        assert c.max_step_change == 0.05


class TestSection02ConfigBounds:
    def test_max_step_change_clamped_low(self):
        c = RegimeWeightEvolutionConfig(max_step_change=-1.0)
        assert c.max_step_change == 0.001

    def test_max_step_change_clamped_high(self):
        c = RegimeWeightEvolutionConfig(max_step_change=5.0)
        assert c.max_step_change == 0.50

    def test_blend_scale_clamped_low(self):
        c = RegimeWeightEvolutionConfig(blend_scale=0.1)
        assert c.blend_scale == 1.0

    def test_blend_scale_clamped_high(self):
        c = RegimeWeightEvolutionConfig(blend_scale=100.0)
        assert c.blend_scale == 10.0


class TestSection03ConfigDictFrozen:
    def test_to_dict_keys(self):
        d = RegimeWeightEvolutionConfig().to_dict()
        assert set(d.keys()) == {"enabled", "evolution_config", "max_step_change", "blend_scale"}

    def test_frozen(self):
        c = RegimeWeightEvolutionConfig()
        try:
            c.enabled = True  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestSection04RegimeObservation:
    def test_creation(self):
        obs = WeightObservation(
            dimension=DimensionName.TREND, direction_signal=0.8, outcome_score=0.9, tick=5
        )
        ro = RegimeObservation(observation=obs, regime=RegimeType.TREND_UP)
        assert ro.regime is RegimeType.TREND_UP
        assert ro.observation.dimension is DimensionName.TREND

    def test_to_dict(self):
        obs = WeightObservation(dimension=DimensionName.RISK, tick=3)
        ro = RegimeObservation(observation=obs, regime=RegimeType.SPIKE_UP)
        d = ro.to_dict()
        assert d["regime"] == "spike_up"
        assert "observation" in d

    def test_frozen(self):
        obs = WeightObservation(dimension=DimensionName.TREND)
        ro = RegimeObservation(observation=obs, regime=RegimeType.STABLE)
        try:
            ro.regime = RegimeType.SPIKE_UP  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestSection05EvolutionDefaults:
    def test_defaults(self):
        e = RegimeDimensionEvolution(dimension=DimensionName.TREND)
        assert e.global_weight == 0.25
        assert e.regime_weight == 0.25
        assert e.blended_weight == 0.25
        assert e.final_weight == 0.25
        assert e.blend_factor == 0.0
        assert e.regime_sample_count == 0
        assert e.global_sample_count == 0
        assert e.step_clamped is False

    def test_bounds_clamp(self):
        e = RegimeDimensionEvolution(
            dimension=DimensionName.RISK,
            global_weight=5.0,
            regime_weight=-1.0,
            blend_factor=2.0,
            regime_quality=-5.0,
        )
        assert e.global_weight == 1.0
        assert e.regime_weight == 0.0
        assert e.blend_factor == 1.0
        assert e.regime_quality == -1.0

    def test_to_dict_keys(self):
        e = RegimeDimensionEvolution(dimension=DimensionName.TREND)
        d = e.to_dict()
        expected = {
            "dimension",
            "regime",
            "global_weight",
            "regime_weight",
            "blended_weight",
            "final_weight",
            "blend_factor",
            "regime_sample_count",
            "global_sample_count",
            "regime_quality",
            "global_quality",
            "step_clamped",
            "explanation",
        }
        assert set(d.keys()) == expected


class TestSection06EvolutionFrozen:
    def test_frozen(self):
        e = RegimeDimensionEvolution(dimension=DimensionName.TREND)
        try:
            e.final_weight = 0.5  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestSection07ResultDefaults:
    def test_defaults(self):
        r = RegimeWeightEvolutionResult(evolutions={}, evolved_weights=default_weight_vector())
        assert r.active_regime is None
        assert r.total_observations == 0
        assert r.explanation == ""

    def test_get_existing(self):
        evo = RegimeDimensionEvolution(dimension=DimensionName.TREND)
        r = RegimeWeightEvolutionResult(
            evolutions={"trend": evo}, evolved_weights=default_weight_vector()
        )
        assert r.get(DimensionName.TREND) is evo

    def test_get_missing(self):
        r = RegimeWeightEvolutionResult(evolutions={}, evolved_weights=default_weight_vector())
        assert r.get(DimensionName.TREND) is None

    def test_to_dict_keys(self):
        r = RegimeWeightEvolutionResult(evolutions={}, evolved_weights=default_weight_vector())
        d = r.to_dict()
        expected = {
            "evolutions",
            "evolved_weights",
            "active_regime",
            "config",
            "total_observations",
            "regime_observation_counts",
            "explanation",
        }
        assert set(d.keys()) == expected


class TestSection08BlendFactor:
    def test_zero_samples(self):
        assert _compute_blend_factor(0, 5, 2.0) == 0.0

    def test_half_of_threshold(self):
        bf = _compute_blend_factor(5, 5, 2.0)
        assert abs(bf - 0.5) < 1e-9

    def test_at_threshold(self):
        bf = _compute_blend_factor(10, 5, 2.0)
        assert abs(bf - 1.0) < 1e-9

    def test_above_threshold(self):
        bf = _compute_blend_factor(20, 5, 2.0)
        assert bf == 1.0

    def test_below_min_samples(self):
        bf = _compute_blend_factor(2, 5, 2.0)
        assert bf == 0.2

    def test_zero_min_samples(self):
        assert _compute_blend_factor(5, 0, 2.0) == 0.0

    def test_blend_scale_1(self):
        bf = _compute_blend_factor(5, 5, 1.0)
        assert abs(bf - 1.0) < 1e-9

    def test_blend_scale_3(self):
        bf = _compute_blend_factor(6, 5, 3.0)
        assert abs(bf - 0.4) < 1e-9


class TestSection09StepChangeClamp:
    def test_no_clamp_needed(self):
        result, clamped = _apply_step_change_clamp(0.26, 0.25, 0.05)
        assert abs(result - 0.26) < 1e-9
        assert clamped is False

    def test_clamp_upward(self):
        result, clamped = _apply_step_change_clamp(0.40, 0.25, 0.05)
        assert abs(result - 0.30) < 1e-9
        assert clamped is True

    def test_clamp_downward(self):
        result, clamped = _apply_step_change_clamp(0.10, 0.25, 0.05)
        assert abs(result - 0.20) < 1e-9
        assert clamped is True

    def test_exact_at_boundary(self):
        result, clamped = _apply_step_change_clamp(0.30, 0.25, 0.05)
        assert abs(result - 0.30) < 1e-9
        assert clamped is False

    def test_never_negative(self):
        result, _ = _apply_step_change_clamp(-0.5, 0.02, 0.05)
        assert result >= 0.0

    def test_never_above_one(self):
        result, _ = _apply_step_change_clamp(1.5, 0.98, 0.05)
        assert result <= 1.0


class TestSection10NeutralRegime:
    def test_stable_is_neutral(self):
        assert _is_neutral_regime(RegimeType.STABLE) is True

    def test_trend_up_not_neutral(self):
        assert _is_neutral_regime(RegimeType.TREND_UP) is False

    def test_trend_down_not_neutral(self):
        assert _is_neutral_regime(RegimeType.TREND_DOWN) is False

    def test_spike_up_not_neutral(self):
        assert _is_neutral_regime(RegimeType.SPIKE_UP) is False

    def test_spike_down_not_neutral(self):
        assert _is_neutral_regime(RegimeType.SPIKE_DOWN) is False


class TestSection11Disabled:
    def test_disabled_returns_base(self):
        r = evolve_regime_weights()
        for dim in DimensionName:
            evo = r.get(dim)
            assert evo is not None
            assert evo.final_weight == 0.25
            assert evo.explanation == "regime evolution disabled"

    def test_disabled_explanation(self):
        r = evolve_regime_weights()
        assert "disabled" in r.explanation

    def test_disabled_with_observations(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        r = evolve_regime_weights(observations=obs)
        for dim in DimensionName:
            assert r.get(dim).final_weight == 0.25

    def test_disabled_weights_unchanged(self):
        r = evolve_regime_weights()
        for dim in DimensionName:
            assert r.evolved_weights.get_weight(dim) == 0.25


class TestSection12NoRegimeData:
    def test_no_observations(self):
        cfg = _enabled_config()
        r = evolve_regime_weights(config=cfg, active_regime=RegimeType.TREND_UP)
        assert "no observations" in r.explanation or "global only" in r.explanation

    def test_no_regime_context(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config()
        r = evolve_regime_weights(observations=obs, config=cfg, active_regime=None)
        assert r.active_regime is None
        for dim in DimensionName:
            assert r.get(dim).blend_factor == 0.0

    def test_global_evolution_applied_without_regime(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config()
        r = evolve_regime_weights(observations=obs, config=cfg, active_regime=None, current_tick=10)
        assert r.get(DimensionName.TREND).global_quality > 0


class TestSection13RegimeSpecificLearning:
    def test_positive_signal_increases_weight(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.TREND).final_weight > 0.25

    def test_negative_signal_decreases_weight(self):
        obs = _make_regime_obs(
            DimensionName.RISK, RegimeType.SPIKE_DOWN, 20, direction=-1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.SPIKE_DOWN, config=cfg
        )
        assert r.get(DimensionName.RISK).final_weight < 0.25

    def test_regime_quality_populated(self):
        obs = _make_regime_obs(
            DimensionName.STABILITY, RegimeType.TREND_DOWN, 10, direction=0.5, outcome=0.8
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_DOWN, config=cfg
        )
        assert r.get(DimensionName.STABILITY).regime_quality > 0


class TestSection14DifferentRegimes:
    def test_trend_up_vs_spike_down_differ(self):
        obs_up = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        obs_down = _make_regime_obs(
            DimensionName.TREND, RegimeType.SPIKE_DOWN, 20, direction=-1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r_up = evolve_regime_weights(
            observations=obs_up, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        r_down = evolve_regime_weights(
            observations=obs_down, current_tick=20, active_regime=RegimeType.SPIKE_DOWN, config=cfg
        )
        assert (
            r_up.get(DimensionName.TREND).final_weight
            != r_down.get(DimensionName.TREND).final_weight
        )

    def test_different_regime_different_active(self):
        all_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 15, direction=1.0, outcome=1.0
        ) + _make_regime_obs(
            DimensionName.TREND, RegimeType.SPIKE_DOWN, 15, direction=-1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r_up = evolve_regime_weights(
            observations=all_obs, current_tick=15, active_regime=RegimeType.TREND_UP, config=cfg
        )
        r_down = evolve_regime_weights(
            observations=all_obs, current_tick=15, active_regime=RegimeType.SPIKE_DOWN, config=cfg
        )
        assert (
            r_up.get(DimensionName.TREND).final_weight
            != r_down.get(DimensionName.TREND).final_weight
        )


class TestSection15BlendingLowSamples:
    def test_zero_regime_obs_pure_global(self):
        global_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.STABLE, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=global_obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.TREND).blend_factor == 0.0

    def test_few_regime_obs_low_blend(self):
        regime_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 3, direction=1.0, outcome=1.0
        )
        global_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.STABLE, 20, direction=0.5, outcome=0.5, start_tick=10
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=regime_obs + global_obs,
            current_tick=30,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        assert r.get(DimensionName.TREND).blend_factor < 0.5

    def test_sparse_regime_blends_toward_global(self):
        regime_obs = _make_regime_obs(
            DimensionName.URGENCY, RegimeType.SPIKE_UP, 2, direction=1.0, outcome=1.0
        )
        global_obs = _make_regime_obs(
            DimensionName.URGENCY,
            RegimeType.TREND_DOWN,
            20,
            direction=-1.0,
            outcome=1.0,
            start_tick=10,
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=regime_obs + global_obs,
            current_tick=30,
            active_regime=RegimeType.SPIKE_UP,
            config=cfg,
        )
        assert r.get(DimensionName.URGENCY).blend_factor < 0.3


class TestSection16BlendingHighSamples:
    def test_many_regime_obs_high_blend(self):
        regime_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=regime_obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.TREND).blend_factor >= 1.0

    def test_sufficient_regime_blends_toward_regime(self):
        regime_obs = _make_regime_obs(
            DimensionName.RISK, RegimeType.SPIKE_UP, 15, direction=1.0, outcome=1.0
        )
        other_obs = _make_regime_obs(
            DimensionName.RISK, RegimeType.STABLE, 15, direction=-1.0, outcome=1.0, start_tick=20
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=regime_obs + other_obs,
            current_tick=35,
            active_regime=RegimeType.SPIKE_UP,
            config=cfg,
        )
        assert r.get(DimensionName.RISK).blend_factor > 0.5


class TestSection17StabilitySmooth:
    def test_step_change_clamped_on_switch(self):
        obs_a = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        obs_b = _make_regime_obs(
            DimensionName.TREND,
            RegimeType.SPIKE_DOWN,
            20,
            direction=-1.0,
            outcome=1.0,
            start_tick=20,
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.03)
        r_a = evolve_regime_weights(
            observations=obs_a + obs_b,
            current_tick=40,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        prev_weights = r_a.evolved_weights
        r_b = evolve_regime_weights(
            observations=obs_a + obs_b,
            current_tick=41,
            active_regime=RegimeType.SPIKE_DOWN,
            previous_weights=prev_weights,
            config=cfg,
        )
        for dim in DimensionName:
            assert (
                abs(r_b.evolved_weights.get_weight(dim) - prev_weights.get_weight(dim))
                <= 0.03 + 1e-9
            )

    def test_sequential_switching_bounded(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 15, direction=1.0, outcome=1.0
        ) + _make_regime_obs(
            DimensionName.TREND,
            RegimeType.SPIKE_DOWN,
            15,
            direction=-1.0,
            outcome=1.0,
            start_tick=15,
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.02)
        prev = None
        for i, regime in enumerate([RegimeType.TREND_UP, RegimeType.SPIKE_DOWN] * 5):
            r = evolve_regime_weights(
                observations=obs,
                current_tick=30 + i,
                active_regime=regime,
                previous_weights=prev,
                config=cfg,
            )
            if prev is not None:
                for dim in DimensionName:
                    assert (
                        abs(r.evolved_weights.get_weight(dim) - prev.get_weight(dim)) <= 0.02 + 1e-9
                    )
            prev = r.evolved_weights


class TestSection18Isolation:
    def test_regime_a_does_not_affect_regime_b(self):
        obs_a = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        obs_b = _make_regime_obs(
            DimensionName.TREND,
            RegimeType.SPIKE_DOWN,
            20,
            direction=-1.0,
            outcome=1.0,
            start_tick=20,
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r_both = evolve_regime_weights(
            observations=obs_a + obs_b,
            current_tick=40,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        r_a_only = evolve_regime_weights(
            observations=obs_a, current_tick=40, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert (
            abs(
                r_both.get(DimensionName.TREND).regime_weight
                - r_a_only.get(DimensionName.TREND).regime_weight
            )
            < 1e-9
        )

    def test_other_dimension_untouched(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.RISK).regime_sample_count == 0

    def test_four_dimensions_independent(self):
        obs = []
        for dim, sig in [
            (DimensionName.TREND, 1.0),
            (DimensionName.RISK, -1.0),
            (DimensionName.STABILITY, 0.5),
            (DimensionName.URGENCY, -0.5),
        ]:
            obs.extend(_make_regime_obs(dim, RegimeType.TREND_UP, 20, direction=sig, outcome=1.0))
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.TREND).regime_quality > 0
        assert r.get(DimensionName.RISK).regime_quality < 0


class TestSection19Clamping:
    def test_never_exceeds_max_adjustment(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 50, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(
            min_samples=3, max_adjustment=0.10, max_step_change=0.50, learning_rate=0.50
        )
        r = evolve_regime_weights(
            observations=obs, current_tick=50, active_regime=RegimeType.TREND_UP, config=cfg
        )
        trend = r.get(DimensionName.TREND)
        assert trend.final_weight <= 0.25 + 0.10 + 1e-9
        assert trend.final_weight >= 0.25 - 0.10 - 1e-9

    def test_never_negative(self):
        obs = _make_regime_obs(
            DimensionName.URGENCY, RegimeType.SPIKE_DOWN, 50, direction=-1.0, outcome=1.0
        )
        cfg = _enabled_config(
            min_samples=3, max_adjustment=0.50, max_step_change=0.50, learning_rate=0.50
        )
        r = evolve_regime_weights(
            observations=obs, current_tick=50, active_regime=RegimeType.SPIKE_DOWN, config=cfg
        )
        for dim in DimensionName:
            assert r.evolved_weights.get_weight(dim) >= 0.0

    def test_never_above_one(self):
        base = DimensionWeightVector(
            weights={
                dim.value: DimensionWeight(dimension=dim, weight=0.90) for dim in DimensionName
            }
        )
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 50, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_adjustment=0.50, max_step_change=0.50)
        r = evolve_regime_weights(
            base_weights=base,
            observations=obs,
            current_tick=50,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        for dim in DimensionName:
            assert r.evolved_weights.get_weight(dim) <= 1.0

    def test_global_max_adjustment_respected(self):
        obs = _make_regime_obs(
            DimensionName.RISK, RegimeType.SPIKE_UP, 100, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(
            min_samples=3, max_adjustment=0.05, max_step_change=0.50, learning_rate=0.50
        )
        r = evolve_regime_weights(
            observations=obs, current_tick=100, active_regime=RegimeType.SPIKE_UP, config=cfg
        )
        assert r.get(DimensionName.RISK).final_weight <= 0.25 + 0.05 + 1e-9


class TestSection20Determinism:
    def test_100_identical_runs(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 15, direction=0.7, outcome=0.8
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        results = []
        for _ in range(100):
            r = evolve_regime_weights(
                observations=obs, current_tick=15, active_regime=RegimeType.TREND_UP, config=cfg
            )
            results.append(r.evolved_weights.get_weight(DimensionName.TREND))
        assert all(abs(v - results[0]) < 1e-12 for v in results)

    def test_deterministic_across_dimensions(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 10, direction=1.0, outcome=0.9
        ) + _make_regime_obs(
            DimensionName.RISK, RegimeType.TREND_UP, 10, direction=-0.5, outcome=0.6
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r1 = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        r2 = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for dim in DimensionName:
            assert (
                abs(r1.evolved_weights.get_weight(dim) - r2.evolved_weights.get_weight(dim)) < 1e-12
            )


class TestSection21NeutralRegime:
    def test_stable_uses_global_only(self):
        regime_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.STABLE, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=regime_obs, current_tick=20, active_regime=RegimeType.STABLE, config=cfg
        )
        for dim in DimensionName:
            evo = r.get(dim)
            assert evo.blend_factor == 0.0
            assert "neutral regime" in evo.explanation

    def test_stable_no_regime_specific_evolution(self):
        regime_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.STABLE, 20, direction=1.0, outcome=1.0
        )
        other_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0, start_tick=20
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r_stable = evolve_regime_weights(
            observations=regime_obs + other_obs,
            current_tick=40,
            active_regime=RegimeType.STABLE,
            config=cfg,
        )
        for dim in DimensionName:
            assert r_stable.get(dim).blend_factor == 0.0


class TestSection22NoMutation:
    def test_observations_unchanged_after_evolution(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 10, direction=0.7, outcome=0.8
        )
        originals = [
            (ro.observation.direction_signal, ro.observation.outcome_score, ro.observation.tick)
            for ro in obs
        ]
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for i, ro in enumerate(obs):
            assert ro.observation.direction_signal == originals[i][0]
            assert ro.observation.outcome_score == originals[i][1]
            assert ro.observation.tick == originals[i][2]


class TestSection23Explainability:
    def test_result_has_explanation(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert len(r.explanation) > 0

    def test_dimension_evolution_has_explanation(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for dim in DimensionName:
            assert len(r.get(dim).explanation) > 0

    def test_blend_factor_in_result(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert "blend" in r.get(DimensionName.TREND).explanation

    def test_global_vs_regime_visible(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 15)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=15, active_regime=RegimeType.TREND_UP, config=cfg
        )
        d = r.get(DimensionName.TREND).to_dict()
        assert "global_weight" in d and "regime_weight" in d and "blend_factor" in d

    def test_regime_sample_count_visible(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 8)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=8, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.TREND).regime_sample_count == 8

    def test_step_clamped_in_explanation(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 50, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.01)
        r = evolve_regime_weights(
            observations=obs, current_tick=50, active_regime=RegimeType.TREND_UP, config=cfg
        )
        trend = r.get(DimensionName.TREND)
        assert trend.step_clamped is True
        assert "step_clamped" in trend.explanation


class TestSection24ObservationCounts:
    def test_counts_per_regime(self):
        obs = (
            _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 5)
            + _make_regime_obs(DimensionName.TREND, RegimeType.SPIKE_DOWN, 3, start_tick=5)
            + _make_regime_obs(DimensionName.TREND, RegimeType.STABLE, 7, start_tick=8)
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=15, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.regime_observation_counts["trend_up"] == 5
        assert r.regime_observation_counts["spike_down"] == 3
        assert r.regime_observation_counts["stable"] == 7

    def test_total_observations(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 12)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=12, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.total_observations == 12


class TestSection25MissingWeights:
    def test_none_base_weights(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            base_weights=None,
            observations=obs,
            current_tick=10,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        for dim in DimensionName:
            assert r.evolved_weights.get_weight(dim) >= 0.0

    def test_none_previous_weights_uses_base(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs,
            current_tick=10,
            active_regime=RegimeType.TREND_UP,
            previous_weights=None,
            config=cfg,
        )
        assert r.evolved_weights is not None


class TestSection26Dependencies:
    def test_no_import_from_cells(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "umh.cells" not in src and "umh/cells" not in src

    def test_no_import_from_environments(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "umh.environments" not in src

    def test_no_import_from_adapters(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "umh.adapters" not in src

    def test_imports_from_weight_evolution(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "from umh.runtime.weight_evolution import" in src

    def test_imports_from_dimension_weighting(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "from umh.runtime.dimension_weighting import" in src

    def test_imports_from_regime(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "from umh.runtime.regime import" in src

    def test_no_import_from_strategy_orchestrator(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "strategy_orchestrator" not in src

    def test_no_import_from_feedback_selection(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "feedback_selection" not in src

    def test_no_import_from_weighted_decision(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "weighted_decision" not in src


class TestSection27NoRandomness:
    def test_no_random_import(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "import random" not in src


class TestSection28NoExecution:
    def test_no_subprocess(self):
        import umh.runtime.regime_weight_evolution as mod

        src = open(mod.__file__).read()
        assert "subprocess" not in src


class TestSection29Phase62Regression:
    def test_global_evolve_weights_still_works(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.9, tick=i
            )
            for i in range(10)
        ]
        cfg = WeightEvolutionConfig(enabled=True, min_samples=3)
        r = evolve_weights(base_weights=None, observations=obs, current_tick=10, config=cfg)
        assert r.get(DimensionName.TREND).evolved_weight > 0.25

    def test_phase62_config_unchanged(self):
        assert DEFAULT_EVOLUTION_CONFIG.decay_rate == 0.98
        assert DEFAULT_EVOLUTION_CONFIG.learning_rate == 0.05
        assert DEFAULT_EVOLUTION_CONFIG.min_samples == 5

    def test_phase62_observation_still_works(self):
        obs = WeightObservation(
            dimension=DimensionName.RISK, direction_signal=0.5, outcome_score=0.8, tick=5
        )
        assert obs.dimension is DimensionName.RISK


class TestSection30Phase61Regression:
    def test_weighted_decision_imports(self):
        from umh.runtime.weighted_decision import (
            WeightedDecisionPolicy,
            apply_weighted_influence,
            compute_weight_factor,
        )

        assert WeightedDecisionPolicy().enabled is False

    def test_weighted_decision_still_works(self):
        from umh.runtime.weighted_decision import compute_weight_factor

        factor, used, conf, expl = compute_weight_factor()
        assert factor == 1.0 and used is False


class TestSection31Phase60Regression:
    def test_dimension_weighting_imports(self):
        v = default_weight_vector()
        assert v.get_weight(DimensionName.TREND) == 0.25

    def test_default_weight_vector_unchanged(self):
        v = default_weight_vector()
        for dim in DimensionName:
            assert v.get_weight(dim) == 0.25


class TestSection32Phase59Regression:
    def test_regime_aggregation_imports(self):
        from umh.runtime.regime_aggregation import NEUTRAL_AGGREGATED, aggregate_regimes

        assert NEUTRAL_AGGREGATED.is_neutral

    def test_aggregate_regimes_still_works(self):
        from umh.runtime.regime_aggregation import aggregate_regimes

        r = aggregate_regimes(trend_label="trend_up")
        assert r.get(DimensionName.TREND).regime_label == "trend_up"


class TestSection33Phase58Regression:
    def test_orchestrator_imports(self):
        from umh.runtime.strategy_orchestrator import StrategyCandidate, orchestrate_selection

        c = StrategyCandidate(strategy_id="test")
        assert c.strategy_id == "test"


class TestSection34InitExports:
    def test_regime_weight_evolution_exports(self):
        from umh.runtime import (
            DEFAULT_REGIME_EVOLUTION_CONFIG,
            RegimeDimensionEvolution,
            RegimeObservation,
            RegimeWeightEvolutionConfig,
            RegimeWeightEvolutionResult,
            evolve_regime_weights,
        )

        assert DEFAULT_REGIME_EVOLUTION_CONFIG.enabled is False

    def test_all_phase62_exports_intact(self):
        from umh.runtime import (
            DEFAULT_EVOLUTION_CONFIG,
            DimensionEvolution,
            WeightEvolutionConfig,
            WeightEvolutionResult,
            WeightObservation,
            evolve_weights,
        )

        assert DEFAULT_EVOLUTION_CONFIG.decay_rate == 0.98


class TestSection35Roundtrips:
    def test_config_roundtrip(self):
        d = _enabled_config().to_dict()
        assert d["enabled"] is True and d["max_step_change"] == 0.05

    def test_result_roundtrip(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        d = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        ).to_dict()
        assert "evolutions" in d and d["active_regime"] == "trend_up"

    def test_dimension_evolution_roundtrip(self):
        e = RegimeDimensionEvolution(
            dimension=DimensionName.RISK,
            regime=RegimeType.SPIKE_UP,
            global_weight=0.30,
            regime_weight=0.35,
            blend_factor=0.6,
        )
        d = e.to_dict()
        assert d["dimension"] == "risk" and d["regime"] == "spike_up" and d["blend_factor"] == 0.6


class TestSection36ZeroLearningRate:
    def test_zero_learning_rate_no_change(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 20)
        cfg = RegimeWeightEvolutionConfig(
            enabled=True,
            evolution_config=WeightEvolutionConfig(enabled=True, learning_rate=0.0, min_samples=3),
            max_step_change=0.50,
        )
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for dim in DimensionName:
            assert abs(r.evolved_weights.get_weight(dim) - 0.25) < 1e-9


class TestSection37ZeroMaxAdjustment:
    def test_zero_max_adjustment_no_change(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 20)
        cfg = RegimeWeightEvolutionConfig(
            enabled=True,
            evolution_config=WeightEvolutionConfig(enabled=True, max_adjustment=0.0, min_samples=3),
            max_step_change=0.50,
        )
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for dim in DimensionName:
            assert abs(r.evolved_weights.get_weight(dim) - 0.25) < 1e-9


class TestSection38Stress:
    def test_500_observations(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 500, direction=0.6, outcome=0.7
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=500, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.total_observations == 500

    def test_2000_observations_mixed_regimes(self):
        obs = (
            _make_regime_obs(
                DimensionName.TREND, RegimeType.TREND_UP, 500, direction=1.0, outcome=1.0
            )
            + _make_regime_obs(
                DimensionName.TREND,
                RegimeType.SPIKE_DOWN,
                500,
                direction=-1.0,
                outcome=1.0,
                start_tick=500,
            )
            + _make_regime_obs(
                DimensionName.RISK,
                RegimeType.TREND_UP,
                500,
                direction=0.5,
                outcome=0.5,
                start_tick=1000,
            )
            + _make_regime_obs(
                DimensionName.RISK,
                RegimeType.STABLE,
                500,
                direction=-0.5,
                outcome=0.5,
                start_tick=1500,
            )
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=2000, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.total_observations == 2000


class TestSection39EvolvedSource:
    def test_changed_weight_has_regime_evolved_source(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        trend_dw = r.evolved_weights.get(DimensionName.TREND)
        if trend_dw.weight != 0.25:
            assert trend_dw.source == "regime_evolved"

    def test_unchanged_weight_keeps_original_source(self):
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=[], current_tick=0, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for dim in DimensionName:
            assert r.evolved_weights.get(dim).source == "default"


class TestSection40CustomBase:
    def test_custom_base_respected(self):
        base = DimensionWeightVector(
            weights={
                DimensionName.TREND.value: DimensionWeight(
                    dimension=DimensionName.TREND, weight=0.40
                ),
                DimensionName.RISK.value: DimensionWeight(
                    dimension=DimensionName.RISK, weight=0.20
                ),
                DimensionName.STABILITY.value: DimensionWeight(
                    dimension=DimensionName.STABILITY, weight=0.25
                ),
                DimensionName.URGENCY.value: DimensionWeight(
                    dimension=DimensionName.URGENCY, weight=0.15
                ),
            }
        )
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            base_weights=base,
            observations=obs,
            current_tick=20,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        assert r.get(DimensionName.TREND).final_weight >= 0.40


class TestSection41FullPipeline:
    def test_regime_evolution_feeds_to_weight_vector(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert isinstance(r.evolved_weights, DimensionWeightVector)

    def test_evolved_vector_compatible_with_weighted_decision(self):
        from umh.runtime.weighted_decision import compute_weight_factor, WeightedDecisionPolicy

        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        factor, used, conf, expl = compute_weight_factor(
            weights=r.evolved_weights,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert isinstance(factor, float)


class TestSection42BlendProgression:
    def test_blend_increases_with_samples(self):
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        blends = []
        for n in [1, 3, 5, 8, 10, 15, 20]:
            obs = _make_regime_obs(
                DimensionName.TREND, RegimeType.TREND_UP, n, direction=1.0, outcome=1.0
            )
            r = evolve_regime_weights(
                observations=obs, current_tick=n, active_regime=RegimeType.TREND_UP, config=cfg
            )
            blends.append(r.get(DimensionName.TREND).blend_factor)
        for i in range(1, len(blends)):
            assert blends[i] >= blends[i - 1] - 1e-9


class TestSection43MultiRegimeHistory:
    def test_mixed_regime_history(self):
        obs = (
            _make_regime_obs(
                DimensionName.TREND, RegimeType.TREND_UP, 10, direction=1.0, outcome=1.0
            )
            + _make_regime_obs(
                DimensionName.TREND,
                RegimeType.TREND_DOWN,
                10,
                direction=-1.0,
                outcome=1.0,
                start_tick=10,
            )
            + _make_regime_obs(
                DimensionName.TREND,
                RegimeType.SPIKE_UP,
                5,
                direction=1.0,
                outcome=0.5,
                start_tick=20,
            )
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r_up = evolve_regime_weights(
            observations=obs, current_tick=25, active_regime=RegimeType.TREND_UP, config=cfg
        )
        r_down = evolve_regime_weights(
            observations=obs, current_tick=25, active_regime=RegimeType.TREND_DOWN, config=cfg
        )
        assert r_up.get(DimensionName.TREND).regime_quality > 0
        assert r_down.get(DimensionName.TREND).regime_quality < 0

    def test_active_regime_determines_blend(self):
        obs = _make_regime_obs(
            DimensionName.RISK, RegimeType.SPIKE_UP, 20, direction=1.0, outcome=1.0
        ) + _make_regime_obs(
            DimensionName.RISK, RegimeType.TREND_DOWN, 3, direction=-1.0, outcome=1.0, start_tick=20
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r_spike = evolve_regime_weights(
            observations=obs, current_tick=23, active_regime=RegimeType.SPIKE_UP, config=cfg
        )
        r_trend = evolve_regime_weights(
            observations=obs, current_tick=23, active_regime=RegimeType.TREND_DOWN, config=cfg
        )
        assert (
            r_spike.get(DimensionName.RISK).blend_factor
            > r_trend.get(DimensionName.RISK).blend_factor
        )


class TestSection44EvolutionChain:
    def test_sequential_evolution_converges(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.03)
        prev = None
        weights_over_time = []
        for step in range(30):
            r = evolve_regime_weights(
                observations=obs,
                current_tick=20 + step,
                active_regime=RegimeType.TREND_UP,
                previous_weights=prev,
                config=cfg,
            )
            prev = r.evolved_weights
            weights_over_time.append(r.evolved_weights.get_weight(DimensionName.TREND))
        last_5 = weights_over_time[-5:]
        assert max(last_5) - min(last_5) < 0.02

    def test_each_step_bounded(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.02)
        prev = None
        for step in range(20):
            r = evolve_regime_weights(
                observations=obs,
                current_tick=20 + step,
                active_regime=RegimeType.TREND_UP,
                previous_weights=prev,
                config=cfg,
            )
            if prev is not None:
                for dim in DimensionName:
                    assert (
                        abs(r.evolved_weights.get_weight(dim) - prev.get_weight(dim)) <= 0.02 + 1e-9
                    )
            prev = r.evolved_weights


class TestSection45Symmetry:
    def test_positive_negative_symmetric(self):
        pos_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        neg_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=-1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r_pos = evolve_regime_weights(
            observations=pos_obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        r_neg = evolve_regime_weights(
            observations=neg_obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        pos_delta = r_pos.get(DimensionName.TREND).final_weight - 0.25
        neg_delta = r_neg.get(DimensionName.TREND).final_weight - 0.25
        assert abs(pos_delta + neg_delta) < 1e-9


class TestSection46ConfigCustom:
    def test_custom_min_samples(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 3)
        cfg = _enabled_config(min_samples=10, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=3, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.TREND).final_weight == 0.25

    def test_custom_blend_scale(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg_low = _enabled_config(min_samples=5, blend_scale=1.0, max_step_change=0.50)
        cfg_high = _enabled_config(min_samples=5, blend_scale=5.0, max_step_change=0.50)
        r_low = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg_low
        )
        r_high = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg_high
        )
        assert (
            r_low.get(DimensionName.TREND).blend_factor
            >= r_high.get(DimensionName.TREND).blend_factor
        )

    def test_custom_max_step_change(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 50, direction=1.0, outcome=1.0
        )
        cfg_tight = _enabled_config(min_samples=3, max_step_change=0.01)
        cfg_loose = _enabled_config(min_samples=3, max_step_change=0.50)
        r_tight = evolve_regime_weights(
            observations=obs, current_tick=50, active_regime=RegimeType.TREND_UP, config=cfg_tight
        )
        r_loose = evolve_regime_weights(
            observations=obs, current_tick=50, active_regime=RegimeType.TREND_UP, config=cfg_loose
        )
        assert (
            abs(r_tight.evolved_weights.get_weight(DimensionName.TREND) - 0.25)
            <= abs(r_loose.evolved_weights.get_weight(DimensionName.TREND) - 0.25) + 1e-9
        )


class TestSection47DecayInfluence:
    def test_regime_uses_decay_from_config(self):
        old_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 10, direction=1.0, outcome=1.0, start_tick=0
        )
        new_obs = _make_regime_obs(
            DimensionName.TREND,
            RegimeType.TREND_UP,
            10,
            direction=-1.0,
            outcome=1.0,
            start_tick=100,
        )
        cfg = _enabled_config(min_samples=3, decay_rate=0.90, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=old_obs + new_obs,
            current_tick=110,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        assert r.get(DimensionName.TREND).regime_quality < 0


class TestSection48AllRegimeTypes:
    def test_all_regime_types_produce_result(self):
        for rt in RegimeType:
            obs = _make_regime_obs(DimensionName.TREND, rt, 10, direction=1.0, outcome=1.0)
            cfg = _enabled_config(min_samples=3, max_step_change=0.50)
            r = evolve_regime_weights(
                observations=obs, current_tick=10, active_regime=rt, config=cfg
            )
            assert r.active_regime is rt


class TestSection49ActiveRegime:
    def test_active_regime_set(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.SPIKE_UP, 10)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.SPIKE_UP, config=cfg
        )
        assert r.active_regime is RegimeType.SPIKE_UP

    def test_active_regime_none(self):
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(config=cfg)
        assert r.active_regime is None

    def test_active_regime_in_dict(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_DOWN, 5)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=5, active_regime=RegimeType.TREND_DOWN, config=cfg
        )
        assert r.to_dict()["active_regime"] == "trend_down"


class TestSection50VarianceDamping:
    def test_high_variance_reduces_delta(self):
        mixed_obs = [
            RegimeObservation(
                observation=WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=(1.0 if i % 2 == 0 else -1.0),
                    outcome_score=1.0,
                    tick=i,
                ),
                regime=RegimeType.TREND_UP,
            )
            for i in range(20)
        ]
        consistent_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r_mixed = evolve_regime_weights(
            observations=mixed_obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        r_consistent = evolve_regime_weights(
            observations=consistent_obs,
            current_tick=20,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        assert abs(r_mixed.evolved_weights.get_weight(DimensionName.TREND) - 0.25) <= abs(
            r_consistent.evolved_weights.get_weight(DimensionName.TREND) - 0.25
        )


class TestSection51SingleDimension:
    def test_single_dimension_evolves(self):
        obs = _make_regime_obs(
            DimensionName.STABILITY, RegimeType.TREND_DOWN, 15, direction=0.8, outcome=0.9
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=15, active_regime=RegimeType.TREND_DOWN, config=cfg
        )
        assert r.get(DimensionName.STABILITY).regime_sample_count == 15
        assert r.get(DimensionName.STABILITY).final_weight > 0.25

    def test_untouched_dimensions_default(self):
        obs = _make_regime_obs(
            DimensionName.STABILITY, RegimeType.TREND_DOWN, 15, direction=0.8, outcome=0.9
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=15, active_regime=RegimeType.TREND_DOWN, config=cfg
        )
        for dim in [DimensionName.TREND, DimensionName.RISK, DimensionName.URGENCY]:
            assert r.get(dim).regime_sample_count == 0


class TestSection52RegimeVsGlobal:
    def test_regime_specific_diverges_from_global(self):
        pos_regime = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        neg_other = _make_regime_obs(
            DimensionName.TREND,
            RegimeType.SPIKE_DOWN,
            20,
            direction=-1.0,
            outcome=1.0,
            start_tick=20,
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=pos_regime + neg_other,
            current_tick=40,
            active_regime=RegimeType.TREND_UP,
            config=cfg,
        )
        assert r.get(DimensionName.TREND).regime_weight > r.get(DimensionName.TREND).global_weight

    def test_with_enough_samples_regime_dominates(self):
        regime_obs = _make_regime_obs(
            DimensionName.URGENCY, RegimeType.SPIKE_UP, 30, direction=1.0, outcome=1.0
        )
        other_obs = _make_regime_obs(
            DimensionName.URGENCY,
            RegimeType.TREND_DOWN,
            30,
            direction=-1.0,
            outcome=1.0,
            start_tick=30,
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=regime_obs + other_obs,
            current_tick=60,
            active_regime=RegimeType.SPIKE_UP,
            config=cfg,
        )
        assert (
            r.get(DimensionName.URGENCY).blend_factor >= 1.0
            and r.get(DimensionName.URGENCY).final_weight > 0.25
        )


class TestSection53PreviousWeights:
    def test_previous_weights_affect_step_clamp(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        prev = DimensionWeightVector(
            weights={
                dim.value: DimensionWeight(dimension=dim, weight=0.10) for dim in DimensionName
            }
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.02)
        r = evolve_regime_weights(
            observations=obs,
            current_tick=20,
            active_regime=RegimeType.TREND_UP,
            previous_weights=prev,
            config=cfg,
        )
        assert abs(r.evolved_weights.get_weight(DimensionName.TREND) - 0.10) <= 0.02 + 1e-9


class TestSection54EmptyObservations:
    def test_empty_obs_returns_base(self):
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=[], current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for dim in DimensionName:
            assert abs(r.evolved_weights.get_weight(dim) - 0.25) < 1e-9

    def test_empty_obs_blend_factor_zero(self):
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=[], current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for dim in DimensionName:
            assert r.get(dim).blend_factor == 0.0


class TestSection55SampleGate:
    def test_below_min_samples_gated(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 2, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=2, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert abs(r.get(DimensionName.TREND).final_weight - 0.25) < 1e-9

    def test_at_min_samples_evolves(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 5, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=5, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=5, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.TREND).final_weight >= 0.25


class TestSection56NeutralSignals:
    def test_zero_direction_no_change(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=0.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert abs(r.get(DimensionName.TREND).final_weight - 0.25) < 1e-9

    def test_zero_outcome_no_change(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=0.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert abs(r.get(DimensionName.TREND).final_weight - 0.25) < 1e-9


class TestSection57LearningRateSensitivity:
    def test_higher_learning_rate_bigger_change(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg_low = _enabled_config(learning_rate=0.01, min_samples=3, max_step_change=0.50)
        cfg_high = _enabled_config(learning_rate=0.10, min_samples=3, max_step_change=0.50)
        r_low = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg_low
        )
        r_high = evolve_regime_weights(
            observations=obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg_high
        )
        assert (
            abs(r_high.evolved_weights.get_weight(DimensionName.TREND) - 0.25)
            >= abs(r_low.evolved_weights.get_weight(DimensionName.TREND) - 0.25) - 1e-9
        )


class TestSection58DecayRateSensitivity:
    def test_lower_decay_emphasizes_recent(self):
        old_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 10, direction=1.0, outcome=1.0, start_tick=0
        )
        new_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 10, direction=-1.0, outcome=1.0, start_tick=50
        )
        cfg_low = _enabled_config(decay_rate=0.80, min_samples=3, max_step_change=0.50)
        cfg_high = _enabled_config(decay_rate=0.99, min_samples=3, max_step_change=0.50)
        r_low = evolve_regime_weights(
            observations=old_obs + new_obs,
            current_tick=60,
            active_regime=RegimeType.TREND_UP,
            config=cfg_low,
        )
        r_high = evolve_regime_weights(
            observations=old_obs + new_obs,
            current_tick=60,
            active_regime=RegimeType.TREND_UP,
            config=cfg_high,
        )
        assert r_low.evolved_weights.get_weight(
            DimensionName.TREND
        ) <= r_high.evolved_weights.get_weight(DimensionName.TREND)


class TestSection59ToDictCompleteness:
    def test_result_to_dict_complete(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        d = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        ).to_dict()
        assert "regime_observation_counts" in d and "trend_up" in d["regime_observation_counts"]

    def test_evolution_to_dict_has_all_fields(self):
        e = RegimeDimensionEvolution(
            dimension=DimensionName.TREND,
            regime=RegimeType.TREND_UP,
            global_weight=0.28,
            regime_weight=0.32,
            blended_weight=0.30,
            final_weight=0.29,
            blend_factor=0.7,
            regime_sample_count=12,
            global_sample_count=25,
            regime_quality=0.6,
            global_quality=0.3,
            step_clamped=True,
            explanation="test",
        )
        d = e.to_dict()
        assert (
            d["global_weight"] == 0.28 and d["regime_weight"] == 0.32 and d["step_clamped"] is True
        )


class TestSection60RegimeObsDict:
    def test_regime_obs_roundtrip(self):
        obs = WeightObservation(
            dimension=DimensionName.URGENCY, direction_signal=0.5, outcome_score=0.7, tick=42
        )
        ro = RegimeObservation(observation=obs, regime=RegimeType.SPIKE_DOWN)
        d = ro.to_dict()
        assert (
            d["regime"] == "spike_down"
            and d["observation"]["dimension"] == "urgency"
            and d["observation"]["tick"] == 42
        )


class TestSection61MultiDimPerRegime:
    def test_all_dims_evolve_in_one_regime(self):
        obs = []
        for dim in DimensionName:
            obs.extend(_make_regime_obs(dim, RegimeType.TREND_UP, 15, direction=1.0, outcome=0.8))
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=15, active_regime=RegimeType.TREND_UP, config=cfg
        )
        for dim in DimensionName:
            assert r.get(dim).regime_sample_count == 15 and r.get(dim).final_weight >= 0.25


class TestSection62NoRunaway:
    def test_repeated_evolution_bounded(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_adjustment=0.15, max_step_change=0.50)
        prev = None
        for _ in range(20):
            r = evolve_regime_weights(
                observations=obs,
                current_tick=20,
                active_regime=RegimeType.TREND_UP,
                previous_weights=prev,
                config=cfg,
            )
            prev = r.evolved_weights
        for dim in DimensionName:
            assert 0.0 <= prev.get_weight(dim) <= 1.0

    def test_10_step_no_runaway(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 50, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(
            min_samples=3, max_adjustment=0.15, max_step_change=0.03, learning_rate=0.10
        )
        prev = None
        for _ in range(10):
            r = evolve_regime_weights(
                observations=obs,
                current_tick=50,
                active_regime=RegimeType.TREND_UP,
                previous_weights=prev,
                config=cfg,
            )
            prev = r.evolved_weights
            for dim in DimensionName:
                assert 0.25 - 0.15 - 1e-9 <= prev.get_weight(dim) <= 0.25 + 0.15 + 1e-9


class TestSection63DisabledWithRegime:
    def test_disabled_ignores_regime(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 20)
        r = evolve_regime_weights(
            observations=obs,
            current_tick=20,
            active_regime=RegimeType.TREND_UP,
            config=RegimeWeightEvolutionConfig(enabled=False),
        )
        for dim in DimensionName:
            assert r.evolved_weights.get_weight(dim) == 0.25

    def test_disabled_explanation_mentions_disabled(self):
        r = evolve_regime_weights(config=RegimeWeightEvolutionConfig(enabled=False))
        assert "disabled" in r.explanation


class TestSection64CrossRegimeStress:
    def test_five_regimes_no_contamination(self):
        all_obs = []
        for rt, sig in [
            (RegimeType.STABLE, 0.0),
            (RegimeType.TREND_UP, 1.0),
            (RegimeType.TREND_DOWN, -1.0),
            (RegimeType.SPIKE_UP, 0.8),
            (RegimeType.SPIKE_DOWN, -0.8),
        ]:
            all_obs.extend(
                _make_regime_obs(DimensionName.TREND, rt, 20, direction=sig, outcome=1.0)
            )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        results = {}
        for rt in [
            RegimeType.TREND_UP,
            RegimeType.TREND_DOWN,
            RegimeType.SPIKE_UP,
            RegimeType.SPIKE_DOWN,
        ]:
            r = evolve_regime_weights(
                observations=all_obs, current_tick=100, active_regime=rt, config=cfg
            )
            results[rt] = r.get(DimensionName.TREND).regime_quality
        assert results[RegimeType.TREND_UP] > 0 and results[RegimeType.TREND_DOWN] < 0
        assert results[RegimeType.SPIKE_UP] > 0 and results[RegimeType.SPIKE_DOWN] < 0


class TestSection65BlendEdge:
    def test_exactly_at_2x_min_samples(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 10)
        cfg = _enabled_config(min_samples=5, blend_scale=2.0, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=10, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert abs(r.get(DimensionName.TREND).blend_factor - 1.0) < 1e-9

    def test_one_below_2x_min_samples(self):
        obs = _make_regime_obs(DimensionName.TREND, RegimeType.TREND_UP, 9)
        cfg = _enabled_config(min_samples=5, blend_scale=2.0, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=9, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert r.get(DimensionName.TREND).blend_factor < 1.0


class TestSection66RegimeSwitchTransition:
    def test_alternating_regimes_smooth(self):
        obs_up = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        obs_down = _make_regime_obs(
            DimensionName.TREND,
            RegimeType.SPIKE_DOWN,
            20,
            direction=-1.0,
            outcome=1.0,
            start_tick=20,
        )
        all_obs = obs_up + obs_down
        cfg = _enabled_config(min_samples=3, max_step_change=0.02)
        prev = None
        max_jump = 0.0
        for i, rt in enumerate(
            [RegimeType.TREND_UP, RegimeType.SPIKE_DOWN, RegimeType.TREND_UP, RegimeType.SPIKE_DOWN]
            * 3
        ):
            r = evolve_regime_weights(
                observations=all_obs,
                current_tick=40 + i,
                active_regime=rt,
                previous_weights=prev,
                config=cfg,
            )
            if prev is not None:
                for dim in DimensionName:
                    max_jump = max(
                        max_jump, abs(r.evolved_weights.get_weight(dim) - prev.get_weight(dim))
                    )
            prev = r.evolved_weights
        assert max_jump <= 0.02 + 1e-9


class TestSection67PartialSignals:
    def test_partial_direction_signals(self):
        obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 15, direction=0.3, outcome=0.6
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r = evolve_regime_weights(
            observations=obs, current_tick=15, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert (
            r.get(DimensionName.TREND).regime_quality > 0
            and r.get(DimensionName.TREND).final_weight >= 0.25
        )

    def test_weak_signals_small_delta(self):
        weak_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=0.1, outcome=0.1
        )
        strong_obs = _make_regime_obs(
            DimensionName.TREND, RegimeType.TREND_UP, 20, direction=1.0, outcome=1.0
        )
        cfg = _enabled_config(min_samples=3, max_step_change=0.50)
        r_weak = evolve_regime_weights(
            observations=weak_obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        r_strong = evolve_regime_weights(
            observations=strong_obs, current_tick=20, active_regime=RegimeType.TREND_UP, config=cfg
        )
        assert abs(r_weak.evolved_weights.get_weight(DimensionName.TREND) - 0.25) <= abs(
            r_strong.evolved_weights.get_weight(DimensionName.TREND) - 0.25
        )


class TestSection68InitRegression:
    def test_phase62_exports(self):
        from umh.runtime import (
            DEFAULT_EVOLUTION_CONFIG,
            DimensionEvolution,
            WeightEvolutionConfig,
            WeightEvolutionResult,
            WeightObservation,
            evolve_weights,
        )

        assert callable(evolve_weights)

    def test_phase61_exports(self):
        from umh.runtime import (
            DEFAULT_WEIGHTED_DECISION_POLICY,
            WeightedDecisionBatchResult,
            WeightedDecisionPolicy,
            WeightedDecisionResult,
            apply_weighted_influence,
            compute_weight_factor,
        )

        assert callable(apply_weighted_influence)

    def test_phase60_exports(self):
        from umh.runtime import (
            DEFAULT_WEIGHTING_CONFIG,
            DEFAULT_WEIGHT_VECTOR,
            DimensionWeight,
            DimensionWeightVector,
            WeightingConfig,
            compute_dimension_weights,
            default_weight_vector,
        )

        assert callable(compute_dimension_weights)

    def test_phase59_exports(self):
        from umh.runtime import (
            AggregatedRegimeState,
            DimensionName,
            DimensionRegime,
            DirectionCategory,
            NEUTRAL_AGGREGATED,
            aggregate_regimes,
        )

        assert NEUTRAL_AGGREGATED is not None

    def test_phase58_exports(self):
        from umh.runtime import (
            StrategyCandidate,
            StrategyOrchestrationPolicy,
            StrategySelectionResult,
            orchestrate_selection,
        )

        assert callable(orchestrate_selection)

    def test_phase63_exports(self):
        from umh.runtime import (
            DEFAULT_REGIME_EVOLUTION_CONFIG,
            RegimeDimensionEvolution,
            RegimeObservation,
            RegimeWeightEvolutionConfig,
            RegimeWeightEvolutionResult,
            evolve_regime_weights,
        )

        assert callable(evolve_regime_weights)
