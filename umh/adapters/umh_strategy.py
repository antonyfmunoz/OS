"""EOS → UMH strategy persistence adapter.

Wraps the existing umh.persistence strategy memory functions to satisfy
the UMH StrategyPersistence protocol.
"""

from __future__ import annotations

from typing import Any


class StrategyPersistenceAdapter:
    """Adapts umh.persistence strategy functions to UMH StrategyPersistence protocol."""

    def save_strategy_memory(
        self, strategy_data: dict[str, dict], global_turn: int
    ) -> None:
        from umh.runtime_engine.persistence import save_strategy_memory

        save_strategy_memory(strategy_data, global_turn=global_turn)

    def load_strategy_memory(self) -> dict[str, Any] | None:
        from umh.runtime_engine.persistence import load_strategy_memory

        return load_strategy_memory()


_ADAPTER_INSTANCE: StrategyPersistenceAdapter | None = None


def get_strategy_persistence_adapter() -> StrategyPersistenceAdapter:
    """Get the singleton strategy persistence adapter."""
    global _ADAPTER_INSTANCE
    if _ADAPTER_INSTANCE is None:
        _ADAPTER_INSTANCE = StrategyPersistenceAdapter()
    return _ADAPTER_INSTANCE
