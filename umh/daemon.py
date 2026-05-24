"""Daemon — headless always-on workstation process.

Runs UMH as a background service without interactive stdin. Maintains:
  - Mesh connection to VPS (WebSocket heartbeat)
  - Perception sources (webcam, workspace, metrics)
  - Relay heartbeat (ALIVE/DEGRADED/DEAD)
  - Adapter lifecycle (desktop, clipboard, shell, filesystem)

Start: `umh --daemon` or `umh daemon start`
Status: `umh status` or `umh daemon status`
Stop: signal (SIGTERM/SIGINT) or `umh daemon stop`
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
PID_FILE = os.path.join(UMH_ROOT, "data", "sessions", "daemon.pid")
STATUS_FILE = os.path.join(UMH_ROOT, "data", "sessions", "daemon_status.json")

HEARTBEAT_INTERVAL_S = 30


class WorkstationDaemon:
    """Headless background daemon for the UMH workstation."""

    def __init__(self, node_id: str = "workstation_local") -> None:
        self._node_id = node_id
        self._running = False
        self._stop_event = threading.Event()
        self._perception: Any = None
        self._mesh_client: Any = None
        self._continuity: Any = None
        self._scheduler: Any = None
        self._inference_checker: Any = None
        self._mode_state: Any = None
        self._session_id: str = ""
        self._started_at: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    def run(self) -> int:
        """Run the daemon until stopped. Returns exit code."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        from umh.installer import ensure_directories

        ensure_directories()

        self._started_at = time.monotonic()
        self._running = True
        self._write_pid()

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("UMH daemon starting (node=%s, pid=%d)", self._node_id, os.getpid())

        self._init_mode_state()
        self._register_transport()
        self._setup_outcome_callback()
        self._sync_operator_boot()
        self._start_continuity()
        self._start_scheduler()
        self._create_inference_checker()
        self._emit_boot_signal()
        self._start_perception()
        self._connect_mesh()
        self._update_status("running")

        logger.info("UMH daemon online")

        try:
            self._heartbeat_loop()
        except Exception as exc:
            logger.error("Daemon heartbeat loop failed: %s", exc)
        finally:
            self._shutdown()

        return 0

    def _signal_handler(self, signum: int, frame: Any) -> None:
        logger.info("Signal %d received, shutting down", signum)
        self._stop_event.set()

    def _heartbeat_loop(self) -> None:
        """Main daemon loop — periodic health check + status update."""
        while not self._stop_event.is_set():
            self._emit_heartbeat()
            self._update_status("running")

            if self._perception is not None:
                self._perception.check_away_timeout()

            if self._inference_checker is not None and self._mode_state is not None:
                suggestion = self._inference_checker.check(self._mode_state.primary_profile.value)
                if suggestion:
                    logger.info("Inference suggestion: %s", suggestion)

            self._stop_event.wait(HEARTBEAT_INTERVAL_S)

    def _init_mode_state(self) -> None:
        """Initialize mode state and session ID for daemon."""
        try:
            from umh.modes import ModeState

            self._mode_state = ModeState()
        except Exception as exc:
            logger.debug("Mode state init failed: %s", exc)

        from uuid import uuid4

        self._session_id = f"daemon-{uuid4().hex[:12]}"

    def _register_transport(self) -> None:
        """Register workstation as a four-socket substrate transport."""
        try:
            from umh.boot import _register_transport

            _register_transport()
        except Exception as exc:
            logger.debug("Transport registration failed: %s", exc)

    def _setup_outcome_callback(self) -> None:
        try:
            from umh.boot import _setup_outcome_callback

            _setup_outcome_callback()
        except Exception as exc:
            logger.debug("Outcome callback setup failed: %s", exc)

    def _sync_operator_boot(self) -> None:
        try:
            from umh.boot import _sync_operator_boot

            _sync_operator_boot(self._node_id)
        except Exception as exc:
            logger.debug("Operator boot sync failed: %s", exc)

    def _start_continuity(self) -> None:
        try:
            from umh.boot import _start_continuity

            self._continuity = _start_continuity(self._session_id)
        except Exception as exc:
            logger.debug("Continuity start failed: %s", exc)

    def _start_scheduler(self) -> None:
        try:
            from umh.boot import _start_scheduler

            self._scheduler = _start_scheduler()
        except Exception as exc:
            logger.debug("Scheduler start failed: %s", exc)

    def _create_inference_checker(self) -> None:
        try:
            from umh.boot import _create_inference_checker

            self._inference_checker = _create_inference_checker()
        except Exception as exc:
            logger.debug("Inference checker creation failed: %s", exc)

    def _emit_boot_signal(self) -> None:
        try:
            from umh.boot import _emit_boot_signal

            _emit_boot_signal(self._session_id, boot_type="daemon")
        except Exception as exc:
            logger.debug("Boot signal emission failed: %s", exc)

    def _start_perception(self) -> None:
        """Start perception sources in daemon mode."""
        try:
            from umh.perception.router import PerceptionRouter

            if self._mode_state is None:
                from umh.modes import ModeState

                self._mode_state = ModeState()
            self._perception = PerceptionRouter(mode_state=self._mode_state, node_id=self._node_id)
            results = self._perception.start_all()
            started = [k for k, v in results.items() if v]
            if started:
                logger.info("Perception active: %s", ", ".join(started))
        except Exception as exc:
            logger.debug("Perception start failed: %s", exc)

    def _connect_mesh(self) -> None:
        """Connect to device mesh if configured."""
        try:
            from daemon.umh_node.config import load_node_config

            config = load_node_config()
            if not config or not config.vps_host:
                logger.info("No mesh config — standalone mode")
                return

            from daemon.umh_node.client import NodeClient

            self._mesh_client = NodeClient(config)
            mesh_thread = threading.Thread(
                target=self._run_mesh_client,
                daemon=True,
                name="umh-mesh",
            )
            mesh_thread.start()
            logger.info("Mesh client connecting to %s:%d", config.vps_host, config.vps_port)
        except ImportError:
            logger.info("Node mesh client not available — standalone mode")
        except Exception as exc:
            logger.debug("Mesh connection failed: %s", exc)

    def _run_mesh_client(self) -> None:
        """Run the async mesh client in a dedicated thread."""
        if self._mesh_client is None:
            return
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._mesh_client.run())
        except Exception as exc:
            logger.debug("Mesh client error: %s", exc)
        finally:
            try:
                loop.close()
            except Exception as exc:
                logger.debug("Event loop close failed: %s", exc)

    def _emit_heartbeat(self) -> None:
        """Emit relay heartbeat to substrate."""
        try:
            from substrate.execution.bridge.perception import (
                PerceptionRecord,
                PerceptionSeverity,
                PerceptionSource,
                PerceptionStore,
            )

            uptime = time.monotonic() - self._started_at
            record = PerceptionRecord.new(
                source=PerceptionSource.LOCAL_NODE_STATUS,
                summary=f"Daemon heartbeat: uptime {uptime:.0f}s, pid {os.getpid()}",
                severity=PerceptionSeverity.INFO,
                payload={
                    "node_id": self._node_id,
                    "uptime_s": round(uptime, 1),
                    "pid": os.getpid(),
                    "mesh_connected": self._mesh_client is not None
                    and getattr(self._mesh_client, "connected", False),
                },
            )
            PerceptionStore.default().put(record)
        except (ImportError, Exception) as exc:
            logger.debug("Heartbeat perception failed: %s", exc)

    def _shutdown(self) -> None:
        """Clean shutdown of all daemon components."""
        logger.info("Daemon shutting down")
        self._running = False

        if self._perception is not None:
            try:
                self._perception.stop_all()
            except Exception as exc:
                logger.debug("Perception shutdown failed: %s", exc)

        if self._scheduler is not None:
            try:
                self._scheduler.stop()
            except Exception as exc:
                logger.debug("Scheduler shutdown failed: %s", exc)

        if self._continuity is not None:
            try:
                self._continuity.save_on_exit()
            except Exception as exc:
                logger.debug("Continuity save failed: %s", exc)

        if self._mesh_client is not None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._mesh_client.stop())
                loop.close()
            except Exception as exc:
                logger.debug("Mesh client shutdown failed: %s", exc)

        try:
            from umh.operator_sync import sync_exit

            sync_exit(self._node_id)
        except Exception as exc:
            logger.debug("Operator sync exit failed: %s", exc)

        self._update_status("stopped")
        self._remove_pid()
        logger.info("Daemon stopped")

    def _write_pid(self) -> None:
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        try:
            with open(PID_FILE, "w") as f:
                f.write(str(os.getpid()))
        except Exception as exc:
            logger.debug("Failed to write PID file: %s", exc)

    def _remove_pid(self) -> None:
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception as exc:
            logger.debug("Failed to remove PID file: %s", exc)

    def _update_status(self, state: str) -> None:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        from datetime import datetime, timezone

        status = {
            "state": state,
            "pid": os.getpid(),
            "node_id": self._node_id,
            "uptime_s": round(time.monotonic() - self._started_at, 1) if self._started_at else 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "mesh_connected": self._mesh_client is not None
            and getattr(self._mesh_client, "connected", False),
            "perception": self._perception.get_snapshot() if self._perception else {},
        }
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
        except Exception as exc:
            logger.debug("Failed to write status file: %s", exc)

    def get_status(self) -> dict[str, Any]:
        """Read current daemon status from file."""
        if not os.path.exists(STATUS_FILE):
            return {"state": "not_running"}
        try:
            with open(STATUS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"state": "unknown"}


