"""Degraded-Mode Coordination Engine v1.

Supports:
  degraded execution, partial environment failure,
  replay-safe throttling, bounded recovery,
  continuity preservation under load.

Prevents:
  cascading execution collapse,
  uncontrolled recovery storms.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    DegradedModeState,
    DegradedReason,
    _content_hash,
    _now_iso,
)


MAX_RECOVERY_ATTEMPTS: int = 3
DEGRADED_CONCURRENCY_FACTOR: float = 0.5


class DegradedModeCoordinationEngine:
    """Coordinates degraded-mode execution and recovery."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/scaling",
        base_concurrency: int = 5,
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._base_concurrency = base_concurrency
        self._mode = DegradedModeState()
        self._recovery_attempts: int = 0
        self._total_entries: int = 0
        self._total_recoveries: int = 0
        self._decisions: list[dict[str, Any]] = []

    def enter_degraded(
        self,
        reason: str = DegradedReason.ENVIRONMENT_FAILURE.value,
        affected_environments: list[str] | None = None,
    ) -> DegradedModeState:
        self._mode.active = True
        self._mode.reason = reason
        self._mode.affected_environments = affected_environments or []
        self._mode.entered_at = _now_iso()
        self._mode.recovered_at = ""
        self._mode.reduced_concurrency = max(
            1, int(self._base_concurrency * DEGRADED_CONCURRENCY_FACTOR),
        )
        self._recovery_attempts = 0
        self._total_entries += 1
        self._persist_decision("enter_degraded", reason)
        return self._mode

    def attempt_recovery(self) -> bool:
        if not self._mode.active:
            return False

        self._recovery_attempts += 1
        if self._recovery_attempts > MAX_RECOVERY_ATTEMPTS:
            self._persist_decision("recovery_exhausted", "max_attempts_reached")
            return False

        self._persist_decision("recovery_attempt", f"attempt_{self._recovery_attempts}")
        return True

    def complete_recovery(self) -> DegradedModeState:
        self._mode.active = False
        self._mode.recovered_at = _now_iso()
        self._mode.reduced_concurrency = 0
        self._total_recoveries += 1
        self._recovery_attempts = 0
        self._persist_decision("recovery_complete", "")
        return self._mode

    def is_degraded(self) -> bool:
        return self._mode.active

    def get_reduced_concurrency(self) -> int:
        if self._mode.active:
            return self._mode.reduced_concurrency
        return self._base_concurrency

    def get_mode(self) -> DegradedModeState:
        return self._mode

    def get_degraded_hash(self) -> str:
        return _content_hash(self._decisions)

    def _persist_decision(self, action: str, detail: str) -> None:
        decision = {
            "action": action,
            "detail": detail,
            "active": self._mode.active,
            "recovery_attempts": self._recovery_attempts,
            "timestamp": _now_iso(),
        }
        self._decisions.append(decision)
        path = self._state_dir / "degraded_mode_decisions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(decision, default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "degraded": self._mode.active,
            "total_entries": self._total_entries,
            "total_recoveries": self._total_recoveries,
            "recovery_attempts": self._recovery_attempts,
            "reduced_concurrency": self._mode.reduced_concurrency,
        }
