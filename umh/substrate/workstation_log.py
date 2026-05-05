"""
Workstation log — structured event logger for workstation lifecycle.

Writes structured JSONL events to a rotating log file plus stderr.
Covers: startup, profile selection, dispatch, health transitions,
bootstrap, daemon crashes, and any workstation-level event.

Log location: /opt/OS/logs/workstation.jsonl (configurable via env)
Rotation: one backup file, 5 MB max per file.

Each log line is a self-contained JSON object:
  {"ts": "...", "event": "...", "data": {...}, "node_id": "..."}

Entry point:
  from umh.substrate.workstation_log import log_event
  log_event("bootstrap_started", {"profile": "founder_workstation"})

Design rules (mirror substrate conventions):
- Additive only. No modifications to existing modules.
- Best-effort. Log failures never raise into callers.
- Bounded. Rotating file, capped per-line size.
- Reversible. Removing this file removes only the log channel.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional


# ─── Configuration ──────────────────────────────────────────────────────────

DEFAULT_LOG_DIR = "/opt/OS/logs"
DEFAULT_LOG_FILE = "workstation.jsonl"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 1
MAX_LINE_LEN = 8192  # truncate individual log lines beyond this

_NODE_ID_DEFAULT = "antony-workstation"


# ─── State ──────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_handler: Optional[RotatingFileHandler] = None
_initialized = False


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_node_id() -> str:
    return os.environ.get("EOS_NODE_ID", _NODE_ID_DEFAULT)


def _ensure_log_dir() -> Path:
    """Create log directory if it doesn't exist. Best-effort."""
    log_dir = Path(os.environ.get("EOS_WORKSTATION_LOG_DIR", DEFAULT_LOG_DIR))
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return log_dir


def _init_handler() -> Optional[RotatingFileHandler]:
    """Initialize the rotating file handler. Called once, lazily."""
    global _handler, _initialized
    if _initialized:
        return _handler
    with _lock:
        if _initialized:
            return _handler
        try:
            log_dir = _ensure_log_dir()
            log_path = log_dir / DEFAULT_LOG_FILE
            h = RotatingFileHandler(
                str(log_path),
                maxBytes=MAX_BYTES,
                backupCount=BACKUP_COUNT,
                encoding="utf-8",
            )
            _handler = h
            _initialized = True
            return h
        except Exception as exc:
            print(
                f"[workstation_log] file handler init failed: {exc}",
                file=sys.stderr,
            )
            _initialized = True  # don't retry
            return None


# ─── Public API ─────────────────────────────────────────────────────────────


def log_event(
    event: str,
    data: Optional[dict[str, Any]] = None,
    *,
    node_id: Optional[str] = None,
    to_stderr: bool = True,
) -> None:
    """Write a structured workstation event.

    Args:
        event: Event type slug (e.g. "bootstrap_started", "daemon_crash").
        data: Arbitrary JSON-serializable payload.
        node_id: Override node ID (defaults to env or "antony-workstation").
        to_stderr: Also print a human-readable summary to stderr.

    Never raises. All errors are swallowed with a best-effort stderr note.
    """
    record = {
        "ts": _utcnow(),
        "event": event,
        "node_id": node_id or _get_node_id(),
        "data": data or {},
    }

    # Stderr output (human-readable)
    if to_stderr:
        try:
            summary = json.dumps(data, default=str) if data else "{}"
            if len(summary) > 200:
                summary = summary[:197] + "..."
            print(
                f"[workstation] {event} | {summary}",
                file=sys.stderr,
            )
        except Exception:
            pass

    # File output (JSONL)
    try:
        line = json.dumps(record, default=str, separators=(",", ":"))
        if len(line) > MAX_LINE_LEN:
            # Truncate data field to fit
            record["data"] = {"_truncated": True, "_event": event}
            line = json.dumps(record, default=str, separators=(",", ":"))

        handler = _init_handler()
        if handler is not None:
            with _lock:
                handler.stream.write(line + "\n")
                handler.stream.flush()
                # Check rotation by file size
                try:
                    if handler.stream.tell() >= MAX_BYTES:
                        handler.doRollover()
                except Exception:
                    pass
    except Exception as exc:
        try:
            print(
                f"[workstation_log] write failed: {exc}",
                file=sys.stderr,
            )
        except Exception:
            pass


def read_recent(n: int = 50) -> list[dict]:
    """Read the last N events from the log file. For observability tools.

    Returns parsed dicts. Malformed lines are skipped. Never raises.
    """
    events: list[dict] = []
    try:
        log_dir = _ensure_log_dir()
        log_path = log_dir / DEFAULT_LOG_FILE
        if not log_path.exists():
            return events

        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return events


def log_summary() -> dict:
    """Return a summary of recent log activity for health dashboards.

    Returns:
        Dict with event_counts, last_event_at, log_file_exists, log_file_size_kb.
    """
    summary: dict[str, Any] = {
        "event_counts": {},
        "last_event_at": None,
        "log_file_exists": False,
        "log_file_size_kb": 0,
    }
    try:
        log_dir = _ensure_log_dir()
        log_path = log_dir / DEFAULT_LOG_FILE
        if log_path.exists():
            summary["log_file_exists"] = True
            summary["log_file_size_kb"] = round(log_path.stat().st_size / 1024, 1)

        recent = read_recent(100)
        if recent:
            summary["last_event_at"] = recent[-1].get("ts")
            for evt in recent:
                etype = evt.get("event", "unknown")
                summary["event_counts"][etype] = (
                    summary["event_counts"].get(etype, 0) + 1
                )
    except Exception:
        pass
    return summary


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = ["log_event", "read_recent", "log_summary"]
