"""Watermark persistence — JSONL append-log for per-database poll high-water marks."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "notion_watermarks.jsonl"


def _default_watermark() -> str:
    """ISO timestamp far enough back to catch recent pages on first poll."""
    return "2000-01-01T00:00:00.000Z"


class WatermarkStore:
    """Thread-safe JSONL append-log for per-database poll watermarks.

    Each line: {"database_id": "...", "watermark": "ISO8601", "recorded_at": "ISO8601"}
    On load, the latest entry per database_id wins.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_PATH
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def load_watermarks(self) -> dict[str, str]:
        """Return latest watermark per database_id. Missing file → empty dict."""
        if not self._path.exists():
            return {}
        result: dict[str, str] = {}
        with self._lock:
            with open(self._path) as f:
                for line_no, raw in enumerate(f, 1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entry = json.loads(raw)
                        db_id = entry["database_id"]
                        result[db_id] = entry["watermark"]
                    except (json.JSONDecodeError, KeyError) as exc:
                        logger.warning("watermarks.jsonl line %d malformed: %s", line_no, exc)
        return result

    def get_watermark(self, database_id: str) -> str:
        """Return watermark for a single database, or default if not found."""
        marks = self.load_watermarks()
        return marks.get(database_id, _default_watermark())

    def record_watermark(self, database_id: str, watermark: str) -> None:
        """Append a new watermark entry to the JSONL file."""
        entry = {
            "database_id": database_id,
            "watermark": watermark,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a") as f:
                f.write(json.dumps(entry) + "\n")
