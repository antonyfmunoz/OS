"""Capability Gap Engine — detect missing or immature capabilities for goals.

Campaign 10.1. UMH substrate layer.

Maps goals → required_capabilities → existing capabilities via deterministic
fuzzy matching. Classifies gaps by severity based on whether a capability
exists and its maturity level.

Wraps CapabilityRuntime + GoalRegistry. Does NOT own capability data.
Deterministic. No LLM. No execution. No mutation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CapabilityGapSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CapabilityGap:
    gap_id: str = field(default_factory=lambda: f"cgap-{uuid4().hex[:8]}")
    goal_id: str = ""
    goal_title: str = ""
    required_capability: str = ""
    matched_capability_id: str = ""
    matched_capability_name: str = ""
    matched_maturity: str = ""
    severity: CapabilityGapSeverity = CapabilityGapSeverity.CRITICAL
    recommendation: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "required_capability": self.required_capability,
            "matched_capability_id": self.matched_capability_id,
            "matched_capability_name": self.matched_capability_name,
            "matched_maturity": self.matched_maturity,
            "severity": self.severity.value,
            "recommendation": self.recommendation,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CapabilityGap:
        d = dict(d)
        sev = d.get("severity", "critical")
        try:
            d["severity"] = CapabilityGapSeverity(sev)
        except ValueError:
            d["severity"] = CapabilityGapSeverity.CRITICAL
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CapabilityGapEngine:
    """Detects missing or immature capabilities required by goals."""

    def __init__(
        self,
        capability_runtime: Any | None = None,
        goal_registry: Any | None = None,
    ) -> None:
        self._capability_runtime = capability_runtime
        self._goal_registry = goal_registry

    def analyze_gaps(self) -> list[CapabilityGap]:
        """Analyze all active goals for capability gaps."""
        if not self._goal_registry:
            return []

        gaps: list[CapabilityGap] = []
        try:
            goals = self._goal_registry.list_goals()
        except Exception:
            try:
                goals = self._goal_registry.list_goals(status=None)
            except Exception as exc:
                logger.debug("capability_gap: cannot list goals: %s", exc)
                return []

        for goal in goals:
            goal_gaps = self._analyze_goal(goal)
            gaps.extend(goal_gaps)

        gaps.sort(key=lambda g: _SEVERITY_ORDER.get(g.severity, 99))
        return gaps

    def gaps_for_goal(self, goal_id: str) -> list[CapabilityGap]:
        """Analyze capability gaps for a single goal."""
        if not self._goal_registry:
            return []
        try:
            goal = self._goal_registry.get(goal_id)
            if goal is None:
                return []
            return self._analyze_goal(goal)
        except Exception as exc:
            logger.debug("capability_gap: gaps_for_goal failed: %s", exc)
            return []

    def critical_gaps(self) -> list[CapabilityGap]:
        """Return only CRITICAL severity gaps (no match at all)."""
        return [g for g in self.analyze_gaps() if g.severity == CapabilityGapSeverity.CRITICAL]

    def immature_gaps(self) -> list[CapabilityGap]:
        """Gaps where capability exists but is below OPERATIONAL maturity."""
        return [
            g for g in self.analyze_gaps()
            if g.severity in (CapabilityGapSeverity.HIGH, CapabilityGapSeverity.MEDIUM)
        ]

    def satisfied(self) -> list[CapabilityGap]:
        """Gaps where capability is OPERATIONAL or better."""
        return [g for g in self.analyze_gaps() if g.severity == CapabilityGapSeverity.LOW]

    def next_to_build(self, limit: int = 5) -> list[dict[str, Any]]:
        """Recommend which capabilities to build or mature next.

        Priority: CRITICAL (missing) first, then HIGH (emerging), then MEDIUM.
        Within each severity, goals with more required capabilities rank higher.
        """
        gaps = self.analyze_gaps()
        seen: set[str] = set()
        result: list[dict[str, Any]] = []

        for gap in gaps:
            key = gap.required_capability.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            result.append({
                "required_capability": gap.required_capability,
                "severity": gap.severity.value,
                "matched_capability_id": gap.matched_capability_id,
                "matched_maturity": gap.matched_maturity,
                "recommendation": gap.recommendation,
                "goal_id": gap.goal_id,
                "goal_title": gap.goal_title,
            })
            if len(result) >= limit:
                break

        return result

    def gap_summary(self) -> dict[str, Any]:
        """Summary counts by severity."""
        gaps = self.analyze_gaps()
        by_severity: dict[str, int] = {}
        for sev in CapabilityGapSeverity:
            by_severity[sev.value] = sum(1 for g in gaps if g.severity == sev)

        return {
            "total_gaps": len(gaps),
            "by_severity": by_severity,
            "critical_count": by_severity.get("critical", 0),
            "next_to_build": self.next_to_build(3),
            "generated_at": time.time(),
        }

    def summary(self) -> dict[str, Any]:
        return self.gap_summary()

    # ── Internal ──────────────────────────────────────────────────

    def _analyze_goal(self, goal: Any) -> list[CapabilityGap]:
        """Analyze capability gaps for one goal."""
        required = getattr(goal, "required_capabilities", [])
        if not required:
            return []

        goal_id = getattr(goal, "goal_id", "")
        goal_title = getattr(goal, "title", "")
        gaps: list[CapabilityGap] = []

        for req_name in required:
            matched = self._match_capability(req_name)
            if matched is None:
                severity = CapabilityGapSeverity.CRITICAL
                recommendation = f"Build capability: {req_name}"
                gap = CapabilityGap(
                    goal_id=goal_id,
                    goal_title=goal_title,
                    required_capability=req_name,
                    severity=severity,
                    recommendation=recommendation,
                )
            else:
                maturity_str = matched.maturity.value if hasattr(matched.maturity, "value") else str(matched.maturity)
                severity = self._classify_severity(maturity_str)
                recommendation = self._generate_recommendation(
                    req_name, matched, severity
                )
                gap = CapabilityGap(
                    goal_id=goal_id,
                    goal_title=goal_title,
                    required_capability=req_name,
                    matched_capability_id=matched.capability_id,
                    matched_capability_name=matched.name,
                    matched_maturity=maturity_str,
                    severity=severity,
                    recommendation=recommendation,
                )
            gaps.append(gap)

        return gaps

    def _match_capability(self, required_name: str) -> Any | None:
        """Deterministic fuzzy match: lowercase substring containment."""
        if not self._capability_runtime:
            return None

        try:
            all_caps = self._capability_runtime.list_capabilities()
        except Exception:
            return None

        req_lower = required_name.lower().strip()
        if not req_lower:
            return None

        best_match: Any = None
        best_score: int = 0

        for cap in all_caps:
            cap_lower = cap.name.lower().strip()
            if cap_lower == req_lower:
                return cap
            if req_lower in cap_lower or cap_lower in req_lower:
                score = len(set(req_lower.split()) & set(cap_lower.split()))
                if score > best_score:
                    best_score = score
                    best_match = cap

        return best_match

    def _classify_severity(self, maturity: str) -> CapabilityGapSeverity:
        """Classify gap severity from maturity level."""
        maturity_lower = maturity.lower()
        if maturity_lower in ("institutional", "operational"):
            return CapabilityGapSeverity.LOW
        if maturity_lower == "validated":
            return CapabilityGapSeverity.MEDIUM
        if maturity_lower == "emerging":
            return CapabilityGapSeverity.HIGH
        return CapabilityGapSeverity.CRITICAL

    def _generate_recommendation(
        self,
        required_name: str,
        matched: Any,
        severity: CapabilityGapSeverity,
    ) -> str:
        """Deterministic recommendation based on severity."""
        name = matched.name if hasattr(matched, "name") else str(matched)
        maturity = matched.maturity.value if hasattr(matched.maturity, "value") else str(getattr(matched, "maturity", "unknown"))
        if severity == CapabilityGapSeverity.LOW:
            return f"Satisfied: {name} is {maturity}"
        if severity == CapabilityGapSeverity.MEDIUM:
            return f"Mature capability: {name} from {maturity} to operational"
        if severity == CapabilityGapSeverity.HIGH:
            return f"Accelerate capability: {name} is only {maturity}"
        return f"Build capability: {required_name}"


_SEVERITY_ORDER: dict[CapabilityGapSeverity, int] = {
    CapabilityGapSeverity.CRITICAL: 0,
    CapabilityGapSeverity.HIGH: 1,
    CapabilityGapSeverity.MEDIUM: 2,
    CapabilityGapSeverity.LOW: 3,
}
