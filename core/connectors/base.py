"""Connector Base — common interface for real data ingestion.

Every connector implements the same protocol:
    healthcheck()   → is the source reachable?
    fetch_signals() → pull raw data and normalize
    normalize()     → convert raw records to RealSignal
    last_sync()     → when did we last pull?

Normalized output is RealSignal — a single unit of external truth
that the reality loop can consume directly.
"""

from __future__ import annotations

import csv
import io
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Normalized signal — the shared output of every connector
# ---------------------------------------------------------------------------


@dataclass
class RealSignal:
    """One unit of external reality, normalized across all sources.

    This is what connectors produce and the reality loop consumes.
    """

    source: str  # connector name (e.g. "email", "content", "crm")
    timestamp: float  # when the signal was observed
    metric_name: str  # what was measured (e.g. "reply_count", "impressions")
    value: float  # the measured value
    entity_id: str = ""  # optional: campaign id, content id, lead id
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "timestamp": self.timestamp,
            "metric_name": self.metric_name,
            "value": self.value,
            "entity_id": self.entity_id,
            "metadata": self.metadata,
        }

    def to_real_data(self) -> dict[str, Any]:
        """Convert to the real_data dict format that objective.evaluate_objective expects."""
        return {
            self.metric_name: self.value,
            **self.metadata,
        }


# ---------------------------------------------------------------------------
# Connector protocol
# ---------------------------------------------------------------------------


class Connector(ABC):
    """Base class for all real data connectors."""

    name: str = "base"

    def __init__(self) -> None:
        self._last_sync: float = 0.0

    @abstractmethod
    def healthcheck(self) -> bool:
        """Return True if the data source is reachable."""

    @abstractmethod
    def fetch_signals(self) -> list[RealSignal]:
        """Pull raw data from source and return normalized signals."""

    @abstractmethod
    def normalize(self, raw: Any) -> list[RealSignal]:
        """Convert a raw data record into normalized RealSignal(s)."""

    def last_sync(self) -> float:
        """Unix timestamp of last successful fetch."""
        return self._last_sync

    def _mark_synced(self) -> None:
        self._last_sync = time.time()


# ---------------------------------------------------------------------------
# File-based adapters — for MVP when live APIs aren't available
# ---------------------------------------------------------------------------


class JsonFileAdapter:
    """Read signals from a JSON file.

    Expected format: list of dicts with keys matching RealSignal fields,
    or a dict with a "signals" key containing that list.
    """

    @staticmethod
    def load(path: str | Path) -> list[dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            return []
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "signals" in data:
            return data["signals"]
        return [data]


class CsvFileAdapter:
    """Read signals from a CSV file.

    Columns: source, metric_name, value, entity_id, timestamp (optional).
    Extra columns go into metadata.
    """

    KNOWN_COLS = {"source", "metric_name", "value", "entity_id", "timestamp"}

    @staticmethod
    def load(path: str | Path) -> list[dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            return []
        rows: list[dict[str, Any]] = []
        with open(p) as f:
            reader = csv.DictReader(f)
            for row in reader:
                record: dict[str, Any] = {}
                metadata: dict[str, Any] = {}
                for k, v in row.items():
                    if k in CsvFileAdapter.KNOWN_COLS:
                        record[k] = v
                    else:
                        metadata[k] = v
                if metadata:
                    record["metadata"] = metadata
                rows.append(record)
        return rows


class LogFileAdapter:
    """Read signals from a JSONL log file (one JSON object per line)."""

    @staticmethod
    def load(path: str | Path) -> list[dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in p.read_text().strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records


class WebhookPayloadAdapter:
    """Parse a raw webhook payload dict into signal records.

    Handles common patterns:
    - Single event dict with "event"/"type" key
    - Batch with "events" list
    """

    @staticmethod
    def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
        if "events" in payload and isinstance(payload["events"], list):
            return payload["events"]
        return [payload]


# ---------------------------------------------------------------------------
# Helper: dict → RealSignal
# ---------------------------------------------------------------------------


def dict_to_signal(raw: dict[str, Any], source: str = "file") -> RealSignal:
    """Convert a raw dict to a RealSignal with sensible defaults."""
    return RealSignal(
        source=raw.get("source", source),
        timestamp=float(raw.get("timestamp", time.time())),
        metric_name=raw.get("metric_name", "unknown"),
        value=float(raw.get("value", 0)),
        entity_id=str(raw.get("entity_id", "")),
        metadata=raw.get("metadata", {}),
    )


# ---------------------------------------------------------------------------
# Aggregate multiple signals into real_data dict for objective evaluation
# ---------------------------------------------------------------------------


def aggregate_signals(signals: list[RealSignal]) -> dict[str, Any]:
    """Merge multiple RealSignals into one real_data dict.

    If the same metric_name appears multiple times, the latest value wins.
    All metadata is merged (latest wins on conflicts).
    """
    real_data: dict[str, Any] = {}
    # Sort by timestamp so latest overwrites earlier
    for sig in sorted(signals, key=lambda s: s.timestamp):
        real_data[sig.metric_name] = sig.value
        real_data.update(sig.metadata)
    return real_data


__all__ = [
    "RealSignal",
    "Connector",
    "JsonFileAdapter",
    "CsvFileAdapter",
    "LogFileAdapter",
    "WebhookPayloadAdapter",
    "dict_to_signal",
    "aggregate_signals",
]
