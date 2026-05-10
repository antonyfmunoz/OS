"""Phase 41 — Multi-Horizon Temporal Context Layer v1.

Tests for:
  - HorizonValue (creation, frozen, to_dict, delta)
  - HorizonSnapshot (creation, frozen, accessors, to_dict)
  - HorizonAlphas (creation, frozen, to_dict)
  - compute_horizon_value (dual EMA, bounds, alpha constraint)
  - compute_all_horizon_values (all signals, custom alphas)
  - HorizonResult (creation, frozen, to_dict)
  - HorizonMemory (first tick, multi tick, reset, override)
  - Fast reacts quicker than slow
  - Slow stabilizes over time
  - Delta behavior (spike, drop, stable)
  - Sustained change aligns both horizons
  - Multi-tick convergence
  - Cross-signal independence
  - ContextMemory.smooth_horizon integration
  - Determinism
  - Hard invariants 141-145
  - Boundary conditions
  - Serialization
  - Edge cases
  - Dependency boundary
  - Exports and compilation
  - Phase 40 regression
"""

from __future__ import annotations

import ast
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Section 1: HorizonValue creation
# ---------------------------------------------------------------------------


class TestHorizonValueCreation:
    def test_basic_creation(self) -> None:
        from umh.runtime.horizon import HorizonValue

        hv = HorizonValue(signal_name="urgency", fast=0.7, slow=0.3, delta=0.4)
        assert hv.signal_name == "urgency"
        assert hv.fast == 0.7
        assert hv.slow == 0.3
        assert hv.delta == 0.4

    def test_frozen(self) -> None:
        from umh.runtime.horizon import HorizonValue

        hv = HorizonValue(signal_name="x", fast=0.5, slow=0.5, delta=0.0)
        with pytest.raises(FrozenInstanceError):
            hv.fast = 0.9  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.horizon import HorizonValue

        hv = HorizonValue(signal_name="urgency", fast=0.7123, slow=0.3456, delta=0.3667)
        d = hv.to_dict()
        assert d["signal_name"] == "urgency"
        assert d["fast"] == 0.7123
        assert d["slow"] == 0.3456
        assert d["delta"] == 0.3667

    def test_zero_delta(self) -> None:
        from umh.runtime.horizon import HorizonValue

        hv = HorizonValue(signal_name="x", fast=0.5, slow=0.5, delta=0.0)
        assert hv.delta == 0.0

    def test_negative_delta(self) -> None:
        from umh.runtime.horizon import HorizonValue

        hv = HorizonValue(signal_name="x", fast=0.3, slow=0.7, delta=-0.4)
        assert hv.delta == -0.4


# ---------------------------------------------------------------------------
# Section 2: HorizonSnapshot
# ---------------------------------------------------------------------------


