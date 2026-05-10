"""Temporal context smoothing — exponential moving average over context signals.

Smooths ExecutionContext signals across ticks to reduce oscillation
while preserving responsiveness to sustained changes.

Smoothing formula:
    smoothed = alpha * current + (1 - alpha) * previous

Adaptive smoothing:
    per-signal alpha based on volatility class and recent delta

Alpha bounds: [_MIN_ALPHA, _MAX_ALPHA]
All output values clamped to [0, 1].

ContextMemory is the only stateful component — it holds previous_context.
All outputs are frozen ExecutionContext instances.

Pure computation internally — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from umh.runtime.context import NEUTRAL_CONTEXT, ExecutionContext

if TYPE_CHECKING:
    from umh.runtime.context_profile import AdaptationSnapshot, SignalProfile
    from umh.runtime.horizon import HorizonMemory, HorizonResult, HorizonSnapshot

_MIN_ALPHA = 0.2
_MAX_ALPHA = 0.8
_DEFAULT_ALPHA = 0.5


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _clamp_alpha(v: float) -> float:
    return max(_MIN_ALPHA, min(_MAX_ALPHA, v))


@dataclass(frozen=True)
class SmoothingResult:
    """Output of a single smoothing operation."""

    smoothed: ExecutionContext
    previous: ExecutionContext
    raw: ExecutionContext
    alpha: float
    tick: int
    was_reset: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "smoothed": self.smoothed.to_dict(),
            "previous": self.previous.to_dict(),
            "raw": self.raw.to_dict(),
            "alpha": round(self.alpha, 4),
            "tick": self.tick,
            "was_reset": self.was_reset,
        }


def smooth_value(current: float, previous: float, alpha: float) -> float:
    """Compute EMA for a single value. Deterministic, bounded."""
    return _clamp01(alpha * current + (1.0 - alpha) * previous)


def smooth_context(
    current: ExecutionContext,
    previous: ExecutionContext,
    alpha: float,
) -> ExecutionContext:
    """Smooth all context signals. Returns a new frozen ExecutionContext."""
    a = _clamp_alpha(alpha)
    return ExecutionContext(
        urgency=smooth_value(current.urgency, previous.urgency, a),
        risk_level=smooth_value(current.risk_level, previous.risk_level, a),
        resource_pressure=smooth_value(current.resource_pressure, previous.resource_pressure, a),
        stability_mode=smooth_value(current.stability_mode, previous.stability_mode, a),
    )


def adaptive_smooth_context(
    current: ExecutionContext,
    previous: ExecutionContext,
    profiles: dict[str, SignalProfile] | None = None,
    tick: int = 0,
) -> tuple[ExecutionContext, AdaptationSnapshot]:
    """Smooth context with per-signal adaptive alpha.

    Each signal uses its own alpha computed from its volatility profile
    and recent delta. Returns (smoothed_context, adaptation_snapshot).
    """
    from umh.runtime.context_profile import (
        DEFAULT_SIGNAL_PROFILES,
        compute_all_adapted_alphas,
    )

    active_profiles = profiles or DEFAULT_SIGNAL_PROFILES

    current_values = {
        "urgency": current.urgency,
        "risk_level": current.risk_level,
        "resource_pressure": current.resource_pressure,
        "stability_mode": current.stability_mode,
    }
    previous_values = {
        "urgency": previous.urgency,
        "risk_level": previous.risk_level,
        "resource_pressure": previous.resource_pressure,
        "stability_mode": previous.stability_mode,
    }

    snapshot = compute_all_adapted_alphas(active_profiles, current_values, previous_values, tick)

    smoothed = ExecutionContext(
        urgency=smooth_value(
            current.urgency,
            previous.urgency,
            snapshot.get_alpha("urgency"),
        ),
        risk_level=smooth_value(
            current.risk_level,
            previous.risk_level,
            snapshot.get_alpha("risk_level"),
        ),
        resource_pressure=smooth_value(
            current.resource_pressure,
            previous.resource_pressure,
            snapshot.get_alpha("resource_pressure"),
        ),
        stability_mode=smooth_value(
            current.stability_mode,
            previous.stability_mode,
            snapshot.get_alpha("stability_mode"),
        ),
    )

    return smoothed, snapshot


class ContextMemory:
    """Temporal context smoothing with EMA.

    Holds the previous context and applies exponential moving average
    to incoming context signals. The only stateful component in the
    context pipeline.

    Thread safety: not thread-safe. Designed for single-threaded tick loops.
    """

    def __init__(
        self,
        *,
        alpha: float = _DEFAULT_ALPHA,
        initial: ExecutionContext | None = None,
    ) -> None:
        self._alpha = _clamp_alpha(alpha)
        self._previous: ExecutionContext = initial or NEUTRAL_CONTEXT
        self._tick: int = 0
        self._initialized: bool = initial is not None
        self._horizon_memory: HorizonMemory | None = None

    @property
    def alpha(self) -> float:
        return self._alpha

    @property
    def previous_context(self) -> ExecutionContext:
        return self._previous

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def initialized(self) -> bool:
        return self._initialized

    def smooth(self, raw: ExecutionContext) -> SmoothingResult:
        """Apply EMA smoothing and advance tick.

        On first call (not initialized), the raw context is used directly
        to avoid pulling toward neutral from the very first tick.
        """
        previous = self._previous

        if not self._initialized:
            smoothed = raw
            self._initialized = True
        else:
            smoothed = smooth_context(raw, previous, self._alpha)

        self._previous = smoothed
        self._tick += 1

        return SmoothingResult(
            smoothed=smoothed,
            previous=previous,
            raw=raw,
            alpha=self._alpha,
            tick=self._tick,
            was_reset=False,
        )

    def smooth_adaptive(
        self,
        raw: ExecutionContext,
        profiles: dict[str, SignalProfile] | None = None,
    ) -> tuple[SmoothingResult, AdaptationSnapshot]:
        """Apply per-signal adaptive smoothing and advance tick.

        Each signal uses its own alpha based on volatility profile
        and recent delta. Returns (smoothing_result, adaptation_snapshot).

        On first call (not initialized), raw passes through directly.
        """
        previous = self._previous

        if not self._initialized:
            smoothed = raw
            self._initialized = True
            from umh.runtime.context_profile import (
                DEFAULT_SIGNAL_PROFILES,
                AdaptationSnapshot,
                AdaptedAlpha,
            )

            active = profiles or DEFAULT_SIGNAL_PROFILES
            neutral_alphas = {
                name: AdaptedAlpha(
                    signal_name=name,
                    base_alpha=p.effective_base_alpha,
                    delta=0.0,
                    adjustment=0.0,
                    adapted_alpha=p.effective_base_alpha,
                )
                for name, p in sorted(active.items())
            }
            snapshot = AdaptationSnapshot(alphas=neutral_alphas, tick=self._tick + 1)
        else:
            smoothed, snapshot = adaptive_smooth_context(raw, previous, profiles, self._tick + 1)

        self._previous = smoothed
        self._tick += 1

        result = SmoothingResult(
            smoothed=smoothed,
            previous=previous,
            raw=raw,
            alpha=0.0,
            tick=self._tick,
            was_reset=False,
        )
        return result, snapshot

    def reset(self, to: ExecutionContext | None = None) -> SmoothingResult:
        """Reset memory to a specific context or neutral.

        Returns a SmoothingResult with was_reset=True.
        """
        previous = self._previous
        new_ctx = to or NEUTRAL_CONTEXT

        self._previous = new_ctx
        self._tick += 1
        self._initialized = to is not None

        if self._horizon_memory is not None:
            self._horizon_memory.reset(to)

        return SmoothingResult(
            smoothed=new_ctx,
            previous=previous,
            raw=new_ctx,
            alpha=self._alpha,
            tick=self._tick,
            was_reset=True,
        )

    def override(self, ctx: ExecutionContext) -> SmoothingResult:
        """Set context directly, bypassing smoothing.

        Useful when the caller has authoritative context that should
        not be blended with history.
        """
        previous = self._previous

        self._previous = ctx
        self._tick += 1
        self._initialized = True

        return SmoothingResult(
            smoothed=ctx,
            previous=previous,
            raw=ctx,
            alpha=self._alpha,
            tick=self._tick,
            was_reset=False,
        )

    def smooth_horizon(
        self,
        raw: ExecutionContext,
    ) -> tuple[SmoothingResult, HorizonSnapshot]:
        """Apply dual-horizon EMA and advance tick.

        Uses an internal HorizonMemory to maintain fast and slow
        EMA tracks. The smoothed context in the SmoothingResult
        uses the fast EMA values (most responsive).

        Returns (smoothing_result, horizon_snapshot).
        """
        from umh.runtime.horizon import HorizonMemory as _HM

        if self._horizon_memory is None:
            initial = self._previous if self._initialized else None
            self._horizon_memory = _HM(initial=initial)

        hr = self._horizon_memory.smooth(raw)

        previous = self._previous
        smoothed = hr.fast_context

        if not self._initialized:
            self._initialized = True

        self._previous = smoothed
        self._tick += 1

        result = SmoothingResult(
            smoothed=smoothed,
            previous=previous,
            raw=raw,
            alpha=0.0,
            tick=self._tick,
            was_reset=False,
        )
        return result, hr.snapshot

    def set_alpha(self, alpha: float) -> None:
        """Update the smoothing factor. Clamped to [_MIN_ALPHA, _MAX_ALPHA]."""
        self._alpha = _clamp_alpha(alpha)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alpha": round(self._alpha, 4),
            "tick": self._tick,
            "initialized": self._initialized,
            "previous_context": self._previous.to_dict(),
        }
