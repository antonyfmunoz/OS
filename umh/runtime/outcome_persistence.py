"""Outcome persistence — JSONL append-only backend for durable outcome storage.

Writes each outcome as a single JSON line. Reads tolerate corrupted lines.
No deletion, no mutation, no in-place edits.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Protocol

from umh.runtime.outcome import OutcomeStatus, StrategyOutcome

_log = logging.getLogger(__name__)


class OutcomePersistenceBackend(Protocol):
    def append_outcome(self, outcome: StrategyOutcome) -> bool: ...
    def load_outcomes(self) -> list[StrategyOutcome]: ...


def _outcome_to_line(outcome: StrategyOutcome) -> str:
    return json.dumps(outcome.to_dict(), separators=(",", ":"))


def _line_to_outcome(line: str) -> StrategyOutcome | None:
    try:
        d = json.loads(line)
        return StrategyOutcome(
            outcome_id=d["outcome_id"],
            decision_id=d["decision_id"],
            action_name=d["action_name"],
            strategy_name=d["strategy_name"],
            state_signature=d["state_signature"],
            status=OutcomeStatus(d.get("status", "unknown")),
            success_score=float(d.get("success_score", 0.0)),
            latency=float(d.get("latency", 0.0)),
            effort=float(d.get("effort", 0.0)),
            error_count=int(d.get("error_count", 0)),
            timestamp=d.get("timestamp", ""),
            metadata=d.get("metadata", {}),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None


@dataclass(frozen=True)
class PersistenceResult:
    """Result of a persistence operation."""

    success: bool
    records_written: int = 0
    records_loaded: int = 0
    records_skipped: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "records_written": self.records_written,
            "records_loaded": self.records_loaded,
            "records_skipped": self.records_skipped,
            "error": self.error,
        }


class FileOutcomePersistenceBackend:
    """JSONL append-only file backend."""

    def __init__(self, path: str) -> None:
        self._path = path

    @property
    def path(self) -> str:
        return self._path

    def append_outcome(self, outcome: StrategyOutcome) -> bool:
        try:
            line = _outcome_to_line(outcome) + "\n"
            dir_name = os.path.dirname(self._path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            try:
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)
            return True
        except OSError as e:
            _log.debug("Outcome persistence write error: %s", e)
            return False

    def load_outcomes(self) -> list[StrategyOutcome]:
        if not os.path.exists(self._path):
            return []
        results: list[StrategyOutcome] = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    outcome = _line_to_outcome(stripped)
                    if outcome is not None:
                        results.append(outcome)
        except OSError as e:
            _log.debug("Outcome persistence read error: %s", e)
        return results

    def load_result(self) -> PersistenceResult:
        if not os.path.exists(self._path):
            return PersistenceResult(success=True, records_loaded=0, records_skipped=0)
        loaded = 0
        skipped = 0
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    outcome = _line_to_outcome(stripped)
                    if outcome is not None:
                        loaded += 1
                    else:
                        skipped += 1
            return PersistenceResult(success=True, records_loaded=loaded, records_skipped=skipped)
        except OSError as e:
            return PersistenceResult(success=False, error=str(e))
