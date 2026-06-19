"""Risk Engine — unified risk register synthesis.

Campaign 7.2. UMH substrate layer.

Executive synthesis layer ABOVE ProjectionEngine. Merges risk signals
from projection forecasting, runtime awareness (blocked work),
documentation awareness (stale docs), and knowledge awareness
(unmet constraints) into a unified risk register.

Does NOT reimplement risk detection — delegates to ProjectionEngine.

Read-only. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────


class RiskCategory(str, Enum):
    BLOCKER = "blocker"
    DRIFT = "drift"
    DEPENDENCY = "dependency"
    GOVERNANCE = "governance"
    DOCUMENTATION = "documentation"
    EXECUTION = "execution"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class UnifiedRisk:
    risk_id: str = field(default_factory=lambda: f"risk-{uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    category: str = RiskCategory.EXECUTION.value
    severity: str = "medium"
    probability: float = 0.5
    impact: float = 0.5
    risk_score: float = 0.0
    source_engine: str = ""
    entity_refs: list[str] = field(default_factory=list)
    mitigation: str = ""
    detected_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.risk_score == 0.0:
            self.risk_score = round(self.probability * self.impact, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "probability": round(self.probability, 4),
            "impact": round(self.impact, 4),
            "risk_score": round(self.risk_score, 4),
            "source_engine": self.source_engine,
            "entity_refs": self.entity_refs,
            "mitigation": self.mitigation,
            "detected_at": self.detected_at,
        }


_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


# ── Engine ────────────────────────────────────────────────────────────


class RiskEngine:
    """Unified risk register — merges projection risks with operational signals.

    Sources:
      - ProjectionEngine → strategic risks (forecasted)
      - RuntimeAwareness → blocked work (active blockers)
      - DocumentationAwareness → stale docs (documentation risk)
      - KnowledgeAwareness → unmet constraints (execution risk)
    """

    def __init__(
        self,
        projection_engine: Any | None = None,
        runtime_awareness: Any | None = None,
        documentation_awareness: Any | None = None,
        knowledge_awareness: Any | None = None,
    ) -> None:
        self._projection_engine = projection_engine
        self._runtime_awareness = runtime_awareness
        self._documentation_awareness = documentation_awareness
        self._knowledge_awareness = knowledge_awareness
        self._last_risks: list[UnifiedRisk] = []

    def detect_risks(self) -> list[UnifiedRisk]:
        """Merge all risk sources into unified register."""
        risks: list[UnifiedRisk] = []

        risks.extend(self._risks_from_projection())
        risks.extend(self._risks_from_blockers())
        risks.extend(self._risks_from_stale_docs())
        risks.extend(self._risks_from_constraints())

        risks.sort(key=lambda r: r.risk_score, reverse=True)
        self._last_risks = risks
        return risks

    def high_risks(self) -> list[UnifiedRisk]:
        """Return HIGH or CRITICAL severity risks."""
        if not self._last_risks:
            self.detect_risks()
        return [
            r for r in self._last_risks
            if r.severity in ("high", "critical")
        ]

    def by_category(self, category: str) -> list[UnifiedRisk]:
        """Filter risks by category."""
        if not self._last_risks:
            self.detect_risks()
        return [r for r in self._last_risks if r.category == category]

    # ── Source extraction ─────────────────────────────────────────

    def _risks_from_projection(self) -> list[UnifiedRisk]:
        if self._projection_engine is None:
            return []
        try:
            state = self._projection_engine.get_projection_state()
            raw_risks = state.get("risks", [])
            results: list[UnifiedRisk] = []
            for r in raw_risks:
                if hasattr(r, "to_dict"):
                    rd = r.to_dict()
                elif isinstance(r, dict):
                    rd = r
                else:
                    continue
                results.append(UnifiedRisk(
                    title=rd.get("title", ""),
                    description=rd.get("description", rd.get("evidence", "")),
                    category=rd.get("risk_type", RiskCategory.EXECUTION.value),
                    severity=rd.get("severity", "medium"),
                    probability=rd.get("probability", 0.5),
                    impact=rd.get("impact", 0.5),
                    source_engine="projection_engine",
                    entity_refs=[rd.get("related_goal_id", "")] if rd.get("related_goal_id") else [],
                    mitigation=rd.get("mitigation", ""),
                    detected_at=rd.get("created_at", time.time()),
                ))
            return results
        except Exception as exc:
            logger.debug("risk_engine: projection extraction failed: %s", exc)
            return []

    def _risks_from_blockers(self) -> list[UnifiedRisk]:
        if self._runtime_awareness is None:
            return []
        try:
            blocked = self._runtime_awareness.blocked_work()
            if not blocked:
                return []
            count = len(blocked)
            severity = "critical" if count >= 3 else "high" if count >= 2 else "medium"
            titles = [b.get("title", b.get("packet_id", "?")) for b in blocked[:3]]
            return [UnifiedRisk(
                title=f"{count} blocked work item(s)",
                description=f"Blocked: {', '.join(titles)}",
                category=RiskCategory.BLOCKER.value,
                severity=severity,
                probability=0.9,
                impact=0.7 + 0.1 * min(count, 3),
                source_engine="runtime_awareness",
                mitigation="Investigate and resolve blockers",
            )]
        except Exception as exc:
            logger.debug("risk_engine: blocker extraction failed: %s", exc)
            return []

    def _risks_from_stale_docs(self) -> list[UnifiedRisk]:
        if self._documentation_awareness is None:
            return []
        try:
            stale = self._documentation_awareness.find_stale_docs()
            if not stale:
                return []
            count = len(stale)
            severity = "high" if count >= 5 else "medium" if count >= 2 else "low"
            names = []
            for d in stale[:3]:
                if hasattr(d, "name"):
                    names.append(d.name)
                elif isinstance(d, dict):
                    names.append(d.get("name", "?"))
            return [UnifiedRisk(
                title=f"{count} stale document(s)",
                description=f"Stale: {', '.join(names)}",
                category=RiskCategory.DOCUMENTATION.value,
                severity=severity,
                probability=0.7,
                impact=0.4 + 0.1 * min(count, 5),
                source_engine="documentation_awareness",
                mitigation="Review and update stale documentation",
            )]
        except Exception as exc:
            logger.debug("risk_engine: stale docs extraction failed: %s", exc)
            return []

    def _risks_from_constraints(self) -> list[UnifiedRisk]:
        if self._knowledge_awareness is None:
            return []
        try:
            constraints = self._knowledge_awareness.find_constraints()
            if not constraints:
                return []
            count = len(constraints)
            if count <= 2:
                return []
            severity = "high" if count >= 10 else "medium"
            return [UnifiedRisk(
                title=f"{count} active constraint(s) to monitor",
                description="High constraint density increases execution risk",
                category=RiskCategory.EXECUTION.value,
                severity=severity,
                probability=0.5,
                impact=0.5,
                source_engine="knowledge_awareness",
                mitigation="Prioritize constraint-heavy work areas",
            )]
        except Exception as exc:
            logger.debug("risk_engine: constraint extraction failed: %s", exc)
            return []
