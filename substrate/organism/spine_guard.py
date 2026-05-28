"""SpineGuard — enforcement layer for the single-spine mutation doctrine.

Any mutation attempt outside the GovernedExecutionSpine is:
  - logged
  - emitted to the EventSpine
  - flagged as an architecture violation

Phase 1: WARN mode — logs violations, does not block.
Phase 2: ENFORCE mode — blocks violations (future).

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class GuardMode:
    WARN = "warn"
    ENFORCE = "enforce"


@dataclass
class Violation:
    source: str
    description: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "description": self.description,
            "timestamp": self.timestamp,
        }


_MAX_VIOLATIONS = 500


class SpineGuard:
    """Tracks and optionally blocks direct mutation attempts.

    Subsystems call report_direct_mutation() when they detect
    a mutation that didn't flow through the GovernedExecutionSpine.
    """

    def __init__(
        self,
        mode: str = GuardMode.WARN,
        event_spine: Any = None,
    ) -> None:
        self._mode = mode
        self._event_spine = event_spine
        self._violations: list[Violation] = []
        self._lock = threading.Lock()
        self._total_violations: int = 0

    def report_direct_mutation(self, source: str, description: str) -> None:
        violation = Violation(source=source, description=description)

        with self._lock:
            if len(self._violations) >= _MAX_VIOLATIONS:
                self._violations = self._violations[-(_MAX_VIOLATIONS // 2):]
            self._violations.append(violation)
            self._total_violations += 1

        logger.warning(
            "SPINE VIOLATION [%s]: %s — %s",
            self._mode, source, description,
        )

        if self._event_spine is not None:
            from substrate.organism.event_spine import EventDomain, EventPriority
            self._event_spine.emit(
                EventDomain.GOVERNANCE,
                "spine_violation",
                source,
                violation.to_dict(),
                priority=EventPriority.CRITICAL,
            )

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def recent_violations(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return [v.to_dict() for v in self._violations[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            recent_count = len(self._violations)
        return {
            "mode": self._mode,
            "total_violations": self._total_violations,
            "recent_violations": recent_count,
        }
