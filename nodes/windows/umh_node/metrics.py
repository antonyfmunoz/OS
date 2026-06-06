"""System metrics collector — CPU, memory, disk, battery, network, GPU."""

from __future__ import annotations

import logging
import platform
import subprocess
from typing import Any

import psutil

logger = logging.getLogger(__name__)


def _collect_gpu() -> dict[str, Any] | None:
    """Query NVIDIA GPU via nvidia-smi. Returns None if no GPU or command fails."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            return None
        mem_used = float(parts[1])
        mem_total = float(parts[2])
        return {
            "utilization": float(parts[0]),
            "memory_used_mb": mem_used,
            "memory_total_mb": mem_total,
            "memory_percent": round(mem_used / mem_total * 100, 1) if mem_total > 0 else 0,
            "temperature": float(parts[3]),
            "name": parts[4] if len(parts) > 4 else "NVIDIA GPU",
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return None
    except Exception as exc:
        logger.debug("GPU metrics collection failed: %s", exc)
        return None


def collect_metrics() -> dict[str, Any]:
    """Collect current system metrics. Safe on all platforms."""
    metrics: dict[str, Any] = {}

    try:
        metrics["cpu"] = psutil.cpu_percent(interval=0.1)
    except Exception:
        pass

    try:
        mem = psutil.virtual_memory()
        metrics["memory"] = mem.percent
    except Exception:
        pass

    try:
        disk = psutil.disk_usage("/" if platform.system() != "Windows" else "C:\\")
        metrics["disk"] = disk.percent
    except Exception:
        pass

    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            metrics["battery"] = battery.percent
    except Exception:
        pass

    try:
        net = psutil.net_io_counters()
        if net:
            metrics["network_io"] = {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
            }
    except Exception:
        pass

    gpu = _collect_gpu()
    if gpu is not None:
        metrics["gpu"] = gpu

    return metrics
