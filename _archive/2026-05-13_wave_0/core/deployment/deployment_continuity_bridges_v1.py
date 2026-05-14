"""Deployment Continuity Bridges v1.

9 bridges connecting deployments to other substrate layers:
applications, environments, scaling, resilience, sessions,
workflows, observability, replay, governance ↔ deployments.

Uses _BaseBridge pattern for shared persistence.

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.deployment.platform_deployment_contracts_v1 import _now_iso


class _BaseBridge:
    """Shared bridge pattern for deployment continuity."""

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


class ApplicationsDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("applications_deployment", state_dir)


class EnvironmentsDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("environments_deployment", state_dir)


class ScalingDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("scaling_deployment", state_dir)


class ResilienceDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("resilience_deployment", state_dir)


class SessionsDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("sessions_deployment", state_dir)


class WorkflowsDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("workflows_deployment", state_dir)


class ObservabilityDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("observability_deployment", state_dir)


class ReplayDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("replay_deployment", state_dir)


class GovernanceDeploymentBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/deployments/bridges") -> None:
        super().__init__("governance_deployment", state_dir)


ALL_BRIDGES = [
    ApplicationsDeploymentBridge,
    EnvironmentsDeploymentBridge,
    ScalingDeploymentBridge,
    ResilienceDeploymentBridge,
    SessionsDeploymentBridge,
    WorkflowsDeploymentBridge,
    ObservabilityDeploymentBridge,
    ReplayDeploymentBridge,
    GovernanceDeploymentBridge,
]
