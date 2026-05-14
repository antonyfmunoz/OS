"""Operational Chronology Engine v1.

Tracks ordered event history for long-horizon operations:
  objective_creation, campaign_creation, stage_transition,
  deferred_execution, continuation_restoration, approval,
  governance_escalation, stage_completion,
  execution_suspension, execution_termination

All events sequenced and persisted to JSONL.

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import (
    ChronologyEventKind,
    _new_id,
    _now_iso,
)


class OperationalChronologyEngine:
    """Tracks ordered chronological events for operations."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/operational_lineage",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._sequence_counters: dict[str, int] = {}
        self._total_events: int = 0

    def record(
        self,
        campaign_id: str,
        kind: ChronologyEventKind,
        description: str = "",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        seq = self._sequence_counters.get(campaign_id, 0)
        self._sequence_counters[campaign_id] = seq + 1

        event = {
            "event_id": _new_id("opchron"),
            "campaign_id": campaign_id,
            "kind": kind.value,
            "description": description,
            "data": data or {},
            "sequence_number": seq,
            "timestamp": _now_iso(),
        }

        if campaign_id not in self._events:
            self._events[campaign_id] = []
        self._events[campaign_id].append(event)
        self._total_events += 1

        path = self._state_dir / "operational_chronology.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return event

    def record_objective_creation(
        self, campaign_id: str, objective_id: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.OBJECTIVE_CREATION,
            data={"objective_id": objective_id},
        )

    def record_campaign_creation(
        self, campaign_id: str, operator_id: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.CAMPAIGN_CREATION,
            data={"operator_id": operator_id},
        )

    def record_stage_transition(
        self, campaign_id: str, stage_id: str = "",
        from_state: str = "", to_state: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.STAGE_TRANSITION,
            description=f"{from_state} -> {to_state}",
            data={"stage_id": stage_id, "from_state": from_state, "to_state": to_state},
        )

    def record_deferred_execution(
        self, campaign_id: str, stage_id: str = "", reason: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.DEFERRED_EXECUTION,
            data={"stage_id": stage_id, "reason": reason},
        )

    def record_continuation_restoration(
        self, campaign_id: str, checkpoint_id: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.CONTINUATION_RESTORATION,
            data={"checkpoint_id": checkpoint_id},
        )

    def record_approval(
        self, campaign_id: str, stage_id: str = "", approved_by: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.APPROVAL,
            data={"stage_id": stage_id, "approved_by": approved_by},
        )

    def record_governance_escalation(
        self, campaign_id: str, reason: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.GOVERNANCE_ESCALATION,
            data={"reason": reason},
        )

    def record_stage_completion(
        self, campaign_id: str, stage_id: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.STAGE_COMPLETION,
            data={"stage_id": stage_id},
        )

    def record_execution_suspension(
        self, campaign_id: str, reason: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.EXECUTION_SUSPENSION,
            data={"reason": reason},
        )

    def record_execution_termination(
        self, campaign_id: str, reason: str = "",
    ) -> dict[str, Any]:
        return self.record(
            campaign_id, ChronologyEventKind.EXECUTION_TERMINATION,
            data={"reason": reason},
        )

    def get_chronology(
        self, campaign_id: str, limit: int = 100,
    ) -> list[dict[str, Any]]:
        events = self._events.get(campaign_id, [])
        return events[-limit:]

    def get_chronology_snapshot(
        self, campaign_id: str,
    ) -> list[dict[str, Any]]:
        return list(self._events.get(campaign_id, []))

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "tracked_campaigns": len(self._events),
        }
