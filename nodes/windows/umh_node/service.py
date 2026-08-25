"""umh-node-service — Windows Service entry point.

Runs in Session 0 (no GUI). Owns the WebSocket connection,
shell adapter, filesystem adapter, metrics collection, heartbeat.

On non-Windows platforms, runs as a regular foreground process
(useful for development and testing on the VPS).
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import threading
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from nodes.windows.umh_node.client import NodeClient  # noqa: E402
from nodes.windows.umh_node.config import DEFAULT_LOG_DIR, load_node_config  # noqa: E402

logger = logging.getLogger("umh_node")


def _setup_logging() -> None:
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = DEFAULT_LOG_DIR / "umh-node-service.log"

    handler = logging.FileHandler(str(log_file), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(console)


def _install_windows_stop_event_handler(
    loop: asyncio.AbstractEventLoop,
    client: NodeClient,
) -> None:
    """Bridge the task supervisor's named event into the async shutdown path."""
    if sys.platform != "win32":
        return
    event_name = os.environ.get("UMH_DAEMON_STOP_EVENT")
    if not event_name:
        return

    try:
        import ctypes
    except Exception as exc:  # noqa: BLE001
        logger.error("cannot install Windows stop event handler: %s", exc)
        return

    SYNCHRONIZE = 0x00100000
    WAIT_OBJECT_0 = 0
    INFINITE = 0xFFFFFFFF

    handle = ctypes.windll.kernel32.OpenEventW(SYNCHRONIZE, False, event_name)
    if not handle:
        logger.error("cannot open UMH daemon stop event: %s", event_name)
        return

    def _wait_for_stop_event() -> None:
        try:
            result = ctypes.windll.kernel32.WaitForSingleObject(handle, INFINITE)
            if result == WAIT_OBJECT_0:
                logger.info("governed Windows stop event received")
                loop.call_soon_threadsafe(lambda: asyncio.ensure_future(client.stop()))
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)

    threading.Thread(target=_wait_for_stop_event, name="umh-stop-event", daemon=True).start()


def _install_windows_parent_exit_handler(
    loop: asyncio.AbstractEventLoop,
    client: NodeClient,
) -> None:
    """Stop gracefully if the governed parent wrapper exits first."""
    if sys.platform != "win32":
        return
    parent_pid = os.getppid()
    parent_label = "parent wrapper"
    supervisor_pid = os.environ.get("UMH_DAEMON_SUPERVISOR_PID", "").strip()
    if supervisor_pid:
        try:
            parent_pid = int(supervisor_pid)
            parent_label = "task supervisor"
        except ValueError:
            logger.warning("invalid UMH_DAEMON_SUPERVISOR_PID=%r", supervisor_pid)
    if parent_pid <= 0:
        return

    try:
        import ctypes
    except Exception as exc:  # noqa: BLE001
        logger.error("cannot install Windows parent-exit handler: %s", exc)
        return

    SYNCHRONIZE = 0x00100000
    WAIT_OBJECT_0 = 0
    INFINITE = 0xFFFFFFFF

    handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, parent_pid)
    if not handle:
        logger.warning("cannot monitor governed parent pid=%s", parent_pid)
        return

    def _wait_for_parent_exit() -> None:
        try:
            result = ctypes.windll.kernel32.WaitForSingleObject(handle, INFINITE)
            if result == WAIT_OBJECT_0:
                logger.info("governed %s exited; stopping daemon", parent_label)
                loop.call_soon_threadsafe(lambda: asyncio.ensure_future(client.stop()))
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)

    threading.Thread(target=_wait_for_parent_exit, name="umh-parent-exit", daemon=True).start()


def run_foreground() -> None:
    """Run the node client as a foreground process (Linux/dev mode)."""
    _setup_logging()
    config = load_node_config()

    if not config.vps_host:
        logger.error("UMH_VPS_HOST not set — cannot connect")
        sys.exit(1)
    if not config.node_id:
        logger.error("UMH_NODE_ID not set — cannot identify this node")
        sys.exit(1)

    logger.info("starting umh-node-service (foreground) as %s", config.node_id)
    logger.info("connecting to %s:%d", config.vps_host, config.vps_port)

    client = NodeClient(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _install_windows_stop_event_handler(loop, client)
    _install_windows_parent_exit_handler(loop, client)

    def _shutdown(*_: object) -> None:
        logger.info("shutdown signal received")
        loop.call_soon_threadsafe(lambda: asyncio.ensure_future(client.stop()))

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        loop.run_until_complete(client.stop())
    finally:
        loop.close()
        logger.info("umh-node-service stopped")


if sys.platform == "win32":
    try:
        import servicemanager  # noqa: F401 - imported for pywin32 service bootstrap side effects
        import win32event
        import win32service
        import win32serviceutil

        class UMHNodeService(win32serviceutil.ServiceFramework):
            _svc_name_ = "umh-node-service"
            _svc_display_name_ = "UMH Node Service"
            _svc_description_ = "UMH node mesh daemon — connects to VPS control plane"

            def __init__(self, args: list[str]) -> None:
                super().__init__(args)
                self.stop_event = win32event.CreateEvent(None, 0, 0, None)
                self.client: NodeClient | None = None
                self.loop: asyncio.AbstractEventLoop | None = None

            def SvcStop(self) -> None:
                self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
                if self.client and self.loop:
                    self.loop.call_soon_threadsafe(
                        lambda: asyncio.ensure_future(self.client.stop())
                    )
                win32event.SetEvent(self.stop_event)

            def SvcDoRun(self) -> None:
                _setup_logging()
                logger.info("Windows service starting")

                config = load_node_config()
                if not config.vps_host or not config.node_id:
                    logger.error("missing VPS_HOST or NODE_ID in config")
                    return

                self.client = NodeClient(config)
                self.loop = asyncio.new_event_loop()

                try:
                    self.loop.run_until_complete(self.client.run())
                except Exception as exc:
                    logger.error("service error: %s", exc)
                finally:
                    self.loop.close()
                    logger.info("Windows service stopped")

    except ImportError:
        pass


def main() -> None:
    """Entry point — Windows service or foreground."""
    if sys.platform == "win32" and len(sys.argv) > 1:
        try:
            win32serviceutil.HandleCommandLine(UMHNodeService)
            return
        except NameError:
            pass

    run_foreground()


if __name__ == "__main__":
    main()
