"""User behavior model — unified profile derived from observed data.

The model is a collection of traits computed from job feedback,
prediction accuracy, and pattern recurrence. It is always derived,
never manually injected (invariants 60-61).

Serializable. Supports incremental updates. Degrades gracefully
with limited data (invariant 64).

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.model.traits import TraitValue, default_traits


@dataclass
class UserBehaviorModel:
    """Persistent, evolving model of user behavior."""

    traits: dict[str, TraitValue] = field(default_factory=default_traits)
    last_updated: str = ""
    update_count: int = 0
    total_observations: int = 0

    @property
    def confidence_score(self) -> float:
        """Overall model confidence: average of trait confidences."""
        if not self.traits:
            return 0.0
        return sum(t.confidence for t in self.traits.values()) / len(self.traits)

    @property
    def dominant_traits(self) -> list[TraitValue]:
        """Traits that deviate most from default (0.5), sorted by magnitude."""
        ranked = sorted(
            self.traits.values(),
            key=lambda t: abs(t.value - 0.5),
            reverse=True,
        )
        return [t for t in ranked if t.confidence > 0.1]

    def get_trait(self, name: str) -> TraitValue | None:
        return self.traits.get(name)

    def set_trait(
        self,
        name: str,
        value: float,
        confidence: float,
        sample_count: int,
    ) -> None:
        """Update a trait value. Timestamps the model."""
        self.traits[name] = TraitValue(
            name=name,
            value=value,
            confidence=confidence,
            sample_count=sample_count,
        )
        self.last_updated = _iso_now()
        self.update_count += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "traits": {k: v.to_dict() for k, v in sorted(self.traits.items())},
            "last_updated": self.last_updated,
            "update_count": self.update_count,
            "total_observations": self.total_observations,
            "confidence_score": round(self.confidence_score, 4),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserBehaviorModel:
        """Deserialize from dict. Skips invalid traits gracefully."""
        model = cls()
        model.last_updated = data.get("last_updated", "")
        model.update_count = data.get("update_count", 0)
        model.total_observations = data.get("total_observations", 0)

        traits_data = data.get("traits", {})
        for name, tdata in traits_data.items():
            if isinstance(tdata, dict):
                model.traits[name] = TraitValue(
                    name=name,
                    value=tdata.get("value", 0.5),
                    confidence=tdata.get("confidence", 0.0),
                    sample_count=tdata.get("sample_count", 0),
                )
        return model
