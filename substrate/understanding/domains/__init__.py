"""Domain bridge — maps ontology observations to domain-typed projections."""

from substrate.ontology.domains.contract import DomainBridge, DomainProjection
from substrate.ontology.domains.registry import BridgeRegistry

from . import business  # noqa: F401 — registers BusinessBridge
import substrate.ontology.domains.creator  # noqa: F401 — registers CreatorBridge
import substrate.ontology.domains.life  # noqa: F401 — registers LifeBridge

__all__ = ["DomainBridge", "DomainProjection", "BridgeRegistry"]
