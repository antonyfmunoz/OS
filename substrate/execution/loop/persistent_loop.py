"""PersistentLoop — config-driven runtime loops for UMH.

Loops are capabilities, not hardcoded classes. Each loop is defined by
a LoopDefinition (name, domain, interval, pipeline stages) and instantiated
at runtime from config or code. You can spin up N loops in parallel,
each with its own composed pipeline.

Built-in stage functions (signal_drain, goal_execution, research_cycle, etc.)
are registered in STAGE_REGISTRY and referenced by name in definitions.
Custom stages are any callable(loop, CycleReport) -> None.

Usage:
    from substrate.execution.loop.persistent_loop import get_registry, LoopDefinition

    # From config
    registry = get_registry()
    registry.load_definitions("data/config/loops.jsonl")
    registry.start("business_ops")

    # Or programmatically
    defn = LoopDefinition(
        name="my_loop",
        domain="custom",
        interval_seconds=60,
        stages=["signal_drain", "actionable_scan"],
    )
    registry.register_definition(defn)
    registry.start("my_loop")
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

def _root() -> Path:
    return Path(os.getenv("UMH_ROOT", "/opt/OS"))

def _heartbeat_dir() -> Path:
    return _root() / "data" / "runtime" / "loop_heartbeats"

def _definitions_path() -> Path:
    return _root() / "data" / "config" / "loop_definitions.jsonl"


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


@dataclass
class LoopDefinition:
    """Declarative loop configuration — what to run and how often."""

    name: str
    domain: str
    interval_seconds: int = 300
    stages: list[str] = field(default_factory=list)
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "interval_seconds": self.interval_seconds,
            "stages": self.stages,
            "enabled": self.enabled,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoopDefinition:
        return cls(
            name=data["name"],
            domain=data.get("domain", "general"),
            interval_seconds=data.get("interval_seconds", 300),
            stages=data.get("stages", []),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
        )


# ─── Stage type ──────────────────────────────────────────────────────────────

StageFunc = Callable[["PersistentLoop", "CycleReport"], None]

STAGE_REGISTRY: dict[str, StageFunc] = {}


def register_stage(name: str, func: StageFunc) -> None:
    """Register a named stage function for use in loop definitions."""
    STAGE_REGISTRY[name] = func


def stage(name: str) -> Callable[[StageFunc], StageFunc]:
    """Decorator to register a stage function."""
    def decorator(func: StageFunc) -> StageFunc:
        STAGE_REGISTRY[name] = func
        return func
    return decorator


# ─── PersistentLoop ──────────────────────────────────────────────────────────


class PersistentLoop:
    """Config-driven loop that executes a pipeline of named stages."""

    def __init__(self, definition: LoopDefinition) -> None:
        self.definition = definition
        self.name = definition.name
        self.domain = definition.domain
        self.interval_seconds = definition.interval_seconds
        self.state = LoopState.STOPPED
        self._cycle_count = 0
        self._last_report: CycleReport | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._error_count = 0
        self._started_at: str | None = None

    def start(self) -> None:
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
        if self.state != LoopState.RUNNING:
            return
        self._stop_event.set()
        self.state = LoopState.STOPPED
        logger.info(f"[{self.name}] stop requested")

    def run_once(self) -> CycleReport:
        return self._execute_cycle()

    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "state": self.state.value,
            "cycle_count": self._cycle_count,
            "interval_seconds": self.interval_seconds,
            "error_count": self._error_count,
            "started_at": self._started_at,
            "stages": self.definition.stages,
            "description": self.definition.description,
            "last_cycle": self._last_report.to_dict() if self._last_report else None,
        }

    def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            self._execute_cycle()
            self._stop_event.wait(timeout=self.interval_seconds)
        self.state = LoopState.STOPPED

    def _execute_cycle(self) -> CycleReport:
        self._cycle_count += 1
        t0 = datetime.now(timezone.utc)
        report = CycleReport(
            loop_name=self.name,
            cycle_num=self._cycle_count,
            started_at=t0.isoformat(),
            finished_at="",
        )
        try:
            for stage_name in self.definition.stages:
                func = STAGE_REGISTRY.get(stage_name)
                if func is None:
                    report.errors += 1
                    report.details.append({
                        "stage": stage_name,
                        "error": f"unknown stage: {stage_name}",
                    })
                    continue
                try:
                    func(self, report)
                except Exception as e:
                    report.errors += 1
                    report.details.append({
                        "stage": stage_name,
                        "error": str(e),
                    })
                    logger.warning(f"[{self.name}] stage '{stage_name}' failed: {e}")
            self._error_count = 0
        except Exception as e:
            self._error_count += 1
            report.errors += 1
            report.details.append({"error": f"cycle failed: {e}"})
            logger.error(f"[{self.name}] cycle {self._cycle_count} failed: {e}")
            if self._error_count >= 5:
                self.state = LoopState.ERROR
                logger.error(f"[{self.name}] entering ERROR state after 5 consecutive failures")

        report.finished_at = datetime.now(timezone.utc).isoformat()
        self._last_report = report
        self._write_heartbeat(report)
        self._publish_event(report)
        return report

    def _write_heartbeat(self, report: CycleReport) -> None:
        try:
            hb_dir = _heartbeat_dir()
            hb_dir.mkdir(parents=True, exist_ok=True)
            path = hb_dir / f"{self.name}.json"
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
        try:
            from substrate.control_plane.events.event_bus import get_bus
            get_bus().publish(f"loop_cycle_{self.name}", report.to_dict())
        except Exception:
            pass


# ─── Registry ────────────────────────────────────────────────────────────────


class LoopRegistry:
    """Central registry — loads definitions, instantiates and manages loops."""

    def __init__(self) -> None:
        self._loops: dict[str, PersistentLoop] = {}
        self._definitions: dict[str, LoopDefinition] = {}

    def register_definition(self, defn: LoopDefinition) -> None:
        """Register a loop definition. Creates the loop instance."""
        self._definitions[defn.name] = defn
        self._loops[defn.name] = PersistentLoop(defn)
        logger.info(f"[LoopRegistry] registered: {defn.name} ({defn.domain}, stages={defn.stages})")

    def register(self, loop: PersistentLoop) -> None:
        """Register a pre-built loop instance (backward compat)."""
        self._loops[loop.name] = loop
        self._definitions[loop.name] = loop.definition

    def get(self, name: str) -> PersistentLoop | None:
        return self._loops.get(name)

    def get_definition(self, name: str) -> LoopDefinition | None:
        return self._definitions.get(name)

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
            if loop.definition.enabled:
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
        return {name: loop.status() for name, loop in self._loops.items()}

    def list_loops(self) -> list[str]:
        return list(self._loops.keys())

    def load_definitions(self, path: str | Path | None = None) -> int:
        """Load loop definitions from a JSONL file. Returns count loaded."""
        path = Path(path) if path else _definitions_path()
        if not path.exists():
            logger.debug(f"[LoopRegistry] no definitions file at {path}")
            return 0
        count = 0
        for line in path.read_text().strip().split("\n"):
            if not line.strip():
                continue
            try:
                defn = LoopDefinition.from_dict(json.loads(line))
                self.register_definition(defn)
                count += 1
            except Exception as e:
                logger.warning(f"[LoopRegistry] bad definition: {e}")
        return count

    def save_definitions(self, path: str | Path | None = None) -> int:
        """Persist current definitions to JSONL."""
        path = Path(path) if path else _definitions_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with open(path, "w") as f:
            for defn in self._definitions.values():
                f.write(json.dumps(defn.to_dict()) + "\n")
                count += 1
        return count

    def remove(self, name: str) -> bool:
        """Stop and remove a loop."""
        loop = self._loops.pop(name, None)
        self._definitions.pop(name, None)
        if loop:
            loop.stop()
            return True
        return False


_registry: LoopRegistry | None = None


def get_registry() -> LoopRegistry:
    """Process-wide singleton registry."""
    global _registry
    if _registry is None:
        _registry = LoopRegistry()
    return _registry
