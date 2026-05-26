"""umh-desktop — System tray companion for UMH node mesh.

Runs in the user session with GUI access. Provides:
- Desktop adapter (mouse, keyboard, screenshots, window management)
- Clipboard adapter (read/write)
- Workspace awareness (active window tracking)
- System tray icon with status indicator

Connects to umh-node-service via named pipe on Windows,
or directly to the VPS mesh server for development/testing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
import time
from typing import Any

from nodes.windows.umh_node.adapters.clipboard import ClipboardAdapter
from nodes.windows.umh_node.adapters.desktop import DesktopAdapter
from nodes.windows.umh_node.config import DEFAULT_LOG_DIR, load_node_config
from nodes.windows.umh_node.workspace import WorkspaceMonitor, get_active_window

logger = logging.getLogger("umh_desktop")

_STATUS = {"connected": False, "last_window": "", "vps_host": ""}


def _setup_logging() -> None:
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = DEFAULT_LOG_DIR / "umh-desktop.log"

    handler = logging.FileHandler(str(log_file), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(console)


class PipeClient:
    """Named pipe client for communicating with umh-node-service.

    On non-Windows platforms, falls back to a no-op for development.
    """

    def __init__(self) -> None:
        self._pipe: Any = None
        self._connected = False

    def connect(self) -> bool:
        if sys.platform != "win32":
            logger.info("named pipe not available on %s (dev mode)", sys.platform)
            return False

        try:
            import win32file
            import win32pipe

            pipe_name = r"\\.\pipe\umh-node"
            self._pipe = win32file.CreateFile(
                pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )
            self._connected = True
            logger.info("connected to service via named pipe")
            return True
        except Exception as exc:
            logger.warning("pipe connection failed: %s", exc)
            return False

    def send(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        if not self._connected or self._pipe is None:
            return None

        try:
            import win32file

            data = json.dumps(msg).encode("utf-8")
            win32file.WriteFile(self._pipe, data)

            _, resp_data = win32file.ReadFile(self._pipe, 65536)
            return json.loads(resp_data.decode("utf-8"))
        except Exception as exc:
            logger.warning("pipe send/recv failed: %s", exc)
            return None

    def close(self) -> None:
        if self._pipe is not None:
            try:
                import win32file

                win32file.CloseHandle(self._pipe)
            except Exception:
                pass
            self._pipe = None
            self._connected = False


def _on_workspace_change(info: dict[str, Any]) -> None:
    """Called by WorkspaceMonitor when active window changes."""
    _STATUS["last_window"] = info.get("title", "")
    logger.debug("active window: %s", info.get("title", ""))


def run_tray() -> None:
    """Run the tray companion — starts workspace monitor and tray icon."""
    _setup_logging()
    config = load_node_config()
    _STATUS["vps_host"] = config.vps_host

    logger.info("starting umh-desktop tray companion")

    workspace = WorkspaceMonitor(
        on_change=_on_workspace_change,
        debounce_s=config.signals.workspace_debounce_s,
    )
    workspace.start()
    logger.info("workspace monitor started")

    pipe = PipeClient()
    pipe.connect()

    try:
        _run_tray_icon(workspace, pipe)
    except ImportError:
        logger.info("pystray not available, running headless (dev mode)")
        _run_headless(workspace)
    finally:
        workspace.stop()
        pipe.close()
        logger.info("umh-desktop stopped")


def _run_tray_icon(workspace: WorkspaceMonitor, pipe: PipeClient) -> None:
    """Run with system tray icon using pystray."""
    import pystray
    from PIL import Image

    def _create_icon_image(color: tuple[int, int, int] = (0, 200, 200)) -> Image.Image:
        img = Image.new("RGB", (64, 64), color)
        return img

    def _on_quit(icon: Any, _: Any) -> None:
        icon.stop()

    def _on_status(icon: Any, _: Any) -> None:
        win = _STATUS.get("last_window", "none")
        logger.info("status: connected=%s, window=%s", _STATUS["connected"], win)

    menu = pystray.Menu(
        pystray.MenuItem("Status", _on_status),
        pystray.MenuItem("Quit", _on_quit),
    )

    icon = pystray.Icon(
        "umh-desktop",
        _create_icon_image(),
        "UMH Desktop",
        menu,
    )

    icon.run()


def _run_headless(workspace: WorkspaceMonitor) -> None:
    """Headless mode for development — no tray icon, just logs."""
    logger.info("running headless (no tray icon)")
    try:
        while True:
            time.sleep(5)
            win = get_active_window()
            if win:
                logger.info("active window: %s", win.get("title", ""))
    except KeyboardInterrupt:
        pass


def main() -> None:
    run_tray()


if __name__ == "__main__":
    main()
