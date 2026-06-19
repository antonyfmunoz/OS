"""Goal Alignment Engine — ensure work supports goals.

Campaign 8.4. UMH substrate layer. Instance-agnostic.

Measures the alignment between active work and the goal hierarchy.
Detects unlinked work (work with no goal connection) and orphan goals
(goals with no active work).

Read-only. No mutation. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class AlignmentReport:
    total_work_count: int = 0
    linked_work_count: int = 0
    unlinked_work_count: int = 0
    alignment_score: float = 0.0
    goal_coverage: dict[str, int] = field(default_factory=dict)
    orphan_goals: list[dict[str, str]] = field(default_factory=list)
    unlinked_items: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_work_count": self.total_work_count,
            "linked_work_count": self.linked_work_count,
            "unlinked_work_count": self.unlinked_work_count,
            "alignment_score": round(self.alignment_score, 4),
            "goal_coverage": self.goal_coverage,
            "orphan_goal_count": len(self.orphan_goals),
            "orphan_goals": self.orphan_goals,
            "unlinked_items": self.unlinked_items,
            "generated_at": self.generated_at,
        }


# ── Engine ────────────────────────────────────────────────────────────────


class GoalAlignmentEngine:
    """Measure alignment between work and goals. Read-only.

    Composes:
      - GoalRegistry (Phase 4) — goal data
      - GoalHierarchyEngine (C8.1) — tree traversal for upward tracing
      - RealityGraph (C5) — work packet entities
      - RuntimeAwarenessRuntime (C6.3) — active work packets
    """

    def __init__(
        self,
        goal_registry: Any | None = None,
        goal_hierarchy: Any | None = None,
        reality_graph: Any | None = None,
        runtime_awareness: Any | None = None,
    ) -> None:
        self._registry = goal_registry
        self._hierarchy = goal_hierarchy
        self._reality = reality_graph
        self._runtime = runtime_awareness

    def _get_work_items(self) -> list[dict[str, Any]]:
        """Gather all work items from reality graph and runtime awareness."""
        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        if self._reality is not None:
            try:
                from substrate.organism.reality_graph import RealityEntityType
                packets = self._reality.find_by_type(RealityEntityType.WORK_PACKET)
                for p in packets:
                    if p.entity_id not in seen_ids:
                        seen_ids.add(p.entity_id)
                        items.append({
                            "work_id": p.entity_id,
                            "title": p.name,
                            "goal_id": p.properties.get("goal_id", ""),
                            "goal_refs": p.properties.get("goal_refs", []),
                            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                        })
            except Exception as exc:
                logger.debug("alignment: reality graph query failed: %s", exc)

        if self._runtime is not None:
            try:
                snap = self._runtime.snapshot()
                for wp in getattr(snap, "active_work_packets", []):
                    if isinstance(wp, dict):
                        wid = wp.get("packet_id", wp.get("work_id", ""))
                        if wid and wid not in seen_ids:
                            seen_ids.add(wid)
                            items.append({
                                "work_id": wid,
                                "title": wp.get("title", ""),
                                "goal_id": wp.get("goal_id", ""),
                                "goal_refs": wp.get("goal_refs", []),
                                "status": wp.get("status", "active"),
                            })
            except Exception as exc:
                logger.debug("alignment: runtime awareness query failed: %s", exc)

        return items

    def _is_linked(self, item: dict[str, Any]) -> bool:
        """Check if a work item is linked to any goal."""
        if item.get("goal_id"):
            return True
        if item.get("goal_refs"):
            return True
        return False

    def alignment_score(self) -> float:
        """Ratio of linked to total work. 0-1."""
        items = self._get_work_items()
        if not items:
            return 1.0
        linked = sum(1 for item in items if self._is_linked(item))
        return linked / len(items)

    def unlinked_work(self) -> list[dict[str, Any]]:
        """Work items with no goal connection."""
        items = self._get_work_items()
        return [item for item in items if not self._is_linked(item)]

    def goal_for_work(self, work_id: str) -> list[dict[str, str]]:
        """Trace work → goal chain upward to vision.

        This is the Campaign 8 acceptance test:
        Work Packet → Project → Initiative → Outcome → Objective → Vision
        """
        items = self._get_work_items()
        item = next((i for i in items if i.get("work_id") == work_id), None)
        if not item:
            return []

        goal_id = item.get("goal_id", "")
        if not goal_id:
            refs = item.get("goal_refs", [])
            goal_id = refs[0] if refs else ""
        if not goal_id:
            return []

        if self._hierarchy is not None:
            try:
                return self._hierarchy.trace_to_vision(goal_id)
            except Exception as exc:
                logger.debug("alignment: trace to vision failed: %s", exc)

        if self._registry is not None:
            goal = self._registry.get(goal_id)
            if goal:
                return [{
                    "goal_id": goal.goal_id,
                    "title": goal.title,
                    "goal_type": goal.goal_type.value if hasattr(goal.goal_type, "value") else str(goal.goal_type),
                }]

        return []

    def coverage(self) -> dict[str, int]:
        """Which goals have active work, and how many items each."""
        items = self._get_work_items()
        coverage: dict[str, int] = {}
        for item in items:
            gid = item.get("goal_id", "")
            if gid:
                coverage[gid] = coverage.get(gid, 0) + 1
            for ref in item.get("goal_refs", []):
                if ref and ref != gid:
                    coverage[ref] = coverage.get(ref, 0) + 1
        return coverage

    def orphan_goals(self) -> list[Any]:
        """Active goals with zero linked work."""
        if self._registry is None:
            return []
        cov = self.coverage()
        active = self._registry.active_goals()
        return [g for g in active if g.goal_id not in cov]

    def report(self) -> AlignmentReport:
        """Full alignment snapshot."""
        items = self._get_work_items()
        linked = [i for i in items if self._is_linked(i)]
        unlinked = [i for i in items if not self._is_linked(i)]
        cov = self.coverage()
        orphans = self.orphan_goals()

        return AlignmentReport(
            total_work_count=len(items),
            linked_work_count=len(linked),
            unlinked_work_count=len(unlinked),
            alignment_score=len(linked) / len(items) if items else 1.0,
            goal_coverage=cov,
            orphan_goals=[
                {"goal_id": g.goal_id, "title": g.title}
                for g in orphans
            ],
            unlinked_items=unlinked,
            generated_at=time.time(),
        )
