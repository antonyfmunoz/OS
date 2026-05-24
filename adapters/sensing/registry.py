"""Sensing adapter registry — auto-discovers and manages sensing adapters.

At boot, the workstation registers sensing adapters with this registry.
The registry tracks lifecycle state and provides health queries. Signal
routing to substrate sockets is handled by the sensing port in
substrate/sockets/sensing_port.py.

UMH substrate subsystem.
"""

from __future__ import annotations

import logging
from typing import Iterator

from adapters.sensing.base import SensingAdapter
from adapters.sensing.types import (
    AdapterFamily,
    AdapterHealth,
    SensingAdapterState,
    SensingSocketType,
)

logger = logging.getLogger(__name__)


class SensingAdapterRegistry:
    """Central registry for all sensing adapters.

    Manages adapter lifecycle (register → start → health → stop)
    and provides queries by family or socket type.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, SensingAdapter] = {}

    def register(self, adapter: SensingAdapter) -> None:
        """Register a sensing adapter. Replaces existing adapter with same ID."""
        aid = adapter.adapter_id
        if aid in self._adapters:
            existing = self._adapters[aid]
            if existing.health().state == SensingAdapterState.RUNNING:
                existing.stop()
            logger.info("replacing sensing adapter: %s", aid)
        self._adapters[aid] = adapter
        logger.info(
            "sensing adapter registered: %s (family=%s, socket=%s)",
            aid,
            adapter.adapter_family.value,
            adapter.socket_type.value,
        )

    def unregister(self, adapter_id: str) -> None:
        """Unregister and stop a sensing adapter. Idempotent."""
        adapter = self._adapters.pop(adapter_id, None)
        if adapter is None:
            return
        if adapter.health().state == SensingAdapterState.RUNNING:
            adapter.stop()
        logger.info("sensing adapter unregistered: %s", adapter_id)

    def start_all(self) -> dict[str, bool]:
        """Start all registered adapters. Returns adapter_id → success map."""
        results: dict[str, bool] = {}
        for aid, adapter in self._adapters.items():
            try:
                results[aid] = adapter.start()
                if results[aid]:
                    logger.info("sensing adapter started: %s", aid)
                else:
                    logger.warning("sensing adapter failed to start: %s", aid)
            except Exception as exc:
                logger.error("sensing adapter start error: %s — %s", aid, exc)
                results[aid] = False
        return results

    def stop_all(self) -> None:
        """Stop all running adapters."""
        for aid, adapter in self._adapters.items():
            if adapter.health().state == SensingAdapterState.RUNNING:
                try:
                    adapter.stop()
                    logger.info("sensing adapter stopped: %s", aid)
                except Exception as exc:
                    logger.error("sensing adapter stop error: %s — %s", aid, exc)

    def get(self, adapter_id: str) -> SensingAdapter | None:
        return self._adapters.get(adapter_id)

    def by_family(self, family: AdapterFamily) -> list[SensingAdapter]:
        return [a for a in self._adapters.values() if a.adapter_family == family]

    def by_socket(self, socket_type: SensingSocketType) -> list[SensingAdapter]:
        return [a for a in self._adapters.values() if a.socket_type == socket_type]

    def running(self) -> list[SensingAdapter]:
        return [
            a for a in self._adapters.values() if a.health().state == SensingAdapterState.RUNNING
        ]

    def health_all(self) -> dict[str, AdapterHealth]:
        return {aid: a.health() for aid, a in self._adapters.items()}

    def registered_ids(self) -> list[str]:
        return list(self._adapters.keys())

    def __len__(self) -> int:
        return len(self._adapters)

    def __iter__(self) -> Iterator[SensingAdapter]:
        return iter(self._adapters.values())

    def summary(self) -> dict[str, object]:
        """Quick summary for status displays."""
        by_state: dict[str, int] = {}
        for adapter in self._adapters.values():
            state = adapter.health().state.value
            by_state[state] = by_state.get(state, 0) + 1
        return {
            "total": len(self._adapters),
            "by_state": by_state,
            "families": sorted({a.adapter_family.value for a in self._adapters.values()}),
        }
