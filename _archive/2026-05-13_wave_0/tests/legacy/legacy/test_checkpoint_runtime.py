"""Tests for runtime.substrate.checkpoint_runtime."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from umh.substrate.checkpoint_runtime import (
    CheckpointRuntime,
    CheckpointWriteResult,
    RuntimeCheckpoint,
    compute_snapshot_hash,
)


class TestCheckpointRuntime:
    """Test suite for CheckpointRuntime."""

    def _make_runtime(self, tmp_path: Path) -> CheckpointRuntime:
        return CheckpointRuntime(checkpoint_dir=tmp_path / "checkpoints")

    def test_write_and_load_latest(self, tmp_path: Path) -> None:
        """Write a checkpoint and load it back as latest."""
        rt = self._make_runtime(tmp_path)
        snapshot = {"session_name": "cc-vps", "status": "cleared"}
        result = rt.write_checkpoint(
            sequence_number=5,
            event_id="evt_abc",
            state_snapshot=snapshot,
        )
        assert result.ok
        assert result.sequence_number == 5

        latest = rt.load_latest_checkpoint()
        assert latest is not None
        assert latest.sequence_number == 5
        assert latest.state_snapshot == snapshot
        assert latest.event_id == "evt_abc"

    def test_load_latest_returns_highest_seq(self, tmp_path: Path) -> None:
        """load_latest_checkpoint returns the checkpoint with highest seq."""
        rt = self._make_runtime(tmp_path)
        for seq in [3, 7, 5, 10, 1]:
            rt.write_checkpoint(
                sequence_number=seq,
                event_id=f"evt_{seq}",
                state_snapshot={"seq": seq},
            )
        latest = rt.load_latest_checkpoint()
        assert latest is not None
        assert latest.sequence_number == 10

    def test_load_at_or_before(self, tmp_path: Path) -> None:
        """load_checkpoint_at_or_before returns correct checkpoint."""
        rt = self._make_runtime(tmp_path)
        for seq in [2, 5, 8, 12]:
            rt.write_checkpoint(
                sequence_number=seq,
                event_id=f"evt_{seq}",
                state_snapshot={"seq": seq},
            )

        # Exact match
        cp = rt.load_checkpoint_at_or_before(8)
        assert cp is not None
        assert cp.sequence_number == 8

        # Between checkpoints — returns lower
        cp = rt.load_checkpoint_at_or_before(7)
        assert cp is not None
        assert cp.sequence_number == 5

        # Before all checkpoints — returns None
        cp = rt.load_checkpoint_at_or_before(1)
        assert cp is None

        # After all checkpoints — returns highest
        cp = rt.load_checkpoint_at_or_before(100)
        assert cp is not None
        assert cp.sequence_number == 12

    def test_snapshot_hash_deterministic(self) -> None:
        """Same snapshot produces the same hash."""
        snap = {"a": 1, "b": [2, 3], "c": {"nested": True}}
        h1 = compute_snapshot_hash(snap)
        h2 = compute_snapshot_hash(snap)
        assert h1 == h2
        assert len(h1) == 64

    def test_snapshot_hash_changes_with_content(self) -> None:
        """Different snapshots produce different hashes."""
        s1 = {"status": "cleared"}
        s2 = {"status": "running"}
        assert compute_snapshot_hash(s1) != compute_snapshot_hash(s2)

    def test_directory_auto_created(self, tmp_path: Path) -> None:
        """Checkpoint directory is created on first write."""
        cp_dir = tmp_path / "deep" / "nested" / "checkpoints"
        rt = CheckpointRuntime(checkpoint_dir=cp_dir)
        result = rt.write_checkpoint(
            sequence_number=0,
            event_id="evt_0",
            state_snapshot={"initial": True},
        )
        assert result.ok
        assert cp_dir.exists()

    def test_load_latest_empty(self, tmp_path: Path) -> None:
        """load_latest_checkpoint returns None when no checkpoints exist."""
        rt = self._make_runtime(tmp_path)
        assert rt.load_latest_checkpoint() is None

    def test_list_checkpoints_ordered(self, tmp_path: Path) -> None:
        """list_checkpoints returns checkpoints ordered by seq ascending."""
        rt = self._make_runtime(tmp_path)
        for seq in [5, 1, 8, 3]:
            rt.write_checkpoint(
                sequence_number=seq,
                event_id=f"evt_{seq}",
                state_snapshot={"seq": seq},
            )
        cps = rt.list_checkpoints()
        seqs = [cp.sequence_number for cp in cps]
        assert seqs == [1, 3, 5, 8]

    def test_checkpoint_fields_populated(self, tmp_path: Path) -> None:
        """All RuntimeCheckpoint fields are correctly persisted and loaded."""
        rt = self._make_runtime(tmp_path)
        snap = {"session_name": "test", "status": "sealed"}
        result = rt.write_checkpoint(
            sequence_number=42,
            event_id="evt_xyz",
            state_snapshot=snap,
            completed_keys=["test:run_abc:terminal_seal_applied"],
            in_flight_execution_ids=["exec_1"],
            metadata={"trigger": "terminal_seal_applied"},
        )
        assert result.ok

        cp = rt.load_latest_checkpoint()
        assert cp is not None
        assert cp.sequence_number == 42
        assert cp.event_id == "evt_xyz"
        assert cp.state_snapshot == snap
        assert cp.completed_keys == ["test:run_abc:terminal_seal_applied"]
        assert cp.in_flight_execution_ids == ["exec_1"]
        assert cp.metadata == {"trigger": "terminal_seal_applied"}
        assert cp.snapshot_hash == compute_snapshot_hash(snap)
        assert cp.checkpoint_id.startswith("cp_")
        assert cp.created_at != ""
