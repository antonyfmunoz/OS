"""Learning Continuity Bridges v1.

9 bridges connecting learning to other substrate layers:
knowledge, memory, intelligence, workflows, operations,
resilience, scaling, replay, observability ↔ learning.

Uses _BaseBridge pattern for shared persistence.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.learning.adaptive_learning_contracts_v1 import _now_iso


class _BaseBridge:
    """Shared bridge pattern for learning continuity."""

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


class KnowledgeLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("knowledge_learning", state_dir)


class MemoryLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("memory_learning", state_dir)


class IntelligenceLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("intelligence_learning", state_dir)


class WorkflowsLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("workflows_learning", state_dir)


class OperationsLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("operations_learning", state_dir)


class ResilienceLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("resilience_learning", state_dir)


class ScalingLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("scaling_learning", state_dir)


class ReplayLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("replay_learning", state_dir)


class ObservabilityLearningBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/learning/bridges") -> None:
        super().__init__("observability_learning", state_dir)


ALL_BRIDGES = [
    KnowledgeLearningBridge,
    MemoryLearningBridge,
    IntelligenceLearningBridge,
    WorkflowsLearningBridge,
    OperationsLearningBridge,
    ResilienceLearningBridge,
    ScalingLearningBridge,
    ReplayLearningBridge,
    ObservabilityLearningBridge,
]
