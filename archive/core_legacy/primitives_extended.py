"""Extended Primitive Attributes — derived overlays on L0 without breaking immutability.

These are NOT new primitives.  They are computed attributes that overlay
existing L0 primitives to provide richer analysis.  Every extension
maps back to one or more L0 tags and is fully optional — the system
runs identically without them.

Usage:
    from core.primitives_extended import (
        compute_extensions, PrimitiveExtension, ExtendedPrimitiveSet
    )

    ext = compute_extensions(
        tags={PrimitiveTag.STATE, PrimitiveTag.CHANGE, PrimitiveTag.GOAL},
        context={"direction": "positive", "magnitude": 0.8},
    )
    print(ext.polarity)    # "positive"
    print(ext.intensity)   # 0.8
    print(ext.leverage)    # output/input ratio
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.primitives import PrimitiveTag


# ---------------------------------------------------------------------------
# Extension definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimitiveExtension:
    """A single derived attribute overlaid on an L0 primitive.

    Every extension is:
    - Traceable: maps to specific L0 tags
    - Optional: non-breaking
    - Computed: never stored as permanent state
    """

    name: str
    value: Any
    source_tags: frozenset[PrimitiveTag]  # which L0 tags this derives from
    confidence: float = 1.0  # 0.0-1.0, how confident the derivation is

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "source_tags": sorted(t.value for t in self.source_tags),
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ExtendedPrimitiveSet:
    """A set of L0 primitives with optional computed extensions.

    The base primitive set is unchanged.  Extensions ride alongside
    and can be queried by downstream consumers that understand them.
    Consumers that don't understand extensions see a normal primitive set.
    """

    tags: set[PrimitiveTag]
    extensions: list[PrimitiveExtension] = field(default_factory=list)

    # Convenience accessors for common extensions
    @property
    def polarity(self) -> str | None:
        """Direction of movement: 'positive', 'negative', or 'neutral'."""
        for ext in self.extensions:
            if ext.name == "polarity":
                return ext.value
        return None

    @property
    def intensity(self) -> float | None:
        """Magnitude of signal/change (0.0-1.0)."""
        for ext in self.extensions:
            if ext.name == "intensity":
                return ext.value
        return None

    @property
    def rhythm(self) -> str | None:
        """Temporal pattern: 'accelerating', 'decelerating', 'steady', 'irregular'."""
        for ext in self.extensions:
            if ext.name == "rhythm":
                return ext.value
        return None

    @property
    def emergence(self) -> bool:
        """Whether an unexpected outcome was detected."""
        for ext in self.extensions:
            if ext.name == "emergence":
                return ext.value
        return False

    @property
    def leverage(self) -> float | None:
        """Output/input ratio — how much result per unit effort."""
        for ext in self.extensions:
            if ext.name == "leverage":
                return ext.value
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tags": sorted(t.value for t in self.tags),
            "extensions": [e.to_dict() for e in self.extensions],
        }


# ---------------------------------------------------------------------------
# Extension computation
# ---------------------------------------------------------------------------

# Polarity: requires CHANGE or OUTCOME or FEEDBACK
_POLARITY_TAGS = {PrimitiveTag.CHANGE, PrimitiveTag.OUTCOME, PrimitiveTag.FEEDBACK}

# Intensity: requires SIGNAL or CHANGE
_INTENSITY_TAGS = {PrimitiveTag.SIGNAL, PrimitiveTag.CHANGE}

# Rhythm: requires TIME + (CHANGE or ACTION)
_RHYTHM_TAGS_REQUIRED = {PrimitiveTag.TIME}
_RHYTHM_TAGS_OPTIONAL = {PrimitiveTag.CHANGE, PrimitiveTag.ACTION}

# Emergence: requires OUTCOME + GOAL (unexpected = outcome != expected goal)
_EMERGENCE_TAGS = {PrimitiveTag.OUTCOME, PrimitiveTag.GOAL}

# Leverage: requires ACTION + OUTCOME + RESOURCE
_LEVERAGE_TAGS = {PrimitiveTag.ACTION, PrimitiveTag.OUTCOME, PrimitiveTag.RESOURCE}


def compute_extensions(
    tags: set[PrimitiveTag],
    context: dict[str, Any] | None = None,
) -> ExtendedPrimitiveSet:
    """Compute derived extensions for a primitive set.

    Extensions are only computed when the required L0 tags are present.
    Context provides hints for computation (e.g. direction, magnitude).

    Args:
        tags:    The L0 primitive set.
        context: Optional hints — keys like "direction", "magnitude",
                 "pattern", "expected_outcome", "input_cost", "output_value".

    Returns:
        ExtendedPrimitiveSet with all computable extensions.
    """
    context = context or {}
    extensions: list[PrimitiveExtension] = []

    # Polarity — direction of movement
    if tags & _POLARITY_TAGS:
        direction = context.get("direction", "neutral")
        if direction not in ("positive", "negative", "neutral"):
            direction = "neutral"
        source = frozenset(tags & _POLARITY_TAGS)
        extensions.append(
            PrimitiveExtension(
                name="polarity",
                value=direction,
                source_tags=source,
                confidence=0.9 if "direction" in context else 0.5,
            )
        )

    # Intensity — magnitude of signal/change
    if tags & _INTENSITY_TAGS:
        magnitude = context.get("magnitude", 0.5)
        magnitude = max(0.0, min(1.0, float(magnitude)))
        source = frozenset(tags & _INTENSITY_TAGS)
        extensions.append(
            PrimitiveExtension(
                name="intensity",
                value=magnitude,
                source_tags=source,
                confidence=0.9 if "magnitude" in context else 0.4,
            )
        )

    # Rhythm — temporal pattern
    if _RHYTHM_TAGS_REQUIRED <= tags and tags & _RHYTHM_TAGS_OPTIONAL:
        pattern = context.get("pattern", "steady")
        if pattern not in ("accelerating", "decelerating", "steady", "irregular"):
            pattern = "steady"
        source = frozenset(
            (tags & _RHYTHM_TAGS_REQUIRED) | (tags & _RHYTHM_TAGS_OPTIONAL)
        )
        extensions.append(
            PrimitiveExtension(
                name="rhythm",
                value=pattern,
                source_tags=source,
                confidence=0.8 if "pattern" in context else 0.3,
            )
        )

    # Emergence — unexpected outcome
    if _EMERGENCE_TAGS <= tags:
        expected = context.get("expected_outcome")
        actual = context.get("actual_outcome")
        emerged = expected is not None and actual is not None and expected != actual
        source = frozenset(_EMERGENCE_TAGS)
        extensions.append(
            PrimitiveExtension(
                name="emergence",
                value=emerged,
                source_tags=source,
                confidence=0.95 if expected is not None else 0.2,
            )
        )

    # Leverage — output/input ratio
    if _LEVERAGE_TAGS <= tags:
        input_cost = context.get("input_cost", 1.0)
        output_value = context.get("output_value", 1.0)
        ratio = float(output_value) / max(float(input_cost), 0.001)
        source = frozenset(_LEVERAGE_TAGS)
        extensions.append(
            PrimitiveExtension(
                name="leverage",
                value=round(ratio, 3),
                source_tags=source,
                confidence=0.9 if "input_cost" in context else 0.3,
            )
        )

    return ExtendedPrimitiveSet(tags=tags, extensions=extensions)


__all__ = [
    "PrimitiveExtension",
    "ExtendedPrimitiveSet",
    "compute_extensions",
]
