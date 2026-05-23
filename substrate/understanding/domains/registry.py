"""Bridge registry — plug-in system for domain bridges."""

from __future__ import annotations

from .contract import DomainBridge


class BridgeRegistry:
    """Registry of domain bridges.

    Bridges register themselves at module load time.
    The orchestrator calls get_all() during the bridge stage.
    """

    _bridges: dict[str, DomainBridge]

    def __init__(self) -> None:
        self._bridges = {}

    def register(self, bridge: DomainBridge) -> None:
        self._bridges[bridge.domain_id] = bridge

    def get_all(self) -> list[DomainBridge]:
        return list(self._bridges.values())

    def get_by_id(self, domain_id: str) -> DomainBridge | None:
        return self._bridges.get(domain_id)


# Global registry instance
default_registry = BridgeRegistry()
