"""GlobalEvent schema — normalized container for all awareness events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventCategory(str, Enum):
    NEWS = "news"
    WEATHER = "weather"
    MARKETS = "markets"
    CRYPTO = "crypto"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GlobalEvent:
    category: EventCategory
    title: str
    summary: str
    source: str
    timestamp: datetime
    severity: Severity = Severity.LOW
    confidence: float = 1.0
    source_url: str | None = None
    location: str | None = None
    symbols: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GlobalEvent:
        data = dict(data)
        data["category"] = EventCategory(data["category"])
        data["severity"] = Severity(data["severity"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
