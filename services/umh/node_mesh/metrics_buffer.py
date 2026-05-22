"""Per-node ring buffer for telemetry metrics — bypasses the full pipeline."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

METRICS_STORE = Path("/opt/OS/data/umh/mesh/metrics.jsonl")


@dataclass
class MetricsSnapshot:
    node_id: str
    timestamp: str
    cpu: float | None = None
    memory: float | None = None
    disk: float | None = None
    battery: float | None = None
    network_io: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"node_id": self.node_id, "timestamp": self.timestamp}
        if self.cpu is not None:
            d["cpu"] = self.cpu
        if self.memory is not None:
            d["memory"] = self.memory
        if self.disk is not None:
            d["disk"] = self.disk
        if self.battery is not None:
            d["battery"] = self.battery
        if self.network_io:
            d["network_io"] = self.network_io
        return d


class MetricsBuffer:
    """In-memory ring buffer per node, periodically flushed to JSONL."""

    def __init__(self, buffer_size: int = 1000, flush_interval_s: int = 300) -> None:
        self._buffers: dict[str, deque[MetricsSnapshot]] = {}
        self._buffer_size = buffer_size
        self._flush_interval_s = flush_interval_s
        self._lock = threading.Lock()
        self._flush_thread: threading.Thread | None = None
        self._shutdown = threading.Event()

    def record(self, snapshot: MetricsSnapshot) -> None:
        with self._lock:
            if snapshot.node_id not in self._buffers:
                self._buffers[snapshot.node_id] = deque(maxlen=self._buffer_size)
            self._buffers[snapshot.node_id].append(snapshot)

    def latest(self, node_id: str) -> MetricsSnapshot | None:
        with self._lock:
            buf = self._buffers.get(node_id)
            if buf:
                return buf[-1]
            return None

    def latest_all(self) -> dict[str, MetricsSnapshot]:
        with self._lock:
            result: dict[str, MetricsSnapshot] = {}
            for node_id, buf in self._buffers.items():
                if buf:
                    result[node_id] = buf[-1]
            return result

    def history(self, node_id: str, limit: int = 100) -> list[MetricsSnapshot]:
        with self._lock:
            buf = self._buffers.get(node_id)
            if not buf:
                return []
            items = list(buf)
            return items[-limit:]

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            self._buffers.pop(node_id, None)

    def start_flush_loop(self) -> None:
        if self._flush_thread is not None:
            return
        self._shutdown.clear()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def stop_flush_loop(self) -> None:
        self._shutdown.set()
        if self._flush_thread is not None:
            self._flush_thread.join(timeout=5)
            self._flush_thread = None

    def _flush_loop(self) -> None:
        while not self._shutdown.wait(timeout=self._flush_interval_s):
            self._flush_to_disk()

    def _flush_to_disk(self) -> None:
        with self._lock:
            all_snapshots: list[MetricsSnapshot] = []
            for buf in self._buffers.values():
                all_snapshots.extend(buf)

        if not all_snapshots:
            return

        try:
            METRICS_STORE.parent.mkdir(parents=True, exist_ok=True)
            with open(METRICS_STORE, "a") as f:
                for snap in all_snapshots:
                    f.write(json.dumps(snap.to_dict()) + "\n")
            logger.debug("flushed %d metric snapshots to %s", len(all_snapshots), METRICS_STORE)
        except Exception as exc:
            logger.error("metrics flush failed: %s", exc)
