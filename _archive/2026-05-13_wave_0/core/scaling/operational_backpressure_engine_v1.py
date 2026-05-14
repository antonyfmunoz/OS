"""Operational Backpressure Engine v1.

Throttles execution, delays low-priority work,
regulates traversal rate, protects critical workflows,
stabilizes degraded environments.

Supports bounded throttling, bounded queue delay,
bounded continuation pacing.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    ExecutionThrottleState,
    PriorityClass,
    _content_hash,
    _now_iso,
)


THROTTLE_DELAY_MAP: dict[str, int] = {
    "nominal": 0,
    "low": 50,
    "elevated": 200,
    "high": 500,
    "critical": 1000,
}

MAX_THROTTLE_DELAY_MS: int = 5000
MAX_QUEUE_DELAY_MS: int = 10000
MAX_CONTINUATION_PACE_MS: int = 3000

PRIORITY_PROTECTION: dict[str, bool] = {
    PriorityClass.CRITICAL.value: True,
    PriorityClass.HIGH.value: False,
    PriorityClass.STANDARD.value: False,
    PriorityClass.DEFERRED.value: False,
    PriorityClass.SUSPENDED.value: False,
}


class OperationalBackpressureEngine:
    """Applies governed backpressure to execution."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/scaling",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._throttle = ExecutionThrottleState()
        self._total_throttles: int = 0
        self._total_releases: int = 0
        self._decisions: list[dict[str, Any]] = []

    def apply_throttle(
        self,
        pressure_level: str,
        reason: str = "",
    ) -> ExecutionThrottleState:
        delay = THROTTLE_DELAY_MAP.get(pressure_level, 0)
        delay = min(delay, MAX_THROTTLE_DELAY_MS)

        if delay > 0:
            self._throttle.active = True
            self._throttle.delay_ms = delay
            self._throttle.reason = reason or pressure_level
            self._throttle.started_at = _now_iso()
            self._throttle.released_at = ""
            self._throttle.affected_priorities = [
                p for p, protected in PRIORITY_PROTECTION.items()
                if not protected
            ]
            self._total_throttles += 1
        else:
            self.release_throttle()

        self._persist_decision("throttle", pressure_level, delay)
        return self._throttle

    def release_throttle(self) -> ExecutionThrottleState:
        if self._throttle.active:
            self._throttle.active = False
            self._throttle.released_at = _now_iso()
            self._throttle.delay_ms = 0
            self._total_releases += 1
            self._persist_decision("release", "nominal", 0)
        return self._throttle

    def compute_queue_delay(self, queue_depth: int, max_queue: int) -> int:
        if max_queue <= 0 or queue_depth <= 0:
            return 0
        ratio = queue_depth / max_queue
        delay = int(ratio * MAX_QUEUE_DELAY_MS)
        return min(delay, MAX_QUEUE_DELAY_MS)

    def compute_continuation_pace(self, continuation_depth: int) -> int:
        if continuation_depth <= 0:
            return 0
        pace = min(continuation_depth * 500, MAX_CONTINUATION_PACE_MS)
        return pace

    def should_protect(self, priority_class: str) -> bool:
        return PRIORITY_PROTECTION.get(priority_class, False)

    def get_throttle_state(self) -> ExecutionThrottleState:
        return self._throttle

    def get_throttle_hash(self) -> str:
        return _content_hash(self._decisions)

    def _persist_decision(
        self,
        action: str,
        level: str,
        delay: int,
    ) -> None:
        decision = {
            "action": action,
            "level": level,
            "delay_ms": delay,
            "timestamp": _now_iso(),
        }
        self._decisions.append(decision)
        path = self._state_dir / "backpressure_decisions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(decision, default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "throttle_active": self._throttle.active,
            "current_delay_ms": self._throttle.delay_ms,
            "total_throttles": self._total_throttles,
            "total_releases": self._total_releases,
        }
