"""Domain bridge — maps ontology observations to domain-typed projections."""

from .contract import DomainBridge, DomainProjection
from .registry import BridgeRegistry

from . import business  # noqa: F401 — registers BusinessBridge
from . import creator  # noqa: F401 — registers CreatorBridge
from . import life  # noqa: F401 — registers LifeBridge

__all__ = ["DomainBridge", "DomainProjection", "BridgeRegistry"]
