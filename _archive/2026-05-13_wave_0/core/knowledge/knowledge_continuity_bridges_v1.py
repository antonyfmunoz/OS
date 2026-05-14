"""Knowledge Continuity Bridges v1.

9 bridges connecting knowledge fabric to other substrate layers:
memory, intelligence, workflows, resilience, sessions,
continuity, replay, observability, cognition ↔ knowledge.

Uses _BaseBridge pattern for shared persistence.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import _now_iso


class _BaseBridge:
    """Shared bridge pattern for knowledge continuity."""

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


class MemoryKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("memory_knowledge", state_dir)


class IntelligenceKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("intelligence_knowledge", state_dir)


class WorkflowsKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("workflows_knowledge", state_dir)


class ResilienceKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("resilience_knowledge", state_dir)


class SessionsKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("sessions_knowledge", state_dir)


class ContinuityKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("continuity_knowledge", state_dir)


class ReplayKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("replay_knowledge", state_dir)


class ObservabilityKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("observability_knowledge", state_dir)


class CognitionKnowledgeBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/bridges") -> None:
        super().__init__("cognition_knowledge", state_dir)


ALL_BRIDGES = [
    MemoryKnowledgeBridge,
    IntelligenceKnowledgeBridge,
    WorkflowsKnowledgeBridge,
    ResilienceKnowledgeBridge,
    SessionsKnowledgeBridge,
    ContinuityKnowledgeBridge,
    ReplayKnowledgeBridge,
    ObservabilityKnowledgeBridge,
    CognitionKnowledgeBridge,
]
