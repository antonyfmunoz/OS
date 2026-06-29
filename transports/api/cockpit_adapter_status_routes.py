"""Cockpit adapter status routes — read-only observability for the adapter fleet.

Wired by cockpit.py sub-router registration.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from transports.api.cockpit_auth import require_clerk_auth

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/umh/adapters",
    tags=["adapters"],
    dependencies=[Depends(require_clerk_auth)],
)

_registry = None


def _get_registry():
    global _registry
    if _registry is None:
        try:
            from adapters.adapter_engine.production_manifests import populate_production_registry
            _registry = populate_production_registry()
            logger.info("adapter registry populated with %d adapters", len(_registry.adapters))
        except Exception:
            logger.debug("adapter registry init failed", exc_info=True)
            from adapters.adapter_engine.adapter_registry_contracts import AdapterRegistry
            _registry = AdapterRegistry()
    return _registry


@router.get("/status")
async def adapter_status() -> dict[str, Any]:
    """Return status of all registered production adapters."""
    registry = _get_registry()
    adapters = []
    for adapter_id, desc in registry.adapters.items():
        adapters.append({
            "adapter_id": desc.adapter_id,
            "adapter_type": desc.adapter_type,
            "capabilities": [c.action_type for c in desc.capabilities],
            "modalities": [m.value for m in (desc.modalities or [])],
            "participant_type": desc.participant_type.value if desc.participant_type else None,
            "version": desc.version,
        })
    return {
        "adapter_count": len(adapters),
        "adapters": adapters,
    }
