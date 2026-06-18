"""Decision Impact Engine — blast radius analysis for strategic decisions.

Answers: "If this decision changes, what breaks?" Composes lineage,
assumptions, and reality graph to compute affected goals, work packets,
and cascading invalidations.

Campaign 9.5 — Decision Intelligence & Strategic Memory.
UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class DecisionImpact:
    decision_id: str = ""
    decision_title: str = ""
    affected_goals: list[dict[str, Any]] = field(default_factory=list)
    affected_work_packets: list[dict[str, Any]] = field(default_factory=list)
    affected_decisions: list[dict[str, Any]] = field(default_factory=list)
    blast_radius: int = 0
    risk_level: str = "low"
    cascading_invalidations: list[str] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_title": self.decision_title,
            "affected_goals": list(self.affected_goals),
            "affected_work_packets": list(self.affected_work_packets),
            "affected_decisions": list(self.affected_decisions),
            "blast_radius": self.blast_radius,
            "risk_level": self.risk_level,
            "cascading_invalidations": list(self.cascading_invalidations),
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionImpact:
        return cls(
            decision_id=d.get("decision_id", ""),
            decision_title=d.get("decision_title", ""),
            affected_goals=d.get("affected_goals", []),
            affected_work_packets=d.get("affected_work_packets", []),
            affected_decisions=d.get("affected_decisions", []),
            blast_radius=d.get("blast_radius", 0),
            risk_level=d.get("risk_level", "low"),
            cascading_invalidations=d.get("cascading_invalidations", []),
            generated_at=d.get("generated_at", 0.0),
        )


# ── Engine ────────────────────────────────────────────────────────────────


class DecisionImpactEngine:
    """Blast radius analysis for strategic decisions."""

    def __init__(
        self,
        decision_registry: Any | None = None,
        decision_lineage: Any | None = None,
        assumption_tracking: Any | None = None,
        reality_graph: Any | None = None,
        goal_hierarchy: Any | None = None,
    ) -> None:
        self._decision_registry = decision_registry
        self._decision_lineage = decision_lineage
        self._assumption_tracking = assumption_tracking
        self._reality_graph = reality_graph
        self._goal_hierarchy = goal_hierarchy

    def assess(self, decision_id: str) -> DecisionImpact:
        """Assess the full impact/blast radius of a decision."""
        result = DecisionImpact(
            decision_id=decision_id,
            generated_at=time.time(),
        )

        decision = self._get_decision(decision_id)
        if not decision:
            return result

        result.decision_title = decision.title

        result.affected_goals = self._find_affected_goals(decision)
        result.affected_work_packets = self._find_affected_work(decision)
        result.affected_decisions = self._find_affected_decisions(decision)
        result.cascading_invalidations = self._find_cascading_invalidations(
            decision
        )

        result.blast_radius = (
            len(result.affected_goals)
            + len(result.affected_work_packets)
            + len(result.affected_decisions)
            + len(result.cascading_invalidations)
        )
        result.risk_level = self._classify_risk(result.blast_radius)

        return result

    def assess_change(
        self, decision_id: str, proposed_status: str
    ) -> DecisionImpact:
        """Assess impact of changing a decision's status."""
        impact = self.assess(decision_id)
        if proposed_status in ("invalidated", "superseded"):
            if impact.blast_radius >= 5:
                impact.risk_level = "critical"
            elif impact.blast_radius >= 3:
                impact.risk_level = "high"
        return impact

    def highest_impact(self, limit: int = 5) -> list[DecisionImpact]:
        """Return the decisions with highest blast radius."""
        if not self._decision_registry:
            return []
        try:
            decisions = self._decision_registry.active_decisions()
            impacts = [self.assess(d.decision_id) for d in decisions]
            impacts.sort(key=lambda i: i.blast_radius, reverse=True)
            return impacts[:limit]
        except Exception:
            logger.debug("Failed to compute highest impact", exc_info=True)
            return []

    def summary(self) -> dict[str, Any]:
        """Aggregated impact summary."""
        impacts = self.highest_impact(limit=100)
        if not impacts:
            return {
                "total_assessed": 0,
                "high_impact_count": 0,
                "average_blast_radius": 0.0,
                "generated_at": time.time(),
            }
        total_br = sum(i.blast_radius for i in impacts)
        high_count = sum(
            1 for i in impacts if i.risk_level in ("high", "critical")
        )
        return {
            "total_assessed": len(impacts),
            "high_impact_count": high_count,
            "average_blast_radius": total_br / len(impacts) if impacts else 0.0,
            "generated_at": time.time(),
        }

    # ── Internal ──────────────────────────────────────────────────────

    def _get_decision(self, decision_id: str) -> Any | None:
        if not self._decision_registry:
            return None
        try:
            return self._decision_registry.get(decision_id)
        except Exception:
            logger.debug("Failed to get decision %s", decision_id, exc_info=True)
            return None

    def _find_affected_goals(self, decision: Any) -> list[dict[str, Any]]:
        """Find all goals affected by this decision."""
        goals: list[dict[str, Any]] = []
        seen: set[str] = set()

        for goal_id in getattr(decision, "goal_refs", []):
            if goal_id in seen:
                continue
            seen.add(goal_id)
            goals.append({
                "goal_id": goal_id,
                "relationship": "direct",
            })
            if self._goal_hierarchy:
                try:
                    descendants = self._goal_hierarchy.descendants(goal_id)
                    for child in descendants:
                        child_id = child.goal_id if hasattr(child, "goal_id") else str(child)
                        if child_id not in seen:
                            seen.add(child_id)
                            goals.append({
                                "goal_id": child_id,
                                "relationship": "descendant",
                            })
                except Exception:
                    logger.debug("Failed to get descendants", exc_info=True)

        return goals

    def _find_affected_work(self, decision: Any) -> list[dict[str, Any]]:
        """Find all work packets affected by this decision."""
        work: list[dict[str, Any]] = []
        for wp_id in getattr(decision, "work_packet_refs", []):
            work.append({"work_packet_id": wp_id, "relationship": "direct"})
        return work

    def _find_affected_decisions(
        self, decision: Any
    ) -> list[dict[str, Any]]:
        """Find decisions that depend on or supersede this one."""
        affected: list[dict[str, Any]] = []
        if not self._decision_registry:
            return affected

        try:
            all_decisions = self._decision_registry.list_decisions()
            for d in all_decisions:
                if d.decision_id == decision.decision_id:
                    continue
                if d.supersedes == decision.decision_id:
                    affected.append({
                        "decision_id": d.decision_id,
                        "title": d.title,
                        "relationship": "supersedes_this",
                    })
                if decision.decision_id in getattr(d, "goal_refs", []):
                    affected.append({
                        "decision_id": d.decision_id,
                        "title": d.title,
                        "relationship": "shares_goal",
                    })
        except Exception:
            logger.debug("Failed to find affected decisions", exc_info=True)

        return affected

    def _find_cascading_invalidations(
        self, decision: Any
    ) -> list[str]:
        """Find assumptions that would be invalidated if decision changes."""
        if not self._assumption_tracking:
            return []

        cascading: list[str] = []
        try:
            assumptions = self._assumption_tracking.assumptions_for_decision(
                decision.decision_id
            )
            for asm in assumptions:
                asm_id = asm.assumption_id if hasattr(asm, "assumption_id") else str(asm)
                cascading.append(asm_id)
        except Exception:
            logger.debug("Failed to find cascading invalidations", exc_info=True)

        return cascading

    def _classify_risk(self, blast_radius: int) -> str:
        """Deterministic risk classification from blast radius."""
        if blast_radius >= 10:
            return "critical"
        elif blast_radius >= 5:
            return "high"
        elif blast_radius >= 2:
            return "medium"
        return "low"
