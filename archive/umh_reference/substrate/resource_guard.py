"""
Resource Guard v1 — pre-execution VPS resource check.

Purpose
-------
Prevents VPS overload by checking system resources before execution.
Returns a structured guard decision.  No daemon, no background thread —
evaluated only in the request flow.

Design rules
------------
- Pure functions + immutable snapshot = thread-safe.
- Uses only stdlib (no psutil).  Reads /proc/meminfo for memory stats.
- Fail-safe: if /proc is unavailable, returns allowed=True with partial data.
- Imports NOTHING from the hot path (gateway, cognitive_loop,
  model_router, agent_runtime, primitives).

Env vars
--------
  EOS_RESOURCE_GUARD_ENABLED       "1" | "0"  (default "0")
  EOS_MAX_MEM_PCT                  float       (default 75)
  EOS_MAX_SWAP_PCT                 float       (default 20)
  EOS_MAX_LOAD_PER_CPU             float       (default 1.5)
  EOS_HEAVYWORK_FORCE_LOCAL        "1" | "0"  (default "0")
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "current_resource_snapshot",
    "evaluate_resource_guard",
]

_GUARD_VERSION = "1.0"


# ── helpers ─────────────────────────────────────────────────────────────────


def _flag_truthy(env_name: str) -> bool:
    """Return True if the env var is set to a truthy value."""
    return (os.getenv(env_name, "") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _env_float(env_name: str, default: float) -> float:
    """Read a float from an env var, falling back to *default*."""
    raw = (os.getenv(env_name, "") or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _parse_meminfo() -> dict[str, float]:
    """Parse /proc/meminfo and return mem/swap used percentages.

    Returns a dict with ``mem_used_pct`` and ``swap_used_pct``.
    If /proc/meminfo is unavailable, returns an empty dict.
    """
    try:
        with open("/proc/meminfo", "r") as fh:
            lines = fh.readlines()
    except (OSError, IOError):
        return {}

    values: dict[str, int] = {}
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            key = parts[0].rstrip(":")
            try:
                values[key] = int(parts[1])
            except ValueError:
                continue

    result: dict[str, float] = {}

    mem_total = values.get("MemTotal", 0)
    mem_available = values.get("MemAvailable", 0)
    if mem_total > 0:
        result["mem_used_pct"] = round((1.0 - mem_available / mem_total) * 100.0, 2)

    swap_total = values.get("SwapTotal", 0)
    swap_free = values.get("SwapFree", 0)
    if swap_total > 0:
        result["swap_used_pct"] = round((1.0 - swap_free / swap_total) * 100.0, 2)
    else:
        result["swap_used_pct"] = 0.0

    return result


def _count_processes() -> int | None:
    """Count running processes via /proc/[0-9]* dirs.

    Returns None if /proc is unavailable.
    """
    try:
        return sum(1 for entry in os.listdir("/proc") if entry.isdigit())
    except (OSError, IOError):
        return None


# ── public API ──────────────────────────────────────────────────────────────


def current_resource_snapshot() -> dict[str, Any]:
    """Collect a cheap point-in-time resource snapshot.

    Uses only stdlib and /proc — no psutil.  Returns a partial dict
    if /proc is unavailable (fail-safe).
    """
    snap: dict[str, Any] = {}

    # Memory from /proc/meminfo
    mem = _parse_meminfo()
    if "mem_used_pct" in mem:
        snap["mem_used_pct"] = mem["mem_used_pct"]
    if "swap_used_pct" in mem:
        snap["swap_used_pct"] = mem["swap_used_pct"]

    # CPU load
    try:
        load1, _, _ = os.getloadavg()
        snap["load_avg_1m"] = round(load1, 2)
    except OSError:
        pass

    cpu_count = os.cpu_count() or 1
    snap["cpu_count"] = cpu_count

    if "load_avg_1m" in snap:
        snap["load_per_cpu"] = round(snap["load_avg_1m"] / cpu_count, 2)

    # Process count
    proc_count = _count_processes()
    if proc_count is not None:
        snap["process_count"] = proc_count

    snap["snapshot_at"] = datetime.now(timezone.utc).isoformat()
    return snap


def evaluate_resource_guard(
    mode: str,
    target: str,
    workload_class: str,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate whether execution should proceed given current resources.

    Parameters
    ----------
    mode:
        Operating mode — ``"builder"`` or ``"product"``.
    target:
        Current execution target — ``"vps"`` or ``"local"``.
    workload_class:
        ``"standard"`` or ``"heavyweight"``.
    snapshot:
        Pre-collected snapshot, or None to collect now.

    Returns
    -------
    dict with keys: allowed, recommended_target, pressure_level,
    guard_reason, snapshot, guard_version.
    """
    if snapshot is None:
        snapshot = current_resource_snapshot()

    # Guard disabled → always allow, pressure low
    if not _flag_truthy("EOS_RESOURCE_GUARD_ENABLED"):
        return _guard_result(
            allowed=True,
            recommended_target=target,
            pressure_level="low",
            guard_reason="guard_disabled",
            snapshot=snapshot,
        )

    # Read thresholds
    max_mem = _env_float("EOS_MAX_MEM_PCT", 75.0)
    max_swap = _env_float("EOS_MAX_SWAP_PCT", 20.0)
    max_load = _env_float("EOS_MAX_LOAD_PER_CPU", 1.5)

    # Current values (default to safe/low if unavailable)
    mem_pct = snapshot.get("mem_used_pct", 0.0)
    swap_pct = snapshot.get("swap_used_pct", 0.0)
    load_pc = snapshot.get("load_per_cpu", 0.0)

    # Determine pressure level
    high = mem_pct > max_mem or swap_pct > max_swap or load_pc > max_load
    moderate = not high and (
        mem_pct > max_mem * 0.8 or swap_pct > max_swap * 0.8 or load_pc > max_load * 0.8
    )

    if high:
        pressure = "high"
    elif moderate:
        pressure = "moderate"
    else:
        pressure = "low"

    # Decision logic
    allowed = True
    recommended = target
    reason = "within_thresholds"

    if pressure == "high" and workload_class == "heavyweight":
        allowed = False
        recommended = "local"
        reason = (
            f"high_pressure: mem={mem_pct}%>{max_mem}% "
            f"swap={swap_pct}%>{max_swap}% "
            f"load/cpu={load_pc}>{max_load} — heavyweight blocked"
        )
    elif pressure == "high" and workload_class == "standard":
        recommended = "local"
        reason = (
            f"high_pressure: mem={mem_pct}% swap={swap_pct}% "
            f"load/cpu={load_pc} — standard allowed, local recommended"
        )
    elif (
        pressure == "moderate"
        and workload_class == "heavyweight"
        and _flag_truthy("EOS_HEAVYWORK_FORCE_LOCAL")
    ):
        recommended = "local"
        reason = "moderate_pressure + heavyweight + HEAVYWORK_FORCE_LOCAL"

    # Product mode override: never block user-facing requests
    if mode == "product" and not allowed:
        allowed = True
        reason += " [product_mode_override: allowed]"

    return _guard_result(
        allowed=allowed,
        recommended_target=recommended,
        pressure_level=pressure,
        guard_reason=reason,
        snapshot=snapshot,
    )


def _guard_result(
    *,
    allowed: bool,
    recommended_target: str,
    pressure_level: str,
    guard_reason: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Build the canonical guard result dict."""
    return {
        "allowed": allowed,
        "recommended_target": recommended_target,
        "pressure_level": pressure_level,
        "guard_reason": guard_reason,
        "snapshot": snapshot,
        "guard_version": _GUARD_VERSION,
    }
