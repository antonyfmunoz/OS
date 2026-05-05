"""Execution context — explicit environmental signals for decision adaptation.

Provides ExecutionContext as a frozen dataclass capturing urgency,
risk level, resource pressure, and stability mode. All values
normalized to [0,1]. Used as explicit input to weight adaptation.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_DEFAULT_URGENCY = 0.5
_DEFAULT_RISK = 0.5
_DEFAULT_PRESSURE = 0.5
_DEFAULT_STABILITY = 0.0


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


@dataclass(frozen=True)
class ExecutionContext:
    """Environmental signals that influence tradeoff weighting.

    All values are in [0, 1]:
      urgency: how time-critical the current decision is
      risk_level: how much is at stake if the decision fails
      resource_pressure: how constrained resources are
      stability_mode: preference for conservative choices (1.0 = max stability)
    """

    urgency: float = _DEFAULT_URGENCY
    risk_level: float = _DEFAULT_RISK
    resource_pressure: float = _DEFAULT_PRESSURE
    stability_mode: float = _DEFAULT_STABILITY

    def __post_init__(self) -> None:
        object.__setattr__(self, "urgency", _clamp01(self.urgency))
        object.__setattr__(self, "risk_level", _clamp01(self.risk_level))
        object.__setattr__(self, "resource_pressure", _clamp01(self.resource_pressure))
        object.__setattr__(self, "stability_mode", _clamp01(self.stability_mode))

    @property
    def is_neutral(self) -> bool:
        return (
            abs(self.urgency - _DEFAULT_URGENCY) < 1e-9
            and abs(self.risk_level - _DEFAULT_RISK) < 1e-9
            and abs(self.resource_pressure - _DEFAULT_PRESSURE) < 1e-9
            and abs(self.stability_mode - _DEFAULT_STABILITY) < 1e-9
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "urgency": round(self.urgency, 4),
            "risk_level": round(self.risk_level, 4),
            "resource_pressure": round(self.resource_pressure, 4),
            "stability_mode": round(self.stability_mode, 4),
            "is_neutral": self.is_neutral,
        }


NEUTRAL_CONTEXT = ExecutionContext()


def make_context(
    *,
    urgency: float = _DEFAULT_URGENCY,
    risk_level: float = _DEFAULT_RISK,
    resource_pressure: float = _DEFAULT_PRESSURE,
    stability_mode: float = _DEFAULT_STABILITY,
) -> ExecutionContext:
    """Factory for ExecutionContext with named parameters."""
    return ExecutionContext(
        urgency=urgency,
        risk_level=risk_level,
        resource_pressure=resource_pressure,
        stability_mode=stability_mode,
    )
