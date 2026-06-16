"""Worker Lifecycle Emitter — structured lifecycle events.

Emits worker spawn/ready/idle/fail/terminate events to the organism
event spine. Consumed by reality model and cockpit.

Phase 24. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WorkerEventType(str, Enum):
    SPAWNED = "worker_spawned"
    READY = "worker_ready"
    ASSIGNED = "worker_assigned"
    IDLE = "worker_idle"
    FAILED = "worker_failed"
    TERMINATED = "worker_terminated"
    HEARTBEAT_LOST = "worker_heartbeat_lost"


class WorkerLifecycleEmitter:
    """Emits worker lifecycle events to the organism event spine."""

    def __init__(self, event_spine: Any) -> None:
        self._event_spine = event_spine

    def on_spawn(self, worker: Any) -> None:
        self._emit(
            WorkerEventType.SPAWNED,
            {
                "worker_id": worker.worker_id,
                "device_id": worker.device_id,
                "capabilities": worker.capabilities,
            },
        )

    def on_ready(self, worker: Any) -> None:
        self._emit(
            WorkerEventType.READY,
            {
                "worker_id": worker.worker_id,
                "device_id": worker.device_id,
            },
        )

    def on_assigned(self, worker: Any, task_id: str) -> None:
        self._emit(
            WorkerEventType.ASSIGNED,
            {
                "worker_id": worker.worker_id,
                "device_id": worker.device_id,
                "task_id": task_id,
            },
        )

    def on_idle(self, worker: Any) -> None:
        self._emit(
            WorkerEventType.IDLE,
            {
                "worker_id": worker.worker_id,
                "device_id": worker.device_id,
            },
        )

    def on_failed(self, worker: Any, error: str) -> None:
        self._emit(
            WorkerEventType.FAILED,
            {
                "worker_id": worker.worker_id,
                "device_id": worker.device_id,
                "error": error,
            },
        )

    def on_terminated(self, worker: Any, reason: str) -> None:
        self._emit(
            WorkerEventType.TERMINATED,
            {
                "worker_id": worker.worker_id,
                "device_id": worker.device_id,
                "reason": reason,
            },
        )

    def on_heartbeat_lost(self, worker_id: str, device_id: str) -> None:
        self._emit(
            WorkerEventType.HEARTBEAT_LOST,
            {
                "worker_id": worker_id,
                "device_id": device_id,
            },
        )

    def _emit(self, event_type: WorkerEventType, data: dict[str, Any]) -> None:
        try:
            from substrate.organism.event_spine import EventDomain

            self._event_spine.emit(
                domain=EventDomain.WORKER,
                event_type=event_type.value,
                source="worker_lifecycle",
                data=data,
            )
        except Exception as exc:
            logger.debug("WorkerLifecycleEmitter emission failed: %s", exc)
