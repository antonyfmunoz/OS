"""Tests for C31 Phase 5: spine → learning loop integration.

Verifies that GovernedExecutionSpine records outcomes in OutcomeLearningLoop
directly, independent of propagation engine.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.action_envelope import ActionEnvelope, ActionType
from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.execution_modes import ExecutionModeManager
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.outcome_learning import OutcomeLearningLoop


@pytest.fixture
def learning_loop(tmp_path):
    return OutcomeLearningLoop(store_path=str(tmp_path / "learning.jsonl"))


@pytest.fixture
def spine(tmp_path, learning_loop):
    return GovernedExecutionSpine(
        event_spine=EventSpine(),
        execution_mode=ExecutionModeManager(),
        mutation_registry=MutationRegistry(),
        journal=ExecutionJournal(persist_path=str(tmp_path / "journal.jsonl")),
        learning_loop=learning_loop,
    )


class TestSpineLearningIntegration:
    def test_successful_execution_records_learning(self, spine, learning_loop):
        envelope = ActionEnvelope(
            intent="test action",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
        )
        result = spine.submit(envelope)
        assert result.result_success is True

        summary = learning_loop.summary()
        assert summary["total_outcomes"] == 1
        scores = summary["reliability_scores"]
        assert "state" in scores

    def test_failed_execution_records_learning(self, spine, learning_loop):
        envelope = ActionEnvelope(
            intent="failing action",
            action_type=ActionType.FILESYSTEM,
            source="test",
            execute_fn=lambda: ("error occurred", False),
        )
        result = spine.submit(envelope)
        assert result.result_success is False

        summary = learning_loop.summary()
        assert summary["total_outcomes"] == 1
        counts = summary["outcome_counts"]
        assert "filesystem" in counts
        assert counts["filesystem"].get("failure", 0) == 1

    def test_exception_execution_records_learning(self, spine, learning_loop):
        def raise_error():
            raise RuntimeError("boom")

        envelope = ActionEnvelope(
            intent="crashing action",
            action_type=ActionType.PROCESS,
            source="test",
            execute_fn=raise_error,
        )
        result = spine.submit(envelope)
        assert result.result_success is False

        summary = learning_loop.summary()
        assert summary["total_outcomes"] == 1

    def test_multiple_executions_track_reliability(self, spine, learning_loop):
        for i in range(5):
            envelope = ActionEnvelope(
                intent=f"action {i}",
                action_type=ActionType.STATE,
                source="test",
                execute_fn=lambda: ("ok", True),
            )
            spine.submit(envelope)

        envelope = ActionEnvelope(
            intent="failing action",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("fail", False),
        )
        spine.submit(envelope)

        summary = learning_loop.summary()
        assert summary["total_outcomes"] == 6
        assert summary["reliability_scores"]["state"] < 1.0
        assert summary["reliability_scores"]["state"] > 0.5

    def test_spine_without_learning_loop_works(self, tmp_path):
        spine = GovernedExecutionSpine(
            event_spine=EventSpine(),
            execution_mode=ExecutionModeManager(),
            mutation_registry=MutationRegistry(),
            journal=ExecutionJournal(persist_path=str(tmp_path / "j.jsonl")),
        )
        envelope = ActionEnvelope(
            intent="no learning",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("ok", True),
        )
        result = spine.submit(envelope)
        assert result.result_success is True

    def test_to_dict_includes_learning_stats(self, spine, learning_loop):
        envelope = ActionEnvelope(
            intent="tracked action",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("ok", True),
        )
        spine.submit(envelope)

        stats = spine.to_dict()
        assert stats["learning_loop_connected"] is True
        assert stats["learning_summary"] is not None
        assert stats["learning_summary"]["total_outcomes"] == 1

    def test_to_dict_without_learning(self, tmp_path):
        spine = GovernedExecutionSpine(
            event_spine=EventSpine(),
            execution_mode=ExecutionModeManager(),
            mutation_registry=MutationRegistry(),
            journal=ExecutionJournal(persist_path=str(tmp_path / "j.jsonl")),
        )
        stats = spine.to_dict()
        assert stats["learning_loop_connected"] is False
        assert stats["learning_summary"] is None
