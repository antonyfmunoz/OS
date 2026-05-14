"""Environment Observability Pipeline v1.

Emits and persists environment coordination events:
  registered, available, unavailable, selected,
  delegated, denied, synchronized, restored,
  checkpointed, replayed.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    EnvironmentEventType,
    _new_id,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    et.value: f"{et.value}.jsonl" for et in EnvironmentEventType
}


class EnvironmentObservabilityPipeline:
    """Observability for environment coordination."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/environment_coordination/observability",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []
        self._total_events: int = 0

    def emit(
        self,
        event_type: EnvironmentEventType,
        environment_id: str = "",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": _new_id("eobs"),
            "event_type": event_type.value,
            "environment_id": environment_id,
            "data": data or {},
            "timestamp": _now_iso(),
        }
        self._events.append(event)
        self._total_events += 1

        filename = EVENT_FILE_MAP.get(event_type.value, "unknown_events.jsonl")
        path = self._state_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return event

    def emit_registered(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_REGISTERED, environment_id, kw)

    def emit_available(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_AVAILABLE, environment_id, kw)

    def emit_unavailable(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_UNAVAILABLE, environment_id, kw)

    def emit_selected(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_SELECTED, environment_id, kw)

    def emit_delegated(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_DELEGATED, environment_id, kw)

    def emit_denied(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_DENIED, environment_id, kw)

    def emit_synchronized(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_SYNCHRONIZED, environment_id, kw)

    def emit_restored(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_RESTORED, environment_id, kw)

    def emit_checkpointed(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_CHECKPOINTED, environment_id, kw)

    def emit_replayed(self, environment_id: str, **kw: Any) -> dict[str, Any]:
        return self.emit(EnvironmentEventType.ENVIRONMENT_REPLAYED, environment_id, kw)

    def get_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._events[-limit:]

    def read_events(self, event_type: EnvironmentEventType) -> list[dict[str, Any]]:
        filename = EVENT_FILE_MAP.get(event_type.value, "")
        if not filename:
            return []
        path = self._state_dir / filename
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                events.append(json.loads(line))
        return events

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "event_types": len(EVENT_FILE_MAP),
        }
