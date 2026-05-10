"""Phase 9A — Attention queue tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.attention.priority import AttentionState, PriorityBreakdown, PriorityEntry
from umh.attention.queue import AttentionQueue, get_attention_queue, reset_attention_queue


# ── helpers ──────────────────────────────────────────────────────────────


def _entry(
    task_id: str,
    score: float = 0.5,
    state: AttentionState = AttentionState.READY,
    created_at: str = "",
) -> PriorityEntry:
    return PriorityEntry(
        task_id=task_id,
        priority_score=score,
        state=state,
        created_at=created_at or "",
    )


# ── TestAttentionQueue ───────────────────────────────────────────────────


class TestAttentionQueue:
    def setup_method(self):
        self.q = AttentionQueue()

    def test_enqueue_dequeue(self):
        e = _entry("t1", score=0.5)
        self.q.enqueue(e)
        result = self.q.dequeue()
        assert result is not None
        assert result.task_id == "t1"

    def test_dequeue_empty(self):
        assert self.q.dequeue() is None

    def test_priority_ordering(self):
        self.q.enqueue(_entry("low", score=0.2))
        self.q.enqueue(_entry("high", score=0.9))
        self.q.enqueue(_entry("mid", score=0.5))
        first = self.q.dequeue()
        assert first is not None
        assert first.task_id == "high"
        second = self.q.dequeue()
        assert second is not None
        assert second.task_id == "mid"

    def test_stable_ordering(self):
        """Same score: older entry (earlier created_at) dequeued first."""
        e1 = _entry("older", score=0.5, created_at="2026-01-01T00:00:00Z")
        e2 = _entry("newer", score=0.5, created_at="2026-01-02T00:00:00Z")
        self.q.enqueue(e2)
        self.q.enqueue(e1)
        first = self.q.dequeue()
        assert first is not None
        assert first.task_id == "older"

    def test_peek(self):
        self.q.enqueue(_entry("t1", score=0.8))
        peeked = self.q.peek()
        assert peeked is not None
        assert peeked.task_id == "t1"
        # Still in queue
        assert self.q.size() == 1

    def test_remove(self):
        self.q.enqueue(_entry("t1", score=0.5))
        removed = self.q.remove("t1")
        assert removed is True
        assert self.q.dequeue() is None

    def test_update_score(self):
        self.q.enqueue(_entry("low", score=0.2))
        self.q.enqueue(_entry("high", score=0.9))
        # Promote low to top
        self.q.update_score("low", 1.0)
        first = self.q.dequeue()
        assert first is not None
        assert first.task_id == "low"

    def test_update_state(self):
        self.q.enqueue(_entry("t1", score=0.5))
        self.q.update_state("t1", AttentionState.BLOCKED)
        # Blocked entries skipped by dequeue
        assert self.q.dequeue() is None

    def test_list_ordered(self):
        self.q.enqueue(_entry("a", score=0.3))
        self.q.enqueue(_entry("b", score=0.9))
        self.q.enqueue(_entry("c", score=0.6))
        ordered = self.q.list_ordered()
        assert len(ordered) == 3
        assert ordered[0].task_id == "b"
        assert ordered[1].task_id == "c"
        assert ordered[2].task_id == "a"

    def test_list_by_state(self):
        self.q.enqueue(_entry("ready1", state=AttentionState.READY))
        self.q.enqueue(_entry("blocked1", state=AttentionState.BLOCKED))
        self.q.enqueue(_entry("ready2", state=AttentionState.READY))
        ready = self.q.list_by_state(AttentionState.READY)
        assert len(ready) == 2
        blocked = self.q.list_by_state(AttentionState.BLOCKED)
        assert len(blocked) == 1

    def test_size(self):
        assert self.q.size() == 0
        self.q.enqueue(_entry("t1"))
        self.q.enqueue(_entry("t2"))
        assert self.q.size() == 2
        self.q.dequeue()
        assert self.q.size() == 1

    def test_clear(self):
        self.q.enqueue(_entry("t1"))
        self.q.enqueue(_entry("t2"))
        self.q.clear()
        assert self.q.size() == 0

    def test_dequeue_skips_blocked(self):
        self.q.enqueue(_entry("t1", score=0.9, state=AttentionState.BLOCKED))
        self.q.enqueue(_entry("t2", score=0.1, state=AttentionState.READY))
        result = self.q.dequeue()
        assert result is not None
        assert result.task_id == "t2"

    def test_dequeue_skips_deferred(self):
        self.q.enqueue(_entry("t1", score=0.9, state=AttentionState.DEFERRED))
        assert self.q.dequeue() is None

    def test_dequeue_skips_running(self):
        self.q.enqueue(_entry("t1", score=0.9, state=AttentionState.RUNNING))
        assert self.q.dequeue() is None

    def test_dequeue_returns_starved(self):
        self.q.enqueue(_entry("t1", score=0.5, state=AttentionState.STARVED))
        result = self.q.dequeue()
        assert result is not None
        assert result.task_id == "t1"

    def test_starvation_boost_all(self):
        # Entry with age_seconds=0 but we pass current_time=900 with threshold=600
        e = _entry("t1", score=0.3, state=AttentionState.READY)
        self.q.enqueue(e)
        boosted = self.q.apply_starvation_boost_all(current_time_seconds=900, threshold=600)
        assert boosted == 1
        entries = self.q.list_ordered()
        assert entries[0].state == AttentionState.STARVED

    def test_singleton(self):
        reset_attention_queue()
        q1 = get_attention_queue()
        q2 = get_attention_queue()
        assert q1 is q2
        q3 = reset_attention_queue()
        assert q3 is not q1
