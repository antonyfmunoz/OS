"""Integration tests for runtime bootstrap + event log + checkpoint.

Verifies that the full write path works end-to-end:
- Event log writes succeed
- Checkpoint writes succeed
- Bootstrap singletons work
- No existing public imports break
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from umh.substrate.checkpoint_runtime import CheckpointRuntime
from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.runtime_bootstrap import (
    _reset_for_testing,
    get_checkpoint_runtime,
    get_event_log_runtime,
    get_runtime_state_store,
)
from umh.substrate.runtime_state_store import RuntimeStateStore


class TestRuntimeBootstrapIntegration:
    """Integration tests for the runtime bootstrap layer."""

    def setup_method(self) -> None:
        """Reset singletons before each test."""
        _reset_for_testing()

    def test_terminal_lifecycle_event_write(self, tmp_path: Path) -> None:
        """Writing a terminal lifecycle event through bootstrap succeeds."""
        log_file = tmp_path / "events.jsonl"
        _reset_for_testing(log_path=log_file)

        log = get_event_log_runtime()
        result = log.append(
            event_type="terminal_seal_applied",
            session_name="cc-vps",
            source="lifecycle_manager",
            run_id="run_abc123",
            payload={"detail": "lifecycle CLOSED via clear_completed"},
            state_mutations=[
                {"op": "SET", "key": "terminally_finalized", "value": True},
            ],
            metadata={"generation": 3, "task_id": "t_xyz"},
        )
        assert result.ok
        assert result.sequence_number == 0

        # Verify persisted
        events = log.read_all()
        assert len(events) == 1
        assert events[0].event_type == "terminal_seal_applied"

    def test_checkpoint_write_succeeds(self, tmp_path: Path) -> None:
        """Writing a checkpoint through bootstrap succeeds."""
        cp_dir = tmp_path / "checkpoints"
        _reset_for_testing(checkpoint_dir=cp_dir)

        cp = get_checkpoint_runtime()
        result = cp.write_checkpoint(
            sequence_number=5,
            event_id="evt_abc",
            state_snapshot={
                "session_name": "cc-vps",
                "run_id": "run_abc123",
                "status": "cleared",
                "finalization_status": "succeeded",
                "publication_confirmed": True,
                "clear_status": "confirmed",
                "terminally_finalized": False,
                "trigger_event": "clear_confirmed",
            },
            completed_keys=["cc-vps:run_abc123:clear_confirmed"],
            metadata={"trigger": "clear_confirmed"},
        )
        assert result.ok
        assert result.sequence_number == 5

        latest = cp.load_latest_checkpoint()
        assert latest is not None
        assert latest.state_snapshot["session_name"] == "cc-vps"

    def test_state_store_through_bootstrap(self, tmp_path: Path) -> None:
        """RuntimeStateStore works through bootstrap singleton."""
        _reset_for_testing()

        store = get_runtime_state_store()
        store.apply_mutations(
            [
                {"op": "SET", "key": "status", "value": "running"},
                {"op": "INCREMENT", "key": "gen"},
            ]
        )
        assert store.get("status") == "running"
        assert store.get("gen") == 1

    def test_singletons_are_stable(self, tmp_path: Path) -> None:
        """Multiple calls return the same instance."""
        log_file = tmp_path / "events.jsonl"
        cp_dir = tmp_path / "checkpoints"
        _reset_for_testing(log_path=log_file, checkpoint_dir=cp_dir)

        log1 = get_event_log_runtime()
        log2 = get_event_log_runtime()
        assert log1 is log2

        cp1 = get_checkpoint_runtime()
        cp2 = get_checkpoint_runtime()
        assert cp1 is cp2

        store1 = get_runtime_state_store()
        store2 = get_runtime_state_store()
        assert store1 is store2

    def test_full_lifecycle_flow(self, tmp_path: Path) -> None:
        """Simulate a full lifecycle: event → event → checkpoint."""
        log_file = tmp_path / "events.jsonl"
        cp_dir = tmp_path / "checkpoints"
        _reset_for_testing(log_path=log_file, checkpoint_dir=cp_dir)

        log = get_event_log_runtime()
        cp = get_checkpoint_runtime()
        store = get_runtime_state_store()

        # 1. Finalization succeeded
        r1 = log.append(
            event_type="finalization_succeeded",
            session_name="cc-vps",
            source="watcher",
            run_id="run_001",
            state_mutations=[
                {"op": "SET", "key": "finalization_status", "value": "succeeded"},
            ],
        )
        assert r1.ok
        store.apply_mutations(
            r1.ok
            and [
                {"op": "SET", "key": "finalization_status", "value": "succeeded"},
            ]
            or []
        )

        # 2. Publication confirmed
        r2 = log.append(
            event_type="publication_confirmed",
            session_name="cc-vps",
            source="discord_bridge",
            run_id="run_001",
            causal_event_id=r1.event_id,
            state_mutations=[
                {"op": "SET", "key": "publication_confirmed", "value": True},
            ],
        )
        assert r2.ok
        store.apply_mutations(
            [
                {"op": "SET", "key": "publication_confirmed", "value": True},
            ]
        )

        # 3. Clear confirmed
        r3 = log.append(
            event_type="clear_confirmed",
            session_name="cc-vps",
            source="session_control",
            run_id="run_001",
            causal_event_id=r2.event_id,
            state_mutations=[
                {"op": "SET", "key": "clear_status", "value": "confirmed"},
            ],
        )
        assert r3.ok

        # 4. Write checkpoint at clear boundary
        cp_result = cp.write_checkpoint(
            sequence_number=r3.sequence_number,
            event_id=r3.event_id,
            state_snapshot=store.snapshot(),
        )
        assert cp_result.ok

        # Verify the full chain
        all_events = log.read_all()
        assert len(all_events) == 3
        assert [e.event_type for e in all_events] == [
            "finalization_succeeded",
            "publication_confirmed",
            "clear_confirmed",
        ]

        latest_cp = cp.load_latest_checkpoint()
        assert latest_cp is not None
        assert latest_cp.state_snapshot["finalization_status"] == "succeeded"
        assert latest_cp.state_snapshot["publication_confirmed"] is True

    def test_existing_imports_not_broken(self) -> None:
        """Verify that existing substrate public imports still work."""
        # These are the most critical existing exports
        from umh.substrate.run_lifecycle import (
            ClearDecision,
            ClearStatus,
            CompletionProposal,
            FinalizationDecision,
            FinalizationStatus,
            ForensicEntry,
            RunHandle,
            RunLifecycleRecord,
            RunStatus,
        )

        # Verify the record dataclass still works
        record = RunLifecycleRecord(source_session="test", generation=1)
        assert record.status == RunStatus.RUNNING
        assert record.finalization_status == FinalizationStatus.NOT_STARTED
        assert record.clear_status == ClearStatus.NOT_REQUESTED
