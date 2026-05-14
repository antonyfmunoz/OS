"""Resilience Continuity Bridges v1.

Bridges between resilience coordination and substrate layers:
  scaling ↔ resilience
  environments ↔ resilience
  operations ↔ resilience
  workflows ↔ resilience
  sessions ↔ resilience
  replay ↔ resilience
  continuity ↔ resilience
  observability ↔ resilience

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.resilience.adaptive_resilience_contracts_v1 import (
    _new_id,
    _now_iso,
)


class _BaseBridge:
    """Shared persistence for all resilience bridges."""

    def __init__(
        self,
        bridge_type: str,
        state_dir: str | Path = "data/runtime/resilience/lineage",
    ) -> None:
        self._bridge_type = bridge_type
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def _persist(self, data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "bridge_id": _new_id("rbr"),
            "bridge_type": self._bridge_type,
            "data": data,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / f"{self._bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        self._total_captures += 1
        return record


class ScalingResilienceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/resilience/lineage") -> None:
        super().__init__("scaling_resilience", state_dir)

    def capture(self, pressure_score: float = 0.0, instability_score: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "pressure_score": pressure_score,
            "instability_score": instability_score,
            **kw,
        })


class EnvironmentsResilienceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/resilience/lineage") -> None:
        super().__init__("environments_resilience", state_dir)

    def capture(self, environment_id: str = "", healthy: bool = True,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "environment_id": environment_id, "healthy": healthy, **kw,
        })


class OperationsResilienceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/resilience/lineage") -> None:
        super().__init__("operations_resilience", state_dir)

    def capture(self, campaign_id: str = "", fault_count: int = 0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "campaign_id": campaign_id, "fault_count": fault_count, **kw,
        })


class WorkflowsResilienceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/resilience/lineage") -> None:
        super().__init__("workflows_resilience", state_dir)

    def capture(self, workflow_id: str = "", degraded: bool = False,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "workflow_id": workflow_id, "degraded": degraded, **kw,
        })


class SessionsResilienceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/resilience/lineage") -> None:
        super().__init__("sessions_resilience", state_dir)

    def capture(self, session_id: str = "", isolated: bool = False,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "session_id": session_id, "isolated": isolated, **kw,
        })


class ReplayResilienceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/resilience/lineage") -> None:
        super().__init__("replay_resilience", state_dir)

    def capture(self, total_validations: int = 0, total_passes: int = 0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "total_validations": total_validations,
            "total_passes": total_passes,
            **kw,
        })


class ContinuityResilienceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/resilience/lineage") -> None:
        super().__init__("continuity_resilience", state_dir)

    def capture(self, checkpoint_count: int = 0, continuity_intact: bool = True,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "checkpoint_count": checkpoint_count,
            "continuity_intact": continuity_intact,
            **kw,
        })


class ObservabilityResilienceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/resilience/lineage") -> None:
        super().__init__("observability_resilience", state_dir)

    def capture(self, total_events: int = 0, event_rate: float = 0.0,
                **kw: Any) -> dict[str, Any]:
        return self._persist({
            "total_events": total_events, "event_rate": event_rate, **kw,
        })
