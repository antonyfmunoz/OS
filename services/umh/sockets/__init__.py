"""UMH Socket Layer — typed boundary between substrate and integrations."""

from services.umh.sockets.envelopes import (
    CapabilityRequest,
    CapabilityResponse,
    OutcomeEnvelope,
    SignalEnvelope,
    SignalReceipt,
    ViewFrame,
)
from services.umh.sockets.protocols import (
    CapabilityDescriptor,
    CapabilityHandler,
    CapabilityHealth,
    OutcomeReceiver,
    SignalDescriptor,
    SignalEmitter,
    ViewSubscriber,
)
from services.umh.sockets.registry import (
    IntegrationAdapter,
    IntegrationManifest,
    IntegrationRegistry,
)

__all__ = [
    "CapabilityDescriptor",
    "CapabilityHandler",
    "CapabilityHealth",
    "CapabilityRequest",
    "CapabilityResponse",
    "IntegrationAdapter",
    "IntegrationManifest",
    "IntegrationRegistry",
    "OutcomeEnvelope",
    "OutcomeReceiver",
    "SignalDescriptor",
    "SignalEmitter",
    "SignalEnvelope",
    "SignalReceipt",
    "ViewFrame",
    "ViewSubscriber",
]
