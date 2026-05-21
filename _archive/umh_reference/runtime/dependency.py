"""Dependency — directed graph of objective relationships.

Models structural dependencies between objectives: which objectives
enable, boost, or block others. The graph is read-only during planning
(built before planning, queried during sequence generation).

Pure computation — no I/O, no subprocess, no state mutation during reads.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DependencyType(Enum):
    """How one objective relates to another."""

    ENABLES = "enables"
    BOOSTS = "boosts"
    BLOCKS = "blocks"


_MIN_STRENGTH = 0.0
_MAX_STRENGTH = 1.0


@dataclass(frozen=True)
class ObjectiveDependency:
    """A directed edge: parent_id's completion affects child_id."""

    parent_id: str
    child_id: str
    strength: float
    dep_type: DependencyType = DependencyType.ENABLES

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "strength",
            max(_MIN_STRENGTH, min(_MAX_STRENGTH, self.strength)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "strength": round(self.strength, 4),
            "dep_type": self.dep_type.value,
        }


class DependencyGraph:
    """Directed graph of objective dependencies.

    Supports add, query by parent/child, and dependency-aware scoring.
    Read-only during planning — all mutations happen before plan().
    """

    def __init__(self) -> None:
        self._edges: list[ObjectiveDependency] = []
        self._by_parent: dict[str, list[ObjectiveDependency]] = {}
        self._by_child: dict[str, list[ObjectiveDependency]] = {}

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def add_dependency(self, dep: ObjectiveDependency) -> None:
        """Add a dependency edge. Idempotent for same parent/child pair."""
        for existing in self._edges:
            if existing.parent_id == dep.parent_id and existing.child_id == dep.child_id:
                return
        self._edges.append(dep)
        self._by_parent.setdefault(dep.parent_id, []).append(dep)
        self._by_child.setdefault(dep.child_id, []).append(dep)

    def get_children(self, parent_id: str) -> list[ObjectiveDependency]:
        """Get all dependencies where parent_id is the parent."""
        return list(self._by_parent.get(parent_id, []))

    def get_parents(self, child_id: str) -> list[ObjectiveDependency]:
        """Get all dependencies where child_id is the child."""
        return list(self._by_child.get(child_id, []))

    def has_dependency(self, parent_id: str, child_id: str) -> bool:
        """Check if a direct dependency exists."""
        for dep in self._by_parent.get(parent_id, []):
            if dep.child_id == child_id:
                return True
        return False

    def get_dependency(self, parent_id: str, child_id: str) -> ObjectiveDependency | None:
        """Get a specific dependency edge."""
        for dep in self._by_parent.get(parent_id, []):
            if dep.child_id == child_id:
                return dep
        return None

    def dependency_score(self, parent_id: str, child_id: str) -> float:
        """Score the dependency relationship between two objectives.

        Returns positive for ENABLES/BOOSTS, negative for BLOCKS.
        Returns 0.0 if no dependency exists.
        """
        dep = self.get_dependency(parent_id, child_id)
        if dep is None:
            return 0.0
        if dep.dep_type == DependencyType.BLOCKS:
            return -dep.strength
        return dep.strength

    def sequence_dependency_score(self, objective_ids: list[str]) -> float:
        """Score how well a sequence respects dependencies.

        Sums pairwise dependency scores for consecutive objectives.
        Higher = better dependency alignment.
        """
        if len(objective_ids) < 2:
            return 0.0
        total = 0.0
        for i in range(len(objective_ids) - 1):
            total += self.dependency_score(objective_ids[i], objective_ids[i + 1])
        return total

    def all_edges(self) -> list[ObjectiveDependency]:
        """Return all dependency edges. Read-only snapshot."""
        return list(self._edges)

    def clear(self) -> None:
        """Remove all edges."""
        self._edges.clear()
        self._by_parent.clear()
        self._by_child.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_count": self.edge_count,
            "edges": [e.to_dict() for e in self._edges],
        }
