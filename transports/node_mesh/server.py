"""Node Mesh WebSocket server — manages node connections and lifecycle.

Runs on a dedicated port (default 8094). Each connected node gets a
proxy IntegrationManifest registered through IntegrationRegistry,
making it a first-class integration indistinguishable from Notion/EOS.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, Callable
from uuid import uuid4

import websockets
from websockets.asyncio.server import ServerConnection

from substrate.execution.durable_remote_transport import (
    DurableRemoteStore,
    sha256_json,
    shell_running_identity_error,
    terminal_result_identity,
)
from substrate.execution.executor import WorkPacketExecutor
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.envelopes import ViewFrame
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.registry import IntegrationRegistry
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket
from transports.node_mesh.config import MeshConfig
from transports.node_mesh.metrics_buffer import MetricsBuffer, MetricsSnapshot
from transports.node_mesh.registry import ConnectedNode, NodeCapability, NodeRegistry, Peripheral

logger = logging.getLogger(__name__)

_DURABLE_CLAIM_PROOF_STATES = frozenset(
    {
        "CLAIMED",
        "RUNNING",
        "CANCEL_REQUESTED",
        "CANCELLED",
        "EXPIRED",
        "FAILED",
        "SUCCEEDED",
        "RECONCILIATION_REQUIRED",
    }
)
_DURABLE_PUMP_SCAN_LIMIT = 16
_DURABLE_DELIVERY_SUPPRESSION_MAX = 512
_DURABLE_DELIVERY_SUPPRESSION_DEFAULT_S = 30.0
_DURABLE_DELIVERY_SUPPRESSION_MIN_S = 8.0
_DURABLE_PUMP_TEARDOWN_S = 2.0


def hmac_compare(a: str, b: str) -> bool:
    """Constant-time token comparison (avoids timing side channels)."""
    import hmac as _hmac

    return _hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _durable_params(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ValueError("durable frame params must be an object")
    return params


def _durable_dict_field(params: dict[str, Any], field: str) -> dict[str, Any]:
    value = params.get(field)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"durable frame {field} must be an object")
    return dict(value)


class NodeMeshServer:
    """WebSocket server for the UMH node mesh."""

    def __init__(
        self,
        config: MeshConfig,
        executor: WorkPacketExecutor,
        signal_socket: SignalSocket,
        capability_socket: CapabilitySocket,
        outcome_socket: OutcomeSocket,
        view_socket: ViewSocket,
        pipeline_submit_fn: Callable[..., Any] | None = None,
        runtime_graph_hook: Callable[[str, list[str], str], None] | None = None,
    ) -> None:
        self._config = config
        self._executor = executor
        self._runtime_graph_hook = runtime_graph_hook
        self._registry = NodeRegistry(heartbeat_timeout_s=config.heartbeat_timeout_s)
        self._metrics = MetricsBuffer(
            buffer_size=config.buffer_size,
            flush_interval_s=config.flush_interval_s,
        )
        self._integration_registry = IntegrationRegistry(
            signal_socket,
            capability_socket,
            outcome_socket,
            view_socket,
        )
        self._view_socket = view_socket
        self._pipeline_submit_fn = pipeline_submit_fn
        self._frame_callback: Callable[..., None] | None = None
        self._workstation_callback: Callable[[str, dict[str, Any]], None] | None = None
        self._frame_queue: asyncio.Queue[tuple[str, dict[str, Any]]] | None = None
        self._frame_relay_url: str | None = None
        self._frame_relay_token: str = ""
        self._desktop_frame_queue: asyncio.Queue[tuple[str, dict[str, Any]]] | None = None
        self._desktop_relay_url: str | None = None
        self._desktop_relay_token: str = ""
        self._server: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()
        self._health_task: asyncio.Task[None] | None = None
        self._durable_store = DurableRemoteStore()
        self._durable_delivery_inflight: dict[str, dict[str, Any]] = {}
        self._durable_pump_tasks: dict[str, asyncio.Task[None]] = {}
        self._durable_pump_connections: dict[str, str] = {}
        self._ws_send_locks: dict[str, asyncio.Lock] = {}

    @property
    def node_registry(self) -> NodeRegistry:
        return self._registry

    @property
    def metrics_buffer(self) -> MetricsBuffer:
        return self._metrics

    def register_frame_callback(self, callback: Callable[..., None]) -> None:
        """Register a callback for camera frames: callback(node_id, payload_dict)."""
        self._frame_callback = callback

    def register_workstation_callback(
        self, callback: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Register a callback for workstation state: callback(node_id, payload)."""
        self._workstation_callback = callback

    def register_frame_relay(self, ws_url: str, token: str = "") -> None:
        """Enable persistent WS frame relay (replaces per-frame HTTP POST)."""
        self._frame_relay_url = ws_url
        self._frame_relay_token = token

    def register_desktop_relay(self, ws_url: str, token: str = "") -> None:
        """Enable persistent WS relay for desktop frames (separate from vision)."""
        self._desktop_relay_url = ws_url
        self._desktop_relay_token = token

    def start(self) -> threading.Thread:
        """Start the mesh server in a background thread."""
        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="node-mesh")
        self._thread.start()
        self._metrics.start_flush_loop()
        logger.info("node mesh server starting on port %d", self._config.port)
        return self._thread

    def stop(self) -> None:
        self._shutdown_event.set()
        self._metrics.stop_flush_loop()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("node mesh server stopped")

    def _emit_mesh_event(self, event_type: str, node: ConnectedNode) -> None:
        from datetime import datetime, timezone
        from uuid import uuid4

        frame = ViewFrame(
            frame_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            stage=0,
            data=node.to_api_dict(),
            integration_id=f"node-{node.node_id}",
        )
        try:
            self._view_socket.broadcast(frame)
        except Exception as exc:
            logger.debug("mesh event broadcast failed: %s", exc)

    @staticmethod
    def _task_done_cb(task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.error("background task %s failed: %s", task.get_name(), exc, exc_info=exc)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _frame_relay_ws_loop(self) -> None:
        """Persistent WS connection to relay for frame push.

        Drains _frame_queue, encodes each frame as:
          [4-byte big-endian meta_len][JSON meta][JPEG bytes]
        and sends as a single binary WS message.
        Reconnects on failure with backoff.
        """
        import base64 as _b64
        import struct as _struct

        assert self._frame_queue is not None
        assert self._frame_relay_url is not None

        backoff = 1.0
        while not self._shutdown_event.is_set():
            try:
                async with websockets.connect(
                    self._frame_relay_url,
                    max_size=4 * 1024 * 1024,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=2,
                ) as ws:
                    if self._frame_relay_token:
                        await ws.send(self._frame_relay_token)
                    ack = await asyncio.wait_for(ws.recv(), timeout=5)
                    if ack != "ok":
                        logger.warning("frame relay WS auth rejected: %s", ack)
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, 30)
                        continue

                    logger.info("frame relay WS connected to %s", self._frame_relay_url)
                    backoff = 1.0
                    frames_sent = 0

                    while not self._shutdown_event.is_set():
                        try:
                            node_id, payload = await asyncio.wait_for(
                                self._frame_queue.get(),
                                timeout=5.0,
                            )
                        except asyncio.TimeoutError:
                            continue

                        raw_msg = payload.get("__raw__")
                        if raw_msg is not None:
                            await ws.send(raw_msg)
                        else:
                            b64_data = payload.get("image_base64", "")
                            if not b64_data:
                                continue
                            try:
                                jpeg_bytes = _b64.b64decode(b64_data)
                            except Exception:
                                continue
                            meta = {k: v for k, v in payload.items() if k != "image_base64"}
                            meta["node_id"] = node_id
                            meta_bytes = json.dumps(meta).encode()
                            msg = _struct.pack(">I", len(meta_bytes)) + meta_bytes + jpeg_bytes
                            await ws.send(msg)

                        frames_sent += 1
                        if frames_sent <= 3 or frames_sent % 500 == 0:
                            logger.info("frame relay WS: %d frames sent", frames_sent)

            except websockets.ConnectionClosed as exc:
                logger.warning("frame relay WS closed: %s", exc)
            except Exception as exc:
                logger.warning("frame relay WS error: %s", exc)

            if not self._shutdown_event.is_set():
                logger.info("frame relay WS reconnecting in %.0fs...", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def _desktop_relay_ws_loop(self) -> None:
        """Persistent WS connection to desktop relay for frame push.

        Same protocol as _frame_relay_ws_loop but drains _desktop_frame_queue.
        """

        assert self._desktop_frame_queue is not None
        assert self._desktop_relay_url is not None

        backoff = 1.0
        while not self._shutdown_event.is_set():
            try:
                async with websockets.connect(
                    self._desktop_relay_url,
                    max_size=4 * 1024 * 1024,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=2,
                ) as ws:
                    if self._desktop_relay_token:
                        await ws.send(self._desktop_relay_token)
                    ack = await asyncio.wait_for(ws.recv(), timeout=5)
                    if ack != "ok":
                        logger.warning("desktop relay WS auth rejected: %s", ack)
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, 30)
                        continue

                    logger.info("desktop relay WS connected to %s", self._desktop_relay_url)
                    backoff = 1.0
                    frames_sent = 0

                    while not self._shutdown_event.is_set():
                        try:
                            node_id, payload = await asyncio.wait_for(
                                self._desktop_frame_queue.get(),
                                timeout=5.0,
                            )
                        except asyncio.TimeoutError:
                            continue

                        raw_msg = payload.get("__raw__")
                        if raw_msg is not None:
                            await ws.send(raw_msg)
                        else:
                            continue

                        frames_sent += 1
                        if frames_sent <= 3 or frames_sent % 500 == 0:
                            logger.info("desktop relay WS: %d frames sent", frames_sent)

            except websockets.ConnectionClosed as exc:
                logger.warning("desktop relay WS closed: %s", exc)
            except Exception as exc:
                logger.warning("desktop relay WS error: %s", exc)

            if not self._shutdown_event.is_set():
                logger.info("desktop relay WS reconnecting in %.0fs...", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def _serve(self) -> None:
        assert self._loop is not None
        self._health_task = self._loop.create_task(self._health_check_loop())
        self._vps_metrics_task = self._loop.create_task(self._vps_metrics_loop())
        self._http_task = self._loop.create_task(self._run_http_relay())
        self._http_task.add_done_callback(self._task_done_cb)

        if self._frame_relay_url:
            self._frame_queue = asyncio.Queue(maxsize=8)
            self._frame_relay_task = self._loop.create_task(self._frame_relay_ws_loop())
            self._frame_relay_task.add_done_callback(self._task_done_cb)
            logger.info("frame relay WS push enabled → %s", self._frame_relay_url)

        if self._desktop_relay_url:
            self._desktop_frame_queue = asyncio.Queue(maxsize=8)
            self._desktop_relay_task = self._loop.create_task(self._desktop_relay_ws_loop())
            self._desktop_relay_task.add_done_callback(self._task_done_cb)
            logger.info("desktop relay WS push enabled → %s", self._desktop_relay_url)

        async with websockets.serve(
            self._handle_connection,
            "0.0.0.0",
            self._config.port,
            ping_interval=120,
            ping_timeout=180,
            max_size=4 * 1024 * 1024,
        ) as server:
            self._server = server
            logger.info("node mesh server listening on :%d", self._config.port)
            while not self._shutdown_event.is_set():
                await asyncio.sleep(0.5)

            server.close()
            await server.wait_closed()

        for node_id in list(self._durable_pump_tasks):
            await self._stop_durable_pump(node_id)
        self._health_task.cancel()
        self._vps_metrics_task.cancel()
        self._http_task.cancel()
        if hasattr(self, "_frame_relay_task"):
            self._frame_relay_task.cancel()

    async def _handle_connection(self, ws: ServerConnection) -> None:
        """Handle a single node WebSocket connection."""
        node_id: str | None = None
        connection_id = uuid4().hex
        try:
            token = self._extract_token(ws)
            if not self._authenticate(token):
                await ws.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "error": {"code": -32000, "message": "authentication failed"},
                            "id": None,
                        }
                    )
                )
                await ws.close(4001, "authentication failed")
                return

            _binary_count = 0
            async for raw in ws:
                if isinstance(raw, bytes):
                    _binary_count += 1
                    if _binary_count <= 3 or _binary_count % 500 == 0:
                        logger.info(
                            "binary WS frame from %s: %d bytes (n=%d)",
                            node_id or "?",
                            len(raw),
                            _binary_count,
                        )
                    if node_id and len(raw) > 6:
                        # A node that streams ONLY binary frames (desktop/camera
                        # capture) sends no JSON heartbeat, so the registry used
                        # to evict it after heartbeat_timeout_s while its socket
                        # stayed ESTABLISHED — and because the socket never
                        # dropped, the daemon never reconnected or re-registered.
                        # Dispatch then refused a demonstrably live node with
                        # "node not connected" (Beast, 2026-08-05 00:41:30).
                        #
                        # Refresh ONLY on a frame the normal handler ACCEPTED,
                        # and only for THIS connection's authenticated node_id
                        # (node_id is None until node.hello binds it, so an
                        # unauthenticated or unregistered socket can never reach
                        # here). update_heartbeat() is the authoritative
                        # registry write and returns False for an unknown node —
                        # that refusal is surfaced, never swallowed.
                        proves_liveness = self._frame_proves_liveness(raw)
                        forwarded = self._handle_binary_frame(node_id, raw)
                        # BOTH gates: the frame must prove a working capture
                        # pipeline (unforgeable) AND be accepted by the normal
                        # handler. Forwarding tolerance alone is NOT proof of
                        # life — b"\x00" * 7 forwards fine but proves nothing.
                        if proves_liveness and forwarded:
                            if not self._registry.update_heartbeat(
                                node_id, connection_id=connection_id
                            ):
                                logger.warning(
                                    "binary-frame heartbeat refused: %s not in registry",
                                    node_id,
                                )
                            else:
                                await self._schedule_durable_pump(
                                    node_id,
                                    ws,
                                    connection_id,
                                    reason="binary_liveness",
                                )
                    continue

                msg = json.loads(raw)
                method = msg.get("method", "")
                params = msg.get("params", {})
                msg_id = msg.get("id")

                if method == "node.hello":
                    node_id = await self._handle_hello(
                        ws, params, msg_id, token, connection_id
                    )
                elif method == "node.heartbeat" and node_id:
                    await self._handle_heartbeat(node_id, params, msg_id, ws, connection_id)
                elif method == "durable_command.claimed" and node_id:
                    await self._handle_durable_claimed(
                        node_id, params, msg_id, ws, connection_id
                    )
                elif method == "durable_command.claim_state" and node_id:
                    await self._handle_durable_claim_state(
                        node_id, params, msg_id, ws, connection_id
                    )
                elif method == "durable_command.result" and node_id:
                    await self._handle_durable_result(
                        node_id, params, msg_id, ws, connection_id
                    )
                elif method == "node.capabilities_changed" and node_id:
                    await self._handle_capabilities_changed(
                        node_id, params, ws, connection_id
                    )
                elif method == "node.peripherals_changed" and node_id:
                    await self._handle_peripherals_changed(node_id, params, connection_id)
                elif method == "signal.emit" and node_id:
                    await self._handle_signal(node_id, params, msg_id, ws, connection_id)
                elif not method and ("result" in msg or "error" in msg):
                    self._resolve_pending_dispatch(msg)
                else:
                    if msg_id is not None:
                        await self._send_ws_json(
                            ws,
                            {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32601,
                                    "message": f"unknown method: {method}",
                                },
                                "id": msg_id,
                            },
                            connection_id,
                        )

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as exc:
            logger.error("node connection error: %s", exc)
        finally:
            if node_id:
                self._unregister_node(node_id, connection_id=connection_id)
            if node_id:
                await self._stop_durable_pump(node_id, connection_id=connection_id)
            if connection_id:
                self._ws_send_locks.pop(connection_id, None)

    @staticmethod
    def _frame_proves_liveness(raw: bytes) -> bool:
        """Strict predicate: does this frame PROVE a working capture pipeline?

        Deliberately separate from forwarding acceptance. Forwarding is
        permissive by design — a frame whose meta is unparseable is still
        relayed with ``meta = {}``. Liveness is the opposite: it must be
        impossible to forge, because it decides whether dispatch will route real
        work to this node.

        Reusing forwarding-tolerance as proof of life is what made
        ``b"\\x00" * 7`` a valid heartbeat: ``meta_len == 0`` clears both bounds
        checks, ``json.loads(raw[4:4])`` raises, degrades to ``{}``, and the
        frame "succeeds". A node whose capture thread is dead but whose socket
        still emits padding would then be advertised as live forever — a
        fail-OPEN inversion of the eviction bug this path exists to fix.

        Requires: a non-empty meta block that parses to a JSON object, plus a
        non-empty payload after it.
        """
        import struct as _struct

        if len(raw) < 8:
            return False
        try:
            meta_len = _struct.unpack(">I", raw[:4])[0]
        except Exception:
            return False
        if meta_len == 0 or meta_len > 65536 or 4 + meta_len >= len(raw):
            return False
        try:
            meta = json.loads(raw[4 : 4 + meta_len])
        except Exception:
            return False
        return isinstance(meta, dict)

    def _handle_binary_frame(self, node_id: str, raw: bytes) -> bool:
        """Handle binary camera frame from Beast — forward to relay queue.

        Wire format: [4-byte meta_len][JSON meta][JPEG bytes]
        Same format as the relay ingest WS, so forward directly.

        Returns True when the frame was well-formed enough to FORWARD. This is
        NOT the liveness signal — see ``_frame_proves_liveness`` for that, and do
        not conflate the two: forwarding is intentionally tolerant, liveness must
        be unforgeable.
        """
        import struct as _struct

        meta_len = _struct.unpack(">I", raw[:4])[0]
        if meta_len > 65536 or 4 + meta_len > len(raw):
            return False
        try:
            meta = json.loads(raw[4 : 4 + meta_len])
        except Exception:
            meta = {}
        meta["node_id"] = node_id

        source = meta.get("source", "camera")
        meta_bytes = json.dumps(meta).encode()
        fwd = _struct.pack(">I", len(meta_bytes)) + meta_bytes + raw[4 + meta_len :]

        if source == "desktop" and self._desktop_frame_queue is not None:
            try:
                self._desktop_frame_queue.put_nowait(("__binary__", {"__raw__": fwd}))
            except asyncio.QueueFull:
                pass
        elif self._frame_queue is not None:
            try:
                self._frame_queue.put_nowait(("__binary__", {"__raw__": fwd}))
            except asyncio.QueueFull:
                pass
        elif self._frame_callback is not None:
            import base64 as _b64

            jpeg_bytes = raw[4 + meta_len :]
            payload = dict(meta)
            payload["image_base64"] = _b64.b64encode(jpeg_bytes).decode("ascii")
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, self._frame_callback, node_id, payload)
        return True

    def _resolve_pending_dispatch(self, msg: dict[str, Any]) -> None:
        """Route JSON-RPC responses back to pending HTTP dispatch futures."""
        msg_id = str(msg.get("id", ""))
        if not msg_id:
            return
        pending = getattr(self, "_pending_http", {})
        future = pending.pop(msg_id, None)
        if future is None:
            return
        result = msg.get("result", msg.get("error", {}))
        if not future.done():
            future.set_result(result)

    def _extract_token(self, ws: ServerConnection) -> str:
        """Read the node auth token from the request.

        Preferred transport: an Authorization: Bearer <token> header (or the
        X-UMH-Mesh-Token header). The token is NEVER logged. A legacy query
        string (?token=) is still read for backward compatibility with nodes
        that have not yet been upgraded, but this path is deprecated because
        query strings leak into access logs.
        """
        request = ws.request
        headers = getattr(request, "headers", None) if request else None
        if headers is not None:
            auth = headers.get("authorization") or headers.get("Authorization") or ""
            if auth[:7].lower() == "bearer ":
                return auth[7:].strip()
            mesh_hdr = headers.get("x-umh-mesh-token") or headers.get("X-UMH-Mesh-Token")
            if mesh_hdr:
                return mesh_hdr.strip()

        path = request.path if request else ""
        if "?" in path:
            query = path.split("?", 1)[1]
            for part in query.split("&"):
                if part.startswith("token="):
                    return part[6:]
        return ""

    def _authenticate(self, token: str) -> bool:
        """Authenticate a node token. FAIL CLOSED.

        When no tokens are configured the mesh refuses every connection — an
        unconfigured mesh must not accept anonymous nodes. A configured mesh
        accepts only a token that matches a registered node entry.
        """
        if not self._config.node_tokens:
            logger.error(
                "mesh WS auth fail-closed: no node tokens configured — refusing connection"
            )
            return False
        if not token:
            return False
        return any(hmac_compare(nt.token, token) for nt in self._config.node_tokens.values())

    def _node_id_for_token(self, token: str) -> str | None:
        if not token:
            return None
        for nt in self._config.node_tokens.values():
            if hmac_compare(nt.token, token):
                return nt.node_id
        return None

    def _http_authenticated_node_id(self, auth_header: str) -> str | None:
        if not auth_header or auth_header[:7].lower() != "bearer ":
            return None
        token = auth_header[7:].strip()
        relay_secret = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()
        if relay_secret and hmac_compare(token, relay_secret):
            return "*"
        return self._node_id_for_token(token)

    async def _handle_hello(
        self,
        ws: ServerConnection,
        params: dict[str, Any],
        msg_id: Any,
        token: str = "",
        connection_id: str = "",
    ) -> str:
        node_id = params.get("node_id", "unknown")

        # Token → node binding. The node_id is self-declared in the hello
        # payload, so it MUST be checked against the node this token is bound
        # to. A token issued for node A must never register as node B. When
        # tokens are configured, a token that is not bound to any node, or is
        # bound to a different node than declared, is rejected (fail-closed).
        if self._config.node_tokens:
            bound_node_id = self._node_id_for_token(token)
            if bound_node_id is None or bound_node_id != node_id:
                logger.error(
                    "mesh hello rejected: token/node binding mismatch (declared=%s bound=%s)",
                    node_id,
                    bound_node_id,
                )
                await ws.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32001,
                                "message": "token not bound to declared node_id",
                            },
                            "id": msg_id,
                        }
                    )
                )
                await ws.close(4003, "token/node binding mismatch")
                return node_id

        if self._registry.node_count() >= self._config.max_nodes:
            existing = self._registry.get(node_id)
            if existing is None:
                await ws.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "error": {"code": -32000, "message": "max nodes reached"},
                            "id": msg_id,
                        }
                    )
                )
                return node_id

        if self._registry.get(node_id) is not None:
            existing = self._registry.get(node_id)
            self._unregister_node(
                node_id,
                connection_id=existing.connection_id if existing is not None else None,
            )

        caps = [
            NodeCapability(
                name=c.get("name", ""),
                category=c.get("category", "system"),
                risk_class=c.get("risk_class", "READ_ONLY"),
                max_risk_class=c.get("max_risk_class", "REVERSIBLE_WRITE"),
            )
            for c in params.get("capabilities", [])
        ]

        peripherals = [Peripheral.from_dict(p) for p in params.get("peripherals", [])]

        node = ConnectedNode(
            node_id=node_id,
            hostname=params.get("hostname", "unknown"),
            os=params.get("os", "unknown"),
            os_version=params.get("os_version", ""),
            capabilities=caps,
            daemon_version=params.get("daemon_version", "0.0.0"),
            tailscale_ip=params.get("tailscale_ip", ""),
            ws=ws,
            connection_id=connection_id,
            peripherals=peripherals,
        )

        self._registry.add(node)
        self._register_integration(node)

        if self._runtime_graph_hook is not None:
            cap_names = [c.name for c in caps]
            try:
                self._runtime_graph_hook(node_id, cap_names, "connect")
            except Exception as exc:
                logger.warning("runtime graph hook (connect) failed: %s", exc)

        await ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "result": {
                        "accepted": True,
                        "server_version": "0.1.0",
                        "heartbeat_interval_s": self._config.heartbeat_interval_s,
                    },
                    "id": msg_id,
                }
            )
        )

        self._emit_mesh_event("mesh.node_connected", node)
        logger.info(
            "node connected: %s (%s %s, %d peripherals)",
            node_id,
            node.os,
            node.hostname,
            len(node.peripherals),
        )
        await self._schedule_durable_pump(node_id, ws, connection_id, reason="hello")
        return node_id

    async def _handle_heartbeat(
        self,
        node_id: str,
        params: dict[str, Any],
        msg_id: Any,
        ws: ServerConnection,
        connection_id: str = "",
    ) -> None:
        metrics = params.get("metrics", {})
        if not self._registry.update_heartbeat(node_id, metrics, connection_id=connection_id):
            logger.warning("heartbeat refused: %s not owned by this connection", node_id)
            if msg_id is not None:
                await self._send_ws_json(
                    ws,
                    {
                        "jsonrpc": "2.0",
                        "result": {"ack": False, "error": "stale node connection"},
                        "id": msg_id,
                    },
                    connection_id,
                )
            return

        if self._runtime_graph_hook is not None:
            try:
                self._runtime_graph_hook(node_id, [], "heartbeat")
            except Exception as exc:
                logger.debug("runtime graph hook (heartbeat) failed: %s", exc)

        from datetime import datetime, timezone

        snapshot = MetricsSnapshot(
            node_id=node_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu=metrics.get("cpu"),
            memory=metrics.get("memory"),
            disk=metrics.get("disk"),
            battery=metrics.get("battery"),
            network_io=metrics.get("network_io", {}),
            gpu=metrics.get("gpu"),
        )
        self._metrics.record(snapshot)
        self._write_metrics_snapshot()

        self._check_anomalies(node_id, metrics)

        node = self._registry.get(node_id)
        if node:
            self._emit_mesh_event("mesh.node_heartbeat", node)

        if msg_id is not None:
            await self._send_ws_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "result": {"ack": True},
                    "id": msg_id,
                },
                connection_id,
            )
        await self._schedule_durable_pump(node_id, ws, connection_id, reason="heartbeat")

    async def _send_ws_json(
        self,
        ws: ServerConnection,
        message: dict[str, Any],
        connection_id: str = "",
    ) -> None:
        """Serialize sends per connection without blocking the receive handler on pump scans."""
        if not connection_id:
            await ws.send(json.dumps(message))
            return
        lock = self._ws_send_locks.setdefault(connection_id, asyncio.Lock())
        async with lock:
            await ws.send(json.dumps(message))

    def _durable_transport_identity(self, req: Any) -> dict[str, str]:
        return {
            "request_id": str(getattr(req, "request_id", "")),
            "correlation_id": str(getattr(req, "correlation_id", "")),
            "node_id": str(getattr(req, "node_id", "")),
            "candidate_sha": str(getattr(req, "candidate_sha", "")),
            "idempotency_key": str(getattr(req, "idempotency_key", "")),
            "payload_digest": str(getattr(req, "payload_digest", "")),
        }

    @staticmethod
    def _same_durable_transport_identity(entry: dict[str, Any], req: Any) -> bool:
        identity = entry.get("identity")
        if not isinstance(identity, dict):
            return False
        expected = {
            "request_id": str(getattr(req, "request_id", "")),
            "correlation_id": str(getattr(req, "correlation_id", "")),
            "node_id": str(getattr(req, "node_id", "")),
            "candidate_sha": str(getattr(req, "candidate_sha", "")),
            "idempotency_key": str(getattr(req, "idempotency_key", "")),
            "payload_digest": str(getattr(req, "payload_digest", "")),
        }
        return all(str(identity.get(key, "")) == value for key, value in expected.items())

    @staticmethod
    def _durable_delivery_suppression_seconds(req: Any) -> float:
        budgets = getattr(req, "params", {}).get("budgets", {})
        if not isinstance(budgets, dict):
            budgets = {}
        raw_claim = budgets.get("claim_acquisition_timeout_s", None)
        try:
            claim_budget = float(raw_claim)
        except (TypeError, ValueError):
            claim_budget = _DURABLE_DELIVERY_SUPPRESSION_DEFAULT_S
        if claim_budget <= 0:
            claim_budget = _DURABLE_DELIVERY_SUPPRESSION_DEFAULT_S
        return max(
            _DURABLE_DELIVERY_SUPPRESSION_MIN_S,
            min(_DURABLE_DELIVERY_SUPPRESSION_DEFAULT_S, claim_budget),
        )

    def _record_durable_delivery_progress(
        self,
        request_id: str,
        event: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            self._durable_store.record_transport_diagnostic(request_id, event, payload)
        except Exception as exc:  # noqa: BLE001
            logger.debug("durable transport diagnostic failed for %s: %s", request_id, exc)

    def _clear_durable_delivery_inflight(self, request_id: str, reason: str) -> None:
        if request_id in self._durable_delivery_inflight:
            self._durable_delivery_inflight.pop(request_id, None)
            self._record_durable_delivery_progress(
                request_id,
                "delivery_inflight_cleared",
                {"reason": reason},
            )

    def _durable_delivery_suppressed(self, req: Any, current: float) -> bool:
        entry = self._durable_delivery_inflight.get(str(getattr(req, "request_id", "")))
        if not entry:
            return False
        if not self._same_durable_transport_identity(entry, req):
            self._clear_durable_delivery_inflight(
                str(getattr(req, "request_id", "")),
                "identity_changed",
            )
            return False
        if str(getattr(req, "lifecycle_state", "")).upper() != "QUEUED":
            self._clear_durable_delivery_inflight(
                str(getattr(req, "request_id", "")),
                "canonical_progress",
            )
            return False
        if current >= float(entry.get("suppress_until", 0.0)):
            self._clear_durable_delivery_inflight(
                str(getattr(req, "request_id", "")),
                "suppression_expired",
            )
            return False
        self._record_durable_delivery_progress(
            str(getattr(req, "request_id", "")),
            "delivery_suppressed",
            {
                "reason": "inflight_same_request",
                "suppress_until": entry.get("suppress_until"),
                "connection_id": entry.get("connection_id", ""),
            },
        )
        return True

    def _trim_durable_delivery_inflight(self) -> None:
        if len(self._durable_delivery_inflight) <= _DURABLE_DELIVERY_SUPPRESSION_MAX:
            return
        items = sorted(
            self._durable_delivery_inflight.items(),
            key=lambda item: float(item[1].get("sent_at", 0.0)),
        )
        overflow = len(items) - _DURABLE_DELIVERY_SUPPRESSION_MAX
        for request_id, _entry in items[:overflow]:
            self._clear_durable_delivery_inflight(request_id, "bounded_eviction")

    async def _stop_durable_pump(
        self,
        node_id: str,
        *,
        connection_id: str | None = None,
    ) -> None:
        if connection_id is not None and self._durable_pump_connections.get(node_id) != connection_id:
            return
        task = self._durable_pump_tasks.get(node_id)
        if task is None:
            return
        if not task.done():
            task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=_DURABLE_PUMP_TEARDOWN_S)
        except asyncio.CancelledError:
            pass
        except asyncio.TimeoutError as exc:
            raise RuntimeError("durable pump teardown exceeded bounded deadline") from exc
        if self._durable_pump_tasks.get(node_id) is task:
            self._durable_pump_tasks.pop(node_id, None)
            self._durable_pump_connections.pop(node_id, None)

    async def _schedule_durable_pump(
        self,
        node_id: str,
        ws: ServerConnection,
        connection_id: str,
        *,
        reason: str,
    ) -> None:
        existing = self._durable_pump_tasks.get(node_id)
        if existing is not None and not existing.done():
            if self._durable_pump_connections.get(node_id) == connection_id:
                return
            await self._stop_durable_pump(node_id)

        async def _runner() -> None:
            try:
                await self._pump_durable_requests(node_id, ws, connection_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("durable pump failed for %s (%s): %s", node_id, reason, exc)

        task = asyncio.create_task(_runner())
        self._durable_pump_tasks[node_id] = task
        self._durable_pump_connections[node_id] = connection_id

        def _cleanup(done: asyncio.Task[None]) -> None:
            if self._durable_pump_tasks.get(node_id) is done:
                self._durable_pump_tasks.pop(node_id, None)
                self._durable_pump_connections.pop(node_id, None)

        task.add_done_callback(_cleanup)

    async def _pump_durable_requests(
        self, node_id: str, ws: ServerConnection, connection_id: str = ""
    ) -> None:
        """Deliver persisted remote requests to a connected node.

        Delivery is deliberately idempotent: the node owns claim/execution
        deduplication by request_id, and the controller store remains the source
        of truth if the socket drops before a terminal result is observed.
        """
        if connection_id and not self._registry.owns(node_id, connection_id):
            logger.warning("durable delivery refused: %s not owned by this connection", node_id)
            return
        current = time.time()
        sent = 0
        for req in self._durable_store.deliverable_for_node(
            node_id,
            limit=_DURABLE_PUMP_SCAN_LIMIT,
        ):
            request_id = req.request_id
            if self._durable_delivery_suppressed(req, current):
                continue
            try:
                suppression_s = self._durable_delivery_suppression_seconds(req)
                suppress_until = current + suppression_s
                self._durable_delivery_inflight[request_id] = {
                    "identity": self._durable_transport_identity(req),
                    "sent_at": current,
                    "suppress_until": suppress_until,
                    "connection_id": connection_id,
                    "node_id": node_id,
                    "transport_coordination_only": True,
                }
                self._trim_durable_delivery_inflight()
                self._record_durable_delivery_progress(
                    request_id,
                    "delivery_frame_queued",
                    {
                        "node_id": node_id,
                        "connection_id": connection_id,
                        "suppression_s": suppression_s,
                        "suppress_until": suppress_until,
                        "canonical_lifecycle": req.lifecycle_state,
                        "transport_coordination_only": True,
                    },
                )
                await self._send_ws_json(
                    ws,
                    {
                        "jsonrpc": "2.0",
                        "method": "durable_command.request",
                        "params": req.to_dict(),
                        "id": f"durable-{request_id}",
                    },
                    connection_id,
                )
                self._record_durable_delivery_progress(
                    request_id,
                    "delivery_frame_sent",
                    {
                        "node_id": node_id,
                        "connection_id": connection_id,
                        "canonical_lifecycle": req.lifecycle_state,
                    },
                )
                delivered = self._durable_store.mark_delivered(request_id)
                self._record_durable_delivery_progress(
                    request_id,
                    "delivery_marked",
                    {
                        "delivery_attempts": delivered.delivery_attempts,
                        "canonical_lifecycle": delivered.lifecycle_state,
                    },
                )
                sent += 1
            except Exception as exc:
                self._clear_durable_delivery_inflight(request_id, "send_failed")
                logger.warning("durable request delivery failed for %s: %s", request_id, exc)
                return
            if sent >= 1:
                break

    async def _handle_durable_claimed(
        self,
        node_id: str,
        params: dict[str, Any],
        msg_id: Any,
        ws: ServerConnection,
        connection_id: str = "",
    ) -> None:
        request_id = ""
        claim_id = ""
        state = "CLAIMED"
        result: dict[str, Any] = {
            "ok": False,
            "accepted": False,
            "error": "",
            "request_id": request_id,
            "correlation_id": "",
            "candidate_sha": "",
            "node_id": node_id,
            "claim_id": "",
            "lifecycle_state": "",
            "lease_expires_at": 0.0,
            "process_tree": {},
            "authority_source": "vps_canonical_durable_store",
        }
        try:
            params = _durable_params(params)
            request_id = str(params.get("request_id", "") or "").strip()
            claim_id = str(params.get("claim_id", "") or "").strip()
            state = str(params.get("state", "CLAIMED") or "CLAIMED").upper()
            process_tree = _durable_dict_field(params, "process_tree")
            result["request_id"] = request_id
            result["claim_id"] = claim_id
            self._record_durable_delivery_progress(
                request_id,
                "durable_control_frame_received",
                {
                    "method": "durable_command.claimed",
                    "node_id": node_id,
                    "claim_id": claim_id,
                    "state": state,
                    "connection_id": connection_id,
                },
            )
            self._record_durable_delivery_progress(
                request_id,
                "inbound_handler_entered",
                {"method": "durable_command.claimed", "state": state},
            )
            if connection_id and not self._registry.owns(node_id, connection_id):
                result["error"] = "stale node connection"
                raise RuntimeError(result["error"])
            req = self._durable_store.get_request(request_id)
            if req is None or req.node_id != node_id:
                result["error"] = "request not found for node"
            elif state not in {"CLAIMED", "RUNNING"}:
                result["error"] = "unsupported claim state"
            elif state == "RUNNING":
                self._record_durable_delivery_progress(
                    request_id,
                    "canonical_write_started",
                    {"method": "durable_command.claimed", "state": "RUNNING"},
                )
                identity_error = shell_running_identity_error(
                    req,
                    claim_id=claim_id,
                    process_tree=process_tree,
                )
                if identity_error:
                    updated = self._durable_store.mark_reconciliation_required(
                        request_id,
                        reason=identity_error,
                        cleanup={
                            "process_residue": [
                                {
                                    "pid": process_tree.get("root_pid"),
                                    "state": "shell_running_identity_rejected",
                                }
                            ],
                            "execution_outcome_unknown": True,
                            "duplicate_launch_fenced": True,
                        },
                    )
                else:
                    updated = self._durable_store.mark_running(
                        request_id, claim_id=claim_id, process_tree=process_tree
                    )
                self._record_durable_delivery_progress(
                    request_id,
                    "canonical_write_completed",
                    {
                        "method": "durable_command.claimed",
                        "state": updated.lifecycle_state,
                        "claim_id": updated.claim_id,
                    },
                )
                result.update(
                    {
                        "request_id": updated.request_id,
                        "correlation_id": updated.correlation_id,
                        "candidate_sha": updated.candidate_sha,
                        "node_id": updated.node_id,
                        "claim_id": updated.claim_id,
                        "lifecycle_state": updated.lifecycle_state,
                        "lease_expires_at": updated.lease_expires_at,
                        "process_tree": updated.process_tree,
                    }
                )
                result["ok"] = updated.lifecycle_state == "RUNNING" and updated.claim_id == claim_id
                result["accepted"] = result["ok"]
                if not result["ok"]:
                    result["error"] = f"claim rejected into {updated.lifecycle_state}"
            else:
                self._record_durable_delivery_progress(
                    request_id,
                    "canonical_write_started",
                    {"method": "durable_command.claimed", "state": "CLAIMED"},
                )
                updated = self._durable_store.mark_claimed(
                    request_id, claim_id=claim_id, process_tree=process_tree
                )
                self._record_durable_delivery_progress(
                    request_id,
                    "canonical_write_completed",
                    {
                        "method": "durable_command.claimed",
                        "state": updated.lifecycle_state,
                        "claim_id": updated.claim_id,
                    },
                )
                result.update(
                    {
                        "request_id": updated.request_id,
                        "correlation_id": updated.correlation_id,
                        "candidate_sha": updated.candidate_sha,
                        "node_id": updated.node_id,
                        "claim_id": updated.claim_id,
                        "lifecycle_state": updated.lifecycle_state,
                        "lease_expires_at": updated.lease_expires_at,
                        "process_tree": updated.process_tree,
                    }
                )
                result["ok"] = (
                    updated.claim_id == claim_id
                    and updated.lifecycle_state in _DURABLE_CLAIM_PROOF_STATES
                )
                result["accepted"] = result["ok"]
                if not result["ok"]:
                    result["error"] = f"claim rejected into {updated.lifecycle_state}"
        except Exception as exc:  # noqa: BLE001
            result["ok"] = False
            result["accepted"] = False
            result["error"] = str(exc)
        if msg_id is not None:
            self._record_durable_delivery_progress(
                request_id,
                "ack_constructed",
                {
                    "method": "durable_command.claimed",
                    "ok": result.get("ok"),
                    "accepted": result.get("accepted"),
                    "lifecycle_state": result.get("lifecycle_state", ""),
                },
            )
            await self._send_ws_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": msg_id,
                },
                connection_id,
            )
            self._record_durable_delivery_progress(
                request_id,
                "ack_sent",
                {"method": "durable_command.claimed", "ok": result.get("ok")},
            )
        if result.get("accepted"):
            self._clear_durable_delivery_inflight(request_id, f"canonical_{state.lower()}")

    async def _handle_durable_claim_state(
        self,
        node_id: str,
        params: dict[str, Any],
        msg_id: Any,
        ws: ServerConnection,
        connection_id: str = "",
    ) -> None:
        request_id = str(params.get("request_id", ""))
        result: dict[str, Any] = {
            "ok": False,
            "accepted": False,
            "error": "",
            "request_id": request_id,
            "correlation_id": "",
            "candidate_sha": "",
            "node_id": node_id,
            "claim_id": "",
            "lifecycle_state": "",
            "lease_expires_at": 0.0,
            "process_tree": {},
            "authority_source": "vps_canonical_durable_store",
        }
        self._record_durable_delivery_progress(
            request_id,
            "claim_state_read_received",
            {
                "node_id": node_id,
                "connection_id": connection_id,
                "claim_id": str(params.get("claim_id", "")),
                "state": str(params.get("state", "CLAIMED")).upper(),
            },
        )
        self._record_durable_delivery_progress(
            request_id,
            "inbound_handler_entered",
            {"method": "durable_command.claim_state"},
        )
        try:
            if connection_id and not self._registry.owns(node_id, connection_id):
                result["error"] = "stale node connection"
                raise RuntimeError(result["error"])
            result = self._canonical_durable_claim_state(node_id, params)
        except Exception as exc:  # noqa: BLE001
            result["ok"] = False
            result["accepted"] = False
            result["error"] = str(exc)
        if msg_id is not None:
            await self._send_ws_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": msg_id,
                },
                connection_id,
            )
            self._record_durable_delivery_progress(
                request_id,
                "claim_state_response_sent",
                {
                    "ok": result.get("ok"),
                    "accepted": result.get("accepted"),
                    "lifecycle_state": result.get("lifecycle_state", ""),
                },
            )

    def _canonical_durable_claim_state(
        self,
        node_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        request_id = str(params.get("request_id", ""))
        correlation_id = str(params.get("correlation_id", ""))
        candidate_sha = str(params.get("candidate_sha", ""))
        claim_id = str(params.get("claim_id", ""))
        expected_state = str(params.get("state", "CLAIMED")).upper()
        result: dict[str, Any] = {
            "ok": False,
            "accepted": False,
            "error": "",
            "request_id": request_id,
            "correlation_id": "",
            "candidate_sha": "",
            "node_id": node_id,
            "claim_id": "",
            "lifecycle_state": "",
            "lease_expires_at": 0.0,
            "process_tree": {},
            "authority_source": "vps_canonical_durable_store",
        }
        req = self._durable_store.get_request(request_id)
        if req is None:
            result["error"] = "request not found"
            return result
        if req.node_id != node_id:
            result["error"] = "request not found for node"
            return result
        if not self._durable_store.is_canonical_request(req):
            result["error"] = "request is not canonical for idempotency"
            return result
        result.update(
            {
                "request_id": req.request_id,
                "correlation_id": req.correlation_id,
                "candidate_sha": req.candidate_sha,
                "node_id": req.node_id,
                "claim_id": req.claim_id,
                "lifecycle_state": req.lifecycle_state,
                "lease_expires_at": req.lease_expires_at,
                "process_tree": req.process_tree,
            }
        )
        mismatches: list[str] = []
        if not correlation_id or req.correlation_id != correlation_id:
            mismatches.append("correlation_id")
        if not candidate_sha or req.candidate_sha != candidate_sha:
            mismatches.append("candidate_sha")
        if not claim_id or req.claim_id != claim_id:
            mismatches.append("claim_id")
        if expected_state not in {"CLAIMED", "RUNNING"}:
            mismatches.append("state")
        elif expected_state == "CLAIMED":
            if req.lifecycle_state not in _DURABLE_CLAIM_PROOF_STATES:
                mismatches.append("lifecycle_state")
        elif req.lifecycle_state != expected_state:
            mismatches.append("lifecycle_state")
        if mismatches:
            result["error"] = "claim mismatch: " + ",".join(mismatches)
            return result
        result["ok"] = True
        result["accepted"] = True
        return result

    async def _handle_durable_result(
        self,
        node_id: str,
        params: dict[str, Any],
        msg_id: Any,
        ws: ServerConnection,
        connection_id: str = "",
    ) -> None:
        request_id = ""
        claim_id = ""
        state = "FAILED"
        result: dict[str, Any] = {}
        cleanup: dict[str, Any] = {}
        incoming_digest = ""
        receipt: dict[str, Any] = {}
        ok = False
        error = ""
        try:
            params = _durable_params(params)
            request_id = str(params.get("request_id", "") or "").strip()
            claim_id = str(params.get("claim_id", "") or "").strip()
            state = str(params.get("state", "FAILED") or "FAILED").upper()
            result = _durable_dict_field(params, "result")
            cleanup = _durable_dict_field(params, "cleanup")
            incoming_result_id = str(params.get("result_id", "") or "").strip()
            incoming_digest = sha256_json(
                {"state": state, "claim_id": claim_id, "result": result, "cleanup": cleanup}
            )
            self._record_durable_delivery_progress(
                request_id,
                "durable_control_frame_received",
                {
                    "method": "durable_command.result",
                    "node_id": node_id,
                    "claim_id": claim_id,
                    "state": state,
                    "connection_id": connection_id,
                },
            )
            self._record_durable_delivery_progress(
                request_id,
                "inbound_handler_entered",
                {"method": "durable_command.result", "state": state},
            )
            if connection_id and not self._registry.owns(node_id, connection_id):
                error = "stale node connection"
                raise RuntimeError(error)
            req = self._durable_store.get_request(request_id)
            if req is None or req.node_id != node_id:
                error = "request not found for node"
            else:
                prior_lifecycle_state = req.lifecycle_state
                result_identity = terminal_result_identity(
                    req,
                    {
                        "claim_id": claim_id,
                        "state": state,
                        "result_digest": incoming_digest,
                        "cleanup_digest": sha256_json(cleanup),
                    },
                )
                identity_mismatches = [
                    key
                    for key in ("correlation_id", "candidate_sha", "node_id")
                    if str(params.get(key, "") or "") != str(result_identity[key])
                ]
                if not incoming_result_id:
                    identity_mismatches.append("result_id")
                elif incoming_result_id != result_identity["result_id"]:
                    identity_mismatches.append("result_id")
                if identity_mismatches:
                    raise ValueError(
                        "terminal result identity mismatch: "
                        + ",".join(identity_mismatches)
                    )
                self._record_durable_delivery_progress(
                    request_id,
                    "canonical_write_started",
                    {"method": "durable_command.result", "state": state},
                )
                updated = self._durable_store.publish_result(
                    request_id,
                    claim_id=claim_id,
                    state=state,
                    result=result,
                    cleanup=cleanup,
                )
                self._record_durable_delivery_progress(
                    request_id,
                    "canonical_write_completed",
                    {
                        "method": "durable_command.result",
                        "state": updated.lifecycle_state,
                        "claim_id": updated.claim_id,
                    },
                )
                if (
                    updated.lifecycle_state == "RECONCILIATION_REQUIRED"
                    and not updated.diagnostics.get("cancel_without_cleanup")
                    and not updated.diagnostics.get("failed_without_cleanup")
                    and not updated.diagnostics.get("success_without_cleanup")
                    and not updated.diagnostics.get("terminal_cancel_cleanup_conflict")
                ):
                    updated = self._durable_store.reconcile_request(
                        request_id,
                        reason="server_result_ingestion_reconciliation",
                    )
                ok = updated.lifecycle_state == state and self._durable_store.result_was_accepted(
                    request_id, incoming_digest
                )
                if not ok:
                    error = (
                        f"result rejected from {prior_lifecycle_state} "
                        f"into {updated.lifecycle_state}"
                    )
                else:
                    receipt = {
                        "ok": True,
                        **result_identity,
                    }
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        if msg_id is not None:
            await self._send_ws_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "result": receipt if ok else {"ok": False, "error": error},
                    "id": msg_id,
                },
                connection_id,
            )
            self._record_durable_delivery_progress(
                request_id,
                "ack_sent",
                {"method": "durable_command.result", "ok": ok, "error": error},
            )
        if ok:
            self._clear_durable_delivery_inflight(request_id, f"terminal_{state.lower()}")

    async def _handle_capabilities_changed(
        self,
        node_id: str,
        params: dict[str, Any],
        ws: ServerConnection,
        connection_id: str = "",
    ) -> None:
        if connection_id and not self._registry.owns(node_id, connection_id):
            logger.warning("capabilities update refused: %s stale connection", node_id)
            return
        node = self._registry.get(node_id)
        if node is None:
            return

        self._unregister_integration(node_id)

        new_caps = [
            NodeCapability(
                name=c.get("name", ""),
                category=c.get("category", "system"),
                risk_class=c.get("risk_class", "READ_ONLY"),
                max_risk_class=c.get("max_risk_class", "REVERSIBLE_WRITE"),
            )
            for c in params.get("capabilities", [])
        ]
        node.capabilities = new_caps
        self._register_integration(node)
        logger.info("node %s capabilities updated: %s", node_id, [c.name for c in new_caps])

    async def _handle_peripherals_changed(
        self,
        node_id: str,
        params: dict[str, Any],
        connection_id: str = "",
    ) -> None:
        if connection_id and not self._registry.owns(node_id, connection_id):
            logger.warning("peripherals update refused: %s stale connection", node_id)
            return
        node = self._registry.get(node_id)
        if node is None:
            return
        node.peripherals = [Peripheral.from_dict(p) for p in params.get("peripherals", [])]
        self._registry._write_snapshot()
        self._emit_mesh_event("mesh.node_peripherals_changed", node)
        logger.info("node %s peripherals updated: %d devices", node_id, len(node.peripherals))

    async def _handle_signal(
        self,
        node_id: str,
        params: dict[str, Any],
        msg_id: Any,
        ws: ServerConnection,
        connection_id: str = "",
    ) -> None:
        if connection_id and not self._registry.owns(node_id, connection_id):
            logger.warning("signal refused: %s stale connection", node_id)
            return
        signal_class = params.get("signal_class", "event")

        if signal_class == "telemetry":
            from datetime import datetime, timezone

            snapshot = MetricsSnapshot(
                node_id=node_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                cpu=params.get("payload", {}).get("cpu"),
                memory=params.get("payload", {}).get("memory"),
                disk=params.get("payload", {}).get("disk"),
                battery=params.get("payload", {}).get("battery"),
            )
            self._metrics.record(snapshot)
        elif signal_class == "workstation_state":
            payload = params.get("payload", {})
            if self._workstation_callback is not None:
                loop = asyncio.get_running_loop()
                try:
                    loop.run_in_executor(None, self._workstation_callback, node_id, payload)
                except Exception as exc:
                    logger.debug("workstation callback failed: %s", exc)
        elif signal_class == "camera_frame":
            payload = params.get("payload", {})
            if payload.get("image_base64"):
                if self._frame_queue is not None:
                    try:
                        self._frame_queue.put_nowait((node_id, payload))
                    except asyncio.QueueFull:
                        pass
                elif self._frame_callback is not None:
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, self._frame_callback, node_id, payload)
        elif self._pipeline_submit_fn is not None:
            content = params.get("content_type", "node.signal")
            payload = params.get("payload", {})
            payload["_node_id"] = node_id
            try:
                self._pipeline_submit_fn(
                    f"[{node_id}] {content}: {json.dumps(payload)[:200]}",
                    adapter_name=f"node-{node_id}",
                )
            except Exception as exc:
                logger.error("pipeline submit for node signal failed: %s", exc)

        if msg_id is not None:
            await self._send_ws_json(
                ws,
                {
                    "jsonrpc": "2.0",
                    "result": {"ack": True},
                    "id": msg_id,
                },
                connection_id,
            )

    def _check_anomalies(self, node_id: str, metrics: dict[str, Any]) -> None:
        """Promote anomalous metrics to the pipeline as alert signals."""
        if self._pipeline_submit_fn is None:
            return

        alerts: list[str] = []
        cpu = metrics.get("cpu")
        disk = metrics.get("disk")
        battery = metrics.get("battery")

        if cpu is not None and cpu > self._config.anomaly_cpu_threshold:
            alerts.append(f"CPU at {cpu}%")
        if disk is not None and disk > self._config.anomaly_disk_threshold:
            alerts.append(f"Disk at {disk}%")
        if battery is not None and battery < self._config.anomaly_battery_threshold:
            alerts.append(f"Battery at {battery}%")

        if not alerts:
            return

        try:
            self._pipeline_submit_fn(
                f"[{node_id}] ALERT: {', '.join(alerts)}",
                adapter_name=f"node-{node_id}",
            )
        except Exception as exc:
            logger.error("anomaly alert submit failed: %s", exc)

    def _register_integration(self, node: ConnectedNode) -> None:
        """Create and register a proxy IntegrationManifest for this node."""
        from transports.node_mesh.integration.manifest import build_node_manifest

        integration_id = f"node-{node.node_id}"
        manifest = build_node_manifest(node)
        adapter = self._integration_registry.register(manifest)
        if adapter is not None:
            self._executor.register_adapter(adapter)
            logger.info("node adapter registered: %s", integration_id)

    def _unregister_integration(self, node_id: str) -> None:
        integration_id = f"node-{node_id}"
        self._integration_registry.unregister(integration_id)
        self._executor.unregister_adapter(integration_id)
        logger.info("node adapter unregistered: %s", integration_id)

    def _unregister_node(self, node_id: str, *, connection_id: str | None = None) -> None:
        node = self._registry.get(node_id)
        if connection_id is not None and node is not None and node.connection_id != connection_id:
            logger.info("node unregister skipped: %s owned by a newer connection", node_id)
            return

        if self._runtime_graph_hook is not None:
            try:
                self._runtime_graph_hook(node_id, [], "disconnect")
            except Exception as exc:
                logger.warning("runtime graph hook (disconnect) failed: %s", exc)

        self._unregister_integration(node_id)
        removed = self._registry.remove(node_id, connection_id=connection_id)
        if removed is None and connection_id is not None:
            return
        if node:
            node.status = "disconnected"
            self._emit_mesh_event("mesh.node_disconnected", node)
        logger.info("node fully unregistered: %s", node_id)

    _METRICS_SNAPSHOT_PATH = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data",
        "umh",
        "organism",
        "mesh_metrics.json",
    )

    def _write_metrics_snapshot(self) -> None:
        """Persist ALL node metrics (VPS + remote) to disk.

        This file is the single source of truth for the cockpit.
        VPS metrics come from psutil (collected by _vps_metrics_loop).
        Remote node metrics come from heartbeats.
        """
        try:
            from datetime import datetime, timezone

            import psutil

            out: dict[str, Any] = {}
            # VPS self-metrics (always present — this IS the VPS)
            out["vps"] = {
                "cpu": psutil.cpu_percent(interval=0),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent,
                "battery": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            # Remote node metrics from heartbeats
            for nid, snap in self._metrics.latest_all().items():
                entry: dict[str, Any] = {
                    "cpu": snap.cpu,
                    "memory": snap.memory,
                    "disk": snap.disk,
                    "battery": snap.battery,
                    "timestamp": snap.timestamp,
                }
                if snap.gpu is not None:
                    entry["gpu"] = snap.gpu
                out[nid] = entry
            os.makedirs(os.path.dirname(self._METRICS_SNAPSHOT_PATH), exist_ok=True)
            tmp = self._METRICS_SNAPSHOT_PATH + ".tmp"
            with open(tmp, "w") as f:
                json.dump(out, f)
            os.replace(tmp, self._METRICS_SNAPSHOT_PATH)
        except Exception as exc:
            logger.debug("metrics snapshot write failed: %s", exc)

    async def _vps_metrics_loop(self) -> None:
        """Collect VPS self-metrics on the same cadence as remote heartbeats."""
        while True:
            await asyncio.sleep(self._config.heartbeat_interval_s)
            self._write_metrics_snapshot()

    async def _health_check_loop(self) -> None:
        """Periodically check for stale nodes."""
        while True:
            await asyncio.sleep(30)
            try:
                for req in self._durable_store.reconcile_due_requests():
                    logger.info(
                        "durable request reconciled by health loop: %s -> %s",
                        req.request_id,
                        req.lifecycle_state,
                    )
            except Exception as exc:
                logger.warning("durable request reconciliation sweep failed: %s", exc)
            stale = self._registry.stale_nodes()
            for node_id in stale:
                node = self._registry.get(node_id)
                if node and node.status != "disconnected":
                    node.status = "degraded"
                    age = node.heartbeat_age_s()
                    if age > self._config.heartbeat_timeout_s * 2:
                        logger.warning("node %s timed out (%.0fs), unregistering", node_id, age)
                        self._unregister_node(node_id, connection_id=node.connection_id)
                        try:
                            await node.ws.close(4002, "heartbeat timeout")
                        except Exception:
                            pass

    # ── HTTP Command Relay ─────────────────────────────────────────────

    @staticmethod
    def _relay_auth_ok(auth_header: str) -> bool:
        """Relay bearer auth. FAIL CLOSED.

        When UMH_MESH_RELAY_SECRET is unset the relay refuses every request —
        "no secret" is NEVER treated as "allow". A configured secret requires
        an exact constant-time match of the Authorization: Bearer header.
        """
        relay_secret = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()
        if not relay_secret:
            logger.error("mesh relay fail-closed: UMH_MESH_RELAY_SECRET unset — refusing request")
            return False
        if not auth_header:
            return False
        expected = f"Bearer {relay_secret}"
        return hmac_compare(auth_header, expected)

    @staticmethod
    async def _write_unauthorized(writer: asyncio.StreamWriter) -> None:
        resp_body = json.dumps({"error": "unauthorized"}).encode()
        writer.write(
            b"HTTP/1.1 401 Unauthorized\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: " + str(len(resp_body)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + resp_body
        )
        await writer.drain()

    async def _run_http_relay(self) -> None:
        """Lightweight HTTP server for command dispatch from Docker containers."""
        logger.info("_run_http_relay task started")
        http_port = self._config.port + 1

        async def handle_request(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            try:
                request_line = await asyncio.wait_for(reader.readline(), timeout=5)
                headers: dict[str, str] = {}
                while True:
                    line = await asyncio.wait_for(reader.readline(), timeout=5)
                    if line in (b"\r\n", b"\n", b""):
                        break
                    if b":" in line:
                        k, v = line.decode().split(":", 1)
                        headers[k.strip().lower()] = v.strip()

                method, path, _ = request_line.decode().split(" ", 2)
                content_length = int(headers.get("content-length", "0"))
                body = b""
                if content_length > 0:
                    body = await asyncio.wait_for(reader.readexactly(content_length), timeout=10)

                # /reload and /health both read node state; everything except
                # nothing is anonymous now. Relay bearer auth is required on
                # every dispatch and every read that leaks node identity.
                relay_authed = self._relay_auth_ok(headers.get("authorization", ""))

                if method == "GET" and path.rstrip("/") == "/health":
                    if not relay_authed:
                        await self._write_unauthorized(writer)
                        return
                    resp = self._http_health()
                elif method == "POST" and path.rstrip("/") == "/reload":
                    peer = writer.get_extra_info("peername")
                    peer_ip = peer[0] if peer else ""
                    if peer_ip in ("127.0.0.1", "::1"):
                        self.reload_config()
                        resp = {"ok": True, "message": "config reloaded"}
                    else:
                        logger.warning("mesh relay /reload rejected from %s", peer_ip)
                        resp = {"error": "localhost only"}
                elif method == "POST" and path.rstrip("/") == "/dispatch":
                    if not relay_authed:
                        logger.warning(
                            "mesh relay /dispatch auth failed from %s",
                            writer.get_extra_info("peername"),
                        )
                        await self._write_unauthorized(writer)
                        return
                    resp = await self._http_dispatch(json.loads(body))
                elif method == "GET" and path.rstrip("/") == "/nodes":
                    if not relay_authed:
                        await self._write_unauthorized(writer)
                        return
                    resp = self._http_nodes()
                elif method == "POST" and path.rstrip("/") == "/durable-claim-state":
                    authed_node_id = self._http_authenticated_node_id(
                        headers.get("authorization", "")
                    )
                    if not authed_node_id:
                        await self._write_unauthorized(writer)
                        return
                    payload = json.loads(body)
                    if not isinstance(payload, dict):
                        resp = {"ok": False, "accepted": False, "error": "invalid payload"}
                    else:
                        requested_node_id = str(payload.get("node_id", ""))
                        if authed_node_id != "*" and requested_node_id != authed_node_id:
                            resp = {
                                "ok": False,
                                "accepted": False,
                                "error": "node token does not match requested node_id",
                            }
                        else:
                            resp = self._canonical_durable_claim_state(
                                requested_node_id,
                                payload,
                            )
                else:
                    resp = {"error": "not found"}

                resp_body = json.dumps(resp).encode()
                writer.write(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: " + str(len(resp_body)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n" + resp_body
                )
                await writer.drain()
            except Exception as exc:
                logger.debug("http relay request error: %s", exc)
                try:
                    err = json.dumps({"error": str(exc)}).encode()
                    writer.write(
                        b"HTTP/1.1 500 Internal Server Error\r\n"
                        b"Content-Type: application/json\r\n"
                        b"Content-Length: " + str(len(err)).encode() + b"\r\n"
                        b"Connection: close\r\n\r\n" + err
                    )
                    await writer.drain()
                except Exception:
                    pass
            finally:
                writer.close()

        try:
            logger.info("starting http command relay on port %d...", http_port)
            bind_host = os.environ.get("UMH_MESH_RELAY_BIND", "0.0.0.0")
            srv = await asyncio.start_server(handle_request, bind_host, http_port)
            logger.info("http command relay listening on :%d", http_port)
            async with srv:
                await srv.serve_forever()
        except asyncio.CancelledError:
            logger.info("http relay shutting down")
        except Exception as exc:
            logger.error("http relay failed to start: %s", exc, exc_info=True)

    def reload_config(self) -> None:
        """Reload node_mesh_config.toml without restart. Thread-safe."""
        from transports.node_mesh.config import load_mesh_config

        new_config = load_mesh_config()
        self._config = new_config
        logger.info(
            "mesh config reloaded: %d node tokens",
            len(new_config.node_tokens),
        )

    def _http_health(self) -> dict[str, Any]:
        nodes = self._registry.all_nodes()
        return {
            "status": "healthy",
            "connected_nodes": len(nodes),
            "node_ids": [n.node_id for n in nodes],
        }

    def _http_nodes(self) -> list[dict[str, Any]]:
        return [n.to_api_dict() for n in self._registry.all_nodes()]

    async def _http_dispatch(self, body: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a capability.execute to a connected node via WS and wait for response.

        Synchronous mesh is restricted to explicit READ_ONLY observations.
        Consequential writes must enter DurableRemote so canonical request
        trajectory/idempotency owns replay, redelivery, and authority proof.
        Unknown effect classes fail closed.
        """
        from uuid import uuid4

        from substrate.execution.mesh_verdict import (
            READ_ONLY_EFFECT,
            canonical_payload_digest,
            canonical_sync_effect_policy,
            verify_verdict,
        )

        request_id = str(body.get("request_id", "")).strip()
        correlation_id = str(body.get("correlation_id", "")).strip()
        candidate_sha = str(body.get("candidate_sha", "")).strip()
        effect_class = str(body.get("effect_class", "")).strip()
        idempotency_key = str(body.get("idempotency_key", "")).strip()
        node_id = body.get("node_id", "")
        capability = body.get("capability", "")
        params = body.get("params", {})
        risk_class = body.get("risk_class", "")
        expected_payload_digest = canonical_payload_digest(params)
        supplied_payload_digest = str(body.get("payload_digest", "")).strip()
        verdict_token = body.get("verdict_token", "") or body.get("governance_verdict_id", "")
        _MAX_DISPATCH_TIMEOUT = 600
        raw_timeout = body.get("timeout", 15)
        timeout = max(
            1,
            min(
                int(raw_timeout) if isinstance(raw_timeout, (int, float)) else 15,
                _MAX_DISPATCH_TIMEOUT,
            ),
        )

        if not node_id or not capability:
            return {"ok": False, "error": "node_id and capability required"}

        policy = canonical_sync_effect_policy(capability, declared_effect_class=effect_class)
        declared_effect = policy.declared_effect_class
        if not declared_effect:
            return {
                "ok": False,
                "error": "sync dispatch requires explicit known effect_class",
                "status": "effect_class_required",
            }
        if declared_effect != policy.authoritative_effect_class:
            return {
                "ok": False,
                "error": f"sync effect policy mismatch: {policy.reason}",
                "status": "effect_policy_mismatch",
                "authoritative_effect_class": policy.authoritative_effect_class,
                "effect_policy": policy.policy_id,
            }
        if not request_id or not correlation_id or not idempotency_key:
            return {
                "ok": False,
                "error": "sync dispatch requires request, correlation and idempotency binding",
                "status": "operation_binding_required",
            }
        if supplied_payload_digest != expected_payload_digest:
            return {
                "ok": False,
                "error": "payload digest mismatch",
                "status": "payload_digest_mismatch",
            }
        if not policy.sync_allowed:
            return {
                "ok": False,
                "error": policy.reason,
                "status": "sync_write_denied"
                if policy.authoritative_effect_class
                else "effect_policy_unavailable",
                "authoritative_effect_class": policy.authoritative_effect_class,
                "effect_policy": policy.policy_id,
            }
        if policy.authoritative_effect_class != READ_ONLY_EFFECT:
            return {
                "ok": False,
                "error": "sync dispatch is restricted to READ_ONLY effect_class",
                "status": "effect_class_mismatch",
            }
        if verdict_token:
            check = verify_verdict(
                verdict_token,
                expected_node_id=node_id,
                expected_capability=capability,
                expected_risk_class=risk_class,
                expected_request_id=request_id,
                expected_correlation_id=correlation_id,
                expected_candidate_sha=candidate_sha,
                expected_effect_class=declared_effect,
                expected_authoritative_effect_class=policy.authoritative_effect_class,
                expected_effect_policy=policy.policy_id,
                expected_payload_digest=expected_payload_digest if supplied_payload_digest else "",
                expected_idempotency_key=idempotency_key,
            )
            if not check.valid:
                logger.error(
                    "mesh dispatch rejected: invalid verdict for %s on %s: %s",
                    capability,
                    node_id,
                    check.reason,
                )
                return {
                    "ok": False,
                    "error": f"invalid governance verdict: {check.reason}",
                    "status": "verdict_invalid",
                }

        node = self._registry.get(node_id)
        if node is None:
            return {"ok": False, "error": f"node {node_id} not connected"}
        if node.ws is None:
            return {"ok": False, "error": f"node {node_id} has no WS connection"}

        req_id = request_id or uuid4().hex
        rpc_msg = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "capability.execute",
                "params": {
                    "request_id": req_id,
                    "correlation_id": correlation_id,
                    "candidate_sha": candidate_sha,
                    "effect_class": declared_effect,
                    "authoritative_effect_class": policy.authoritative_effect_class,
                    "effect_policy": policy.policy_id,
                    "idempotency_key": idempotency_key,
                    "payload_digest": expected_payload_digest,
                    "capability_name": capability,
                    "params": params,
                    "risk_class": risk_class,
                    "governance_verdict_id": verdict_token,
                    "timeout_seconds": timeout,
                },
                "id": req_id,
            }
        )

        response_future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        if not hasattr(self, "_pending_http"):
            self._pending_http: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._pending_http[req_id] = response_future

        try:
            await node.ws.send(rpc_msg)
        except Exception as exc:
            self._pending_http.pop(req_id, None)
            return {"ok": False, "error": f"failed to send to node: {exc}", "status": "send_error"}

        try:
            result = await asyncio.wait_for(response_future, timeout=timeout)
        except asyncio.TimeoutError:
            return {"ok": False, "error": f"timeout after {timeout}s", "status": "timeout"}
        finally:
            self._pending_http.pop(req_id, None)

        success = result.get("success", False)
        return {
            "ok": success,
            "status": "executed" if success else "failed",
            "result_data": result.get("result_data", {}),
            "error": result.get("error"),
            "latency_ms": result.get("latency_ms", 0),
        }
