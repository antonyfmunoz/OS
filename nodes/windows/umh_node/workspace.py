"""Workspace awareness — tracks active window and full screen state.

Phase 34 enhancement: collects full workstation state (monitors, windows,
editor context, browser tabs, terminal sessions) for observation by VPS.

Runs in the tray companion process. Emits workspace signals when
the active window changes (debounced) or on periodic full refresh.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Deterministic app classification — no LLM
_APP_CATEGORY: dict[str, str] = {
    "code.exe": "ide",
    "cursor.exe": "ide",
    "devenv.exe": "ide",
    "pycharm64.exe": "ide",
    "webstorm64.exe": "ide",
    "idea64.exe": "ide",
    "chrome.exe": "browser",
    "msedge.exe": "browser",
    "firefox.exe": "browser",
    "brave.exe": "browser",
    "windowsterminal.exe": "terminal",
    "powershell.exe": "terminal",
    "cmd.exe": "terminal",
    "wt.exe": "terminal",
    "alacritty.exe": "terminal",
    "discord.exe": "communication",
    "slack.exe": "communication",
    "teams.exe": "communication",
    "figma.exe": "design",
    "photoshop.exe": "design",
}

_EDITOR_TITLE_PATTERNS = [
    "Visual Studio Code",
    "Cursor",
    "PyCharm",
    "WebStorm",
    "IntelliJ IDEA",
]

_BROWSER_PROCESSES = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"}
_TERMINAL_PROCESSES = {
    "windowsterminal.exe",
    "powershell.exe",
    "cmd.exe",
    "wt.exe",
    "alacritty.exe",
}


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


def _classify_app(process_name: str) -> str:
    """Classify process name to category string."""
    if not process_name:
        return "other"
    return _APP_CATEGORY.get(process_name.lower(), "other")


def _get_window_pid(hwnd: int) -> int:
    """Get process ID for a window handle via Win32 API."""
    try:
        import ctypes

        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value
    except Exception:
        return 0


def _get_process_name(pid: int) -> str:
    """Get process executable name from PID."""
    if pid <= 0:
        return ""
    try:
        import psutil

        return psutil.Process(pid).name()
    except Exception:
        return ""


def _collect_monitors() -> list[dict[str, Any]]:
    """Collect monitor information."""
    if sys.platform != "win32":
        return []
    try:
        from screeninfo import get_monitors

        monitors = []
        for i, m in enumerate(get_monitors()):
            monitors.append(
                {
                    "monitor_id": f"M{i}",
                    "name": getattr(m, "name", f"Monitor {i}"),
                    "width": m.width,
                    "height": m.height,
                    "x": m.x,
                    "y": m.y,
                    "is_primary": m.is_primary if hasattr(m, "is_primary") else i == 0,
                }
            )
        return monitors
    except Exception as exc:
        logger.debug("monitor collection failed: %s", exc)
        return []


def _collect_windows() -> list[dict[str, Any]]:
    """Collect all visible windows with process info."""
    if sys.platform != "win32":
        return []
    try:
        import ctypes

        import pygetwindow as gw

        foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
        windows = []
        for win in gw.getAllWindows():
            if not win.title.strip():
                continue
            hwnd = getattr(win, "_hWnd", 0)
            pid = _get_window_pid(hwnd) if hwnd else 0
            proc = _get_process_name(pid)
            category = _classify_app(proc)

            windows.append(
                {
                    "window_id": f"w{hwnd}" if hwnd else f"w{id(win)}",
                    "title": win.title,
                    "app_name": proc,
                    "pid": pid,
                    "x": getattr(win, "left", 0),
                    "y": getattr(win, "top", 0),
                    "width": getattr(win, "width", 0),
                    "height": getattr(win, "height", 0),
                    "is_visible": getattr(win, "visible", True),
                    "is_minimized": getattr(win, "isMinimized", False),
                    "is_focused": hwnd == foreground_hwnd,
                    "category": category,
                }
            )
        return windows
    except Exception as exc:
        logger.debug("window collection failed: %s", exc)
        return []


def _detect_editor_context(windows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Parse IDE window titles to extract editor context."""
    for win in windows:
        title = win.get("title", "")
        for pattern in _EDITOR_TITLE_PATTERNS:
            if pattern in title:
                parts = title.split(" - ")
                editor_name = pattern
                active_file = ""
                workspace_name = ""

                if len(parts) >= 3:
                    active_file = parts[0].strip()
                    workspace_name = parts[-2].strip()
                elif len(parts) == 2:
                    active_file = parts[0].strip()

                return {
                    "editor_name": editor_name,
                    "workspace_name": workspace_name,
                    "project_path": "",
                    "open_files": [active_file] if active_file else [],
                    "active_file": active_file,
                    "git_branch": "",
                }
    return None


