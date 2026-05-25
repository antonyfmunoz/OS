"""Tests for override outcome tracking in HomeostasisEngine.

Covers: record_override(), record_override_outcome(), override_history(),
override_stats(), backwards compatibility, cap enforcement.
"""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/close-all-gaps-v2")

from datetime import datetime, timezone

import pytest

from substrate.organism.homeostasis import (
    HomeostasisEngine,
    Override,
    _OVERRIDE_HISTORY_MAX,
)


@pytest.fixture
def engine() -> HomeostasisEngine:
    return HomeostasisEngine()


class TestRecordOverride:
    """Tests for the expanded record_override method."""

    def test_returns_uuid_string(self, engine: HomeostasisEngine) -> None:
        """record_override returns a UUID string ID."""
        override_id = engine.record_override(
            original_recommendation="Use Haiku for cost",
            founder_decision="Use Opus — this is strategic",
            agent="model_router",
            action_type="model_selection",
        )
        assert isinstance(override_id, str)
        assert len(override_id) == 36  # UUID format

    def test_backwards_compatible_no_args(self, engine: HomeostasisEngine) -> None:
        """Calling record_override() with no args still works and increments counter."""
        override_id = engine.record_override()
        assert isinstance(override_id, str)
        assert engine._override_count == 1
        assert len(engine._overrides) == 1
        # Fields should be empty strings / empty dict
        override = engine._overrides[0]
        assert override.original_recommendation == ""
        assert override.founder_decision == ""
        assert override.agent == ""
        assert override.context == {}

    def test_stores_full_context(self, engine: HomeostasisEngine) -> None:
        """Override stores all provided fields."""
        ctx = {"signal_id": "sig-123", "risk_level": "high"}
        override_id = engine.record_override(
            original_recommendation="Block this action — risk too high",
            founder_decision="Proceed — I know this client",
            agent="governance_engine",
            action_type="risk_classification",
            context=ctx,
        )
        override = engine._overrides[0]
        assert override.id == override_id
        assert override.original_recommendation == "Block this action — risk too high"
        assert override.founder_decision == "Proceed — I know this client"
        assert override.agent == "governance_engine"
        assert override.action_type == "risk_classification"
        assert override.context == ctx
        assert override.outcome is None
        assert override.outcome_recorded_at is None
        assert isinstance(override.timestamp, datetime)

    def test_increments_counter(self, engine: HomeostasisEngine) -> None:
        """Each call increments the override counter."""
        engine.record_override(agent="a1")
        engine.record_override(agent="a2")
        engine.record_override(agent="a3")
        assert engine._override_count == 3
        assert len(engine._overrides) == 3


class TestRecordOverrideOutcome:
    """Tests for recording outcomes against existing overrides."""

    def test_records_outcome_for_existing_override(self, engine: HomeostasisEngine) -> None:
        """Outcome is stored on the correct override."""
        oid = engine.record_override(
            original_recommendation="Delay send",
            founder_decision="Send now",
            agent="scheduler",
            action_type="timing",
        )
        result = engine.record_override_outcome(oid, "positive — client responded immediately")
        assert result is True

        override = engine._overrides[0]
        assert override.outcome == "positive — client responded immediately"
        assert isinstance(override.outcome_recorded_at, datetime)

    def test_returns_false_for_missing_id(self, engine: HomeostasisEngine) -> None:
        """Returns False when the override ID doesn't exist."""
        result = engine.record_override_outcome("nonexistent-id", "positive")
        assert result is False

    def test_overwrites_previous_outcome(self, engine: HomeostasisEngine) -> None:
        """A second outcome call overwrites the first."""
        oid = engine.record_override(agent="test")
        engine.record_override_outcome(oid, "positive — looked good initially")
        engine.record_override_outcome(oid, "negative — fell apart after a week")

        override = engine._overrides[0]
        assert override.outcome == "negative — fell apart after a week"


class TestOverrideHistory:
    """Tests for the override_history query method."""

    def test_returns_newest_first(self, engine: HomeostasisEngine) -> None:
        """History is ordered newest-first."""
        engine.record_override(agent="first")
        engine.record_override(agent="second")
        engine.record_override(agent="third")

        history = engine.override_history()
        assert len(history) == 3
        assert history[0]["agent"] == "third"
        assert history[1]["agent"] == "second"
        assert history[2]["agent"] == "first"

    def test_respects_limit(self, engine: HomeostasisEngine) -> None:
        """Limit caps the returned records."""
        for i in range(10):
            engine.record_override(agent=f"agent-{i}")

        history = engine.override_history(limit=3)
        assert len(history) == 3
        # Should be the 3 newest
        assert history[0]["agent"] == "agent-9"
        assert history[1]["agent"] == "agent-8"
        assert history[2]["agent"] == "agent-7"

    def test_includes_outcomes(self, engine: HomeostasisEngine) -> None:
        """History entries include outcome data when present."""
        oid = engine.record_override(agent="test")
        engine.record_override_outcome(oid, "positive — great result")

        history = engine.override_history()
        assert history[0]["outcome"] == "positive — great result"
        assert history[0]["outcome_recorded_at"] is not None

    def test_empty_when_no_overrides(self, engine: HomeostasisEngine) -> None:
        """Returns empty list when no overrides recorded."""
        assert engine.override_history() == []


