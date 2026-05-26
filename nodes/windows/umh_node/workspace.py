"""Workspace awareness — tracks active window and screen state.

Runs in the tray companion process. Emits workspace signals when
the active window changes (debounced).
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


def get_active_window() -> dict[str, Any] | None:
    """Get the currently active window title and process name."""
    if sys.platform != "win32":
        return None

    try:
        import pygetwindow as gw

        win = gw.getActiveWindow()
        if win is None or not win.title.strip():
            return None
        return {"title": win.title, "process": ""}
    except Exception:
        return None

    return None


class WorkspaceMonitor:
    """Watches for active window changes and calls back on change."""

    def __init__(
        self,
        on_change: Callable[[dict[str, Any]], None],
        debounce_s: float = 2.0,
        poll_interval_s: float = 1.0,
    ) -> None:
        self._on_change = on_change
        self._debounce_s = debounce_s
        self._poll_interval_s = poll_interval_s
        self._last_window: str = ""
        self._last_emit: float = 0.0
        self._thread: threading.Thread | None = None
        self._shutdown = threading.Event()

    def start(self) -> threading.Thread:
        self._shutdown.clear()
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="workspace-monitor"
        )
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        self._shutdown.set()
        if self._thread is not None:
            self._thread.join(timeout=3)

    def _poll_loop(self) -> None:
        while not self._shutdown.wait(timeout=self._poll_interval_s):
            try:
                info = get_active_window()
                if info is None:
                    continue

                title = info["title"]
                now = time.monotonic()
                if title != self._last_window and (now - self._last_emit) >= self._debounce_s:
                    self._last_window = title
                    self._last_emit = now
                    self._on_change(info)
            except Exception as exc:
                logger.debug("workspace poll error: %s", exc)
