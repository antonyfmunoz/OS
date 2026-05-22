"""WebSocket client — connects to the VPS node mesh server.

Handles the full lifecycle: connect → hello → heartbeat loop →
capability execution → signal emission → reconnect on failure.
"""

from __future__ import annotations

import asyncio
import json
import logging
import platform
import socket
import time
from typing import Any, Callable

import websockets

from daemon.umh_node.adapters.clipboard import ClipboardAdapter
from daemon.umh_node.adapters.desktop import DesktopAdapter
from daemon.umh_node.adapters.filesystem import FilesystemAdapter
from daemon.umh_node.adapters.shell import ShellAdapter
from daemon.umh_node.config import NodeConfig
from daemon.umh_node.governance import validate_request
from daemon.umh_node.metrics import collect_metrics

logger = logging.getLogger(__name__)


class NodeClient:
    """WebSocket client that connects to the UMH node mesh server."""

    def __init__(self, config: NodeConfig) -> None:
        self._config = config
        self._ws: Any = None
        self._connected = False
        self._shutdown = asyncio.Event()
        self._msg_id = 0

        self._adapters: dict[str, Any] = {}
        self._init_adapters()

        self._on_workspace_change: Callable[[dict[str, Any]], None] | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    def _init_adapters(self) -> None:
        cap_cfg = self._config.capabilities

        if cap_cfg.get("shell") is None or cap_cfg.get("shell").enabled:
            self._adapters["shell"] = ShellAdapter()
        if cap_cfg.get("filesystem") is None or cap_cfg.get("filesystem").enabled:
            self._adapters["filesystem"] = FilesystemAdapter()
        if cap_cfg.get("desktop") and cap_cfg["desktop"].enabled:
            self._adapters["desktop"] = DesktopAdapter()
        if cap_cfg.get("clipboard") and cap_cfg["clipboard"].enabled:
            self._adapters["clipboard"] = ClipboardAdapter()

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def _build_capabilities(self) -> list[dict[str, str]]:
        caps = []
        cap_cfg = self._config.capabilities
        default_risk = "reversible_write"
        default_max = "irreversible_write"

        if "shell" in self._adapters:
            cfg = cap_cfg.get("shell")
            caps.append(
                {
                    "name": "shell",
                    "category": "compute",
                    "risk_class": default_risk,
                    "max_risk_class": cfg.max_risk_class if cfg else default_max,
                }
            )

        if "filesystem" in self._adapters:
            cfg = cap_cfg.get("filesystem")
            caps.append(
                {
                    "name": "filesystem",
                    "category": "compute",
                    "risk_class": "read_only",
                    "max_risk_class": cfg.max_risk_class if cfg else default_max,
                }
            )

        if "desktop" in self._adapters:
            cfg = cap_cfg.get("desktop")
            caps.append(
                {
                    "name": "desktop",
                    "category": "compute",
                    "risk_class": default_risk,
                    "max_risk_class": cfg.max_risk_class if cfg else default_max,
                }
            )

        if "clipboard" in self._adapters:
            cfg = cap_cfg.get("clipboard")
            caps.append(
                {
                    "name": "clipboard",
                    "category": "compute",
                    "risk_class": "read_only",
                    "max_risk_class": cfg.max_risk_class if cfg else "safe_write",
                }
            )

        return caps

    async def run(self) -> None:
        """Main loop — connect with exponential backoff, handle messages."""
        backoff = 1.0
        max_backoff = self._config.reconnect_max_backoff_s

        while not self._shutdown.is_set():
            try:
                await self._connect_and_serve()
                backoff = 1.0
            except (
                websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError,
                OSError,
            ) as exc:
                logger.warning("connection lost: %s, reconnecting in %.0fs", exc, backoff)
                self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("unexpected error: %s, reconnecting in %.0fs", exc, backoff)
                self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def stop(self) -> None:
        self._shutdown.set()
        if self._ws:
            await self._ws.close()

    async def _connect_and_serve(self) -> None:
        url = self._config.ws_url
        logger.info("connecting to %s", url.split("?")[0])

        async with websockets.connect(url, ping_interval=30, ping_timeout=10) as ws:
            self._ws = ws
            await self._send_hello()
            self._connected = True
            logger.info("connected to VPS mesh server")

            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            try:
                async for raw in ws:
                    await self._handle_message(raw)
            finally:
                heartbeat_task.cancel()
                self._connected = False

    async def _send_hello(self) -> None:
        hostname = self._config.hostname or socket.gethostname()
        msg = {
            "jsonrpc": "2.0",
            "method": "node.hello",
            "params": {
                "node_id": self._config.node_id,
                "hostname": hostname,
                "os": platform.system().lower(),
                "os_version": platform.version(),
                "capabilities": self._build_capabilities(),
                "daemon_version": "0.1.0",
                "tailscale_ip": self._get_tailscale_ip(),
            },
            "id": self._next_id(),
        }
        await self._ws.send(json.dumps(msg))
        resp = json.loads(await self._ws.recv())
        if resp.get("result", {}).get("accepted"):
            logger.info("node.hello accepted")
        else:
            error = resp.get("error", {}).get("message", "unknown")
            raise ConnectionError(f"node.hello rejected: {error}")

    async def _heartbeat_loop(self) -> None:
        interval = self._config.signals.metrics_interval_s
        while True:
            await asyncio.sleep(interval)
            try:
                metrics = collect_metrics()
                msg = {
                    "jsonrpc": "2.0",
                    "method": "node.heartbeat",
                    "params": {"metrics": metrics},
                    "id": self._next_id(),
                }
                await self._ws.send(json.dumps(msg))
            except Exception as exc:
                logger.warning("heartbeat send failed: %s", exc)
                break

    async def _handle_message(self, raw: str) -> None:
        msg = json.loads(raw)
        method = msg.get("method", "")

        if method == "capability.execute":
            await self._handle_capability(msg)
        elif method == "outcome.notify":
            logger.info("outcome received: %s", msg.get("params", {}).get("summary", ""))
        elif "result" in msg or "error" in msg:
            pass
        else:
            logger.debug("unhandled message method: %s", method)

    async def _handle_capability(self, msg: dict[str, Any]) -> None:
        params = msg.get("params", {})
        msg_id = msg.get("id")
        cap_name = params.get("capability_name", "")
        cap_params = params.get("params", {})
        risk_class = params.get("risk_class", "REVERSIBLE_WRITE")

        adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
        cap_config = self._config.capabilities.get(adapter_key)
        allowed, reason = validate_request(adapter_key, cap_params, risk_class, cap_config)

        if not allowed:
            await self._ws.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {"success": False, "error": f"node governance denied: {reason}"},
                        "id": msg_id,
                    }
                )
            )
            return

        adapter = self._adapters.get(adapter_key)
        if adapter is None:
            await self._ws.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {
                            "success": False,
                            "error": f"adapter not available: {adapter_key}",
                        },
                        "id": msg_id,
                    }
                )
            )
            return

        t0 = time.monotonic()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, adapter.execute, cap_name, cap_params)
        duration = (time.monotonic() - t0) * 1000

        await self._ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "result": {
                        "success": result.get("success", False),
                        "result_data": result,
                        "latency_ms": round(duration, 1),
                        "side_effects": [],
                    },
                    "id": msg_id,
                }
            )
        )

    async def emit_signal(
        self,
        content_type: str,
        payload: dict[str, Any],
        signal_class: str = "event",
        urgency: str = "LOW",
    ) -> None:
        """Emit a signal to the VPS."""
        if not self._connected or self._ws is None:
            return
        msg = {
            "jsonrpc": "2.0",
            "method": "signal.emit",
            "params": {
                "content_type": content_type,
                "payload": payload,
                "urgency": urgency,
                "signal_class": signal_class,
            },
            "id": self._next_id(),
        }
        try:
            await self._ws.send(json.dumps(msg))
        except Exception as exc:
            logger.warning("signal emit failed: %s", exc)

    def _get_tailscale_ip(self) -> str:
        try:
            import subprocess

            result = subprocess.run(
                ["tailscale", "ip", "-4"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return ""
