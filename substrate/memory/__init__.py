"""Memory candidate staging, promotion, auto-reconciliation, bridging, and watching."""

from substrate.memory.candidate_generator import MemoryCandidateGenerator
from substrate.memory.promoter import MemoryPromoter
from substrate.memory.auto_reconciler import AutoReconciler
from substrate.memory.claude_bridge import ClaudeMemoryBridge

__all__ = [
    "MemoryCandidateGenerator",
    "MemoryPromoter",
    "AutoReconciler",
    "ClaudeMemoryBridge",
    "MemoryWatcher",
    "start_memory_watcher",
]


def __getattr__(name: str):
    if name in ("MemoryWatcher", "start_memory_watcher"):
        from substrate.memory.watcher import MemoryWatcher, start_memory_watcher
        return MemoryWatcher if name == "MemoryWatcher" else start_memory_watcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
