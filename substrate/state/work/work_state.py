"""
Work State Detection + Idle Gate + Adaptive Throttling.

Determines whether the system has meaningful work to do, and controls
sleep duration based on load and provider health.  Consumers call
``get_idle_delay()`` to learn how long to sleep before the next cycle.

Integration:
    orchestrator.py  — ambient refresh loop checks before each cycle
    discord_bot.py   — same loop via orchestrator import
    cc_sdk.py        — checks before LLM dispatch

Usage:
    from substrate.state.work.work_state import detect_work_state, get_idle_delay

    ws = detect_work_state()
    if ws.is_idle:
        time.sleep(ws.idle_delay)
        continue
"""

from __future__ import annotations

import os
import time
import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)

_LOG_PREFIX = "[WorkState]"


class Pressure(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class WorkState:
    has_pending_goals: bool
    has_active_tasks: bool
    has_recent_signal: bool
    pressure: Pressure
    idle_delay: float

    @property
    def is_idle(self) -> bool:
        return (
            not self.has_pending_goals and not self.has_active_tasks and not self.has_recent_signal
        )


# ─── Signal registry ────────────────────────────────────────────────────

_last_signal_ts: float = 0.0
_signal_lock = threading.Lock()

# Signals older than this are stale — system returns to idle
_SIGNAL_TTL: float = 300.0  # 5 minutes


def record_signal() -> None:
    """Call when external input arrives (user message, webhook, event)."""
    global _last_signal_ts
    with _signal_lock:
        _last_signal_ts = time.time()


def has_recent_signal() -> bool:
    with _signal_lock:
        return (time.time() - _last_signal_ts) < _SIGNAL_TTL


# ─── Pressure measurement ───────────────────────────────────────────────


def _measure_pressure() -> Pressure:
    """Read OS load and swap to determine resource pressure."""
    try:
        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        load_per_cpu = load1 / cpu_count

        swap_pct = _get_swap_pct()

        if load_per_cpu > 10.0 or swap_pct > 80.0:
            return Pressure.CRITICAL
        if load_per_cpu > 5.0 or swap_pct > 50.0:
            return Pressure.HIGH
        if load_per_cpu > 2.0 or swap_pct > 20.0:
            return Pressure.MODERATE
        return Pressure.LOW
    except Exception:
        return Pressure.LOW


def _get_swap_pct() -> float:
    try:
        with open("/proc/meminfo", "r") as fh:
            vals: dict[str, int] = {}
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0].rstrip(":") in (
                    "SwapTotal",
                    "SwapFree",
                ):
                    vals[parts[0].rstrip(":")] = int(parts[1])
            total = vals.get("SwapTotal", 0)
            free = vals.get("SwapFree", 0)
            if total == 0:
                return 0.0
            return round((1.0 - free / total) * 100.0, 1)
    except Exception:
        return 0.0


# ─── Idle delay calculation ─────────────────────────────────────────────

# Tracks consecutive idle cycles for exponential backoff
_consecutive_idle: int = 0
_idle_lock = threading.Lock()

_BASE_IDLE_DELAY: float = 5.0  # seconds — idle with no pressure
_MAX_IDLE_DELAY: float = 1800.0  # cap at 30 minutes
_NORMAL_INTERVAL: float = 1800.0  # normal work interval (30 min)


def _compute_idle_delay(pressure: Pressure, is_idle: bool) -> float:
    """Compute how long to sleep before the next cycle.

    When idle: exponential backoff starting at 5s, capped at 30 min.
    When working: fixed interval scaled by pressure.
    """
    global _consecutive_idle

    with _idle_lock:
        if is_idle:
            _consecutive_idle += 1
            # Exponential backoff: 5, 10, 20, 40, 80, 160, 320, 640, 1280, 1800
            delay = min(_BASE_IDLE_DELAY * (2 ** (_consecutive_idle - 1)), _MAX_IDLE_DELAY)
        else:
            _consecutive_idle = 0
            delay = _NORMAL_INTERVAL

    # Scale by pressure — even working cycles slow down under load
    multipliers = {
        Pressure.LOW: 1.0,
        Pressure.MODERATE: 1.0,
        Pressure.HIGH: 2.0,
        Pressure.CRITICAL: 4.0,
    }
    delay *= multipliers.get(pressure, 1.0)

    return min(delay, _MAX_IDLE_DELAY)


def reset_idle_counter() -> None:
    """Reset when meaningful work arrives (signal, goal, task)."""
    global _consecutive_idle
    with _idle_lock:
        _consecutive_idle = 0


# ─── Goal / task detection ──────────────────────────────────────────────

# Pluggable detectors — callers can register real checks
_goal_detector: Callable[[], bool] | None = None
_task_detector: Callable[[], bool] | None = None


def register_goal_detector(fn: Callable[[], bool]) -> None:
    global _goal_detector
    _goal_detector = fn


def register_task_detector(fn: Callable[[], bool]) -> None:
    global _task_detector
    _task_detector = fn


# ─── Public API ─────────────────────────────────────────────────────────


def detect_work_state() -> WorkState:
    """Snapshot current work state and compute idle delay."""
    has_goals = _goal_detector() if _goal_detector else False
    has_tasks = _task_detector() if _task_detector else False
    has_signal = has_recent_signal()
    pressure = _measure_pressure()

    is_idle = not has_goals and not has_tasks and not has_signal

    delay = _compute_idle_delay(pressure, is_idle)

    if is_idle and delay > 60:
        logger.debug(
            "%s idle — next check in %.0fs (pressure=%s)",
            _LOG_PREFIX,
            delay,
            pressure.value,
        )

    return WorkState(
        has_pending_goals=has_goals,
        has_active_tasks=has_tasks,
        has_recent_signal=has_signal,
        pressure=pressure,
        idle_delay=delay,
    )


def get_idle_delay() -> float:
    """Convenience: returns just the delay in seconds."""
    return detect_work_state().idle_delay
