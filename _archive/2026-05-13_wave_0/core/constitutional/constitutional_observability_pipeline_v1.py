"""Constitutional Observability Pipeline v1.

7 event types for constitutional runtime consolidation.
Dynamic EVENT_FILE_MAP from enum. JSONL persistence.

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import (
    ConstitutionalEventType,
    _now_iso,
)

EVENT_FILE_MAP: dict[str, str] = {
    e.value: f"{e.value}.jsonl" for e in ConstitutionalEventType
}


class ConstitutionalObservabilityPipeline:
    """Emits and persists constitutional runtime events."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/constitutional/observability",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []

    def _emit(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "event_type": event_type,
            "timestamp": _now_iso(),
            **payload,
        }
        self._events.append(event)

        filename = EVENT_FILE_MAP.get(event_type, "unknown.jsonl")
        path = self._state_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return event

    def emit_invariant_validated(
        self, invariant_id: str, domain: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            ConstitutionalEventType.INVARIANT_VALIDATED.value,
            {"invariant_id": invariant_id, "domain": domain, **kwargs},
        )

    def emit_invariant_violated(
        self, invariant_id: str, domain: str, severity: str = "violation",
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            ConstitutionalEventType.INVARIANT_VIOLATED.value,
            {"invariant_id": invariant_id, "domain": domain,
             "severity": severity, **kwargs},
        )

    def emit_replay_semantics_validated(
        self, layers_checked: int = 0, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            ConstitutionalEventType.REPLAY_SEMANTICS_VALIDATED.value,
            {"layers_checked": layers_checked, **kwargs},
        )

    def emit_lifecycle_semantics_validated(
        self, layers_checked: int = 0, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            ConstitutionalEventType.LIFECYCLE_SEMANTICS_VALIDATED.value,
            {"layers_checked": layers_checked, **kwargs},
        )

    def emit_topology_semantics_validated(
        self, domains_checked: int = 0, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            ConstitutionalEventType.TOPOLOGY_SEMANTICS_VALIDATED.value,
            {"domains_checked": domains_checked, **kwargs},
        )

    def emit_continuity_semantics_validated(
        self, layers_checked: int = 0, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            ConstitutionalEventType.CONTINUITY_SEMANTICS_VALIDATED.value,
            {"layers_checked": layers_checked, **kwargs},
        )

    def emit_constitutional_replay_validated(
        self, checks_passed: int = 0, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            ConstitutionalEventType.CONSTITUTIONAL_REPLAY_VALIDATED.value,
            {"checks_passed": checks_passed, **kwargs},
        )

    def get_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._events[-limit:]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_events": len(self._events),
        }
