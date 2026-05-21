"""Behavioral traits — measurable dimensions of user behavior.

Each trait is a bounded numeric value derived from observed data.
Traits are never manually injected (invariant 61).

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


_DEFAULT_VALUE = 0.5
_MIN_VALUE = 0.0
_MAX_VALUE = 1.0


@dataclass(frozen=True)
class TraitDefinition:
    """Definition of a measurable behavioral trait."""

    name: str
    description: str
    min_value: float = _MIN_VALUE
    max_value: float = _MAX_VALUE
    default_value: float = _DEFAULT_VALUE


TRAIT_DEFINITIONS: dict[str, TraitDefinition] = {
    "execution_rate": TraitDefinition(
        name="execution_rate",
        description="Fraction of scheduled tasks that get executed",
    ),
    "completion_rate": TraitDefinition(
        name="completion_rate",
        description="Fraction of executed tasks that succeed",
    ),
    "consistency_score": TraitDefinition(
        name="consistency_score",
        description="Regularity of activity timing (1.0 = perfectly regular)",
    ),
    "latency_score": TraitDefinition(
        name="latency_score",
        description="Inverse of average response time (1.0 = fastest)",
    ),
    "pattern_stability": TraitDefinition(
        name="pattern_stability",
        description="Tendency to repeat established patterns (1.0 = fully stable)",
    ),
    "time_preference": TraitDefinition(
        name="time_preference",
        description="Morning vs evening bias (0.0 = night, 0.5 = balanced, 1.0 = morning)",
    ),
    "volatility_index": TraitDefinition(
        name="volatility_index",
        description="Rate of behavioral change (0.0 = static, 1.0 = highly volatile)",
    ),
}


@dataclass
class TraitValue:
    """A computed trait value with confidence and sample count."""

    name: str
    value: float
    confidence: float = 0.0
    sample_count: int = 0

    def __post_init__(self) -> None:
        defn = TRAIT_DEFINITIONS.get(self.name)
        if defn is not None:
            self.value = max(defn.min_value, min(defn.max_value, self.value))
        self.confidence = max(0.0, min(1.0, self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "confidence": round(self.confidence, 4),
            "sample_count": self.sample_count,
        }


def default_traits() -> dict[str, TraitValue]:
    """Return all traits at default (neutral) values with zero confidence."""
    return {
        name: TraitValue(name=name, value=defn.default_value, confidence=0.0, sample_count=0)
        for name, defn in TRAIT_DEFINITIONS.items()
    }


def confidence_from_samples(n: int, required: int = 20) -> float:
    """Compute confidence score from sample count. Saturates at 1.0."""
    if n <= 0:
        return 0.0
    return min(1.0, n / required)
