"""Shared EngineeringPlanner singleton for all cockpit route modules.

All engineering route files (engineering_routes, review_routes, meta_ide_conv_routes)
must share a single planner instance so plans created via one endpoint are visible
to all others. This module owns that singleton.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_instance: Any = None


def get_shared_planner() -> Any:
    global _instance
    if _instance is not None:
        return _instance
    try:
        from substrate.meta_ide.engineering_planner import EngineeringPlanner

        _instance = EngineeringPlanner()
        logger.info("shared engineering planner created")
        return _instance
    except Exception as exc:
        logger.debug("failed to create shared planner: %s", exc)
        return None
