"""Domain bridge — maps ontology observations to domain-typed projections.

Canonical location for DomainBridge, DomainProjection, BridgeRegistry,
CreatorBridge, and LifeBridge. substrate.ontology.domains re-exports from here.
"""

from .contract import DomainBridge, DomainProjection
from .registry import BridgeRegistry

from . import business  # noqa: F401 — registers BusinessBridge
from . import creator  # noqa: F401 — registers CreatorBridge
from . import life  # noqa: F401 — registers LifeBridge

__all__ = ["DomainBridge", "DomainProjection", "BridgeRegistry"]
