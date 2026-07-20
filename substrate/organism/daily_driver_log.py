"""Daily Driver Log — records unhandled failures during real operation.

Captures every failure the operator encounters, whether homeostasis
detected it, and whether a work packet was auto-created. Feeds back
into the qualification harness as ground truth for "does the system
actually work under real daily use?"

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _log_path() -> Path:
    from substrate.state.runtime_paths import runtime_state_path

    return runtime_state_path("organism", "daily_driver_log.jsonl", create_parent=False)


@dataclass
class DriverFailure:
    failure_id: str = ""
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    source: str = ""
    error: str = ""
    homeostasis_detected: bool = False
    work_packet_created: bool = False
    work_packet_id: str = ""
    resolution: str = ""
    resolved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "timestamp": self.timestamp,
            "description": self.description,
            "source": self.source,
            "error": self.error,
            "homeostasis_detected": self.homeostasis_detected,
            "work_packet_created": self.work_packet_created,
            "work_packet_id": self.work_packet_id,
            "resolution": self.resolution,
            "resolved_at": self.resolved_at,
        }


class DailyDriverLog:
    """Append-only log of operator-facing failures."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _log_path()
        self._entries: list[DriverFailure] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            for line in self._path.read_text().strip().splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    entry = DriverFailure(
                        **{k: v for k, v in row.items() if k in DriverFailure.__dataclass_fields__}
                    )
                    self._entries.append(entry)
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as exc:
            logger.debug("failed to load daily driver log: %s", exc)

    def record(self, failure: DriverFailure) -> None:
        self._entries.append(failure)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a") as f:
                f.write(json.dumps(failure.to_dict(), default=str) + "\n")
        except Exception as exc:
            logger.debug("failed to persist driver failure: %s", exc)

    def unresolved(self) -> list[DriverFailure]:
        return [e for e in self._entries if not e.resolution]

    def auto_detected_rate(self) -> float:
        if not self._entries:
            return 1.0
        detected = sum(1 for e in self._entries if e.homeostasis_detected)
        return detected / len(self._entries)

    def work_packet_rate(self) -> float:
        if not self._entries:
            return 1.0
        created = sum(1 for e in self._entries if e.work_packet_created)
        return created / len(self._entries)

    @property
    def total_failures(self) -> int:
        return len(self._entries)

    @property
    def total_resolved(self) -> int:
        return sum(1 for e in self._entries if e.resolution)
