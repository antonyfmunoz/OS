"""Environment Continuity Bridges v1.

Bridges between environments and substrate layers:
  operations ↔ environments
  sessions ↔ environments
  workflows ↔ environments
  ingress ↔ environments
  cognition ↔ environments
  embodiment ↔ environments
  observability ↔ environments
  replay ↔ environments

Each bridge captures layer-specific state into the
environment coordination model.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    _new_id,
    _now_iso,
)


class _BaseBridge:
    """Shared persistence for all environment bridges."""

    def __init__(
        self,
        bridge_type: str,
        state_dir: str | Path = "data/runtime/environment_coordination/lineage",
    ) -> None:
        self._bridge_type = bridge_type
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_captures: int = 0

    def _persist(self, environment_id: str, data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "bridge_id": _new_id("envbr"),
            "bridge_type": self._bridge_type,
            "environment_id": environment_id,
            "data": data,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / f"{self._bridge_type}_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        self._total_captures += 1
        return record


class OperationsEnvironmentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/environment_coordination/lineage") -> None:
        super().__init__("operations_environment", state_dir)

    def capture(self, environment_id: str, campaign_id: str = "",
                operation: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(environment_id, {
            "campaign_id": campaign_id, "operation": operation, **kw,
        })


class SessionsEnvironmentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/environment_coordination/lineage") -> None:
        super().__init__("sessions_environment", state_dir)

    def capture(self, environment_id: str, session_id: str = "",
                session_state: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(environment_id, {
            "session_id": session_id, "session_state": session_state, **kw,
        })


class WorkflowsEnvironmentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/environment_coordination/lineage") -> None:
        super().__init__("workflows_environment", state_dir)

    def capture(self, environment_id: str, workflow_id: str = "",
                workflow_state: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(environment_id, {
            "workflow_id": workflow_id, "workflow_state": workflow_state, **kw,
        })


class IngressEnvironmentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/environment_coordination/lineage") -> None:
        super().__init__("ingress_environment", state_dir)

    def capture(self, environment_id: str, source: str = "",
                signal_id: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(environment_id, {
            "source": source, "signal_id": signal_id, **kw,
        })


class CognitionEnvironmentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/environment_coordination/lineage") -> None:
        super().__init__("cognition_environment", state_dir)

    def capture(self, environment_id: str, operator_mode: str = "",
                cognition_phase: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(environment_id, {
            "operator_mode": operator_mode, "cognition_phase": cognition_phase, **kw,
        })


class EmbodimentEnvironmentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/environment_coordination/lineage") -> None:
        super().__init__("embodiment_environment", state_dir)

    def capture(self, environment_id: str, workstation_mode: str = "",
                browser_mode: str = "", **kw: Any) -> dict[str, Any]:
        return self._persist(environment_id, {
            "workstation_mode": workstation_mode, "browser_mode": browser_mode, **kw,
        })


class ObservabilityEnvironmentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/environment_coordination/lineage") -> None:
        super().__init__("observability_environment", state_dir)

    def capture(self, environment_id: str, total_events: int = 0,
                event_types: dict[str, int] | None = None, **kw: Any) -> dict[str, Any]:
        return self._persist(environment_id, {
            "total_events": total_events, "event_types": event_types or {}, **kw,
        })


class ReplayEnvironmentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/environment_coordination/lineage") -> None:
        super().__init__("replay_environment", state_dir)

    def capture(self, environment_id: str, total_validations: int = 0,
                total_passes: int = 0, **kw: Any) -> dict[str, Any]:
        return self._persist(environment_id, {
            "total_validations": total_validations, "total_passes": total_passes, **kw,
        })
