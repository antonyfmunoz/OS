"""Phase 62 — Temporal weight evolution tests.

Tests time-aware evolution of dimension weights from historical
outcome–dimension signal correlations.

Invariants 265-273.
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
from umh.runtime.regime_aggregation import DimensionName, DirectionCategory
from umh.runtime.weight_evolution import (
    DEFAULT_EVOLUTION_CONFIG,
    DimensionEvolution,
    WeightEvolutionConfig,
    WeightEvolutionResult,
    WeightObservation,
    _compute_decayed_quality,
    _compute_signal_variance,
    _evolve_single_dimension,
    evolve_weights,
)


# ===========================================================================
# SECTION 1 — WeightEvolutionConfig defaults
# ===========================================================================


class TestSection01ConfigDefaults:
    def test_default_enabled(self):
        assert WeightEvolutionConfig().enabled is False

    def test_default_decay_rate(self):
        assert WeightEvolutionConfig().decay_rate == 0.98

    def test_default_learning_rate(self):
        assert WeightEvolutionConfig().learning_rate == 0.05

    def test_default_min_samples(self):
        assert WeightEvolutionConfig().min_samples == 5

    def test_default_max_adjustment(self):
        assert WeightEvolutionConfig().max_adjustment == 0.15

    def test_default_variance_damping_threshold(self):
        assert WeightEvolutionConfig().variance_damping_threshold == 0.25

    def test_default_constant(self):
        c = DEFAULT_EVOLUTION_CONFIG
        assert c.enabled is False
        assert c.decay_rate == 0.98


# ===========================================================================
# SECTION 2 — WeightEvolutionConfig bounds
# ===========================================================================


class TestSection02ConfigBounds:
    def test_decay_rate_clamped_low(self):
        c = WeightEvolutionConfig(decay_rate=-1.0)
        assert c.decay_rate == 0.0

    def test_decay_rate_clamped_high(self):
        c = WeightEvolutionConfig(decay_rate=5.0)
        assert c.decay_rate == 1.0

    def test_learning_rate_clamped_low(self):
        c = WeightEvolutionConfig(learning_rate=-1.0)
        assert c.learning_rate == 0.0

    def test_learning_rate_clamped_high(self):
        c = WeightEvolutionConfig(learning_rate=2.0)
        assert c.learning_rate == 0.50

    def test_min_samples_floor(self):
        c = WeightEvolutionConfig(min_samples=0)
        assert c.min_samples == 1

    def test_max_adjustment_clamped_low(self):
        c = WeightEvolutionConfig(max_adjustment=-1.0)
        assert c.max_adjustment == 0.0

    def test_max_adjustment_clamped_high(self):
        c = WeightEvolutionConfig(max_adjustment=2.0)
        assert c.max_adjustment == 0.50

    def test_variance_threshold_clamped(self):
        c = WeightEvolutionConfig(variance_damping_threshold=5.0)
        assert c.variance_damping_threshold == 1.0


# ===========================================================================
# SECTION 3 — WeightEvolutionConfig to_dict
# ===========================================================================


class TestSection03ConfigDict:
    def test_to_dict_keys(self):
        d = WeightEvolutionConfig().to_dict()
        expected = {
            "enabled",
            "decay_rate",
            "learning_rate",
            "min_samples",
            "max_adjustment",
            "variance_damping_threshold",
        }
        assert set(d.keys()) == expected

    def test_to_dict_values(self):
        d = WeightEvolutionConfig(enabled=True, decay_rate=0.95).to_dict()
        assert d["enabled"] is True
        assert d["decay_rate"] == 0.95


# ===========================================================================
# SECTION 4 — WeightEvolutionConfig frozen
# ===========================================================================


class TestSection04ConfigFrozen:
    def test_frozen(self):
        c = WeightEvolutionConfig()
        try:
            c.enabled = True
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 5 — WeightObservation defaults
# ===========================================================================


class TestSection05ObservationDefaults:
    def test_default_direction_signal(self):
        obs = WeightObservation(dimension=DimensionName.TREND)
        assert obs.direction_signal == 0.0

    def test_default_outcome_score(self):
        obs = WeightObservation(dimension=DimensionName.TREND)
        assert obs.outcome_score == 0.0

    def test_default_tick(self):
        obs = WeightObservation(dimension=DimensionName.TREND)
        assert obs.tick == 0


# ===========================================================================
# SECTION 6 — WeightObservation bounds
# ===========================================================================


class TestSection06ObservationBounds:
    def test_direction_signal_clamped_low(self):
        obs = WeightObservation(dimension=DimensionName.TREND, direction_signal=-5.0)
        assert obs.direction_signal == -1.0

    def test_direction_signal_clamped_high(self):
        obs = WeightObservation(dimension=DimensionName.TREND, direction_signal=5.0)
        assert obs.direction_signal == 1.0

    def test_outcome_score_clamped_low(self):
        obs = WeightObservation(dimension=DimensionName.TREND, outcome_score=-1.0)
        assert obs.outcome_score == 0.0

    def test_outcome_score_clamped_high(self):
        obs = WeightObservation(dimension=DimensionName.TREND, outcome_score=5.0)
        assert obs.outcome_score == 1.0

    def test_tick_floor(self):
        obs = WeightObservation(dimension=DimensionName.TREND, tick=-10)
        assert obs.tick == 0


# ===========================================================================
# SECTION 7 — WeightObservation to_dict
# ===========================================================================


class TestSection07ObservationDict:
    def test_to_dict_keys(self):
        obs = WeightObservation(dimension=DimensionName.TREND)
        d = obs.to_dict()
        expected = {"dimension", "direction_signal", "outcome_score", "tick"}
        assert set(d.keys()) == expected


# ===========================================================================
# SECTION 8 — WeightObservation frozen
# ===========================================================================


class TestSection08ObservationFrozen:
    def test_frozen(self):
        obs = WeightObservation(dimension=DimensionName.TREND)
        try:
            obs.direction_signal = 0.5
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 9 — DimensionEvolution defaults
# ===========================================================================


class TestSection09EvolutionDefaults:
    def test_default_base_weight(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        assert e.base_weight == 0.25

    def test_default_evolved_weight(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        assert e.evolved_weight == 0.25

    def test_default_quality_score(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        assert e.quality_score == 0.0

    def test_default_sample_count(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        assert e.sample_count == 0

    def test_default_decay_applied(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        assert e.decay_applied is False

    def test_default_variance_damped(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        assert e.variance_damped is False

    def test_default_sample_gated(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        assert e.sample_gated is False

    def test_default_delta(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        assert e.delta == 0.0


# ===========================================================================
# SECTION 10 — DimensionEvolution bounds
# ===========================================================================


class TestSection10EvolutionBounds:
    def test_base_weight_clamped(self):
        e = DimensionEvolution(dimension=DimensionName.TREND, base_weight=5.0)
        assert e.base_weight == 1.0

    def test_evolved_weight_clamped(self):
        e = DimensionEvolution(dimension=DimensionName.TREND, evolved_weight=-1.0)
        assert e.evolved_weight == 0.0

    def test_quality_score_clamped_low(self):
        e = DimensionEvolution(dimension=DimensionName.TREND, quality_score=-5.0)
        assert e.quality_score == -1.0

    def test_quality_score_clamped_high(self):
        e = DimensionEvolution(dimension=DimensionName.TREND, quality_score=5.0)
        assert e.quality_score == 1.0


# ===========================================================================
# SECTION 11 — DimensionEvolution to_dict
# ===========================================================================


class TestSection11EvolutionDict:
    def test_to_dict_keys(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        d = e.to_dict()
        expected = {
            "dimension",
            "base_weight",
            "evolved_weight",
            "quality_score",
            "sample_count",
            "decay_applied",
            "variance_damped",
            "sample_gated",
            "delta",
            "explanation",
        }
        assert set(d.keys()) == expected

    def test_delta_in_dict(self):
        e = DimensionEvolution(
            dimension=DimensionName.TREND,
            base_weight=0.25,
            evolved_weight=0.30,
        )
        d = e.to_dict()
        assert abs(d["delta"] - 0.05) < 1e-4


# ===========================================================================
# SECTION 12 — DimensionEvolution frozen
# ===========================================================================


class TestSection12EvolutionFrozen:
    def test_frozen(self):
        e = DimensionEvolution(dimension=DimensionName.TREND)
        try:
            e.evolved_weight = 0.5
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 13 — WeightEvolutionResult defaults
# ===========================================================================


class TestSection13ResultDefaults:
    def test_default_total_observations(self):
        r = WeightEvolutionResult(
            evolutions={},
            evolved_weights=default_weight_vector(),
        )
        assert r.total_observations == 0

    def test_default_explanation(self):
        r = WeightEvolutionResult(
            evolutions={},
            evolved_weights=default_weight_vector(),
        )
        assert r.explanation == ""


# ===========================================================================
# SECTION 14 — WeightEvolutionResult to_dict
# ===========================================================================


class TestSection14ResultDict:
    def test_to_dict_keys(self):
        r = WeightEvolutionResult(
            evolutions={},
            evolved_weights=default_weight_vector(),
        )
        d = r.to_dict()
        expected = {"evolutions", "evolved_weights", "config", "total_observations", "explanation"}
        assert set(d.keys()) == expected

    def test_get_dimension(self):
        evo = DimensionEvolution(dimension=DimensionName.TREND, evolved_weight=0.30)
        r = WeightEvolutionResult(
            evolutions={DimensionName.TREND.value: evo},
            evolved_weights=default_weight_vector(),
        )
        assert r.get(DimensionName.TREND) is not None
        assert r.get(DimensionName.TREND).evolved_weight == 0.30

    def test_get_missing_dimension(self):
        r = WeightEvolutionResult(
            evolutions={},
            evolved_weights=default_weight_vector(),
        )
        assert r.get(DimensionName.TREND) is None


# ===========================================================================
# SECTION 15 — _compute_decayed_quality: empty
# ===========================================================================


class TestSection15DecayedQualityEmpty:
    def test_empty_observations(self):
        assert _compute_decayed_quality([], 10, 0.98) == 0.0


# ===========================================================================
# SECTION 16 — _compute_decayed_quality: single observation
# ===========================================================================


class TestSection16DecayedQualitySingle:
    def test_positive_signal_positive_outcome(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.8, tick=10
            )
        ]
        q = _compute_decayed_quality(obs, 10, 0.98)
        assert abs(q - 0.8) < 1e-9

    def test_negative_signal_positive_outcome(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=0.8, tick=10
            )
        ]
        q = _compute_decayed_quality(obs, 10, 0.98)
        assert abs(q - (-0.8)) < 1e-9

    def test_neutral_signal(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=0.0, outcome_score=0.8, tick=10
            )
        ]
        q = _compute_decayed_quality(obs, 10, 0.98)
        assert q == 0.0


# ===========================================================================
# SECTION 17 — _compute_decayed_quality: time decay (inv 267)
# ===========================================================================


class TestSection17TimeDecay:
    def test_recent_has_more_weight(self):
        old = WeightObservation(
            dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=0
        )
        new = WeightObservation(
            dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=1.0, tick=100
        )
        q = _compute_decayed_quality([old, new], 100, 0.98)
        assert q < 0.0

    def test_no_decay_at_same_tick(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=50
            )
        ]
        q = _compute_decayed_quality(obs, 50, 0.98)
        assert abs(q - 1.0) < 1e-9

    def test_decay_reduces_old_signal(self):
        old_obs = WeightObservation(
            dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=0
        )
        new_obs = WeightObservation(
            dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=0.5, tick=100
        )
        q = _compute_decayed_quality([old_obs, new_obs], 100, 0.90)
        assert q < 0.0

    def test_zero_decay_rate_kills_old(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=0
            )
        ]
        q = _compute_decayed_quality(obs, 1, 0.0)
        assert q == 0.0

    def test_decay_one_preserves_all(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=0
            )
        ]
        q = _compute_decayed_quality(obs, 1000, 1.0)
        assert abs(q - 1.0) < 1e-9


# ===========================================================================
# SECTION 18 — _compute_signal_variance
# ===========================================================================


class TestSection18SignalVariance:
    def test_empty(self):
        assert _compute_signal_variance([]) == 0.0

    def test_single(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.8
            )
        ]
        assert _compute_signal_variance(obs) == 0.0

    def test_identical_signals(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.5
            ),
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.5
            ),
        ]
        assert _compute_signal_variance(obs) == 0.0

    def test_varied_signals(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0
            ),
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=1.0
            ),
        ]
        v = _compute_signal_variance(obs)
        assert v > 0.0

    def test_high_variance_from_mixed(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0
            ),
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=1.0
            ),
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.0
            ),
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=0.0
            ),
        ]
        v = _compute_signal_variance(obs)
        assert v > 0.0


# ===========================================================================
# SECTION 19 — evolve_weights: disabled (inv 272)
# ===========================================================================


class TestSection19Disabled:
    def test_disabled_returns_base(self):
        base = default_weight_vector()
        result = evolve_weights(
            base_weights=base,
            observations=_make_positive_observations(DimensionName.TREND, 10),
            current_tick=10,
            config=WeightEvolutionConfig(enabled=False),
        )
        assert result.evolved_weights is base
        assert "disabled" in result.explanation

    def test_default_config_disabled(self):
        result = evolve_weights()
        assert "disabled" in result.explanation


# ===========================================================================
# SECTION 20 — evolve_weights: no history (inv 272)
# ===========================================================================


class TestSection20NoHistory:
    def test_no_observations(self):
        result = evolve_weights(
            config=WeightEvolutionConfig(enabled=True),
        )
        assert "no observations" in result.explanation
        for dim in DimensionName:
            evo = result.get(dim)
            assert evo is not None
            assert evo.evolved_weight == evo.base_weight

    def test_empty_list(self):
        result = evolve_weights(
            observations=[],
            config=WeightEvolutionConfig(enabled=True),
        )
        assert result.total_observations == 0


# ===========================================================================
# SECTION 21 — evolve_weights: positive outcomes increase weight
# ===========================================================================


class TestSection21PositiveOutcomes:
    def test_consistent_positive_increases(self):
        obs = _make_positive_observations(DimensionName.TREND, 20)
        result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo is not None
        assert evo.evolved_weight > evo.base_weight
        assert evo.quality_score > 0.0

    def test_positive_signal_with_success(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.RISK,
                direction_signal=1.0,
                outcome_score=0.9,
                tick=i,
            )
            for i in range(10)
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.RISK)
        assert evo.evolved_weight > evo.base_weight


# ===========================================================================
# SECTION 22 — evolve_weights: negative outcomes decrease weight
# ===========================================================================


class TestSection22NegativeOutcomes:
    def test_consistent_negative_decreases(self):
        obs = _make_negative_observations(DimensionName.TREND, 20)
        result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo is not None
        assert evo.evolved_weight < evo.base_weight
        assert evo.quality_score < 0.0

    def test_negative_signal_with_success(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.STABILITY,
                direction_signal=-1.0,
                outcome_score=0.9,
                tick=i,
            )
            for i in range(10)
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.STABILITY)
        assert evo.evolved_weight < evo.base_weight


# ===========================================================================
# SECTION 23 — evolve_weights: decay influence (inv 267)
# ===========================================================================


class TestSection23DecayInfluence:
    def test_old_data_has_less_influence(self):
        positive = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=0
            )
            for _ in range(5)
        ]
        negative = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=0.5, tick=100
            )
            for _ in range(5)
        ]

        cfg = WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=0.90)

        mixed = positive + negative
        result = evolve_weights(observations=mixed, current_tick=100, config=cfg)
        evo = result.get(DimensionName.TREND)
        assert evo.quality_score < 0.0

    def test_decay_applied_flag(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=0.98),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.decay_applied is True

    def test_no_decay_when_rate_one(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=1.0),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.decay_applied is False


# ===========================================================================
# SECTION 24 — evolve_weights: bounded (inv 265)
# ===========================================================================


class TestSection24Bounded:
    def test_weight_bounded_above(self):
        obs = _make_positive_observations(DimensionName.TREND, 100)
        result = evolve_weights(
            observations=obs,
            current_tick=100,
            config=WeightEvolutionConfig(
                enabled=True,
                min_samples=5,
                learning_rate=0.50,
                max_adjustment=0.15,
            ),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.evolved_weight <= evo.base_weight + 0.15 + 1e-9

    def test_weight_bounded_below(self):
        obs = _make_negative_observations(DimensionName.TREND, 100)
        result = evolve_weights(
            observations=obs,
            current_tick=100,
            config=WeightEvolutionConfig(
                enabled=True,
                min_samples=5,
                learning_rate=0.50,
                max_adjustment=0.15,
            ),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.evolved_weight >= evo.base_weight - 0.15 - 1e-9

    def test_weight_never_negative(self):
        obs = _make_negative_observations(DimensionName.TREND, 200)
        result = evolve_weights(
            observations=obs,
            current_tick=200,
            config=WeightEvolutionConfig(
                enabled=True,
                min_samples=5,
                learning_rate=0.50,
                max_adjustment=0.50,
            ),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.evolved_weight >= 0.0


# ===========================================================================
# SECTION 25 — evolve_weights: no runaway amplification (inv 266)
# ===========================================================================


class TestSection25NoRunaway:
    def test_repeated_evolution_bounded(self):
        base = default_weight_vector()
        cfg = WeightEvolutionConfig(
            enabled=True,
            min_samples=5,
            learning_rate=0.50,
            max_adjustment=0.15,
        )
        obs = _make_positive_observations(DimensionName.TREND, 50)
        r1 = evolve_weights(base_weights=base, observations=obs, current_tick=50, config=cfg)
        r2 = evolve_weights(
            base_weights=r1.evolved_weights, observations=obs, current_tick=100, config=cfg
        )

        evo = r2.get(DimensionName.TREND)
        initial_base = 0.25
        assert evo.evolved_weight <= initial_base + 2 * 0.15 + 1e-9

    def test_amplification_stays_reasonable(self):
        base = default_weight_vector()
        cfg = WeightEvolutionConfig(
            enabled=True,
            min_samples=3,
            learning_rate=0.10,
            max_adjustment=0.10,
        )
        obs = _make_positive_observations(DimensionName.TREND, 20)
        current = base
        for step in range(10):
            r = evolve_weights(
                base_weights=current,
                observations=obs,
                current_tick=(step + 1) * 20,
                config=cfg,
            )
            current = r.evolved_weights
        evo = r.get(DimensionName.TREND)
        assert evo.evolved_weight <= 1.0


# ===========================================================================
# SECTION 26 — evolve_weights: sample gate (inv 268)
# ===========================================================================


class TestSection26SampleGate:
    def test_below_min_samples_gated(self):
        obs = _make_positive_observations(DimensionName.TREND, 3)
        result = evolve_weights(
            observations=obs,
            current_tick=5,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.sample_gated is True
        assert evo.evolved_weight == evo.base_weight

    def test_at_min_samples_not_gated(self):
        obs = _make_positive_observations(DimensionName.TREND, 5)
        result = evolve_weights(
            observations=obs,
            current_tick=5,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.sample_gated is False

    def test_above_min_samples_not_gated(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.sample_gated is False


# ===========================================================================
# SECTION 27 — evolve_weights: mixed outcomes → minimal change
# ===========================================================================


class TestSection27MixedOutcomes:
    def test_random_mixed_small_delta(self):
        obs = []
        for i in range(20):
            signal = 1.0 if i % 2 == 0 else -1.0
            obs.append(
                WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=signal,
                    outcome_score=0.5,
                    tick=i,
                )
            )
        result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert abs(evo.delta) < 0.05

    def test_contradictory_signals_near_zero_quality(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.RISK, direction_signal=1.0, outcome_score=1.0, tick=i
            )
            for i in range(10)
        ] + [
            WeightObservation(
                dimension=DimensionName.RISK, direction_signal=-1.0, outcome_score=1.0, tick=i + 10
            )
            for i in range(10)
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=1.0),
        )
        evo = result.get(DimensionName.RISK)
        assert abs(evo.quality_score) < 0.1


# ===========================================================================
# SECTION 28 — evolve_weights: variance damping
# ===========================================================================


class TestSection28VarianceDamping:
    def test_high_variance_damped(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=i
            )
            for i in range(10)
        ] + [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=1.0, tick=i + 10
            )
            for i in range(10)
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(
                enabled=True,
                min_samples=5,
                variance_damping_threshold=0.10,
                decay_rate=1.0,
            ),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.variance_damped is True

    def test_low_variance_not_damped(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(
                enabled=True,
                min_samples=5,
                variance_damping_threshold=0.50,
            ),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.variance_damped is False


# ===========================================================================
# SECTION 29 — evolve_weights: determinism (inv 269)
# ===========================================================================


class TestSection29Determinism:
    def test_identical_inputs_identical_outputs(self):
        obs = _make_positive_observations(DimensionName.TREND, 15)
        cfg = WeightEvolutionConfig(enabled=True, min_samples=5)

        r1 = evolve_weights(observations=obs, current_tick=15, config=cfg)
        r2 = evolve_weights(observations=obs, current_tick=15, config=cfg)

        e1 = r1.get(DimensionName.TREND)
        e2 = r2.get(DimensionName.TREND)
        assert e1.evolved_weight == e2.evolved_weight
        assert e1.quality_score == e2.quality_score

    def test_determinism_100_runs(self):
        obs = _make_positive_observations(DimensionName.STABILITY, 10)
        cfg = WeightEvolutionConfig(enabled=True, min_samples=3)

        weights = set()
        for _ in range(100):
            r = evolve_weights(observations=obs, current_tick=10, config=cfg)
            e = r.get(DimensionName.STABILITY)
            weights.add(e.evolved_weight)
        assert len(weights) == 1


# ===========================================================================
# SECTION 30 — evolve_weights: dimension isolation (inv 273)
# ===========================================================================


class TestSection30DimensionIsolation:
    def test_trend_evolution_independent(self):
        trend_obs = _make_positive_observations(DimensionName.TREND, 10)
        risk_obs = _make_negative_observations(DimensionName.RISK, 10)

        result = evolve_weights(
            observations=trend_obs + risk_obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )

        trend_evo = result.get(DimensionName.TREND)
        risk_evo = result.get(DimensionName.RISK)

        assert trend_evo.evolved_weight > trend_evo.base_weight
        assert risk_evo.evolved_weight < risk_evo.base_weight

    def test_untouched_dimension_unchanged(self):
        trend_obs = _make_positive_observations(DimensionName.TREND, 10)

        result = evolve_weights(
            observations=trend_obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )

        stability_evo = result.get(DimensionName.STABILITY)
        assert stability_evo.sample_gated is True
        assert stability_evo.evolved_weight == stability_evo.base_weight

    def test_four_dimensions_independent(self):
        all_obs = (
            _make_positive_observations(DimensionName.TREND, 10)
            + _make_negative_observations(DimensionName.RISK, 10)
            + _make_positive_observations(DimensionName.STABILITY, 10)
            + _make_negative_observations(DimensionName.URGENCY, 10)
        )

        result = evolve_weights(
            observations=all_obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )

        assert result.get(DimensionName.TREND).evolved_weight > 0.25
        assert result.get(DimensionName.RISK).evolved_weight < 0.25
        assert result.get(DimensionName.STABILITY).evolved_weight > 0.25
        assert result.get(DimensionName.URGENCY).evolved_weight < 0.25


# ===========================================================================
# SECTION 31 — evolve_weights: no mutation (inv 270)
# ===========================================================================


class TestSection31NoMutation:
    def test_observations_not_mutated(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        original = [(o.dimension, o.direction_signal, o.outcome_score, o.tick) for o in obs]
        evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        after = [(o.dimension, o.direction_signal, o.outcome_score, o.tick) for o in obs]
        assert original == after

    def test_base_weights_not_mutated(self):
        base = default_weight_vector()
        original_weights = {k: v.weight for k, v in base.weights.items()}
        evolve_weights(
            base_weights=base,
            observations=_make_positive_observations(DimensionName.TREND, 10),
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        for k, v in base.weights.items():
            assert v.weight == original_weights[k]


# ===========================================================================
# SECTION 32 — evolve_weights: explainability (inv 271)
# ===========================================================================


class TestSection32Explainability:
    def test_result_has_explanation(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        assert result.explanation != ""
        assert "observations" in result.explanation

    def test_dimension_evolution_has_explanation(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert "quality=" in evo.explanation
        assert "delta=" in evo.explanation
        assert "samples=" in evo.explanation

    def test_gated_dimension_explanation(self):
        obs = _make_positive_observations(DimensionName.TREND, 3)
        result = evolve_weights(
            observations=obs,
            current_tick=5,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert "gated" in evo.explanation

    def test_disabled_explanation(self):
        result = evolve_weights(
            config=WeightEvolutionConfig(enabled=False),
        )
        assert "disabled" in result.explanation


# ===========================================================================
# SECTION 33 — evolve_weights: missing base weights (inv 272)
# ===========================================================================


class TestSection33MissingWeights:
    def test_none_base_uses_default(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            base_weights=None,
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.base_weight == 0.25


# ===========================================================================
# SECTION 34 — No circular dependency (inv 270)
# ===========================================================================


class TestSection34NoDependency:
    def test_no_scoring_import(self):
        import inspect
        import umh.runtime.weight_evolution as m

        src = inspect.getsource(m)
        assert "from umh.runtime.strategy_orchestrator" not in src
        assert "from umh.runtime.feedback_selection" not in src
        assert "from umh.runtime.weighted_decision" not in src

    def test_no_subprocess(self):
        import inspect
        import umh.runtime.weight_evolution as m

        src = inspect.getsource(m)
        assert "import subprocess" not in src
        assert "from subprocess" not in src

    def test_imports_only_allowed_modules(self):
        import inspect
        import umh.runtime.weight_evolution as m

        src = inspect.getsource(m)
        allowed = {"dimension_weighting", "regime_aggregation", "adaptive_learning"}
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"


# ===========================================================================
# SECTION 35 — No randomness (inv 269)
# ===========================================================================


class TestSection35NoRandomness:
    def test_no_random_import(self):
        import inspect
        import umh.runtime.weight_evolution as m

        src = inspect.getsource(m)
        assert "import random" not in src
        assert "from random" not in src


# ===========================================================================
# SECTION 36 — No execution methods
# ===========================================================================


class TestSection36NoExecution:
    def test_config_no_execute(self):
        assert not hasattr(WeightEvolutionConfig, "execute")
        assert not hasattr(WeightEvolutionConfig, "run")

    def test_observation_no_execute(self):
        assert not hasattr(WeightObservation, "execute")
        assert not hasattr(WeightObservation, "run")

    def test_evolution_no_execute(self):
        assert not hasattr(DimensionEvolution, "execute")
        assert not hasattr(DimensionEvolution, "run")

    def test_result_no_execute(self):
        assert not hasattr(WeightEvolutionResult, "execute")
        assert not hasattr(WeightEvolutionResult, "run")


# ===========================================================================
# SECTION 37 — Phase 61 regression
# ===========================================================================


class TestSection37Phase61Regression:
    def test_weighted_decision_policy_unchanged(self):
        from umh.runtime.weighted_decision import WeightedDecisionPolicy

        p = WeightedDecisionPolicy()
        assert p.enabled is False
        assert p.max_weight_influence == 0.10
        assert p.min_confidence == 0.60

    def test_orchestrate_selection_unchanged(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
        )
        assert r.selected_strategy == "a"
        assert r.used_weights is False


# ===========================================================================
# SECTION 38 — Phase 60 regression
# ===========================================================================


class TestSection38Phase60Regression:
    def test_dimension_weight_vector_unchanged(self):
        v = default_weight_vector()
        assert v.is_uniform is True
        assert v.normalized is True

    def test_compute_dimension_weights_still_works(self):
        from umh.runtime.dimension_weighting import compute_dimension_weights

        result = compute_dimension_weights([])
        assert result.is_uniform is True


# ===========================================================================
# SECTION 39 — Phase 59 regression
# ===========================================================================


class TestSection39Phase59Regression:
    def test_aggregated_regime_unchanged(self):
        from umh.runtime.regime_aggregation import NEUTRAL_AGGREGATED

        assert NEUTRAL_AGGREGATED.is_neutral is True


# ===========================================================================
# SECTION 40 — Init exports for Phase 62
# ===========================================================================


class TestSection40InitExports:
    def test_weight_evolution_config(self):
        from umh.runtime import WeightEvolutionConfig as C

        assert C is not None

    def test_weight_evolution_result(self):
        from umh.runtime import WeightEvolutionResult as R

        assert R is not None

    def test_weight_observation(self):
        from umh.runtime import WeightObservation as O

        assert O is not None

    def test_dimension_evolution(self):
        from umh.runtime import DimensionEvolution as E

        assert E is not None

    def test_default_config(self):
        from umh.runtime import DEFAULT_EVOLUTION_CONFIG as D

        assert D.enabled is False

    def test_evolve_weights(self):
        from umh.runtime import evolve_weights as f

        assert callable(f)


# ===========================================================================
# SECTION 41 — Roundtrip: to_dict values correct
# ===========================================================================


class TestSection41Roundtrip:
    def test_config_roundtrip(self):
        c = WeightEvolutionConfig(enabled=True, decay_rate=0.95, learning_rate=0.08)
        d = c.to_dict()
        assert d["enabled"] is True
        assert d["decay_rate"] == 0.95
        assert d["learning_rate"] == 0.08

    def test_observation_roundtrip(self):
        obs = WeightObservation(
            dimension=DimensionName.TREND,
            direction_signal=0.7,
            outcome_score=0.85,
            tick=42,
        )
        d = obs.to_dict()
        assert d["dimension"] == "trend"
        assert d["direction_signal"] == 0.7
        assert d["outcome_score"] == 0.85
        assert d["tick"] == 42

    def test_evolution_roundtrip(self):
        e = DimensionEvolution(
            dimension=DimensionName.RISK,
            base_weight=0.25,
            evolved_weight=0.30,
            quality_score=0.6,
            sample_count=15,
        )
        d = e.to_dict()
        assert d["base_weight"] == 0.25
        assert d["evolved_weight"] == 0.30
        assert d["quality_score"] == 0.6
        assert d["sample_count"] == 15
        assert abs(d["delta"] - 0.05) < 1e-4


# ===========================================================================
# SECTION 42 — Edge: zero learning rate
# ===========================================================================


class TestSection42ZeroLearningRate:
    def test_zero_learning_rate_no_change(self):
        obs = _make_positive_observations(DimensionName.TREND, 20)
        result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(enabled=True, min_samples=5, learning_rate=0.0),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.evolved_weight == evo.base_weight


# ===========================================================================
# SECTION 43 — Edge: zero max adjustment
# ===========================================================================


class TestSection43ZeroMaxAdjustment:
    def test_zero_max_adjustment_no_change(self):
        obs = _make_positive_observations(DimensionName.TREND, 20)
        result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(enabled=True, min_samples=5, max_adjustment=0.0),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.evolved_weight == evo.base_weight


# ===========================================================================
# SECTION 44 — Stress: 500 observations
# ===========================================================================


class TestSection44Stress:
    def test_500_observations(self):
        obs = _make_positive_observations(DimensionName.TREND, 500)
        result = evolve_weights(
            observations=obs,
            current_tick=500,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo is not None
        assert evo.evolved_weight > evo.base_weight
        assert evo.sample_count == 500

    def test_all_dimensions_500_each(self):
        obs = []
        for dim in DimensionName:
            obs.extend(_make_positive_observations(dim, 500))

        result = evolve_weights(
            observations=obs,
            current_tick=500,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        assert result.total_observations == 2000
        for dim in DimensionName:
            evo = result.get(dim)
            assert evo.sample_count == 500


# ===========================================================================
# SECTION 45 — Evolved weights are DimensionWeightVector
# ===========================================================================


class TestSection45EvolvedType:
    def test_evolved_is_weight_vector(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        assert isinstance(result.evolved_weights, DimensionWeightVector)

    def test_evolved_has_all_dimensions(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        for dim in DimensionName:
            assert result.evolved_weights.get(dim) is not None

    def test_evolved_source_label(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        trend_w = result.evolved_weights.get(DimensionName.TREND)
        assert trend_w.source == "evolved"


# ===========================================================================
# SECTION 46 — Custom base weights
# ===========================================================================


class TestSection46CustomBase:
    def test_non_uniform_base(self):
        weights = {
            DimensionName.TREND.value: DimensionWeight(
                dimension=DimensionName.TREND, weight=0.40, confidence=0.8, source="learned"
            ),
            DimensionName.RISK.value: DimensionWeight(
                dimension=DimensionName.RISK, weight=0.20, confidence=0.8, source="learned"
            ),
            DimensionName.STABILITY.value: DimensionWeight(
                dimension=DimensionName.STABILITY, weight=0.20, confidence=0.8, source="learned"
            ),
            DimensionName.URGENCY.value: DimensionWeight(
                dimension=DimensionName.URGENCY, weight=0.20, confidence=0.8, source="learned"
            ),
        }
        base = DimensionWeightVector(weights=weights, normalized=True)

        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            base_weights=base,
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )

        evo = result.get(DimensionName.TREND)
        assert evo.base_weight == 0.40
        assert evo.evolved_weight >= evo.base_weight

    def test_custom_base_confidence_preserved(self):
        weights = {
            DimensionName.TREND.value: DimensionWeight(
                dimension=DimensionName.TREND, weight=0.30, confidence=0.9, source="learned"
            ),
            DimensionName.RISK.value: DimensionWeight(
                dimension=DimensionName.RISK, weight=0.30, confidence=0.7, source="learned"
            ),
            DimensionName.STABILITY.value: DimensionWeight(
                dimension=DimensionName.STABILITY, weight=0.20, confidence=0.5
            ),
            DimensionName.URGENCY.value: DimensionWeight(
                dimension=DimensionName.URGENCY, weight=0.20, confidence=0.3
            ),
        }
        base = DimensionWeightVector(weights=weights, normalized=True)

        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            base_weights=base,
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )

        evolved_trend = result.evolved_weights.get(DimensionName.TREND)
        assert evolved_trend.confidence == 0.9


# ===========================================================================
# SECTION 47 — Decay curve verification
# ===========================================================================


class TestSection47DecayCurve:
    def test_exponential_decay_curve(self):
        old_pos = WeightObservation(
            dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=0
        )
        new_neg = WeightObservation(
            dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=1.0, tick=10
        )

        q_low_decay = _compute_decayed_quality([old_pos, new_neg], 10, 0.50)
        q_high_decay = _compute_decayed_quality([old_pos, new_neg], 10, 0.99)

        assert q_low_decay < q_high_decay

    def test_single_observation_decay_invariant(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.8, tick=0
            )
        ]
        q_near = _compute_decayed_quality(obs, 0, 0.90)
        q_far = _compute_decayed_quality(obs, 100, 0.90)
        assert abs(q_near - q_far) < 1e-9

    def test_decay_with_multiple_ticks(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=5
            ),
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=10
            ),
        ]
        q = _compute_decayed_quality(obs, 10, 0.95)
        decay_5 = 0.95**5
        decay_0 = 1.0
        expected = (1.0 * decay_5 + 1.0 * decay_0) / (decay_5 + decay_0)
        assert abs(q - expected) < 1e-9


# ===========================================================================
# SECTION 48 — Sparse data safety (inv 268)
# ===========================================================================


class TestSection48SparseData:
    def test_one_sample_gated(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND,
                direction_signal=1.0,
                outcome_score=1.0,
                tick=0,
            )
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=0,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.sample_gated is True
        assert evo.evolved_weight == 0.25

    def test_dimension_with_zero_samples(self):
        result = evolve_weights(
            observations=[],
            config=WeightEvolutionConfig(enabled=True),
        )
        for dim in DimensionName:
            evo = result.get(dim)
            assert evo.evolved_weight == evo.base_weight


# ===========================================================================
# SECTION 49 — evolve_single_dimension directly
# ===========================================================================


class TestSection49SingleDimension:
    def test_directly(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        cfg = WeightEvolutionConfig(enabled=True, min_samples=5)
        evo = _evolve_single_dimension(
            dimension=DimensionName.TREND,
            base_weight=0.25,
            observations=obs,
            current_tick=10,
            config=cfg,
        )
        assert evo.evolved_weight > 0.25
        assert evo.sample_count == 10

    def test_empty_observations(self):
        cfg = WeightEvolutionConfig(enabled=True, min_samples=5)
        evo = _evolve_single_dimension(
            dimension=DimensionName.TREND,
            base_weight=0.25,
            observations=[],
            current_tick=10,
            config=cfg,
        )
        assert evo.sample_gated is True
        assert evo.evolved_weight == 0.25


# ===========================================================================
# SECTION 50 — Full pipeline: evolve → weighted_decision → orchestrator
# ===========================================================================


class TestSection50FullPipeline:
    def test_evolved_weights_feed_into_orchestrator(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection
        from umh.runtime.weighted_decision import WeightedDecisionPolicy
        from umh.runtime.regime_aggregation import aggregate_regimes

        obs = _make_positive_observations(DimensionName.TREND, 20)
        evo_result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )

        regime = aggregate_regimes(trend_label="trend_up")

        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=regime,
            dimension_weights=evo_result.evolved_weights,
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )

        assert r.used_weights is True
        assert r.selected_strategy == "a"

    def test_disabled_evolution_same_as_default(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection
        from umh.runtime.weighted_decision import WeightedDecisionPolicy
        from umh.runtime.regime_aggregation import aggregate_regimes, NEUTRAL_AGGREGATED

        evo_result = evolve_weights(
            config=WeightEvolutionConfig(enabled=False),
        )

        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            dimension_weights=evo_result.evolved_weights,
        )

        assert r.selected_strategy == "a"
        assert r.used_weights is False


# ===========================================================================
# SECTION 51 — Edge: all zero outcome scores
# ===========================================================================


class TestSection51ZeroOutcomes:
    def test_all_zero_outcomes(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND,
                direction_signal=1.0,
                outcome_score=0.0,
                tick=i,
            )
            for i in range(10)
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.quality_score == 0.0
        assert evo.evolved_weight == evo.base_weight


# ===========================================================================
# SECTION 52 — Edge: all neutral signals
# ===========================================================================


class TestSection52NeutralSignals:
    def test_all_neutral_signals(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND,
                direction_signal=0.0,
                outcome_score=0.8,
                tick=i,
            )
            for i in range(10)
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.quality_score == 0.0
        assert evo.evolved_weight == evo.base_weight


# ===========================================================================
# SECTION 53 — Init regression: all prior exports still present
# ===========================================================================


class TestSection53InitRegression:
    def test_phase61_exports(self):
        from umh.runtime import (
            DEFAULT_WEIGHTED_DECISION_POLICY,
            WeightedDecisionBatchResult,
            WeightedDecisionPolicy,
            WeightedDecisionResult,
            apply_weighted_influence,
            compute_weight_factor,
        )

        assert DEFAULT_WEIGHTED_DECISION_POLICY is not None

    def test_phase60_exports(self):
        from umh.runtime import (
            DEFAULT_WEIGHT_VECTOR,
            DimensionWeight,
            DimensionWeightVector,
            WeightingConfig,
            compute_dimension_weights,
            default_weight_vector,
        )

        assert DEFAULT_WEIGHT_VECTOR is not None

    def test_phase59_exports(self):
        from umh.runtime import (
            AggregatedRegimeState,
            DimensionName,
            DirectionCategory,
            NEUTRAL_AGGREGATED,
            aggregate_regimes,
        )

        assert NEUTRAL_AGGREGATED is not None


# ===========================================================================
# SECTION 54 — Learning rate sensitivity
# ===========================================================================


class TestSection54LearningRate:
    def test_higher_learning_rate_larger_delta(self):
        obs = _make_positive_observations(DimensionName.TREND, 20)
        cfg_low = WeightEvolutionConfig(enabled=True, min_samples=5, learning_rate=0.01)
        cfg_high = WeightEvolutionConfig(enabled=True, min_samples=5, learning_rate=0.10)

        r_low = evolve_weights(observations=obs, current_tick=20, config=cfg_low)
        r_high = evolve_weights(observations=obs, current_tick=20, config=cfg_high)

        evo_low = r_low.get(DimensionName.TREND)
        evo_high = r_high.get(DimensionName.TREND)

        assert abs(evo_high.delta) > abs(evo_low.delta)

    def test_very_small_learning_rate_minimal_change(self):
        obs = _make_positive_observations(DimensionName.TREND, 20)
        cfg = WeightEvolutionConfig(enabled=True, min_samples=5, learning_rate=0.001)
        result = evolve_weights(observations=obs, current_tick=20, config=cfg)
        evo = result.get(DimensionName.TREND)
        assert abs(evo.delta) < 0.01


# ===========================================================================
# SECTION 55 — Max adjustment sensitivity
# ===========================================================================


class TestSection55MaxAdjustment:
    def test_smaller_max_adjustment_tighter_clamp(self):
        obs = _make_positive_observations(DimensionName.TREND, 50)
        cfg_small = WeightEvolutionConfig(
            enabled=True, min_samples=5, learning_rate=0.50, max_adjustment=0.05
        )
        cfg_large = WeightEvolutionConfig(
            enabled=True, min_samples=5, learning_rate=0.50, max_adjustment=0.30
        )

        r_small = evolve_weights(observations=obs, current_tick=50, config=cfg_small)
        r_large = evolve_weights(observations=obs, current_tick=50, config=cfg_large)

        evo_small = r_small.get(DimensionName.TREND)
        evo_large = r_large.get(DimensionName.TREND)

        assert evo_large.evolved_weight >= evo_small.evolved_weight

    def test_max_adjustment_enforced_exactly(self):
        obs = _make_positive_observations(DimensionName.TREND, 100)
        cfg = WeightEvolutionConfig(
            enabled=True, min_samples=5, learning_rate=0.50, max_adjustment=0.10
        )
        result = evolve_weights(observations=obs, current_tick=100, config=cfg)
        evo = result.get(DimensionName.TREND)
        assert evo.evolved_weight <= evo.base_weight + 0.10 + 1e-9


# ===========================================================================
# SECTION 56 — Decay rate sensitivity
# ===========================================================================


class TestSection56DecayRate:
    def test_lower_decay_rate_less_old_influence(self):
        old_pos = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=1.0, tick=i
            )
            for i in range(5)
        ]
        new_neg = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=-1.0, outcome_score=1.0, tick=i + 50
            )
            for i in range(5)
        ]
        mixed = old_pos + new_neg

        cfg_low = WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=0.50)
        cfg_high = WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=0.99)

        r_low = evolve_weights(observations=mixed, current_tick=55, config=cfg_low)
        r_high = evolve_weights(observations=mixed, current_tick=55, config=cfg_high)

        evo_low = r_low.get(DimensionName.TREND)
        evo_high = r_high.get(DimensionName.TREND)
        assert evo_low.quality_score < evo_high.quality_score


# ===========================================================================
# SECTION 57 — Partial signals (fractional direction_signal)
# ===========================================================================


class TestSection57PartialSignals:
    def test_weak_positive_signal(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND,
                direction_signal=0.3,
                outcome_score=0.8,
                tick=i,
            )
            for i in range(10)
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.quality_score > 0.0
        assert evo.quality_score < 1.0

    def test_weak_vs_strong_signal_magnitude(self):
        obs_weak = [
            WeightObservation(
                dimension=DimensionName.RISK, direction_signal=0.2, outcome_score=0.9, tick=i
            )
            for i in range(10)
        ]
        obs_strong = [
            WeightObservation(
                dimension=DimensionName.RISK, direction_signal=1.0, outcome_score=0.9, tick=i
            )
            for i in range(10)
        ]

        cfg = WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=1.0)
        r_weak = evolve_weights(observations=obs_weak, current_tick=10, config=cfg)
        r_strong = evolve_weights(observations=obs_strong, current_tick=10, config=cfg)

        assert r_weak.get(DimensionName.RISK).delta < r_strong.get(DimensionName.RISK).delta


# ===========================================================================
# SECTION 58 — Multiple dimensions with different histories
# ===========================================================================


class TestSection58MultiDimensionHistory:
    def test_different_sample_counts(self):
        obs = _make_positive_observations(DimensionName.TREND, 20) + _make_positive_observations(
            DimensionName.RISK, 3
        )
        result = evolve_weights(
            observations=obs,
            current_tick=20,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        assert result.get(DimensionName.TREND).sample_gated is False
        assert result.get(DimensionName.RISK).sample_gated is True

    def test_opposite_directions(self):
        obs = (
            _make_positive_observations(DimensionName.TREND, 10)
            + _make_negative_observations(DimensionName.TREND, 0)
            + _make_negative_observations(DimensionName.RISK, 10)
        )
        result = evolve_weights(
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        trend_delta = result.get(DimensionName.TREND).delta
        risk_delta = result.get(DimensionName.RISK).delta
        assert trend_delta > 0.0
        assert risk_delta < 0.0


# ===========================================================================
# SECTION 59 — Evolution with custom min_samples
# ===========================================================================


class TestSection59CustomMinSamples:
    def test_min_samples_1(self):
        obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.9, tick=0
            )
        ]
        result = evolve_weights(
            observations=obs,
            current_tick=0,
            config=WeightEvolutionConfig(enabled=True, min_samples=1),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.sample_gated is False
        assert evo.evolved_weight > evo.base_weight

    def test_high_min_samples_gates_small_dataset(self):
        obs = _make_positive_observations(DimensionName.TREND, 15)
        result = evolve_weights(
            observations=obs,
            current_tick=15,
            config=WeightEvolutionConfig(enabled=True, min_samples=20),
        )
        evo = result.get(DimensionName.TREND)
        assert evo.sample_gated is True


# ===========================================================================
# SECTION 60 — Symmetry: positive and negative signals
# ===========================================================================


class TestSection60Symmetry:
    def test_positive_and_negative_symmetric(self):
        pos_obs = _make_positive_observations(DimensionName.TREND, 20)
        neg_obs = _make_negative_observations(DimensionName.TREND, 20)

        cfg = WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=1.0)

        r_pos = evolve_weights(observations=pos_obs, current_tick=20, config=cfg)
        r_neg = evolve_weights(observations=neg_obs, current_tick=20, config=cfg)

        pos_delta = r_pos.get(DimensionName.TREND).delta
        neg_delta = r_neg.get(DimensionName.TREND).delta

        assert abs(pos_delta + neg_delta) < 1e-9

    def test_quality_magnitudes_match(self):
        pos_obs = _make_positive_observations(DimensionName.RISK, 10)
        neg_obs = _make_negative_observations(DimensionName.RISK, 10)

        cfg = WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=1.0)

        r_pos = evolve_weights(observations=pos_obs, current_tick=10, config=cfg)
        r_neg = evolve_weights(observations=neg_obs, current_tick=10, config=cfg)

        assert (
            abs(
                r_pos.get(DimensionName.RISK).quality_score
                + r_neg.get(DimensionName.RISK).quality_score
            )
            < 1e-9
        )


# ===========================================================================
# SECTION 61 — Evolved weights feed into Phase 60 compute_dimension_weights
# ===========================================================================


class TestSection61EvolutionChain:
    def test_evolved_vector_is_valid_input_for_phase60(self):
        obs = _make_positive_observations(DimensionName.TREND, 15)
        evo_result = evolve_weights(
            observations=obs,
            current_tick=15,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        v = evo_result.evolved_weights
        assert isinstance(v, DimensionWeightVector)
        assert v.get(DimensionName.TREND) is not None

    def test_evolved_weights_can_re_evolve(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        cfg = WeightEvolutionConfig(enabled=True, min_samples=5)

        r1 = evolve_weights(observations=obs, current_tick=10, config=cfg)
        r2 = evolve_weights(
            base_weights=r1.evolved_weights, observations=obs, current_tick=20, config=cfg
        )

        assert r2.get(DimensionName.TREND).base_weight == r1.get(DimensionName.TREND).evolved_weight


# ===========================================================================
# SECTION 62 — Phase 58 regression: orchestrator unchanged
# ===========================================================================


class TestSection62Phase58Regression:
    def test_orchestrate_basic(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(
            strategy_ids=["a", "b", "c"],
            base_scores=[0.7, 0.9, 0.5],
        )
        assert r.selected_strategy == "b"

    def test_empty_strategies(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(strategy_ids=[], base_scores=[])
        assert r.selected_strategy == ""


# ===========================================================================
# SECTION 63 — Edge: all dimensions same observations
# ===========================================================================


class TestSection63AllDimensionsSame:
    def test_all_dimensions_same_obs_same_evolution(self):
        obs = []
        for dim in DimensionName:
            obs.extend(
                [
                    WeightObservation(
                        dimension=dim, direction_signal=1.0, outcome_score=0.8, tick=i
                    )
                    for i in range(10)
                ]
            )
        cfg = WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=1.0)
        result = evolve_weights(observations=obs, current_tick=10, config=cfg)
        evolutions = [result.get(dim).evolved_weight for dim in DimensionName]
        assert len(set(evolutions)) == 1

    def test_all_dimensions_same_quality(self):
        obs = []
        for dim in DimensionName:
            obs.extend(
                [
                    WeightObservation(
                        dimension=dim, direction_signal=0.5, outcome_score=0.6, tick=i
                    )
                    for i in range(10)
                ]
            )
        cfg = WeightEvolutionConfig(enabled=True, min_samples=5, decay_rate=1.0)
        result = evolve_weights(observations=obs, current_tick=10, config=cfg)
        qualities = [result.get(dim).quality_score for dim in DimensionName]
        assert len(set(qualities)) == 1


# ===========================================================================
# SECTION 64 — Variance damping factor
# ===========================================================================


class TestSection64VarianceDampingEffect:
    def test_damped_delta_smaller(self):
        consistent_obs = [
            WeightObservation(
                dimension=DimensionName.TREND, direction_signal=1.0, outcome_score=0.8, tick=i
            )
            for i in range(20)
        ]
        mixed_obs = []
        for i in range(20):
            sig = 1.0 if i < 15 else -1.0
            mixed_obs.append(
                WeightObservation(
                    dimension=DimensionName.TREND, direction_signal=sig, outcome_score=0.8, tick=i
                )
            )

        cfg = WeightEvolutionConfig(
            enabled=True, min_samples=5, decay_rate=1.0, variance_damping_threshold=0.01
        )

        r_consistent = evolve_weights(observations=consistent_obs, current_tick=20, config=cfg)
        r_mixed = evolve_weights(observations=mixed_obs, current_tick=20, config=cfg)

        assert r_consistent.get(DimensionName.TREND).variance_damped is False
        assert r_mixed.get(DimensionName.TREND).variance_damped is True


# ===========================================================================
# SECTION 65 — Concurrent evolution and default weight vector
# ===========================================================================


class TestSection65DefaultVector:
    def test_default_vector_still_works(self):
        v = default_weight_vector()
        assert v.is_uniform is True
        assert v.get_weight(DimensionName.TREND) == 0.25

    def test_evolved_from_default_is_valid(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        result = evolve_weights(
            base_weights=default_weight_vector(),
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        assert result.evolved_weights.get(DimensionName.TREND).weight > 0.0

    def test_default_weight_vector_immutable_after_evolution(self):
        dv = DEFAULT_WEIGHT_VECTOR
        obs = _make_positive_observations(DimensionName.TREND, 10)
        evolve_weights(
            base_weights=dv,
            observations=obs,
            current_tick=10,
            config=WeightEvolutionConfig(enabled=True, min_samples=5),
        )
        assert dv.get_weight(DimensionName.TREND) == 0.25


# ===========================================================================
# SECTION 66 — Stability over sequential evolutions
# ===========================================================================


class TestSection66SequentialStability:
    def test_10_sequential_evolutions_stay_bounded(self):
        cfg = WeightEvolutionConfig(
            enabled=True, min_samples=3, learning_rate=0.05, max_adjustment=0.10
        )
        current = default_weight_vector()
        obs = _make_positive_observations(DimensionName.TREND, 10)

        for step in range(10):
            result = evolve_weights(
                base_weights=current,
                observations=obs,
                current_tick=(step + 1) * 10,
                config=cfg,
            )
            current = result.evolved_weights
            evo = result.get(DimensionName.TREND)
            assert evo.evolved_weight <= 1.0
            assert evo.evolved_weight >= 0.0

    def test_convergence_with_consistent_signal(self):
        cfg = WeightEvolutionConfig(
            enabled=True, min_samples=3, learning_rate=0.05, max_adjustment=0.05
        )
        current = default_weight_vector()
        obs = _make_positive_observations(DimensionName.TREND, 10)
        weights = []

        for step in range(30):
            result = evolve_weights(
                base_weights=current,
                observations=obs,
                current_tick=(step + 1) * 10,
                config=cfg,
            )
            current = result.evolved_weights
            weights.append(result.get(DimensionName.TREND).evolved_weight)

        last_5 = weights[-5:]
        assert max(last_5) - min(last_5) < 0.02


# ===========================================================================
# SECTION 67 — Config custom values
# ===========================================================================


class TestSection67ConfigCustom:
    def test_custom_config_applied(self):
        obs = _make_positive_observations(DimensionName.TREND, 10)
        cfg = WeightEvolutionConfig(
            enabled=True,
            decay_rate=0.90,
            learning_rate=0.10,
            min_samples=3,
            max_adjustment=0.20,
            variance_damping_threshold=0.50,
        )
        result = evolve_weights(observations=obs, current_tick=10, config=cfg)
        assert result.config.decay_rate == 0.90
        assert result.config.learning_rate == 0.10
        assert result.config.min_samples == 3
        assert result.config.max_adjustment == 0.20

    def test_config_in_result_dict(self):
        result = evolve_weights(config=WeightEvolutionConfig(enabled=True, decay_rate=0.95))
        d = result.to_dict()
        assert d["config"]["decay_rate"] == 0.95


# ============================= HELPERS ====================================


def _make_positive_observations(dimension: DimensionName, count: int) -> list[WeightObservation]:
    return [
        WeightObservation(
            dimension=dimension,
            direction_signal=1.0,
            outcome_score=0.8,
            tick=i,
        )
        for i in range(count)
    ]


def _make_negative_observations(dimension: DimensionName, count: int) -> list[WeightObservation]:
    return [
        WeightObservation(
            dimension=dimension,
            direction_signal=-1.0,
            outcome_score=0.8,
            tick=i,
        )
        for i in range(count)
    ]
