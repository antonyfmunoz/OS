"""Autonomous tick engine — continuous organism metabolism heartbeat.

This is NOT a replacement for PersistentLoop or orchestration_loop.py.
Those remain the infrastructure for stage registration and daemon
threading. This engine adds:

  - Governed pause/kill (RecursionGovernor integration)
  - Adaptive cadence (speeds up under load, slows down when idle)
  - Per-stage failure isolation
  - Tick metrics for observability
  - Event emission through the EventSpine

The tick engine executes registered stage functions each cycle.
Stages are the same concept as orchestration_loop stages — they
wrap existing subsystem operations (refresh runtimes, check health,
advance objectives, etc.).

Usage:
    spine = EventSpine()
    tick = AutonomousTick(spine=spine)
    tick.register_stage("refresh_runtimes", graph.refresh_availability)
    tick.register_stage("homeostasis", lambda: homeostasis.check())
    tick.run()  # blocks until killed

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine

logger = logging.getLogger(__name__)

StageFunction = Callable[[], Any]


@dataclass
class TickConfig:
    base_interval_seconds: float = 30.0
    min_interval_seconds: float = 5.0
    max_interval_seconds: float = 300.0
    adaptive_cadence: bool = True
    speedup_factor: float = 0.85
    slowdown_factor: float = 1.15
    idle_threshold_cycles: int = 3


@dataclass
class TickMetrics:
    total_cycles: int = 0
    total_stages_executed: int = 0
    total_stages_failed: int = 0
    total_elapsed_ms: float = 0.0
    consecutive_idle: int = 0

    @property
    def avg_cycle_ms(self) -> float:
        if self.total_cycles == 0:
            return 0.0
        return self.total_elapsed_ms / self.total_cycles


@dataclass
class TickStage:
    name: str
    function: StageFunction


@dataclass
class CycleReport:
    cycle_number: int
    stages_executed: int = 0
    stages_failed: int = 0
    elapsed_ms: float = 0.0
    had_work: bool = False
    skipped_reason: str | None = None
    stage_details: list[dict[str, Any]] = field(default_factory=list)


class AutonomousTick:
    """Continuous organism metabolism loop.

    Executes registered stages each cycle, emits events to the spine,
    adapts cadence based on workload, and respects governance kill/pause.
    """

    def __init__(
        self,
        spine: EventSpine,
        config: TickConfig | None = None,
    ) -> None:
        self._spine = spine
        self._config = config or TickConfig()
        self._stages: list[TickStage] = []
        self._metrics = TickMetrics()
        self._current_interval = self._config.base_interval_seconds
        self._killed = False
        self._paused = False
        self._stop_event = threading.Event()
        self._cycle_count = 0

    @property
    def stages(self) -> dict[str, StageFunction]:
        return {s.name: s.function for s in self._stages}

    @property
    def metrics(self) -> TickMetrics:
        return self._metrics

    @property
    def current_interval(self) -> float:
        return self._current_interval

    @property
    def is_killed(self) -> bool:
        return self._killed

    @property
    def is_paused(self) -> bool:
        return self._paused

    def register_stage(self, name: str, function: StageFunction) -> None:
        self._stages.append(TickStage(name=name, function=function))

    def kill(self) -> None:
        self._killed = True
        self._stop_event.set()
        self._spine.emit(
            EventDomain.GOVERNANCE, "tick_killed", "autonomous_tick",
            {"cycle": self._cycle_count},
            priority=EventPriority.CRITICAL,
        )

    def pause(self) -> None:
        self._paused = True
        self._spine.emit(
            EventDomain.GOVERNANCE, "tick_paused", "autonomous_tick",
            {"cycle": self._cycle_count},
        )

    def resume(self) -> None:
        self._paused = False
        self._spine.emit(
            EventDomain.GOVERNANCE, "tick_resumed", "autonomous_tick",
            {"cycle": self._cycle_count},
        )

    def execute_cycle(self) -> CycleReport:
        self._cycle_count += 1
        report = CycleReport(cycle_number=self._cycle_count)

        if self._killed:
            report.skipped_reason = "killed"
            return report

        if self._paused:
            report.skipped_reason = "paused"
            return report

        start = time.monotonic_ns()
        had_work = False

        for stage in self._stages:
            try:
                result = stage.function()
                report.stages_executed += 1
                is_work = result is not None and result is not False
                if is_work:
                    had_work = True
                report.stage_details.append({
                    "stage": stage.name, "success": True,
                    "had_work": is_work,
                })
            except Exception as exc:
                report.stages_executed += 1
                report.stages_failed += 1
                logger.warning("tick stage '%s' failed: %s", stage.name, exc)
                report.stage_details.append({
                    "stage": stage.name, "success": False,
                    "error": str(exc)[:200],
                })

        elapsed_ms = (time.monotonic_ns() - start) / 1_000_000
        report.elapsed_ms = elapsed_ms
        report.had_work = had_work

        self._metrics.total_cycles += 1
        self._metrics.total_stages_executed += report.stages_executed
        self._metrics.total_stages_failed += report.stages_failed
        self._metrics.total_elapsed_ms += elapsed_ms

        if had_work:
            self._metrics.consecutive_idle = 0
        else:
            self._metrics.consecutive_idle += 1

        if self._config.adaptive_cadence:
            self._adapt_cadence(had_work)

        self._spine.emit(
            EventDomain.EXECUTION, "tick_completed", "autonomous_tick",
            {
                "cycle": self._cycle_count,
                "stages_executed": report.stages_executed,
                "stages_failed": report.stages_failed,
                "elapsed_ms": round(elapsed_ms, 2),
                "had_work": had_work,
                "interval": round(self._current_interval, 2),
            },
        )

        return report

    def _adapt_cadence(self, had_work: bool) -> None:
        if had_work:
            self._current_interval = max(
                self._config.min_interval_seconds,
                self._current_interval * self._config.speedup_factor,
            )
        elif self._metrics.consecutive_idle >= self._config.idle_threshold_cycles:
            self._current_interval = min(
                self._config.max_interval_seconds,
                self._current_interval * self._config.slowdown_factor,
            )

    def run(self, max_cycles: int | None = None) -> None:
        """Run the tick loop. Blocks until killed or max_cycles reached."""
        cycles = 0
        while not self._killed:
            self.execute_cycle()
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            if not self._killed:
                self._stop_event.wait(timeout=self._current_interval)
                self._stop_event.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_killed": self._killed,
            "is_paused": self._paused,
            "current_interval": round(self._current_interval, 2),
            "cycle_count": self._cycle_count,
            "stages": [s.name for s in self._stages],
            "config": {
                "base_interval": self._config.base_interval_seconds,
                "min_interval": self._config.min_interval_seconds,
                "max_interval": self._config.max_interval_seconds,
                "adaptive": self._config.adaptive_cadence,
            },
            "metrics": {
                "total_cycles": self._metrics.total_cycles,
                "total_stages_executed": self._metrics.total_stages_executed,
                "total_stages_failed": self._metrics.total_stages_failed,
                "avg_cycle_ms": round(self._metrics.avg_cycle_ms, 2),
                "consecutive_idle": self._metrics.consecutive_idle,
            },
        }
