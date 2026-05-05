"""UMH Memory Metrics — memory statistics for the metrics endpoint.

Thread-safe counters for search tracking and type-level breakdown
of stored memories.
"""

from __future__ import annotations

import threading

from umh.memory.persistent_store import get_memory_store, VALID_MEMORY_TYPES

_lock = threading.Lock()
_search_count: int = 0
_search_hits: int = 0


def track_search(result_count: int) -> None:
    """Track a memory search for metrics.

    Call after each search with the number of results returned.
    A result_count > 0 counts as a hit; 0 counts as a miss.
    """
    global _search_count, _search_hits
    with _lock:
        _search_count += 1
        if result_count > 0:
            _search_hits += 1


def reset_metrics() -> None:
    """Reset search counters (for testing)."""
    global _search_count, _search_hits
    with _lock:
        _search_count = 0
        _search_hits = 0


def get_memory_metrics() -> dict:
    """Return memory statistics for the metrics endpoint."""
    store = get_memory_store()

    total = store.count_memories()

    by_type: dict[str, int] = {}
    for mtype in sorted(VALID_MEMORY_TYPES):
        by_type[mtype] = len(store.list_memories(type=mtype, limit=10_000))

    with _lock:
        searches = _search_count
        hits = _search_hits

    misses = searches - hits
    miss_rate = misses / searches if searches > 0 else 0.0

    return {
        "total_memories": total,
        "by_type": by_type,
        "memory_searches": searches,
        "memory_hits": hits,
        "memory_miss_rate": miss_rate,
    }
