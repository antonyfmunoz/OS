"""Operational Dependency Engine v1.

Tracks dependencies between execution stages and prevents
cyclic execution graphs, recursive progression, and hidden
continuation chains.

Dependency types:
  stage, workflow, checkpoint, governance, chronology, approval

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import (
    DependencyType,
    ExecutionDependency,
    _new_id,
    _now_iso,
)


class OperationalDependencyEngine:
    """Tracks and validates dependencies between execution stages."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/operations",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._dependencies: dict[str, list[ExecutionDependency]] = {}
        self._total_dependencies: int = 0

    def add_dependency(
        self,
        source_stage_id: str,
        target_stage_id: str,
        dependency_type: DependencyType = DependencyType.STAGE,
    ) -> ExecutionDependency | None:
        """Add a dependency: target depends on source."""
        if self._would_create_cycle(source_stage_id, target_stage_id):
            return None

        dep = ExecutionDependency(
            source_stage_id=source_stage_id,
            target_stage_id=target_stage_id,
            dependency_type=dependency_type.value,
        )

        if target_stage_id not in self._dependencies:
            self._dependencies[target_stage_id] = []
        self._dependencies[target_stage_id].append(dep)
        self._total_dependencies += 1

        path = self._state_dir / "operational_dependencies.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dep.to_dict(), default=str) + "\n")

        return dep

    def satisfy(self, source_stage_id: str) -> int:
        """Mark all dependencies on source_stage_id as satisfied."""
        count = 0
        for deps in self._dependencies.values():
            for dep in deps:
                if dep.source_stage_id == source_stage_id and not dep.satisfied:
                    dep.satisfied = True
                    count += 1
        return count

    def are_dependencies_met(self, stage_id: str) -> bool:
        """Check if all dependencies for a stage are satisfied."""
        deps = self._dependencies.get(stage_id, [])
        return all(d.satisfied for d in deps)

    def get_dependencies(self, stage_id: str) -> list[dict[str, Any]]:
        deps = self._dependencies.get(stage_id, [])
        return [d.to_dict() for d in deps]

    def get_unmet_dependencies(self, stage_id: str) -> list[dict[str, Any]]:
        deps = self._dependencies.get(stage_id, [])
        return [d.to_dict() for d in deps if not d.satisfied]

    def _would_create_cycle(self, source: str, target: str) -> bool:
        """Detect if adding source->target would create a cycle."""
        if source == target:
            return True
        visited: set[str] = set()
        stack = [source]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for dep in self._dependencies.get(current, []):
                if dep.source_stage_id == target:
                    return True
                stack.append(dep.source_stage_id)
        return False

    def get_execution_order(self, stage_ids: list[str]) -> list[str]:
        """Topological sort of stages by dependencies."""
        in_degree: dict[str, int] = {sid: 0 for sid in stage_ids}
        for sid in stage_ids:
            for dep in self._dependencies.get(sid, []):
                if dep.source_stage_id in in_degree:
                    in_degree[sid] = in_degree.get(sid, 0) + 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        result: list[str] = []
        while queue:
            current = queue.pop(0)
            result.append(current)
            for sid in stage_ids:
                for dep in self._dependencies.get(sid, []):
                    if dep.source_stage_id == current:
                        in_degree[sid] -= 1
                        if in_degree[sid] == 0:
                            queue.append(sid)
        return result

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_dependencies": self._total_dependencies,
            "tracked_stages": len(self._dependencies),
        }
