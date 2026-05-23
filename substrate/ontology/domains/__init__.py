"""Domain bridges — re-exports from substrate.understanding.domains.

The canonical implementations live in substrate/understanding/domains/.
This package re-exports for backward compatibility.
"""

from substrate.understanding.domains.contract import DomainBridge, DomainProjection, make_projection_id  # noqa: F401
from substrate.understanding.domains.registry import BridgeRegistry, default_registry  # noqa: F401
from substrate.understanding.domains.life import LifeBridge  # noqa: F401
from substrate.understanding.domains.creator import CreatorBridge  # noqa: F401

__all__ = [
    "DomainBridge",
    "DomainProjection",
    "make_projection_id",
    "BridgeRegistry",
    "default_registry",
    "LifeBridge",
    "CreatorBridge",
]
