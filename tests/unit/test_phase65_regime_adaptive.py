"""Phase 65 — Regime-Dependent Adaptive Learning Layer v1 tests.

Tests regime-specific learning rate modulation, factor resolution,
transition smoothing, and composition with Phase 64 adaptive learning.
Covers invariants 294-302.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.adaptive_learning import AdaptiveLearningConfig, compute_adaptive_rate
from umh.runtime.regime import RegimeType
from umh.runtime.regime_adaptive_learning import (
    DEFAULT_REGIME_ADAPTIVE_CONFIG,
    RegimeAdaptiveConfig,
    RegimeAdaptiveResult,
    _resolve_regime_factor,
    _smooth_regime_factor,
    compute_regime_adaptive_rate,
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


def _enabled_adaptive(
    base_rate: float = 0.05,
    min_rate: float = 0.005,
    max_rate: float = 0.20,
    variance_threshold: float = 0.25,
) -> AdaptiveLearningConfig:
    return AdaptiveLearningConfig(
        enabled=True,
        base_rate=base_rate,
        min_rate=min_rate,
        max_rate=max_rate,
        variance_threshold=variance_threshold,
    )


def _enabled_regime(
    stable: float = 0.5,
    trend: float = 1.0,
    spike: float = 1.5,
    min_samples: int = 5,
    max_delta: float = 0.2,
) -> RegimeAdaptiveConfig:
    return RegimeAdaptiveConfig(
        enabled=True,
        regime_factors={
            RegimeType.STABLE.value: stable,
            RegimeType.TREND_UP.value: trend,
            RegimeType.TREND_DOWN.value: trend,
            RegimeType.SPIKE_UP.value: spike,
            RegimeType.SPIKE_DOWN.value: spike,
        },
        min_regime_samples=min_samples,
        max_factor_delta=max_delta,
    )


def _evo_config(
    learning_rate: float = 0.05,
    min_samples: int = 3,
    max_adjustment: float = 0.15,
) -> WeightEvolutionConfig:
    return WeightEvolutionConfig(
        enabled=True,
        learning_rate=learning_rate,
        min_samples=min_samples,
        max_adjustment=max_adjustment,
    )


# ===========================================================================
# SECTION 1 — RegimeAdaptiveConfig defaults
# ===========================================================================


class TestSection01ConfigDefaults:
    def test_disabled_by_default(self):
        cfg = RegimeAdaptiveConfig()
        assert cfg.enabled is False

    def test_default_factors(self):
        cfg = RegimeAdaptiveConfig()
        assert cfg.regime_factors[RegimeType.STABLE.value] == 0.5
        assert cfg.regime_factors[RegimeType.TREND_UP.value] == 1.0
        assert cfg.regime_factors[RegimeType.SPIKE_UP.value] == 1.5

    def test_min_regime_samples_default(self):
        cfg = RegimeAdaptiveConfig()
        assert cfg.min_regime_samples == 5

    def test_max_factor_delta_default(self):
        cfg = RegimeAdaptiveConfig()
        assert cfg.max_factor_delta == 0.2


# ===========================================================================
# SECTION 2 — Config bounds clamping
# ===========================================================================


class TestSection02ConfigBounds:
    def test_factor_clamped_low(self):
        cfg = RegimeAdaptiveConfig(regime_factors={RegimeType.STABLE.value: -1.0})
        assert cfg.regime_factors[RegimeType.STABLE.value] == 0.1

    def test_factor_clamped_high(self):
        cfg = RegimeAdaptiveConfig(regime_factors={RegimeType.SPIKE_UP.value: 100.0})
        assert cfg.regime_factors[RegimeType.SPIKE_UP.value] == 3.0

    def test_min_samples_clamped(self):
        cfg = RegimeAdaptiveConfig(min_regime_samples=0)
        assert cfg.min_regime_samples == 1

    def test_max_delta_clamped_low(self):
        cfg = RegimeAdaptiveConfig(max_factor_delta=0.001)
        assert cfg.max_factor_delta == 0.01

    def test_max_delta_clamped_high(self):
        cfg = RegimeAdaptiveConfig(max_factor_delta=5.0)
        assert cfg.max_factor_delta == 1.0


# ===========================================================================
# SECTION 3 — Config frozen + to_dict
# ===========================================================================


class TestSection03ConfigFrozenDict:
    def test_frozen(self):
        cfg = RegimeAdaptiveConfig()
        try:
            cfg.enabled = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict_keys(self):
        d = RegimeAdaptiveConfig().to_dict()
        assert set(d.keys()) == {
            "enabled",
            "regime_factors",
            "min_regime_samples",
            "max_factor_delta",
        }

    def test_to_dict_values(self):
        d = _enabled_regime().to_dict()
        assert d["enabled"] is True
        assert d["regime_factors"][RegimeType.STABLE.value] == 0.5


# ===========================================================================
# SECTION 4 — RegimeAdaptiveResult defaults
# ===========================================================================


class TestSection04ResultDefaults:
    def test_adaptive_rate_default(self):
        r = RegimeAdaptiveResult()
        assert r.adaptive_rate == 0.05

    def test_regime_factor_default(self):
        r = RegimeAdaptiveResult()
        assert r.regime_factor == 1.0

    def test_smoothed_factor_default(self):
        r = RegimeAdaptiveResult()
        assert r.smoothed_regime_factor == 1.0

    def test_factor_smoothed_default(self):
        r = RegimeAdaptiveResult()
        assert r.factor_smoothed is False


# ===========================================================================
# SECTION 5 — Result frozen + to_dict
# ===========================================================================


class TestSection05ResultFrozenDict:
    def test_frozen(self):
        r = RegimeAdaptiveResult()
        try:
            r.adaptive_rate = 0.1  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict_keys(self):
        d = RegimeAdaptiveResult().to_dict()
        expected = {
            "adaptive_rate",
            "base_rate",
            "confidence_factor",
            "stability_factor",
            "regime_factor",
            "smoothed_regime_factor",
            "variance",
            "confidence_input",
            "regime",
            "regime_sample_count",
            "factor_smoothed",
            "explanation",
        }
        assert set(d.keys()) == expected

    def test_to_dict_all_12(self):
        d = RegimeAdaptiveResult().to_dict()
        assert len(d) == 12


# ===========================================================================
# SECTION 6 — Result bounds clamping
# ===========================================================================


class TestSection06ResultBounds:
    def test_adaptive_rate_clamped(self):
        r = RegimeAdaptiveResult(adaptive_rate=5.0)
        assert r.adaptive_rate == 0.50

    def test_regime_factor_clamped_low(self):
        r = RegimeAdaptiveResult(regime_factor=0.01)
        assert r.regime_factor == 0.1

    def test_regime_factor_clamped_high(self):
        r = RegimeAdaptiveResult(regime_factor=10.0)
        assert r.regime_factor == 3.0

    def test_confidence_clamped(self):
        r = RegimeAdaptiveResult(confidence_factor=2.0)
        assert r.confidence_factor == 1.0


# ===========================================================================
# SECTION 7 — _resolve_regime_factor
# ===========================================================================


class TestSection07ResolveFactor:
    def test_none_regime_returns_one(self):
        f = _resolve_regime_factor(None, 10, 5, _enabled_regime().regime_factors)
        assert f == 1.0

    def test_stable_returns_config_value(self):
        f = _resolve_regime_factor(RegimeType.STABLE, 10, 5, _enabled_regime().regime_factors)
        assert f == 0.5

    def test_trend_sufficient_samples(self):
        f = _resolve_regime_factor(RegimeType.TREND_UP, 10, 5, _enabled_regime().regime_factors)
        assert f == 1.0

    def test_spike_sufficient_samples(self):
        f = _resolve_regime_factor(RegimeType.SPIKE_UP, 10, 5, _enabled_regime().regime_factors)
        assert f == 1.5

    def test_insufficient_samples_returns_one(self):
        f = _resolve_regime_factor(RegimeType.SPIKE_UP, 2, 5, _enabled_regime().regime_factors)
        assert f == 1.0

    def test_exact_min_samples(self):
        f = _resolve_regime_factor(RegimeType.SPIKE_UP, 5, 5, _enabled_regime().regime_factors)
        assert f == 1.5

    def test_stable_always_uses_factor_regardless_of_samples(self):
        f = _resolve_regime_factor(RegimeType.STABLE, 0, 5, _enabled_regime().regime_factors)
        assert f == 0.5


# ===========================================================================
# SECTION 8 — _smooth_regime_factor
# ===========================================================================


class TestSection08SmoothFactor:
    def test_within_delta_no_smoothing(self):
        f, smoothed = _smooth_regime_factor(1.1, 1.0, 0.2)
        assert f == 1.1
        assert smoothed is False

    def test_exceeds_delta_smoothed(self):
        f, smoothed = _smooth_regime_factor(1.5, 1.0, 0.2)
        assert abs(f - 1.2) < 0.001
        assert smoothed is True

    def test_negative_delta_smoothed(self):
        f, smoothed = _smooth_regime_factor(0.5, 1.0, 0.2)
        assert abs(f - 0.8) < 0.001
        assert smoothed is True

    def test_exact_delta_no_smoothing(self):
        f, smoothed = _smooth_regime_factor(1.2, 1.0, 0.2)
        assert f == 1.2
        assert smoothed is False

    def test_large_jump_clamped(self):
        f, smoothed = _smooth_regime_factor(3.0, 1.0, 0.2)
        assert abs(f - 1.2) < 0.001
        assert smoothed is True


# ===========================================================================
# SECTION 9 — Disabled behavior
# ===========================================================================


class TestSection09Disabled:
    def test_disabled_returns_phase64_result(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = RegimeAdaptiveConfig(enabled=False)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r.regime_factor == 1.0
        assert "disabled" in r.explanation

    def test_disabled_same_rate_as_phase64(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        r64 = compute_adaptive_rate(obs, confidence=0.8, config=acfg)
        r65 = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            adaptive_config=acfg,
            regime_config=RegimeAdaptiveConfig(enabled=False),
        )
        assert r65.adaptive_rate == r64.adaptive_rate


# ===========================================================================
# SECTION 10 — No observations
# ===========================================================================


class TestSection10NoObs:
    def test_no_obs_returns_base(self):
        rcfg = _enabled_regime()
        r = compute_regime_adaptive_rate(
            observations=[],
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=rcfg,
        )
        assert r.adaptive_rate == 0.05

    def test_none_obs_returns_base(self):
        r = compute_regime_adaptive_rate(
            observations=None,
            regime_config=_enabled_regime(),
            adaptive_config=_enabled_adaptive(),
        )
        assert r.adaptive_rate == 0.05


# ===========================================================================
# SECTION 11 — Spike → fastest learning
# ===========================================================================


class TestSection11SpikeFastest:
    def test_spike_higher_than_trend(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        r_spike = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_trend = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_spike.adaptive_rate >= r_trend.adaptive_rate

    def test_spike_factor_is_1_5(self):
        obs = _make_obs()
        rcfg = _enabled_regime()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=rcfg,
        )
        assert r.regime_factor == 1.5


# ===========================================================================
# SECTION 12 — Trend → moderate
# ===========================================================================


class TestSection12TrendModerate:
    def test_trend_factor_is_1(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=1.0,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.regime_factor == 1.0

    def test_trend_between_spike_and_stable(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        r_spike = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_trend = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_stable = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.STABLE,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_spike.adaptive_rate >= r_trend.adaptive_rate >= r_stable.adaptive_rate


# ===========================================================================
# SECTION 13 — Stable → slow learning
# ===========================================================================


class TestSection13StableSlow:
    def test_stable_factor_is_0_5(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=1.0,
            regime=RegimeType.STABLE,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.regime_factor == 0.5

    def test_stable_lower_rate(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        r_stable = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.STABLE,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_trend = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_stable.adaptive_rate <= r_trend.adaptive_rate


# ===========================================================================
# SECTION 14 — Low samples → neutral factor (inv 296)
# ===========================================================================


class TestSection14LowSamples:
    def test_insufficient_samples_neutral(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=2,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(min_samples=5),
        )
        assert r.regime_factor == 1.0

    def test_sufficient_samples_uses_factor(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=10,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(min_samples=5),
        )
        assert r.regime_factor == 1.5


# ===========================================================================
# SECTION 15 — Never exceeds max_rate (inv 295)
# ===========================================================================


class TestSection15MaxRateBound:
    def test_spike_clamped_to_max(self):
        obs = _make_obs()
        acfg = _enabled_adaptive(base_rate=0.10, max_rate=0.10)
        rcfg = _enabled_regime(spike=2.0)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r.adaptive_rate <= 0.10

    def test_extreme_factor_still_bounded(self):
        obs = _make_obs()
        acfg = _enabled_adaptive(base_rate=0.5, max_rate=0.20)
        rcfg = _enabled_regime(spike=3.0)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r.adaptive_rate <= 0.20


# ===========================================================================
# SECTION 16 — Regime factor bounded (inv 294)
# ===========================================================================


class TestSection16FactorBounded:
    def test_factor_never_below_min(self):
        r = RegimeAdaptiveResult(regime_factor=0.01)
        assert r.regime_factor >= 0.1

    def test_factor_never_above_max(self):
        r = RegimeAdaptiveResult(regime_factor=10.0)
        assert r.regime_factor <= 3.0


# ===========================================================================
# SECTION 17 — Transition smoothing
# ===========================================================================


class TestSection17Smoothing:
    def test_smooth_large_jump(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            previous_regime_factor=0.5,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(max_delta=0.2),
        )
        assert r.factor_smoothed is True
        assert r.smoothed_regime_factor <= 0.5 + 0.2 + 0.001

    def test_no_smoothing_small_change(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            previous_regime_factor=0.9,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(max_delta=0.2),
        )
        assert r.factor_smoothed is False

    def test_sequential_smoothing_converges(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime(max_delta=0.2)
        prev = 0.5
        for _ in range(20):
            r = compute_regime_adaptive_rate(
                obs,
                confidence=0.8,
                regime=RegimeType.SPIKE_UP,
                regime_sample_count=20,
                previous_regime_factor=prev,
                adaptive_config=acfg,
                regime_config=rcfg,
            )
            prev = r.smoothed_regime_factor
        assert abs(prev - 1.5) < 0.01


# ===========================================================================
# SECTION 18 — Determinism (inv 298)
# ===========================================================================


class TestSection18Determinism:
    def test_100_runs_identical(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        results = [
            compute_regime_adaptive_rate(
                obs,
                confidence=0.7,
                regime=RegimeType.SPIKE_UP,
                regime_sample_count=15,
                adaptive_config=acfg,
                regime_config=rcfg,
            )
            for _ in range(100)
        ]
        rates = [r.adaptive_rate for r in results]
        assert len(set(rates)) == 1


# ===========================================================================
# SECTION 19 — Explainability (inv 299)
# ===========================================================================


class TestSection19Explainability:
    def test_explanation_has_regime_factor(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.7,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert "regime_f=" in r.explanation
        assert "regime=spike_up" in r.explanation

    def test_to_dict_complete(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.7,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        d = r.to_dict()
        assert "regime_factor" in d
        assert "smoothed_regime_factor" in d
        assert "regime" in d


# ===========================================================================
# SECTION 20 — Neutral regime → no modification (inv 300)
# ===========================================================================


class TestSection20NeutralRegime:
    def test_stable_uses_config_factor(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.STABLE,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(stable=0.5),
        )
        assert r.regime_factor == 0.5


# ===========================================================================
# SECTION 21 — Missing regime → default factor (inv 302)
# ===========================================================================


class TestSection21MissingRegime:
    def test_none_regime_factor_one(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=None,
            regime_sample_count=0,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.regime_factor == 1.0


# ===========================================================================
# SECTION 22 — No cross-regime contamination (inv 297)
# ===========================================================================


class TestSection22Isolation:
    def test_spike_up_independent_of_spike_down(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        r_up = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_down = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_DOWN,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_up.adaptive_rate == r_down.adaptive_rate

    def test_trend_independent_of_spike(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime(trend=1.0, spike=2.0)
        r_trend = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_spike = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_trend.regime_factor != r_spike.regime_factor


# ===========================================================================
# SECTION 23 — Composition: adaptive + regime (inv 301)
# ===========================================================================


class TestSection23Composition:
    def test_no_runaway(self):
        obs = _make_obs(count=20, direction=1.0, outcome=1.0)
        acfg = _enabled_adaptive(base_rate=0.5, max_rate=0.20)
        rcfg = _enabled_regime(spike=3.0)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=50,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r.adaptive_rate <= 0.20

    def test_composition_order(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime(spike=1.5)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        expected_raw = (
            acfg.base_rate * r.confidence_factor * r.stability_factor * r.smoothed_regime_factor
        )
        assert abs(r.adaptive_rate - max(acfg.min_rate, min(acfg.max_rate, expected_raw))) < 0.0001


# ===========================================================================
# SECTION 24 — DEFAULT_REGIME_ADAPTIVE_CONFIG
# ===========================================================================


class TestSection24DefaultConfig:
    def test_exists(self):
        assert DEFAULT_REGIME_ADAPTIVE_CONFIG is not None

    def test_disabled(self):
        assert DEFAULT_REGIME_ADAPTIVE_CONFIG.enabled is False

    def test_frozen(self):
        try:
            DEFAULT_REGIME_ADAPTIVE_CONFIG.enabled = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===========================================================================
# SECTION 25 — Dependencies
# ===========================================================================


class TestSection25Dependencies:
    def test_no_import_from_cells(self):
        import umh.runtime.regime_adaptive_learning as mod

        src = open(mod.__file__).read()
        assert "umh.cells" not in src and "umh/cells" not in src

    def test_no_import_from_environments(self):
        import umh.runtime.regime_adaptive_learning as mod

        src = open(mod.__file__).read()
        assert "umh.environments" not in src and "umh/environments" not in src

    def test_imports_only_allowed(self):
        import inspect
        import umh.runtime.regime_adaptive_learning as m

        src = inspect.getsource(m)
        allowed = {"adaptive_learning", "regime", "weight_evolution"}
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"


# ===========================================================================
# SECTION 26 — No randomness
# ===========================================================================


class TestSection26NoRandomness:
    def test_no_random_import(self):
        import inspect
        import umh.runtime.regime_adaptive_learning as m

        src = inspect.getsource(m)
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "import random" not in stripped


# ===========================================================================
# SECTION 27 — No child processes
# ===========================================================================


class TestSection27NoExecution:
    def test_no_child_proc(self):
        import inspect
        import umh.runtime.regime_adaptive_learning as m

        src = inspect.getsource(m)
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""'):
                continue
            if "import" in stripped and "subproc" in stripped:
                assert False, f"unexpected: {stripped}"


# ===========================================================================
# SECTION 28 — Phase 64 regression
# ===========================================================================


class TestSection28Phase64Regression:
    def test_phase64_adaptive_unchanged(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        r = compute_adaptive_rate(obs, confidence=0.8, config=acfg)
        assert r.adaptive_rate > 0


# ===========================================================================
# SECTION 29 — Phase 63 regression
# ===========================================================================


class TestSection29Phase63Regression:
    def test_phase63_still_works(self):
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


# ===========================================================================
# SECTION 30 — Phase 62 regression
# ===========================================================================


class TestSection30Phase62Regression:
    def test_phase62_unchanged(self):
        obs = _make_obs()
        cfg = _evo_config()
        r = evolve_weights(observations=obs, current_tick=20, config=cfg)
        t = r.get(DimensionName.TREND)
        assert t.evolved_weight != t.base_weight


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
    def test_phase65_exports(self):
        from umh.runtime import (
            DEFAULT_REGIME_ADAPTIVE_CONFIG,
            RegimeAdaptiveConfig,
            RegimeAdaptiveResult,
            compute_regime_adaptive_rate,
        )

        assert DEFAULT_REGIME_ADAPTIVE_CONFIG is not None
        assert callable(compute_regime_adaptive_rate)


# ===========================================================================
# SECTION 36 — Roundtrips
# ===========================================================================


class TestSection36Roundtrips:
    def test_config_roundtrip(self):
        cfg = _enabled_regime(stable=0.3, spike=2.0)
        d = cfg.to_dict()
        cfg2 = RegimeAdaptiveConfig(**d)
        assert cfg2.enabled is True
        assert cfg2.regime_factors[RegimeType.STABLE.value] == 0.3

    def test_result_roundtrip(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.7,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        d = r.to_dict()
        assert isinstance(d["regime_factor"], float)


# ===========================================================================
# SECTION 37 — Stress tests
# ===========================================================================


class TestSection37Stress:
    def test_500_observations(self):
        obs = _make_obs(count=500)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=500,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert 0.0 <= r.adaptive_rate <= 0.20

    def test_2000_observations(self):
        obs = _make_obs(count=2000)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=2000,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert 0.0 <= r.adaptive_rate <= 0.20


# ===========================================================================
# SECTION 38 — All regime types
# ===========================================================================


class TestSection38AllRegimeTypes:
    def test_all_five_regimes(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        for rt in RegimeType:
            r = compute_regime_adaptive_rate(
                obs,
                confidence=0.8,
                regime=rt,
                regime_sample_count=20,
                adaptive_config=acfg,
                regime_config=rcfg,
            )
            assert r.adaptive_rate > 0
            assert r.regime == rt

    def test_spike_up_equals_spike_down(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        r_up = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_down = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_DOWN,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_up.regime_factor == r_down.regime_factor


# ===========================================================================
# SECTION 39 — Custom factors
# ===========================================================================


class TestSection39CustomFactors:
    def test_custom_spike_factor(self):
        obs = _make_obs()
        rcfg = _enabled_regime(spike=2.5)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=rcfg,
        )
        assert r.regime_factor == 2.5

    def test_custom_stable_factor(self):
        obs = _make_obs()
        rcfg = _enabled_regime(stable=0.2)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.STABLE,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=rcfg,
        )
        assert r.regime_factor == 0.2


# ===========================================================================
# SECTION 40 — Integration with evolve_weights
# ===========================================================================


class TestSection40EvolveWeightsIntegration:
    def test_regime_factor_changes_delta(self):
        obs = _make_obs(count=10, direction=0.8, outcome=0.9)
        cfg = _evo_config()
        acfg = _enabled_adaptive()
        dim_conf = {DimensionName.TREND.value: 0.8}
        r1 = evolve_weights(
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
            regime_factor=1.0,
        )
        r2 = evolve_weights(
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
            regime_factor=2.0,
        )
        d1 = abs(r1.get(DimensionName.TREND).delta)
        d2 = abs(r2.get(DimensionName.TREND).delta)
        assert d2 > d1

    def test_regime_factor_one_unchanged(self):
        obs = _make_obs(count=10)
        cfg = _evo_config()
        acfg = _enabled_adaptive()
        dim_conf = {DimensionName.TREND.value: 0.8}
        r1 = evolve_weights(
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
        )
        r2 = evolve_weights(
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
            regime_factor=1.0,
        )
        t1 = r1.get(DimensionName.TREND)
        t2 = r2.get(DimensionName.TREND)
        assert t1.evolved_weight == t2.evolved_weight


# ===========================================================================
# SECTION 41 — Integration with regime_weight_evolution
# ===========================================================================


class TestSection41RegimeEvoIntegration:
    def test_regime_adaptive_passes_through(self):
        from umh.runtime.regime_weight_evolution import (
            RegimeObservation,
            RegimeWeightEvolutionConfig,
            evolve_regime_weights,
        )

        inner_cfg = _evo_config(min_samples=3)
        rwcfg = RegimeWeightEvolutionConfig(enabled=True, evolution_config=inner_cfg)
        acfg = _enabled_adaptive()
        racfg = _enabled_regime()
        obs = [
            RegimeObservation(
                observation=WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=0.8,
                    outcome_score=0.9,
                    tick=i + 1,
                ),
                regime=RegimeType.SPIKE_UP,
            )
            for i in range(20)
        ]
        r = evolve_regime_weights(
            observations=obs,
            current_tick=30,
            active_regime=RegimeType.SPIKE_UP,
            config=rwcfg,
            adaptive_config=acfg,
            dimension_confidences={DimensionName.TREND.value: 0.9},
            regime_adaptive_config=racfg,
        )
        assert r.total_observations == 20


# ===========================================================================
# SECTION 42 — No mutation (inv 298)
# ===========================================================================


class TestSection42NoMutation:
    def test_observations_unchanged(self):
        obs = _make_obs()
        original = [(o.direction_signal, o.outcome_score, o.tick) for o in obs]
        compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        after = [(o.direction_signal, o.outcome_score, o.tick) for o in obs]
        assert original == after


# ===========================================================================
# SECTION 43 — Symmetry
# ===========================================================================


class TestSection43Symmetry:
    def test_trend_up_equals_trend_down(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        r_up = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_down = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_DOWN,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_up.adaptive_rate == r_down.adaptive_rate


# ===========================================================================
# SECTION 44 — Variance interaction
# ===========================================================================


class TestSection44VarianceInteraction:
    def test_high_variance_dampens_even_with_spike(self):
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
        r = compute_regime_adaptive_rate(
            noisy,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.stability_factor < 0.5
        assert r.adaptive_rate < 0.10


# ===========================================================================
# SECTION 45 — Confidence interaction
# ===========================================================================


class TestSection45ConfidenceInteraction:
    def test_zero_confidence_overrides_spike(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.adaptive_rate <= 0.005


# ===========================================================================
# SECTION 46 — Full pipeline
# ===========================================================================


class TestSection46FullPipeline:
    def test_end_to_end(self):
        from umh.runtime.dimension_weighting import default_weight_vector

        base = default_weight_vector()
        obs = []
        for dim in DimensionName:
            obs.extend(_make_obs(dim=dim, count=10, direction=0.7, outcome=0.8))
        cfg = _evo_config()
        acfg = _enabled_adaptive()
        dim_conf = {d.value: 0.8 for d in DimensionName}
        r = evolve_weights(
            base_weights=base,
            observations=obs,
            current_tick=20,
            config=cfg,
            adaptive_config=acfg,
            dimension_confidences=dim_conf,
            regime_factor=1.5,
        )
        for dim in DimensionName:
            evo = r.get(dim)
            assert 0.0 <= evo.evolved_weight <= 1.0


# ===========================================================================
# SECTION 47 — No oscillation under regime switching
# ===========================================================================


class TestSection47NoOscillation:
    def test_alternating_regimes_stable(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime(max_delta=0.2)
        prev_factor = 1.0
        factors = []
        regimes = [
            RegimeType.SPIKE_UP,
            RegimeType.STABLE,
            RegimeType.SPIKE_UP,
            RegimeType.STABLE,
            RegimeType.SPIKE_UP,
        ]
        for rt in regimes:
            r = compute_regime_adaptive_rate(
                obs,
                confidence=0.8,
                regime=rt,
                regime_sample_count=20,
                previous_regime_factor=prev_factor,
                adaptive_config=acfg,
                regime_config=rcfg,
            )
            factors.append(r.smoothed_regime_factor)
            prev_factor = r.smoothed_regime_factor
        for i in range(1, len(factors)):
            assert abs(factors[i] - factors[i - 1]) <= 0.2 + 0.001


# ===========================================================================
# SECTION 48 — Regime sample count in result
# ===========================================================================


class TestSection48SampleCount:
    def test_sample_count_preserved(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=42,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.regime_sample_count == 42


# ===========================================================================
# SECTION 49 — Zero base rate
# ===========================================================================


class TestSection49ZeroBase:
    def test_zero_base_min_applies(self):
        obs = _make_obs()
        acfg = _enabled_adaptive(base_rate=0.0, min_rate=0.005)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=_enabled_regime(),
        )
        assert r.adaptive_rate == 0.005


# ===========================================================================
# SECTION 50 — Partial factor map
# ===========================================================================


class TestSection50PartialMap:
    def test_missing_regime_defaults_to_one(self):
        rcfg = RegimeAdaptiveConfig(
            enabled=True,
            regime_factors={RegimeType.STABLE.value: 0.5},
            min_regime_samples=3,
        )
        f = _resolve_regime_factor(
            RegimeType.SPIKE_UP,
            20,
            3,
            rcfg.regime_factors,
        )
        assert f == 1.0


# ===========================================================================
# SECTION 51 — Sequential evolution with regime factor
# ===========================================================================


class TestSection51Sequential:
    def test_sequential_steps_bounded(self):
        cfg = _evo_config(max_adjustment=0.15)
        acfg = _enabled_adaptive()
        weight = 0.25
        for step in range(5):
            obs = _make_obs(count=10, direction=0.8, outcome=0.9, start_tick=step * 10)
            r = _evolve_single_dimension(
                DimensionName.TREND,
                weight,
                obs,
                (step + 1) * 10,
                cfg,
                adaptive_config=acfg,
                confidence=0.8,
                regime_factor=1.5,
            )
            weight = r.evolved_weight
            assert 0.0 <= weight <= 1.0


# ===========================================================================
# SECTION 52 — Confidence spectrum with regime
# ===========================================================================


class TestSection52ConfidenceSpectrum:
    def test_monotonic_with_spike(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        rates = []
        for conf in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            r = compute_regime_adaptive_rate(
                obs,
                confidence=conf,
                regime=RegimeType.SPIKE_UP,
                regime_sample_count=20,
                adaptive_config=acfg,
                regime_config=rcfg,
            )
            rates.append(r.adaptive_rate)
        for i in range(1, len(rates)):
            assert rates[i] >= rates[i - 1]


# ===========================================================================
# SECTION 53 — Regime ordering test
# ===========================================================================


class TestSection53RegimeOrdering:
    def test_ordering_spike_trend_stable(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime()
        r_spike = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_trend = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_stable = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.STABLE,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_spike.regime_factor > r_trend.regime_factor > r_stable.regime_factor


# ===========================================================================
# SECTION 54 — Edge: all factors minimum
# ===========================================================================


class TestSection54MinFactors:
    def test_all_min(self):
        obs = _make_obs()
        acfg = _enabled_adaptive(base_rate=0.01, min_rate=0.001, max_rate=0.01)
        rcfg = _enabled_regime(stable=0.1, trend=0.1, spike=0.1)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.1,
            regime=RegimeType.STABLE,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r.adaptive_rate >= 0.001


# ===========================================================================
# SECTION 55 — Edge: regime_factor exactly 1.0
# ===========================================================================


class TestSection55FactorOne:
    def test_factor_one_no_change(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = _enabled_regime(trend=1.0)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_base = compute_adaptive_rate(obs, confidence=0.8, config=acfg, regime_factor=1.0)
        assert r.adaptive_rate == r_base.adaptive_rate


# ===========================================================================
# SECTION 56 — Phase 64 compute_adaptive_rate regime_factor param
# ===========================================================================


class TestSection56Phase64RegimeFactor:
    def test_regime_factor_in_adaptive_rate(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        r1 = compute_adaptive_rate(obs, confidence=0.8, config=acfg, regime_factor=1.0)
        r2 = compute_adaptive_rate(obs, confidence=0.8, config=acfg, regime_factor=2.0)
        assert r2.adaptive_rate >= r1.adaptive_rate

    def test_regime_factor_in_result(self):
        obs = _make_obs()
        r = compute_adaptive_rate(
            obs, confidence=0.8, config=_enabled_adaptive(), regime_factor=1.5
        )
        assert r.regime_factor == 1.5


# ===========================================================================
# SECTION 57 — Multi-regime factor comparison
# ===========================================================================


class TestSection57MultiRegimeFactors:
    def test_custom_asymmetric_factors(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        rcfg = RegimeAdaptiveConfig(
            enabled=True,
            regime_factors={
                RegimeType.STABLE.value: 0.3,
                RegimeType.TREND_UP.value: 0.8,
                RegimeType.TREND_DOWN.value: 1.2,
                RegimeType.SPIKE_UP.value: 2.0,
                RegimeType.SPIKE_DOWN.value: 1.0,
            },
            min_regime_samples=3,
        )
        r_up = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        r_down = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_DOWN,
            regime_sample_count=20,
            adaptive_config=acfg,
            regime_config=rcfg,
        )
        assert r_up.regime_factor != r_down.regime_factor


# ===========================================================================
# SECTION 58 — Smoothing convergence speed
# ===========================================================================


class TestSection58SmoothingSpeed:
    def test_larger_delta_converges_faster(self):
        obs = _make_obs()
        acfg = _enabled_adaptive()
        prev_slow = 0.5
        prev_fast = 0.5
        for _ in range(5):
            r_slow = compute_regime_adaptive_rate(
                obs,
                confidence=0.8,
                regime=RegimeType.SPIKE_UP,
                regime_sample_count=20,
                previous_regime_factor=prev_slow,
                adaptive_config=acfg,
                regime_config=_enabled_regime(max_delta=0.1),
            )
            r_fast = compute_regime_adaptive_rate(
                obs,
                confidence=0.8,
                regime=RegimeType.SPIKE_UP,
                regime_sample_count=20,
                previous_regime_factor=prev_fast,
                adaptive_config=acfg,
                regime_config=_enabled_regime(max_delta=0.5),
            )
            prev_slow = r_slow.smoothed_regime_factor
            prev_fast = r_fast.smoothed_regime_factor
        assert abs(prev_fast - 1.5) < abs(prev_slow - 1.5)


# ===========================================================================
# SECTION 59 — Init regression
# ===========================================================================


class TestSection59InitRegression:
    def test_phase65_exports(self):
        from umh.runtime import (
            DEFAULT_REGIME_ADAPTIVE_CONFIG,
            RegimeAdaptiveConfig,
            RegimeAdaptiveResult,
            compute_regime_adaptive_rate,
        )

        assert DEFAULT_REGIME_ADAPTIVE_CONFIG is not None

    def test_phase64_exports_still_work(self):
        from umh.runtime import (
            DEFAULT_ADAPTIVE_LEARNING_CONFIG,
            AdaptiveLearningConfig,
            compute_adaptive_rate,
        )

        assert DEFAULT_ADAPTIVE_LEARNING_CONFIG is not None

    def test_phase63_exports_still_work(self):
        from umh.runtime import (
            DEFAULT_REGIME_EVOLUTION_CONFIG,
            evolve_regime_weights,
        )

        assert DEFAULT_REGIME_EVOLUTION_CONFIG is not None


# ===========================================================================
# SECTION 60 — Negative direction signals
# ===========================================================================


class TestSection60NegativeSignals:
    def test_negative_signals_work(self):
        obs = _make_obs(direction=-0.8, outcome=0.9)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.adaptive_rate > 0


# ===========================================================================
# SECTION 61 — Factor smoothing edge cases
# ===========================================================================


class TestSection61SmoothingEdges:
    def test_same_factor_no_smoothing(self):
        f, smoothed = _smooth_regime_factor(1.0, 1.0, 0.2)
        assert f == 1.0
        assert smoothed is False

    def test_very_small_delta_no_smoothing(self):
        f, smoothed = _smooth_regime_factor(1.001, 1.0, 0.2)
        assert abs(f - 1.001) < 0.0001
        assert smoothed is False


# ===========================================================================
# SECTION 62 — Disabled with regime context
# ===========================================================================


class TestSection62DisabledWithRegime:
    def test_disabled_ignores_regime(self):
        obs = _make_obs()
        rcfg = RegimeAdaptiveConfig(enabled=False)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=100,
            adaptive_config=_enabled_adaptive(),
            regime_config=rcfg,
        )
        assert r.regime_factor == 1.0


# ===========================================================================
# SECTION 63 — Compound: regime_evo + adaptive + regime_adaptive
# ===========================================================================


class TestSection63CompoundIntegration:
    def test_all_three_layers(self):
        from umh.runtime.regime_weight_evolution import (
            RegimeObservation,
            RegimeWeightEvolutionConfig,
            evolve_regime_weights,
        )
        from umh.runtime.dimension_weighting import default_weight_vector

        inner_cfg = _evo_config(min_samples=3)
        rwcfg = RegimeWeightEvolutionConfig(
            enabled=True,
            evolution_config=inner_cfg,
            max_step_change=0.05,
        )
        acfg = _enabled_adaptive()
        racfg = _enabled_regime()
        obs = [
            RegimeObservation(
                observation=WeightObservation(
                    dimension=DimensionName.TREND,
                    direction_signal=0.9,
                    outcome_score=1.0,
                    tick=i + 1,
                ),
                regime=RegimeType.SPIKE_UP,
            )
            for i in range(20)
        ]
        r = evolve_regime_weights(
            observations=obs,
            current_tick=30,
            active_regime=RegimeType.SPIKE_UP,
            previous_weights=default_weight_vector(),
            config=rwcfg,
            adaptive_config=acfg,
            dimension_confidences={DimensionName.TREND.value: 0.9},
            regime_adaptive_config=racfg,
        )
        t = r.get(DimensionName.TREND)
        assert t is not None
        assert 0.0 <= t.final_weight <= 1.0


# ===========================================================================
# SECTION 64 — Variance threshold sensitivity
# ===========================================================================


class TestSection64VarianceThreshold:
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
        r1 = compute_regime_adaptive_rate(
            noisy,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(variance_threshold=0.05),
            regime_config=_enabled_regime(),
        )
        r2 = compute_regime_adaptive_rate(
            noisy,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(variance_threshold=0.50),
            regime_config=_enabled_regime(),
        )
        assert r1.stability_factor < r2.stability_factor


# ===========================================================================
# SECTION 65 — Single observation
# ===========================================================================


class TestSection65SingleObs:
    def test_single_obs_zero_variance(self):
        obs = _make_obs(count=1)
        r = compute_regime_adaptive_rate(
            obs,
            confidence=1.0,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.variance == 0.0
        assert r.stability_factor == 1.0


# ===========================================================================
# SECTION 66 — Factor persists in result
# ===========================================================================


class TestSection66FactorInResult:
    def test_raw_and_smoothed_both_present(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.8,
            regime=RegimeType.SPIKE_UP,
            regime_sample_count=20,
            previous_regime_factor=0.5,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(max_delta=0.1),
        )
        assert r.regime_factor == 1.5
        assert r.smoothed_regime_factor < 1.5
        assert r.factor_smoothed is True


# ===========================================================================
# SECTION 67 — No amplification with 10-step test
# ===========================================================================


class TestSection67NoRunaway:
    def test_10_step_bounded(self):
        cfg = _evo_config(max_adjustment=0.15)
        acfg = _enabled_adaptive(max_rate=0.20)
        weight = 0.25
        prev_w = weight
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
                regime_factor=1.5,
            )
            weight = r.evolved_weight
            assert 0.0 <= weight <= 1.0
            assert weight <= prev_w + cfg.max_adjustment + 0.001
            prev_w = weight


# ===========================================================================
# SECTION 68 — Confidence input preserved
# ===========================================================================


class TestSection68ConfidenceInput:
    def test_confidence_in_result(self):
        obs = _make_obs()
        r = compute_regime_adaptive_rate(
            obs,
            confidence=0.73,
            regime=RegimeType.TREND_UP,
            regime_sample_count=20,
            adaptive_config=_enabled_adaptive(),
            regime_config=_enabled_regime(),
        )
        assert r.confidence_input == 0.73
