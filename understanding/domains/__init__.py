"""Domain bridge — maps ontology observations to domain-typed projections."""

from .contract import DomainBridge, DomainProjection
from .registry import BridgeRegistry

__all__ = ["DomainBridge", "DomainProjection", "BridgeRegistry"]
