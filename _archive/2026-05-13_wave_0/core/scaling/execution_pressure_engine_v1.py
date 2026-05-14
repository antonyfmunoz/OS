"""Execution Pressure Engine v1.

Tracks operational pressure:
  active traversals, queue depth, latency,
  concurrency load, continuation pressure,
  environment saturation, deferred accumulation.

Prevents:
  uncontrolled execution expansion,
  hidden execution saturation,
  recursive scaling reactions.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    ExecutionPressureState,
    _content_hash,
    _now_iso,
)


PRESSURE_THRESHOLDS: dict[str, float] = {
    "low": 0.3,
    "elevated": 0.5,
    "high": 0.7,
    "critical": 0.9,
}


class ExecutionPressureEngine:
    """Tracks and computes execution pressure."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/scaling",
        max_concurrent: int = 5,
        max_queue: int = 50,
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._max_concurrent = max_concurrent
        self._max_queue = max_queue
        self._active_traversals: int = 0
        self._queue_depth: int = 0
        self._latency_sum: float = 0.0
        self._latency_count: int = 0
        self._continuation_pressure: int = 0
        self._deferred_accumulation: int = 0
        self._environment_saturation: float = 0.0
        self._snapshots: list[ExecutionPressureState] = []

    def record_traversal_start(self) -> None:
        self._active_traversals += 1

    def record_traversal_end(self, latency_ms: float = 0.0) -> None:
        self._active_traversals = max(0, self._active_traversals - 1)
        if latency_ms > 0:
            self._latency_sum += latency_ms
            self._latency_count += 1

    def record_queue_change(self, depth: int) -> None:
        self._queue_depth = max(0, depth)

    def record_continuation(self) -> None:
        self._continuation_pressure += 1

    def record_deferred(self) -> None:
        self._deferred_accumulation += 1

    def record_environment_saturation(self, saturation: float) -> None:
        self._environment_saturation = max(0.0, min(1.0, saturation))

    def compute_pressure(self) -> ExecutionPressureState:
        conc_load = (
            self._active_traversals / self._max_concurrent
            if self._max_concurrent > 0 else 0.0
        )
        avg_latency = (
            self._latency_sum / self._latency_count
            if self._latency_count > 0 else 0.0
        )
        queue_ratio = (
            self._queue_depth / self._max_queue
            if self._max_queue > 0 else 0.0
        )

        score = (
            conc_load * 0.35
            + queue_ratio * 0.25
            + min(self._environment_saturation, 1.0) * 0.20
            + min(self._continuation_pressure / 10.0, 1.0) * 0.10
            + min(self._deferred_accumulation / 20.0, 1.0) * 0.10
        )
        score = min(1.0, max(0.0, score))

        state = ExecutionPressureState(
            active_traversals=self._active_traversals,
            queue_depth=self._queue_depth,
            avg_latency_ms=round(avg_latency, 2),
            concurrency_load=round(conc_load, 3),
            continuation_pressure=self._continuation_pressure,
            environment_saturation=self._environment_saturation,
            deferred_accumulation=self._deferred_accumulation,
            pressure_score=round(score, 3),
        )
        self._snapshots.append(state)
        self._persist_snapshot(state)
        return state

    def get_pressure_level(self, score: float) -> str:
        if score >= PRESSURE_THRESHOLDS["critical"]:
            return "critical"
        if score >= PRESSURE_THRESHOLDS["high"]:
            return "high"
        if score >= PRESSURE_THRESHOLDS["elevated"]:
            return "elevated"
        if score >= PRESSURE_THRESHOLDS["low"]:
            return "low"
        return "nominal"

    def get_pressure_hash(self) -> str:
        return _content_hash([s.to_dict() for s in self._snapshots])

    def _persist_snapshot(self, state: ExecutionPressureState) -> None:
        path = self._state_dir / "execution_pressure_snapshots.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_traversals": self._active_traversals,
            "queue_depth": self._queue_depth,
            "total_snapshots": len(self._snapshots),
            "continuation_pressure": self._continuation_pressure,
            "deferred_accumulation": self._deferred_accumulation,
        }
