"""Operational Observability Pipeline v1.

Records 12 event types for operational observability:
  objective_created, campaign_started, stage_started,
  stage_completed, stage_failed, stage_deferred,
  continuation_restored, approval_requested, approval_received,
  execution_suspended, execution_resumed, execution_terminated

Each event type persists to its own JSONL file.

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import (
    OperationalEventType,
    _new_id,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    et.value: f"op_{et.value}_events.jsonl"
    for et in OperationalEventType
}


class OperationalObservabilityPipeline:
    """Records operational events to JSONL files."""

    def __init__(
        self,
        obs_dir: str | Path = "data/runtime/operational_observability",
    ) -> None:
        self._obs_dir = Path(obs_dir)
        self._obs_dir.mkdir(parents=True, exist_ok=True)
        self._event_counts: dict[str, int] = {
            et.value: 0 for et in OperationalEventType
        }
        self._total_events: int = 0

    def record_event(
        self,
        event_type: OperationalEventType,
        campaign_id: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": _new_id("opobs"),
            "event_type": event_type.value,
            "campaign_id": campaign_id,
            "data": data or {},
            "timestamp": _now_iso(),
        }

        filename = EVENT_FILE_MAP.get(event_type.value, "op_unknown_events.jsonl")
        path = self._obs_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        self._event_counts[event_type.value] += 1
        self._total_events += 1
        return event

    def record_objective_created(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.OBJECTIVE_CREATED, campaign_id, kw)

    def record_campaign_started(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.CAMPAIGN_STARTED, campaign_id, kw)

    def record_stage_started(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.STAGE_STARTED, campaign_id, kw)

    def record_stage_completed(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.STAGE_COMPLETED, campaign_id, kw)

    def record_stage_failed(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.STAGE_FAILED, campaign_id, kw)

    def record_stage_deferred(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.STAGE_DEFERRED, campaign_id, kw)

    def record_continuation_restored(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.CONTINUATION_RESTORED, campaign_id, kw)

    def record_approval_requested(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.APPROVAL_REQUESTED, campaign_id, kw)

    def record_approval_received(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.APPROVAL_RECEIVED, campaign_id, kw)

    def record_execution_suspended(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.EXECUTION_SUSPENDED, campaign_id, kw)

    def record_execution_resumed(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.EXECUTION_RESUMED, campaign_id, kw)

    def record_execution_terminated(self, campaign_id: str, **kw: Any) -> dict[str, Any]:
        return self.record_event(OperationalEventType.EXECUTION_TERMINATED, campaign_id, kw)

    def get_events_by_type(
        self, event_type: OperationalEventType, limit: int = 50,
    ) -> list[dict[str, Any]]:
        filename = EVENT_FILE_MAP.get(event_type.value)
        if not filename:
            return []
        path = self._obs_dir / filename
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "event_counts": dict(self._event_counts),
        }
