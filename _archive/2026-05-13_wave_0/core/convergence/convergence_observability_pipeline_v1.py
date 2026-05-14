"""Convergence Observability Pipeline v1.

9 event types with JSONL persistence for convergence operations.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.convergence.repository_topology_contracts_v1 import (
    ConvergenceEventType,
    _now_iso,
)


EVENT_FILE_MAP = {e.value: f"{e.value}.jsonl" for e in ConvergenceEventType}


class ConvergenceObservabilityPipeline:
    """Emits and persists convergence observability events."""

    def __init__(self, output_dir: str = "data/runtime/convergence") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []

    def _emit(self, event_type: ConvergenceEventType, details: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "event_type": event_type.value,
            "timestamp": _now_iso(),
            **details,
        }
        self._events.append(entry)
        filepath = self._output_dir / EVENT_FILE_MAP[event_type.value]
        with open(filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def emit_topology_scanned(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.TOPOLOGY_SCANNED, details)

    def emit_namespace_verified(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.NAMESPACE_VERIFIED, details)

    def emit_duplicate_detected(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.DUPLICATE_DETECTED, details)

    def emit_runtime_quarantined(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.RUNTIME_QUARANTINED, details)

    def emit_import_graph_verified(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.IMPORT_GRAPH_VERIFIED, details)

    def emit_runtime_entrypoint_verified(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.RUNTIME_ENTRYPOINT_VERIFIED, details)

    def emit_filesystem_verified(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.FILESYSTEM_VERIFIED, details)

    def emit_ingestion_readiness_verified(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.INGESTION_READINESS_VERIFIED, details)

    def emit_convergence_boundary_denied(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(ConvergenceEventType.CONVERGENCE_BOUNDARY_DENIED, details)

    def get_stats(self) -> dict[str, Any]:
        return {"total_events": len(self._events)}
