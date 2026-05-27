"""Canonical fix-forever error recorder.

Every error in the system is appended to a single JSONL log for
pattern detection and permanent fixing.  All modules import from here
instead of carrying their own copy.

Usage:
    from substrate.observability.error_recorder import record_error

    record_error("gateway", err, {"request_id": rid})
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from substrate.observability.jsonl_rotation import rotate_if_needed

_log = logging.getLogger(__name__)

_ERROR_LOG_PATH = Path(
    os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or "/opt/OS"
) / "logs" / "errors.jsonl"


def record_error(
    component: str,
    error: Exception | str,
    context: dict | None = None,
) -> None:
    """Append a structured error record to errors.jsonl.

    Fields:
        ts         — UTC ISO-8601 timestamp
        component  — subsystem that raised the error
        error      — stringified error (truncated to 500 chars)
        error_type — exception class name, or ``"str"`` for plain strings
        context    — arbitrary key/value pairs (values truncated to 200 chars)
    """
    try:
        _ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        rotate_if_needed(_ERROR_LOG_PATH)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "error": str(error)[:500],
            "error_type": type(error).__name__ if isinstance(error, Exception) else "str",
            "context": {k: str(v)[:200] for k, v in (context or {}).items()},
        }
        with _ERROR_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as log_err:
        _log.warning("Failed to write error log: %s", log_err)
