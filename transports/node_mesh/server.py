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

import websockets
from websockets.asyncio.server import ServerConnection

from substrate.execution.executor import WorkPacketExecutor
from transports.node_mesh.config import MeshConfig
from transports.node_mesh.metrics_buffer import MetricsBuffer, MetricsSnapshot
from transports.node_mesh.registry import ConnectedNode, NodeCapability, NodeRegistry
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.registry import IntegrationManifest, IntegrationRegistry
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.envelopes import ViewFrame
from substrate.sockets.view_socket import ViewSocket

logger = logging.getLogger(__name__)


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
        self._frame_callback: Callable[[str, str], None] | None = None
        self._server: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()
        self._health_task: asyncio.Task[None] | None = None

    @property
    def node_registry(self) -> NodeRegistry:
        return self._registry

    @property
    def metrics_buffer(self) -> MetricsBuffer:
        return self._metrics

    def register_frame_callback(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback for camera frames: callback(node_id, base64_jpeg)."""
        self._frame_callback = callback

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

    async def _serve(self) -> None:
        assert self._loop is not None
        self._health_task = self._loop.create_task(self._health_check_loop())
        self._vps_metrics_task = self._loop.create_task(self._vps_metrics_loop())
        self._http_task = self._loop.create_task(self._run_http_relay())
        self._http_task.add_done_callback(self._task_done_cb)

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

        self._health_task.cancel()
        self._vps_metrics_task.cancel()
        self._http_task.cancel()

    async def _handle_connection(self, ws: ServerConnection) -> None:
        """Handle a single node WebSocket connection."""
        node_id: str | None = None
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

            async for raw in ws:
                msg = json.loads(raw)
                method = msg.get("method", "")
                params = msg.get("params", {})
                msg_id = msg.get("id")

                if method == "node.hello":
                    node_id = await self._handle_hello(ws, params, msg_id)
                elif method == "node.heartbeat" and node_id:
                    await self._handle_heartbeat(node_id, params, msg_id, ws)
                elif method == "node.capabilities_changed" and node_id:
                    await self._handle_capabilities_changed(node_id, params, ws)
                elif method == "signal.emit" and node_id:
                    await self._handle_signal(node_id, params, msg_id, ws)
                elif not method and ("result" in msg or "error" in msg):
                    self._resolve_pending_dispatch(msg)
                else:
                    if msg_id is not None:
                        await ws.send(
                            json.dumps(
                                {
                                    "jsonrpc": "2.0",
                                    "error": {
                                        "code": -32601,
                                        "message": f"unknown method: {method}",
                                    },
                                    "id": msg_id,
                                }
                            )
                        )

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as exc:
            logger.error("node connection error: %s", exc)
        finally:
            if node_id:
                self._unregister_node(node_id)

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
        path = ws.request.path if ws.request else ""
        if "?" in path:
            query = path.split("?", 1)[1]
            for part in query.split("&"):
                if part.startswith("token="):
                    return part[6:]
        return ""

    def _authenticate(self, token: str) -> bool:
        if not self._config.node_tokens:
            return True
        return any(nt.token == token for nt in self._config.node_tokens.values())

    def _node_id_for_token(self, token: str) -> str | None:
        for nt in self._config.node_tokens.values():
            if nt.token == token:
                return nt.node_id
        return None

    async def _handle_hello(
        self,
        ws: ServerConnection,
        params: dict[str, Any],
        msg_id: Any,
    ) -> str:
        node_id = params.get("node_id", "unknown")

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
            self._unregister_node(node_id)

        caps = [
            NodeCapability(
                name=c.get("name", ""),
                category=c.get("category", "system"),
                risk_class=c.get("risk_class", "READ_ONLY"),
                max_risk_class=c.get("max_risk_class", "REVERSIBLE_WRITE"),
            )
            for c in params.get("capabilities", [])
        ]

        node = ConnectedNode(
            node_id=node_id,
            hostname=params.get("hostname", "unknown"),
            os=params.get("os", "unknown"),
            os_version=params.get("os_version", ""),
            capabilities=caps,
            daemon_version=params.get("daemon_version", "0.0.0"),
            tailscale_ip=params.get("tailscale_ip", ""),
            ws=ws,
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
        logger.info("node connected: %s (%s %s)", node_id, node.os, node.hostname)
        return node_id

    async def _handle_heartbeat(
        self,
        node_id: str,
        params: dict[str, Any],
        msg_id: Any,
        ws: ServerConnection,
    ) -> None:
        metrics = params.get("metrics", {})
        self._registry.update_heartbeat(node_id, metrics)

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
            await ws.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {"ack": True},
                        "id": msg_id,
                    }
                )
            )

    async def _handle_capabilities_changed(
        self,
        node_id: str,
        params: dict[str, Any],
        ws: ServerConnection,
    ) -> None:
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

    async def _handle_signal(
        self,
        node_id: str,
        params: dict[str, Any],
        msg_id: Any,
        ws: ServerConnection,
    ) -> None:
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
        elif signal_class == "camera_frame":
            if self._frame_callback is not None:
                frame_b64 = params.get("payload", {}).get("image_base64", "")
                if frame_b64:
                    try:
                        self._frame_callback(node_id, frame_b64)
                    except Exception as exc:
                        logger.warning("frame callback failed: %s", exc)
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
            await ws.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {"ack": True},
                        "id": msg_id,
                    }
                )
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

    def _unregister_node(self, node_id: str) -> None:
        node = self._registry.get(node_id)

        if self._runtime_graph_hook is not None:
            try:
                self._runtime_graph_hook(node_id, [], "disconnect")
            except Exception as exc:
                logger.warning("runtime graph hook (disconnect) failed: %s", exc)

        self._unregister_integration(node_id)
        self._registry.remove(node_id)
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
            import psutil
            from datetime import datetime, timezone

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
            stale = self._registry.stale_nodes()
            for node_id in stale:
                node = self._registry.get(node_id)
                if node and node.status != "disconnected":
                    node.status = "degraded"
                    age = node.heartbeat_age_s()
                    if age > self._config.heartbeat_timeout_s * 2:
                        logger.warning("node %s timed out (%.0fs), unregistering", node_id, age)
                        self._unregister_node(node_id)
                        try:
                            await node.ws.close(4002, "heartbeat timeout")
                        except Exception:
                            pass

    # ── HTTP Command Relay ─────────────────────────────────────────────

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

                if method == "GET" and path.rstrip("/") == "/health":
                    resp = self._http_health()
                elif method == "POST" and path.rstrip("/") == "/dispatch":
                    resp = await self._http_dispatch(json.loads(body))
                elif method == "GET" and path.rstrip("/") == "/nodes":
                    resp = self._http_nodes()
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
            bind_host = os.environ.get("UMH_MESH_RELAY_BIND", "127.0.0.1")
            srv = await asyncio.start_server(handle_request, bind_host, http_port)
            logger.info("http command relay listening on :%d", http_port)
            async with srv:
                await srv.serve_forever()
        except asyncio.CancelledError:
            logger.info("http relay shutting down")
        except Exception as exc:
            logger.error("http relay failed to start: %s", exc, exc_info=True)

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
        """Dispatch a capability.execute to a connected node via WS and wait for response."""
        from uuid import uuid4

        node_id = body.get("node_id", "")
        capability = body.get("capability", "")
        params = body.get("params", {})
        _MAX_DISPATCH_TIMEOUT = 180
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

        node = self._registry.get(node_id)
        if node is None:
            return {"ok": False, "error": f"node {node_id} not connected"}
        if node.ws is None:
            return {"ok": False, "error": f"node {node_id} has no WS connection"}

        req_id = uuid4().hex
        rpc_msg = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "capability.execute",
                "params": {
                    "request_id": req_id,
                    "capability_name": capability,
                    "params": params,
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
