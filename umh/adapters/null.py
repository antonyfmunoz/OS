"""Centralized null adapter registry.

Re-exports all null/stub adapter implementations from their canonical
locations for convenient import:

    from umh.adapters.null import NullLLMAdapter, NullShellAdapter
"""

from __future__ import annotations

from umh.adapters.base import (
    NullBrowserAdapter,
    NullFilesystemAdapter,
    NullLLMAdapter,
    NullShellAdapter,
    NullWorkstationAdapter,
)
from umh.execution.interfaces import NullExecutionBackend, NullExecutionObserver
from umh.goals.interfaces import NullGoalPersistence
from umh.strategy.interfaces import NullStrategyPersistence
from umh.signal.event_bus import NullLogger

__all__ = [
    "NullBrowserAdapter",
    "NullExecutionBackend",
    "NullExecutionObserver",
    "NullFilesystemAdapter",
    "NullGoalPersistence",
    "NullLLMAdapter",
    "NullLogger",
    "NullShellAdapter",
    "NullStrategyPersistence",
    "NullWorkstationAdapter",
]
