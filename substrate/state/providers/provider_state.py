"""
Global Provider State + Backpressure + Execution Budget.

Single module that prevents system-wide failure cascades under provider
outages or resource exhaustion.  Process-wide singleton — shared across
all threads (ambient loop, gateway, SessionWatcher, etc.).

Integration points:
    model_router.py  — records per-provider success/failure
    orchestrator.py  — checks backpressure gate before each cycle
    discord_bot.py   — checks spawn guard before subagent creation

Usage:
    from substrate.state.providers.provider_state import get_system_state

    state = get_system_state()
    if not state.allow_execution():
        # back off — system is degraded
        ...
"""

from __future__ import annotations

import os
import time
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

_LOG_PREFIX = "[ProviderState]"


# ─── Status enum ──────────────────────────────────────────────────────────


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class SystemStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


# ─── Per-provider state ──────────────────────────────────────────────────


@dataclass
class ProviderState:
    provider_name: str
    status: ProviderStatus = ProviderStatus.HEALTHY
    consecutive_failures: int = 0
    last_success_ts: float = 0.0
    cooldown_until: float = 0.0

    _DEGRADED_THRESHOLD: int = 3
    _DOWN_THRESHOLD: int = 5
    _BASE_COOLDOWN: float = 30.0
    _MAX_COOLDOWN: float = 300.0

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.last_success_ts = time.time()
        self.cooldown_until = 0.0
        self.status = ProviderStatus.HEALTHY

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        now = time.time()

        if self.consecutive_failures >= self._DOWN_THRESHOLD:
            self.status = ProviderStatus.DOWN
            cooldown = min(
                self._BASE_COOLDOWN * (2 ** (self.consecutive_failures - self._DOWN_THRESHOLD)),
                self._MAX_COOLDOWN,
            )
            self.cooldown_until = now + cooldown
        elif self.consecutive_failures >= self._DEGRADED_THRESHOLD:
            self.status = ProviderStatus.DEGRADED

    def is_available(self) -> bool:
        if self.status == ProviderStatus.DOWN:
            return time.time() >= self.cooldown_until
        return True


# ─── Execution budget ────────────────────────────────────────────────────


@dataclass
class ExecutionBudget:
    max_cycles_per_minute: int = 30
    max_concurrent_agents: int = 4
    max_retries_per_goal: int = 3

    _cycle_timestamps: list[float] = field(default_factory=list)
    _active_agents: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def can_start_cycle(self) -> bool:
        now = time.time()
        cutoff = now - 60.0
        with self._lock:
            self._cycle_timestamps = [t for t in self._cycle_timestamps if t > cutoff]
            return len(self._cycle_timestamps) < self.max_cycles_per_minute

    def record_cycle(self) -> None:
        with self._lock:
            self._cycle_timestamps.append(time.time())

    def can_spawn_agent(self) -> bool:
        with self._lock:
            return self._active_agents < self.max_concurrent_agents

    def agent_started(self) -> None:
        with self._lock:
            self._active_agents += 1

    def agent_finished(self) -> None:
        with self._lock:
            self._active_agents = max(0, self._active_agents - 1)

    @property
    def active_agents(self) -> int:
        with self._lock:
            return self._active_agents


# ─── System-level state ──────────────────────────────────────────────────


class SystemProviderState:
    """Process-wide singleton tracking all provider health + resource pressure."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderState] = {}
        self._lock = threading.RLock()
        self.budget = ExecutionBudget()
        self._backoff_until: float = 0.0
        self._consecutive_all_down: int = 0

    # ── Provider tracking ────────────────────────────────────────────────

    def _get_provider(self, name: str) -> ProviderState:
        if name not in self._providers:
            self._providers[name] = ProviderState(provider_name=name)
        return self._providers[name]

    def record_provider_success(self, provider: str) -> None:
        with self._lock:
            self._get_provider(provider).record_success()
            self._consecutive_all_down = 0
            self._backoff_until = 0.0

    def record_provider_failure(self, provider: str) -> None:
        with self._lock:
            self._get_provider(provider).record_failure()

    def record_all_providers_failed(self) -> None:
        with self._lock:
            self._consecutive_all_down += 1
            backoff = min(30.0 * (2 ** (self._consecutive_all_down - 1)), 300.0)
            self._backoff_until = time.time() + backoff
            logger.warning(
                "%s ALL_DOWN #%d — backoff %.0fs",
                _LOG_PREFIX,
                self._consecutive_all_down,
                backoff,
            )

    # ── Global status ────────────────────────────────────────────────────

    @property
    def global_status(self) -> SystemStatus:
        with self._lock:
            if not self._providers:
                return SystemStatus.HEALTHY

            statuses = [p.status for p in self._providers.values()]
            if all(s == ProviderStatus.DOWN for s in statuses):
                return SystemStatus.DOWN
            if any(s == ProviderStatus.DOWN for s in statuses):
                return SystemStatus.DEGRADED
            if any(s == ProviderStatus.DEGRADED for s in statuses):
                return SystemStatus.DEGRADED
            return SystemStatus.HEALTHY

    # ── Backpressure gate ────────────────────────────────────────────────

    def allow_execution(self) -> bool:
        """Check if the system should allow a new execution cycle."""
        now = time.time()

        # Global backoff from all-providers-failed
        if now < self._backoff_until:
            remaining = int(self._backoff_until - now)
            logger.debug(
                "%s execution blocked — global backoff %ds remaining",
                _LOG_PREFIX,
                remaining,
            )
            return False

        # Execution budget
        if not self.budget.can_start_cycle():
            logger.debug("%s execution blocked — cycle budget exhausted", _LOG_PREFIX)
            return False

        # Resource pressure check
        pressure = self._check_resource_pressure()
        if pressure == "critical":
            logger.warning("%s execution blocked — critical resource pressure", _LOG_PREFIX)
            return False

        return True

    def allow_agent_spawn(self) -> bool:
        """Check if a new agent/subagent can be spawned."""
        if not self.budget.can_spawn_agent():
            logger.debug(
                "%s spawn blocked — %d/%d agents active",
                _LOG_PREFIX,
                self.budget.active_agents,
                self.budget.max_concurrent_agents,
            )
            return False

        pressure = self._check_resource_pressure()
        if pressure in ("critical", "high"):
            logger.warning(
                "%s spawn blocked — %s resource pressure",
                _LOG_PREFIX,
                pressure,
            )
            return False

        return True

    # ── Resource pressure ────────────────────────────────────────────────

    def _check_resource_pressure(self) -> str:
        """Return 'low', 'moderate', 'high', or 'critical'."""
        from substrate.state.work.work_state import _measure_pressure

        return _measure_pressure().value

    # ── Diagnostics ──────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Snapshot for logging/debugging."""
        with self._lock:
            providers = {}
            for name, ps in self._providers.items():
                providers[name] = {
                    "status": ps.status.value,
                    "consecutive_failures": ps.consecutive_failures,
                    "available": ps.is_available(),
                }
            return {
                "global_status": self.global_status.value,
                "providers": providers,
                "active_agents": self.budget.active_agents,
                "backoff_remaining": max(0, int(self._backoff_until - time.time())),
                "resource_pressure": self._check_resource_pressure(),
            }


# ─── Singleton ───────────────────────────────────────────────────────────

_instance: SystemProviderState | None = None
_instance_lock = threading.Lock()


def get_system_state() -> SystemProviderState:
    """Get the process-wide system provider state singleton."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = SystemProviderState()
    return _instance
