"""Prediction persistence — durable append-only storage for prediction records and weights.

File-based JSONL backend with atomic writes (temp -> fsync -> replace).
Tolerates partial failure: corrupted lines are skipped on load.
Never overwrites historical data — append-only or atomic-replace.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from umh.prediction.store import PredictionRecord, PredictionStatus

_log = logging.getLogger(__name__)

_DEFAULT_RECORDS_FILE = "prediction_records.jsonl"
_DEFAULT_WEIGHTS_FILE = "prediction_weights.json"


def _record_to_json(record: PredictionRecord) -> dict[str, Any]:
    return record.to_dict()


def _record_from_json(data: dict[str, Any]) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=data["prediction_id"],
        intent_id=data["intent_id"],
        inferred_goal=data["inferred_goal"],
        confidence=data["confidence"],
        predicted_actions=tuple(data.get("predicted_actions", ())),
        related_entities=tuple(data.get("related_entities", ())),
        source=data.get("source", ""),
        context_hash=data.get("context_hash", ""),
        emitted_at=data.get("emitted_at", ""),
        status=PredictionStatus(data.get("status", "pending")),
        resolved_at=data.get("resolved_at", ""),
        matched_job_id=data.get("matched_job_id", ""),
        tick_emitted=data.get("tick_emitted", 0),
        metadata=data.get("metadata", {}),
    )


def _weight_to_json(pw: Any) -> dict[str, Any]:
    return pw.to_dict()


@dataclass
class PersistenceStats:
    """Summary of a persistence operation."""

    records_saved: int = 0
    records_loaded: int = 0
    records_skipped: int = 0
    weights_saved: int = 0
    weights_loaded: int = 0
    weights_skipped: int = 0
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "records_saved": self.records_saved,
            "records_loaded": self.records_loaded,
            "records_skipped": self.records_skipped,
            "weights_saved": self.weights_saved,
            "weights_loaded": self.weights_loaded,
            "weights_skipped": self.weights_skipped,
            "errors": self.errors or [],
        }


class FilePredictionBackend:
    """JSONL-based persistence backend for prediction records and weights.

    Atomic writes: write to temp file -> fsync -> rename.
    Append-only for records (JSONL). Atomic-replace for weights (JSON).
    Corrupted lines skipped on load.
    """

    def __init__(
        self,
        data_dir: str | Path,
        *,
        records_file: str = _DEFAULT_RECORDS_FILE,
        weights_file: str = _DEFAULT_WEIGHTS_FILE,
    ) -> None:
        self._data_dir = Path(data_dir)
        self._records_path = self._data_dir / records_file
        self._weights_path = self._data_dir / weights_file

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @property
    def records_path(self) -> Path:
        return self._records_path

    @property
    def weights_path(self) -> Path:
        return self._weights_path

    def _ensure_dir(self) -> bool:
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            _log.warning("Cannot create persistence directory %s: %s", self._data_dir, e)
            return False

    def save_records(self, records: list[PredictionRecord]) -> PersistenceStats:
        """Atomically write all records as JSONL."""
        stats = PersistenceStats()
        if not self._ensure_dir():
            stats.errors = [f"cannot create dir {self._data_dir}"]
            return stats

        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._data_dir), suffix=".tmp", prefix="records_"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    for rec in records:
                        try:
                            line = json.dumps(_record_to_json(rec), separators=(",", ":"))
                            f.write(line + "\n")
                            stats.records_saved += 1
                        except (TypeError, ValueError) as e:
                            stats.records_skipped += 1
                            if stats.errors is None:
                                stats.errors = []
                            stats.errors.append(f"serialize {rec.prediction_id}: {e}")
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, str(self._records_path))
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            _log.warning("Failed to save prediction records: %s", e)
            if stats.errors is None:
                stats.errors = []
            stats.errors.append(f"save_records: {e}")

        return stats

    def load_records(self) -> tuple[list[PredictionRecord], PersistenceStats]:
        """Load records from JSONL, skipping corrupted lines."""
        stats = PersistenceStats()
        records: list[PredictionRecord] = []

        if not self._records_path.exists():
            return records, stats

        try:
            with open(self._records_path) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        rec = _record_from_json(data)
                        records.append(rec)
                        stats.records_loaded += 1
                    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                        stats.records_skipped += 1
                        if stats.errors is None:
                            stats.errors = []
                        stats.errors.append(f"line {line_num}: {e}")
                        _log.debug("Skipping corrupted record at line %d: %s", line_num, e)
        except OSError as e:
            _log.warning("Failed to load prediction records: %s", e)
            if stats.errors is None:
                stats.errors = []
            stats.errors.append(f"load_records: {e}")

        return records, stats

    def save_weights(self, weights_data: list[dict[str, Any]]) -> PersistenceStats:
        """Atomically write weight data as JSON."""
        stats = PersistenceStats()
        if not self._ensure_dir():
            stats.errors = [f"cannot create dir {self._data_dir}"]
            return stats

        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._data_dir), suffix=".tmp", prefix="weights_"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(weights_data, f, separators=(",", ":"))
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, str(self._weights_path))
                stats.weights_saved = len(weights_data)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            _log.warning("Failed to save prediction weights: %s", e)
            if stats.errors is None:
                stats.errors = []
            stats.errors.append(f"save_weights: {e}")

        return stats

    def load_weights(self) -> tuple[list[dict[str, Any]], PersistenceStats]:
        """Load weight data from JSON. Returns empty list on failure."""
        stats = PersistenceStats()
        weights: list[dict[str, Any]] = []

        if not self._weights_path.exists():
            return weights, stats

        try:
            with open(self._weights_path) as f:
                data = json.load(f)
            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict) and "pattern_key" in entry:
                        weights.append(entry)
                        stats.weights_loaded += 1
                    else:
                        stats.weights_skipped += 1
            else:
                stats.weights_skipped += 1
                if stats.errors is None:
                    stats.errors = []
                stats.errors.append("weights file is not a JSON array")
        except (json.JSONDecodeError, OSError) as e:
            _log.warning("Failed to load prediction weights: %s", e)
            if stats.errors is None:
                stats.errors = []
            stats.errors.append(f"load_weights: {e}")

        return weights, stats

    def exists(self) -> bool:
        return self._records_path.exists() or self._weights_path.exists()
