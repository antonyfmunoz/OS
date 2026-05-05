"""Phase 39 — Temporal Context Smoothing Layer v1.

Tests for:
  - smooth_value (EMA single value)
  - smooth_context (EMA all signals)
  - SmoothingResult (creation, frozen, to_dict)
  - ContextMemory (creation, properties, smooth, reset, override)
  - First-tick passthrough behavior
  - Alpha clamping [0.2, 0.8]
  - Output bounds [0, 1]
  - Oscillation reduction
  - Sustained change responsiveness
  - Convergence behavior
  - Reset conditions
  - Override behavior
  - Integration with WeightAdapter
  - Integration with TradeoffEngine
  - make_context factory
  - Determinism
  - Hard invariants 131-135
  - Dependency boundary
  - Exports and compilation
"""

from __future__ import annotations

import ast
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Section 1: smooth_value
# ---------------------------------------------------------------------------


class TestSmoothValue:
    def test_identity_when_equal(self) -> None:
        from umh.runtime.context_memory import smooth_value

        assert smooth_value(0.7, 0.7, 0.5) == pytest.approx(0.7)

    def test_midpoint_at_half_alpha(self) -> None:
        from umh.runtime.context_memory import smooth_value

        result = smooth_value(1.0, 0.0, 0.5)
        assert result == pytest.approx(0.5)

    def test_high_alpha_favors_current(self) -> None:
        from umh.runtime.context_memory import smooth_value

        result = smooth_value(1.0, 0.0, 0.8)
        assert result == pytest.approx(0.8)

    def test_low_alpha_favors_previous(self) -> None:
        from umh.runtime.context_memory import smooth_value

        result = smooth_value(1.0, 0.0, 0.2)
        assert result == pytest.approx(0.2)

    def test_clamped_to_zero(self) -> None:
        from umh.runtime.context_memory import smooth_value

        result = smooth_value(-5.0, -5.0, 0.5)
        assert result == 0.0

    def test_clamped_to_one(self) -> None:
        from umh.runtime.context_memory import smooth_value

        result = smooth_value(5.0, 5.0, 0.5)
        assert result == 1.0

    def test_boundary_zero_zero(self) -> None:
        from umh.runtime.context_memory import smooth_value

        assert smooth_value(0.0, 0.0, 0.5) == 0.0

    def test_boundary_one_one(self) -> None:
        from umh.runtime.context_memory import smooth_value

        assert smooth_value(1.0, 1.0, 0.5) == 1.0

    def test_formula_exact(self) -> None:
        from umh.runtime.context_memory import smooth_value

        c, p, a = 0.8, 0.3, 0.6
        expected = a * c + (1.0 - a) * p
        assert smooth_value(c, p, a) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Section 2: smooth_context
# ---------------------------------------------------------------------------


