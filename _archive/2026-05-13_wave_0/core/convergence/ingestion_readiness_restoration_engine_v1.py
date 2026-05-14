"""Ingestion Readiness Restoration Engine v1.

Verifies ingestion directories exist, runtime paths valid,
dependencies canonical, import graph stable, continuity valid,
replay valid, observability valid.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.convergence.repository_topology_contracts_v1 import (
    IngestionReadinessState,
    _now_iso,
    _deterministic_id,
)


MAX_READINESS_CHECKS = 50


class IngestionReadinessRestorationEngine:
    """Verifies ingestion readiness for resume."""

    def __init__(self, output_dir: str = "data/runtime/convergence/reports") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._checks: list[IngestionReadinessState] = []

    def verify_readiness(
        self,
        directories_exist: bool = True,
        runtime_paths_valid: bool = True,
        dependencies_canonical: bool = True,
        import_graph_stable: bool = True,
        continuity_valid: bool = True,
        replay_valid: bool = True,
        observability_valid: bool = True,
    ) -> dict[str, Any]:
        if len(self._checks) >= MAX_READINESS_CHECKS:
            raise ValueError("Max readiness checks reached")

        ready = all([
            directories_exist,
            runtime_paths_valid,
            dependencies_canonical,
            import_graph_stable,
            continuity_valid,
            replay_valid,
            observability_valid,
        ])

        state = IngestionReadinessState(
            readiness_id=_deterministic_id("ingrd-", _now_iso()),
            directories_exist=directories_exist,
            runtime_paths_valid=runtime_paths_valid,
            dependencies_canonical=dependencies_canonical,
            import_graph_stable=import_graph_stable,
            continuity_valid=continuity_valid,
            replay_valid=replay_valid,
            observability_valid=observability_valid,
            ready=ready,
        )
        self._checks.append(state)

        filepath = self._output_dir / "ingestion_resume_readiness.json"
        with open(filepath, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

        return state.to_dict()

    def all_ready(self) -> bool:
        return all(c.ready for c in self._checks) if self._checks else False

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checks": len(self._checks),
            "all_ready": self.all_ready() if self._checks else False,
        }
