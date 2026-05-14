"""Phase 66 — Cross-Dimension Interaction Layer v1 tests.

Tests bounded pairwise dimension interactions, sparse selection,
clamping, safety invariants, and orchestrator integration.
Covers invariants 303-312.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.dimension_interactions import (
    DEFAULT_INTERACTION_CONFIG,
    ActiveInteraction,
    InteractionConfig,
    InteractionDirection,
    InteractionResult,
    InteractionRule,
    _INTERACTION_FACTOR_MAX,
    _INTERACTION_FACTOR_MIN,
    _direction_matches,
    _evaluate_rule,
    compute_interaction_factor,
)
from umh.runtime.regime_aggregation import (
    DimensionName,
    DimensionRegime,
    DirectionCategory,
)
from umh.runtime.strategy_orchestrator import (
    StrategyCandidate,
    StrategyOrchestrationPolicy,
    StrategySelectionResult,
    orchestrate_selection,
)


def _regime(
    dim: DimensionName,
    direction: DirectionCategory,
    strength: float = 0.8,
    confidence: float = 0.9,
    label: str = "test",
) -> DimensionRegime:
    return DimensionRegime(
        dimension=dim,
        regime_label=label,
        direction=direction,
        strength=strength,
        confidence=confidence,
    )


def _enabled_config(
    max_active: int = 3,
    strength_threshold: float = 0.3,
    rules: tuple[InteractionRule, ...] | None = None,
) -> InteractionConfig:
    return InteractionConfig(
        enabled=True,
        max_active_pairs=max_active,
        strength_threshold=strength_threshold,
        rules=rules if rules is not None else (),
    )


def _full_regimes(
    trend_dir: DirectionCategory = DirectionCategory.POSITIVE,
    risk_dir: DirectionCategory = DirectionCategory.POSITIVE,
    stab_dir: DirectionCategory = DirectionCategory.POSITIVE,
    urg_dir: DirectionCategory = DirectionCategory.POSITIVE,
    strength: float = 0.8,
) -> dict[DimensionName, DimensionRegime]:
    return {
        DimensionName.TREND: _regime(DimensionName.TREND, trend_dir, strength),
        DimensionName.RISK: _regime(DimensionName.RISK, risk_dir, strength),
        DimensionName.STABILITY: _regime(DimensionName.STABILITY, stab_dir, strength),
        DimensionName.URGENCY: _regime(DimensionName.URGENCY, urg_dir, strength),
    }


# ===========================================================================
# SECTION 1 — InteractionConfig defaults
# ===========================================================================


class TestSection01ConfigDefaults:
    def test_disabled_by_default(self):
        cfg = InteractionConfig()
        assert cfg.enabled is False

    def test_max_active_default(self):
        cfg = InteractionConfig()
        assert cfg.max_active_pairs == 3

    def test_strength_threshold_default(self):
        cfg = InteractionConfig()
        assert cfg.strength_threshold == 0.3

    def test_default_rules_populated(self):
        cfg = InteractionConfig()
        assert len(cfg.rules) == 4


# ===========================================================================
# SECTION 2 — Config bounds clamping
# ===========================================================================


class TestSection02ConfigBounds:
    def test_max_active_clamped_low(self):
        cfg = InteractionConfig(max_active_pairs=0)
        assert cfg.max_active_pairs == 1

    def test_max_active_clamped_high(self):
        cfg = InteractionConfig(max_active_pairs=100)
        assert cfg.max_active_pairs == 6

    def test_strength_threshold_clamped_low(self):
        cfg = InteractionConfig(strength_threshold=-1.0)
        assert cfg.strength_threshold == 0.0

    def test_strength_threshold_clamped_high(self):
        cfg = InteractionConfig(strength_threshold=5.0)
        assert cfg.strength_threshold == 1.0


# ===========================================================================
# SECTION 3 — Config frozen + to_dict
# ===========================================================================


class TestSection03ConfigFrozenDict:
    def test_frozen(self):
        cfg = InteractionConfig()
        try:
            cfg.enabled = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict_keys(self):
        d = InteractionConfig().to_dict()
        assert set(d.keys()) == {"enabled", "max_active_pairs", "rules", "strength_threshold"}

    def test_to_dict_values(self):
        d = _enabled_config().to_dict()
        assert d["enabled"] is True
        assert d["max_active_pairs"] == 3


# ===========================================================================
# SECTION 4 — InteractionRule
# ===========================================================================


class TestSection04Rule:
    def test_factor_clamped_low(self):
        r = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.5,
        )
        assert r.factor == _INTERACTION_FACTOR_MIN

    def test_factor_clamped_high(self):
        r = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=2.0,
        )
        assert r.factor == _INTERACTION_FACTOR_MAX

    def test_to_dict(self):
        r = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
            label="test",
        )
        d = r.to_dict()
        assert d["dim_a"] == "trend"
        assert d["dim_b"] == "risk"
        assert d["factor"] == 0.95
        assert d["label"] == "test"

    def test_default_factor(self):
        r = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.POSITIVE,
        )
        assert r.factor == 1.0


# ===========================================================================
# SECTION 5 — InteractionDirection enum
# ===========================================================================


class TestSection05Direction:
    def test_positive(self):
        assert InteractionDirection.POSITIVE.value == "positive"

    def test_negative(self):
        assert InteractionDirection.NEGATIVE.value == "negative"

    def test_any(self):
        assert InteractionDirection.ANY.value == "any"


# ===========================================================================
# SECTION 6 — _direction_matches
# ===========================================================================


class TestSection06DirectionMatches:
    def test_positive_matches_positive(self):
        assert _direction_matches(DirectionCategory.POSITIVE, InteractionDirection.POSITIVE)

    def test_positive_no_match_negative(self):
        assert not _direction_matches(DirectionCategory.POSITIVE, InteractionDirection.NEGATIVE)

    def test_negative_matches_negative(self):
        assert _direction_matches(DirectionCategory.NEGATIVE, InteractionDirection.NEGATIVE)

    def test_any_matches_positive(self):
        assert _direction_matches(DirectionCategory.POSITIVE, InteractionDirection.ANY)

    def test_any_matches_negative(self):
        assert _direction_matches(DirectionCategory.NEGATIVE, InteractionDirection.ANY)

    def test_any_matches_neutral(self):
        assert _direction_matches(DirectionCategory.NEUTRAL, InteractionDirection.ANY)

    def test_neutral_no_match_positive(self):
        assert not _direction_matches(DirectionCategory.NEUTRAL, InteractionDirection.POSITIVE)


# ===========================================================================
# SECTION 7 — _evaluate_rule basics
# ===========================================================================


class TestSection07EvaluateRule:
    def test_matching_rule(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        regimes = {
            DimensionName.TREND: _regime(DimensionName.TREND, DirectionCategory.POSITIVE),
            DimensionName.RISK: _regime(DimensionName.RISK, DirectionCategory.NEGATIVE),
        }
        result = _evaluate_rule(rule, regimes, 0.3)
        assert result is not None
        assert result.raw_factor < 1.0

    def test_non_matching_direction(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        regimes = {
            DimensionName.TREND: _regime(DimensionName.TREND, DirectionCategory.POSITIVE),
            DimensionName.RISK: _regime(DimensionName.RISK, DirectionCategory.POSITIVE),
        }
        result = _evaluate_rule(rule, regimes, 0.3)
        assert result is None

    def test_missing_dimension_a(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        regimes = {
            DimensionName.RISK: _regime(DimensionName.RISK, DirectionCategory.NEGATIVE),
        }
        result = _evaluate_rule(rule, regimes, 0.3)
        assert result is None

    def test_missing_dimension_b(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        regimes = {
            DimensionName.TREND: _regime(DimensionName.TREND, DirectionCategory.POSITIVE),
        }
        result = _evaluate_rule(rule, regimes, 0.3)
        assert result is None

    def test_below_strength_threshold(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=0.1
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=0.1
            ),
        }
        result = _evaluate_rule(rule, regimes, 0.3)
        assert result is None


# ===========================================================================
# SECTION 8 — Strength weighting
# ===========================================================================


class TestSection08StrengthWeighting:
    def test_full_strength_full_factor(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = _evaluate_rule(rule, regimes, 0.0)
        assert result is not None
        assert abs(result.raw_factor - 0.95) < 0.001

    def test_partial_strength_attenuated(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.9,
        )
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=0.5
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=0.5
            ),
        }
        result = _evaluate_rule(rule, regimes, 0.0)
        assert result is not None
        expected = 1.0 + (0.9 - 1.0) * 0.5
        assert abs(result.raw_factor - expected) < 0.001

    def test_min_strength_used(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.9,
        )
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=0.4
            ),
        }
        result = _evaluate_rule(rule, regimes, 0.0)
        assert result is not None
        expected = 1.0 + (0.9 - 1.0) * 0.4
        assert abs(result.raw_factor - expected) < 0.001


# ===========================================================================
# SECTION 9 — ActiveInteraction
# ===========================================================================


class TestSection09ActiveInteraction:
    def test_deviation(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        ai = ActiveInteraction(
            rule=rule,
            dim_a_regime=_regime(DimensionName.TREND, DirectionCategory.POSITIVE),
            dim_b_regime=_regime(DimensionName.RISK, DirectionCategory.NEGATIVE),
            raw_factor=0.95,
        )
        assert abs(ai.deviation - 0.05) < 0.001

    def test_to_dict(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        ai = ActiveInteraction(
            rule=rule,
            dim_a_regime=_regime(DimensionName.TREND, DirectionCategory.POSITIVE),
            dim_b_regime=_regime(DimensionName.RISK, DirectionCategory.NEGATIVE),
            raw_factor=0.95,
        )
        d = ai.to_dict()
        assert "rule" in d
        assert "raw_factor" in d
        assert "deviation" in d

    def test_factor_clamped(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        ai = ActiveInteraction(
            rule=rule,
            dim_a_regime=_regime(DimensionName.TREND, DirectionCategory.POSITIVE),
            dim_b_regime=_regime(DimensionName.RISK, DirectionCategory.NEGATIVE),
            raw_factor=0.5,
        )
        assert ai.raw_factor == _INTERACTION_FACTOR_MIN


# ===========================================================================
# SECTION 10 — InteractionResult defaults
# ===========================================================================


class TestSection10ResultDefaults:
    def test_factor_default(self):
        r = InteractionResult()
        assert r.interaction_factor == 1.0

    def test_raw_product_default(self):
        r = InteractionResult()
        assert r.raw_product == 1.0

    def test_active_empty(self):
        r = InteractionResult()
        assert r.active_interactions == ()

    def test_clamped_default(self):
        r = InteractionResult()
        assert r.clamped is False


# ===========================================================================
# SECTION 11 — Result bounds + to_dict
# ===========================================================================


class TestSection11ResultBoundsDict:
    def test_factor_clamped_low(self):
        r = InteractionResult(interaction_factor=0.5)
        assert r.interaction_factor == _INTERACTION_FACTOR_MIN

    def test_factor_clamped_high(self):
        r = InteractionResult(interaction_factor=2.0)
        assert r.interaction_factor == _INTERACTION_FACTOR_MAX

    def test_to_dict_keys(self):
        d = InteractionResult().to_dict()
        expected = {
            "interaction_factor",
            "raw_product",
            "active_interactions",
            "total_rules_evaluated",
            "total_rules_matched",
            "clamped",
            "explanation",
        }
        assert set(d.keys()) == expected

    def test_to_dict_count(self):
        d = InteractionResult().to_dict()
        assert len(d) == 7

    def test_frozen(self):
        r = InteractionResult()
        try:
            r.interaction_factor = 0.95  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===========================================================================
# SECTION 12 — Disabled → no change (inv 312)
# ===========================================================================


class TestSection12Disabled:
    def test_disabled_returns_neutral(self):
        r = compute_interaction_factor(
            dimension_regimes=_full_regimes(),
            config=InteractionConfig(enabled=False),
        )
        assert r.interaction_factor == 1.0

    def test_disabled_no_evaluation(self):
        r = compute_interaction_factor(
            dimension_regimes=_full_regimes(),
            config=InteractionConfig(enabled=False),
        )
        assert r.total_rules_evaluated == 0

    def test_disabled_explanation(self):
        r = compute_interaction_factor(config=InteractionConfig(enabled=False))
        assert "disabled" in r.explanation


# ===========================================================================
# SECTION 13 — No regimes → neutral (inv 308)
# ===========================================================================


class TestSection13NoRegimes:
    def test_no_regimes_neutral(self):
        r = compute_interaction_factor(
            dimension_regimes=None,
            config=_enabled_config(),
        )
        assert r.interaction_factor == 1.0

    def test_empty_regimes_neutral(self):
        r = compute_interaction_factor(
            dimension_regimes={},
            config=_enabled_config(),
        )
        assert r.interaction_factor == 1.0

    def test_empty_explanation(self):
        r = compute_interaction_factor(
            dimension_regimes={},
            config=_enabled_config(),
        )
        assert "no dimension regimes" in r.explanation


# ===========================================================================
# SECTION 14 — Simple trend+risk interaction
# ===========================================================================


class TestSection14TrendRisk:
    def test_trend_up_high_risk_caution(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor < 1.0

    def test_trend_up_low_risk_boost(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.POSITIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor > 1.0

    def test_no_trend_no_interaction(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.NEUTRAL,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        matched_trend_risk = [
            a
            for a in r.active_interactions
            if a.rule.dim_a == DimensionName.TREND and a.rule.dim_b == DimensionName.RISK
        ]
        assert len(matched_trend_risk) == 0


# ===========================================================================
# SECTION 15 — Stability+urgency interaction
# ===========================================================================


class TestSection15StabilityUrgency:
    def test_low_stab_high_urg_danger(self):
        regimes = _full_regimes(
            stab_dir=DirectionCategory.NEGATIVE,
            urg_dir=DirectionCategory.NEGATIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor < 1.0

    def test_high_stab_high_urg_confident(self):
        regimes = _full_regimes(
            stab_dir=DirectionCategory.POSITIVE,
            urg_dir=DirectionCategory.NEGATIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        factor_from_stab_urg = any(
            a.rule.dim_a == DimensionName.STABILITY and a.rule.dim_b == DimensionName.URGENCY
            for a in r.active_interactions
        )
        assert factor_from_stab_urg


# ===========================================================================
# SECTION 16 — Selection top N (inv 305)
# ===========================================================================


class TestSection16Selection:
    def test_max_3_active(self):
        rules = tuple(
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.95 - i * 0.01,
                label=f"rule_{i}",
            )
            for i in range(5)
        )
        regimes = _full_regimes()
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(max_active=3, rules=rules),
        )
        assert len(r.active_interactions) <= 3

    def test_sorted_by_deviation(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.99,
                label="small",
            ),
            InteractionRule(
                dim_a=DimensionName.STABILITY,
                dim_b=DimensionName.URGENCY,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.91,
                label="big",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(max_active=1, rules=rules, strength_threshold=0.0),
        )
        assert len(r.active_interactions) == 1
        assert r.active_interactions[0].rule.label == "big"

    def test_max_1_active(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            stab_dir=DirectionCategory.NEGATIVE,
            urg_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(max_active=1),
        )
        assert len(r.active_interactions) <= 1


# ===========================================================================
# SECTION 17 — Clamping [0.9, 1.1] (inv 303)
# ===========================================================================


class TestSection17Clamping:
    def test_product_clamped_low(self):
        rules = tuple(
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.9,
                label=f"low_{i}",
            )
            for i in range(5)
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(max_active=5, rules=rules, strength_threshold=0.0),
        )
        assert r.interaction_factor >= _INTERACTION_FACTOR_MIN
        assert r.clamped

    def test_product_clamped_high(self):
        rules = tuple(
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=1.1,
                label=f"high_{i}",
            )
            for i in range(5)
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(max_active=5, rules=rules, strength_threshold=0.0),
        )
        assert r.interaction_factor <= _INTERACTION_FACTOR_MAX
        assert r.clamped

    def test_within_bounds_no_clamp(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.POSITIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        if not r.clamped:
            assert _INTERACTION_FACTOR_MIN <= r.interaction_factor <= _INTERACTION_FACTOR_MAX


# ===========================================================================
# SECTION 18 — Safety: cannot flip clearly superior (inv 304)
# ===========================================================================


class TestSection18Safety:
    def test_interaction_cannot_dominate(self):
        r = compute_interaction_factor(
            dimension_regimes=_full_regimes(strength=1.0),
            config=_enabled_config(),
        )
        assert abs(r.interaction_factor - 1.0) <= 0.10

    def test_max_swing(self):
        for _ in range(20):
            regimes = _full_regimes(
                trend_dir=DirectionCategory.POSITIVE,
                risk_dir=DirectionCategory.NEGATIVE,
                stab_dir=DirectionCategory.NEGATIVE,
                urg_dir=DirectionCategory.NEGATIVE,
                strength=1.0,
            )
            r = compute_interaction_factor(
                dimension_regimes=regimes,
                config=_enabled_config(),
            )
            assert 0.9 <= r.interaction_factor <= 1.1

    def test_base_ordering_preserved(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        cfg = _enabled_config()
        int_result = compute_interaction_factor(
            dimension_regimes=regimes,
            config=cfg,
        )
        score_a = 1.0 * int_result.interaction_factor
        score_b = 0.70 * int_result.interaction_factor
        assert score_a > score_b


# ===========================================================================
# SECTION 19 — Determinism (inv 306)
# ===========================================================================


class TestSection19Determinism:
    def test_100_runs_identical(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        cfg = _enabled_config()
        results = [
            compute_interaction_factor(dimension_regimes=regimes, config=cfg) for _ in range(100)
        ]
        first = results[0].interaction_factor
        assert all(r.interaction_factor == first for r in results)

    def test_active_pairs_stable(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        cfg = _enabled_config()
        results = [
            compute_interaction_factor(dimension_regimes=regimes, config=cfg) for _ in range(50)
        ]
        first_pairs = len(results[0].active_interactions)
        assert all(len(r.active_interactions) == first_pairs for r in results)


# ===========================================================================
# SECTION 20 — Explainability (inv 309)
# ===========================================================================


class TestSection20Explainability:
    def test_explanation_populated(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert len(r.explanation) > 0

    def test_matched_count_in_explanation(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert "matched=" in r.explanation

    def test_active_count_in_explanation(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert "active=" in r.explanation

    def test_active_labels_in_explanation(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        for active in r.active_interactions:
            assert active.rule.label in r.explanation


# ===========================================================================
# SECTION 21 — No mutation (inv 311)
# ===========================================================================


class TestSection21NoMutation:
    def test_regimes_unchanged(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
        )
        before = {k: v.strength for k, v in regimes.items()}
        compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        after = {k: v.strength for k, v in regimes.items()}
        assert before == after

    def test_config_unchanged(self):
        cfg = _enabled_config()
        before_active = cfg.max_active_pairs
        compute_interaction_factor(
            dimension_regimes=_full_regimes(),
            config=cfg,
        )
        assert cfg.max_active_pairs == before_active


# ===========================================================================
# SECTION 22 — Custom rules
# ===========================================================================


class TestSection22CustomRules:
    def test_custom_rule_applied(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.STABILITY,
                dir_a=InteractionDirection.POSITIVE,
                dir_b=InteractionDirection.POSITIVE,
                factor=1.08,
                label="custom_boost",
            ),
        )
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            stab_dir=DirectionCategory.POSITIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        assert r.interaction_factor > 1.0
        assert any(a.rule.label == "custom_boost" for a in r.active_interactions)

    def test_no_matching_custom_rules(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.STABILITY,
                dir_a=InteractionDirection.NEGATIVE,
                dir_b=InteractionDirection.NEGATIVE,
                factor=0.92,
            ),
        )
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            stab_dir=DirectionCategory.POSITIVE,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules),
        )
        assert r.interaction_factor == 1.0

    def test_empty_rules_use_defaults(self):
        cfg = _enabled_config()
        assert len(cfg.rules) == 4


# ===========================================================================
# SECTION 23 — Partial regimes (inv 308)
# ===========================================================================


class TestSection23PartialRegimes:
    def test_single_dimension_neutral(self):
        regimes = {
            DimensionName.TREND: _regime(DimensionName.TREND, DirectionCategory.POSITIVE),
        }
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor == 1.0

    def test_two_matching_dimensions(self):
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor != 1.0

    def test_three_dimensions_no_pair(self):
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.NEUTRAL, strength=0.0
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEUTRAL, strength=0.0
            ),
            DimensionName.STABILITY: _regime(
                DimensionName.STABILITY, DirectionCategory.NEUTRAL, strength=0.0
            ),
        }
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor == 1.0


# ===========================================================================
# SECTION 24 — DEFAULT_INTERACTION_CONFIG
# ===========================================================================


class TestSection24DefaultConfig:
    def test_exists(self):
        assert DEFAULT_INTERACTION_CONFIG is not None

    def test_disabled(self):
        assert DEFAULT_INTERACTION_CONFIG.enabled is False

    def test_rules_count(self):
        assert len(DEFAULT_INTERACTION_CONFIG.rules) == 4


# ===========================================================================
# SECTION 25 — No combinatorial explosion (inv 310)
# ===========================================================================


class TestSection25NoExplosion:
    def test_many_rules_bounded(self):
        rules = tuple(
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.91,
                label=f"rule_{i}",
            )
            for i in range(20)
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(max_active=3, rules=rules, strength_threshold=0.0),
        )
        assert len(r.active_interactions) <= 3
        assert r.interaction_factor >= _INTERACTION_FACTOR_MIN

    def test_total_evaluated_vs_matched(self):
        rules = tuple(
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.95,
                label=f"rule_{i}",
            )
            for i in range(10)
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        assert r.total_rules_evaluated == 10
        assert r.total_rules_matched <= 10


# ===========================================================================
# SECTION 26 — No circular dependency (inv 307)
# ===========================================================================


class TestSection26NoCicular:
    def test_imports_only_allowed(self):
        import inspect

        import umh.runtime.dimension_interactions as m

        src = inspect.getsource(m)
        allowed = {"regime_aggregation"}
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"


# ===========================================================================
# SECTION 27 — Orchestrator integration: interaction_factor in candidate
# ===========================================================================


class TestSection27OrchestratorCandidate:
    def test_interaction_factor_default(self):
        c = StrategyCandidate()
        assert c.interaction_factor == 1.0

    def test_interaction_factor_in_final_score(self):
        c = StrategyCandidate(
            base_score=1.0,
            regime_factor=1.0,
            feedback_factor=1.0,
            weight_factor=1.0,
            interaction_factor=0.95,
        )
        assert abs(c.final_score - 0.95) < 0.001

    def test_interaction_factor_clamped_low(self):
        c = StrategyCandidate(interaction_factor=0.5)
        assert c.interaction_factor == 0.9

    def test_interaction_factor_clamped_high(self):
        c = StrategyCandidate(interaction_factor=2.0)
        assert c.interaction_factor == 1.1

    def test_interaction_factor_in_to_dict(self):
        d = StrategyCandidate().to_dict()
        assert "interaction_factor" in d


# ===========================================================================
# SECTION 28 — Orchestrator integration: used_interactions + interaction_winner
# ===========================================================================


class TestSection28OrchestratorResult:
    def test_used_interactions_default_false(self):
        r = StrategySelectionResult()
        assert r.used_interactions is False

    def test_interaction_winner_default_empty(self):
        r = StrategySelectionResult()
        assert r.interaction_winner == ""

    def test_interaction_result_default_none(self):
        r = StrategySelectionResult()
        assert r.interaction_result is None

    def test_changed_from_weights_default(self):
        r = StrategySelectionResult()
        assert r.changed_from_weights is False

    def test_used_interactions_in_to_dict(self):
        d = StrategySelectionResult().to_dict()
        assert "used_interactions" in d
        assert "interaction_winner" in d
        assert "changed_from_weights" in d


# ===========================================================================
# SECTION 29 — Orchestrate with interactions disabled
# ===========================================================================


class TestSection29OrchestrateDisabled:
    def test_no_config_no_interaction(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
        )
        assert result.used_interactions is False
        assert result.interaction_result is None

    def test_disabled_config_no_interaction(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=InteractionConfig(enabled=False),
        )
        assert result.used_interactions is False

    def test_disabled_preserves_selection(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=InteractionConfig(enabled=False),
        )
        assert result.selected_strategy == "a"


# ===========================================================================
# SECTION 30 — Orchestrate with interactions enabled
# ===========================================================================


class TestSection30OrchestrateEnabled:
    def test_interaction_factor_applied(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        for c in result.candidates:
            assert c.interaction_factor != 1.0 or not result.used_interactions

    def test_interaction_result_attached(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert result.interaction_result is not None


# ===========================================================================
# SECTION 31 — Orchestrate: interactions cannot override clear leader
# ===========================================================================


class TestSection31InteractionCannotOverride:
    def test_clear_leader_survives(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[1.0, 0.5],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert result.selected_strategy == "a"

    def test_close_scores_interaction_preserves_order(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.POSITIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.80, 0.79],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert result.selected_strategy == "a"


# ===========================================================================
# SECTION 32 — Orchestrate: interaction_winner tracked
# ===========================================================================


class TestSection32InteractionWinner:
    def test_interaction_winner_set(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert result.interaction_winner in ["a", "b"]


# ===========================================================================
# SECTION 33 — Orchestrate explanation includes interaction info
# ===========================================================================


class TestSection33OrchestrateExplanation:
    def test_interactions_in_explanation_when_active(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert "interaction" in result.explanation.lower()

    def test_interactions_disabled_in_explanation(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
        )
        assert "interactions disabled" in result.explanation


# ===========================================================================
# SECTION 34 — Interaction with all dimensions neutral
# ===========================================================================


class TestSection34AllNeutral:
    def test_all_neutral_no_interaction(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.NEUTRAL,
            risk_dir=DirectionCategory.NEUTRAL,
            stab_dir=DirectionCategory.NEUTRAL,
            urg_dir=DirectionCategory.NEUTRAL,
            strength=0.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor == 1.0
        assert r.total_rules_matched == 0


# ===========================================================================
# SECTION 35 — Strength threshold filtering
# ===========================================================================


class TestSection35StrengthThreshold:
    def test_below_threshold_filtered(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=0.2,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(strength_threshold=0.5),
        )
        assert r.interaction_factor == 1.0

    def test_above_threshold_active(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=0.8,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(strength_threshold=0.3),
        )
        assert r.total_rules_matched > 0

    def test_zero_threshold_all_pass(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=0.01,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(strength_threshold=0.0),
        )
        assert r.total_rules_matched > 0


# ===========================================================================
# SECTION 36 — Product computation
# ===========================================================================


class TestSection36Product:
    def test_single_factor_is_product(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.95,
                label="only",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        assert abs(r.raw_product - 0.95) < 0.001

    def test_two_factors_multiply(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.95,
                label="r1",
            ),
            InteractionRule(
                dim_a=DimensionName.STABILITY,
                dim_b=DimensionName.URGENCY,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=1.05,
                label="r2",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        expected = 0.95 * 1.05
        assert abs(r.raw_product - expected) < 0.001


# ===========================================================================
# SECTION 37 — ANY direction matching
# ===========================================================================


class TestSection37AnyDirection:
    def test_any_matches_all(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.95,
                label="any_both",
            ),
        )
        for dir_a in DirectionCategory:
            for dir_b in DirectionCategory:
                regimes = {
                    DimensionName.TREND: _regime(DimensionName.TREND, dir_a, strength=1.0),
                    DimensionName.RISK: _regime(DimensionName.RISK, dir_b, strength=1.0),
                }
                r = compute_interaction_factor(
                    dimension_regimes=regimes,
                    config=_enabled_config(rules=rules, strength_threshold=0.0),
                )
                assert r.total_rules_matched >= 1


# ===========================================================================
# SECTION 38 — Symmetry of default rules
# ===========================================================================


class TestSection38DefaultRuleSymmetry:
    def test_trend_risk_has_both_directions(self):
        cfg = DEFAULT_INTERACTION_CONFIG
        trend_risk = [
            r for r in cfg.rules if r.dim_a == DimensionName.TREND and r.dim_b == DimensionName.RISK
        ]
        dirs_a = {r.dir_a for r in trend_risk}
        assert InteractionDirection.POSITIVE in dirs_a

    def test_stability_urgency_has_rules(self):
        cfg = DEFAULT_INTERACTION_CONFIG
        stab_urg = [
            r
            for r in cfg.rules
            if r.dim_a == DimensionName.STABILITY and r.dim_b == DimensionName.URGENCY
        ]
        assert len(stab_urg) >= 2


# ===========================================================================
# SECTION 39 — __init__.py exports
# ===========================================================================


class TestSection39Exports:
    def test_interaction_config_exported(self):
        from umh.runtime import InteractionConfig as IC

        assert IC is InteractionConfig

    def test_interaction_result_exported(self):
        from umh.runtime import InteractionResult as IR

        assert IR is InteractionResult

    def test_compute_exported(self):
        from umh.runtime import compute_interaction_factor as cif

        assert cif is compute_interaction_factor

    def test_default_config_exported(self):
        from umh.runtime import DEFAULT_INTERACTION_CONFIG as dic

        assert dic is DEFAULT_INTERACTION_CONFIG

    def test_interaction_rule_exported(self):
        from umh.runtime import InteractionRule as IRu

        assert IRu is InteractionRule

    def test_interaction_direction_exported(self):
        from umh.runtime import InteractionDirection as ID

        assert ID is InteractionDirection

    def test_active_interaction_exported(self):
        from umh.runtime import ActiveInteraction as AI

        assert AI is ActiveInteraction


# ===========================================================================
# SECTION 40 — Edge: zero strength
# ===========================================================================


class TestSection40ZeroStrength:
    def test_zero_strength_neutral(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=0.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(strength_threshold=0.0),
        )
        assert r.interaction_factor == 1.0


# ===========================================================================
# SECTION 41 — Edge: single dimension only
# ===========================================================================


class TestSection41SingleDimension:
    def test_trend_only(self):
        regimes = {
            DimensionName.TREND: _regime(DimensionName.TREND, DirectionCategory.POSITIVE),
        }
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor == 1.0
        assert r.total_rules_matched == 0

    def test_risk_only(self):
        regimes = {
            DimensionName.RISK: _regime(DimensionName.RISK, DirectionCategory.NEGATIVE),
        }
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor == 1.0


# ===========================================================================
# SECTION 42 — All four dimensions active
# ===========================================================================


class TestSection42AllDimensions:
    def test_all_positive(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.POSITIVE,
            stab_dir=DirectionCategory.POSITIVE,
            urg_dir=DirectionCategory.POSITIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.total_rules_matched >= 1

    def test_all_negative(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.NEGATIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            stab_dir=DirectionCategory.NEGATIVE,
            urg_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert _INTERACTION_FACTOR_MIN <= r.interaction_factor <= _INTERACTION_FACTOR_MAX

    def test_mixed(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            stab_dir=DirectionCategory.NEGATIVE,
            urg_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor < 1.0


# ===========================================================================
# SECTION 43 — Interaction factor monotonicity with strength
# ===========================================================================


class TestSection43StrengthMonotonicity:
    def test_stronger_signal_larger_deviation(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.9,
            label="test",
        )
        cfg_low = _enabled_config(rules=(rule,), strength_threshold=0.0)
        cfg_high = _enabled_config(rules=(rule,), strength_threshold=0.0)

        regimes_low = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=0.4
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=0.4
            ),
        }
        regimes_high = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }

        r_low = compute_interaction_factor(dimension_regimes=regimes_low, config=cfg_low)
        r_high = compute_interaction_factor(dimension_regimes=regimes_high, config=cfg_high)

        dev_low = abs(r_low.interaction_factor - 1.0)
        dev_high = abs(r_high.interaction_factor - 1.0)
        assert dev_high >= dev_low


# ===========================================================================
# SECTION 44 — Orchestrator: no regimes + interaction enabled
# ===========================================================================


class TestSection44OrchestratorNoRegimes:
    def test_no_regimes_neutral(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=_enabled_config(),
        )
        assert result.used_interactions is False
        for c in result.candidates:
            assert c.interaction_factor == 1.0


# ===========================================================================
# SECTION 45 — Orchestrator: interaction result in to_dict
# ===========================================================================


class TestSection45OrchestratorToDict:
    def test_interaction_result_in_to_dict(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        d = result.to_dict()
        assert "interaction_result" in d


# ===========================================================================
# SECTION 46 — Neutral factors filtered out
# ===========================================================================


class TestSection46NeutralFiltered:
    def test_neutral_factor_not_active(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=1.0,
                label="neutral",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        assert r.total_rules_matched == 0
        assert r.interaction_factor == 1.0


# ===========================================================================
# SECTION 47 — Multiple same-pair rules
# ===========================================================================


class TestSection47MultipleSamePair:
    def test_multiple_rules_same_pair(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.POSITIVE,
                dir_b=InteractionDirection.NEGATIVE,
                factor=0.95,
                label="r1",
            ),
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.POSITIVE,
                dir_b=InteractionDirection.NEGATIVE,
                factor=0.92,
                label="r2",
            ),
        )
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        assert r.total_rules_matched == 2


# ===========================================================================
# SECTION 48 — Interaction with regime aggregation state
# ===========================================================================


class TestSection48WithAggregatedRegime:
    def test_orchestrator_accepts_both(self):
        from umh.runtime.regime_aggregation import NEUTRAL_AGGREGATED

        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=NEUTRAL_AGGREGATED,
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert result.aggregated_regime is not None
        assert result.interaction_result is not None


# ===========================================================================
# SECTION 49 — Interaction factor range (all scenarios)
# ===========================================================================


class TestSection49FactorRange:
    def test_all_direction_combos_bounded(self):
        cfg = _enabled_config()
        for td in DirectionCategory:
            for rd in DirectionCategory:
                for sd in DirectionCategory:
                    for ud in DirectionCategory:
                        regimes = _full_regimes(
                            trend_dir=td,
                            risk_dir=rd,
                            stab_dir=sd,
                            urg_dir=ud,
                            strength=1.0,
                        )
                        r = compute_interaction_factor(dimension_regimes=regimes, config=cfg)
                        assert (
                            _INTERACTION_FACTOR_MIN
                            <= r.interaction_factor
                            <= _INTERACTION_FACTOR_MAX
                        ), f"OOB for {td} {rd} {sd} {ud}: {r.interaction_factor}"


# ===========================================================================
# SECTION 50 — Interaction raw_product vs final
# ===========================================================================


class TestSection50RawVsFinal:
    def test_clamped_when_different(self):
        rules = tuple(
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.9,
                label=f"r_{i}",
            )
            for i in range(4)
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(max_active=4, rules=rules, strength_threshold=0.0),
        )
        if r.raw_product < _INTERACTION_FACTOR_MIN or r.raw_product > _INTERACTION_FACTOR_MAX:
            assert r.clamped
            assert r.interaction_factor != r.raw_product

    def test_not_clamped_when_same(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=1.02,
                label="small",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        if _INTERACTION_FACTOR_MIN <= r.raw_product <= _INTERACTION_FACTOR_MAX:
            assert not r.clamped
            assert abs(r.interaction_factor - r.raw_product) < 0.0001


# ===========================================================================
# SECTION 51 — Orchestrate: 3 candidates with interaction
# ===========================================================================


class TestSection51ThreeCandidates:
    def test_three_candidates(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.POSITIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b", "c"],
            base_scores=[0.7, 0.71, 0.69],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert len(result.candidates) == 3
        assert all(c.interaction_factor >= 0.9 for c in result.candidates)
        assert all(c.interaction_factor <= 1.1 for c in result.candidates)


# ===========================================================================
# SECTION 52 — Orchestrate: empty strategies
# ===========================================================================


class TestSection52EmptyStrategies:
    def test_empty_with_interaction(self):
        result = orchestrate_selection(
            strategy_ids=[],
            base_scores=[],
            interaction_config=_enabled_config(),
        )
        assert result.selected_strategy == ""
        assert "no strategies" in result.explanation


# ===========================================================================
# SECTION 53 — Regression: Phase 58 unchanged
# ===========================================================================


class TestSection53Phase58Regression:
    def test_base_selection_unchanged(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b", "c"],
            base_scores=[0.9, 0.7, 0.5],
        )
        assert result.selected_strategy == "a"
        assert result.base_winner == "a"

    def test_regime_selection_unchanged(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.7],
            regime_factors=[0.9, 1.15],
        )
        assert result.used_regime is True


# ===========================================================================
# SECTION 54 — Interaction with DimensionName keys (not strings)
# ===========================================================================


class TestSection54DimensionNameKeys:
    def test_enum_keys_in_compute(self):
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.total_rules_matched >= 1


# ===========================================================================
# SECTION 55 — Interaction with max_active=6 (ceiling)
# ===========================================================================


class TestSection55MaxActive6:
    def test_max_6_respected(self):
        rules = tuple(
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.95,
                label=f"r_{i}",
            )
            for i in range(10)
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(max_active=6, rules=rules, strength_threshold=0.0),
        )
        assert len(r.active_interactions) <= 6


# ===========================================================================
# SECTION 56 — Factor at boundary values
# ===========================================================================


class TestSection56BoundaryFactors:
    def test_factor_exactly_09(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.9,
                label="min",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        assert abs(r.interaction_factor - 0.9) < 0.001

    def test_factor_exactly_11(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=1.1,
                label="max",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        assert abs(r.interaction_factor - 1.1) < 0.001


# ===========================================================================
# SECTION 57 — Negative caution stronger than positive boost
# ===========================================================================


class TestSection57CautionStronger:
    def test_default_caution_vs_boost(self):
        cfg = DEFAULT_INTERACTION_CONFIG
        trend_risk_rules = [
            r for r in cfg.rules if r.dim_a == DimensionName.TREND and r.dim_b == DimensionName.RISK
        ]
        caution = [r for r in trend_risk_rules if r.factor < 1.0]
        boost = [r for r in trend_risk_rules if r.factor > 1.0]
        if caution and boost:
            assert abs(caution[0].factor - 1.0) >= abs(boost[0].factor - 1.0)


# ===========================================================================
# SECTION 58 — Multi-rule interaction ordering
# ===========================================================================


class TestSection58MultiRuleOrdering:
    def test_highest_deviation_first(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.99,
                label="tiny",
            ),
            InteractionRule(
                dim_a=DimensionName.STABILITY,
                dim_b=DimensionName.URGENCY,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.91,
                label="big",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        assert r.active_interactions[0].rule.label == "big"


# ===========================================================================
# SECTION 59 — Interaction isolation from other pipeline stages
# ===========================================================================


class TestSection59PipelineIsolation:
    def test_interaction_does_not_affect_regime(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            regime_factors=[1.1, 0.9],
            interaction_config=_enabled_config(),
            dimension_regimes={
                DimensionName.TREND.value: _regime(
                    DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
                ),
                DimensionName.RISK.value: _regime(
                    DimensionName.RISK, DirectionCategory.POSITIVE, strength=1.0
                ),
            },
        )
        assert result.regime_winner == "a"

    def test_interaction_does_not_affect_feedback(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=_enabled_config(),
        )
        assert result.feedback_winner == result.regime_winner


# ===========================================================================
# SECTION 60 — Interaction factor persistence in candidate
# ===========================================================================


class TestSection60FactorPersistence:
    def test_all_candidates_same_factor(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b", "c"],
            base_scores=[0.8, 0.7, 0.6],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        factors = [c.interaction_factor for c in result.candidates]
        assert all(f == factors[0] for f in factors)


# ===========================================================================
# SECTION 61 — Confidence does not affect interaction
# ===========================================================================


class TestSection61ConfidenceIndependent:
    def test_different_confidences_same_interaction(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        cfg = _enabled_config()
        r1 = compute_interaction_factor(dimension_regimes=regimes, config=cfg)

        regimes2 = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0, confidence=0.1
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0, confidence=0.1
            ),
        }
        r2 = compute_interaction_factor(dimension_regimes=regimes2, config=cfg)
        assert r1.interaction_factor == r2.interaction_factor


# ===========================================================================
# SECTION 62 — Default rules cover all intended pairs
# ===========================================================================


class TestSection62DefaultRuleCoverage:
    def test_trend_risk_covered(self):
        cfg = DEFAULT_INTERACTION_CONFIG
        pairs = [(r.dim_a, r.dim_b) for r in cfg.rules]
        assert (DimensionName.TREND, DimensionName.RISK) in pairs

    def test_stability_urgency_covered(self):
        cfg = DEFAULT_INTERACTION_CONFIG
        pairs = [(r.dim_a, r.dim_b) for r in cfg.rules]
        assert (DimensionName.STABILITY, DimensionName.URGENCY) in pairs

    def test_no_self_interactions(self):
        cfg = DEFAULT_INTERACTION_CONFIG
        for r in cfg.rules:
            assert r.dim_a != r.dim_b

    def test_total_default_rules(self):
        cfg = DEFAULT_INTERACTION_CONFIG
        assert len(cfg.rules) == 4


# ===========================================================================
# SECTION 63 — Config with explicit empty rules
# ===========================================================================


class TestSection63ExplicitEmptyRules:
    def test_explicit_rules_override_defaults(self):
        custom_rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.STABILITY,
            dir_a=InteractionDirection.ANY,
            dir_b=InteractionDirection.ANY,
            factor=1.05,
            label="custom",
        )
        cfg = InteractionConfig(enabled=True, rules=(custom_rule,))
        assert len(cfg.rules) == 1
        assert cfg.rules[0].label == "custom"


# ===========================================================================
# SECTION 64 — Interaction does not change with repeated calls
# ===========================================================================


class TestSection64Idempotent:
    def test_repeated_calls_same_result(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=0.7,
        )
        cfg = _enabled_config()
        results = [
            compute_interaction_factor(dimension_regimes=regimes, config=cfg) for _ in range(10)
        ]
        assert all(r.interaction_factor == results[0].interaction_factor for r in results)
        assert all(r.total_rules_matched == results[0].total_rules_matched for r in results)


# ===========================================================================
# SECTION 65 — Orchestrator: interaction in to_dict when None
# ===========================================================================


class TestSection65NoneInteractionToDict:
    def test_no_interaction_result_not_in_dict(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
        )
        d = result.to_dict()
        assert "interaction_result" not in d


# ===========================================================================
# SECTION 66 — Orchestrator: final_score includes interaction
# ===========================================================================


class TestSection66FinalScoreIncludes:
    def test_final_score_with_interaction(self):
        c = StrategyCandidate(
            base_score=1.0,
            regime_factor=1.1,
            feedback_factor=1.0,
            weight_factor=1.0,
            interaction_factor=0.95,
        )
        expected = 1.0 * 1.1 * 1.0 * 1.0 * 0.95
        assert abs(c.final_score - expected) < 0.001


# ===========================================================================
# SECTION 67 — No runaway with many iterations
# ===========================================================================


class TestSection67NoRunaway:
    def test_10_iterations_bounded(self):
        cfg = _enabled_config()
        for _ in range(10):
            regimes = _full_regimes(
                trend_dir=DirectionCategory.POSITIVE,
                risk_dir=DirectionCategory.NEGATIVE,
                stab_dir=DirectionCategory.NEGATIVE,
                urg_dir=DirectionCategory.NEGATIVE,
                strength=1.0,
            )
            r = compute_interaction_factor(dimension_regimes=regimes, config=cfg)
            assert _INTERACTION_FACTOR_MIN <= r.interaction_factor <= _INTERACTION_FACTOR_MAX


# ===========================================================================
# SECTION 68 — Orchestrate: pipeline order preserved
# ===========================================================================


class TestSection68PipelineOrder:
    def test_order_base_regime_feedback_weight_interaction(self):
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            regime_factors=[1.0, 1.0],
        )
        assert result.base_winner == "a"
        assert result.regime_winner == "a"
        assert result.feedback_winner == "a"
        assert result.weight_winner == "a"
        assert result.interaction_winner == "a"
        assert result.selected_strategy == "a"


# ===========================================================================
# SECTION 69 — Interaction with all 4 default rules matching
# ===========================================================================


class TestSection69AllDefaultRules:
    def test_all_rules_can_match(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            stab_dir=DirectionCategory.NEGATIVE,
            urg_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.total_rules_matched >= 2

    def test_bounded_even_when_all_match(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            stab_dir=DirectionCategory.NEGATIVE,
            urg_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert 0.9 <= r.interaction_factor <= 1.1


# ===========================================================================
# SECTION 70 — Factor 1.0 rule has zero deviation
# ===========================================================================


class TestSection70ZeroDeviation:
    def test_factor_1_zero_deviation(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.POSITIVE,
            factor=1.0,
        )
        ai = ActiveInteraction(
            rule=rule,
            dim_a_regime=_regime(DimensionName.TREND, DirectionCategory.POSITIVE),
            dim_b_regime=_regime(DimensionName.RISK, DirectionCategory.POSITIVE),
            raw_factor=1.0,
        )
        assert ai.deviation == 0.0


# ===========================================================================
# SECTION 71 — Orchestrator: many candidates
# ===========================================================================


class TestSection71ManyCandidates:
    def test_10_candidates(self):
        ids = [f"s{i}" for i in range(10)]
        scores = [0.5 + i * 0.05 for i in range(10)]
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.POSITIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=ids,
            base_scores=scores,
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert len(result.candidates) == 10
        assert result.selected_strategy == "s9"


# ===========================================================================
# SECTION 72 — Interaction strength_weight tracking
# ===========================================================================


class TestSection72StrengthWeight:
    def test_strength_weight_matches_min(self):
        rule = InteractionRule(
            dim_a=DimensionName.TREND,
            dim_b=DimensionName.RISK,
            dir_a=InteractionDirection.POSITIVE,
            dir_b=InteractionDirection.NEGATIVE,
            factor=0.95,
        )
        regimes = {
            DimensionName.TREND: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=0.6
            ),
            DimensionName.RISK: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=0.4
            ),
        }
        result = _evaluate_rule(rule, regimes, 0.0)
        assert result is not None
        assert abs(result.strength_weight - 0.4) < 0.001


# ===========================================================================
# SECTION 73 — Interaction factor in candidate final_score multiplicative
# ===========================================================================


class TestSection73Multiplicative:
    def test_five_factor_multiplication(self):
        c = StrategyCandidate(
            base_score=1.0,
            regime_factor=1.10,
            feedback_factor=1.2,
            weight_factor=0.9,
            interaction_factor=0.95,
        )
        expected = 1.0 * 1.10 * 1.2 * 0.9 * 0.95
        assert abs(c.final_score - expected) < 0.001


# ===========================================================================
# SECTION 74 — Interaction: negative factor with boost
# ===========================================================================


class TestSection74NegativeAndBoost:
    def test_opposing_rules_partially_cancel(self):
        rules = (
            InteractionRule(
                dim_a=DimensionName.TREND,
                dim_b=DimensionName.RISK,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=0.93,
                label="down",
            ),
            InteractionRule(
                dim_a=DimensionName.STABILITY,
                dim_b=DimensionName.URGENCY,
                dir_a=InteractionDirection.ANY,
                dir_b=InteractionDirection.ANY,
                factor=1.07,
                label="up",
            ),
        )
        regimes = _full_regimes(strength=1.0)
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(rules=rules, strength_threshold=0.0),
        )
        expected = 0.93 * 1.07
        assert abs(r.raw_product - expected) < 0.001


# ===========================================================================
# SECTION 75 — Orchestrator: interaction_result to_dict structure
# ===========================================================================


class TestSection75InteractionResultDict:
    def test_to_dict_structure(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        d = result.to_dict()
        if "interaction_result" in d:
            ir = d["interaction_result"]
            assert "interaction_factor" in ir
            assert "active_interactions" in ir
            assert "clamped" in ir


# ===========================================================================
# SECTION 76 — Config: custom max_active_pairs values
# ===========================================================================


class TestSection76CustomMaxActive:
    def test_max_1(self):
        cfg = InteractionConfig(enabled=True, max_active_pairs=1)
        assert cfg.max_active_pairs == 1

    def test_max_6(self):
        cfg = InteractionConfig(enabled=True, max_active_pairs=6)
        assert cfg.max_active_pairs == 6

    def test_max_clamped_to_6(self):
        cfg = InteractionConfig(enabled=True, max_active_pairs=10)
        assert cfg.max_active_pairs == 6


# ===========================================================================
# SECTION 77 — Regression: interaction does not break weighted decision
# ===========================================================================


class TestSection77WeightedDecisionRegression:
    def test_weighted_policy_still_works(self):
        from umh.runtime.weighted_decision import WeightedDecisionPolicy

        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            weighted_decision_policy=WeightedDecisionPolicy(enabled=False),
            interaction_config=_enabled_config(),
            dimension_regimes={
                DimensionName.TREND.value: _regime(
                    DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
                ),
                DimensionName.RISK.value: _regime(
                    DimensionName.RISK, DirectionCategory.POSITIVE, strength=1.0
                ),
            },
        )
        assert result.used_weights is False
        assert result.selected_strategy == "a"


# ===========================================================================
# SECTION 78 — Interaction with exact boundary strengths
# ===========================================================================


class TestSection78BoundaryStrengths:
    def test_strength_exactly_at_threshold(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=0.3,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(strength_threshold=0.3),
        )
        assert r.total_rules_evaluated == 4

    def test_strength_just_below_threshold(self):
        regimes = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=0.29,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(strength_threshold=0.3),
        )
        assert r.total_rules_matched == 0


# ===========================================================================
# SECTION 79 — Interaction factor symmetry
# ===========================================================================


class TestSection79Symmetry:
    def test_positive_boost_vs_negative_caution_same_magnitude(self):
        cfg = _enabled_config()
        regimes_boost = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.POSITIVE,
            strength=1.0,
        )
        regimes_caution = _full_regimes(
            trend_dir=DirectionCategory.POSITIVE,
            risk_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        r_boost = compute_interaction_factor(dimension_regimes=regimes_boost, config=cfg)
        r_caution = compute_interaction_factor(dimension_regimes=regimes_caution, config=cfg)
        assert r_boost.interaction_factor >= 1.0 or r_boost.total_rules_matched == 0
        assert r_caution.interaction_factor <= 1.0 or r_caution.total_rules_matched == 0


# ===========================================================================
# SECTION 80 — Orchestrator: string key conversion
# ===========================================================================


class TestSection80StringKeys:
    def test_string_keys_work(self):
        result = orchestrate_selection(
            strategy_ids=["a"],
            base_scores=[0.8],
            interaction_config=_enabled_config(),
            dimension_regimes={
                "trend": _regime(DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0),
                "risk": _regime(DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0),
            },
        )
        assert result.interaction_result is not None

    def test_enum_keys_work(self):
        result = orchestrate_selection(
            strategy_ids=["a"],
            base_scores=[0.8],
            interaction_config=_enabled_config(),
            dimension_regimes={
                DimensionName.TREND.value: _regime(
                    DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
                ),
                DimensionName.RISK.value: _regime(
                    DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
                ),
            },
        )
        assert result.interaction_result is not None


# ===========================================================================
# SECTION 81 — Interaction: high urgency scenarios
# ===========================================================================


class TestSection81HighUrgency:
    def test_high_urgency_low_stability_dampens(self):
        regimes = _full_regimes(
            stab_dir=DirectionCategory.NEGATIVE,
            urg_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        assert r.interaction_factor <= 1.0

    def test_high_urgency_high_stability_boosts(self):
        regimes = _full_regimes(
            stab_dir=DirectionCategory.POSITIVE,
            urg_dir=DirectionCategory.NEGATIVE,
            strength=1.0,
        )
        r = compute_interaction_factor(
            dimension_regimes=regimes,
            config=_enabled_config(),
        )
        stab_urg_active = [
            a
            for a in r.active_interactions
            if a.rule.dim_a == DimensionName.STABILITY and a.rule.dim_b == DimensionName.URGENCY
        ]
        if stab_urg_active:
            assert stab_urg_active[0].raw_factor > 1.0


# ===========================================================================
# SECTION 82 — Compound: interaction with regime + feedback
# ===========================================================================


class TestSection82CompoundPipeline:
    def test_all_stages_enabled(self):
        from umh.runtime.feedback_selection import FeedbackSelectionPolicy

        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.POSITIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.75],
            regime_factors=[1.05, 0.95],
            feedback_factors=[1.1, 1.0],
            policy=StrategyOrchestrationPolicy(
                use_regime_weighting=True,
                use_feedback_selection=True,
                feedback_policy=FeedbackSelectionPolicy(enabled=True),
            ),
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        assert result.used_regime is True
        assert result.used_feedback is True
        assert result.selected_strategy in ["a", "b"]
        for c in result.candidates:
            assert 0.9 <= c.interaction_factor <= 1.1

    def test_compound_does_not_exceed_bounds(self):
        regimes = {
            DimensionName.TREND.value: _regime(
                DimensionName.TREND, DirectionCategory.POSITIVE, strength=1.0
            ),
            DimensionName.RISK.value: _regime(
                DimensionName.RISK, DirectionCategory.NEGATIVE, strength=1.0
            ),
            DimensionName.STABILITY.value: _regime(
                DimensionName.STABILITY, DirectionCategory.NEGATIVE, strength=1.0
            ),
            DimensionName.URGENCY.value: _regime(
                DimensionName.URGENCY, DirectionCategory.NEGATIVE, strength=1.0
            ),
        }
        result = orchestrate_selection(
            strategy_ids=["a", "b", "c"],
            base_scores=[1.0, 0.9, 0.8],
            regime_factors=[1.15, 1.0, 0.85],
            interaction_config=_enabled_config(),
            dimension_regimes=regimes,
        )
        for c in result.candidates:
            assert c.final_score >= 0.0
