"""Universal CPU gate — single choke point for all UMH execution paths.

Every component that might spike CPU must call `cpu_gate_check()` before
doing work. If the system is overloaded, the gate returns a block signal
and the caller must skip or defer.

This exists because Hostinger throttles the VPS for a week if CPU is abused.
The same principle applies to any node UMH operates on — never saturate
a shared resource.

Layers of defense (from innermost to outermost):
  1. This gate — checked by substrate code before any LLM call or heavy work
  2. Docker CPU caps — hard per-container limits (docker-compose.yml)
  3. cron-run wrapper — flock + nice + ionice + timeout + load check
  4. cc_sdk CPU gate — blocks CLI subprocess when load/core > 1.5
  5. systemd watchdog — SIGSTOP/SIGKILL at extreme loads (cpu-watchdog.sh)

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_LOAD_CEILING_PER_CORE: float = float(os.environ.get("UMH_CPU_GATE_CEILING", "1.8"))

_CRITICAL_CEILING_PER_CORE: float = float(os.environ.get("UMH_CPU_GATE_CRITICAL", "2.5"))

_COOLDOWN_SECONDS: float = 10.0

_last_block_time: float = 0.0
_consecutive_blocks: int = 0


@dataclass
class CpuGateResult:
    allowed: bool
    load_per_core: float
    cores: int
    reason: str = ""
    level: str = "ok"


def cpu_gate_check(caller: str = "") -> CpuGateResult:
    """Check if CPU load allows work to proceed.

    Call this before any LLM call, subprocess spawn, or heavy computation.
    Returns CpuGateResult with allowed=True if safe to proceed.

    Args:
        caller: identifier for the subsystem calling (for logging)
    """
    global _last_block_time, _consecutive_blocks

    try:
        load1, _, _ = os.getloadavg()
    except (AttributeError, OSError):
        return CpuGateResult(allowed=True, load_per_core=0.0, cores=1)

    cores = os.cpu_count() or 4
    load_per_core = load1 / cores

    if load_per_core <= _LOAD_CEILING_PER_CORE:
        if _consecutive_blocks > 0:
            logger.info(
                "[cpu_gate] %s: load recovered (%.1f/core), resuming after %d blocks",
                caller or "unknown",
                load_per_core,
                _consecutive_blocks,
            )
            _consecutive_blocks = 0
        return CpuGateResult(
            allowed=True,
            load_per_core=load_per_core,
            cores=cores,
        )

    now = time.monotonic()
    _last_block_time = now
    _consecutive_blocks += 1

    if load_per_core > _CRITICAL_CEILING_PER_CORE:
        level = "critical"
        logger.error(
            "[cpu_gate] CRITICAL — %s blocked: load=%.1f (%.1f/core > %.1f) blocks=%d",
            caller or "unknown",
            load1,
            load_per_core,
            _CRITICAL_CEILING_PER_CORE,
            _consecutive_blocks,
        )
    else:
        level = "warn"
        logger.warning(
            "[cpu_gate] %s blocked: load=%.1f (%.1f/core > %.1f) blocks=%d",
            caller or "unknown",
            load1,
            load_per_core,
            _LOAD_CEILING_PER_CORE,
            _consecutive_blocks,
        )

    return CpuGateResult(
        allowed=False,
        load_per_core=load_per_core,
        cores=cores,
        reason=f"load_per_core={load_per_core:.1f} > ceiling={_LOAD_CEILING_PER_CORE}",
        level=level,
    )


def cpu_gate_status() -> dict:
    """Return current gate status for observability/health endpoints."""
    try:
        load1, load5, load15 = os.getloadavg()
    except (AttributeError, OSError):
        load1 = load5 = load15 = 0.0

    cores = os.cpu_count() or 4
    load_per_core = load1 / cores

    return {
        "load1": round(load1, 2),
        "load5": round(load5, 2),
        "load15": round(load15, 2),
        "cores": cores,
        "load_per_core": round(load_per_core, 2),
        "ceiling": _LOAD_CEILING_PER_CORE,
        "critical_ceiling": _CRITICAL_CEILING_PER_CORE,
        "blocked": load_per_core > _LOAD_CEILING_PER_CORE,
        "consecutive_blocks": _consecutive_blocks,
        "status": (
            "critical"
            if load_per_core > _CRITICAL_CEILING_PER_CORE
            else "blocked"
            if load_per_core > _LOAD_CEILING_PER_CORE
            else "ok"
        ),
    }