class TestSmoothContext:
    def test_all_signals_smoothed(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import smooth_context

        current = ExecutionContext(
            urgency=1.0, risk_level=1.0, resource_pressure=1.0, stability_mode=1.0
        )
        previous = ExecutionContext(
            urgency=0.0, risk_level=0.0, resource_pressure=0.0, stability_mode=0.0
        )
        result = smooth_context(current, previous, 0.5)

        assert result.urgency == pytest.approx(0.5)
        assert result.risk_level == pytest.approx(0.5)
        assert result.resource_pressure == pytest.approx(0.5)
        assert result.stability_mode == pytest.approx(0.5)

    def test_returns_frozen_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import smooth_context

        current = ExecutionContext(urgency=0.8)
        previous = ExecutionContext(urgency=0.2)
        result = smooth_context(current, previous, 0.5)

        with pytest.raises(FrozenInstanceError):
            result.urgency = 0.0  # type: ignore[misc]

    def test_alpha_clamped_internally(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import smooth_context

        current = ExecutionContext(urgency=1.0)
        previous = ExecutionContext(urgency=0.0)

        result_low = smooth_context(current, previous, 0.01)
        assert result_low.urgency == pytest.approx(0.2)

        result_high = smooth_context(current, previous, 0.99)
        assert result_high.urgency == pytest.approx(0.8)

    def test_identical_inputs_preserved(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import smooth_context

        ctx = ExecutionContext(
            urgency=0.7, risk_level=0.3, resource_pressure=0.6, stability_mode=0.2
        )
        result = smooth_context(ctx, ctx, 0.5)
        assert result.urgency == pytest.approx(0.7)
        assert result.risk_level == pytest.approx(0.3)
        assert result.resource_pressure == pytest.approx(0.6)
        assert result.stability_mode == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# Section 3: SmoothingResult
# ---------------------------------------------------------------------------


class TestSmoothingResult:
    def test_creation(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import SmoothingResult

        ctx = ExecutionContext()
        sr = SmoothingResult(
            smoothed=ctx, previous=ctx, raw=ctx, alpha=0.5, tick=1, was_reset=False
        )
        assert sr.tick == 1
        assert sr.was_reset is False
        assert sr.alpha == 0.5

    def test_frozen(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import SmoothingResult

        ctx = ExecutionContext()
        sr = SmoothingResult(
            smoothed=ctx, previous=ctx, raw=ctx, alpha=0.5, tick=1, was_reset=False
        )
        with pytest.raises(FrozenInstanceError):
            sr.tick = 2  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import SmoothingResult

        ctx = ExecutionContext(urgency=0.7)
        sr = SmoothingResult(smoothed=ctx, previous=ctx, raw=ctx, alpha=0.6, tick=3, was_reset=True)
        d = sr.to_dict()
        assert d["alpha"] == 0.6
        assert d["tick"] == 3
        assert d["was_reset"] is True
        assert "smoothed" in d
        assert "previous" in d
        assert "raw" in d


# ---------------------------------------------------------------------------
# Section 4: ContextMemory creation
# ---------------------------------------------------------------------------


class TestContextMemoryCreation:
    def test_default_creation(self) -> None:
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        assert cm.alpha == 0.5
        assert cm.tick == 0
        assert cm.initialized is False
        assert cm.previous_context.is_neutral is True

    def test_custom_alpha(self) -> None:
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.3)
        assert cm.alpha == 0.3

    def test_alpha_clamped_low(self) -> None:
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.01)
        assert cm.alpha == 0.2

    def test_alpha_clamped_high(self) -> None:
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.99)
        assert cm.alpha == 0.8

    def test_custom_initial(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        initial = ExecutionContext(urgency=0.9)
        cm = ContextMemory(initial=initial)
        assert cm.initialized is True
        assert cm.previous_context.urgency == 0.9

    def test_to_dict(self) -> None:
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.4)
        d = cm.to_dict()
        assert d["alpha"] == 0.4
        assert d["tick"] == 0
        assert d["initialized"] is False
        assert "previous_context" in d


# ---------------------------------------------------------------------------
# Section 5: ContextMemory.smooth — first tick
# ---------------------------------------------------------------------------


class TestSmoothFirstTick:
    def test_first_tick_passthrough(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        raw = ExecutionContext(urgency=0.9, risk_level=0.2)
        result = cm.smooth(raw)

        assert result.smoothed.urgency == 0.9
        assert result.smoothed.risk_level == 0.2
        assert result.tick == 1
        assert cm.initialized is True

    def test_first_tick_sets_previous(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        raw = ExecutionContext(urgency=0.8)
        cm.smooth(raw)

        assert cm.previous_context.urgency == 0.8

    def test_first_tick_previous_was_neutral(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        raw = ExecutionContext(urgency=0.9)
        result = cm.smooth(raw)

        assert result.previous.is_neutral is True

    def test_initialized_memory_smooths_first_tick(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        initial = ExecutionContext(urgency=0.0)
        cm = ContextMemory(initial=initial)
        raw = ExecutionContext(urgency=1.0)
        result = cm.smooth(raw)

        assert result.smoothed.urgency != 1.0
        assert result.smoothed.urgency == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Section 6: ContextMemory.smooth — multi-tick
# ---------------------------------------------------------------------------


class TestSmoothMultiTick:
    def test_second_tick_blends(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))
        result = cm.smooth(ExecutionContext(urgency=1.0))

        assert result.smoothed.urgency == pytest.approx(0.5)

    def test_tick_advances(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext())
        cm.smooth(ExecutionContext())
        cm.smooth(ExecutionContext())
        assert cm.tick == 3

    def test_convergence_toward_sustained_signal(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))

        for _ in range(20):
            result = cm.smooth(ExecutionContext(urgency=1.0))

        assert result.smoothed.urgency > 0.99

    def test_convergence_toward_zero(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=1.0))

        for _ in range(20):
            result = cm.smooth(ExecutionContext(urgency=0.0))

        assert result.smoothed.urgency < 0.01

    def test_high_alpha_converges_faster(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm_fast = ContextMemory(alpha=0.8)
        cm_slow = ContextMemory(alpha=0.2)

        cm_fast.smooth(ExecutionContext(urgency=0.0))
        cm_slow.smooth(ExecutionContext(urgency=0.0))

        for _ in range(5):
            r_fast = cm_fast.smooth(ExecutionContext(urgency=1.0))
            r_slow = cm_slow.smooth(ExecutionContext(urgency=1.0))

        assert r_fast.smoothed.urgency > r_slow.smoothed.urgency


# ---------------------------------------------------------------------------
# Section 7: Oscillation reduction
# ---------------------------------------------------------------------------


class TestOscillationReduction:
    def test_alternating_signals_dampened(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.3)
        cm.smooth(ExecutionContext(urgency=0.5))

        values = []
        for i in range(20):
            if i % 2 == 0:
                r = cm.smooth(ExecutionContext(urgency=1.0))
            else:
                r = cm.smooth(ExecutionContext(urgency=0.0))
            values.append(r.smoothed.urgency)

        spread = max(values[-6:]) - min(values[-6:])
        raw_spread = 1.0
        assert spread < raw_spread * 0.8

    def test_rapid_flipping_converges_to_mean(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.3)
        cm.smooth(ExecutionContext(urgency=0.5))

        for i in range(50):
            if i % 2 == 0:
                r = cm.smooth(ExecutionContext(urgency=0.8))
            else:
                r = cm.smooth(ExecutionContext(urgency=0.2))

        assert abs(r.smoothed.urgency - 0.5) < 0.15

    def test_smoothed_variance_less_than_raw(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.4)
        cm.smooth(ExecutionContext(urgency=0.5))

        raw_values = []
        smoothed_values = []
        for i in range(20):
            raw_u = 0.9 if i % 2 == 0 else 0.1
            r = cm.smooth(ExecutionContext(urgency=raw_u))
            raw_values.append(raw_u)
            smoothed_values.append(r.smoothed.urgency)

        def variance(vals: list[float]) -> float:
            mean = sum(vals) / len(vals)
            return sum((v - mean) ** 2 for v in vals) / len(vals)

        assert variance(smoothed_values) < variance(raw_values)


# ---------------------------------------------------------------------------
# Section 8: Sustained change responsiveness
# ---------------------------------------------------------------------------


class TestSustainedChangeResponsiveness:
    def test_step_change_eventual_tracking(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        for _ in range(5):
            cm.smooth(ExecutionContext(urgency=0.2))

        for _ in range(10):
            r = cm.smooth(ExecutionContext(urgency=0.8))

        assert r.smoothed.urgency > 0.7

    def test_gradual_ramp_tracked(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))

        for i in range(10):
            r = cm.smooth(ExecutionContext(urgency=i / 9.0))

        assert r.smoothed.urgency > 0.7

    def test_all_signals_track_simultaneously(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0, risk_level=0.0, resource_pressure=0.0))

        for _ in range(15):
            r = cm.smooth(ExecutionContext(urgency=1.0, risk_level=1.0, resource_pressure=1.0))

        assert r.smoothed.urgency > 0.95
        assert r.smoothed.risk_level > 0.95
        assert r.smoothed.resource_pressure > 0.95


# ---------------------------------------------------------------------------
# Section 9: Reset conditions
# ---------------------------------------------------------------------------


class TestResetConditions:
    def test_reset_to_neutral(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        result = cm.reset()

        assert result.smoothed.is_neutral is True
        assert result.was_reset is True
        assert cm.previous_context.is_neutral is True

    def test_reset_to_specific(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        target = ExecutionContext(urgency=0.3, risk_level=0.7)
        result = cm.reset(to=target)

        assert result.smoothed.urgency == 0.3
        assert result.smoothed.risk_level == 0.7
        assert result.was_reset is True

    def test_reset_advances_tick(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext())
        assert cm.tick == 1
        cm.reset()
        assert cm.tick == 2

    def test_reset_clears_initialized(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        assert cm.initialized is True
        cm.reset()
        assert cm.initialized is False

    def test_reset_with_target_stays_initialized(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        cm.reset(to=ExecutionContext(urgency=0.3))
        assert cm.initialized is True

    def test_smooth_after_reset_passthrough(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        cm.reset()
        result = cm.smooth(ExecutionContext(urgency=0.7))
        assert result.smoothed.urgency == 0.7


# ---------------------------------------------------------------------------
# Section 10: Override behavior
# ---------------------------------------------------------------------------


class TestOverrideBehavior:
    def test_override_bypasses_smoothing(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.3)
        cm.smooth(ExecutionContext(urgency=0.0))
        result = cm.override(ExecutionContext(urgency=1.0))

        assert result.smoothed.urgency == 1.0

    def test_override_sets_previous(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.0))
        cm.override(ExecutionContext(urgency=0.8))

        assert cm.previous_context.urgency == 0.8

    def test_override_advances_tick(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.override(ExecutionContext())
        assert cm.tick == 1

    def test_override_sets_initialized(self) -> None:
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.context import ExecutionContext

        cm = ContextMemory()
        assert cm.initialized is False
        cm.override(ExecutionContext(urgency=0.5))
        assert cm.initialized is True

    def test_smooth_after_override_blends(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.override(ExecutionContext(urgency=0.0))
        result = cm.smooth(ExecutionContext(urgency=1.0))

        assert result.smoothed.urgency == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Section 11: set_alpha
# ---------------------------------------------------------------------------


class TestSetAlpha:
    def test_set_alpha(self) -> None:
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.set_alpha(0.7)
        assert cm.alpha == 0.7

    def test_set_alpha_clamped(self) -> None:
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.set_alpha(0.01)
        assert cm.alpha == 0.2
        cm.set_alpha(0.99)
        assert cm.alpha == 0.8

    def test_set_alpha_affects_next_smooth(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))

        cm.set_alpha(0.8)
        result = cm.smooth(ExecutionContext(urgency=1.0))
        assert result.smoothed.urgency == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Section 12: Bounds preservation
# ---------------------------------------------------------------------------


class TestBoundsPreservation:
    def test_all_values_in_range(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        signals = [0.0, 1.0, 0.0, 1.0, 0.5, 0.0, 1.0, 0.3, 0.9, 0.1]

        for u in signals:
            result = cm.smooth(ExecutionContext(urgency=u, risk_level=1.0 - u))
            assert 0.0 <= result.smoothed.urgency <= 1.0
            assert 0.0 <= result.smoothed.risk_level <= 1.0
            assert 0.0 <= result.smoothed.resource_pressure <= 1.0
            assert 0.0 <= result.smoothed.stability_mode <= 1.0

    def test_extreme_sequences_bounded(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.8)
        for _ in range(100):
            r = cm.smooth(ExecutionContext(urgency=1.0))
            assert r.smoothed.urgency <= 1.0

        for _ in range(100):
            r = cm.smooth(ExecutionContext(urgency=0.0))
            assert r.smoothed.urgency >= 0.0


# ---------------------------------------------------------------------------
# Section 13: make_context factory
# ---------------------------------------------------------------------------


class TestMakeContext:
    def test_defaults(self) -> None:
        from umh.runtime.context import make_context

        ctx = make_context()
        assert ctx.is_neutral is True

    def test_custom_values(self) -> None:
        from umh.runtime.context import make_context

        ctx = make_context(urgency=0.9, risk_level=0.1)
        assert ctx.urgency == 0.9
        assert ctx.risk_level == 0.1
        assert ctx.resource_pressure == 0.5
        assert ctx.stability_mode == 0.0

    def test_returns_frozen(self) -> None:
        from umh.runtime.context import make_context

        ctx = make_context(urgency=0.7)
        with pytest.raises(FrozenInstanceError):
            ctx.urgency = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Section 14: Integration with WeightAdapter
# ---------------------------------------------------------------------------


class TestWeightAdapterIntegration:
    def test_smoothed_context_feeds_adapter(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.5))

        result = cm.smooth(ExecutionContext(urgency=0.9))
        smoothed = result.smoothed

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        adapt_result = adapter.adjust(profile, smoothed)

        latency_adj = adapt_result.adjustments[0]
        assert latency_adj.multiplier > 1.0

    def test_smoothed_vs_raw_produces_different_weights(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        cm = ContextMemory(alpha=0.3)
        cm.smooth(ExecutionContext(urgency=0.2))
        result = cm.smooth(ExecutionContext(urgency=0.9))

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="speed", weight=1.0),))

        raw_adapt = adapter.adjust(profile, ExecutionContext(urgency=0.9))
        smoothed_adapt = adapter.adjust(profile, result.smoothed)

        assert raw_adapt.adjustments[0].multiplier > smoothed_adapt.adjustments[0].multiplier

    def test_pipeline_raw_smooth_adapt_resolve(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.5))
        result = cm.smooth(ExecutionContext(urgency=0.9))

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="quality", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {
            "fast": {"latency": 0.1, "quality": 0.4},
            "good": {"latency": 0.8, "quality": 0.9},
        }

        resolve_result = engine.resolve(candidates, context=result.smoothed)
        assert resolve_result is not None
        assert resolve_result.best.candidate_id in ("fast", "good")


# ---------------------------------------------------------------------------
# Section 15: Integration with TradeoffEngine
# ---------------------------------------------------------------------------


class TestTradeoffEngineIntegration:
    def test_smoothed_context_in_engine_resolve(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.5))
        smoothed = cm.smooth(ExecutionContext(urgency=1.0)).smoothed

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="safety", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {
            "fast": {"speed": 0.9, "safety": 0.3},
            "safe": {"speed": 0.3, "safety": 0.9},
        }

        result = engine.resolve(candidates, context=smoothed)
        assert result is not None

    def test_smoothing_changes_engine_winner(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="stability", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {
            "fast": {"speed": 0.9, "stability": 0.4},
            "stable": {"speed": 0.4, "stability": 0.9},
        }

        raw_ctx = ExecutionContext(urgency=1.0)
        raw_result = engine.resolve(candidates, context=raw_ctx)

        cm = ContextMemory(alpha=0.3)
        cm.smooth(ExecutionContext(urgency=0.2))
        smoothed = cm.smooth(ExecutionContext(urgency=1.0)).smoothed
        smoothed_result = engine.resolve(candidates, context=smoothed)

        assert raw_result is not None
        assert smoothed_result is not None
        assert raw_result.best.candidate_id == "fast"
        assert smoothed_result.best.candidate_id == "stable"


# ---------------------------------------------------------------------------
# Section 16: Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_sequence_same_output(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        def run_sequence() -> list[float]:
            cm = ContextMemory(alpha=0.4)
            results = []
            for u in [0.1, 0.9, 0.3, 0.7, 0.5, 0.8, 0.2]:
                r = cm.smooth(ExecutionContext(urgency=u))
                results.append(r.smoothed.urgency)
            return results

        r1 = run_sequence()
        r2 = run_sequence()
        for v1, v2 in zip(r1, r2):
            assert v1 == v2

    def test_smooth_value_deterministic(self) -> None:
        from umh.runtime.context_memory import smooth_value

        results = set()
        for _ in range(50):
            results.add(round(smooth_value(0.7, 0.3, 0.6), 15))
        assert len(results) == 1

    def test_smooth_context_deterministic(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import smooth_context

        c = ExecutionContext(urgency=0.8, risk_level=0.3)
        p = ExecutionContext(urgency=0.2, risk_level=0.7)
        results = [smooth_context(c, p, 0.5) for _ in range(10)]

        for r in results[1:]:
            assert r.urgency == results[0].urgency
            assert r.risk_level == results[0].risk_level


# ---------------------------------------------------------------------------
# Section 17: Hard invariants 131-135
# ---------------------------------------------------------------------------


class TestHardInvariants:
    def test_inv131_deterministic_smoothing(self) -> None:
        """Invariant 131: Context smoothing must be deterministic."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        sequence = [0.1, 0.9, 0.4, 0.6, 0.3, 0.8, 0.5, 0.7, 0.2, 0.9]
        all_results: list[list[float]] = []

        for _ in range(10):
            cm = ContextMemory(alpha=0.4)
            run_results = []
            for u in sequence:
                r = cm.smooth(ExecutionContext(urgency=u))
                run_results.append(round(r.smoothed.urgency, 12))
            all_results.append(run_results)

        for run in all_results[1:]:
            assert run == all_results[0]

    def test_inv132_no_external_state_mutation(self) -> None:
        """Invariant 132: No state mutation outside context memory module."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        raw = ExecutionContext(urgency=0.9, risk_level=0.1)
        cm = ContextMemory()

        raw_urgency_before = raw.urgency
        raw_risk_before = raw.risk_level
        cm.smooth(raw)

        assert raw.urgency == raw_urgency_before
        assert raw.risk_level == raw_risk_before

    def test_inv132_output_is_frozen(self) -> None:
        """Invariant 132: Output contexts are frozen."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        result = cm.smooth(ExecutionContext(urgency=0.8))

        with pytest.raises(FrozenInstanceError):
            result.smoothed.urgency = 0.0  # type: ignore[misc]

    def test_inv133_smoothing_bounded(self) -> None:
        """Invariant 133: Smoothing must be bounded [0, 1]."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.8)
        for val in [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]:
            r = cm.smooth(
                ExecutionContext(
                    urgency=val,
                    risk_level=1.0 - val,
                    resource_pressure=val,
                    stability_mode=1.0 - val,
                )
            )
            assert 0.0 <= r.smoothed.urgency <= 1.0
            assert 0.0 <= r.smoothed.risk_level <= 1.0
            assert 0.0 <= r.smoothed.resource_pressure <= 1.0
            assert 0.0 <= r.smoothed.stability_mode <= 1.0

    def test_inv133_alpha_bounded(self) -> None:
        """Invariant 133: Alpha bounded [0.2, 0.8]."""
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.0)
        assert 0.2 <= cm.alpha <= 0.8

        cm = ContextMemory(alpha=1.0)
        assert 0.2 <= cm.alpha <= 0.8

    def test_inv134_no_lag_instability(self) -> None:
        """Invariant 134: No lag-induced instability."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.5))

        for _ in range(5):
            cm.smooth(ExecutionContext(urgency=1.0))

        for _ in range(5):
            r = cm.smooth(ExecutionContext(urgency=0.0))

        assert r.smoothed.urgency < 0.5

        for _ in range(5):
            r = cm.smooth(ExecutionContext(urgency=1.0))

        assert r.smoothed.urgency > 0.5

    def test_inv134_no_overshoot(self) -> None:
        """Invariant 134: Smoothed value never overshoots target."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.8)
        cm.smooth(ExecutionContext(urgency=0.0))

        for _ in range(50):
            r = cm.smooth(ExecutionContext(urgency=0.7))
            assert r.smoothed.urgency <= 0.7 + 1e-9

    def test_inv135_neutral_stays_neutral(self) -> None:
        """Invariant 135: Neutral context must remain neutral."""
        from umh.runtime.context import NEUTRAL_CONTEXT, ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        for _ in range(10):
            r = cm.smooth(NEUTRAL_CONTEXT)

        assert r.smoothed.is_neutral is True

    def test_inv135_neutral_initial_with_neutral_input(self) -> None:
        """Invariant 135: Starting from neutral with neutral input stays neutral."""
        from umh.runtime.context import NEUTRAL_CONTEXT
        from umh.runtime.context_memory import ContextMemory, smooth_context

        result = smooth_context(NEUTRAL_CONTEXT, NEUTRAL_CONTEXT, 0.5)
        assert result.is_neutral is True


# ---------------------------------------------------------------------------
# Section 18: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_tick_memory(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        result = cm.smooth(ExecutionContext(urgency=0.7))
        assert cm.tick == 1
        assert result.smoothed.urgency == 0.7

    def test_reset_then_override(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        cm.reset()
        cm.override(ExecutionContext(urgency=0.3))
        assert cm.previous_context.urgency == 0.3
        assert cm.initialized is True

    def test_override_then_smooth(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.override(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.5)

    def test_many_resets(self) -> None:
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        for _ in range(100):
            cm.reset()
        assert cm.tick == 100
        assert cm.previous_context.is_neutral is True

    def test_alpha_at_min_boundary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.2)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.2)

    def test_alpha_at_max_boundary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.8)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.8)

    def test_stability_mode_smoothed_independently(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(stability_mode=0.0))
        r = cm.smooth(ExecutionContext(stability_mode=1.0))
        assert r.smoothed.stability_mode == pytest.approx(0.5)

    def test_result_contains_raw_and_smoothed(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))
        raw = ExecutionContext(urgency=1.0)
        r = cm.smooth(raw)

        assert r.raw.urgency == 1.0
        assert r.smoothed.urgency == pytest.approx(0.5)
        assert r.raw is not r.smoothed


# ---------------------------------------------------------------------------
# Section 19: No I/O verification
# ---------------------------------------------------------------------------


class TestNoIO:
    def test_context_memory_no_forbidden_imports(self) -> None:
        with open("/opt/OS/umh/runtime/context_memory.py") as f:
            source = f.read()
        tree = ast.parse(source)
        forbidden_modules = {"subprocess", "socket", "requests", "urllib", "http"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_modules, f"Forbidden: {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in forbidden_modules, f"Forbidden: {node.module}"

    def test_no_cells_environments_adapters_imports(self) -> None:
        with open("/opt/OS/umh/runtime/context_memory.py") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                if module:
                    assert not module.startswith("umh.cells"), f"Forbidden: {module}"
                    assert not module.startswith("umh.environments"), f"Forbidden: {module}"
                    assert not module.startswith("umh.adapters"), f"Forbidden: {module}"


# ---------------------------------------------------------------------------
# Section 20: Convergence analysis
# ---------------------------------------------------------------------------


class TestConvergence:
    def test_half_life_computation(self) -> None:
        """After n ticks of constant input, smoothed should be within expected range."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        alpha = 0.5
        cm = ContextMemory(alpha=alpha)
        cm.smooth(ExecutionContext(urgency=0.0))

        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.5)

        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.75)

        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.875)

    def test_steady_state_convergence(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))

        target = 0.6
        for _ in range(50):
            r = cm.smooth(ExecutionContext(urgency=target))

        assert abs(r.smoothed.urgency - target) < 1e-10

    def test_monotonic_approach_to_target(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))

        prev_gap = 1.0
        for _ in range(10):
            r = cm.smooth(ExecutionContext(urgency=1.0))
            gap = abs(r.smoothed.urgency - 1.0)
            assert gap < prev_gap
            prev_gap = gap


# ---------------------------------------------------------------------------
# Section 21: Full pipeline E2E
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_raw_smooth_adapt_resolve(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.5))
        smoothed = cm.smooth(ExecutionContext(urgency=0.9)).smoothed

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="safety", direction="maximize", weight=1.0),
            )
        )

        adapted, _ = apply_context_weights(profile, smoothed)
        engine = TradeoffEngine(profile=adapted)
        candidates = {
            "fast": {"latency": 0.1, "safety": 0.3},
            "safe": {"latency": 0.9, "safety": 0.9},
        }
        result = engine.resolve(candidates)

        assert result is not None
        assert result.best.candidate_id in ("fast", "safe")

    def test_full_pipeline_with_engine_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.5))
        smoothed = cm.smooth(ExecutionContext(urgency=1.0)).smoothed

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="cost", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {"cheap": {"speed": 0.3, "cost": 0.9}, "fast": {"speed": 0.9, "cost": 0.3}}
        result = engine.resolve(candidates, context=smoothed)

        assert result is not None


# ---------------------------------------------------------------------------
# Section 22: Exports and compilation
# ---------------------------------------------------------------------------


class TestExportsAndCompilation:
    def test_runtime_exports_context_memory(self) -> None:
        from umh.runtime import ContextMemory, SmoothingResult, smooth_context, smooth_value

        assert ContextMemory is not None
        assert SmoothingResult is not None
        assert smooth_context is not None
        assert smooth_value is not None

    def test_runtime_exports_make_context(self) -> None:
        from umh.runtime import make_context

        assert make_context is not None

    def test_context_memory_py_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/context_memory.py", doraise=True)

    def test_context_py_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/context.py", doraise=True)

    def test_init_py_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_all_exports_in_all_list(self) -> None:
        import umh.runtime as rt

        expected = [
            "ContextMemory",
            "SmoothingResult",
            "make_context",
            "smooth_context",
            "smooth_value",
        ]
        for name in expected:
            assert name in rt.__all__, f"{name} not in __all__"


# ---------------------------------------------------------------------------
# Section 23: Additional smooth_value coverage
# ---------------------------------------------------------------------------


class TestSmoothValueAdditional:
    def test_asymmetric_blend(self) -> None:
        from umh.runtime.context_memory import smooth_value

        assert smooth_value(0.9, 0.1, 0.7) == pytest.approx(0.7 * 0.9 + 0.3 * 0.1)

    def test_zero_current(self) -> None:
        from umh.runtime.context_memory import smooth_value

        result = smooth_value(0.0, 0.6, 0.5)
        assert result == pytest.approx(0.3)

    def test_zero_previous(self) -> None:
        from umh.runtime.context_memory import smooth_value

        result = smooth_value(0.6, 0.0, 0.5)
        assert result == pytest.approx(0.3)

    def test_both_at_one(self) -> None:
        from umh.runtime.context_memory import smooth_value

        assert smooth_value(1.0, 1.0, 0.3) == pytest.approx(1.0)

    def test_both_at_zero(self) -> None:
        from umh.runtime.context_memory import smooth_value

        assert smooth_value(0.0, 0.0, 0.7) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Section 24: Additional ContextMemory behavior
# ---------------------------------------------------------------------------


class TestContextMemoryBehavior:
    def test_multiple_smooth_calls_accumulate(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))
        r1 = cm.smooth(ExecutionContext(urgency=1.0))
        r2 = cm.smooth(ExecutionContext(urgency=1.0))
        r3 = cm.smooth(ExecutionContext(urgency=1.0))

        assert r1.smoothed.urgency < r2.smoothed.urgency < r3.smoothed.urgency

    def test_previous_context_updated_after_smooth(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert cm.previous_context.urgency == r.smoothed.urgency

    def test_result_previous_field_is_pre_smooth(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.3))
        r = cm.smooth(ExecutionContext(urgency=0.9))
        assert r.previous.urgency == pytest.approx(0.3)

    def test_reset_returns_previous_state(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.8))
        r = cm.reset()
        assert r.previous.urgency == pytest.approx(0.8)

    def test_override_returns_previous_state(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.6))
        r = cm.override(ExecutionContext(urgency=0.3))
        assert r.previous.urgency == pytest.approx(0.6)

    def test_smooth_preserves_risk_and_pressure(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(risk_level=0.0, resource_pressure=1.0))
        r = cm.smooth(ExecutionContext(risk_level=1.0, resource_pressure=0.0))
        assert r.smoothed.risk_level == pytest.approx(0.5)
        assert r.smoothed.resource_pressure == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Section 25: Alpha sensitivity analysis
# ---------------------------------------------------------------------------


class TestAlphaSensitivity:
    def test_alpha_02_very_sluggish(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.2)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.2)

    def test_alpha_08_very_responsive(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.8)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.8)

    def test_alpha_05_balanced(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.5)

    def test_lower_alpha_smoother_oscillation(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        def oscillation_spread(alpha: float) -> float:
            cm = ContextMemory(alpha=alpha)
            cm.smooth(ExecutionContext(urgency=0.5))
            vals = []
            for i in range(20):
                u = 1.0 if i % 2 == 0 else 0.0
                r = cm.smooth(ExecutionContext(urgency=u))
                vals.append(r.smoothed.urgency)
            return max(vals[-6:]) - min(vals[-6:])

        spread_low = oscillation_spread(0.2)
        spread_high = oscillation_spread(0.8)
        assert spread_low < spread_high


# ---------------------------------------------------------------------------
# Section 26: Multi-signal smoothing
# ---------------------------------------------------------------------------


class TestMultiSignalSmoothing:
    def test_all_four_signals_independent(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(
            ExecutionContext(urgency=0.0, risk_level=1.0, resource_pressure=0.0, stability_mode=1.0)
        )
        r = cm.smooth(
            ExecutionContext(urgency=1.0, risk_level=0.0, resource_pressure=1.0, stability_mode=0.0)
        )

        assert r.smoothed.urgency == pytest.approx(0.5)
        assert r.smoothed.risk_level == pytest.approx(0.5)
        assert r.smoothed.resource_pressure == pytest.approx(0.5)
        assert r.smoothed.stability_mode == pytest.approx(0.5)

    def test_selective_signal_change(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        base = ExecutionContext(
            urgency=0.5, risk_level=0.5, resource_pressure=0.5, stability_mode=0.5
        )
        cm.smooth(base)

        changed = ExecutionContext(
            urgency=1.0, risk_level=0.5, resource_pressure=0.5, stability_mode=0.5
        )
        r = cm.smooth(changed)

        assert r.smoothed.urgency == pytest.approx(0.75)
        assert r.smoothed.risk_level == pytest.approx(0.5)
        assert r.smoothed.resource_pressure == pytest.approx(0.5)
        assert r.smoothed.stability_mode == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Section 27: Regression — Phase 38 unchanged
# ---------------------------------------------------------------------------


class TestPhase38Regression:
    def test_execution_context_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(urgency=0.9)
        assert ctx.urgency == 0.9
        assert ctx.is_neutral is False

    def test_neutral_context_unchanged(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT

        assert NEUTRAL_CONTEXT.is_neutral is True
        assert NEUTRAL_CONTEXT.urgency == 0.5

    def test_weight_adapter_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert result.adjustments[0].multiplier > 1.0

    def test_apply_context_weights_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(
            dimensions=(TradeoffDimension(name="speed", weight=1.0),), name="test"
        )
        ctx = ExecutionContext(urgency=0.9)
        adjusted, result = apply_context_weights(profile, ctx)
        assert adjusted.name == "test_adapted"
        assert result.any_changed is True

    def test_tradeoff_engine_with_context_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="quality", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {
            "fast": {"latency": 0.1, "quality": 0.4},
            "good": {"latency": 0.8, "quality": 0.9},
        }
        ctx = ExecutionContext(urgency=1.0)
        result = engine.resolve(candidates, context=ctx)
        assert result is not None
        assert result.best.candidate_id == "fast"


# ---------------------------------------------------------------------------
# Section 28: Additional invariant verification
# ---------------------------------------------------------------------------


class TestAdditionalInvariants:
    def test_smoothed_output_always_valid_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        for u in [0.0, 1.0, 0.3, 0.8, 0.5, 0.0, 1.0, 0.2]:
            r = cm.smooth(ExecutionContext(urgency=u, risk_level=1.0 - u))
            d = r.smoothed.to_dict()
            for key in ("urgency", "risk_level", "resource_pressure", "stability_mode"):
                assert 0.0 <= d[key] <= 1.0

    def test_reset_output_always_valid(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        r = cm.reset()
        assert 0.0 <= r.smoothed.urgency <= 1.0

    def test_override_output_always_valid(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r = cm.override(ExecutionContext(urgency=0.7, risk_level=0.3))
        assert 0.0 <= r.smoothed.urgency <= 1.0
        assert 0.0 <= r.smoothed.risk_level <= 1.0

    def test_tick_monotonically_increases(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        ticks = []
        cm.smooth(ExecutionContext())
        ticks.append(cm.tick)
        cm.smooth(ExecutionContext())
        ticks.append(cm.tick)
        cm.reset()
        ticks.append(cm.tick)
        cm.override(ExecutionContext())
        ticks.append(cm.tick)

        for i in range(1, len(ticks)):
            assert ticks[i] > ticks[i - 1]

    def test_smoothing_result_to_dict_serializable(self) -> None:
        import json

        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r = cm.smooth(ExecutionContext(urgency=0.8))
        d = r.to_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_context_memory_to_dict_serializable(self) -> None:
        import json

        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.4)
        cm.smooth(ExecutionContext(urgency=0.7))
        d = cm.to_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)
