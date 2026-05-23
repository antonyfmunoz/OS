"""Bridge registry — re-exports from substrate.understanding.domains.registry.

The canonical implementation lives in substrate/understanding/domains/registry.py.
"""

from substrate.understanding.domains.registry import (  # noqa: F401
    BridgeRegistry,
    default_registry,
)

__all__ = ["BridgeRegistry", "default_registry"]
