"""Tests for Phase 7A Agent 3: Memory CLI commands.

Covers:
1. cmd_memory — list memories (empty, populated, filtered, json)
2. cmd_memory_search — search (match, no match, json)
3. cmd_memory_add — add memory (valid, invalid type, json)
4. cmd_memory_stats — statistics (json + text)
5. Integration — add + list + search cycle
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest

from umh.memory.persistent_store import (
    MemoryPersistentStore,
    reset_memory_store,
)


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_memory(tmp_path, monkeypatch):
    """Use a fresh temp DB for every test."""
    db_path = str(tmp_path / "test_memory.sqlite")
    monkeypatch.setenv("UMH_MEMORY_DB_PATH", db_path)
    reset_memory_store()
    yield
    reset_memory_store()


def _cli_capture(*argv: str) -> tuple[int, str]:
    """Run CLI main() in-process and capture stdout."""
    from umh.control.cli import main as cli_main

    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = cli_main(list(argv))
    except SystemExit as e:
        rc = e.code if e.code is not None else 0
    finally:
        sys.stdout = old_stdout
    return rc, buf.getvalue()


def _seed_memories():
    """Seed a few memories for testing."""
    from umh.memory.persistent_store import get_memory_store

    store = get_memory_store()
    store.save_memory(type="task", content="Completed lead outreach", tags=["crm", "outreach"])
    store.save_memory(type="insight", content="Conversion rate improved by 15%", tags=["metrics"])
    store.save_memory(type="summary", content="Daily standup notes from Monday", tags=["standup"])
    store.save_memory(type="system", content="Database migration completed", tags=["ops"])
    return store


# ── 1. cmd_memory — list ────────────────────────────────────────────


class TestCmdMemory:
    """Memory list command."""

    def test_memory_empty_state(self):
        rc, stdout = _cli_capture("memory")
        assert rc == 0
        assert "No memories." in stdout

    def test_memory_lists_after_adding(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory")
        assert rc == 0
        assert "task" in stdout
        assert "insight" in stdout
        assert "summary" in stdout
        assert "system" in stdout

    def test_memory_filters_by_type(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory", "--type", "insight")
        assert rc == 0
        assert "Conversion rate" in stdout
        # Should not contain task or summary content
        assert "lead outreach" not in stdout

    def test_memory_json_output(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory", "--json")
        assert rc == 0
        data = json.loads(stdout)
        assert isinstance(data, list)
        assert len(data) == 4
        # Verify structure
        first = data[0]
        assert "id" in first
        assert "type" in first
        assert "content" in first
        assert "tags" in first
        assert "created_at" in first

    def test_memory_limit_flag(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory", "--limit", "2", "--json")
        assert rc == 0
        data = json.loads(stdout)
        assert len(data) == 2


# ── 2. cmd_memory_search ────────────────────────────────────────────


class TestCmdMemorySearch:
    """Memory search command."""

    def test_search_finds_matches(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory-search", "outreach")
        assert rc == 0
        assert "outreach" in stdout.lower()

    def test_search_no_matches(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory-search", "nonexistent_xyz_term")
        assert rc == 0
        assert "No matches." in stdout

    def test_search_json_output(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory-search", "Conversion", "--json")
        assert rc == 0
        data = json.loads(stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "Conversion" in data[0]["content"]

    def test_search_by_tag(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory-search", "crm")
        assert rc == 0
        assert "outreach" in stdout.lower()

    def test_search_limit(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory-search", "e", "--limit", "1", "--json")
        assert rc == 0
        data = json.loads(stdout)
        assert len(data) <= 1


# ── 3. cmd_memory_add ───────────────────────────────────────────────


class TestCmdMemoryAdd:
    """Memory add command."""

    def test_add_creates_memory(self):
        rc, stdout = _cli_capture("memory-add", "--type", "insight", "--content", "Test insight")
        assert rc == 0
        assert "Saved:" in stdout

    def test_add_json_output(self):
        rc, stdout = _cli_capture(
            "memory-add", "--type", "task", "--content", "Test task", "--json"
        )
        assert rc == 0
        data = json.loads(stdout)
        assert data["type"] == "task"
        assert data["content"] == "Test task"
        assert "id" in data
        assert "created_at" in data

    def test_add_validates_type(self):
        rc, stdout = _cli_capture("memory-add", "--type", "invalid_type", "--content", "Nope")
        assert rc == 1
        assert "Invalid type" in stdout

    def test_add_validates_type_json(self):
        rc, stdout = _cli_capture("memory-add", "--type", "bogus", "--content", "Nope", "--json")
        assert rc == 1
        data = json.loads(stdout)
        assert "error" in data

    def test_add_with_tags(self):
        rc, stdout = _cli_capture(
            "memory-add",
            "--type",
            "insight",
            "--content",
            "Tagged insight",
            "--tags",
            "alpha,beta",
            "--json",
        )
        assert rc == 0
        data = json.loads(stdout)
        assert data["tags"] == ["alpha", "beta"]

    def test_add_with_empty_tags(self):
        rc, stdout = _cli_capture(
            "memory-add", "--type", "insight", "--content", "No tags", "--tags", "", "--json"
        )
        assert rc == 0
        data = json.loads(stdout)
        assert data["tags"] == []


# ── 4. cmd_memory_stats ────────────────────────────────────────────


class TestCmdMemoryStats:
    """Memory stats command."""

    def test_stats_empty(self):
        rc, stdout = _cli_capture("memory-stats")
        assert rc == 0
        assert "Total: 0" in stdout

    def test_stats_with_data(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory-stats")
        assert rc == 0
        assert "Total: 4" in stdout
        assert "task: 1" in stdout
        assert "insight: 1" in stdout
        assert "summary: 1" in stdout
        assert "system: 1" in stdout

    def test_stats_json_output(self):
        _seed_memories()
        rc, stdout = _cli_capture("memory-stats", "--json")
        assert rc == 0
        data = json.loads(stdout)
        assert data["total"] == 4
        assert data["task"] == 1
        assert data["insight"] == 1
        assert data["summary"] == 1
        assert data["system"] == 1


# ── 5. Integration ─────────────────────────────────────────────────


class TestMemoryIntegration:
    """End-to-end: add, list, search cycle."""

    def test_add_list_search_cycle(self):
        # Add
        rc, stdout = _cli_capture(
            "memory-add",
            "--type",
            "insight",
            "--content",
            "Integration test memory",
            "--tags",
            "test,e2e",
            "--json",
        )
        assert rc == 0
        added = json.loads(stdout)
        mem_id = added["id"]

        # List — should contain the new memory
        rc, stdout = _cli_capture("memory", "--json")
        assert rc == 0
        all_memories = json.loads(stdout)
        ids = [m["id"] for m in all_memories]
        assert mem_id in ids

        # Search by content
        rc, stdout = _cli_capture("memory-search", "Integration", "--json")
        assert rc == 0
        results = json.loads(stdout)
        assert len(results) >= 1
        assert any(m["id"] == mem_id for m in results)

        # Search by tag
        rc, stdout = _cli_capture("memory-search", "e2e", "--json")
        assert rc == 0
        results = json.loads(stdout)
        assert any(m["id"] == mem_id for m in results)

        # Stats
        rc, stdout = _cli_capture("memory-stats", "--json")
        assert rc == 0
        stats = json.loads(stdout)
        assert stats["total"] >= 1
        assert stats["insight"] >= 1
