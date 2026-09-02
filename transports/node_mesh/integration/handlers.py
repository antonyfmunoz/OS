"""Node mesh capability handler — proxies execution requests to remote nodes over WebSocket."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from substrate.governance.risk_classes import RiskClass
from substrate.sockets.envelopes import CapabilityRequest, CapabilityResponse
from substrate.sockets.protocols import CapabilityDescriptor, CapabilityHealth
from substrate.types import CapabilityCategory
from transports.node_mesh.integration.types import ConnectedNode, NodeCapability

logger = logging.getLogger(__name__)

_RISK_CLASS_MAP: dict[str, RiskClass] = {rc.value: rc for rc in RiskClass}


def _parse_risk_class(s: str) -> RiskClass:
    return _RISK_CLASS_MAP.get(s.lower(), RiskClass.EXTERNAL_COMMUNICATION)


def _parse_category(s: str) -> CapabilityCategory:
    try:
        return CapabilityCategory(s)
    except ValueError:
        return CapabilityCategory.COMPUTE


class NodeCapabilityHandler:
    """Proxies CapabilityHandler protocol to a remote node over WebSocket.

    handle_capability() blocks the calling thread (matching the synchronous
    executor contract) by sending a JSON-RPC request over the node's
    WebSocket and waiting on a threading.Event for the response.
    """

    def __init__(self, node: ConnectedNode) -> None:
        self._node = node
        self._node_id = node.node_id
        self._pending: dict[str, tuple[threading.Event, list[CapabilityResponse]]] = {}
        self._descriptors = self._build_descriptors(node.capabilities)
        self._response_thread: threading.Thread | None = None

    @property
    def integration_id(self) -> str:
        return f"node-{self._node_id}"

    def describe_capabilities(self) -> list[CapabilityDescriptor]:
        return self._descriptors

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        """Send capability request to node and block until response arrives.

        Legacy synchronous mesh may only carry exact-operation-bound read-only
        requests. Consequential writes must enter DurableRemote; this handler
        fails closed rather than creating a parallel write protocol.
        """
        from substrate.execution.mesh_verdict import (
            READ_ONLY_EFFECT,
            canonical_payload_digest,
            canonical_sync_effect_policy,
        )

        req_id = request.request_id.hex
        declared_effect = READ_ONLY_EFFECT
        policy = canonical_sync_effect_policy(
            request.capability_name,
            declared_effect_class=declared_effect,
        )
        if not policy.sync_allowed:
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"consequential or unknown capability requires DurableRemote: {policy.reason}",
            )

        payload_digest = canonical_payload_digest(request.params)
        correlation_id = str(request.trace_id)
        idempotency_key = req_id

        event = threading.Event()
        holder: list[CapabilityResponse] = []
        self._pending[req_id] = (event, holder)

        rpc_msg = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "capability.execute",
                "params": {
                    "request_id": req_id,
                    "correlation_id": correlation_id,
                    "candidate_sha": str(request.metadata.get("candidate_sha", "")).strip(),
                    "effect_class": declared_effect,
                    "authoritative_effect_class": policy.authoritative_effect_class,
                    "effect_policy": policy.policy_id,
                    "idempotency_key": idempotency_key,
                    "payload_digest": payload_digest,
                    "capability_name": request.capability_name,
                    "params": request.params,
                    "governance_verdict_id": "",
                    "risk_class": self._risk_class_for(request.capability_name),
                    "trace_id": str(request.trace_id),
                    "timeout_seconds": request.timeout_seconds,
                },
                "id": req_id,
            }
        )

        try:
            import asyncio

            ws = self._node.ws
            loop = getattr(ws, "_loop", None)
            if loop is not None and loop.is_running():
                asyncio.run_coroutine_threadsafe(ws.send(rpc_msg), loop)
            else:
                asyncio.get_event_loop().run_until_complete(ws.send(rpc_msg))
        except Exception as exc:
            self._pending.pop(req_id, None)
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"failed to send to node {self._node_id}: {exc}",
            )

        completed = event.wait(timeout=request.timeout_seconds)
        self._pending.pop(req_id, None)

        if not completed:
            raise TimeoutError(
                f"node {self._node_id} did not respond within {request.timeout_seconds}s"
            )

        return holder[0]

    def _risk_class_for(self, capability_name: str) -> str:
        """Resolve the wire risk class for a capability from its descriptor."""
        base = capability_name.split(".")[0] if "." in capability_name else capability_name
        for desc in self._descriptors:
            if desc.name == base or desc.name == capability_name:
                rc = desc.risk_class
                return rc.value if hasattr(rc, "value") else str(rc)
        # Unknown capability → treat as write-class (fail-closed).
        return "reversible_write"

    def _verdict_field_for(self, request: CapabilityRequest) -> str:
        """Return the verdict field to send to the node.

        Retained for compatibility with older tests/imports. Legacy sync writes
        are rejected in handle_capability() before this can authorize anything.
        Write-class capabilities get a signed verdict token bound to node +
        capability. Read-only capabilities pass the raw verdict id through.
        Fail-closed: if the token cannot be signed (no secret), send the raw id
        — the node's own gate will reject a write-class request without a valid
        token, so nothing executes ungoverned.
        """
        from substrate.execution.mesh_verdict import is_write_class, sign_verdict

        risk_class = self._risk_class_for(request.capability_name)
        raw_id = str(request.governance_verdict_id)
        if not is_write_class(risk_class):
            return raw_id
        try:
            return sign_verdict(
                verdict_id=raw_id,
                node_id=self._node_id,
                capability=request.capability_name,
                risk_class=risk_class,
                ttl_seconds=int(request.timeout_seconds) + 60,
            )
        except ValueError as exc:
            logger.error(
                "cannot sign verdict for %s on %s (node will reject): %s",
                request.capability_name,
                self._node_id,
                exc,
            )
            return raw_id

    def receive_response(self, msg_id: str, result: dict[str, Any]) -> None:
        """Called by the server when a capability response arrives over WebSocket."""
        pending = self._pending.get(msg_id)
        if pending is None:
            logger.warning("orphaned capability response: %s", msg_id)
            return

        event, holder = pending
        from uuid import UUID

        holder.append(
            CapabilityResponse(
                request_id=UUID(msg_id),
                success=result.get("success", False),
                result_data=result.get("result_data", {}),
                error=result.get("error"),
                latency_ms=result.get("latency_ms", 0.0),
                side_effects=result.get("side_effects", []),
            )
        )
        event.set()

    def health(self) -> CapabilityHealth:
        age = self._node.heartbeat_age_s()
        if age > 90:
            return CapabilityHealth(
                self.integration_id, "unavailable", f"no heartbeat for {age:.0f}s"
            )
        if age > 60:
            return CapabilityHealth(self.integration_id, "degraded", "heartbeat delayed")
        return CapabilityHealth(self.integration_id, "healthy")

    def _build_descriptors(self, capabilities: list[NodeCapability]) -> list[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                name=cap.name,
                category=_parse_category(cap.category),
                risk_class=_parse_risk_class(cap.risk_class),
                description=f"Remote {cap.name} on node {self._node_id}",
            )
            for cap in capabilities
        ]
