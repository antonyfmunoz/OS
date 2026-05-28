"""Operator Compression — reduce human operational burden.

Tracks operator interactions and identifies automation candidates:
  - actions the organism handled autonomously
  - actions requiring approval
  - actions requiring intervention
  - repetitive operator action patterns

When the operator repeats the same intervention pattern, this
engine flags it as an automation candidate and suggests:
  - new execution policies
  - runtime routing rules
  - objective decomposition improvements

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class InterventionType(str, Enum):
    APPROVAL = "approval"
    OVERRIDE = "override"
    MANUAL_EXECUTION = "manual_execution"
    RESTART = "restart"
    CONFIGURATION_CHANGE = "configuration_change"
    ESCALATION_RESPONSE = "escalation_response"
    ERROR_CORRECTION = "error_correction"


@dataclass
class OperatorAction:
    action_id: str
    intervention_type: InterventionType
    description: str
    context: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0

    def signature(self) -> str:
        return f"{self.intervention_type.value}:{self.context}"


@dataclass
class AutomationCandidate:
    pattern_signature: str
    intervention_type: InterventionType
    occurrence_count: int
    total_operator_seconds: float
    first_seen: float
    last_seen: float
    suggested_automation: str
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_signature": self.pattern_signature,
            "intervention_type": self.intervention_type.value,
            "occurrence_count": self.occurrence_count,
            "total_operator_seconds": round(self.total_operator_seconds, 1),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "suggested_automation": self.suggested_automation,
            "examples": self.examples[:3],
        }


_AUTOMATION_SUGGESTIONS: dict[InterventionType, str] = {
    InterventionType.APPROVAL: "Create pre-approved execution policy for this task class",
    InterventionType.OVERRIDE: "Adjust governance thresholds to match operator judgment",
    InterventionType.MANUAL_EXECUTION: "Build automated execution path for this operation",
    InterventionType.RESTART: "Add auto-restart policy with health check",
    InterventionType.CONFIGURATION_CHANGE: "Create adaptive configuration rule",
    InterventionType.ESCALATION_RESPONSE: "Lower risk classification for this task pattern",
    InterventionType.ERROR_CORRECTION: "Add deterministic error correction handler",
}

_PROMOTION_THRESHOLD = 3
_MAX_ACTIONS = 2000


class OperatorCompression:
    """Tracks operator burden and identifies automation opportunities.

    Records every operator interaction, detects repeated patterns,
    and surfaces automation candidates that would eliminate manual work.
    """

    def __init__(
        self,
        event_spine: Any | None = None,
        promotion_threshold: int = _PROMOTION_THRESHOLD,
    ) -> None:
        self._event_spine = event_spine
        self._promotion_threshold = promotion_threshold
        self._actions: deque[OperatorAction] = deque(maxlen=_MAX_ACTIONS)
        self._pattern_counts: dict[str, int] = {}
        self._pattern_first_seen: dict[str, float] = {}
        self._pattern_last_seen: dict[str, float] = {}
        self._pattern_total_seconds: dict[str, float] = {}
        self._pattern_type: dict[str, InterventionType] = {}
        self._pattern_examples: dict[str, list[str]] = {}
        self._total_autonomous: int = 0
        self._total_manual: int = 0

    def record_autonomous(self) -> None:
        self._total_autonomous += 1

    def record_intervention(self, action: OperatorAction) -> None:
        self._actions.append(action)
        self._total_manual += 1

        sig = action.signature()
        self._pattern_counts[sig] = self._pattern_counts.get(sig, 0) + 1
        self._pattern_type[sig] = action.intervention_type

        if sig not in self._pattern_first_seen:
            self._pattern_first_seen[sig] = action.timestamp
        self._pattern_last_seen[sig] = action.timestamp

        self._pattern_total_seconds[sig] = (
            self._pattern_total_seconds.get(sig, 0.0) + action.duration_seconds
        )

        examples = self._pattern_examples.setdefault(sig, [])
        if len(examples) < 5:
            examples.append(action.description[:200])

    def automation_candidates(self) -> list[AutomationCandidate]:
        candidates: list[AutomationCandidate] = []
        for sig, count in self._pattern_counts.items():
            if count < self._promotion_threshold:
                continue
            itype = self._pattern_type.get(sig, InterventionType.MANUAL_EXECUTION)
            candidates.append(AutomationCandidate(
                pattern_signature=sig,
                intervention_type=itype,
                occurrence_count=count,
                total_operator_seconds=self._pattern_total_seconds.get(sig, 0.0),
                first_seen=self._pattern_first_seen.get(sig, 0.0),
                last_seen=self._pattern_last_seen.get(sig, 0.0),
                suggested_automation=_AUTOMATION_SUGGESTIONS.get(
                    itype, "Automate this repeated pattern"
                ),
                examples=self._pattern_examples.get(sig, []),
            ))
        return sorted(candidates, key=lambda c: c.occurrence_count, reverse=True)

    def compression_ratio(self) -> float:
        total = self._total_autonomous + self._total_manual
        if total == 0:
            return 0.0
        return self._total_autonomous / total

    def compression_tick(self) -> dict[str, Any]:
        candidates = self.automation_candidates()
        result = {
            "compression_ratio": round(self.compression_ratio(), 4),
            "total_autonomous": self._total_autonomous,
            "total_manual": self._total_manual,
            "automation_candidates": len(candidates),
            "top_candidates": [c.to_dict() for c in candidates[:5]],
        }

        if candidates and self._event_spine is not None:
            from substrate.organism.event_spine import EventDomain
            self._event_spine.emit(
                EventDomain.OBSERVABILITY,
                "automation_candidates_found",
                "operator_compression",
                {
                    "count": len(candidates),
                    "top": [c.to_dict() for c in candidates[:3]],
                },
            )

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "compression_ratio": round(self.compression_ratio(), 4),
            "total_autonomous": self._total_autonomous,
            "total_manual": self._total_manual,
            "unique_patterns": len(self._pattern_counts),
            "automation_candidates": len(self.automation_candidates()),
        }
