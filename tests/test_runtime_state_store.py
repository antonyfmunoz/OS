"""Tests for eos_ai.substrate.runtime_state_store."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.substrate.runtime_state_store import RuntimeStateStore


class TestRuntimeStateStore:
    """Test suite for RuntimeStateStore."""

    def test_set_and_get(self) -> None:
        """SET op and get() work."""
        store = RuntimeStateStore()
        store.set("name", "eos")
        assert store.get("name") == "eos"

    def test_get_default(self) -> None:
        """get() returns default for missing keys."""
        store = RuntimeStateStore()
        assert store.get("missing") is None
        assert store.get("missing", "fallback") == "fallback"

    def test_set_mutation(self) -> None:
        """SET via apply_mutations."""
        store = RuntimeStateStore()
        store.apply_mutations(
            [
                {"op": "SET", "key": "status", "value": "finalized"},
            ]
        )
        assert store.get("status") == "finalized"

    def test_increment_mutation(self) -> None:
        """INCREMENT creates or adds to a numeric key."""
        store = RuntimeStateStore()
        store.apply_mutations(
            [
                {"op": "INCREMENT", "key": "count"},  # default +1
            ]
        )
        assert store.get("count") == 1

        store.apply_mutations(
            [
                {"op": "INCREMENT", "key": "count", "value": 5},
            ]
        )
        assert store.get("count") == 6

    def test_append_unique_mutation(self) -> None:
        """APPEND_UNIQUE adds to a list, skips duplicates."""
        store = RuntimeStateStore()
        store.apply_mutations(
            [
                {"op": "APPEND_UNIQUE", "key": "tags", "value": "alpha"},
            ]
        )
        assert store.get("tags") == ["alpha"]

        store.apply_mutations(
            [
                {"op": "APPEND_UNIQUE", "key": "tags", "value": "beta"},
            ]
        )
        assert store.get("tags") == ["alpha", "beta"]

        # Duplicate — should not add again
        store.apply_mutations(
            [
                {"op": "APPEND_UNIQUE", "key": "tags", "value": "alpha"},
            ]
        )
        assert store.get("tags") == ["alpha", "beta"]

    def test_remove_mutation(self) -> None:
        """REMOVE deletes a key."""
        store = RuntimeStateStore()
        store.set("temp", "data")
        assert store.get("temp") == "data"

        store.apply_mutations(
            [
                {"op": "REMOVE", "key": "temp"},
            ]
        )
        assert store.get("temp") is None

    def test_remove_missing_key_no_error(self) -> None:
        """REMOVE on missing key does not raise."""
        store = RuntimeStateStore()
        store.apply_mutations(
            [
                {"op": "REMOVE", "key": "nonexistent"},
            ]
        )

    def test_unknown_op_raises(self) -> None:
        """Unknown mutation op raises ValueError."""
        store = RuntimeStateStore()
        with pytest.raises(ValueError, match="Unknown mutation op"):
            store.apply_mutations(
                [
                    {"op": "MERGE", "key": "x", "value": {}},
                ]
            )

    def test_snapshot_load_roundtrip(self) -> None:
        """snapshot() and load_snapshot() roundtrip preserves state."""
        store = RuntimeStateStore()
        store.set("a", 1)
        store.set("b", [2, 3])
        store.set("c", {"nested": True})

        snap = store.snapshot()
        assert snap == {"a": 1, "b": [2, 3], "c": {"nested": True}}

        # Load into fresh store
        store2 = RuntimeStateStore()
        store2.load_snapshot(snap)
        assert store2.get("a") == 1
        assert store2.get("b") == [2, 3]
        assert store2.get("c") == {"nested": True}

    def test_snapshot_is_deep_copy(self) -> None:
        """Mutations to snapshot dict do not affect store."""
        store = RuntimeStateStore()
        store.set("items", [1, 2, 3])

        snap = store.snapshot()
        snap["items"].append(4)  # mutate the copy

        assert store.get("items") == [1, 2, 3]  # original unchanged

    def test_reset_clears_all(self) -> None:
        """reset() removes all state."""
        store = RuntimeStateStore()
        store.set("x", 1)
        store.set("y", 2)
        store.reset()
        assert store.get("x") is None
        assert store.get("y") is None
        assert store.keys() == []

    def test_multiple_mutations_in_order(self) -> None:
        """apply_mutations applies ops in order."""
        store = RuntimeStateStore()
        store.apply_mutations(
            [
                {"op": "SET", "key": "counter", "value": 0},
                {"op": "INCREMENT", "key": "counter", "value": 10},
                {"op": "INCREMENT", "key": "counter", "value": 5},
            ]
        )
        assert store.get("counter") == 15
