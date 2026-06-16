"""Worker Registry — active worker inventory per device.

Tracks which workers are alive on which devices, their capabilities,
status, and current task. Thread-safe. Emits lifecycle events to
EventSpine.

Phase 24. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorkerStatus(str, Enum):
    SPAWNING = "spawning"
    IDLE = "idle"
    WORKING = "working"
    STOPPING = "stopping"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class WorkerInstance:
    worker_id: str = field(default_factory=lambda: f"wkr-{uuid4().hex[:8]}")
    device_id: str = ""
    runtime_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    spec: Any = None
    status: WorkerStatus = WorkerStatus.SPAWNING
    current_task_id: str = ""
    started_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "device_id": self.device_id,
            "runtime_id": self.runtime_id,
            "capabilities": self.capabilities,
            "status": self.status.value if isinstance(self.status, WorkerStatus) else self.status,
            "current_task_id": self.current_task_id,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "metadata": self.metadata,
        }


class WorkerRegistry:
    """Persistent in-memory registry of active worker instances per device."""

    def __init__(self, event_spine: Any = None) -> None:
        self._workers: dict[str, WorkerInstance] = {}
        self._by_device: dict[str, set[str]] = {}
        self._event_spine = event_spine
        self._lock = threading.Lock()

    def register(
        self,
        worker_id: str,
        device_id: str,
        runtime_id: str,
        capabilities: list[str] | None = None,
        spec: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkerInstance:
        worker = WorkerInstance(
            worker_id=worker_id,
            device_id=device_id,
            runtime_id=runtime_id,
            capabilities=capabilities or [],
            spec=spec,
            metadata=metadata or {},
        )
        with self._lock:
            self._workers[worker_id] = worker
            self._by_device.setdefault(device_id, set()).add(worker_id)
        self._emit("worker_registered", {"worker_id": worker_id, "device_id": device_id})
        return worker

    def unregister(self, worker_id: str) -> WorkerInstance | None:
        with self._lock:
            worker = self._workers.pop(worker_id, None)
            if worker is not None:
                device_set = self._by_device.get(worker.device_id)
                if device_set:
                    device_set.discard(worker_id)
        if worker is not None:
            self._emit(
                "worker_unregistered", {"worker_id": worker_id, "device_id": worker.device_id}
            )
        return worker

    def update_status(
        self, worker_id: str, status: WorkerStatus, current_task_id: str = ""
    ) -> bool:
        with self._lock:
            worker = self._workers.get(worker_id)
            if worker is None:
                return False
            worker.status = status
            worker.current_task_id = current_task_id
            worker.last_heartbeat = time.time()
        self._emit("worker_status_changed", {"worker_id": worker_id, "status": status.value})
        return True

    def heartbeat(self, worker_id: str) -> bool:
        with self._lock:
            worker = self._workers.get(worker_id)
            if worker is None:
                return False
            worker.last_heartbeat = time.time()
        return True

    def get(self, worker_id: str) -> WorkerInstance | None:
        with self._lock:
            return self._workers.get(worker_id)

    def workers_on_device(self, device_id: str) -> list[WorkerInstance]:
        with self._lock:
            ids = self._by_device.get(device_id, set())
            return [self._workers[wid] for wid in ids if wid in self._workers]

    def active_workers(self) -> list[WorkerInstance]:
        with self._lock:
            return [w for w in self._workers.values() if w.status != WorkerStatus.TERMINATED]

    def idle_workers(self, device_id: str | None = None) -> list[WorkerInstance]:
        with self._lock:
            workers = self._workers.values()
            if device_id is not None:
                ids = self._by_device.get(device_id, set())
                workers = [self._workers[wid] for wid in ids if wid in self._workers]
            return [w for w in workers if w.status == WorkerStatus.IDLE]

    def workers_with_capability(self, capability: str) -> list[WorkerInstance]:
        with self._lock:
            return [
                w
                for w in self._workers.values()
                if capability in w.capabilities and w.status != WorkerStatus.TERMINATED
            ]

    def stale_workers(self, timeout_s: float = 120.0) -> list[str]:
        now = time.time()
        with self._lock:
            return [
                wid
                for wid, w in self._workers.items()
                if w.status not in (WorkerStatus.TERMINATED, WorkerStatus.FAILED)
                and (now - w.last_heartbeat) > timeout_s
            ]

    def worker_count_by_device(self) -> dict[str, int]:
        with self._lock:
            return {
                device_id: len([wid for wid in ids if wid in self._workers])
                for device_id, ids in self._by_device.items()
            }

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "workers": [w.to_dict() for w in self._workers.values()],
                "total": len(self._workers),
                "by_device": {did: len(ids) for did, ids in self._by_device.items()},
            }

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._event_spine is None:
            return
        try:
            from substrate.organism.event_spine import EventDomain

            self._event_spine.emit(
                domain=EventDomain.WORKER,
                event_type=event_type,
                source="worker_registry",
                data=data,
            )
        except Exception as exc:
            logger.debug("WorkerRegistry event emission failed: %s", exc)
