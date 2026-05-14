"""Intelligence Continuity Bridges v1.

Bridges between intelligence coordination and substrate layers:
  cognition ↔ intelligence
  workflows ↔ intelligence
  operations ↔ intelligence
  resilience ↔ intelligence
  environments ↔ intelligence
  scaling ↔ intelligence
  sessions ↔ intelligence
  replay ↔ intelligence
  observability ↔ intelligence

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    _new_id,
    _now_iso,
)


class _BaseBridge:
    """Shared persistence for all intelligence bridges."""

    def __init__(
        self,
        bridge_type: str,
        state_dir: str | Path = "data/runtime/intelligence/lineage",
    ) -> None:
        self._bridge_type = bridge_type
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def _persist(self, data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "bridge_id": _new_id("ibr"),
            "bridge_type": self._bridge_type,
            "data": data,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / f"{self._bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        self._total_captures += 1
        return record


class CognitionIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("cognition_intelligence", state_dir)

    def capture(self, focus: str = "", attention_score: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "focus": focus, "attention_score": attention_score, **kw,
        })


class WorkflowsIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("workflows_intelligence", state_dir)

    def capture(self, workflow_id: str = "", status: str = "",
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "workflow_id": workflow_id, "status": status, **kw,
        })


class OperationsIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("operations_intelligence", state_dir)

    def capture(self, campaign_id: str = "", progress: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "campaign_id": campaign_id, "progress": progress, **kw,
        })


class ResilienceIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("resilience_intelligence", state_dir)

    def capture(self, instability_score: float = 0.0, survivability: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "instability_score": instability_score,
            "survivability": survivability,
            **kw,
        })


class EnvironmentsIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("environments_intelligence", state_dir)

    def capture(self, environment_id: str = "", healthy: bool = True,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "environment_id": environment_id, "healthy": healthy, **kw,
        })


class ScalingIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("scaling_intelligence", state_dir)

    def capture(self, pressure_score: float = 0.0, throttle_active: bool = False,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "pressure_score": pressure_score,
            "throttle_active": throttle_active,
            **kw,
        })


class SessionsIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("sessions_intelligence", state_dir)

    def capture(self, session_id: str = "", active: bool = True,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "session_id": session_id, "active": active, **kw,
        })


class ReplayIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("replay_intelligence", state_dir)

    def capture(self, total_validations: int = 0, total_passes: int = 0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "total_validations": total_validations,
            "total_passes": total_passes,
            **kw,
        })


class ObservabilityIntelligenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/intelligence/lineage") -> None:
        super().__init__("observability_intelligence", state_dir)

    def capture(self, total_events: int = 0, event_rate: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "total_events": total_events, "event_rate": event_rate, **kw,
        })
