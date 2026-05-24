"""System metrics perception — CPU, memory, disk monitoring with alerting.

Wraps daemon/umh_node/metrics.py and adds threshold-based alerting that
produces PerceptionRecords when resources exceed configured limits.
Runs in a background thread at configurable intervals.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


@dataclass
class MetricsThresholds:
    """Alerting thresholds for system metrics."""

    cpu_warning: float = 90.0
    cpu_critical: float = 98.0
    memory_warning: float = 85.0
    memory_critical: float = 95.0
    disk_warning: float = 90.0
    disk_critical: float = 98.0


@dataclass
class MetricsAlert:
    """A single metrics threshold breach."""

    metric: str
    value: float
    threshold: float
    severity: str  # "warning" or "critical"
    timestamp: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }


@dataclass
class MetricsSnapshot:
    """Latest system metrics reading."""

    cpu: float = 0.0
    memory: float = 0.0
    disk: float = 0.0
    battery: float | None = None
    network_sent: int = 0
    network_recv: int = 0
    collected_at: float = 0.0
    alerts: list[MetricsAlert] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "cpu": self.cpu,
            "memory": self.memory,
            "disk": self.disk,
            "collected_at": self.collected_at,
        }
        if self.battery is not None:
            d["battery"] = self.battery
        if self.alerts:
            d["alerts"] = [a.as_dict() for a in self.alerts]
        return d


def _collect_raw() -> dict[str, Any]:
    """Collect raw system metrics. Falls back gracefully."""
    try:
        from daemon.umh_node.metrics import collect_metrics

        return collect_metrics()
    except ImportError:
        pass

    try:
        import psutil

        metrics: dict[str, Any] = {}
        try:
            metrics["cpu"] = psutil.cpu_percent(interval=0.1)
        except Exception:
            pass
        try:
            metrics["memory"] = psutil.virtual_memory().percent
        except Exception:
            pass
        try:
            import platform

            disk_path = "/" if platform.system() != "Windows" else "C:\\"
            metrics["disk"] = psutil.disk_usage(disk_path).percent
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
    except ImportError:
        logger.info("psutil not installed — metrics collection disabled")
        return {}


class MetricsCollector:
    """Background system metrics collector with threshold alerting.

    Polls at collect_interval_s (default 30s). When a metric exceeds
    its threshold, calls on_alert with a MetricsAlert.
    """

    def __init__(
        self,
        on_alert: Callable[[MetricsAlert], None] | None = None,
        thresholds: MetricsThresholds | None = None,
        collect_interval_s: float = 30.0,
    ) -> None:
        self._on_alert = on_alert
        self._thresholds = thresholds or MetricsThresholds()
        self._collect_interval_s = collect_interval_s
        self._snapshot = MetricsSnapshot()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def snapshot(self) -> MetricsSnapshot:
        return self._snapshot

    def start(self) -> bool:
        """Start background metrics collection."""
        if self._running:
            return True

        test = _collect_raw()
        if not test:
            logger.info("No metrics sources available — metrics disabled")
            return False

        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True, name="umh-metrics")
        self._thread.start()
        logger.info("Metrics collector started (interval %.0fs)", self._collect_interval_s)
        return True

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def collect_once(self) -> MetricsSnapshot:
        """Collect metrics synchronously (for on-demand status display)."""
        return self._do_collect()

    def _collect_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._do_collect()
            except Exception as exc:
                logger.debug("Metrics collection error: %s", exc)
            self._stop_event.wait(self._collect_interval_s)

    def _do_collect(self) -> MetricsSnapshot:
        raw = _collect_raw()
        now = time.monotonic()

        snap = MetricsSnapshot(
            cpu=raw.get("cpu", 0.0),
            memory=raw.get("memory", 0.0),
            disk=raw.get("disk", 0.0),
            battery=raw.get("battery"),
            collected_at=now,
        )
        net = raw.get("network_io", {})
        snap.network_sent = net.get("bytes_sent", 0)
        snap.network_recv = net.get("bytes_recv", 0)

        alerts = self._check_thresholds(snap, now)
        snap.alerts = alerts
        self._snapshot = snap

        for alert in alerts:
            if self._on_alert is not None:
                try:
                    self._on_alert(alert)
                except Exception as exc:
                    logger.debug("Metrics alert callback failed: %s", exc)

        return snap

    def _check_thresholds(self, snap: MetricsSnapshot, now: float) -> list[MetricsAlert]:
        alerts: list[MetricsAlert] = []
        t = self._thresholds

        checks = [
            ("cpu", snap.cpu, t.cpu_warning, t.cpu_critical),
            ("memory", snap.memory, t.memory_warning, t.memory_critical),
            ("disk", snap.disk, t.disk_warning, t.disk_critical),
        ]

        for metric, value, warn, crit in checks:
            if value >= crit:
                alerts.append(
                    MetricsAlert(
                        metric=metric,
                        value=value,
                        threshold=crit,
                        severity="critical",
                        timestamp=now,
                    )
                )
            elif value >= warn:
                alerts.append(
                    MetricsAlert(
                        metric=metric,
                        value=value,
                        threshold=warn,
                        severity="warning",
                        timestamp=now,
                    )
                )

        return alerts

    def get_snapshot(self) -> dict[str, Any]:
        return {
            "running": self._running,
            **self._snapshot.as_dict(),
        }
