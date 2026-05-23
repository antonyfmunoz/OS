"""Protocol definitions for integration-side contracts.

These are the load-bearing pieces of Hard Invariant 8: integrations
satisfy these Protocols structurally (by shape) without importing them.
UMH holds references typed as these Protocols; the actual objects are
integration code. The import graph never crosses the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.capability import CapabilityCategory
from services.umh.protocols.signal import SignalUrgency
from substrate.sockets.envelopes import (
    CapabilityRequest,
    CapabilityResponse,
    OutcomeEnvelope,
    ViewFrame,
)


@dataclass(frozen=True)
class SignalDescriptor:
    """Declares a signal type an integration can emit."""

    content_type: str
    description: str
    default_urgency: SignalUrgency = SignalUrgency.NORMAL
    default_risk_class: RiskClass = RiskClass.READ_ONLY


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Declares a capability an integration provides."""

    name: str
    category: CapabilityCategory
    risk_class: RiskClass
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    cost_estimate: float = 0.0
    rate_limit: int | None = None


@dataclass(frozen=True)
class CapabilityHealth:
    """Current health status of an integration's capability layer."""

    integration_id: str
    status: str  # "healthy", "degraded", "unavailable"
    detail: str = ""


@runtime_checkable
class SignalEmitter(Protocol):
    """What an integration provides to push signals into UMH.

    The emitter is a declaration — it describes what signal types the
    integration can emit. The actual sending goes through
    SignalSocket.emit(envelope), not through the emitter itself.
    """

    @property
    def integration_id(self) -> str: ...

    def describe_signals(self) -> list[SignalDescriptor]: ...


@runtime_checkable
class CapabilityHandler(Protocol):
    """What an integration implements to receive capability requests from UMH.

    UMH calls handle_capability() when the pipeline reaches Stage 5 and
    the work packet targets this integration's adapter. The handler
    executes the request (calls external API) and returns a result.
    """

    @property
    def integration_id(self) -> str: ...

    def describe_capabilities(self) -> list[CapabilityDescriptor]: ...

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse: ...

    def health(self) -> CapabilityHealth: ...


@runtime_checkable
class OutcomeReceiver(Protocol):
    """What an integration implements to receive outcome notifications.

    UMH calls on_outcome() after pipeline Stage 7 (outcome classification)
    or after Stage 3 (governance denial). This is fire-and-forget — UMH
    does not wait for the receiver to finish. Long-running receivers
    should defer work to a background task rather than blocking the
    notification path.
    """

    @property
    def integration_id(self) -> str: ...

    def on_outcome(self, envelope: OutcomeEnvelope) -> None: ...

    def accepts_outcomes(self) -> list[str]: ...


@runtime_checkable
class ViewSubscriber(Protocol):
    """What an observer implements to receive pipeline state frames.

    Frames are broadcast at every pipeline stage (1-10). Subscribers
    must not block — the broadcast loop catches and logs exceptions
    but slow subscribers delay all subsequent subscribers in the list.
    """

    @property
    def subscriber_id(self) -> str: ...

    def on_frame(self, frame: ViewFrame) -> None: ...

    def accepts_events(self) -> list[str]: ...
