"""
Capability abstraction — what a node can do.

Future routing should target *capabilities*, not machines. Today the VPS is
the only executor; tomorrow a local Station Daemon will advertise things the
VPS cannot do (microphone input, screen inspection, full computer control).

This module defines the canonical capability vocabulary and a thin registry
for querying which nodes offer a given capability. It is ADDITIVE — it does
not alter current routing.

Usage:
    from runtime.substrate import Capability, CapabilityRegistry, NodeRegistry

    nodes = NodeRegistry.default()
    caps = CapabilityRegistry(nodes)
    targets = caps.nodes_for(Capability.MICROPHONE_INPUT)
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid runtime cycle
    from runtime.transport.nodes import Node, NodeRegistry


class Capability(str, Enum):
    """
    Canonical capability vocabulary.

    Strings are stable slugs — persisted to Node.capabilities and used across
    the station protocol. Add new capabilities here rather than ad-hoc strings
    so the registry stays introspectable.
    """

    REASONING = "reasoning"
    HIGH_COMPUTE = "high_compute"
    BROWSER_CONTROL = "browser_control"
    FULL_COMPUTER_CONTROL = "full_computer_control"
    AUDIO_OUTPUT = "audio_output"
    MICROPHONE_INPUT = "microphone_input"
    SCREEN_INSPECTION = "screen_inspection"
    LONG_RUNNING_SESSION = "long_running_session"

    @classmethod
    def all_slugs(cls) -> list[str]:
        return [c.value for c in cls]


class CapabilityRegistry:
    """
    Query helper over a NodeRegistry.

    Kept deliberately thin — no scoring, no preference logic. The capability-
    aware router will layer on top of this later; for now it just answers
    "which nodes advertise this capability?"
    """

    def __init__(self, node_registry: "NodeRegistry") -> None:
        self._nodes = node_registry

    def nodes_for(self, capability: Capability | str) -> list["Node"]:
        slug = capability.value if isinstance(capability, Capability) else capability
        return self._nodes.with_capability(slug)

    def is_available(self, capability: Capability | str) -> bool:
        return len(self.nodes_for(capability)) > 0

    def inventory(self) -> dict[str, list[str]]:
        """
        Returns {capability_slug: [node_id, ...]} across all known nodes.
        Useful for debug endpoints and future Discord `/substrate` command.
        """
        out: dict[str, list[str]] = {c.value: [] for c in Capability}
        for node in self._nodes.all():
            for cap in node.capabilities:
                out.setdefault(cap, []).append(node.node_id)
        return out
