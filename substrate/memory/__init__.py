"""Memory candidate staging, promotion, auto-reconciliation, bridging, and watching."""

from substrate.memory.candidate_generator import MemoryCandidateGenerator
from substrate.memory.promoter import MemoryPromoter
from substrate.memory.auto_reconciler import AutoReconciler
from substrate.memory.claude_bridge import ClaudeMemoryBridge
from substrate.memory.watcher import MemoryWatcher, start_memory_watcher

__all__ = [
    "MemoryCandidateGenerator",
    "MemoryPromoter",
    "AutoReconciler",
    "ClaudeMemoryBridge",
    "MemoryWatcher",
    "start_memory_watcher",
]
