"""Node daemon — persistent worker process for distributed execution.

Starts a WorkerLoop, sends heartbeats, and runs until stopped.
Can operate in LOCAL or REMOTE mode.

No imports from umh/cells, umh/environments, umh/adapters.
No subprocess, no shell — execution is delegated to the worker's
executor callback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Callable

from umh.core.clock import iso_now as _iso_now
from umh.jobs.models import ExecutionJob
from umh.jobs.store import JobStore
from umh.nodes.heartbeat import HeartbeatMonitor, HeartbeatStatus, NodeHeartbeat
from umh.nodes.worker import ExecutionResult, WorkerLoop

_log = logging.getLogger(__name__)


@unique
class DaemonMode(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


@dataclass
class DaemonConfig:
    """Configuration for a node daemon."""

    node_id: str
    mode: DaemonMode = DaemonMode.LOCAL
    poll_interval_s: float = 5.0
    heartbeat_interval_s: float = 30.0

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id must be non-empty")


class NodeDaemon:
    """Persistent worker daemon that claims and executes jobs.

    The daemon wraps a WorkerLoop and adds heartbeat emission.
    It does NOT run in an infinite loop itself — the caller drives
    ticks via tick() for testability, or calls run() for production.
    """

    def __init__(
        self,
        config: DaemonConfig,
        store: JobStore,
        *,
        heartbeat_monitor: HeartbeatMonitor | None = None,
        executor: Callable[[ExecutionJob], ExecutionResult] | None = None,
    ) -> None:
        self._config = config
        self._store = store
        self._heartbeat_monitor = heartbeat_monitor
        self._worker = WorkerLoop(
            node_id=config.node_id,
            store=store,
            executor=executor,
            poll_interval_s=config.poll_interval_s,
        )
        self._active = False
        self._tick_count = 0
        self._heartbeat_count = 0
        self._ticks_per_heartbeat = max(
            1, int(config.heartbeat_interval_s / config.poll_interval_s)
        )

    @property
    def config(self) -> DaemonConfig:
        return self._config

    @property
    def node_id(self) -> str:
        return self._config.node_id

    @property
    def mode(self) -> DaemonMode:
        return self._config.mode

    @property
    def active(self) -> bool:
        return self._active

    @property
    def worker(self) -> WorkerLoop:
        return self._worker

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def heartbeat_count(self) -> int:
        return self._heartbeat_count

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._worker.start()
        self._emit_heartbeat()
        _log.info("Daemon %s started in %s mode", self._config.node_id, self._config.mode.value)

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self._worker.stop()
        _log.info("Daemon %s stopped", self._config.node_id)

    def tick(self) -> dict[str, Any]:
        """Single daemon tick: poll for work + periodic heartbeat.

        Returns a summary dict of what happened this tick.
        """
        if not self._active:
            return {"error": "daemon not active", "tick": self._tick_count}

        self._tick_count += 1
        result: dict[str, Any] = {"tick": self._tick_count, "node_id": self._config.node_id}

        job = self._worker.poll_once()
        if job is not None:
            result["job_processed"] = job.job_id
            result["job_status"] = job.status.value

        if self._tick_count % self._ticks_per_heartbeat == 0:
            self._emit_heartbeat()
            result["heartbeat_sent"] = True

        result["stats"] = self._worker.stats.to_dict()
        return result

    def run_ticks(self, count: int) -> list[dict[str, Any]]:
        """Run multiple ticks. For testing."""
        results = []
        for _ in range(count):
            if not self._active:
                break
            results.append(self.tick())
        return results

    def _emit_heartbeat(self) -> None:
        """Send a heartbeat to the monitor if configured."""
        if self._heartbeat_monitor is None:
            return

        active_job_id = None
        if self._worker.current_job is not None:
            active_job_id = self._worker.current_job.job_id

        heartbeat = NodeHeartbeat(
            node_id=self._config.node_id,
            timestamp=_iso_now(),
            status=HeartbeatStatus.OK,
            telemetry={
                "active_job_id": active_job_id,
                "jobs_claimed": self._worker.stats.jobs_claimed,
                "jobs_succeeded": self._worker.stats.jobs_succeeded,
                "jobs_failed": self._worker.stats.jobs_failed,
                "polls": self._worker.stats.polls,
            },
            metadata={
                "mode": self._config.mode.value,
                "daemon": True,
            },
        )
        self._heartbeat_monitor.record_heartbeat(heartbeat)
        self._heartbeat_count += 1
