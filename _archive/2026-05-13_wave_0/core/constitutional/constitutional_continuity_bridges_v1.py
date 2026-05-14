"""Constitutional Continuity Bridges v1.

9 bridges connecting the constitutional runtime to other substrate layers:
governance, replay, continuity, topology, observability,
deployment, applications, cognition, orchestration ↔ constitutional.

Uses _BaseBridge pattern for shared persistence.

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import _now_iso


class _BaseBridge:
    """Shared bridge pattern for constitutional continuity."""

    def __init__(self, bridge_name: str, state_dir: str | Path) -> None:
        self._bridge_name = bridge_name
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []

    def record(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "bridge": self._bridge_name,
            "event_type": event_type,
            "timestamp": _now_iso(),
            **payload,
        }
        self._events.append(event)

        path = self._state_dir / f"{self._bridge_name}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return event

    def get_events(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._events[-limit:]

    def get_stats(self) -> dict[str, object]:
        return {
            "bridge_name": self._bridge_name,
            "total_events": len(self._events),
        }


class GovernanceConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("governance_constitutional", state_dir)


class ReplayConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("replay_constitutional", state_dir)


class ContinuityConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("continuity_constitutional", state_dir)


class TopologyConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("topology_constitutional", state_dir)


class ObservabilityConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("observability_constitutional", state_dir)


class DeploymentConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("deployment_constitutional", state_dir)


class ApplicationsConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("applications_constitutional", state_dir)


class CognitionConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("cognition_constitutional", state_dir)


class OrchestrationConstitutionalBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/constitutional/bridges") -> None:
        super().__init__("orchestration_constitutional", state_dir)


ALL_BRIDGES = [
    GovernanceConstitutionalBridge,
    ReplayConstitutionalBridge,
    ContinuityConstitutionalBridge,
    TopologyConstitutionalBridge,
    ObservabilityConstitutionalBridge,
    DeploymentConstitutionalBridge,
    ApplicationsConstitutionalBridge,
    CognitionConstitutionalBridge,
    OrchestrationConstitutionalBridge,
]
