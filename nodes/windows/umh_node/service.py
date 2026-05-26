"""umh-node-service — Windows Service entry point.

Runs in Session 0 (no GUI). Owns the WebSocket connection,
shell adapter, filesystem adapter, metrics collection, heartbeat.

On non-Windows platforms, runs as a regular foreground process
(useful for development and testing on the VPS).
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

_service_dir = Path(__file__).resolve().parent.parent.parent
if str(_service_dir) not in sys.path:
    sys.path.insert(0, str(_service_dir))

from nodes.windows.umh_node.client import NodeClient
from nodes.windows.umh_node.config import DEFAULT_LOG_DIR, load_node_config

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
        import servicemanager
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
