"""Scaling Continuity Bridges v1.

Bridges between scaling coordination and substrate layers:
  operations ↔ scaling
  environments ↔ scaling
  workflows ↔ scaling
  sessions ↔ scaling
  observability ↔ scaling
  replay ↔ scaling
  continuity ↔ scaling

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    _new_id,
    _now_iso,
)


class _BaseBridge:
    """Shared persistence for all scaling bridges."""

    def __init__(
        self,
        bridge_type: str,
        state_dir: str | Path = "data/runtime/scaling/lineage",
    ) -> None:
        self._bridge_type = bridge_type
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def _persist(self, data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "bridge_id": _new_id("sbr"),
            "bridge_type": self._bridge_type,
            "data": data,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / f"{self._bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        self._total_captures += 1
        return record


class OperationsScalingBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/scaling/lineage") -> None:
        super().__init__("operations_scaling", state_dir)

    def capture(self, campaign_id: str = "", pressure_score: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "campaign_id": campaign_id, "pressure_score": pressure_score, **kw,
        })


class EnvironmentsScalingBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/scaling/lineage") -> None:
        super().__init__("environments_scaling", state_dir)

    def capture(self, environment_id: str = "", saturation: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "environment_id": environment_id, "saturation": saturation, **kw,
        })


class WorkflowsScalingBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/scaling/lineage") -> None:
        super().__init__("workflows_scaling", state_dir)

    def capture(self, workflow_id: str = "", concurrency: int = 0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "workflow_id": workflow_id, "concurrency": concurrency, **kw,
        })


class SessionsScalingBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/scaling/lineage") -> None:
        super().__init__("sessions_scaling", state_dir)

    def capture(self, session_id: str = "", active_traversals: int = 0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "session_id": session_id, "active_traversals": active_traversals, **kw,
        })


class ObservabilityScalingBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/scaling/lineage") -> None:
        super().__init__("observability_scaling", state_dir)

    def capture(self, total_events: int = 0, event_rate: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "total_events": total_events, "event_rate": event_rate, **kw,
        })


class ReplayScalingBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/scaling/lineage") -> None:
        super().__init__("replay_scaling", state_dir)

    def capture(self, total_validations: int = 0, total_passes: int = 0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "total_validations": total_validations, "total_passes": total_passes, **kw,
        })


class ContinuityScalingBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/scaling/lineage") -> None:
        super().__init__("continuity_scaling", state_dir)

    def capture(self, checkpoint_count: int = 0, continuation_depth: int = 0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "checkpoint_count": checkpoint_count, "continuation_depth": continuation_depth, **kw,
        })
