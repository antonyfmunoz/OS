"""Goal Hierarchy Engine — structural operations on the goal tree.

Campaign 8.1. UMH substrate layer. Instance-agnostic.

Consumes GoalRegistry (from strategic_gap_engine.py). Read-only —
all mutation stays inside GoalRegistry. This engine provides
tree traversal, path computation, validation, and structural queries.

Deterministic. Zero LLM calls. No execution authority.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class HierarchyValidation:
    valid: bool = True
    orphans: list[str] = field(default_factory=list)
    cycles: list[str] = field(default_factory=list)
    type_violations: list[dict[str, str]] = field(default_factory=list)
    missing_parents: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "orphan_count": len(self.orphans),
            "orphans": self.orphans,
            "cycle_count": len(self.cycles),
            "cycles": self.cycles,
            "type_violation_count": len(self.type_violations),
            "type_violations": self.type_violations,
            "missing_parent_count": len(self.missing_parents),
            "missing_parents": self.missing_parents,
        }


# ── Hierarchy depth ordering (parent types should be above child types) ──

_TYPE_DEPTH: dict[str, int] = {
    "vision": 0,
    "objective": 1,
    "outcome": 2,
    "initiative": 3,
    "project": 4,
    "goal": 2,
    "roadmap": 1,
    "milestone": 3,
}


# ── Engine ────────────────────────────────────────────────────────────────


class GoalHierarchyEngine:
    """Structural operations on the goal hierarchy.

    Read-only. All mutation goes through GoalRegistry.
    """

    def __init__(self, goal_registry: Any | None = None) -> None:
        self._registry = goal_registry

    def _all_goals(self) -> list[Any]:
        if self._registry is None:
            return []
        try:
            return self._registry.all_goals()
        except Exception as exc:
            logger.debug("hierarchy: failed to get goals: %s", exc)
            return []

    def roots(self) -> list[Any]:
        """Goals with no parent — typically VISION type."""
        return [g for g in self._all_goals() if not g.parent_goal_id]

    def leaves(self) -> list[Any]:
        """Goals with no children."""
        if self._registry is None:
            return []
        all_goals = self._all_goals()
        parent_ids = {g.parent_goal_id for g in all_goals if g.parent_goal_id}
        return [g for g in all_goals if g.goal_id not in parent_ids]

    def path(self, goal_id: str) -> list[Any]:
        """Root-to-leaf path for a goal. Returns [root, ..., goal]."""
        if self._registry is None:
            return []
        goal = self._registry.get(goal_id)
        if not goal:
            return []
        ancestors = self._registry.ancestors(goal_id)
        return list(reversed(ancestors)) + [goal]

    def ancestors(self, goal_id: str) -> list[Any]:
        """Leaf-to-root chain (delegates to GoalRegistry.ancestors)."""
        if self._registry is None:
            return []
        return self._registry.ancestors(goal_id)

    def descendants(self, goal_id: str) -> list[Any]:
        """All children recursively (BFS)."""
        if self._registry is None:
            return []
        result: list[Any] = []
        queue = [goal_id]
        seen: set[str] = {goal_id}
        while queue:
            current = queue.pop(0)
            children = self._registry.children_of(current)
            for child in children:
                if child.goal_id not in seen:
                    seen.add(child.goal_id)
                    result.append(child)
                    queue.append(child.goal_id)
        return result

    def depth(self, goal_id: str) -> int:
        """Distance from root (0 = root)."""
        return len(self.ancestors(goal_id))

    def tree(self, root_id: str | None = None) -> dict[str, Any]:
        """Nested dict of goal hierarchy. Delegates to GoalRegistry.tree."""
        if self._registry is None:
            return {"roots": []}
        return self._registry.tree(root_id)

    def subtree_ids(self, goal_id: str) -> list[str]:
        """All goal IDs in the subtree rooted at goal_id (including root)."""
        return [goal_id] + [d.goal_id for d in self.descendants(goal_id)]

    def validate_hierarchy(self) -> HierarchyValidation:
        """Check for orphans, cycles, missing parents, type violations."""
        result = HierarchyValidation()
        all_goals = self._all_goals()
        goal_ids = {g.goal_id for g in all_goals}

        for goal in all_goals:
            if goal.parent_goal_id and goal.parent_goal_id not in goal_ids:
                result.missing_parents.append({
                    "goal_id": goal.goal_id,
                    "title": goal.title,
                    "missing_parent_id": goal.parent_goal_id,
                })

            if goal.parent_goal_id:
                seen: set[str] = set()
                current = goal
                while current and current.parent_goal_id:
                    if current.parent_goal_id in seen:
                        result.cycles.append(goal.goal_id)
                        break
                    seen.add(current.parent_goal_id)
                    if self._registry:
                        current = self._registry.get(current.parent_goal_id)
                    else:
                        current = None

            if goal.parent_goal_id and self._registry:
                parent = self._registry.get(goal.parent_goal_id)
                if parent:
                    parent_depth = _TYPE_DEPTH.get(parent.goal_type.value, 0)
                    child_depth = _TYPE_DEPTH.get(goal.goal_type.value, 0)
                    if child_depth <= parent_depth:
                        result.type_violations.append({
                            "goal_id": goal.goal_id,
                            "goal_type": goal.goal_type.value,
                            "parent_id": parent.goal_id,
                            "parent_type": parent.goal_type.value,
                        })

        if not self.roots():
            all_with_parents = [g for g in all_goals if g.parent_goal_id]
            if all_with_parents:
                result.orphans = [g.goal_id for g in all_with_parents]

        result.valid = (
            not result.orphans
            and not result.cycles
            and not result.missing_parents
        )
        return result

    def trace_to_vision(self, goal_id: str) -> list[dict[str, str]]:
        """Trace a goal upward to its vision. Returns list of
        {goal_id, title, goal_type} from leaf to root."""
        path = self.path(goal_id)
        return [
            {
                "goal_id": g.goal_id,
                "title": g.title,
                "goal_type": g.goal_type.value if hasattr(g.goal_type, "value") else str(g.goal_type),
            }
            for g in path
        ]

    def summary(self) -> dict[str, Any]:
        """Compact hierarchy summary."""
        all_goals = self._all_goals()
        by_type: dict[str, int] = {}
        for g in all_goals:
            t = g.goal_type.value if hasattr(g.goal_type, "value") else str(g.goal_type)
            by_type[t] = by_type.get(t, 0) + 1

        validation = self.validate_hierarchy()
        return {
            "total_goals": len(all_goals),
            "root_count": len(self.roots()),
            "leaf_count": len(self.leaves()),
            "max_depth": max((self.depth(g.goal_id) for g in all_goals), default=0),
            "by_type": by_type,
            "valid": validation.valid,
            "issue_count": (
                len(validation.orphans)
                + len(validation.cycles)
                + len(validation.missing_parents)
            ),
        }
