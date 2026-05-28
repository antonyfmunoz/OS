"""SpineGuard — enforcement layer for the single-spine mutation doctrine.

Graduated enforcement ladder for the GovernedExecutionSpine:
  OFF             — no enforcement, no logging
  WARN            — logs violations, does not block
  BLOCK_HIGH_RISK — blocks medium/high/critical mutations that bypass spine
  ENFORCE_ALL     — blocks ALL mutations that bypass spine

Production default: BLOCK_HIGH_RISK
  LOW read-only/probe actions pass through if classified safe.
  MEDIUM+ mutations MUST go through spine.

Violations emit EventSpine events, write journal entries,
and appear in cockpit /organism/spine-guard.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class GuardMode(str, Enum):
    OFF = "off"
    WARN = "warn"
    BLOCK_HIGH_RISK = "block_high_risk"
    ENFORCE_ALL = "enforce_all"


_GUARD_MODE_SEVERITY: dict[GuardMode, int] = {
    GuardMode.OFF: 0,
    GuardMode.WARN: 1,
    GuardMode.BLOCK_HIGH_RISK: 2,
    GuardMode.ENFORCE_ALL: 3,
}


_RISK_SEVERITY: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


@dataclass
class Violation:
    source: str
    description: str
    risk_level: str = "unknown"
    blocked: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "description": self.description,
            "risk_level": self.risk_level,
            "blocked": self.blocked,
            "timestamp": self.timestamp,
        }


_MAX_VIOLATIONS = 500


class SpineGuard:
    """Tracks and optionally blocks direct mutation attempts.

    Subsystems call check_direct_mutation() before performing
    any mutation outside the GovernedExecutionSpine. The guard
    decides whether to allow, warn, or block based on the
    current enforcement mode and the mutation's risk level.
    """

    def __init__(
        self,
        mode: GuardMode = GuardMode.BLOCK_HIGH_RISK,
        event_spine: Any = None,
        journal: Any = None,
    ) -> None:
        self._mode = mode
        self._event_spine = event_spine
        self._journal = journal
        self._violations: list[Violation] = []
        self._lock = threading.Lock()
        self._total_violations: int = 0
        self._total_blocked: int = 0
        self._total_allowed: int = 0

    def check_direct_mutation(
        self,
        source: str,
        description: str,
        risk_level: str = "medium",
    ) -> bool:
        """Check whether a direct mutation should be allowed.

        Returns True if the mutation is BLOCKED (caller must abort).
        Returns False if the mutation is allowed (caller may proceed).
        """
        if self._mode == GuardMode.OFF:
            self._total_allowed += 1
            return False

        should_block = self._should_block(risk_level)
        violation = Violation(
            source=source,
            description=description,
            risk_level=risk_level,
            blocked=should_block,
        )

        with self._lock:
            if len(self._violations) >= _MAX_VIOLATIONS:
                self._violations = self._violations[-(_MAX_VIOLATIONS // 2):]
            self._violations.append(violation)
            self._total_violations += 1

        if should_block:
            self._total_blocked += 1
            logger.warning(
                "SPINE GUARD BLOCKED [%s]: %s — %s (risk=%s)",
                self._mode.value, source, description, risk_level,
            )
        else:
            self._total_allowed += 1
            logger.warning(
                "SPINE VIOLATION [%s]: %s — %s (risk=%s)",
                self._mode.value, source, description, risk_level,
            )

        self._emit_event(violation)
        self._record_journal(violation)

        return should_block

    def report_direct_mutation(self, source: str, description: str) -> None:
        """Legacy compatibility — report a violation without risk classification.

        Equivalent to check_direct_mutation with risk_level="medium".
        Does NOT return a blocking decision (legacy callers don't check).
        """
        self.check_direct_mutation(source, description, risk_level="medium")

    def _should_block(self, risk_level: str) -> bool:
        if self._mode == GuardMode.OFF:
            return False
        if self._mode == GuardMode.WARN:
            return False
        if self._mode == GuardMode.BLOCK_HIGH_RISK:
            return _RISK_SEVERITY.get(risk_level, 1) >= _RISK_SEVERITY["medium"]
        if self._mode == GuardMode.ENFORCE_ALL:
            return True
        return False

    def _emit_event(self, violation: Violation) -> None:
        if self._event_spine is None:
            return
        try:
            from substrate.organism.event_spine import EventDomain, EventPriority
            priority = EventPriority.CRITICAL if violation.blocked else EventPriority.HIGH
            self._event_spine.emit(
                EventDomain.GOVERNANCE,
                "spine_guard_violation" if not violation.blocked else "spine_guard_blocked",
                violation.source,
                violation.to_dict(),
                priority=priority,
            )
        except Exception as exc:
            logger.debug("spine guard event emission failed: %s", exc)

    def _record_journal(self, violation: Violation) -> None:
        if self._journal is None:
            return
        try:
            from substrate.organism.execution_journal import JournalPhase
            self._journal.record(
                envelope_id=f"guard-{int(violation.timestamp * 1000)}",
                phase=JournalPhase.GOVERNANCE_CHECK,
                source=f"spine_guard:{violation.source}",
                details={
                    "description": violation.description,
                    "risk_level": violation.risk_level,
                    "blocked": violation.blocked,
                    "guard_mode": self._mode.value,
                },
            )
        except Exception as exc:
            logger.debug("spine guard journal recording failed: %s", exc)

    @property
    def mode(self) -> GuardMode:
        return self._mode

    def set_mode(self, mode: GuardMode) -> None:
        old = self._mode
        self._mode = mode
        logger.info("SpineGuard mode changed: %s → %s", old.value, mode.value)

        if self._event_spine is not None:
            try:
                from substrate.organism.event_spine import EventDomain, EventPriority
                self._event_spine.emit(
                    EventDomain.GOVERNANCE,
                    "spine_guard_mode_changed",
                    "spine_guard",
                    {"old_mode": old.value, "new_mode": mode.value},
                    priority=EventPriority.HIGH,
                )
            except Exception:
                pass

    def recent_violations(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return [v.to_dict() for v in self._violations[-limit:]]

    def blocked_violations(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            blocked = [v for v in self._violations if v.blocked]
        return [v.to_dict() for v in blocked[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            recent_count = len(self._violations)
        return {
            "mode": self._mode.value,
            "total_violations": self._total_violations,
            "total_blocked": self._total_blocked,
            "total_allowed": self._total_allowed,
            "recent_violations": recent_count,
        }