class TestHorizonSnapshot:
    def test_creation(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot, HorizonValue

        values = {
            "urgency": HorizonValue(signal_name="urgency", fast=0.7, slow=0.3, delta=0.4),
        }
        snap = HorizonSnapshot(values=values, tick=1)
        assert snap.tick == 1
        assert "urgency" in snap.values

    def test_frozen(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot

        snap = HorizonSnapshot(values={}, tick=0)
        with pytest.raises(FrozenInstanceError):
            snap.tick = 5  # type: ignore[misc]

    def test_get_existing(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot, HorizonValue

        hv = HorizonValue(signal_name="urgency", fast=0.8, slow=0.4, delta=0.4)
        snap = HorizonSnapshot(values={"urgency": hv}, tick=1)
        assert snap.get("urgency") is hv

    def test_get_missing(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot

        snap = HorizonSnapshot(values={}, tick=1)
        assert snap.get("nonexistent") is None

    def test_get_delta(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot, HorizonValue

        hv = HorizonValue(signal_name="urgency", fast=0.8, slow=0.3, delta=0.5)
        snap = HorizonSnapshot(values={"urgency": hv}, tick=1)
        assert snap.get_delta("urgency") == 0.5

    def test_get_delta_missing(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot

        snap = HorizonSnapshot(values={}, tick=1)
        assert snap.get_delta("missing") == 0.0

    def test_get_fast(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot, HorizonValue

        hv = HorizonValue(signal_name="urgency", fast=0.9, slow=0.2, delta=0.7)
        snap = HorizonSnapshot(values={"urgency": hv}, tick=1)
        assert snap.get_fast("urgency") == 0.9

    def test_get_fast_missing(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot

        snap = HorizonSnapshot(values={}, tick=1)
        assert snap.get_fast("missing") == 0.5

    def test_get_slow(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot, HorizonValue

        hv = HorizonValue(signal_name="urgency", fast=0.9, slow=0.2, delta=0.7)
        snap = HorizonSnapshot(values={"urgency": hv}, tick=1)
        assert snap.get_slow("urgency") == 0.2

    def test_get_slow_missing(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot

        snap = HorizonSnapshot(values={}, tick=1)
        assert snap.get_slow("missing") == 0.5

    def test_to_dict(self) -> None:
        from umh.runtime.horizon import HorizonSnapshot, HorizonValue

        values = {
            "urgency": HorizonValue(signal_name="urgency", fast=0.7, slow=0.3, delta=0.4),
            "risk_level": HorizonValue(signal_name="risk_level", fast=0.5, slow=0.5, delta=0.0),
        }
        snap = HorizonSnapshot(values=values, tick=5)
        d = snap.to_dict()
        assert d["tick"] == 5
        assert "urgency" in d["values"]
        assert "risk_level" in d["values"]


# ---------------------------------------------------------------------------
# Section 3: HorizonAlphas
# ---------------------------------------------------------------------------


class TestHorizonAlphas:
    def test_creation(self) -> None:
        from umh.runtime.horizon import HorizonAlphas

        ha = HorizonAlphas(signal_name="urgency", fast_alpha=0.7, slow_alpha=0.3)
        assert ha.signal_name == "urgency"
        assert ha.fast_alpha == 0.7
        assert ha.slow_alpha == 0.3

    def test_frozen(self) -> None:
        from umh.runtime.horizon import HorizonAlphas

        ha = HorizonAlphas(signal_name="x", fast_alpha=0.5, slow_alpha=0.3)
        with pytest.raises(FrozenInstanceError):
            ha.fast_alpha = 0.9  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.horizon import HorizonAlphas

        ha = HorizonAlphas(signal_name="urgency", fast_alpha=0.7, slow_alpha=0.3)
        d = ha.to_dict()
        assert d["signal_name"] == "urgency"
        assert d["fast_alpha"] == 0.7
        assert d["slow_alpha"] == 0.3


# ---------------------------------------------------------------------------
# Section 4: compute_horizon_value — dual EMA formula
# ---------------------------------------------------------------------------


class TestComputeHorizonValue:
    def test_basic_computation(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("urgency", 1.0, 0.0, 0.0, 0.7, 0.3)
        assert hv.fast == pytest.approx(0.7)
        assert hv.slow == pytest.approx(0.3)
        assert hv.delta == pytest.approx(0.4)

    def test_fast_higher_than_slow_for_step_up(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 1.0, 0.0, 0.0, 0.7, 0.3)
        assert hv.fast > hv.slow

    def test_fast_lower_than_slow_for_step_down(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 0.0, 1.0, 1.0, 0.7, 0.3)
        assert hv.fast < hv.slow

    def test_outputs_bounded_01(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 1.0, 1.0, 1.0, 0.8, 0.2)
        assert 0.0 <= hv.fast <= 1.0
        assert 0.0 <= hv.slow <= 1.0

    def test_delta_bounded(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 1.0, 0.0, 1.0, 0.8, 0.2)
        assert -1.0 <= hv.delta <= 1.0

    def test_alpha_clamped(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 1.0, 0.0, 0.0, 0.05, 0.01)
        assert hv.fast >= 0.0
        assert hv.slow >= 0.0

    def test_fast_alpha_enforced_above_slow(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 1.0, 0.0, 0.0, 0.3, 0.3)
        assert hv.fast > hv.slow

    def test_identical_inputs_no_change(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 0.5, 0.5, 0.5, 0.7, 0.3)
        assert hv.fast == pytest.approx(0.5)
        assert hv.slow == pytest.approx(0.5)
        assert hv.delta == pytest.approx(0.0)

    def test_formula_exact_fast(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 0.8, 0.2, 0.2, 0.6, 0.3)
        expected_fast = 0.6 * 0.8 + 0.4 * 0.2
        assert hv.fast == pytest.approx(expected_fast)

    def test_formula_exact_slow(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("x", 0.8, 0.2, 0.2, 0.6, 0.3)
        expected_slow = 0.3 * 0.8 + 0.7 * 0.2
        assert hv.slow == pytest.approx(expected_slow)


# ---------------------------------------------------------------------------
# Section 5: compute_all_horizon_values
# ---------------------------------------------------------------------------


class TestComputeAllHorizonValues:
    def test_computes_all_four_signals(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import compute_all_horizon_values

        current = ExecutionContext(urgency=0.8)
        prev_fast = ExecutionContext(urgency=0.0)
        prev_slow = ExecutionContext(urgency=0.0)
        snap = compute_all_horizon_values(current, prev_fast, prev_slow)
        assert len(snap.values) == 4
        for name in ("urgency", "risk_level", "resource_pressure", "stability_mode"):
            assert name in snap.values

    def test_custom_alphas(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonAlphas, compute_all_horizon_values

        alphas = {
            "urgency": HorizonAlphas(signal_name="urgency", fast_alpha=0.8, slow_alpha=0.2),
            "risk_level": HorizonAlphas(signal_name="risk_level", fast_alpha=0.8, slow_alpha=0.2),
            "resource_pressure": HorizonAlphas(
                signal_name="resource_pressure", fast_alpha=0.8, slow_alpha=0.2
            ),
            "stability_mode": HorizonAlphas(
                signal_name="stability_mode", fast_alpha=0.8, slow_alpha=0.2
            ),
        }
        current = ExecutionContext(urgency=1.0)
        prev_f = ExecutionContext(urgency=0.0)
        prev_s = ExecutionContext(urgency=0.0)
        snap = compute_all_horizon_values(current, prev_f, prev_s, alphas)
        assert snap.get_fast("urgency") == pytest.approx(0.8)
        assert snap.get_slow("urgency") == pytest.approx(0.2)

    def test_tick_recorded(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import compute_all_horizon_values

        snap = compute_all_horizon_values(
            ExecutionContext(), ExecutionContext(), ExecutionContext(), tick=42
        )
        assert snap.tick == 42

    def test_default_alphas_used_when_none(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import compute_all_horizon_values

        snap = compute_all_horizon_values(
            ExecutionContext(urgency=1.0),
            ExecutionContext(urgency=0.0),
            ExecutionContext(urgency=0.0),
            alphas=None,
        )
        assert snap.get_fast("urgency") == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# Section 6: HorizonResult
# ---------------------------------------------------------------------------


class TestHorizonResult:
    def test_creation(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonResult, HorizonSnapshot

        snap = HorizonSnapshot(values={}, tick=1)
        hr = HorizonResult(
            snapshot=snap,
            fast_context=ExecutionContext(),
            slow_context=ExecutionContext(),
            raw=ExecutionContext(),
            tick=1,
            was_reset=False,
        )
        assert hr.tick == 1
        assert hr.was_reset is False

    def test_frozen(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonResult, HorizonSnapshot

        snap = HorizonSnapshot(values={}, tick=1)
        hr = HorizonResult(
            snapshot=snap,
            fast_context=ExecutionContext(),
            slow_context=ExecutionContext(),
            raw=ExecutionContext(),
            tick=1,
            was_reset=False,
        )
        with pytest.raises(FrozenInstanceError):
            hr.tick = 5  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonResult, HorizonSnapshot

        snap = HorizonSnapshot(values={}, tick=1)
        hr = HorizonResult(
            snapshot=snap,
            fast_context=ExecutionContext(),
            slow_context=ExecutionContext(),
            raw=ExecutionContext(),
            tick=1,
            was_reset=False,
        )
        d = hr.to_dict()
        assert "snapshot" in d
        assert "fast_context" in d
        assert "slow_context" in d
        assert "raw" in d


# ---------------------------------------------------------------------------
# Section 7: HorizonMemory — first tick passthrough
# ---------------------------------------------------------------------------


class TestHorizonMemoryFirstTick:
    def test_first_tick_passthrough(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        r = hm.smooth(ExecutionContext(urgency=0.9))
        assert r.fast_context.urgency == pytest.approx(0.9)
        assert r.slow_context.urgency == pytest.approx(0.9)

    def test_first_tick_delta_zero(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        r = hm.smooth(ExecutionContext(urgency=0.9))
        assert r.snapshot.get_delta("urgency") == pytest.approx(0.0)

    def test_first_tick_initialized(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        assert hm.initialized is False
        hm.smooth(ExecutionContext())
        assert hm.initialized is True

    def test_first_tick_all_signals_passthrough(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        ctx = ExecutionContext(
            urgency=0.1, risk_level=0.2, resource_pressure=0.3, stability_mode=0.4
        )
        r = hm.smooth(ctx)
        for name in ("urgency", "risk_level", "resource_pressure", "stability_mode"):
            assert r.snapshot.get_fast(name) == pytest.approx(getattr(ctx, name))
            assert r.snapshot.get_slow(name) == pytest.approx(getattr(ctx, name))

    def test_with_initial_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        initial = ExecutionContext(urgency=0.3)
        hm = HorizonMemory(initial=initial)
        assert hm.initialized is True
        r = hm.smooth(ExecutionContext(urgency=0.9))
        assert r.fast_context.urgency != pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Section 8: HorizonMemory — multi tick
# ---------------------------------------------------------------------------


class TestHorizonMemoryMultiTick:
    def test_second_tick_applies_ema(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0))
        r = hm.smooth(ExecutionContext(urgency=1.0))
        assert r.fast_context.urgency > r.slow_context.urgency

    def test_tick_increments(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        r1 = hm.smooth(ExecutionContext())
        r2 = hm.smooth(ExecutionContext())
        r3 = hm.smooth(ExecutionContext())
        assert r1.tick == 1
        assert r2.tick == 2
        assert r3.tick == 3

    def test_snapshot_tick_matches_result_tick(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        r = hm.smooth(ExecutionContext())
        assert r.snapshot.tick == r.tick

    def test_previous_state_updates(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0))
        hm.smooth(ExecutionContext(urgency=1.0))
        assert hm.prev_fast.urgency > 0.0
        assert hm.prev_slow.urgency > 0.0


# ---------------------------------------------------------------------------
# Section 9: HorizonMemory — reset
# ---------------------------------------------------------------------------


class TestHorizonMemoryReset:
    def test_reset_to_neutral(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.9))
        r = hm.reset()
        assert r.was_reset is True
        assert r.fast_context.is_neutral is True
        assert r.slow_context.is_neutral is True

    def test_reset_to_specific(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.9))
        target = ExecutionContext(urgency=0.3)
        r = hm.reset(to=target)
        assert r.fast_context.urgency == pytest.approx(0.3)
        assert r.slow_context.urgency == pytest.approx(0.3)

    def test_reset_delta_zero(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.9))
        r = hm.reset()
        for name in ("urgency", "risk_level", "resource_pressure", "stability_mode"):
            assert r.snapshot.get_delta(name) == pytest.approx(0.0)

    def test_reset_clears_initialized_when_no_target(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext())
        assert hm.initialized is True
        hm.reset()
        assert hm.initialized is False

    def test_reset_preserves_initialized_when_target(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext())
        hm.reset(to=ExecutionContext(urgency=0.5))
        assert hm.initialized is True


# ---------------------------------------------------------------------------
# Section 10: HorizonMemory — override
# ---------------------------------------------------------------------------


class TestHorizonMemoryOverride:
    def test_override_sets_both_horizons(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        ctx = ExecutionContext(urgency=0.7)
        r = hm.override(ctx)
        assert r.fast_context.urgency == pytest.approx(0.7)
        assert r.slow_context.urgency == pytest.approx(0.7)

    def test_override_delta_zero(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        r = hm.override(ExecutionContext(urgency=0.7))
        assert r.snapshot.get_delta("urgency") == pytest.approx(0.0)

    def test_override_sets_initialized(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        assert hm.initialized is False
        hm.override(ExecutionContext())
        assert hm.initialized is True

    def test_override_was_reset_false(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        r = hm.override(ExecutionContext())
        assert r.was_reset is False


# ---------------------------------------------------------------------------
# Section 11: Fast reacts quicker than slow
# ---------------------------------------------------------------------------


class TestFastReactsQuicker:
    def test_step_up_fast_closer_to_target(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0))
        r = hm.smooth(ExecutionContext(urgency=1.0))
        fast_err = abs(r.fast_context.urgency - 1.0)
        slow_err = abs(r.slow_context.urgency - 1.0)
        assert fast_err < slow_err

    def test_step_down_fast_closer_to_target(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=1.0))
        r = hm.smooth(ExecutionContext(urgency=0.0))
        fast_err = abs(r.fast_context.urgency - 0.0)
        slow_err = abs(r.slow_context.urgency - 0.0)
        assert fast_err < slow_err

    def test_fast_converges_faster_over_ticks(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0))
        for _ in range(3):
            r = hm.smooth(ExecutionContext(urgency=1.0))
        fast_err = abs(r.fast_context.urgency - 1.0)
        slow_err = abs(r.slow_context.urgency - 1.0)
        assert fast_err < slow_err

    def test_all_signals_fast_closer_for_step(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0, risk_level=0.0, resource_pressure=0.0))
        target = ExecutionContext(urgency=1.0, risk_level=1.0, resource_pressure=1.0)
        r = hm.smooth(target)
        for name in ("urgency", "risk_level", "resource_pressure"):
            fast = getattr(r.fast_context, name)
            slow = getattr(r.slow_context, name)
            assert abs(fast - 1.0) < abs(slow - 1.0)


# ---------------------------------------------------------------------------
# Section 12: Slow stabilizes over time
# ---------------------------------------------------------------------------


class TestSlowStabilizes:
    def test_slow_converges_to_constant(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        target = ExecutionContext(urgency=0.7)
        for _ in range(30):
            r = hm.smooth(target)
        assert r.slow_context.urgency == pytest.approx(0.7, abs=0.01)

    def test_slow_less_variance_on_oscillation(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.5))
        fast_vals = []
        slow_vals = []
        for i in range(20):
            raw = ExecutionContext(urgency=0.0 if i % 2 == 0 else 1.0)
            r = hm.smooth(raw)
            fast_vals.append(r.fast_context.urgency)
            slow_vals.append(r.slow_context.urgency)
        fast_var = sum((v - 0.5) ** 2 for v in fast_vals) / len(fast_vals)
        slow_var = sum((v - 0.5) ** 2 for v in slow_vals) / len(slow_vals)
        assert slow_var < fast_var

    def test_slow_dampens_noise(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(risk_level=0.5))
        for _ in range(10):
            hm.smooth(ExecutionContext(risk_level=0.5))
        r = hm.smooth(ExecutionContext(risk_level=0.9))
        assert r.slow_context.risk_level < r.fast_context.risk_level


# ---------------------------------------------------------------------------
# Section 13: Delta behavior
# ---------------------------------------------------------------------------


class TestDeltaBehavior:
    def test_spike_produces_positive_delta(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.3))
        r = hm.smooth(ExecutionContext(urgency=0.9))
        assert r.snapshot.get_delta("urgency") > 0

    def test_drop_produces_negative_delta(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.9))
        r = hm.smooth(ExecutionContext(urgency=0.1))
        assert r.snapshot.get_delta("urgency") < 0

    def test_stable_input_produces_near_zero_delta(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for _ in range(20):
            r = hm.smooth(ExecutionContext(urgency=0.5))
        assert abs(r.snapshot.get_delta("urgency")) < 0.01

    def test_delta_shrinks_after_sustained_input(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0))
        r1 = hm.smooth(ExecutionContext(urgency=1.0))
        for _ in range(5):
            r2 = hm.smooth(ExecutionContext(urgency=1.0))
        assert abs(r2.snapshot.get_delta("urgency")) < abs(r1.snapshot.get_delta("urgency"))

    def test_delta_equals_fast_minus_slow(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.2))
        r = hm.smooth(ExecutionContext(urgency=0.8))
        hv = r.snapshot.get("urgency")
        assert hv is not None
        assert hv.delta == pytest.approx(hv.fast - hv.slow)


# ---------------------------------------------------------------------------
# Section 14: Sustained change aligns both horizons
# ---------------------------------------------------------------------------


class TestSustainedChangeAlignment:
    def test_both_converge_to_same_target(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        target = ExecutionContext(urgency=0.8, risk_level=0.3)
        for _ in range(30):
            r = hm.smooth(target)
        assert r.fast_context.urgency == pytest.approx(0.8, abs=0.01)
        assert r.slow_context.urgency == pytest.approx(0.8, abs=0.01)
        assert r.fast_context.risk_level == pytest.approx(0.3, abs=0.01)
        assert r.slow_context.risk_level == pytest.approx(0.3, abs=0.01)

    def test_delta_near_zero_after_convergence(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for _ in range(30):
            r = hm.smooth(ExecutionContext(urgency=0.6))
        assert abs(r.snapshot.get_delta("urgency")) < 0.01

    def test_all_signals_converge(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        target = ExecutionContext(
            urgency=0.7, risk_level=0.2, resource_pressure=0.8, stability_mode=0.4
        )
        for _ in range(30):
            r = hm.smooth(target)
        for name in ("urgency", "risk_level", "resource_pressure", "stability_mode"):
            assert getattr(r.fast_context, name) == pytest.approx(getattr(target, name), abs=0.01)
            assert getattr(r.slow_context, name) == pytest.approx(getattr(target, name), abs=0.01)


# ---------------------------------------------------------------------------
# Section 15: Cross-signal independence
# ---------------------------------------------------------------------------


class TestCrossSignalIndependence:
    def test_changing_one_signal_doesnt_affect_others(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.5, risk_level=0.5))

        hm2 = HorizonMemory()
        hm2.smooth(ExecutionContext(urgency=0.5, risk_level=0.5))

        hm.smooth(ExecutionContext(urgency=0.9, risk_level=0.5))
        r2 = hm2.smooth(ExecutionContext(urgency=0.5, risk_level=0.5))
        r1 = hm.smooth(ExecutionContext(urgency=0.5, risk_level=0.5))

        assert r1.fast_context.risk_level == pytest.approx(r2.fast_context.risk_level, abs=0.01)

    def test_independent_delta_per_signal(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0, risk_level=0.5))
        r = hm.smooth(ExecutionContext(urgency=1.0, risk_level=0.5))
        assert abs(r.snapshot.get_delta("urgency")) > abs(r.snapshot.get_delta("risk_level"))


# ---------------------------------------------------------------------------
# Section 16: ContextMemory.smooth_horizon integration
# ---------------------------------------------------------------------------


class TestContextMemorySmoothHorizon:
    def test_basic_integration(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        result, snapshot = cm.smooth_horizon(ExecutionContext(urgency=0.8))
        assert result.smoothed.urgency == pytest.approx(0.8)
        assert snapshot.get_delta("urgency") == pytest.approx(0.0)

    def test_second_tick_applies_horizon(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_horizon(ExecutionContext(urgency=0.0))
        result, snapshot = cm.smooth_horizon(ExecutionContext(urgency=1.0))
        assert result.smoothed.urgency > 0.0
        assert result.smoothed.urgency < 1.0
        assert snapshot.get_delta("urgency") > 0

    def test_tick_increments(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r1, _ = cm.smooth_horizon(ExecutionContext())
        r2, _ = cm.smooth_horizon(ExecutionContext())
        assert r1.tick == 1
        assert r2.tick == 2

    def test_smoothed_uses_fast_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_horizon(ExecutionContext(urgency=0.0))
        r, snap = cm.smooth_horizon(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(snap.get_fast("urgency"))

    def test_result_alpha_is_zero(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r, _ = cm.smooth_horizon(ExecutionContext())
        assert r.alpha == 0.0

    def test_result_was_reset_false(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r, _ = cm.smooth_horizon(ExecutionContext())
        assert r.was_reset is False

    def test_horizon_after_reset(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_horizon(ExecutionContext(urgency=0.9))
        cm.reset()
        r, snap = cm.smooth_horizon(ExecutionContext(urgency=0.3))
        assert r.smoothed.urgency == pytest.approx(0.3)
        assert snap.get_delta("urgency") == pytest.approx(0.0)

    def test_mixed_smooth_and_horizon(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.5))
        r, snap = cm.smooth_horizon(ExecutionContext(urgency=0.8))
        assert r.tick == 2
        assert snap.tick > 0


# ---------------------------------------------------------------------------
# Section 17: Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_inputs_same_outputs(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        results = []
        for _ in range(3):
            hm = HorizonMemory()
            hm.smooth(ExecutionContext(urgency=0.2))
            r = hm.smooth(ExecutionContext(urgency=0.8))
            results.append(r.fast_context.urgency)
        assert results[0] == results[1] == results[2]

    def test_deterministic_delta(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        deltas = []
        for _ in range(3):
            hm = HorizonMemory()
            hm.smooth(ExecutionContext(urgency=0.0))
            r = hm.smooth(ExecutionContext(urgency=1.0))
            deltas.append(r.snapshot.get_delta("urgency"))
        assert deltas[0] == deltas[1] == deltas[2]

    def test_deterministic_multi_tick(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        results = []
        for _ in range(2):
            hm = HorizonMemory()
            for i in range(10):
                r = hm.smooth(ExecutionContext(urgency=i / 10.0))
            results.append((r.fast_context.urgency, r.slow_context.urgency))
        assert results[0] == results[1]


# ---------------------------------------------------------------------------
# Section 18: Hard invariants 141-145
# ---------------------------------------------------------------------------


class TestHardInvariants:
    def test_inv141_fast_slow_independent(self) -> None:
        """Fast and slow EMA are independent — changing fast_alpha
        doesn't change slow result and vice versa."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonAlphas, HorizonMemory

        alphas_a = {
            name: HorizonAlphas(signal_name=name, fast_alpha=0.8, slow_alpha=0.3)
            for name in ("urgency", "risk_level", "resource_pressure", "stability_mode")
        }
        alphas_b = {
            name: HorizonAlphas(signal_name=name, fast_alpha=0.5, slow_alpha=0.3)
            for name in ("urgency", "risk_level", "resource_pressure", "stability_mode")
        }
        hm_a = HorizonMemory(alphas=alphas_a)
        hm_b = HorizonMemory(alphas=alphas_b)
        hm_a.smooth(ExecutionContext(urgency=0.0))
        hm_b.smooth(ExecutionContext(urgency=0.0))
        ra = hm_a.smooth(ExecutionContext(urgency=1.0))
        rb = hm_b.smooth(ExecutionContext(urgency=1.0))
        assert ra.slow_context.urgency == pytest.approx(rb.slow_context.urgency)
        assert ra.fast_context.urgency != pytest.approx(rb.fast_context.urgency)

    def test_inv142_no_cross_signal_contamination(self) -> None:
        """Changing urgency cannot affect risk_level computation."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import compute_all_horizon_values

        prev = ExecutionContext()
        snap_a = compute_all_horizon_values(
            ExecutionContext(urgency=1.0, risk_level=0.5), prev, prev
        )
        snap_b = compute_all_horizon_values(
            ExecutionContext(urgency=0.0, risk_level=0.5), prev, prev
        )
        assert snap_a.get_fast("risk_level") == pytest.approx(snap_b.get_fast("risk_level"))
        assert snap_a.get_slow("risk_level") == pytest.approx(snap_b.get_slow("risk_level"))

    def test_inv143_deterministic_dual_smoothing(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        runs = []
        for _ in range(5):
            hm = HorizonMemory()
            hm.smooth(ExecutionContext(urgency=0.1, risk_level=0.9))
            r = hm.smooth(ExecutionContext(urgency=0.9, risk_level=0.1))
            runs.append(
                (
                    r.fast_context.urgency,
                    r.slow_context.urgency,
                    r.snapshot.get_delta("urgency"),
                )
            )
        assert all(r == runs[0] for r in runs)

    def test_inv144_neutral_produces_neutral(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for _ in range(10):
            r = hm.smooth(NEUTRAL_CONTEXT)
        assert r.fast_context.is_neutral is True
        assert r.slow_context.is_neutral is True

    def test_inv144_neutral_through_context_memory(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        for _ in range(10):
            result, snap = cm.smooth_horizon(NEUTRAL_CONTEXT)
        assert result.smoothed.is_neutral is True

    def test_inv145_no_amplification_fast(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for i in range(50):
            raw = ExecutionContext(urgency=0.0 if i % 2 == 0 else 1.0)
            r = hm.smooth(raw)
            assert 0.0 <= r.fast_context.urgency <= 1.0

    def test_inv145_no_amplification_slow(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for i in range(50):
            raw = ExecutionContext(urgency=0.0 if i % 2 == 0 else 1.0)
            r = hm.smooth(raw)
            assert 0.0 <= r.slow_context.urgency <= 1.0

    def test_inv145_no_amplification_delta(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for i in range(50):
            raw = ExecutionContext(urgency=0.0 if i % 2 == 0 else 1.0)
            r = hm.smooth(raw)
            assert -1.0 <= r.snapshot.get_delta("urgency") <= 1.0


# ---------------------------------------------------------------------------
# Section 19: Boundary conditions
# ---------------------------------------------------------------------------


class TestBoundaryConditions:
    def test_all_zeros(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        ctx = ExecutionContext(
            urgency=0.0, risk_level=0.0, resource_pressure=0.0, stability_mode=0.0
        )
        for _ in range(10):
            r = hm.smooth(ctx)
        assert r.fast_context.urgency == pytest.approx(0.0)
        assert r.slow_context.urgency == pytest.approx(0.0)

    def test_all_ones(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        ctx = ExecutionContext(
            urgency=1.0, risk_level=1.0, resource_pressure=1.0, stability_mode=1.0
        )
        for _ in range(10):
            r = hm.smooth(ctx)
        assert r.fast_context.urgency == pytest.approx(1.0)
        assert r.slow_context.urgency == pytest.approx(1.0)

    def test_extreme_alpha_values(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonAlphas, HorizonMemory

        alphas = {
            name: HorizonAlphas(signal_name=name, fast_alpha=0.99, slow_alpha=0.01)
            for name in ("urgency", "risk_level", "resource_pressure", "stability_mode")
        }
        hm = HorizonMemory(alphas=alphas)
        hm.smooth(ExecutionContext(urgency=0.0))
        r = hm.smooth(ExecutionContext(urgency=1.0))
        assert 0.0 <= r.fast_context.urgency <= 1.0
        assert 0.0 <= r.slow_context.urgency <= 1.0


# ---------------------------------------------------------------------------
# Section 20: Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_horizon_memory_to_dict(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.7))
        d = hm.to_dict()
        assert "alphas" in d
        assert "tick" in d
        assert "initialized" in d
        assert "prev_fast" in d
        assert "prev_slow" in d

    def test_horizon_result_to_dict(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        r = hm.smooth(ExecutionContext(urgency=0.7))
        d = r.to_dict()
        assert "snapshot" in d
        assert "fast_context" in d
        assert "slow_context" in d
        assert "raw" in d

    def test_snapshot_to_dict_has_all_signals(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        r = hm.smooth(ExecutionContext())
        d = r.snapshot.to_dict()
        for name in ("urgency", "risk_level", "resource_pressure", "stability_mode"):
            assert name in d["values"]

    def test_set_alphas(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonAlphas, HorizonMemory

        hm = HorizonMemory()
        new_alphas = {
            "urgency": HorizonAlphas(signal_name="urgency", fast_alpha=0.8, slow_alpha=0.2),
        }
        hm.set_alphas(new_alphas)
        assert hm.alphas == new_alphas


# ---------------------------------------------------------------------------
# Section 21: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_reset_then_smooth(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.9))
        hm.reset()
        r = hm.smooth(ExecutionContext(urgency=0.3))
        assert r.fast_context.urgency == pytest.approx(0.3)

    def test_override_then_smooth(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.override(ExecutionContext(urgency=0.2))
        r = hm.smooth(ExecutionContext(urgency=0.8))
        assert r.fast_context.urgency > 0.2
        assert r.fast_context.urgency < 0.8

    def test_many_ticks_no_drift(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for _ in range(100):
            r = hm.smooth(ExecutionContext(urgency=0.5))
        assert r.fast_context.urgency == pytest.approx(0.5, abs=0.001)
        assert r.slow_context.urgency == pytest.approx(0.5, abs=0.001)

    def test_alternating_rapid_converges(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for i in range(20):
            hm.smooth(ExecutionContext(urgency=float(i % 2)))
        r = hm.smooth(ExecutionContext(urgency=0.5))
        assert 0.3 <= r.fast_context.urgency <= 0.7
        assert 0.3 <= r.slow_context.urgency <= 0.7

    def test_custom_initial_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        initial = ExecutionContext(urgency=0.8, risk_level=0.1)
        hm = HorizonMemory(initial=initial)
        r = hm.smooth(ExecutionContext(urgency=0.8, risk_level=0.1))
        assert r.fast_context.urgency == pytest.approx(0.8, abs=0.01)


# ---------------------------------------------------------------------------
# Section 22: Default horizon alphas
# ---------------------------------------------------------------------------


class TestDefaultHorizonAlphas:
    def test_urgency_fast_higher_than_slow(self) -> None:
        from umh.runtime.horizon import _DEFAULT_HORIZON_ALPHAS

        ha = _DEFAULT_HORIZON_ALPHAS["urgency"]
        assert ha.fast_alpha > ha.slow_alpha

    def test_risk_fast_higher_than_slow(self) -> None:
        from umh.runtime.horizon import _DEFAULT_HORIZON_ALPHAS

        ha = _DEFAULT_HORIZON_ALPHAS["risk_level"]
        assert ha.fast_alpha > ha.slow_alpha

    def test_pressure_fast_higher_than_slow(self) -> None:
        from umh.runtime.horizon import _DEFAULT_HORIZON_ALPHAS

        ha = _DEFAULT_HORIZON_ALPHAS["resource_pressure"]
        assert ha.fast_alpha > ha.slow_alpha

    def test_stability_fast_higher_than_slow(self) -> None:
        from umh.runtime.horizon import _DEFAULT_HORIZON_ALPHAS

        ha = _DEFAULT_HORIZON_ALPHAS["stability_mode"]
        assert ha.fast_alpha > ha.slow_alpha

    def test_all_four_signals_present(self) -> None:
        from umh.runtime.horizon import _DEFAULT_HORIZON_ALPHAS

        for name in ("urgency", "risk_level", "resource_pressure", "stability_mode"):
            assert name in _DEFAULT_HORIZON_ALPHAS


# ---------------------------------------------------------------------------
# Section 23: Multi-tick convergence patterns
# ---------------------------------------------------------------------------


class TestMultiTickConvergence:
    def test_ramp_up_tracks_monotonically(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0))
        prev_fast = 0.0
        prev_slow = 0.0
        for _ in range(5):
            r = hm.smooth(ExecutionContext(urgency=1.0))
            assert r.fast_context.urgency >= prev_fast
            assert r.slow_context.urgency >= prev_slow
            prev_fast = r.fast_context.urgency
            prev_slow = r.slow_context.urgency

    def test_ramp_down_tracks_monotonically(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=1.0))
        prev_fast = 1.0
        prev_slow = 1.0
        for _ in range(5):
            r = hm.smooth(ExecutionContext(urgency=0.0))
            assert r.fast_context.urgency <= prev_fast
            assert r.slow_context.urgency <= prev_slow
            prev_fast = r.fast_context.urgency
            prev_slow = r.slow_context.urgency

    def test_half_life_fast_shorter_than_slow(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0))
        fast_half = None
        slow_half = None
        for i in range(30):
            r = hm.smooth(ExecutionContext(urgency=1.0))
            if fast_half is None and r.fast_context.urgency >= 0.5:
                fast_half = i
            if slow_half is None and r.slow_context.urgency >= 0.5:
                slow_half = i
        assert fast_half is not None
        assert slow_half is not None
        assert fast_half <= slow_half


# ---------------------------------------------------------------------------
# Section 24: Spike detection patterns
# ---------------------------------------------------------------------------


class TestSpikeDetection:
    def test_single_spike_detected_by_delta(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for _ in range(10):
            hm.smooth(ExecutionContext(urgency=0.3))
        r = hm.smooth(ExecutionContext(urgency=0.9))
        assert r.snapshot.get_delta("urgency") > 0.1

    def test_spike_delta_decays_if_sustained(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for _ in range(10):
            hm.smooth(ExecutionContext(urgency=0.3))
        r_spike = hm.smooth(ExecutionContext(urgency=0.9))
        delta_at_spike = r_spike.snapshot.get_delta("urgency")
        for _ in range(10):
            r = hm.smooth(ExecutionContext(urgency=0.9))
        delta_after = r.snapshot.get_delta("urgency")
        assert abs(delta_after) < abs(delta_at_spike)

    def test_spike_delta_decays_if_reverted(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for _ in range(10):
            hm.smooth(ExecutionContext(urgency=0.3))
        hm.smooth(ExecutionContext(urgency=0.9))
        r = hm.smooth(ExecutionContext(urgency=0.3))
        assert r.snapshot.get_delta("urgency") < 0.3

    def test_drop_detected(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for _ in range(10):
            hm.smooth(ExecutionContext(urgency=0.8))
        r = hm.smooth(ExecutionContext(urgency=0.1))
        assert r.snapshot.get_delta("urgency") < -0.1


# ---------------------------------------------------------------------------
# Section 25: Dependency boundary
# ---------------------------------------------------------------------------


class TestDependencyBoundary:
    def test_horizon_no_forbidden_imports(self) -> None:
        with open("/opt/OS/umh/runtime/horizon.py") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                assert "subprocess" not in module

    def test_horizon_no_cells_envs_adapters(self) -> None:
        with open("/opt/OS/umh/runtime/horizon.py") as f:
            source = f.read()
        for forbidden in ("from umh.cells", "from umh.environments", "from umh.adapters"):
            assert forbidden not in source


# ---------------------------------------------------------------------------
# Section 26: Exports and compilation
# ---------------------------------------------------------------------------


class TestExportsAndCompilation:
    def test_runtime_exports_horizon_types(self) -> None:
        from umh.runtime import (
            HorizonAlphas,
            HorizonMemory,
            HorizonResult,
            HorizonSnapshot,
            HorizonValue,
            compute_all_horizon_values,
            compute_horizon_value,
        )

        assert HorizonValue is not None
        assert HorizonSnapshot is not None
        assert HorizonAlphas is not None
        assert HorizonResult is not None
        assert HorizonMemory is not None
        assert compute_horizon_value is not None
        assert compute_all_horizon_values is not None

    def test_horizon_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/horizon.py", doraise=True)

    def test_context_memory_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/context_memory.py", doraise=True)

    def test_init_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_all_new_exports_in_all_list(self) -> None:
        import umh.runtime as rt

        expected = [
            "HorizonAlphas",
            "HorizonMemory",
            "HorizonResult",
            "HorizonSnapshot",
            "HorizonValue",
            "compute_all_horizon_values",
            "compute_horizon_value",
        ]
        for name in expected:
            assert name in rt.__all__, f"{name} not in __all__"


# ---------------------------------------------------------------------------
# Section 27: Phase 40 regression
# ---------------------------------------------------------------------------


class TestPhase40Regression:
    def test_adaptive_smooth_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0))
        r, snap = cm.smooth_adaptive(ExecutionContext(urgency=1.0))
        assert "urgency" in snap.alphas
        assert r.smoothed.urgency > 0.0

    def test_fixed_alpha_smooth_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.5)

    def test_smooth_context_function_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import smooth_context

        c = ExecutionContext(urgency=1.0)
        p = ExecutionContext(urgency=0.0)
        result = smooth_context(c, p, 0.5)
        assert result.urgency == pytest.approx(0.5)

    def test_smooth_value_function_unchanged(self) -> None:
        from umh.runtime.context_memory import smooth_value

        assert smooth_value(1.0, 0.0, 0.5) == pytest.approx(0.5)

    def test_signal_profiles_unchanged(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES

        assert DEFAULT_SIGNAL_PROFILES["urgency"].volatility_class == "high"
        assert DEFAULT_SIGNAL_PROFILES["risk_level"].volatility_class == "low"

    def test_reset_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        r = cm.reset()
        assert r.smoothed.is_neutral is True
        assert r.was_reset is True

    def test_override_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r = cm.override(ExecutionContext(urgency=0.7))
        assert r.smoothed.urgency == 0.7

    def test_make_context_unchanged(self) -> None:
        from umh.runtime.context import make_context

        ctx = make_context(urgency=0.8)
        assert ctx.urgency == 0.8

    def test_neutral_context_unchanged(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT

        assert NEUTRAL_CONTEXT.is_neutral is True


# ---------------------------------------------------------------------------
# Section 28: HorizonMemory properties
# ---------------------------------------------------------------------------


class TestHorizonMemoryProperties:
    def test_prev_fast_property(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.7))
        assert hm.prev_fast.urgency == pytest.approx(0.7)

    def test_prev_slow_property(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.7))
        assert hm.prev_slow.urgency == pytest.approx(0.7)

    def test_tick_property(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        assert hm.tick == 0
        hm.smooth(ExecutionContext())
        assert hm.tick == 1

    def test_initialized_property(self) -> None:
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        assert hm.initialized is False

    def test_alphas_property(self) -> None:
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        alphas = hm.alphas
        assert "urgency" in alphas
        assert "risk_level" in alphas


# ---------------------------------------------------------------------------
# Section 29: Trend detection patterns
# ---------------------------------------------------------------------------


class TestTrendDetection:
    def test_gradual_ramp_positive_delta(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for i in range(10):
            r = hm.smooth(ExecutionContext(urgency=i / 10.0))
        assert r.snapshot.get_delta("urgency") > 0

    def test_gradual_ramp_down_negative_delta(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for i in range(10):
            r = hm.smooth(ExecutionContext(urgency=1.0 - i / 10.0))
        assert r.snapshot.get_delta("urgency") < 0

    def test_plateau_after_ramp_delta_decays(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        for i in range(10):
            hm.smooth(ExecutionContext(urgency=i / 10.0))
        r_ramp = hm.smooth(ExecutionContext(urgency=0.9))
        delta_at_ramp = abs(r_ramp.snapshot.get_delta("urgency"))
        for _ in range(15):
            r = hm.smooth(ExecutionContext(urgency=0.9))
        delta_plateau = abs(r.snapshot.get_delta("urgency"))
        assert delta_plateau < delta_at_ramp


# ---------------------------------------------------------------------------
# Section 30: All three smoothing modes coexist
# ---------------------------------------------------------------------------


class TestThreeModesCoexist:
    def test_fixed_then_adaptive_then_horizon(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        r1 = cm.smooth(ExecutionContext(urgency=0.6))
        assert r1.tick == 1

        r2, snap2 = cm.smooth_adaptive(ExecutionContext(urgency=0.7))
        assert r2.tick == 2
        assert "urgency" in snap2.alphas

        r3, snap3 = cm.smooth_horizon(ExecutionContext(urgency=0.8))
        assert r3.tick == 3
        assert snap3.tick > 0

    def test_horizon_then_fixed(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_horizon(ExecutionContext(urgency=0.5))
        r = cm.smooth(ExecutionContext(urgency=0.7))
        assert r.tick == 2
        assert r.smoothed.urgency > 0.0

    def test_all_modes_share_tick_counter(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext())
        cm.smooth_adaptive(ExecutionContext())
        r, _ = cm.smooth_horizon(ExecutionContext())
        assert r.tick == 3
