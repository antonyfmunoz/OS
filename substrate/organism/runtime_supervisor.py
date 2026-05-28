"""RuntimeSupervisor — persistent runtime lifecycle management.

Manages the lifecycle of runtime processes: spawn, monitor heartbeat,
detect crashes, restart with exponential backoff, and track health
state transitions.

Health state machine:
  STOPPED → STARTING → ALIVE → DEGRADED → DEAD → RECOVERING → ALIVE
                                    ↓
                                  DEAD → RECOVERING → ALIVE

Crash loop detection (adapted from cortextOS):
  - Sliding window: N crashes within M seconds = auto-pause
  - Daily crash budget: max K restarts per day
  - Exponential backoff: 5s * 2^N, max 300s

UMH substrate subsystem.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    RuntimeGraph,
    RuntimeNode,
)

logger = logging.getLogger(__name__)


class SupervisedHealth(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    ALIVE = "alive"
    DEGRADED = "degraded"
    DEAD = "dead"
    RECOVERING = "recovering"
    PAUSED = "paused"


_HEARTBEAT_TIMEOUT_S = 90.0
_HEARTBEAT_DEGRADED_S = 45.0
_BASE_BACKOFF_S = 5.0
_MAX_BACKOFF_S = 300.0
_CRASH_WINDOW_S = 900.0
_MAX_CRASHES_IN_WINDOW = 5
_MAX_DAILY_RESTARTS = 15


@dataclass
class CrashRecord:
    runtime_id: str
    timestamp: float
    error: str = ""
    generation: int = 0


@dataclass
class SupervisedRuntime:
    """A runtime under supervision."""

    runtime_id: str
    health: SupervisedHealth = SupervisedHealth.STOPPED
    last_heartbeat: float = 0.0
    generation: int = 0
    restart_count: int = 0
    daily_restart_count: int = 0
    daily_reset_at: float = 0.0
    last_restart_at: float = 0.0
    crashes: list[CrashRecord] = field(default_factory=list)
    paused_until: float = 0.0
    error: str = ""

    @property
    def is_alive(self) -> bool:
        return self.health in {SupervisedHealth.ALIVE, SupervisedHealth.DEGRADED}

    @property
    def is_paused(self) -> bool:
        return self.health == SupervisedHealth.PAUSED and time.time() < self.paused_until

    @property
    def backoff_seconds(self) -> float:
        return min(_BASE_BACKOFF_S * (2**self.restart_count), _MAX_BACKOFF_S)

    def crashes_in_window(self) -> int:
        cutoff = time.time() - _CRASH_WINDOW_S
        return sum(1 for c in self.crashes if c.timestamp > cutoff)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "health": self.health.value,
            "generation": self.generation,
            "restart_count": self.restart_count,
            "daily_restart_count": self.daily_restart_count,
            "crashes_in_window": self.crashes_in_window(),
            "backoff_seconds": round(self.backoff_seconds, 1),
            "is_paused": self.is_paused,
            "error": self.error[:200] if self.error else "",
        }


class RuntimeSupervisor:
    """Supervises runtime lifecycle with crash detection and recovery.

    Does NOT directly spawn processes — that responsibility stays with
    the RuntimeAdapter. The supervisor monitors heartbeats, detects
    failures, decides whether to restart, and coordinates with the
    RuntimeGraph to update availability status.
    """

    def __init__(
        self,
        graph: RuntimeGraph,
        state_dir: str | Path = "data/umh/supervisor",
        event_spine: Any | None = None,
    ) -> None:
        self._graph = graph
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._supervised: dict[str, SupervisedRuntime] = {}
        self._event_spine = event_spine

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._event_spine is None:
            return
        from substrate.organism.event_spine import EventDomain
        self._event_spine.emit(EventDomain.SUPERVISOR, event_type, "runtime_supervisor", data)

    def supervise(self, runtime_id: str) -> SupervisedRuntime:
        """Start supervising a runtime."""
        if runtime_id in self._supervised:
            return self._supervised[runtime_id]

        sr = SupervisedRuntime(runtime_id=runtime_id)
        self._supervised[runtime_id] = sr

        node = self._graph.get(runtime_id)
        if node and node.adapter:
            try:
                available = node.adapter.check_available()
                sr.health = SupervisedHealth.ALIVE if available else SupervisedHealth.STOPPED
                sr.last_heartbeat = time.time() if available else 0.0
            except Exception:
                sr.health = SupervisedHealth.STOPPED

        logger.info("supervising runtime: %s (health=%s)", runtime_id, sr.health.value)
        return sr

    def heartbeat(self, runtime_id: str) -> None:
        """Record a heartbeat from a runtime."""
        sr = self._supervised.get(runtime_id)
        if not sr:
            return

        sr.last_heartbeat = time.time()

        if sr.health in {
            SupervisedHealth.DEAD,
            SupervisedHealth.RECOVERING,
            SupervisedHealth.STARTING,
        }:
            sr.health = SupervisedHealth.ALIVE
            sr.restart_count = 0
            self._graph.update_status(runtime_id, AvailabilityStatus.AVAILABLE)
        elif sr.health == SupervisedHealth.DEGRADED:
            sr.health = SupervisedHealth.ALIVE
            self._graph.update_status(runtime_id, AvailabilityStatus.AVAILABLE)

    def check_health(self, runtime_id: str) -> SupervisedHealth:
        """Evaluate a runtime's health based on heartbeat freshness."""
        sr = self._supervised.get(runtime_id)
        if not sr:
            return SupervisedHealth.STOPPED

        if sr.is_paused:
            return SupervisedHealth.PAUSED

        if sr.health == SupervisedHealth.STOPPED:
            return SupervisedHealth.STOPPED

        now = time.time()
        age = now - sr.last_heartbeat if sr.last_heartbeat > 0 else float("inf")

        if age > _HEARTBEAT_TIMEOUT_S:
            if sr.health != SupervisedHealth.DEAD:
                sr.health = SupervisedHealth.DEAD
                self._graph.update_status(runtime_id, AvailabilityStatus.UNAVAILABLE)
                logger.warning(
                    "runtime %s declared DEAD (no heartbeat for %.0fs)",
                    runtime_id,
                    age,
                )
        elif age > _HEARTBEAT_DEGRADED_S:
            if sr.health != SupervisedHealth.DEGRADED:
                sr.health = SupervisedHealth.DEGRADED
                self._graph.update_status(runtime_id, AvailabilityStatus.DEGRADED)
        else:
            if sr.health not in {SupervisedHealth.ALIVE, SupervisedHealth.STARTING}:
                sr.health = SupervisedHealth.ALIVE
                self._graph.update_status(runtime_id, AvailabilityStatus.AVAILABLE)

        return sr.health

    def record_crash(self, runtime_id: str, error: str = "") -> None:
        """Record a runtime crash and evaluate recovery."""
        sr = self._supervised.get(runtime_id)
        if not sr:
            return

        sr.generation += 1
        crash = CrashRecord(
            runtime_id=runtime_id,
            timestamp=time.time(),
            error=error,
            generation=sr.generation,
        )
        sr.crashes.append(crash)
        if len(sr.crashes) > 100:
            sr.crashes = sr.crashes[-100:]

        sr.health = SupervisedHealth.DEAD
        sr.error = error
        self._graph.update_status(runtime_id, AvailabilityStatus.UNAVAILABLE)

        logger.warning(
            "runtime %s crashed (gen=%d): %s",
            runtime_id,
            sr.generation,
            error[:200],
        )
        self._emit("runtime_crashed", {"runtime_id": runtime_id, "error": error or ""})

    def should_restart(self, runtime_id: str) -> tuple[bool, str]:
        """Determine if a crashed runtime should be restarted.

        Returns (should_restart, reason).
        """
        sr = self._supervised.get(runtime_id)
        if not sr:
            return False, "not_supervised"

        if sr.health not in {SupervisedHealth.DEAD, SupervisedHealth.STOPPED}:
            return False, f"health_is_{sr.health.value}"

        if sr.is_paused:
            remaining = sr.paused_until - time.time()
            return False, f"paused_for_{remaining:.0f}s"

        now = time.time()
        day_start = now - (now % 86400)
        if sr.daily_reset_at < day_start:
            sr.daily_restart_count = 0
            sr.daily_reset_at = now

        if sr.daily_restart_count >= _MAX_DAILY_RESTARTS:
            return False, f"daily_budget_exhausted ({sr.daily_restart_count}/{_MAX_DAILY_RESTARTS})"

        crashes_in_window = sr.crashes_in_window()
        if crashes_in_window >= _MAX_CRASHES_IN_WINDOW:
            pause_duration = _MAX_BACKOFF_S
            sr.paused_until = now + pause_duration
            sr.health = SupervisedHealth.PAUSED
            return (
                False,
                f"crash_loop_detected ({crashes_in_window} in {_CRASH_WINDOW_S}s), paused {pause_duration}s",
            )

        if sr.last_restart_at > 0:
            time_since = now - sr.last_restart_at
            if time_since < sr.backoff_seconds:
                remaining = sr.backoff_seconds - time_since
                return False, f"backoff_active ({remaining:.0f}s remaining)"

        return True, "restart_allowed"

    def mark_restarting(self, runtime_id: str) -> None:
        """Mark a runtime as restarting."""
        sr = self._supervised.get(runtime_id)
        if not sr:
            return

        sr.health = SupervisedHealth.RECOVERING
        sr.restart_count += 1
        sr.daily_restart_count += 1
        sr.last_restart_at = time.time()
        sr.generation += 1

        self._graph.update_status(runtime_id, AvailabilityStatus.STARTING)

        logger.info(
            "runtime %s restarting (gen=%d, attempt=%d, backoff=%.0fs)",
            runtime_id,
            sr.generation,
            sr.restart_count,
            sr.backoff_seconds,
        )

    def record_recovery_success(self, runtime_id: str, latency_ms: int = 0) -> None:
        """Record that a runtime recovered successfully after a restart."""
        sr = self._supervised.get(runtime_id)
        if not sr:
            return

        sr.health = SupervisedHealth.ALIVE
        sr.last_heartbeat = time.time()
        sr.error = ""

        self._graph.update_status(runtime_id, AvailabilityStatus.AVAILABLE)
        self._graph.record_success(runtime_id, latency_ms)

        logger.info(
            "runtime %s recovery confirmed (gen=%d)",
            runtime_id,
            sr.generation,
        )
        self._emit("runtime_recovered", {"runtime_id": runtime_id, "latency_ms": latency_ms or 0})

    def record_recovery_failure(self, runtime_id: str, error: str = "") -> None:
        """Record that a runtime failed to recover after a restart attempt."""
        sr = self._supervised.get(runtime_id)
        if not sr:
            return

        sr.health = SupervisedHealth.DEAD
        sr.error = error

        self._graph.update_status(runtime_id, AvailabilityStatus.UNAVAILABLE)
        self._graph.record_failure(runtime_id)

        logger.warning(
            "runtime %s recovery failed (gen=%d): %s",
            runtime_id,
            sr.generation,
            error[:200],
        )
        self._emit("runtime_recovery_failed", {"runtime_id": runtime_id, "error": error or ""})

    def reconcile_graph(self) -> dict[str, str]:
        """Full reconciliation: push all supervised health states to the graph.

        Call this after startup or when graph/supervisor may have drifted.
        Returns mapping of runtime_id → status pushed.
        """
        result: dict[str, str] = {}
        health_to_availability = {
            SupervisedHealth.ALIVE: AvailabilityStatus.AVAILABLE,
            SupervisedHealth.DEGRADED: AvailabilityStatus.DEGRADED,
            SupervisedHealth.DEAD: AvailabilityStatus.UNAVAILABLE,
            SupervisedHealth.STOPPED: AvailabilityStatus.UNAVAILABLE,
            SupervisedHealth.PAUSED: AvailabilityStatus.UNAVAILABLE,
            SupervisedHealth.RECOVERING: AvailabilityStatus.STARTING,
            SupervisedHealth.STARTING: AvailabilityStatus.STARTING,
        }

        for rid, sr in self._supervised.items():
            avail = health_to_availability.get(sr.health, AvailabilityStatus.UNKNOWN)
            self._graph.update_status(rid, avail)
            result[rid] = avail.value

        return result

    def check_all(self) -> dict[str, SupervisedHealth]:
        """Check health of all supervised runtimes."""
        return {rid: self.check_health(rid) for rid in self._supervised}

    def get_recovery_plan(self) -> list[dict[str, Any]]:
        """Get a recovery plan for all dead/stopped runtimes."""
        plan: list[dict[str, Any]] = []
        for rid, sr in self._supervised.items():
            if sr.health in {SupervisedHealth.DEAD, SupervisedHealth.STOPPED}:
                should, reason = self.should_restart(rid)
                plan.append(
                    {
                        "runtime_id": rid,
                        "current_health": sr.health.value,
                        "should_restart": should,
                        "reason": reason,
                        "restart_count": sr.restart_count,
                        "backoff_seconds": round(sr.backoff_seconds, 1),
                    }
                )
        return plan

    def persist_state(self) -> None:
        """Persist supervisor state for crash recovery."""
        state = {
            "supervised": {rid: sr.to_dict() for rid, sr in self._supervised.items()},
        }
        path = self._state_dir / "supervisor_state.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.rename(path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "supervised_count": len(self._supervised),
            "alive": sum(1 for sr in self._supervised.values() if sr.is_alive),
            "dead": sum(
                1 for sr in self._supervised.values() if sr.health == SupervisedHealth.DEAD
            ),
            "paused": sum(1 for sr in self._supervised.values() if sr.is_paused),
            "runtimes": {rid: sr.to_dict() for rid, sr in self._supervised.items()},
        }
