"""
Projection port — substrate-layer abstraction for projection registration.

Application projections register at startup.
Substrate code queries projections here, never importing from projections/.
"""

from __future__ import annotations

from typing import Any

_projections: dict[str, dict[str, Any]] = {}


def register_projection(projection_id: str, config: dict[str, Any]) -> None:
    """Register a projection with its configuration."""
    _projections[projection_id] = config


def get_projection(projection_id: str) -> dict[str, Any] | None:
    """Return a projection's config, or None if not registered."""
    return _projections.get(projection_id)


def list_projections() -> list[str]:
    """Return all registered projection IDs."""
    return list(_projections.keys())


def unregister_projection(projection_id: str) -> bool:
    """Remove a projection. Returns True if it existed."""
    return _projections.pop(projection_id, None) is not None