def run_daemon(node_id: str = "workstation_local") -> int:
    """Entry point for `umh --daemon`."""
    daemon = WorkstationDaemon(node_id=node_id)
    return daemon.run()


def get_daemon_status() -> dict[str, Any]:
    """Get daemon status without starting it."""
    daemon = WorkstationDaemon()
    status = daemon.get_status()

    if status.get("state") == "running":
        pid = status.get("pid")
        if pid and not _pid_alive(pid):
            status["state"] = "stale"
            status["note"] = f"PID {pid} not running — daemon crashed or was killed"

    return status


def show_daemon_status() -> int:
    """Print daemon status. Returns 0."""
    status = get_daemon_status()
    print()
    print("Daemon Status")
    print("-" * 40)
    print(f"  State:          {status.get('state', 'unknown')}")
    if status.get("pid"):
        print(f"  PID:            {status['pid']}")
    if status.get("node_id"):
        print(f"  Node:           {status['node_id']}")
    if status.get("uptime_s"):
        uptime = status["uptime_s"]
        if uptime > 3600:
            print(f"  Uptime:         {uptime / 3600:.1f}h")
        elif uptime > 60:
            print(f"  Uptime:         {uptime / 60:.1f}m")
        else:
            print(f"  Uptime:         {uptime:.0f}s")
    if status.get("mesh_connected"):
        print("  Mesh:           connected")
    elif status.get("state") == "running":
        print("  Mesh:           standalone")
    if status.get("note"):
        print(f"  Note:           {status['note']}")
    print()
    return 0


def stop_daemon() -> int:
    """Stop a running daemon via SIGTERM. Returns 0 on success, 1 on failure."""
    if not os.path.exists(PID_FILE):
        print("No daemon PID file found.")
        return 1
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
    except Exception:
        print("Invalid PID file.")
        return 1

    if not _pid_alive(pid):
        print(f"Daemon PID {pid} not running (stale PID file).")
        try:
            os.remove(PID_FILE)
        except Exception as exc:
            logger.debug("Failed to remove stale PID file: %s", exc)
        return 1

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to daemon (PID {pid}).")
        return 0
    except ProcessLookupError:
        print(f"Process {pid} not found.")
        return 1
    except PermissionError:
        print(f"Permission denied sending signal to PID {pid}.")
        return 1


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
