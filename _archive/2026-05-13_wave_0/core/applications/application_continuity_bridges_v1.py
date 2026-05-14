"""Application Continuity Bridges v1.

9 bridges connecting applications to other substrate layers:
sessions, workflows, knowledge, learning, cognition,
ingress, environments, scaling, resilience ↔ applications.

Uses _BaseBridge pattern for shared persistence.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.applications.application_projection_contracts_v1 import _now_iso


class _BaseBridge:
    """Shared bridge pattern for application continuity."""

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


class SessionsApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("sessions_application", state_dir)


class WorkflowsApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("workflows_application", state_dir)


class KnowledgeApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("knowledge_application", state_dir)


class LearningApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("learning_application", state_dir)


class CognitionApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("cognition_application", state_dir)


class IngressApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("ingress_application", state_dir)


class EnvironmentsApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("environments_application", state_dir)


class ScalingApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("scaling_application", state_dir)


class ResilienceApplicationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/applications/bridges") -> None:
        super().__init__("resilience_application", state_dir)


ALL_BRIDGES = [
    SessionsApplicationBridge,
    WorkflowsApplicationBridge,
    KnowledgeApplicationBridge,
    LearningApplicationBridge,
    CognitionApplicationBridge,
    IngressApplicationBridge,
    EnvironmentsApplicationBridge,
    ScalingApplicationBridge,
    ResilienceApplicationBridge,
]