def _detect_browser_tabs(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract browser tab info from browser window titles."""
    tabs = []
    for win in windows:
        proc = win.get("app_name", "").lower()
        if proc not in _BROWSER_PROCESSES:
            continue
        title = win.get("title", "")
        tabs.append(
            {
                "tab_id": win.get("window_id", ""),
                "url": "",
                "title": title,
                "domain": "",
                "is_active": win.get("is_focused", False),
            }
        )
    return tabs


def _detect_terminal_sessions(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract terminal session info from terminal window titles."""
    sessions = []
    for win in windows:
        proc = win.get("app_name", "").lower()
        if proc not in _TERMINAL_PROCESSES:
            continue
        sessions.append(
            {
                "terminal_id": win.get("window_id", ""),
                "terminal_type": proc.replace(".exe", ""),
                "title": win.get("title", ""),
                "pid": win.get("pid", 0),
                "cwd": "",
                "is_active": win.get("is_focused", False),
            }
        )
    return sessions


def _get_focused_window_id(windows: list[dict[str, Any]]) -> str:
    """Find the currently focused window ID."""
    for win in windows:
        if win.get("is_focused", False):
            return win.get("window_id", "")
    return ""


def collect_workstation_state() -> dict[str, Any]:
    """Collect full workstation state from Windows desktop.

    Returns a dict suitable for serialization and transport to VPS
    via signal.emit(signal_class="workstation_state").
    """
    monitors = _collect_monitors()
    windows = _collect_windows()
    editor_context = _detect_editor_context(windows)
    browser_tabs = _detect_browser_tabs(windows)
    terminal_sessions = _detect_terminal_sessions(windows)
    active_window_id = _get_focused_window_id(windows)

    return {
        "monitors": monitors,
        "windows": windows,
        "editor_context": editor_context,
        "browser_tabs": browser_tabs,
        "terminal_sessions": terminal_sessions,
        "active_window_id": active_window_id,
        "collected_at": time.time(),
    }


def _state_hash(state: dict[str, Any]) -> str:
    """Hash workstation state for change detection."""
    serialized = json.dumps(state, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode()).hexdigest()


class WorkspaceMonitor:
    """Watches for active window changes and calls back on change.

    Phase 34: enhanced to collect full workstation state (not just title)
    and debounce on content hash. Periodic full refresh every 30s.
    """

    def __init__(
        self,
        on_change: Callable[[dict[str, Any]], None],
        debounce_s: float = 2.0,
        poll_interval_s: float = 1.0,
        full_refresh_s: float = 30.0,
    ) -> None:
        self._on_change = on_change
        self._debounce_s = debounce_s
        self._poll_interval_s = poll_interval_s
        self._full_refresh_s = full_refresh_s
        self._last_window: str = ""
        self._last_hash: str = ""
        self._last_emit: float = 0.0
        self._last_full_refresh: float = 0.0
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
                now = time.monotonic()

                # Quick check: active window title changed?
                info = get_active_window()
                title_changed = False
                if info is not None:
                    title = info["title"]
                    if title != self._last_window:
                        self._last_window = title
                        title_changed = True

                force_refresh = (now - self._last_full_refresh) >= self._full_refresh_s
                debounce_ok = (now - self._last_emit) >= self._debounce_s

                if (title_changed or force_refresh) and debounce_ok:
                    state = collect_workstation_state()
                    h = _state_hash(state)
                    if h != self._last_hash or force_refresh:
                        self._last_hash = h
                        self._last_emit = now
                        self._last_full_refresh = now
                        self._on_change(state)

            except Exception as exc:
                logger.debug("workspace poll error: %s", exc)
