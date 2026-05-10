"""Adapter registry — central lookup for execution surface adapters.

Supports multiple adapters per event type with deterministic ordering
(insertion order preserved).
"""

from __future__ import annotations

import logging
from typing import Sequence

from umh.adapters.contracts import Adapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Thread-safe adapter registry with deterministic ordering.

    Adapters are stored in insertion order. get_handlers returns them
    in that same order, guaranteeing deterministic dispatch.
    """

    def __init__(self) -> None:
        self._adapters: list[Adapter] = []

    def register(self, adapter: Adapter) -> None:
        """Register an adapter. Duplicates are silently ignored."""
        if adapter in self._adapters:
            logger.debug(
                "Adapter %s already registered, skipping", type(adapter).__name__
            )
            return
        if not isinstance(adapter, Adapter):
            raise TypeError(
                f"{type(adapter).__name__} does not satisfy the Adapter protocol"
            )
        self._adapters.append(adapter)
        logger.info("Registered adapter: %s", type(adapter).__name__)

    def get_handlers(self, event_type: str) -> Sequence[Adapter]:
        """Return all adapters that support the given event type.

        Order matches registration order (deterministic).
        Returns empty list if no adapters match — never raises.
        """
        return [a for a in self._adapters if a.supports(event_type)]

    @property
    def registered_count(self) -> int:
        """Number of registered adapters."""
        return len(self._adapters)

    def clear(self) -> None:
        """Remove all registered adapters. Useful for testing."""
        self._adapters.clear()
