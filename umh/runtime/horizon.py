"""Multi-horizon temporal context — dual EMA per signal.

Provides fast and slow exponential moving averages for each context
signal, enabling spike detection, trend detection, and regime awareness.

Dual EMA model:
    fast_value = α_fast * current + (1 - α_fast) * prev_fast
    slow_value = α_slow * current + (1 - α_slow) * prev_slow

Constraint: α_fast > α_slow always.

Delta interpretation:
    delta = fast - slow
    large positive → spike (signal rising faster than trend)
    large negative → drop (signal falling faster than trend)
    near zero      → stable (signal tracking its trend)

Alpha bounds: [_MIN_ALPHA, _MAX_ALPHA] per horizon.
All output values clamped to [0, 1].
Delta values clamped to [-1, 1].

Pure computation internally — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from umh.runtime.context import NEUTRAL_CONTEXT, ExecutionContext

if TYPE_CHECKING:
    from umh.runtime.context_profile import SignalProfile

_MIN_ALPHA = 0.2
_MAX_ALPHA = 0.8

_DEFAULT_FAST_ALPHA = 0.7
_DEFAULT_SLOW_ALPHA = 0.3

_SIGNAL_NAMES = ("urgency", "risk_level", "resource_pressure", "stability_mode")


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _clamp_alpha(v: float) -> float:
    return max(_MIN_ALPHA, min(_MAX_ALPHA, v))


def _clamp_delta(v: float) -> float:
    return max(-1.0, min(1.0, v))


@dataclass(frozen=True)
class HorizonValue:
    """Dual EMA output for a single signal."""

    signal_name: str
    fast: float
    slow: float
    delta: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "fast": round(self.fast, 4),
            "slow": round(self.slow, 4),
            "delta": round(self.delta, 4),
        }


@dataclass(frozen=True)
class HorizonSnapshot:
    """Complete multi-horizon state for all signals at one tick."""

    values: dict[str, HorizonValue]
    tick: int

    def get(self, signal_name: str) -> HorizonValue | None:
        return self.values.get(signal_name)

    def get_delta(self, signal_name: str) -> float:
        v = self.values.get(signal_name)
        return v.delta if v is not None else 0.0

    def get_fast(self, signal_name: str) -> float:
        v = self.values.get(signal_name)
        return v.fast if v is not None else 0.5

    def get_slow(self, signal_name: str) -> float:
        v = self.values.get(signal_name)
        return v.slow if v is not None else 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": {k: v.to_dict() for k, v in sorted(self.values.items())},
            "tick": self.tick,
        }


@dataclass(frozen=True)
class HorizonAlphas:
    """Per-signal fast/slow alpha pair."""

    signal_name: str
    fast_alpha: float
    slow_alpha: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "fast_alpha": round(self.fast_alpha, 4),
            "slow_alpha": round(self.slow_alpha, 4),
        }


_DEFAULT_HORIZON_ALPHAS: dict[str, HorizonAlphas] = {
    "urgency": HorizonAlphas(signal_name="urgency", fast_alpha=0.7, slow_alpha=0.3),
    "risk_level": HorizonAlphas(signal_name="risk_level", fast_alpha=0.5, slow_alpha=0.2),
    "resource_pressure": HorizonAlphas(
        signal_name="resource_pressure", fast_alpha=0.6, slow_alpha=0.25
    ),
    "stability_mode": HorizonAlphas(signal_name="stability_mode", fast_alpha=0.5, slow_alpha=0.2),
}


def compute_horizon_value(
    signal_name: str,
    current: float,
    prev_fast: float,
    prev_slow: float,
    fast_alpha: float,
    slow_alpha: float,
) -> HorizonValue:
    """Compute dual EMA for a single signal. Deterministic, bounded."""
    af = _clamp_alpha(fast_alpha)
    as_ = _clamp_alpha(slow_alpha)

    if af <= as_:
        af = min(as_ + 0.1, _MAX_ALPHA)

    fast = _clamp01(af * current + (1.0 - af) * prev_fast)
    slow = _clamp01(as_ * current + (1.0 - as_) * prev_slow)
    delta = _clamp_delta(fast - slow)

    return HorizonValue(signal_name=signal_name, fast=fast, slow=slow, delta=delta)


def compute_all_horizon_values(
    current: ExecutionContext,
    prev_fast: ExecutionContext,
    prev_slow: ExecutionContext,
    alphas: dict[str, HorizonAlphas] | None = None,
    tick: int = 0,
) -> HorizonSnapshot:
    """Compute dual EMA for all context signals."""
    active_alphas = alphas or _DEFAULT_HORIZON_ALPHAS

    current_vals = {
        "urgency": current.urgency,
        "risk_level": current.risk_level,
        "resource_pressure": current.resource_pressure,
        "stability_mode": current.stability_mode,
    }
    fast_vals = {
        "urgency": prev_fast.urgency,
        "risk_level": prev_fast.risk_level,
        "resource_pressure": prev_fast.resource_pressure,
        "stability_mode": prev_fast.stability_mode,
    }
    slow_vals = {
        "urgency": prev_slow.urgency,
        "risk_level": prev_slow.risk_level,
        "resource_pressure": prev_slow.resource_pressure,
        "stability_mode": prev_slow.stability_mode,
    }

    values: dict[str, HorizonValue] = {}
    for name in sorted(_SIGNAL_NAMES):
        ha = active_alphas.get(name)
        if ha is None:
            ha = HorizonAlphas(
                signal_name=name,
                fast_alpha=_DEFAULT_FAST_ALPHA,
                slow_alpha=_DEFAULT_SLOW_ALPHA,
            )
        values[name] = compute_horizon_value(
            signal_name=name,
            current=current_vals[name],
            prev_fast=fast_vals[name],
            prev_slow=slow_vals[name],
            fast_alpha=ha.fast_alpha,
            slow_alpha=ha.slow_alpha,
        )

    return HorizonSnapshot(values=values, tick=tick)


@dataclass(frozen=True)
class HorizonResult:
    """Output of a multi-horizon smoothing operation."""

    snapshot: HorizonSnapshot
    fast_context: ExecutionContext
    slow_context: ExecutionContext
    raw: ExecutionContext
    tick: int
    was_reset: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "fast_context": self.fast_context.to_dict(),
            "slow_context": self.slow_context.to_dict(),
            "raw": self.raw.to_dict(),
            "tick": self.tick,
            "was_reset": self.was_reset,
        }


class HorizonMemory:
    """Dual-horizon temporal context with fast and slow EMA.

    Maintains two EMA tracks per signal:
    - fast: responsive to recent changes (α ≈ 0.7)
    - slow: tracks underlying trend (α ≈ 0.3)

    The delta (fast - slow) indicates:
    - spike: signal rising faster than trend
    - drop: signal falling below trend
    - stable: signal tracking trend

    Thread safety: not thread-safe. Designed for single-threaded tick loops.
    """

    def __init__(
        self,
        *,
        alphas: dict[str, HorizonAlphas] | None = None,
        initial: ExecutionContext | None = None,
    ) -> None:
        self._alphas = alphas or dict(_DEFAULT_HORIZON_ALPHAS)
        init_ctx = initial or NEUTRAL_CONTEXT
        self._prev_fast: ExecutionContext = init_ctx
        self._prev_slow: ExecutionContext = init_ctx
        self._tick: int = 0
        self._initialized: bool = initial is not None

    @property
    def prev_fast(self) -> ExecutionContext:
        return self._prev_fast

    @property
    def prev_slow(self) -> ExecutionContext:
        return self._prev_slow

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def alphas(self) -> dict[str, HorizonAlphas]:
        return dict(self._alphas)

    def smooth(self, raw: ExecutionContext) -> HorizonResult:
        """Apply dual-horizon EMA and advance tick.

        On first call (not initialized), raw passes through to both
        fast and slow horizons to avoid false neutral-pull on tick 1.
        """
        prev_fast = self._prev_fast
        prev_slow = self._prev_slow

        if not self._initialized:
            fast_ctx = raw
            slow_ctx = raw
            snapshot = HorizonSnapshot(
                values={
                    name: HorizonValue(
                        signal_name=name,
                        fast=getattr(raw, name),
                        slow=getattr(raw, name),
                        delta=0.0,
                    )
                    for name in _SIGNAL_NAMES
                },
                tick=self._tick + 1,
            )
            self._initialized = True
        else:
            snapshot = compute_all_horizon_values(
                raw, prev_fast, prev_slow, self._alphas, self._tick + 1
            )
            fast_ctx = ExecutionContext(
                urgency=snapshot.get_fast("urgency"),
                risk_level=snapshot.get_fast("risk_level"),
                resource_pressure=snapshot.get_fast("resource_pressure"),
                stability_mode=snapshot.get_fast("stability_mode"),
            )
            slow_ctx = ExecutionContext(
                urgency=snapshot.get_slow("urgency"),
                risk_level=snapshot.get_slow("risk_level"),
                resource_pressure=snapshot.get_slow("resource_pressure"),
                stability_mode=snapshot.get_slow("stability_mode"),
            )

        self._prev_fast = fast_ctx
        self._prev_slow = slow_ctx
        self._tick += 1

        return HorizonResult(
            snapshot=snapshot,
            fast_context=fast_ctx,
            slow_context=slow_ctx,
            raw=raw,
            tick=self._tick,
            was_reset=False,
        )

    def reset(self, to: ExecutionContext | None = None) -> HorizonResult:
        """Reset both horizons to a specific context or neutral."""
        new_ctx = to or NEUTRAL_CONTEXT

        snapshot = HorizonSnapshot(
            values={
                name: HorizonValue(
                    signal_name=name,
                    fast=getattr(new_ctx, name),
                    slow=getattr(new_ctx, name),
                    delta=0.0,
                )
                for name in _SIGNAL_NAMES
            },
            tick=self._tick + 1,
        )

        self._prev_fast = new_ctx
        self._prev_slow = new_ctx
        self._tick += 1
        self._initialized = to is not None

        return HorizonResult(
            snapshot=snapshot,
            fast_context=new_ctx,
            slow_context=new_ctx,
            raw=new_ctx,
            tick=self._tick,
            was_reset=True,
        )

    def override(self, ctx: ExecutionContext) -> HorizonResult:
        """Set both horizons directly, bypassing smoothing."""
        snapshot = HorizonSnapshot(
            values={
                name: HorizonValue(
                    signal_name=name,
                    fast=getattr(ctx, name),
                    slow=getattr(ctx, name),
                    delta=0.0,
                )
                for name in _SIGNAL_NAMES
            },
            tick=self._tick + 1,
        )

        self._prev_fast = ctx
        self._prev_slow = ctx
        self._tick += 1
        self._initialized = True

        return HorizonResult(
            snapshot=snapshot,
            fast_context=ctx,
            slow_context=ctx,
            raw=ctx,
            tick=self._tick,
            was_reset=False,
        )

    def set_alphas(self, alphas: dict[str, HorizonAlphas]) -> None:
        """Update alpha configuration for future ticks."""
        self._alphas = dict(alphas)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alphas": {k: v.to_dict() for k, v in sorted(self._alphas.items())},
            "tick": self._tick,
            "initialized": self._initialized,
            "prev_fast": self._prev_fast.to_dict(),
            "prev_slow": self._prev_slow.to_dict(),
        }
