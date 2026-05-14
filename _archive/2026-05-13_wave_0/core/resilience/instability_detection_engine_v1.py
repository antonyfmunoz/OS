"""Instability Detection Engine v1.

Detects instability signals across subsystems:
  consecutive failures, severity scoring, pattern classification.

Cannot repair or restart — detection only.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.resilience.adaptive_resilience_contracts_v1 import (
    InstabilitySignal,
    SubsystemHealthState,
    InstabilityClass,
    _now_iso,
)


INSTABILITY_THRESHOLDS: dict[str, float] = {
    "transient": 0.2,
    "intermittent": 0.4,
    "persistent": 0.6,
    "cascading": 0.8,
    "systemic": 0.9,
}

FAILURE_THRESHOLD: int = 3
MAX_TRACKED_SUBSYSTEMS: int = 50
MAX_SIGNAL_HISTORY: int = 100


class InstabilityDetectionEngine:
    """Detects and classifies instability across subsystems."""

    def __init__(self, state_dir: str | Path = "data/runtime/resilience") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._subsystem_health: dict[str, SubsystemHealthState] = {}
        self._signals: list[InstabilitySignal] = []
        self._total_detections: int = 0

    def record_success(self, subsystem_id: str) -> SubsystemHealthState:
        health = self._get_or_create_health(subsystem_id)
        health.healthy = True
        health.consecutive_failures = 0
        health.last_success = _now_iso()
        health.degraded = False
        health.timestamp = _now_iso()
        return health

    def record_failure(self, subsystem_id: str) -> InstabilitySignal | None:
        health = self._get_or_create_health(subsystem_id)
        health.consecutive_failures += 1
        health.last_failure = _now_iso()
        health.timestamp = _now_iso()

        if health.consecutive_failures >= FAILURE_THRESHOLD:
            health.healthy = False
            health.degraded = True
            return self._emit_signal(subsystem_id, health)

        return None

    def compute_instability_score(self) -> float:
        if not self._subsystem_health:
            return 0.0

        total = len(self._subsystem_health)
        unhealthy = sum(
            1 for h in self._subsystem_health.values() if not h.healthy
        )
        degraded = sum(
            1 for h in self._subsystem_health.values() if h.degraded
        )

        unhealthy_ratio = unhealthy / total if total > 0 else 0.0
        degraded_ratio = degraded / total if total > 0 else 0.0

        score = (unhealthy_ratio * 0.6) + (degraded_ratio * 0.4)
        return min(1.0, score)

    def classify_instability(self, score: float) -> str:
        if score >= INSTABILITY_THRESHOLDS["systemic"]:
            return "systemic"
        if score >= INSTABILITY_THRESHOLDS["cascading"]:
            return "cascading"
        if score >= INSTABILITY_THRESHOLDS["persistent"]:
            return "persistent"
        if score >= INSTABILITY_THRESHOLDS["intermittent"]:
            return "intermittent"
        if score >= INSTABILITY_THRESHOLDS["transient"]:
            return "transient"
        return "stable"

    def get_unhealthy_subsystems(self) -> list[str]:
        return [
            sid for sid, h in self._subsystem_health.items()
            if not h.healthy
        ]

    def get_degraded_subsystems(self) -> list[str]:
        return [
            sid for sid, h in self._subsystem_health.items()
            if h.degraded
        ]

    def get_health(self, subsystem_id: str) -> SubsystemHealthState | None:
        return self._subsystem_health.get(subsystem_id)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_subsystems": len(self._subsystem_health),
            "unhealthy_count": len(self.get_unhealthy_subsystems()),
            "degraded_count": len(self.get_degraded_subsystems()),
            "total_detections": self._total_detections,
            "total_signals": len(self._signals),
        }

    def _get_or_create_health(self, subsystem_id: str) -> SubsystemHealthState:
        if subsystem_id not in self._subsystem_health:
            if len(self._subsystem_health) >= MAX_TRACKED_SUBSYSTEMS:
                raise ValueError(
                    f"Max tracked subsystems ({MAX_TRACKED_SUBSYSTEMS}) reached"
                )
            self._subsystem_health[subsystem_id] = SubsystemHealthState(
                subsystem_id=subsystem_id,
            )
        return self._subsystem_health[subsystem_id]

    def _emit_signal(
        self,
        subsystem_id: str,
        health: SubsystemHealthState,
    ) -> InstabilitySignal:
        score = self.compute_instability_score()
        classification = self.classify_instability(score)

        signal = InstabilitySignal(
            source=subsystem_id,
            instability_class=classification,
            severity=score,
            consecutive_failures=health.consecutive_failures,
            pattern=f"consecutive_failures:{health.consecutive_failures}",
        )

        self._signals.append(signal)
        if len(self._signals) > MAX_SIGNAL_HISTORY:
            self._signals = self._signals[-MAX_SIGNAL_HISTORY:]

        self._total_detections += 1

        path = self._state_dir / "instability_signals.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(signal.to_dict(), default=str) + "\n")

        return signal
