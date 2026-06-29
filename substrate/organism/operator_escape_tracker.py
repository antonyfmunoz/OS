"""Operator Escape Tracker — records exits from UMH organism.

Tracks when the operator leaves UMH to use raw tools directly
(manual SSH, raw Claude Code, external browser, etc.).
Each escape event records what was missing from UMH.

C33 benchmark infrastructure. UMH substrate subsystem.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class OperatorEscapeEvent:
    event_id: str = field(default_factory=lambda: f"esc-{uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    destination: str = ""
    reason: str = ""
    missing_capability: str = ""
    missing_automation: str = ""
    ux_issue: str = ""
    duration_seconds: float = 0.0
    resolved: bool = False
    surface_before: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OperatorEscapeEvent:
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**fields)


class OperatorEscapeTracker:
    """Tracks operator exits from UMH organism."""

    def __init__(self, store_path: str = "") -> None:
        self._store_path = store_path or os.path.join(
            _REPO_ROOT, "data", "umh", "c33", "escape_events.jsonl"
        )
        self._events: list[OperatorEscapeEvent] = []
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self._store_path):
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._events.append(
                            OperatorEscapeEvent.from_dict(json.loads(line))
                        )
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("Skip malformed escape event: %s", exc)
        except OSError as exc:
            logger.debug("Cannot read %s: %s", self._store_path, exc)

    def _persist(self, event: OperatorEscapeEvent) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "a") as f:
            f.write(json.dumps(event.to_dict(), default=str) + "\n")

    def record_escape(
        self,
        destination: str,
        reason: str,
        *,
        missing_capability: str = "",
        missing_automation: str = "",
        ux_issue: str = "",
        duration_seconds: float = 0.0,
        surface_before: str = "",
    ) -> OperatorEscapeEvent:
        event = OperatorEscapeEvent(
            destination=destination,
            reason=reason,
            missing_capability=missing_capability,
            missing_automation=missing_automation,
            ux_issue=ux_issue,
            duration_seconds=duration_seconds,
            surface_before=surface_before,
        )
        self._events.append(event)
        self._persist(event)
        logger.info(
            "Operator escape recorded: %s -> %s (%s)",
            surface_before or "unknown",
            destination,
            reason,
        )
        return event

    def resolve_escape(self, event_id: str) -> bool:
        for event in self._events:
            if event.event_id == event_id:
                event.resolved = True
                self._rewrite()
                return True
        return False

    def _rewrite(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "w") as f:
            for event in self._events:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")

    def get_events(self, limit: int = 100) -> list[OperatorEscapeEvent]:
        return sorted(self._events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def escape_rate(self, window_hours: float = 8.0) -> float:
        cutoff = time.time() - (window_hours * 3600)
        recent = [e for e in self._events if e.timestamp >= cutoff]
        if not recent or window_hours <= 0:
            return 0.0
        return len(recent) / window_hours

    def summary(self) -> dict[str, Any]:
        if not self._events:
            return {
                "total_escapes": 0,
                "resolved": 0,
                "unresolved": 0,
                "top_destinations": [],
                "top_missing_capabilities": [],
                "avg_duration_seconds": 0.0,
                "escapes_per_hour_8h": 0.0,
            }

        destinations = Counter(e.destination for e in self._events if e.destination)
        capabilities = Counter(
            e.missing_capability for e in self._events if e.missing_capability
        )
        durations = [e.duration_seconds for e in self._events if e.duration_seconds > 0]

        return {
            "total_escapes": len(self._events),
            "resolved": sum(1 for e in self._events if e.resolved),
            "unresolved": sum(1 for e in self._events if not e.resolved),
            "top_destinations": destinations.most_common(5),
            "top_missing_capabilities": capabilities.most_common(5),
            "avg_duration_seconds": round(
                sum(durations) / len(durations), 1
            ) if durations else 0.0,
            "escapes_per_hour_8h": round(self.escape_rate(8.0), 2),
        }
