"""Infrastructure protocol — canonical contracts for substrate storage and projection.

Consolidates SubstrateStorage, ProjectionPortProtocol, and the
execution-layer AdapterProtocol.
"""

from __future__ import annotations

from substrate.execution.bridge.storage import SubstrateStorage  # noqa: F401
from substrate.execution.executor import AdapterProtocol  # noqa: F401
from substrate.sockets.projection_port import ProjectionPortProtocol  # noqa: F401

__all__ = [
    "SubstrateStorage",
    "AdapterProtocol",
    "ProjectionPortProtocol",
]
