"""C32 Cycle 1 — Pipeline A (Legacy) tests.

Validates the reliability-history endpoint implementation.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS")


class TestReliabilityHistory:
    def test_empty_history(self):
        from substrate.organism.outcome_learning import OutcomeLearningLoop

        tmp = tempfile.mkdtemp()
        loop = OutcomeLearningLoop(store_path=os.path.join(tmp, "learn.jsonl"))
        history = loop.reliability_history()
        assert history == {}

    def test_single_action_type_timeline(self):
        from substrate.organism.outcome_learning import (
            OutcomeLearningLoop,
            OutcomeRecord,
            OutcomeStatus,
        )

        tmp = tempfile.mkdtemp()
        loop = OutcomeLearningLoop(store_path=os.path.join(tmp, "learn.jsonl"))

        for i in range(5):
            loop.record_outcome(OutcomeRecord(
                action_type="deploy",
                status=OutcomeStatus.SUCCESS if i < 4 else OutcomeStatus.FAILURE,
                description=f"deploy #{i}",
            ))

        history = loop.reliability_history()
        assert "deploy" in history
        entry = history["deploy"]
        assert entry["sample_size"] == 5
        assert len(entry["timeline"]) == 5
        assert entry["current"] == entry["timeline"][-1]["cumulative_reliability"]

    def test_multiple_action_types(self):
        from substrate.organism.outcome_learning import (
            OutcomeLearningLoop,
            OutcomeRecord,
            OutcomeStatus,
        )

        tmp = tempfile.mkdtemp()
        loop = OutcomeLearningLoop(store_path=os.path.join(tmp, "learn.jsonl"))

        loop.record_outcome(OutcomeRecord(action_type="deploy", status=OutcomeStatus.SUCCESS))
        loop.record_outcome(OutcomeRecord(action_type="test", status=OutcomeStatus.FAILURE))
        loop.record_outcome(OutcomeRecord(action_type="deploy", status=OutcomeStatus.SUCCESS))

        history = loop.reliability_history()
        assert "deploy" in history
        assert "test" in history
        assert history["deploy"]["sample_size"] == 2
        assert history["test"]["sample_size"] == 1
        assert history["deploy"]["current"] > history["test"]["current"]

    def test_timeline_has_timestamps(self):
        from substrate.organism.outcome_learning import (
            OutcomeLearningLoop,
            OutcomeRecord,
            OutcomeStatus,
        )

        tmp = tempfile.mkdtemp()
        loop = OutcomeLearningLoop(store_path=os.path.join(tmp, "learn.jsonl"))
        loop.record_outcome(OutcomeRecord(action_type="build", status=OutcomeStatus.SUCCESS))

        history = loop.reliability_history()
        point = history["build"]["timeline"][0]
        assert "timestamp" in point
        assert "status" in point
        assert "cumulative_reliability" in point
        assert point["status"] == "success"
        assert point["cumulative_reliability"] == 1.0

    def test_cumulative_reliability_tracks_correctly(self):
        from substrate.organism.outcome_learning import (
            OutcomeLearningLoop,
            OutcomeRecord,
            OutcomeStatus,
        )

        tmp = tempfile.mkdtemp()
        loop = OutcomeLearningLoop(store_path=os.path.join(tmp, "learn.jsonl"))

        loop.record_outcome(OutcomeRecord(action_type="run", status=OutcomeStatus.SUCCESS))
        loop.record_outcome(OutcomeRecord(action_type="run", status=OutcomeStatus.FAILURE))

        history = loop.reliability_history()
        timeline = history["run"]["timeline"]
        assert timeline[0]["cumulative_reliability"] == 1.0
        assert timeline[1]["cumulative_reliability"] == 0.5

    def test_partial_counts_as_success(self):
        from substrate.organism.outcome_learning import (
            OutcomeLearningLoop,
            OutcomeRecord,
            OutcomeStatus,
        )

        tmp = tempfile.mkdtemp()
        loop = OutcomeLearningLoop(store_path=os.path.join(tmp, "learn.jsonl"))

        loop.record_outcome(OutcomeRecord(action_type="check", status=OutcomeStatus.PARTIAL))

        history = loop.reliability_history()
        assert history["check"]["timeline"][0]["cumulative_reliability"] == 1.0
