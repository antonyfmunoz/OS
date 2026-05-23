"""Build an IntegrationManifest for a connected mesh node."""

from __future__ import annotations

from substrate.integrations.node_mesh.handlers import NodeCapabilityHandler
from substrate.integrations.node_mesh.outcomes import NodeOutcomeReceiver
from substrate.integrations.node_mesh.signals import NodeSignalEmitter
from transports.node_mesh.registry import ConnectedNode
from substrate.sockets.registry import IntegrationManifest


def build_node_manifest(node: ConnectedNode) -> IntegrationManifest:
    """Create a full proxy IntegrationManifest for a remote node."""
    return IntegrationManifest(
        integration_id=f"node-{node.node_id}",
        signal_emitter=NodeSignalEmitter(node.node_id),
        capability_handler=NodeCapabilityHandler(node),
        outcome_receiver=NodeOutcomeReceiver(node.node_id, node.ws),
    )
