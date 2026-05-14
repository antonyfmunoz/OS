"""Operational Continuation Bridges v1.

Bridges between long-horizon operations and substrate layers:
  sessions ↔ operations
  workflows ↔ operations
  cognition ↔ operations
  embodiment ↔ operations
  observability ↔ operations
  replay ↔ operations
  ingress ↔ operations

Each bridge captures layer-specific state into the operational
continuity model.

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import (
    _new_id,
    _now_iso,
)


class _BaseBridge:
    """Shared persistence for all operational bridges."""

    def __init__(
        self,
        bridge_type: str,
        state_dir: str | Path = "data/runtime/operational_lineage",
    ) -> None:
        self._bridge_type = bridge_type
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def _persist(self, campaign_id: str, data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "bridge_id": _new_id("opbr"),
            "bridge_type": self._bridge_type,
            "campaign_id": campaign_id,
            "data": data,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / f"{self._bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        self._total_captures += 1
        return record


class SessionOperationsBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/operational_lineage") -> None:
        super().__init__("session_operations", state_dir)

    def capture(self, campaign_id: str, session_id: str = "",
                session_state: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(campaign_id, {
            "session_id": session_id, "session_state": session_state, **kw,
        })


class WorkflowOperationsBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/operational_lineage") -> None:
        super().__init__("workflow_operations", state_dir)

    def capture(self, campaign_id: str, workflow_id: str = "",
                workflow_state: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(campaign_id, {
            "workflow_id": workflow_id, "workflow_state": workflow_state, **kw,
        })


class CognitionOperationsBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/operational_lineage") -> None:
        super().__init__("cognition_operations", state_dir)

    def capture(self, campaign_id: str, operator_mode: str = "",
                cognition_phase: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(campaign_id, {
            "operator_mode": operator_mode, "cognition_phase": cognition_phase, **kw,
        })


class EmbodimentOperationsBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/operational_lineage") -> None:
        super().__init__("embodiment_operations", state_dir)

    def capture(self, campaign_id: str, workstation_mode: str = "",
                browser_mode: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(campaign_id, {
            "workstation_mode": workstation_mode, "browser_mode": browser_mode, **kw,
        })


class ObservabilityOperationsBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/operational_lineage") -> None:
        super().__init__("observability_operations", state_dir)

    def capture(self, campaign_id: str, total_events: int = 0,
                event_types: dict[str, int] | None = None, **kw: Any) -> dict[str, Any]:
        return self._persist(campaign_id, {
            "total_events": total_events, "event_types": event_types or {}, **kw,
        })


class ReplayOperationsBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/operational_lineage") -> None:
        super().__init__("replay_operations", state_dir)

    def capture(self, campaign_id: str, total_validations: int = 0,
                total_passes: int = 0, **kw: Any) -> dict[str, Any]:
        return self._persist(campaign_id, {
            "total_validations": total_validations, "total_passes": total_passes, **kw,
        })


class IngressOperationsBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/operational_lineage") -> None:
        super().__init__("ingress_operations", state_dir)

    def capture(self, campaign_id: str, active_sources: list[str] | None = None,
                total_signals: int = 0, **kw: Any) -> dict[str, Any]:
        return self._persist(campaign_id, {
            "active_sources": active_sources or [], "total_signals": total_signals, **kw,
        })
