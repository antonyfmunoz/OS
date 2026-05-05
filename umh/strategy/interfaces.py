"""UMH Strategy — persistence interface for strategy memory state.

Defines the contract for saving/loading StrategyMemory stats
across session restarts. Concrete implementations live in EOS
(e.g. umh/adapters/umh_strategy.py).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StrategyPersistence(Protocol):
    """Contract for persisting StrategyMemory state."""

    def save_strategy_memory(
        self, strategy_data: dict[str, dict], global_turn: int
    ) -> None: ...

    def load_strategy_memory(self) -> dict[str, Any] | None: ...


class NullStrategyPersistence:
    """No-op persistence — used when no backend is configured."""

    def save_strategy_memory(
        self, strategy_data: dict[str, dict], global_turn: int
    ) -> None:
        pass

    def load_strategy_memory(self) -> dict[str, Any] | None:
        return None


_PERSISTENCE: StrategyPersistence | None = None


def get_strategy_persistence() -> StrategyPersistence:
    """Get the configured strategy persistence backend.

    Falls back to EOS adapter if available, then NullStrategyPersistence.
    """
    global _PERSISTENCE
    if _PERSISTENCE is None:
        _PERSISTENCE = _default_persistence()
    return _PERSISTENCE


def set_strategy_persistence(backend: StrategyPersistence) -> None:
    """Override the strategy persistence backend."""
    global _PERSISTENCE
    _PERSISTENCE = backend


def reset_strategy_persistence() -> None:
    """Clear the persistence singleton (for testing)."""
    global _PERSISTENCE
    _PERSISTENCE = None


def _default_persistence() -> StrategyPersistence:
    from umh.adapters.bridge import discover_platform_adapter

    adapter = discover_platform_adapter(
        "umh.adapters.umh_strategy", "get_strategy_persistence_adapter"
    )
    if adapter is not None:
        return adapter
    return NullStrategyPersistence()
