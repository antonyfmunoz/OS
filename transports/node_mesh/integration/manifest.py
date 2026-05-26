"""Build an IntegrationManifest for a connected mesh node."""

from __future__ import annotations

from transports.node_mesh.integration.handlers import NodeCapabilityHandler
from transports.node_mesh.integration.outcomes import NodeOutcomeReceiver
from transports.node_mesh.integration.signals import NodeSignalEmitter
from transports.node_mesh.integration.types import ConnectedNode
from substrate.sockets.registry import IntegrationManifest


def build_node_manifest(node: ConnectedNode) -> IntegrationManifest:
    """Create a full proxy IntegrationManifest for a remote node."""
    return IntegrationManifest(
        integration_id=f"node-{node.node_id}",
        signal_emitter=NodeSignalEmitter(node.node_id),
        capability_handler=NodeCapabilityHandler(node),
        outcome_receiver=NodeOutcomeReceiver(node.node_id, node.ws),
    )
