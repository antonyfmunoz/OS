"""PersistentLoop — base class and registry for long-running substrate loops.

Three persistent loops compose existing machinery:
  1. BusinessOpsLoop  — orchestrator signal drain + scheduled operations
  2. SelfBuildLoop    — goal-driven execution loop for system improvement
  3. ResearchLoop     — cognitive loop for research + world model updates

Each loop:
  - Has a deterministic cycle (runs without LLM)
  - Writes a heartbeat after each cycle
  - Publishes cycle reports via the event bus
  - Respects governance (risk classification per action)
  - Can be started/stopped/queried independently

Usage:
    from substrate.execution.loop.persistent_loop import LoopRegistry

    registry = LoopRegistry()
    registry.register_defaults()
    registry.start("business_ops")
    print(registry.status())
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
_HEARTBEAT_DIR = _ROOT / "data" / "runtime" / "loop_heartbeats"


class LoopState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class CycleReport:
    """Outcome of a single loop cycle."""

    loop_name: str
    cycle_num: int
    started_at: str
    finished_at: str
    actions_taken: int = 0
    errors: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_name": self.loop_name,
            "cycle_num": self.cycle_num,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "actions_taken": self.actions_taken,
            "errors": self.errors,
            "details": self.details,
        }


class PersistentLoop(ABC):
    """Base class for substrate persistent loops.

    Subclasses implement run_cycle() — a single deterministic pass.
    The base class handles threading, heartbeats, and lifecycle.
    """

    def __init__(
        self,
        name: str,
        domain: str,
        interval_seconds: int = 300,
    ) -> None:
        self.name = name
        self.domain = domain
        self.interval_seconds = interval_seconds
        self.state = LoopState.STOPPED
        self._cycle_count = 0
        self._last_report: CycleReport | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._error_count = 0
        self._started_at: str | None = None

    @abstractmethod
    def run_cycle(self) -> CycleReport:
        """Execute one cycle. Must be deterministic and exception-safe."""
        ...

    def start(self) -> None:
        """Start the loop in a background thread."""
        if self.state == LoopState.RUNNING:
            logger.warning(f"[{self.name}] already running")
            return
        self._stop_event.clear()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self.state = LoopState.RUNNING
        self._thread = threading.Thread(
            target=self._run_forever,
            name=f"loop-{self.name}",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"[{self.name}] started (interval={self.interval_seconds}s)")

    def stop(self) -> None:
        """Signal the loop to stop after current cycle."""
        if self.state != LoopState.RUNNING:
            return
        self._stop_event.set()
        self.state = LoopState.STOPPED
        logger.info(f"[{self.name}] stop requested")

    def run_once(self) -> CycleReport:
        """Run a single cycle synchronously (for testing / CLI)."""
        return self._execute_cycle()

    def status(self) -> dict[str, Any]:
        """Return current loop status."""
        return {
            "name": self.name,
            "domain": self.domain,
            "state": self.state.value,
            "cycle_count": self._cycle_count,
            "interval_seconds": self.interval_seconds,
            "error_count": self._error_count,
            "started_at": self._started_at,
            "last_cycle": self._last_report.to_dict() if self._last_report else None,
        }

    def _run_forever(self) -> None:
        """Main loop thread — cycle + sleep until stop event."""
        while not self._stop_event.is_set():
            self._execute_cycle()
            self._stop_event.wait(timeout=self.interval_seconds)
        self.state = LoopState.STOPPED

    def _execute_cycle(self) -> CycleReport:
        """Run one cycle with error handling and heartbeat."""
        self._cycle_count += 1
        t0 = datetime.now(timezone.utc)
        try:
            report = self.run_cycle()
            self._error_count = 0
        except Exception as e:
            self._error_count += 1
            logger.error(f"[{self.name}] cycle {self._cycle_count} failed: {e}")
            report = CycleReport(
                loop_name=self.name,
                cycle_num=self._cycle_count,
                started_at=t0.isoformat(),
                finished_at=datetime.now(timezone.utc).isoformat(),
                errors=1,
                details=[{"error": str(e)}],
            )
            if self._error_count >= 5:
                self.state = LoopState.ERROR
                logger.error(f"[{self.name}] entering ERROR state after 5 consecutive failures")
        self._last_report = report
        self._write_heartbeat(report)
        self._publish_event(report)
        return report

    def _write_heartbeat(self, report: CycleReport) -> None:
        """Write heartbeat JSON for monitoring."""
        try:
            _HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
            path = _HEARTBEAT_DIR / f"{self.name}.json"
            payload = {
                "loop": self.name,
                "state": self.state.value,
                "cycle": self._cycle_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actions": report.actions_taken,
                "errors": report.errors,
            }
            path.write_text(json.dumps(payload, indent=2))
        except Exception as e:
            logger.debug(f"[{self.name}] heartbeat write failed: {e}")

    def _publish_event(self, report: CycleReport) -> None:
        """Publish cycle report to event bus."""
        try:
            from substrate.control_plane.events.event_bus import get_bus
            get_bus().publish(f"loop_cycle_{self.name}", report.to_dict())
        except Exception:
            pass


class LoopRegistry:
    """Central registry for all persistent loops."""

    def __init__(self) -> None:
        self._loops: dict[str, PersistentLoop] = {}

    def register(self, loop: PersistentLoop) -> None:
        self._loops[loop.name] = loop
        logger.info(f"[LoopRegistry] registered: {loop.name} ({loop.domain})")

    def get(self, name: str) -> PersistentLoop | None:
        return self._loops.get(name)

    def start(self, name: str) -> bool:
        loop = self._loops.get(name)
        if not loop:
            logger.warning(f"[LoopRegistry] unknown loop: {name}")
            return False
        loop.start()
        return True

    def stop(self, name: str) -> bool:
        loop = self._loops.get(name)
        if not loop:
            return False
        loop.stop()
        return True

    def start_all(self) -> list[str]:
        started = []
        for name, loop in self._loops.items():
            loop.start()
            started.append(name)
        return started

    def stop_all(self) -> list[str]:
        stopped = []
        for name, loop in self._loops.items():
            loop.stop()
            stopped.append(name)
        return stopped

    def status(self) -> dict[str, Any]:
        return {
            name: loop.status()
            for name, loop in self._loops.items()
        }

    def list_loops(self) -> list[str]:
        return list(self._loops.keys())

    def register_defaults(self) -> None:
        """Register the three canonical persistent loops."""
        from substrate.execution.loop.business_ops import BusinessOpsLoop
        from substrate.execution.loop.self_build import SelfBuildLoop
        from substrate.execution.loop.research import ResearchLoop

        self.register(BusinessOpsLoop())
        self.register(SelfBuildLoop())
        self.register(ResearchLoop())


_registry: LoopRegistry | None = None


def get_registry() -> LoopRegistry:
    """Process-wide singleton registry."""
    global _registry
    if _registry is None:
        _registry = LoopRegistry()
    return _registry
