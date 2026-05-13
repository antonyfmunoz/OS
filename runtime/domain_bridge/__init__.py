"""Domain bridge — maps ontology observations to domain-typed projections."""

from runtime.domain_bridge.contract import DomainBridge, DomainProjection
from runtime.domain_bridge.registry import BridgeRegistry

__all__ = ["DomainBridge", "DomainProjection", "BridgeRegistry"]
