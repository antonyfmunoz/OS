"""Tests for eos_ai.substrate.event_log_runtime."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_log_runtime import (
    EventAppendResult,
    EventEnvelope,
    EventLogRuntime,
    compute_mutation_hash,
)


class TestEventLogRuntime:
    """Test suite for EventLogRuntime."""

    def _make_runtime(self, tmp_path: Path) -> EventLogRuntime:
        log_file = tmp_path / "test_event_log.jsonl"
        return EventLogRuntime(log_path=log_file)

    def test_append_creates_file(self, tmp_path: Path) -> None:
        """Appending to a non-existent file creates it."""
        log_file = tmp_path / "subdir" / "events.jsonl"
        rt = EventLogRuntime(log_path=log_file)
        result = rt.append(
            event_type="finalization_succeeded",
            session_name="test-session",
            source="test",
        )
        assert result.ok
        assert result.sequence_number == 0
        assert log_file.exists()

    def test_sequence_numbers_monotonic_gap_free(self, tmp_path: Path) -> None:
        """Sequence numbers are 0, 1, 2, ... with no gaps."""
        rt = self._make_runtime(tmp_path)
        results = []
        for i in range(5):
            r = rt.append(
                event_type=f"event_{i}",
                session_name="test-session",
                source="test",
            )
            results.append(r)
        for i, r in enumerate(results):
            assert r.ok
            assert r.sequence_number == i

    def test_tail_returns_last_n(self, tmp_path: Path) -> None:
        """tail(n) returns the last n events."""
        rt = self._make_runtime(tmp_path)
        for i in range(10):
            rt.append(
                event_type=f"event_{i}",
                session_name="test-session",
                source="test",
            )
        last_3 = rt.tail(3)
        assert len(last_3) == 3
        assert last_3[0].sequence_number == 7
        assert last_3[1].sequence_number == 8
        assert last_3[2].sequence_number == 9
        assert last_3[2].event_type == "event_9"

    def test_tail_empty_log(self, tmp_path: Path) -> None:
        """tail(n) on empty log returns empty list."""
        rt = self._make_runtime(tmp_path)
        assert rt.tail(5) == []

    def test_mutation_hash_deterministic(self) -> None:
        """Same mutations produce the same hash."""
        mutations = [
            {"op": "SET", "key": "status", "value": "finalized"},
            {"op": "SET", "key": "ts", "value": "2026-04-16T00:00:00Z"},
        ]
        h1 = compute_mutation_hash(mutations)
        h2 = compute_mutation_hash(mutations)
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex

    def test_mutation_hash_changes_with_content(self) -> None:
        """Different mutations produce different hashes."""
        m1 = [{"op": "SET", "key": "a", "value": 1}]
        m2 = [{"op": "SET", "key": "a", "value": 2}]
        assert compute_mutation_hash(m1) != compute_mutation_hash(m2)

    def test_recover_counter_from_disk(self, tmp_path: Path) -> None:
        """New runtime instance recovers sequence counter from existing file."""
        log_file = tmp_path / "events.jsonl"
        rt1 = EventLogRuntime(log_path=log_file)
        for _ in range(3):
            rt1.append(
                event_type="test",
                session_name="s",
                source="t",
            )
        assert rt1.get_last_sequence() == 2

        # Create a new runtime pointing at the same file
        rt2 = EventLogRuntime(log_path=log_file)
        assert rt2.get_last_sequence() == 2

        # Next append should be seq 3
        result = rt2.append(
            event_type="after_recovery",
            session_name="s",
            source="t",
        )
        assert result.ok
        assert result.sequence_number == 3

    def test_read_all(self, tmp_path: Path) -> None:
        """read_all() returns all events in order."""
        rt = self._make_runtime(tmp_path)
        for i in range(3):
            rt.append(
                event_type=f"evt_{i}",
                session_name="session",
                source="src",
                payload={"i": i},
            )
        events = rt.read_all()
        assert len(events) == 3
        for i, evt in enumerate(events):
            assert evt.sequence_number == i
            assert evt.event_type == f"evt_{i}"
            assert evt.payload == {"i": i}

    def test_get_last_sequence_empty(self, tmp_path: Path) -> None:
        """get_last_sequence() returns -1 for empty log."""
        rt = self._make_runtime(tmp_path)
        assert rt.get_last_sequence() == -1

    def test_envelope_fields_populated(self, tmp_path: Path) -> None:
        """All EventEnvelope fields are populated on append."""
        rt = self._make_runtime(tmp_path)
        mutations = [{"op": "SET", "key": "k", "value": "v"}]
        rt.append(
            event_type="clear_confirmed",
            session_name="cc-vps",
            source="session_control",
            run_id="run_abc123",
            payload={"detail": "test"},
            state_mutations=mutations,
            metadata={"gen": 5},
        )
        events = rt.read_all()
        assert len(events) == 1
        evt = events[0]
        assert evt.event_type == "clear_confirmed"
        assert evt.session_name == "cc-vps"
        assert evt.source == "session_control"
        assert evt.run_id == "run_abc123"
        assert evt.payload == {"detail": "test"}
        assert evt.state_mutations == mutations
        assert evt.mutation_hash == compute_mutation_hash(mutations)
        assert evt.metadata == {"gen": 5}
        assert evt.event_id.startswith("evt_")
        assert evt.log_time != ""
        assert evt.event_time != ""
