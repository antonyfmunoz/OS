"""Tests for task_checkpoint — automatic task-boundary context hygiene."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS")


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Isolate archive and event store to temp files."""
    archive_path = str(tmp_path / "test_archive.jsonl")
    event_path = str(tmp_path / "test_events.jsonl")

    # Reset singletons
    from umh.runtime_engine.substrate import interaction_archive, event_store

    interaction_archive._archive = interaction_archive.InteractionArchive(
        path=archive_path
    )
    event_store._store = event_store.EventStore(path=event_path)

    # Disable auto-clear (no tmux in tests)
    monkeypatch.setenv("EOS_TASK_AUTOCLEAR_ENABLED", "0")

    yield

    interaction_archive._archive = None
    event_store._store = event_store.EventStore()


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestCheckpointTaskBoundary:
    def test_basic_checkpoint_returns_result(self):
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        result = checkpoint_task_boundary(
            task_id="task_abc",
            task_title="Build feature X",
            final_report="Feature X implemented successfully.",
        )

        assert result.task_id == "task_abc"
        assert result.task_title == "Build feature X"
        assert result.checkpoint_id.startswith("tcp_")
        assert result.archive_id  # should be non-empty
        assert result.spine_event_id  # should be non-empty
        assert result.auto_cleared is False  # disabled in fixture
        assert result.success

    def test_checkpoint_archives_verbatim(self):
        from umh.substrate.interaction_archive import get_interaction_archive
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        checkpoint_task_boundary(
            task_id="task_xyz",
            task_title="Deploy service",
            final_report="Service deployed to production.",
            interface="webhook",
            source_session="dex_builder_main",
        )

        archive = get_interaction_archive()
        recent = archive.recent(5)
        # Should have the task checkpoint record AND the clear checkpoint
        assert len(recent) >= 1

        # Find the task checkpoint (not the clear checkpoint)
        task_records = [
            r
            for r in recent
            if r.metadata.get("is_task_checkpoint") is True
        ]
        assert len(task_records) == 1
        assert "Deploy service" in task_records[0].raw_text
        assert task_records[0].interface == "webhook"

    def test_checkpoint_emits_spine_event(self):
        from umh.substrate.event_store import get_event_store
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        result = checkpoint_task_boundary(
            task_id="task_evt",
            task_title="Spine test",
            final_report="Done.",
        )

        event = get_event_store().get(result.spine_event_id)
        assert event is not None
        assert event.payload["type"] == "task_completed"
        assert event.payload["task_id"] == "task_evt"

    def test_checkpoint_creates_clear_checkpoint(self):
        from umh.substrate.interaction_archive import get_interaction_archive
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        result = checkpoint_task_boundary(
            task_id="task_clr",
            task_title="Clear test",
            final_report="Done.",
        )

        assert result.clear_checkpoint_id  # should be non-empty

        # Verify clear checkpoint in archive
        archive = get_interaction_archive()
        recent = archive.recent(10)
        clear_records = [
            r
            for r in recent
            if r.metadata.get("is_clear_checkpoint") is True
        ]
        assert len(clear_records) == 1
        assert "task_complete:task_clr" in clear_records[0].raw_text

    def test_carry_forward_items_preserved(self):
        from umh.substrate.interaction_archive import get_interaction_archive
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        result = checkpoint_task_boundary(
            task_id="task_carry",
            task_title="Carry test",
            final_report="Partial completion.",
            carry_forward=["Fix bug #42", "Update docs"],
        )

        assert result.carry_forward == ["Fix bug #42", "Update docs"]

        archive = get_interaction_archive()
        recent = archive.recent(10)
        task_records = [
            r
            for r in recent
            if r.metadata.get("is_task_checkpoint") is True
        ]
        assert len(task_records) == 1
        assert "Fix bug #42" in task_records[0].raw_text

    def test_result_to_dict(self):
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        result = checkpoint_task_boundary(
            task_id="task_dict",
            task_title="Dict test",
            final_report="OK.",
        )
        d = result.to_dict()
        assert d["task_id"] == "task_dict"
        assert d["success"] is True
        assert isinstance(d["errors"], list)

    def test_auto_clear_disabled_by_env(self, monkeypatch):
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        monkeypatch.setenv("EOS_TASK_AUTOCLEAR_ENABLED", "0")

        result = checkpoint_task_boundary(
            task_id="task_noclear",
            task_title="No clear",
            final_report="Done.",
            source_session="test_session",
        )

        assert result.auto_cleared is False

    def test_auto_clear_override_false(self):
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        result = checkpoint_task_boundary(
            task_id="task_override",
            task_title="Override",
            final_report="Done.",
            auto_clear=False,
        )

        assert result.auto_cleared is False

    def test_empty_task_id_works(self):
        from umh.substrate.task_checkpoint import checkpoint_task_boundary

        result = checkpoint_task_boundary(
            task_title="Unnamed task",
            final_report="Done.",
        )

        assert result.task_id == ""
        assert result.success


class TestAutoClearPolicy:
    def test_enabled_by_default(self, monkeypatch):
        monkeypatch.delenv("EOS_TASK_AUTOCLEAR_ENABLED", raising=False)

        from umh.substrate.task_checkpoint import AutoClearPolicy

        assert AutoClearPolicy.enabled() is True

    def test_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv("EOS_TASK_AUTOCLEAR_ENABLED", "0")

        from umh.substrate.task_checkpoint import AutoClearPolicy

        assert AutoClearPolicy.enabled() is False
