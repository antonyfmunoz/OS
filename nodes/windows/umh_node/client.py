"""WebSocket client — connects to the VPS node mesh server.

Handles the full lifecycle: connect → hello → heartbeat loop →
capability execution → signal emission → reconnect on failure.

Architecture: CONTROL PLANE and MEDIA PLANE are hard-separated.
- Control plane (heartbeats, capability dispatch) runs on the main
  asyncio event loop and is NEVER blocked by frame emission.
- Media plane (frame emission) uses a bounded async queue with
  drop-oldest backpressure. A dedicated drain task sends frames
  without blocking the control loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import platform
import socket
import struct
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import websockets

from nodes.windows.umh_node.adapters.broadcast import BroadcastAdapter
from nodes.windows.umh_node.adapters.camera import CameraAdapter
from nodes.windows.umh_node.adapters.clipboard import ClipboardAdapter
from nodes.windows.umh_node.adapters.desktop import DesktopAdapter
from nodes.windows.umh_node.adapters.desktop_stream import DesktopStreamAdapter
from nodes.windows.umh_node.adapters.filesystem import FilesystemAdapter
from nodes.windows.umh_node.adapters.hermes import HermesAdapter
from nodes.windows.umh_node.adapters.shell import ShellAdapter
from nodes.windows.umh_node.config import CapabilityConfig, NodeConfig
from nodes.windows.umh_node.governance import validate_request
from nodes.windows.umh_node.metrics import collect_metrics
from nodes.windows.umh_node.peripheral_scanner import scan_all_peripherals, get_scan_age_s
from nodes.windows.umh_node.workspace import collect_workstation_state, _state_hash

logger = logging.getLogger(__name__)

_MEDIA_QUEUE_MAX = 4
_CONTROL_TIMEOUT_S = 8.0


class NodeClient:
    """WebSocket client that connects to the UMH node mesh server.

    Hard separation between control plane and media plane:
    - Control: heartbeats + capability dispatch — always responsive.
    - Media: frame emission via bounded queue — drops old frames on backpressure.
    """

    def __init__(self, config: NodeConfig) -> None:
        self._config = config
        self._ws: Any = None
        self._connected = False
        self._shutdown = asyncio.Event()
        self._msg_id = 0

        self._adapters: dict[str, Any] = {}
        self._init_adapters()

        self._loop: asyncio.AbstractEventLoop | None = None
        self._on_workspace_change: Callable[[dict[str, Any]], None] | None = None
        self._camera_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cam")
        self._capability_semaphore = asyncio.Semaphore(8)

        # Media plane: bounded frame queue — stream thread pushes, drain task sends
        self._media_queue: deque[str] = deque(maxlen=_MEDIA_QUEUE_MAX)
        self._media_event = asyncio.Event()
        self._media_drain_task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    def _init_adapters(self) -> None:
        cap_cfg = self._config.capabilities

        if cap_cfg.get("shell") is None or cap_cfg.get("shell").enabled:
            self._adapters["shell"] = ShellAdapter()
        from nodes.windows.umh_node.adapters.terminal import TerminalAdapter

        self._adapters["terminal"] = TerminalAdapter()
        if cap_cfg.get("filesystem") is None or cap_cfg.get("filesystem").enabled:
            self._adapters["filesystem"] = FilesystemAdapter()
        if cap_cfg.get("desktop") and cap_cfg["desktop"].enabled:
            self._adapters["desktop"] = DesktopAdapter()
        if cap_cfg.get("clipboard") and cap_cfg["clipboard"].enabled:
            self._adapters["clipboard"] = ClipboardAdapter()
        if cap_cfg.get("camera") and cap_cfg["camera"].enabled:
            cam = CameraAdapter()
            cam.set_frame_callback(self._on_camera_frame)
            self._adapters["camera"] = cam
            try:
                result = cam.execute(
                    "camera.stream_start", {"fps": 2, "quality": 70, "resolution": [1280, 720]}
                )
                if result.get("success"):
                    logger.info("camera stream auto-started (2fps, 1280x720, q70)")
                else:
                    logger.debug("camera auto-start returned: %s", result.get("error"))
            except Exception as exc:
                logger.debug("camera auto-start failed: %s", exc)
        try:
            import mss

            with mss.mss() as sct:
                monitor_count = len(sct.monitors) - 1  # index 0 is virtual combined
            for idx in range(1, monitor_count + 1):
                key = f"desktop_stream_{idx - 1}"
                ds = DesktopStreamAdapter(monitor_index=idx)
                ds.set_frame_callback(self._on_camera_frame)
                self._adapters[key] = ds
                ds.start()
            logger.info("desktop stream: %d monitor(s) active", monitor_count)
        except Exception as exc:
            logger.debug("desktop stream adapter unavailable: %s", exc)
        # Hermes: always register if binary exists, no config gate needed
        hermes = HermesAdapter()
        if hermes._available:
            self._adapters["hermes"] = hermes

        # Broadcast: always register — FFmpeg availability checked at runtime
        broadcast_cfg = cap_cfg.get("broadcast")
        if broadcast_cfg is None or broadcast_cfg.enabled:
            self._adapters["broadcast"] = BroadcastAdapter()

    def _on_camera_frame(self, frame_data: dict[str, Any]) -> None:
        """Called from camera stream thread — enqueues frame for async send.

        Sends binary WS frames: [4-byte meta_len][JSON meta][JPEG bytes].
        Saves ~33% bandwidth vs base64 JSON-RPC encoding.
        NEVER blocks on WS send. Uses bounded deque with drop-oldest semantics.
        """
        if not self._connected or self._ws is None or self._loop is None:
            return
        try:
            jpeg_bytes = frame_data.pop("image_jpeg", None)
            if jpeg_bytes is None:
                return
            meta_bytes = json.dumps(frame_data).encode()
            msg = struct.pack(">I", len(meta_bytes)) + meta_bytes + jpeg_bytes
            self._media_queue.append(msg)
            self._loop.call_soon_threadsafe(self._media_event.set)
        except Exception as exc:
            logger.debug("frame enqueue failed: %s", exc)

    async def _media_drain_loop(self) -> None:
        """Drain media queue and send frames over WS.

        Runs as a separate task — if WS send is slow, frames drop from
        the bounded queue. Control plane is never affected.
        """
        while True:
            await self._media_event.wait()
            self._media_event.clear()
            while self._media_queue:
                try:
                    msg = self._media_queue.popleft()
                except IndexError:
                    break
                if not self._connected or self._ws is None:
                    self._media_queue.clear()
                    break
                try:
                    await self._ws.send(msg)
                except Exception as exc:
                    logger.debug("media send failed: %s", exc)
                    self._media_queue.clear()
                    break

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

        if "camera" in self._adapters:
            cfg = cap_cfg.get("camera")
            caps.append(
                {
                    "name": "camera",
                    "category": "media",
                    "risk_class": "read_only",
                    "max_risk_class": cfg.max_risk_class if cfg else "read_only",
                }
            )

        if "broadcast" in self._adapters:
            caps.append(
                {
                    "name": "broadcast",
                    "category": "media",
                    "risk_class": "reversible_write",
                    "max_risk_class": "external_communication",
                }
            )

        if "terminal" in self._adapters:
            caps.append(
                {
                    "name": "terminal",
                    "category": "compute",
                    "risk_class": "reversible_write",
                    "max_risk_class": "irreversible_write",
                }
            )

        return caps

    async def run(self) -> None:
        """Main loop — connect with exponential backoff, handle messages."""
        self._loop = asyncio.get_running_loop()
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

        # Token travels in the Authorization header, never in the URL.
        async with websockets.connect(
            url,
            ping_interval=120,
            ping_timeout=60,
            max_size=4 * 1024 * 1024,
            additional_headers=self._config.auth_header,
        ) as ws:
            self._ws = ws
            await self._send_hello()
            self._connected = True
            self._media_queue.clear()
            logger.info("connected to VPS mesh server")

            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._media_drain_task = asyncio.create_task(self._media_drain_loop())
            workspace_task = asyncio.create_task(self._workspace_emission_loop())
            try:
                async for raw in ws:
                    await self._handle_message(raw)
            finally:
                heartbeat_task.cancel()
                workspace_task.cancel()
                if self._media_drain_task:
                    self._media_drain_task.cancel()
                    self._media_drain_task = None
                self._connected = False

    async def _send_hello(self) -> None:
        hostname = self._config.hostname or socket.gethostname()
        loop = asyncio.get_running_loop()
        peripherals = await loop.run_in_executor(None, scan_all_peripherals, True)
        msg = {
            "jsonrpc": "2.0",
            "method": "node.hello",
            "params": {
                "node_id": self._config.node_id,
                "hostname": hostname,
                "os": platform.system().lower(),
                "os_version": platform.version(),
                "capabilities": self._build_capabilities(),
                "peripherals": peripherals,
                "peripheral_scan_age_s": 0,
                "daemon_version": "0.2.0",
                "tailscale_ip": self._get_tailscale_ip(),
            },
            "id": self._next_id(),
        }
        await self._ws.send(json.dumps(msg))
        resp = json.loads(await self._ws.recv())
        result = resp.get("result", {})
        if result.get("accepted"):
            server_interval = result.get("heartbeat_interval_s")
            if server_interval and isinstance(server_interval, (int, float)):
                self._heartbeat_interval = int(server_interval)
            else:
                self._heartbeat_interval = self._config.signals.metrics_interval_s
            logger.info("node.hello accepted, heartbeat every %ds", self._heartbeat_interval)
        else:
            error = resp.get("error", {}).get("message", "unknown")
            raise ConnectionError(f"node.hello rejected: {error}")

    async def rescan_peripherals(self) -> list[dict[str, Any]]:
        """Rescan peripherals and notify the server of changes."""
        loop = asyncio.get_running_loop()
        peripherals = await loop.run_in_executor(
            None,
            scan_all_peripherals,
            True,
        )
        if self._connected and self._ws is not None:
            try:
                await self._ws.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "method": "node.peripherals_changed",
                            "params": {
                                "peripherals": peripherals,
                                "scan_age_s": get_scan_age_s(),
                            },
                            "id": self._next_id(),
                        }
                    )
                )
                logger.info("peripherals_changed sent: %d devices", len(peripherals))
            except Exception as exc:
                logger.warning("failed to send peripherals_changed: %s", exc)
        return peripherals

    async def _heartbeat_loop(self) -> None:
        """Control plane heartbeat — runs independently of media plane."""
        interval = getattr(self, "_heartbeat_interval", self._config.signals.metrics_interval_s)
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

    async def _workspace_emission_loop(self) -> None:
        """Emit workstation state to VPS when it changes. Control plane signal."""
        if not self._config.signals.workspace_enabled:
            logger.info("workspace emission disabled by config")
            return

        interval = max(self._config.signals.workspace_debounce_s, 2.0)
        last_hash = ""
        loop = asyncio.get_running_loop()

        while True:
            await asyncio.sleep(interval)
            try:
                state = await loop.run_in_executor(None, collect_workstation_state)
                h = _state_hash(state)
                if h == last_hash:
                    continue
                last_hash = h
                state["device_id"] = self._config.node_id
                await self.emit_signal(
                    content_type="workstation.state",
                    payload=state,
                    signal_class="workstation_state",
                    urgency="LOW",
                )
            except Exception as exc:
                logger.debug("workspace emission failed: %s", exc)

    async def _handle_message(self, raw: str) -> None:
        msg = json.loads(raw)
        method = msg.get("method", "")

        if method == "capability.execute":
            asyncio.create_task(self._safe_handle_capability(msg))
        elif method == "outcome.notify":
            logger.info("outcome received: %s", msg.get("params", {}).get("summary", ""))
        elif "result" in msg or "error" in msg:
            pass
        else:
            logger.debug("unhandled message method: %s", method)

    def _effective_write_class(self, cap_name: str, wire_risk_class: str) -> bool:
        """Decide whether a capability is write-class for verdict purposes.

        Write-class if EITHER the caller-declared wire risk class OR the
        capability's own configured max_risk_class is not read-only. This stops
        a caller from downgrading a write-class capability to "read_only" to
        skip the verdict (fail-closed against risk downgrade).
        """
        from substrate.execution.mesh_verdict import is_write_class

        if is_write_class(wire_risk_class):
            return True
        adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
        cap_config = self._config.capabilities.get(adapter_key)
        if cap_config is not None and is_write_class(cap_config.max_risk_class):
            return True
        return False

    def _validate_verdict(
        self, cap_name: str, risk_class: str, verdict_token: str
    ) -> tuple[bool, str]:
        """Validate a governance verdict token before executing a capability.

        Read-only capabilities do not require a verdict. Write-class ones do:
        the token must be signed with the shared mesh verdict secret and bound
        to this node_id and this capability. Fail-closed — any failure to
        verify rejects execution.

        The verdict signer/verifier is the single canonical module shared with
        the orchestrator (substrate.execution.mesh_verdict).
        """
        try:
            from substrate.execution.mesh_verdict import (
                get_verdict_secret,
                verify_verdict,
            )
        except Exception as exc:  # pragma: no cover - defensive import guard
            # If the shared verifier cannot be imported, we cannot validate a
            # verdict — fail closed for anything that is not explicitly
            # read-only, allow read-only.
            if not self._effective_write_class(cap_name, risk_class):
                return True, "read-only (verifier unavailable)"
            return False, f"verdict verifier unavailable: {exc}"

        # A caller must NOT be able to skip the verdict by lying that a
        # write-class capability is read_only. The node classifies write-class
        # from the wire risk_class OR the capability's own configured max risk —
        # whichever is stricter (fail-closed against downgrade attacks).
        if not self._effective_write_class(cap_name, risk_class):
            return True, "read-only capability, no verdict required"

        if not get_verdict_secret():
            return False, "no mesh verdict secret configured on node (fail-closed)"
        if not verdict_token:
            return False, "write-class capability requires a governance verdict"

        check = verify_verdict(
            verdict_token,
            expected_node_id=self._config.node_id,
            expected_capability=cap_name,
        )
        if not check.valid:
            return False, check.reason
        return True, "verdict valid"

    async def _safe_handle_capability(self, msg: dict[str, Any]) -> None:
        try:
            await self._handle_capability(msg)
        except Exception as exc:
            logger.error("capability handler crashed: %s", exc, exc_info=True)
            msg_id = msg.get("id")
            if msg_id and self._ws:
                try:
                    await self._ws.send(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "result": {"success": False, "error": f"internal error: {exc}"},
                                "id": msg_id,
                            }
                        )
                    )
                except Exception:
                    pass

    async def _handle_capability(self, msg: dict[str, Any]) -> None:
        async with self._capability_semaphore:
            params = msg.get("params", {})
            msg_id = msg.get("id")
            cap_name = params.get("capability_name", "")
            cap_params = params.get("params", {})
            risk_class = params.get("risk_class", "REVERSIBLE_WRITE")
            verdict_token = params.get("governance_verdict_id", "")

            # Node-side verdict validation (fail-closed). A write-class
            # capability must carry a signed governance verdict bound to THIS
            # node and THIS capability. Missing or invalid verdict → reject
            # before touching any adapter. This is the last line of the mesh
            # trust boundary — the node never trusts the orchestrator blindly.
            verdict_ok, verdict_reason = self._validate_verdict(cap_name, risk_class, verdict_token)
            if not verdict_ok:
                logger.warning(
                    "capability %s rejected by node verdict gate: %s",
                    cap_name,
                    verdict_reason,
                )
                await self._ws.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "result": {
                                "success": False,
                                "error": f"node verdict rejected: {verdict_reason}",
                            },
                            "id": msg_id,
                        }
                    )
                )
                return

            adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
            cap_config = self._config.capabilities.get(adapter_key)
            if cap_config is None and adapter_key in self._adapters:
                cap_config = CapabilityConfig()
            # pass the ORIGINAL dotted name — governance normalizes it and
            # denies unknown operations (adapter_key stays for lookup only)
            allowed, reason = validate_request(cap_name, cap_params, risk_class, cap_config)

            if not allowed:
                logger.warning("capability %s denied: %s", cap_name, reason)
                await self._ws.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "result": {
                                "success": False,
                                "error": f"node governance denied: {reason}",
                            },
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
            _MAX_CAPABILITY_TIMEOUT_S = 300.0
            raw_timeout = params.get("timeout_seconds", _CONTROL_TIMEOUT_S)
            request_timeout = max(1.0, min(float(raw_timeout), _MAX_CAPABILITY_TIMEOUT_S))
            has_async = hasattr(adapter, "execute_async") and callable(adapter.execute_async)

            try:
                if has_async:
                    result = await asyncio.wait_for(
                        adapter.execute_async(cap_name, cap_params),
                        timeout=request_timeout,
                    )
                else:
                    loop = asyncio.get_event_loop()
                    executor = self._camera_executor if adapter_key == "camera" else None
                    if "timeout" not in cap_params and request_timeout > _CONTROL_TIMEOUT_S:
                        cap_params["timeout"] = int(request_timeout)
                    result = await asyncio.wait_for(
                        loop.run_in_executor(executor, adapter.execute, cap_name, cap_params),
                        timeout=request_timeout,
                    )
            except asyncio.TimeoutError:
                effective_timeout = request_timeout
                logger.warning("capability %s timed out after %.0fs", cap_name, effective_timeout)
                result = {"success": False, "error": f"{cap_name} timed out"}
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
        """Emit a signal to the VPS (control plane signals, not media frames)."""
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

            from nodes.windows.umh_node.subprocess_utils import no_window_kwargs

            result = subprocess.run(
                ["tailscale", "ip", "-4"],
                capture_output=True,
                text=True,
                timeout=3,
                **no_window_kwargs(),
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return ""
