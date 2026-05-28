"""Objective Physics — causal execution dynamics.

Models how objectives relate to each other and identifies
strategic leverage points:
  - dependency chains and blocking nodes
  - execution gravity (what pulls resources)
  - leverage propagation (what compounds)
  - critical execution paths
  - upstream/downstream impact

The organism uses this to understand not just WHAT to execute,
but WHAT MATTERS MOST and what creates cascading leverage.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ObjectiveState(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    STALLED = "stalled"


@dataclass
class ObjectiveNode:
    objective_id: str
    name: str = ""
    state: ObjectiveState = ObjectiveState.PENDING
    depends_on: list[str] = field(default_factory=list)
    enables: list[str] = field(default_factory=list)
    estimated_seconds: float = 0.0
    actual_seconds: float = 0.0
    leverage_weight: float = 1.0
    resource_cost: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0

    @property
    def is_blocking(self) -> bool:
        return len(self.enables) > 0 and self.state != ObjectiveState.COMPLETED

    @property
    def downstream_count(self) -> int:
        return len(self.enables)

    @property
    def upstream_count(self) -> int:
        return len(self.depends_on)


@dataclass
class CriticalPath:
    path: list[str]
    total_estimated_seconds: float = 0.0
    total_actual_seconds: float = 0.0
    blocking_nodes: list[str] = field(default_factory=list)
    leverage_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "total_estimated_seconds": round(self.total_estimated_seconds, 1),
            "total_actual_seconds": round(self.total_actual_seconds, 1),
            "blocking_nodes": self.blocking_nodes,
            "leverage_score": round(self.leverage_score, 4),
        }


@dataclass
class LeveragePropagation:
    source_id: str
    affected_ids: list[str]
    propagation_depth: int = 0
    compound_leverage: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "affected_count": len(self.affected_ids),
            "propagation_depth": self.propagation_depth,
            "compound_leverage": round(self.compound_leverage, 4),
        }


class ObjectivePhysics:
    """Models causal relationships between objectives.

    Builds a dependency graph and computes:
    - critical paths (longest blocking chains)
    - execution gravity (resource-weighted centrality)
    - leverage propagation (how unblocking one node compounds)
    - blocking analysis (what's stalling the system)
    """

    def __init__(self, event_spine: Any | None = None) -> None:
        self._nodes: dict[str, ObjectiveNode] = {}
        self._event_spine = event_spine

    def register_objective(
        self,
        objective_id: str,
        name: str = "",
        depends_on: list[str] | None = None,
        estimated_seconds: float = 0.0,
        leverage_weight: float = 1.0,
        resource_cost: float = 0.0,
    ) -> ObjectiveNode:
        node = ObjectiveNode(
            objective_id=objective_id,
            name=name or objective_id,
            depends_on=depends_on or [],
            estimated_seconds=estimated_seconds,
            leverage_weight=leverage_weight,
            resource_cost=resource_cost,
        )
        self._nodes[objective_id] = node

        for dep_id in node.depends_on:
            dep = self._nodes.get(dep_id)
            if dep and objective_id not in dep.enables:
                dep.enables.append(objective_id)

        return node

    def update_state(
        self,
        objective_id: str,
        state: ObjectiveState,
        actual_seconds: float = 0.0,
    ) -> None:
        node = self._nodes.get(objective_id)
        if node is None:
            return
        node.state = state
        if actual_seconds > 0:
            node.actual_seconds = actual_seconds
        if state == ObjectiveState.EXECUTING and node.started_at <= 0:
            node.started_at = time.time()
        if state == ObjectiveState.COMPLETED:
            node.completed_at = time.time()

    def blocking_nodes(self) -> list[ObjectiveNode]:
        return sorted(
            [n for n in self._nodes.values() if n.is_blocking],
            key=lambda n: n.downstream_count,
            reverse=True,
        )

    def execution_gravity(self) -> list[dict[str, Any]]:
        gravity: list[dict[str, Any]] = []
        for node in self._nodes.values():
            downstream = self._transitive_downstream(node.objective_id)
            total_resource = node.resource_cost + sum(
                self._nodes[d].resource_cost for d in downstream if d in self._nodes
            )
            gravity.append({
                "objective_id": node.objective_id,
                "name": node.name,
                "direct_downstream": node.downstream_count,
                "transitive_downstream": len(downstream),
                "total_resource_cost": round(total_resource, 2),
                "gravity_score": round(
                    node.leverage_weight * (1 + len(downstream)) * (1 + total_resource),
                    4,
                ),
            })
        return sorted(gravity, key=lambda g: g["gravity_score"], reverse=True)

    def _transitive_downstream(self, objective_id: str, visited: set[str] | None = None) -> set[str]:
        if visited is None:
            visited = set()
        node = self._nodes.get(objective_id)
        if node is None:
            return visited
        for child_id in node.enables:
            if child_id not in visited:
                visited.add(child_id)
                self._transitive_downstream(child_id, visited)
        return visited

    def critical_paths(self) -> list[CriticalPath]:
        roots = [n for n in self._nodes.values() if not n.depends_on]
        if not roots:
            roots = list(self._nodes.values())[:5]

        paths: list[CriticalPath] = []
        for root in roots:
            path = self._longest_path(root.objective_id, set())
            if len(path) > 1:
                cp = CriticalPath(path=path)
                for oid in path:
                    node = self._nodes.get(oid)
                    if node:
                        cp.total_estimated_seconds += node.estimated_seconds
                        cp.total_actual_seconds += node.actual_seconds
                        cp.leverage_score += node.leverage_weight
                        if node.is_blocking:
                            cp.blocking_nodes.append(oid)
                paths.append(cp)

        return sorted(paths, key=lambda p: p.leverage_score, reverse=True)

    def _longest_path(self, start: str, visited: set[str]) -> list[str]:
        if start in visited:
            return []
        visited.add(start)
        node = self._nodes.get(start)
        if node is None:
            return [start]

        best_child_path: list[str] = []
        for child_id in node.enables:
            child_path = self._longest_path(child_id, visited.copy())
            if len(child_path) > len(best_child_path):
                best_child_path = child_path

        return [start] + best_child_path

    def leverage_propagation(self, objective_id: str) -> LeveragePropagation:
        downstream = self._transitive_downstream(objective_id)
        compound = sum(
            self._nodes[d].leverage_weight
            for d in downstream
            if d in self._nodes
        )

        depth = 0
        current = {objective_id}
        visited: set[str] = set()
        while current:
            visited.update(current)
            next_level: set[str] = set()
            for oid in current:
                node = self._nodes.get(oid)
                if node:
                    next_level.update(c for c in node.enables if c not in visited)
            if not next_level:
                break
            depth += 1
            current = next_level

        return LeveragePropagation(
            source_id=objective_id,
            affected_ids=list(downstream),
            propagation_depth=depth,
            compound_leverage=compound,
        )

    def what_matters_most(self, top_n: int = 5) -> list[dict[str, Any]]:
        gravity = self.execution_gravity()
        blocking = {n.objective_id for n in self.blocking_nodes()}

        for g in gravity:
            if g["objective_id"] in blocking:
                g["gravity_score"] *= 1.5

        return sorted(gravity, key=lambda g: g["gravity_score"], reverse=True)[:top_n]

    def what_blocks_everything(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for node in self.blocking_nodes():
            downstream = self._transitive_downstream(node.objective_id)
            blocked_waiting = [
                d for d in downstream
                if d in self._nodes and self._nodes[d].state == ObjectiveState.BLOCKED
            ]
            result.append({
                "objective_id": node.objective_id,
                "name": node.name,
                "state": node.state.value,
                "directly_enables": node.downstream_count,
                "transitively_enables": len(downstream),
                "currently_blocking": len(blocked_waiting),
            })
        return result

    def physics_tick(self) -> dict[str, Any]:
        result = {
            "total_objectives": len(self._nodes),
            "blocking_count": len(self.blocking_nodes()),
            "critical_paths": [cp.to_dict() for cp in self.critical_paths()[:3]],
            "top_gravity": self.what_matters_most(3),
            "blockers": self.what_blocks_everything()[:5],
        }
        if self._event_spine is not None:
            from substrate.organism.event_spine import EventDomain
            self._event_spine.emit(
                EventDomain.OBJECTIVE,
                "physics_analyzed",
                "objective_physics",
                result,
            )
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_objectives": len(self._nodes),
            "by_state": self._count_by_state(),
            "blocking_nodes": len(self.blocking_nodes()),
            "critical_paths_count": len(self.critical_paths()),
        }

    def _count_by_state(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for n in self._nodes.values():
            counts[n.state.value] = counts.get(n.state.value, 0) + 1
        return counts
