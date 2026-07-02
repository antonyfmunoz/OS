"""Browser port — substrate-layer abstraction for web access adapters.

The adapter layer (adapters/scrapling/) registers its concrete
implementation at startup. Substrate code calls the thin wrappers
here, never importing from adapters/.

Covers: Scrapling (web scraping/browsing).
"""

from __future__ import annotations

from typing import Any, Optional

_scrapling_connector_cls: Optional[type] = None


def register_scrapling(*, connector_cls: type) -> None:
    """Register the Scrapling connector class."""
    global _scrapling_connector_cls
    _scrapling_connector_cls = connector_cls


def get_scrapling_connector_class() -> Optional[type]:
    """Return ScraplingConnector class, or None if not registered."""
    return _scrapling_connector_cls
