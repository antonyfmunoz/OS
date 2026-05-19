"""Integration registry — central registration and generic adapter bridge."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from services.umh.governance.risk_classes import RiskClass
from services.umh.sockets.capability_socket import CapabilitySocket
from services.umh.sockets.envelopes import CapabilityRequest, CapabilityResponse
from services.umh.sockets.outcome_socket import OutcomeSocket
from services.umh.sockets.protocols import (
    CapabilityDescriptor,
    CapabilityHandler,
    CapabilityHealth,
    OutcomeReceiver,
    SignalEmitter,
    ViewSubscriber,
)
from services.umh.sockets.signal_socket import SignalSocket
from services.umh.sockets.view_socket import ViewSocket

logger = logging.getLogger(__name__)


@dataclass
class IntegrationManifest:
    """Declares what an integration provides and consumes."""

    integration_id: str
    signal_emitter: SignalEmitter | None = None
    capability_handler: CapabilityHandler | None = None
    outcome_receiver: OutcomeReceiver | None = None
    view_subscriber: ViewSubscriber | None = None


class IntegrationAdapter:
    """Generic adapter that bridges executor's AdapterProtocol to CapabilitySocket.

    One instance per registered integration. Satisfies the executor's
    AdapterProtocol (name, execute, classify_risk) by delegating to
    the CapabilitySocket. No integration-specific logic — all integrations
    use this same class.
    """

    def __init__(
        self,
        integration_id: str,
        capability_socket: CapabilitySocket,
        capability_descriptors: list[CapabilityDescriptor],
    ) -> None:
        self._integration_id = integration_id
        self._socket = capability_socket
        self._risk_map: dict[str, RiskClass] = {
            d.name: d.risk_class for d in capability_descriptors
        }

    @property
    def name(self) -> str:
        return self._integration_id

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Translate executor call into CapabilityRequest → CapabilityResponse → dict."""
        governance_verdict_id = params.pop("_governance_verdict_id", None)
        trace_id = params.pop("_trace_id", None)

        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name=operation,
            integration_id=self._integration_id,
            params=params,
            governance_verdict_id=governance_verdict_id or uuid4(),
            trace_id=trace_id or uuid4(),
        )

        response = self._socket.request(req)

        if not response.success:
            error_msg = response.error or "unknown capability error"
            if response.raw_error:
                error_msg = f"{error_msg} (raw: {response.raw_error})"
            raise RuntimeError(error_msg)

        result: dict[str, Any] = dict(response.result_data)
        if response.side_effects:
            result["_side_effects"] = list(response.side_effects)
        return result

    def classify_risk(self, operation: str, params: dict[str, Any]) -> RiskClass:
        """Look up the declared risk class for this operation."""
        return self._risk_map.get(operation, RiskClass.EXTERNAL_COMMUNICATION)


class IntegrationRegistry:
    """Central registration point for all integrations.

    Wires each manifest component to the appropriate socket. Creates
    an IntegrationAdapter for integrations that provide capabilities.
    """

    def __init__(
        self,
        signal_socket: SignalSocket,
        capability_socket: CapabilitySocket,
        outcome_socket: OutcomeSocket,
        view_socket: ViewSocket,
    ) -> None:
        self._signal = signal_socket
        self._capability = capability_socket
        self._outcome = outcome_socket
        self._view = view_socket
        self._registered: dict[str, IntegrationManifest] = {}
        self._adapters: dict[str, IntegrationAdapter] = {}

    def register(self, manifest: IntegrationManifest) -> IntegrationAdapter | None:
        """Register an integration manifest.

        Wires each non-None component to the appropriate socket.
        Returns the IntegrationAdapter if a capability_handler was
        provided (caller registers it with WorkPacketExecutor).
        Returns None if no capabilities declared.

        Raises ValueError if integration_id is already registered.
        """
        iid = manifest.integration_id
        if iid in self._registered:
            raise ValueError(f"integration '{iid}' already registered")

        if manifest.signal_emitter is not None:
            self._signal.register_emitter(manifest.signal_emitter)

        if manifest.capability_handler is not None:
            self._capability.register_handler(manifest.capability_handler)

        if manifest.outcome_receiver is not None:
            self._outcome.register_receiver(manifest.outcome_receiver)

        if manifest.view_subscriber is not None:
            self._view.subscribe(manifest.view_subscriber)

        adapter: IntegrationAdapter | None = None
        if manifest.capability_handler is not None:
            descriptors = manifest.capability_handler.describe_capabilities()
            adapter = IntegrationAdapter(iid, self._capability, descriptors)
            self._adapters[iid] = adapter

        self._registered[iid] = manifest
        logger.info("integration registered: %s", iid)
        return adapter

    def unregister(self, integration_id: str) -> None:
        """Remove an integration. Idempotent."""
        self._registered.pop(integration_id, None)
        self._adapters.pop(integration_id, None)

    def registered(self) -> list[str]:
        return list(self._registered.keys())

    def get_adapter(self, integration_id: str) -> IntegrationAdapter | None:
        return self._adapters.get(integration_id)

    def health(self) -> dict[str, CapabilityHealth]:
        return {
            iid: self._capability.health_check(iid)
            for iid in self._registered
            if self._registered[iid].capability_handler is not None
        }
