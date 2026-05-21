"""Monotonic clock utilities for UMH timing and tracing."""

from __future__ import annotations

import time
from datetime import datetime, timezone


def now_ms() -> int:
    """Monotonic millisecond timestamp for elapsed-time measurement."""
    return int(time.monotonic() * 1000)


def iso_now() -> str:
    """UTC ISO-8601 timestamp for event recording."""
    return datetime.now(timezone.utc).isoformat()
