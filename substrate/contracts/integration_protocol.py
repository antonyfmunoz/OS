"""Integration protocol — canonical contracts for integration-side adapters.

Consolidates SignalEmitter, CapabilityHandler, OutcomeReceiver, and
ViewSubscriber Protocols from sockets/protocols.py. These are the
contracts that integrations (Discord, Notion, node mesh, projections)
implement to connect to UMH.
"""

from __future__ import annotations

from substrate.sockets.protocols import (  # noqa: F401
    SignalEmitter,
    CapabilityHandler,
    OutcomeReceiver,
    ViewSubscriber,
    SignalDescriptor,
    CapabilityDescriptor,
    CapabilityHealth,
)

__all__ = [
    "SignalEmitter",
    "CapabilityHandler",
    "OutcomeReceiver",
    "ViewSubscriber",
    "SignalDescriptor",
    "CapabilityDescriptor",
    "CapabilityHealth",
]
