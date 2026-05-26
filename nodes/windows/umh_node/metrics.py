"""System metrics collector — CPU, memory, disk, battery, network."""

from __future__ import annotations

import logging
import platform
from typing import Any

import psutil

logger = logging.getLogger(__name__)


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

    return metrics
