"""UMH Structured Logging — file + console output with task context.

Call setup_logging() once at process start. All UMH modules use
standard Python logging which this configures to output structured
JSON to files and human-readable text to console.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """JSON-lines formatter for file output."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add task context if present
        if hasattr(record, "task_id"):
            entry["task_id"] = record.task_id
        if hasattr(record, "phase"):
            entry["phase"] = record.phase
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for console."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        task = getattr(record, "task_id", "")
        prefix = f"[{task}] " if task else ""
        return f"{ts} {record.levelname:<5} {record.name}: {prefix}{record.getMessage()}"


def setup_logging(log_dir: str = "", level: str = "INFO") -> None:
    """Configure logging for the UMH process."""
    if not log_dir:
        from umh.core.config import LOG_DIR, LOG_LEVEL

        log_dir = LOG_DIR
        level = LOG_LEVEL

    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(ConsoleFormatter())
    console.setLevel(logging.INFO)
    root.addHandler(console)

    # API log (all UMH logs)
    api_handler = logging.FileHandler(os.path.join(log_dir, "umh_api.log"))
    api_handler.setFormatter(StructuredFormatter())
    api_handler.setLevel(logging.DEBUG)
    root.addHandler(api_handler)

    # Error log (WARNING+)
    error_handler = logging.FileHandler(os.path.join(log_dir, "umh_errors.log"))
    error_handler.setFormatter(StructuredFormatter())
    error_handler.setLevel(logging.WARNING)
    root.addHandler(error_handler)

    # Worker log (specific logger)
    worker_handler = logging.FileHandler(os.path.join(log_dir, "umh_worker.log"))
    worker_handler.setFormatter(StructuredFormatter())
    worker_logger = logging.getLogger("umh.orchestrator.worker")
    worker_logger.addHandler(worker_handler)
