"""Organism port — substrate-layer abstraction for daemon/organism access.

The transport layer registers the daemon accessor at startup.
Substrate code calls the thin wrapper here, never importing from transports/.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

_get_organism_fn: Optional[Callable] = None


def register_organism_accessor(fn: Callable) -> None:
    """Register the function that returns the organism daemon singleton."""
    global _get_organism_fn
    _get_organism_fn = fn


def get_organism() -> Any:
    """Return the organism daemon singleton, or None if not registered."""
    if _get_organism_fn is not None:
        return _get_organism_fn()
    return None
