"""Deferred Execution Engine v1.

Manages paused, scheduled, and deferred execution states
for long-horizon operations.

Supports:
  scheduled continuation, bounded waiting, deferred approvals,
  delayed execution windows, resumable pauses, operator resume points

Persist to: data/runtime/deferred_operations/

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import (
    DeferredExecutionState,
    OperationalWaitingState,
    _new_id,
    _now_iso,
)


class DeferredExecutionEngine:
    """Manages deferred and waiting execution states."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/deferred_operations",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._deferred: dict[str, DeferredExecutionState] = {}
        self._waiting: dict[str, OperationalWaitingState] = {}
        self._total_deferred: int = 0
        self._total_resumed: int = 0

    def defer_stage(
        self,
        campaign_id: str,
        stage_id: str,
        reason: str = "",
        resume_condition: str = "",
        resume_after: str = "",
    ) -> DeferredExecutionState:
        """Defer execution of a stage."""
        state = DeferredExecutionState(
            campaign_id=campaign_id,
            stage_id=stage_id,
            reason=reason,
            resume_condition=resume_condition,
            resume_after=resume_after,
        )
        self._deferred[state.deferred_id] = state
        self._total_deferred += 1

        path = self._state_dir / "deferred_executions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")

        return state

    def resume_deferred(self, deferred_id: str) -> bool:
        """Resume a deferred execution."""
        state = self._deferred.get(deferred_id)
        if not state or state.resumed:
            return False
        state.resumed = True
        self._total_resumed += 1
        return True

    def enter_waiting(
        self,
        campaign_id: str,
        stage_id: str,
        waiting_for: str = "",
        wait_type: str = "approval",
        max_wait_hours: int = 24,
    ) -> OperationalWaitingState:
        """Enter a governed waiting state."""
        state = OperationalWaitingState(
            campaign_id=campaign_id,
            stage_id=stage_id,
            waiting_for=waiting_for,
            wait_type=wait_type,
            max_wait_hours=max_wait_hours,
        )
        self._waiting[state.waiting_id] = state

        path = self._state_dir / "waiting_states.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")

        return state

    def get_deferred(self, deferred_id: str) -> DeferredExecutionState | None:
        return self._deferred.get(deferred_id)

    def get_active_deferred(self) -> list[dict[str, Any]]:
        return [
            d.to_dict() for d in self._deferred.values()
            if not d.resumed
        ]

    def get_active_waiting(self) -> list[dict[str, Any]]:
        return [w.to_dict() for w in self._waiting.values()]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_deferred": self._total_deferred,
            "total_resumed": self._total_resumed,
            "active_deferred": len(self.get_active_deferred()),
            "active_waiting": len(self._waiting),
        }
