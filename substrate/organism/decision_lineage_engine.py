"""Decision Lineage Engine — causal chain traversal for strategic decisions.

Traces upstream (decision → goals → parent goals) and downstream
(decision → work packets, approvals) to answer "why does this exist?"
and "what breaks if this changes?"

Read-only. Deterministic. Zero LLM calls.

Campaign 9.1 — Decision Intelligence & Strategic Memory.
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
class LineageNode:
    entity_type: str = ""
    entity_id: str = ""
    label: str = ""
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "label": self.label,
            "depth": self.depth,
        }


@dataclass
class DecisionLineage:
    decision_id: str = ""
    decision_title: str = ""
    upstream: list[dict[str, Any]] = field(default_factory=list)
    downstream: list[dict[str, Any]] = field(default_factory=list)
    chain_depth: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_title": self.decision_title,
            "upstream": list(self.upstream),
            "downstream": list(self.downstream),
            "chain_depth": self.chain_depth,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionLineage:
        return cls(
            decision_id=d.get("decision_id", ""),
            decision_title=d.get("decision_title", ""),
            upstream=d.get("upstream", []),
            downstream=d.get("downstream", []),
            chain_depth=d.get("chain_depth", 0),
            generated_at=d.get("generated_at", 0.0),
        )


# ── Engine ────────────────────────────────────────────────────────────────


class DecisionLineageEngine:
    """Traces causal chains through decisions, goals, and work."""

    def __init__(
        self,
        decision_registry: Any | None = None,
        goal_registry: Any | None = None,
        goal_hierarchy: Any | None = None,
        reality_graph: Any | None = None,
    ) -> None:
        self._decision_registry = decision_registry
        self._goal_registry = goal_registry
        self._goal_hierarchy = goal_hierarchy
        self._reality_graph = reality_graph

    # ── Primary API ───────────────────────────────────────────────────

    def trace(self, decision_id: str) -> DecisionLineage:
        """Build full lineage for a single decision."""
        lineage = DecisionLineage(
            decision_id=decision_id,
            generated_at=time.time(),
        )

        if not self._decision_registry:
            return lineage

        try:
            dec = self._decision_registry.get(decision_id)
        except Exception:
            logger.debug("Failed to get decision %s", decision_id, exc_info=True)
            return lineage

        if not dec:
            return lineage

        lineage.decision_title = dec.title

        upstream = self._walk_upstream(dec)
        downstream = self._walk_downstream(dec)

        lineage.upstream = [n.to_dict() for n in upstream]
        lineage.downstream = [n.to_dict() for n in downstream]

        max_depth = 0
        for n in upstream:
            if n.depth > max_depth:
                max_depth = n.depth
        for n in downstream:
            if n.depth > max_depth:
                max_depth = n.depth
        lineage.chain_depth = max_depth

        return lineage

    def full_chain(self, goal_id: str) -> list[DecisionLineage]:
        """All decision lineages connected to a goal and its children."""
        if not self._decision_registry:
            return []

        goal_ids = {goal_id}
        if self._goal_hierarchy:
            try:
                descendants = self._goal_hierarchy.descendants(goal_id)
                for g in descendants:
                    goal_ids.add(g.goal_id if hasattr(g, "goal_id") else str(g))
            except Exception:
                logger.debug("Failed to get descendants for %s", goal_id, exc_info=True)

        seen_decisions: set[str] = set()
        lineages: list[DecisionLineage] = []

        for gid in goal_ids:
            try:
                decisions = self._decision_registry.decisions_for_goal(gid)
            except Exception:
                logger.debug("Failed to query decisions for goal %s", gid, exc_info=True)
                continue

            for dec in decisions:
                if dec.decision_id in seen_decisions:
                    continue
                seen_decisions.add(dec.decision_id)
                lineages.append(self.trace(dec.decision_id))

        return lineages

    def blast_radius(self, decision_id: str) -> dict[str, Any]:
        """Compute what would be affected if this decision changes."""
        result: dict[str, Any] = {
            "decision": decision_id,
            "affected_goals": [],
            "affected_work": [],
            "affected_approvals": [],
            "affected_decisions": [],
            "depth": 0,
        }

        if not self._decision_registry:
            return result

        try:
            dec = self._decision_registry.get(decision_id)
        except Exception:
            logger.debug("Failed to get decision %s", decision_id, exc_info=True)
            return result

        if not dec:
            return result

        affected_goals: list[str] = list(dec.goal_refs)
        affected_work: list[str] = list(dec.work_packet_refs)
        affected_approvals: list[str] = list(dec.approval_refs)
        affected_decisions: list[str] = []
        depth = 1

        if self._goal_hierarchy:
            expanded_goals: list[str] = []
            for gid in dec.goal_refs:
                expanded_goals.append(gid)
                try:
                    descendants = self._goal_hierarchy.descendants(gid)
                    for g in descendants:
                        gid_str = g.goal_id if hasattr(g, "goal_id") else str(g)
                        if gid_str not in expanded_goals:
                            expanded_goals.append(gid_str)
                except Exception:
                    logger.debug("Failed to expand goal %s", gid, exc_info=True)
            affected_goals = expanded_goals
            if len(expanded_goals) > len(dec.goal_refs):
                depth = max(depth, 2)

        if dec.superseded_by:
            affected_decisions.append(dec.superseded_by)
        if dec.supersedes:
            affected_decisions.append(dec.supersedes)

        try:
            all_decisions = self._decision_registry.list_decisions()
            for other in all_decisions:
                if other.decision_id == decision_id:
                    continue
                if other.decision_id in affected_decisions:
                    continue
                for gid in other.goal_refs:
                    if gid in affected_goals:
                        affected_decisions.append(other.decision_id)
                        break
        except Exception:
            logger.debug("Failed to scan related decisions", exc_info=True)

        if affected_decisions:
            depth = max(depth, 3)

        result["affected_goals"] = affected_goals
        result["affected_work"] = affected_work
        result["affected_approvals"] = affected_approvals
        result["affected_decisions"] = affected_decisions
        result["depth"] = depth

        return result

    def summary(self) -> dict[str, Any]:
        """Aggregate lineage statistics."""
        if not self._decision_registry:
            return {
                "total_decisions": 0,
                "average_depth": 0.0,
                "max_depth": 0,
                "generated_at": time.time(),
            }

        try:
            all_decisions = self._decision_registry.list_decisions()
        except Exception:
            logger.debug("Failed to list decisions for summary", exc_info=True)
            return {
                "total_decisions": 0,
                "average_depth": 0.0,
                "max_depth": 0,
                "generated_at": time.time(),
            }

        total = len(all_decisions)
        if total == 0:
            return {
                "total_decisions": 0,
                "average_depth": 0.0,
                "max_depth": 0,
                "generated_at": time.time(),
            }

        depths: list[int] = []
        for dec in all_decisions:
            lineage = self.trace(dec.decision_id)
            depths.append(lineage.chain_depth)

        return {
            "total_decisions": total,
            "average_depth": sum(depths) / len(depths) if depths else 0.0,
            "max_depth": max(depths) if depths else 0,
            "generated_at": time.time(),
        }

    # ── Internal traversal ────────────────────────────────────────────

    def _walk_upstream(self, dec: Any) -> list[LineageNode]:
        """Walk from decision up through goals to vision."""
        nodes: list[LineageNode] = []

        for goal_id in dec.goal_refs:
            goal = self._resolve_goal(goal_id)
            label = goal.title if goal and hasattr(goal, "title") else goal_id
            goal_type = ""
            if goal and hasattr(goal, "goal_type"):
                goal_type = goal.goal_type

            nodes.append(LineageNode(
                entity_type="goal",
                entity_id=goal_id,
                label=label,
                depth=1,
            ))

            if self._goal_hierarchy and goal:
                try:
                    ancestors = self._goal_hierarchy.ancestors(goal_id)
                    for i, ancestor in enumerate(ancestors):
                        anc_id = ancestor.goal_id if hasattr(ancestor, "goal_id") else str(ancestor)
                        anc_label = ancestor.title if hasattr(ancestor, "title") else anc_id
                        nodes.append(LineageNode(
                            entity_type="goal",
                            entity_id=anc_id,
                            label=anc_label,
                            depth=i + 2,
                        ))
                except Exception:
                    logger.debug("Failed to get ancestors for %s", goal_id, exc_info=True)

        return nodes

    def _walk_downstream(self, dec: Any) -> list[LineageNode]:
        """Walk from decision down through work packets and approvals."""
        nodes: list[LineageNode] = []

        for wp_id in dec.work_packet_refs:
            nodes.append(LineageNode(
                entity_type="work_packet",
                entity_id=wp_id,
                label=wp_id,
                depth=1,
            ))

        for ap_id in dec.approval_refs:
            nodes.append(LineageNode(
                entity_type="approval",
                entity_id=ap_id,
                label=ap_id,
                depth=1,
            ))

        for proj_id in dec.project_refs:
            nodes.append(LineageNode(
                entity_type="project",
                entity_id=proj_id,
                label=proj_id,
                depth=1,
            ))

        if dec.superseded_by:
            nodes.append(LineageNode(
                entity_type="decision",
                entity_id=dec.superseded_by,
                label=f"superseded by {dec.superseded_by}",
                depth=1,
            ))

        return nodes

    def _resolve_goal(self, goal_id: str) -> Any:
        """Resolve a goal from the registry."""
        if not self._goal_registry:
            return None
        try:
            return self._goal_registry.get(goal_id)
        except Exception:
            logger.debug("Failed to resolve goal %s", goal_id, exc_info=True)
            return None
