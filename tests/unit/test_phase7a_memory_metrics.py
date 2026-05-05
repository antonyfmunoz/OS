"""Tests for umh.memory.metrics — memory statistics and search tracking."""

from __future__ import annotations

import os
import threading

import pytest

os.environ.setdefault("UMH_ENV", "test")


@pytest.fixture(autouse=True)
def _isolate(tmp_path):
    """Point memory store at a temp DB and reset metrics between tests."""
    db_path = str(tmp_path / "test_metrics_memory.sqlite")
    os.environ["UMH_MEMORY_DB_PATH"] = db_path

    from umh.memory.persistent_store import reset_memory_store
    from umh.memory.metrics import reset_metrics

    reset_memory_store()
    reset_metrics()
    yield
    reset_memory_store()
    reset_metrics()
    os.environ.pop("UMH_MEMORY_DB_PATH", None)


class TestGetMemoryMetrics:
    """get_memory_metrics tests."""

    def test_returns_correct_structure(self):
        from umh.memory.metrics import get_memory_metrics

        m = get_memory_metrics()

        assert "total_memories" in m
        assert "by_type" in m
        assert "memory_searches" in m
        assert "memory_hits" in m
        assert "memory_miss_rate" in m

        assert isinstance(m["total_memories"], int)
        assert isinstance(m["by_type"], dict)
        assert isinstance(m["memory_searches"], int)
        assert isinstance(m["memory_hits"], int)
        assert isinstance(m["memory_miss_rate"], float)

    def test_counts_by_type(self):
        from umh.memory.metrics import get_memory_metrics
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(type="task", content="task 1")
        store.save_memory(type="task", content="task 2")
        store.save_memory(type="summary", content="summary 1")
        store.save_memory(type="insight", content="insight 1")

        m = get_memory_metrics()

        assert m["total_memories"] == 4
        assert m["by_type"]["task"] == 2
        assert m["by_type"]["summary"] == 1
        assert m["by_type"]["insight"] == 1
        assert m["by_type"]["system"] == 0


class TestTrackSearch:
    """track_search tests."""

    def test_increments_counters(self):
        from umh.memory.metrics import track_search, get_memory_metrics

        track_search(3)

        m = get_memory_metrics()
        assert m["memory_searches"] == 1

    def test_with_results_increments_hits(self):
        from umh.memory.metrics import track_search, get_memory_metrics

        track_search(5)
        track_search(2)

        m = get_memory_metrics()
        assert m["memory_searches"] == 2
        assert m["memory_hits"] == 2

    def test_with_zero_results_is_miss(self):
        from umh.memory.metrics import track_search, get_memory_metrics

        track_search(0)

        m = get_memory_metrics()
        assert m["memory_searches"] == 1
        assert m["memory_hits"] == 0

    def test_miss_rate_calculation(self):
        from umh.memory.metrics import track_search, get_memory_metrics

        track_search(5)  # hit
        track_search(0)  # miss
        track_search(0)  # miss
        track_search(3)  # hit

        m = get_memory_metrics()
        assert m["memory_searches"] == 4
        assert m["memory_hits"] == 2
        # miss_rate = misses / total = 2/4 = 0.5
        assert m["memory_miss_rate"] == pytest.approx(0.5)

    def test_miss_rate_zero_when_no_searches(self):
        from umh.memory.metrics import get_memory_metrics

        m = get_memory_metrics()
        assert m["memory_miss_rate"] == 0.0


class TestResetMetrics:
    """reset_metrics tests."""

    def test_clears_counters(self):
        from umh.memory.metrics import track_search, reset_metrics, get_memory_metrics

        track_search(1)
        track_search(0)
        track_search(5)

        reset_metrics()

        m = get_memory_metrics()
        assert m["memory_searches"] == 0
        assert m["memory_hits"] == 0
        assert m["memory_miss_rate"] == 0.0


class TestThreadSafety:
    """Concurrent track_search calls."""

    def test_concurrent_track_search(self):
        from umh.memory.metrics import track_search, get_memory_metrics

        n_threads = 10
        calls_per_thread = 100
        barrier = threading.Barrier(n_threads)

        def _worker():
            barrier.wait()
            for _ in range(calls_per_thread):
                track_search(1)

        threads = [threading.Thread(target=_worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        m = get_memory_metrics()
        assert m["memory_searches"] == n_threads * calls_per_thread
        assert m["memory_hits"] == n_threads * calls_per_thread
