"""Stale Runtime Quarantine Engine v1.

Quarantines dead execution paths, abandoned experiments,
stale prototypes, shadow runtimes, disconnected orchestration trees.
Must NOT delete automatically.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.convergence.repository_topology_contracts_v1 import (
    QuarantineState,
    _now_iso,
    _deterministic_id,
)


MAX_QUARANTINES = 200


class StaleRuntimeQuarantineEngine:
    """Quarantines stale runtime paths without deletion."""

    def __init__(self, output_dir: str = "data/runtime/convergence/quarantine") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._quarantined: list[QuarantineState] = []

    def quarantine(
        self,
        path: str,
        reason: str,
        classification: str = "dead",
    ) -> dict[str, Any]:
        if len(self._quarantined) >= MAX_QUARANTINES:
            raise ValueError("Max quarantines reached")

        state = QuarantineState(
            quarantine_id=_deterministic_id("qrtn-", path, _now_iso()),
            path=path,
            reason=reason,
            classification=classification,
        )
        self._quarantined.append(state)
        filepath = self._output_dir / "quarantine_log.jsonl"
        with open(filepath, "a") as f:
            f.write(json.dumps(state.to_dict()) + "\n")
        return state.to_dict()

    def get_quarantined(self) -> list[dict[str, Any]]:
        return [q.to_dict() for q in self._quarantined]

    def get_by_classification(self, classification: str) -> list[dict[str, Any]]:
        return [q.to_dict() for q in self._quarantined if q.classification == classification]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_quarantined": len(self._quarantined),
        }
