"""Understanding protocol — canonical contracts for domain bridges and sources.

Consolidates DomainBridge and Source Protocols from the understanding layer.
"""

from __future__ import annotations

from substrate.understanding.domains.contract import DomainBridge  # noqa: F401
from substrate.understanding.perception.source import Source  # noqa: F401

__all__ = ["DomainBridge", "Source"]
