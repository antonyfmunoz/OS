"""Control plane protocol — canonical contracts for control plane subsystems.

Consolidates IdentityResolver, ContextAssembler, MemorySystem,
ComponentRegistry, SignalRouter, and Notifier Protocols.
Import from here for type annotations; implement against the Protocol shapes.
"""

from __future__ import annotations

from substrate.control_plane.identity import IdentityResolver  # noqa: F401
from substrate.control_plane.context import ContextAssembler  # noqa: F401
from substrate.control_plane.memory import MemorySystem  # noqa: F401
from substrate.control_plane.registry import ComponentRegistry  # noqa: F401
from substrate.control_plane.router import SignalRouter  # noqa: F401
from substrate.control_plane.actions.notifier import Notifier  # noqa: F401

__all__ = [
    "IdentityResolver",
    "ContextAssembler",
    "MemorySystem",
    "ComponentRegistry",
    "SignalRouter",
    "Notifier",
]
