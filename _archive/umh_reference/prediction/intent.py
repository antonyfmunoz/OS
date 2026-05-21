"""Intent modeling — inferred user goals from behavioral signals.

UserIntent captures a prediction about what the user is likely to do
next, derived from job history, time patterns, and active context.

Intents are IMMUTABLE once created. They are descriptive artifacts,
never state-bearing or side-effecting.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass(frozen=True)
class UserIntent:
    """Predicted user goal inferred from behavioral signals.

    Read-only artifact. Never mutates system state.
    """

    intent_id: str
    inferred_goal: str
    confidence: float
    context_signals: tuple[str, ...] = ()
    related_entities: tuple[str, ...] = ()
    predicted_actions: tuple[str, ...] = ()
    source: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", _iso_now())
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"confidence must be 0.0–1.0, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "inferred_goal": self.inferred_goal,
            "confidence": self.confidence,
            "context_signals": list(self.context_signals),
            "related_entities": list(self.related_entities),
            "predicted_actions": list(self.predicted_actions),
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


def make_intent_id() -> str:
    return f"intent_{uuid.uuid4().hex[:12]}"