class TestOverrideStats:
    """Tests for aggregate override statistics."""

    def test_empty_stats(self, engine: HomeostasisEngine) -> None:
        """Stats with no overrides are all zero."""
        stats = engine.override_stats()
        assert stats["total_overrides"] == 0
        assert stats["tracked_overrides"] == 0
        assert stats["overrides_with_outcomes"] == 0
        assert stats["positive_outcomes"] == 0
        assert stats["negative_outcomes"] == 0
        assert stats["neutral_outcomes"] == 0
        assert stats["override_success_rate"] == 0.0

    def test_mixed_outcomes(self, engine: HomeostasisEngine) -> None:
        """Stats correctly classify positive, negative, and neutral outcomes."""
        oid1 = engine.record_override(agent="a")
        oid2 = engine.record_override(agent="b")
        oid3 = engine.record_override(agent="c")
        oid4 = engine.record_override(agent="d")  # no outcome

        engine.record_override_outcome(oid1, "positive — founder was right")
        engine.record_override_outcome(oid2, "negative — risk materialized")
        engine.record_override_outcome(oid3, "inconclusive, need more data")

        stats = engine.override_stats()
        assert stats["total_overrides"] == 4
        assert stats["tracked_overrides"] == 4
        assert stats["overrides_with_outcomes"] == 3
        assert stats["positive_outcomes"] == 1
        assert stats["negative_outcomes"] == 1
        assert stats["neutral_outcomes"] == 1
        assert stats["override_success_rate"] == pytest.approx(1 / 3, abs=0.01)

    def test_success_rate_all_positive(self, engine: HomeostasisEngine) -> None:
        """100% success rate when all outcomes are positive."""
        for _ in range(5):
            oid = engine.record_override(agent="test")
            engine.record_override_outcome(oid, "positive")

        stats = engine.override_stats()
        assert stats["override_success_rate"] == 1.0


class TestOverrideCapEnforcement:
    """Tests for the in-memory cap on override storage."""

    def test_cap_enforced(self, engine: HomeostasisEngine) -> None:
        """Overrides beyond _OVERRIDE_HISTORY_MAX are pruned."""
        for i in range(_OVERRIDE_HISTORY_MAX + 50):
            engine.record_override(agent=f"agent-{i}")

        assert len(engine._overrides) == _OVERRIDE_HISTORY_MAX
        # Counter reflects true total, not just stored
        assert engine._override_count == _OVERRIDE_HISTORY_MAX + 50
        # Newest should be the last one recorded
        assert engine._overrides[-1].agent == f"agent-{_OVERRIDE_HISTORY_MAX + 49}"


class TestOverrideToDict:
    """Tests for the Override.to_dict serialization."""

    def test_serializes_all_fields(self) -> None:
        """to_dict includes all fields with correct types."""
        ts = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
        outcome_ts = datetime(2026, 5, 25, 14, 0, 0, tzinfo=timezone.utc)
        override = Override(
            id="test-id",
            timestamp=ts,
            original_recommendation="rec",
            founder_decision="dec",
            agent="agent",
            action_type="type",
            context={"key": "val"},
            outcome="positive",
            outcome_recorded_at=outcome_ts,
        )
        d = override.to_dict()
        assert d["id"] == "test-id"
        assert d["timestamp"] == "2026-05-25T12:00:00+00:00"
        assert d["original_recommendation"] == "rec"
        assert d["founder_decision"] == "dec"
        assert d["agent"] == "agent"
        assert d["action_type"] == "type"
        assert d["context"] == {"key": "val"}
        assert d["outcome"] == "positive"
        assert d["outcome_recorded_at"] == "2026-05-25T14:00:00+00:00"

    def test_none_outcome_serializes_correctly(self) -> None:
        """outcome_recorded_at is None when no outcome set."""
        ts = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
        override = Override(
            id="test-id",
            timestamp=ts,
            original_recommendation="rec",
            founder_decision="dec",
            agent="agent",
            action_type="type",
        )
        d = override.to_dict()
        assert d["outcome"] is None
        assert d["outcome_recorded_at"] is None
