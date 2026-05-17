"""Tier 3 fallback — stub for future UI-TARS / computer-use integration.

Called when Camoufox fails 3 times on the same service. Currently logs
and returns failure. Future: routes to UI-TARS vision model or
Anthropic computer-use API to navigate the page visually.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def tier_3_fallback(service: str, page_screenshot: bytes | None = None) -> dict[str, Any]:
    """Attempt export via vision-guided automation (not yet implemented)."""
    logger.warning(
        "[Tier3] Fallback triggered for %s — not yet implemented. "
        "Future: UI-TARS or Anthropic computer-use will handle this.",
        service,
    )
    return {
        "ok": False,
        "reason": "tier_3_not_implemented",
        "service": service,
        "has_screenshot": page_screenshot is not None,
    }
