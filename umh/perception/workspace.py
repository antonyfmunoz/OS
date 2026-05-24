"""Workspace perception — active window tracking + context inference.

Wraps daemon/umh_node/workspace.py WorkspaceMonitor and extends with
cross-platform support (xdotool on Linux, pygetwindow on Windows).
Records active window changes as perception events and infers workspace
context for mode suggestions.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WindowEvent:
    """A single active window observation."""

    title: str = ""
    process: str = ""
    timestamp: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {"title": self.title, "process": self.process, "timestamp": self.timestamp}


@dataclass
class WorkspaceState:
    """Rolling workspace context from recent window observations."""

    current_window: WindowEvent = field(default_factory=WindowEvent)
    recent_windows: list[WindowEvent] = field(default_factory=list)
    dominant_category: str = "unknown"

    def record(self, event: WindowEvent, max_history: int = 50) -> None:
        self.current_window = event
        self.recent_windows.append(event)
        if len(self.recent_windows) > max_history:
            self.recent_windows = self.recent_windows[-max_history:]
        self.dominant_category = _infer_category(event)


_CATEGORY_PATTERNS: dict[str, list[str]] = {
    "development": [
        "code",
        "cursor",
        "terminal",
        "tmux",
        "vim",
        "nvim",
        "emacs",
        "jetbrains",
        "pycharm",
        "webstorm",
        "intellij",
        "github",
    ],
    "research": [
        "chrome",
        "firefox",
        "safari",
        "brave",
        "edge",
        "arxiv",
        "scholar",
        "wikipedia",
        "docs",
    ],
    "communication": [
        "slack",
        "discord",
        "telegram",
        "teams",
        "zoom",
        "meet",
        "gmail",
        "outlook",
        "mail",
    ],
    "content": ["figma", "canva", "photoshop", "premiere", "davinci", "obs", "remotion"],
    "writing": ["obsidian", "notion", "docs", "word", "pages", "bear", "typora"],
}


def _infer_category(event: WindowEvent) -> str:
    """Infer workspace category from window title/process."""
    combined = f"{event.title} {event.process}".lower()
    for category, patterns in _CATEGORY_PATTERNS.items():
        if any(p in combined for p in patterns):
            return category
    return "unknown"


def get_active_window_cross_platform() -> dict[str, Any] | None:
    """Get active window info. Works on Linux (xdotool) and Windows (pygetwindow)."""
    if sys.platform == "win32":
        try:
            import pygetwindow as gw

            win = gw.getActiveWindow()
            if win is None or not win.title.strip():
                return None
            return {"title": win.title, "process": ""}
        except Exception as exc:
            logger.debug("pygetwindow failed: %s", exc)
            return None

    if sys.platform in ("linux", "linux2"):
        if not shutil.which("xdotool"):
            return None
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                title = result.stdout.strip()
                pid_result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowpid"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                process = ""
                if pid_result.returncode == 0 and pid_result.stdout.strip():
                    try:
                        pid = pid_result.stdout.strip()
                        comm_path = f"/proc/{pid}/comm"
                        if os.path.exists(comm_path):
                            with open(comm_path, encoding="utf-8") as f:
                                process = f.read().strip()
                    except Exception as exc:
                        logger.debug("Process name lookup failed: %s", exc)
                return {"title": title, "process": process}
        except Exception as exc:
            logger.debug("xdotool window query failed: %s", exc)
            return None

    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of first application process whose frontmost is true',
                ],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return {"title": result.stdout.strip(), "process": result.stdout.strip()}
        except Exception as exc:
            logger.debug("osascript window query failed: %s", exc)
            return None

    return None


class WorkspaceTracker:
    """Polls active window and emits change events.

    Cross-platform: Linux (xdotool), Windows (pygetwindow), macOS (osascript).
    Debounces rapid window switches to prevent chatter.
    """

    def __init__(
        self,
        on_change: Callable[[WindowEvent], None] | None = None,
        debounce_s: float = 2.0,
        poll_interval_s: float = 1.0,
    ) -> None:
        self._on_change = on_change
        self._debounce_s = debounce_s
        self._poll_interval_s = poll_interval_s
        self._state = WorkspaceState()
        self._last_title: str = ""
        self._last_emit: float = 0.0
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def state(self) -> WorkspaceState:
        return self._state

    def start(self) -> bool:
        """Start workspace monitoring. Returns False if no window tracking available."""
        if self._running:
            return True

        test = get_active_window_cross_platform()
        if test is None:
            logger.info("Active window tracking not available on this platform")
            return False

        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="umh-workspace")
        self._thread.start()
        logger.info("Workspace tracker started")
        return True

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                win = get_active_window_cross_platform()
                if win is None:
                    self._stop_event.wait(self._poll_interval_s)
                    continue

                title = win.get("title", "")
                now = time.monotonic()

                if title != self._last_title and (now - self._last_emit) >= self._debounce_s:
                    event = WindowEvent(
                        title=title,
                        process=win.get("process", ""),
                        timestamp=now,
                    )
                    self._state.record(event)
                    self._last_title = title
                    self._last_emit = now

                    if self._on_change is not None:
                        try:
                            self._on_change(event)
                        except Exception as exc:
                            logger.debug("Workspace change callback failed: %s", exc)

            except Exception as exc:
                logger.debug("Workspace poll error: %s", exc)

            self._stop_event.wait(self._poll_interval_s)

    def get_snapshot(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "current_window": self._state.current_window.title,
            "category": self._state.dominant_category,
            "history_size": len(self._state.recent_windows),
        }
