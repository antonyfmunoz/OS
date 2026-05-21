"""Signal types — domain-independent signal classification.

Adapted from the signal hierarchy principle: higher tiers gate lower tiers.
Tier 1 (Reality) always takes precedence over Tier 5 (Delivery).

No LLM calls. No domain-specific logic. Pure data + deterministic classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class SignalTier(IntEnum):
    REALITY = 1
    CONTEXT = 2
    LEVERAGE = 3
    OPTIMIZATION = 4
    DELIVERY = 5


@dataclass(frozen=True)
class Signal:
    """A single classified signal from raw input."""

    signal_id: str
    tier: SignalTier
    source: str
    content: str
    confidence: float
    domain: str = "universal"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "tier": self.tier.name,
            "source": self.source,
            "content": self.content,
            "confidence": round(self.confidence, 4),
            "domain": self.domain,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class SignalBundle:
    """Ordered collection of signals from a single input, highest tier first."""

    signals: tuple[Signal, ...]
    raw_input: str
    source: str

    @property
    def primary(self) -> Signal | None:
        return self.signals[0] if self.signals else None

    @property
    def highest_tier(self) -> SignalTier | None:
        return min((s.tier for s in self.signals), default=None)

    def by_tier(self, tier: SignalTier) -> tuple[Signal, ...]:
        return tuple(s for s in self.signals if s.tier == tier)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signals": [s.to_dict() for s in self.signals],
            "raw_input": self.raw_input[:200],
            "source": self.source,
            "signal_count": len(self.signals),
            "highest_tier": self.highest_tier.name if self.highest_tier else None,
        }
