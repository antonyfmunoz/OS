"""UMH Attention Queue — priority-ordered task execution queue.

Max-heap based on priority_score with stable ordering for equal scores
(older tasks first). Thread-safe. No execution, no side effects beyond
queue state management.
"""

from __future__ import annotations

import threading
from bisect import insort

from umh.attention.priority import AttentionState, PriorityEntry
from umh.attention.scorer import apply_starvation_boost

# ── Sort key ─────────────────────────────────────────────────────────────
# We want: highest priority_score first, then oldest created_at first.
# Python's bisect keeps ascending order, so we negate priority_score and
# use created_at ascending as the tiebreaker.


def _sort_key(entry: PriorityEntry) -> tuple[float, str]:
    return (-entry.priority_score, entry.created_at)


# ── Dispatchable states ──────────────────────────────────────────────────
_DISPATCHABLE = frozenset({AttentionState.READY, AttentionState.STARVED})


class AttentionQueue:
    """Thread-safe priority queue for attention entries."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: list[PriorityEntry] = []

    # ── mutators ─────────────────────────────────────────────────────────

    def enqueue(self, entry: PriorityEntry) -> None:
        """Insert an entry maintaining sort order."""
        with self._lock:
            insort(self._entries, entry, key=_sort_key)

    def dequeue(self) -> PriorityEntry | None:
        """Pop the highest-priority READY or STARVED entry."""
        with self._lock:
            for i, entry in enumerate(self._entries):
                if entry.state in _DISPATCHABLE:
                    return self._entries.pop(i)
            return None

    def peek(self) -> PriorityEntry | None:
        """Look at the highest-priority READY or STARVED entry without removing."""
        with self._lock:
            for entry in self._entries:
                if entry.state in _DISPATCHABLE:
                    return entry
            return None

    def remove(self, task_id: str) -> bool:
        """Remove an entry by task_id. Returns True if found."""
        with self._lock:
            for i, entry in enumerate(self._entries):
                if entry.task_id == task_id:
                    self._entries.pop(i)
                    return True
            return False

    def update_score(self, task_id: str, new_score: float) -> bool:
        """Update the priority score of an entry and re-sort."""
        with self._lock:
            for i, entry in enumerate(self._entries):
                if entry.task_id == task_id:
                    self._entries.pop(i)
                    updated = PriorityEntry(
                        task_id=entry.task_id,
                        goal_id=entry.goal_id,
                        priority_score=new_score,
                        breakdown=entry.breakdown,
                        state=entry.state,
                        age_seconds=entry.age_seconds,
                        starvation_boost=entry.starvation_boost,
                        created_at=entry.created_at,
                        id=entry.id,
                    )
                    insort(self._entries, updated, key=_sort_key)
                    return True
            return False

    def update_state(self, task_id: str, state: AttentionState) -> bool:
        """Update the attention state of an entry."""
        with self._lock:
            for entry in self._entries:
                if entry.task_id == task_id:
                    entry.state = state
                    return True
            return False

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._entries.clear()

    def apply_starvation_boost_all(
        self,
        current_time_seconds: float,
        threshold: float = 600.0,
    ) -> int:
        """Apply starvation boost to all READY entries exceeding age threshold.

        Returns count of entries boosted.
        """
        with self._lock:
            boosted = 0
            new_entries: list[PriorityEntry] = []
            for entry in self._entries:
                if entry.state == AttentionState.READY:
                    updated = apply_starvation_boost(entry, current_time_seconds, threshold)
                    if updated is not entry:
                        boosted += 1
                    new_entries.append(updated)
                else:
                    new_entries.append(entry)
            # Re-sort after boosting
            new_entries.sort(key=_sort_key)
            self._entries = new_entries
            return boosted

    # ── queries ──────────────────────────────────────────────────────────

    def list_ordered(self) -> list[PriorityEntry]:
        """Return all entries sorted by priority (highest first)."""
        with self._lock:
            return list(self._entries)

    def list_by_state(self, state: AttentionState) -> list[PriorityEntry]:
        """Return entries filtered by attention state, sorted by priority."""
        with self._lock:
            return [e for e in self._entries if e.state == state]

    def size(self) -> int:
        """Return total number of entries in the queue."""
        with self._lock:
            return len(self._entries)


# ── Module-level singleton ───────────────────────────────────────────────
_queue: AttentionQueue | None = None
_queue_lock = threading.Lock()


def get_attention_queue() -> AttentionQueue:
    """Return the module-level singleton AttentionQueue."""
    global _queue
    with _queue_lock:
        if _queue is None:
            _queue = AttentionQueue()
        return _queue


def reset_attention_queue() -> AttentionQueue:
    """Reset the singleton queue to a fresh instance."""
    global _queue
    with _queue_lock:
        _queue = AttentionQueue()
        return _queue
