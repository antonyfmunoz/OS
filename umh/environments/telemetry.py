"""Node telemetry — real system metrics collection.

Collects CPU, memory, and load metrics from the local system.
Uses psutil if available, falls back to /proc parsing on Linux,
and returns safe defaults if neither works.

No imports from umh/cells, umh/adapters, or umh/execution.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now

try:
    import psutil

    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


@dataclass(frozen=True)
class NodeTelemetry:
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_mb: int = 0
    load_avg_1m: float = 0.0
    collected_at: str = ""
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.collected_at:
            object.__setattr__(self, "collected_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_mb": self.memory_available_mb,
            "load_avg_1m": self.load_avg_1m,
            "collected_at": self.collected_at,
            "source": self.source,
        }


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


class TelemetryCollector:
    """Collects real system metrics with graceful fallback."""

    def collect_local(self) -> NodeTelemetry:
        if _HAS_PSUTIL:
            return self._collect_psutil()
        return self._collect_proc()

    def _collect_psutil(self) -> NodeTelemetry:
        import psutil

        mem = psutil.virtual_memory()
        load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
        return NodeTelemetry(
            cpu_percent=_clamp(psutil.cpu_percent(interval=0.1), 0.0, 100.0),
            memory_percent=_clamp(mem.percent, 0.0, 100.0),
            memory_available_mb=int(mem.available / (1024 * 1024)),
            load_avg_1m=load[0],
            source="psutil",
        )

    def _collect_proc(self) -> NodeTelemetry:
        cpu = self._cpu_from_proc()
        mem_pct, mem_avail = self._mem_from_proc()
        load = self._load_from_proc()
        return NodeTelemetry(
            cpu_percent=cpu,
            memory_percent=mem_pct,
            memory_available_mb=mem_avail,
            load_avg_1m=load,
            source="proc",
        )

    def _cpu_from_proc(self) -> float:
        try:
            with open("/proc/stat") as f:
                parts = f.readline().split()
            if parts[0] != "cpu":
                return 0.0
            vals = [int(v) for v in parts[1:8]]
            idle = vals[3]
            total = sum(vals)
            time.sleep(0.05)
            with open("/proc/stat") as f:
                parts2 = f.readline().split()
            vals2 = [int(v) for v in parts2[1:8]]
            idle2 = vals2[3]
            total2 = sum(vals2)
            d_total = total2 - total
            d_idle = idle2 - idle
            if d_total == 0:
                return 0.0
            return _clamp(100.0 * (1.0 - d_idle / d_total), 0.0, 100.0)
        except Exception:
            return 0.0

    def _mem_from_proc(self) -> tuple[float, int]:
        try:
            info: dict[str, int] = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        info[key] = int(parts[1])
            total_kb = info.get("MemTotal", 1)
            avail_kb = info.get("MemAvailable", info.get("MemFree", 0))
            pct = _clamp(100.0 * (1.0 - avail_kb / total_kb), 0.0, 100.0)
            return pct, avail_kb // 1024
        except Exception:
            return 0.0, 0

    def _load_from_proc(self) -> float:
        try:
            if hasattr(os, "getloadavg"):
                return os.getloadavg()[0]
            with open("/proc/loadavg") as f:
                return float(f.read().split()[0])
        except Exception:
            return 0.0


def collect_local_telemetry() -> NodeTelemetry:
    return TelemetryCollector().collect_local()
