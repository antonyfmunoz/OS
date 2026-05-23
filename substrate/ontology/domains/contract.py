"""Domain bridge contract — re-exports from substrate.understanding.domains.contract.

The canonical implementation lives in substrate/understanding/domains/contract.py.
"""

from substrate.understanding.domains.contract import (  # noqa: F401
    DomainBridge,
    DomainProjection,
    make_projection_id,
)

__all__ = ["DomainBridge", "DomainProjection", "make_projection_id"]
