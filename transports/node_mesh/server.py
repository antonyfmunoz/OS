"""Node Mesh WebSocket server — manages node connections and lifecycle.

Runs on a dedicated port (default 8094). Each connected node gets a
proxy IntegrationManifest registered through IntegrationRegistry,
making it a first-class integration indistinguishable from Notion/EOS.
"""

from __future__ import annotations

import asyncio
import json
import logging
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
    ) -> None:
        self._config = config
        self._executor = executor
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

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self) -> None:
        assert self._loop is not None
        self._health_task = self._loop.create_task(self._health_check_loop())

        async with websockets.serve(
            self._handle_connection,
            "0.0.0.0",
            self._config.port,
            ping_interval=30,
            ping_timeout=10,
        ) as server:
            self._server = server
            logger.info("node mesh server listening on :%d", self._config.port)
            while not self._shutdown_event.is_set():
                await asyncio.sleep(0.5)

            server.close()
            await server.wait_closed()

        self._health_task.cancel()

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

        await ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "result": {
                        "accepted": True,
                        "server_version": "0.1.0",
                        "heartbeat_interval_s": 30,
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

        from datetime import datetime, timezone

        snapshot = MetricsSnapshot(
            node_id=node_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu=metrics.get("cpu"),
            memory=metrics.get("memory"),
            disk=metrics.get("disk"),
            battery=metrics.get("battery"),
            network_io=metrics.get("network_io", {}),
        )
        self._metrics.record(snapshot)

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
        from substrate.integrations.node_mesh.manifest import build_node_manifest

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
        self._unregister_integration(node_id)
        self._registry.remove(node_id)
        if node:
            node.status = "disconnected"
            self._emit_mesh_event("mesh.node_disconnected", node)
        logger.info("node fully unregistered: %s", node_id)

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
