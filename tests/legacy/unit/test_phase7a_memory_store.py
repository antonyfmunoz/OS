"""Tests for Phase 7A: Memory + Context Engine.

Verifies:
- SQLite-backed persistent memory store (CRUD, search, validation)
- Context retrieval layer (relevance scoring, deduplication, formatting)
- Thread safety under concurrent writes
- Singleton lifecycle (reset clears state)
"""

import os
import sys
import tempfile
import threading

sys.path.insert(0, "/opt/OS")


def _setup_temp_db():
    """Create a temp directory and set env var for memory DB."""
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test_memory.sqlite")
    os.environ["UMH_MEMORY_DB_PATH"] = db_path
    return tmp, db_path


def _teardown(tmp_dir: str):
    """Reset singleton and clean env."""
    from umh.memory.persistent_store import reset_memory_store

    reset_memory_store()
    os.environ.pop("UMH_MEMORY_DB_PATH", None)
    import shutil

    shutil.rmtree(tmp_dir, ignore_errors=True)


# ── A. save_memory ──────────────────────────────────────────────────────


class TestSaveMemory:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_save_creates_with_correct_fields(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        mem = store.save_memory(
            type="task",
            content="complete the outreach sequence",
            metadata={"priority": "high"},
            tags=["outreach", "leads"],
        )
        assert mem.id is not None
        assert mem.type == "task"
        assert mem.content == "complete the outreach sequence"
        assert mem.metadata == {"priority": "high"}
        assert mem.tags == ["outreach", "leads"]
        assert mem.created_at != ""


# ── B. get_memory ───────────────────────────────────────────────────────


class TestGetMemory:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_get_retrieves_by_id(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        mem = store.save_memory(type="insight", content="leads convert better on Tuesday")
        retrieved = store.get_memory(mem.id)
        assert retrieved is not None
        assert retrieved.id == mem.id
        assert retrieved.content == "leads convert better on Tuesday"
        assert retrieved.type == "insight"

    def test_get_returns_none_for_unknown_id(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        assert store.get_memory("nonexistent-id-12345") is None


# ── C. list_memories ────────────────────────────────────────────────────


class TestListMemories:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_list_returns_all_most_recent_first(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(type="task", content="first")
        store.save_memory(type="insight", content="second")
        store.save_memory(type="summary", content="third")
        results = store.list_memories()
        assert len(results) == 3
        assert results[0].content == "third"
        assert results[2].content == "first"

    def test_list_filters_by_type(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(type="task", content="task one")
        store.save_memory(type="insight", content="insight one")
        store.save_memory(type="task", content="task two")
        results = store.list_memories(type="task")
        assert len(results) == 2
        assert all(r.type == "task" for r in results)

    def test_list_respects_limit(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        for i in range(10):
            store.save_memory(type="system", content=f"entry {i}")
        results = store.list_memories(limit=3)
        assert len(results) == 3


# ── D. search_memories ──────────────────────────────────────────────────


class TestSearchMemories:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_search_finds_by_content_keyword(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(type="insight", content="email outreach converts at 3%")
        store.save_memory(type="task", content="build landing page")
        results = store.search_memories("outreach")
        assert len(results) == 1
        assert "outreach" in results[0].content

    def test_search_finds_by_tag(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(type="task", content="generic content", tags=["marketing"])
        store.save_memory(type="task", content="other content", tags=["engineering"])
        results = store.search_memories("marketing")
        assert len(results) == 1
        assert "marketing" in results[0].tags

    def test_search_returns_empty_for_no_match(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(type="task", content="something unrelated")
        results = store.search_memories("zzz_nonexistent_zzz")
        assert results == []


# ── E. delete_memory ────────────────────────────────────────────────────


class TestDeleteMemory:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_delete_removes_and_returns_true(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        mem = store.save_memory(type="task", content="to delete")
        assert store.delete_memory(mem.id) is True
        assert store.get_memory(mem.id) is None

    def test_delete_returns_false_for_unknown_id(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        assert store.delete_memory("nonexistent-id-99999") is False


# ── F. count_memories ───────────────────────────────────────────────────


class TestCountMemories:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_count_returns_correct_count(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        assert store.count_memories() == 0
        store.save_memory(type="task", content="one")
        store.save_memory(type="insight", content="two")
        assert store.count_memories() == 2


# ── G. Type Validation ──────────────────────────────────────────────────


class TestTypeValidation:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_invalid_type_raises_value_error(self):
        import pytest

        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        with pytest.raises(ValueError, match="Invalid memory type"):
            store.save_memory(type="invalid_type", content="bad")

    def test_all_valid_types_accepted(self):
        from umh.memory.persistent_store import VALID_MEMORY_TYPES, get_memory_store

        store = get_memory_store()
        for t in VALID_MEMORY_TYPES:
            mem = store.save_memory(type=t, content=f"content for {t}")
            assert mem.type == t


# ── H. Context Retrieval ────────────────────────────────────────────────


class TestGetRelevantContext:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_returns_scored_results(self):
        from umh.memory.context import get_relevant_context
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(type="insight", content="outreach emails need better subject lines")
        store.save_memory(type="task", content="build outreach automation pipeline")

        results = get_relevant_context("improve outreach email conversion")
        assert len(results) >= 1
        assert all("relevance_score" in r for r in results)
        assert results[0]["relevance_score"] >= results[-1]["relevance_score"]

    def test_deduplicates_results(self):
        from umh.memory.context import get_relevant_context
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(
            type="insight",
            content="outreach conversion rates improved after email subject change",
            tags=["outreach", "conversion"],
        )

        results = get_relevant_context("outreach conversion email")
        ids = [r["id"] for r in results]
        assert len(ids) == len(set(ids))

    def test_returns_empty_for_no_matches(self):
        from umh.memory.context import get_relevant_context
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        store.save_memory(type="task", content="unrelated content here")

        results = get_relevant_context("zzz_xylophone_quantum_zzz")
        assert results == []


# ── I. format_context_for_planner ───────────────────────────────────────


class TestFormatContextForPlanner:
    def test_produces_correct_format(self):
        from umh.memory.context import format_context_for_planner

        memories = [
            {
                "id": "1",
                "type": "insight",
                "content": "leads convert on Tuesday",
                "tags": ["leads", "timing"],
                "created_at": "2026-04-27T12:00:00+00:00",
                "relevance_score": 2.5,
            },
            {
                "id": "2",
                "type": "task",
                "content": "send follow-up emails",
                "tags": [],
                "created_at": "2026-04-27T11:00:00+00:00",
                "relevance_score": 1.2,
            },
        ]
        result = format_context_for_planner(memories)
        assert result.startswith("Relevant context from memory:")
        assert "- [insight] leads convert on Tuesday (leads, timing)" in result
        assert "- [task] send follow-up emails" in result

    def test_returns_empty_string_for_empty_list(self):
        from umh.memory.context import format_context_for_planner

        assert format_context_for_planner([]) == ""


# ── J. Singleton Lifecycle ──────────────────────────────────────────────


class TestSingletonLifecycle:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_reset_clears_singleton(self):
        from umh.memory.persistent_store import get_memory_store, reset_memory_store

        store1 = get_memory_store()
        reset_memory_store()
        store2 = get_memory_store()
        assert store1 is not store2


# ── K. Thread Safety ────────────────────────────────────────────────────


class TestThreadSafety:
    def setup_method(self):
        self._tmp, self._db = _setup_temp_db()
        from umh.memory.persistent_store import reset_memory_store

        reset_memory_store()

    def teardown_method(self):
        _teardown(self._tmp)

    def test_concurrent_saves_no_corruption(self):
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        errors: list[Exception] = []
        num_threads = 10
        saves_per_thread = 5

        def writer(thread_id: int):
            try:
                for i in range(saves_per_thread):
                    store.save_memory(
                        type="task",
                        content=f"thread {thread_id} save {i}",
                        tags=[f"thread-{thread_id}"],
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert store.count_memories() == num_threads * saves_per_thread
