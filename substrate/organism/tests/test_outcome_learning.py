"""Tests for outcome learning loop."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.outcome_learning import (
    LearningSignal,
    OutcomeEvaluation,
    OutcomeLearningLoop,
    OutcomeRecord,
    OutcomeStatus,
    RecommendationAdjustment,
    ReliabilityUpdate,
    SignalType,
)


@pytest.fixture
def temp_store():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestOutcomeRecord:
    def test_creation(self):
        rec = OutcomeRecord(
            action_type="run_probes",
            description="Execute workload probes",
            status=OutcomeStatus.SUCCESS,
        )
        assert rec.action_type == "run_probes"
        assert rec.status == OutcomeStatus.SUCCESS
        assert rec.id

    def test_to_dict(self):
        rec = OutcomeRecord(
            action_type="deploy",
            status=OutcomeStatus.FAILURE,
            error="Connection timeout",
        )
        d = rec.to_dict()
        assert d["status"] == "failure"
        assert d["error"] == "Connection timeout"


class TestLearningSignal:
    def test_creation(self):
        sig = LearningSignal(
            signal_type=SignalType.RELIABILITY_UPDATE,
            action_type="run_probes",
            description="Reliability increased",
            old_value=0.5,
            new_value=0.8,
        )
        assert sig.signal_type == SignalType.RELIABILITY_UPDATE
        assert sig.new_value == 0.8

    def test_to_dict(self):
        sig = LearningSignal(
            signal_type=SignalType.REPEATED_FAILURE,
            action_type="deploy",
        )
        d = sig.to_dict()
        assert d["signal_type"] == "repeated_failure"


class TestOutcomeEvaluation:
    def test_creation(self):
        ev = OutcomeEvaluation(
            outcome_id="abc",
            success=True,
            quality_score=0.9,
        )
        assert ev.success is True
        assert ev.quality_score == 0.9

    def test_to_dict(self):
        ev = OutcomeEvaluation(outcome_id="x", success=False, quality_score=0.0)
        d = ev.to_dict()
        assert d["success"] is False


class TestRecommendationAdjustment:
    def test_creation(self):
        adj = RecommendationAdjustment(
            action_type="deploy",
            current_reliability=0.2,
            adjustment=-0.1,
            reason="Too many failures",
        )
        assert adj.current_reliability == 0.2

    def test_to_dict_caps_value(self):
        adj = RecommendationAdjustment(
            action_type="test",
            current_reliability=0.95,
            adjustment=0.1,
        )
        d = adj.to_dict()
        assert d["new_reliability"] == 1.0


class TestOutcomeLearningLoop:
    def test_record_success(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        outcome = OutcomeRecord(
            action_type="probe",
            status=OutcomeStatus.SUCCESS,
        )
        eval_result = loop.record_outcome(outcome)
        assert eval_result.success is True
        assert eval_result.quality_score == 1.0

    def test_record_failure(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        outcome = OutcomeRecord(
            action_type="deploy",
            status=OutcomeStatus.FAILURE,
            error="Timeout",
        )
        eval_result = loop.record_outcome(outcome)
        assert eval_result.success is False
        assert eval_result.quality_score == 0.0

    def test_record_partial(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        outcome = OutcomeRecord(
            action_type="migrate",
            status=OutcomeStatus.PARTIAL,
        )
        eval_result = loop.record_outcome(outcome)
        assert eval_result.success is True
        assert eval_result.quality_score == 0.6

    def test_reliability_update(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        for _ in range(3):
            loop.record_outcome(OutcomeRecord(action_type="probe", status=OutcomeStatus.SUCCESS))
        loop.record_outcome(OutcomeRecord(action_type="probe", status=OutcomeStatus.FAILURE))
        reliability = loop.get_reliability("probe")
        assert 0.7 < reliability < 0.8

    def test_repeated_failure_detection(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        for _ in range(4):
            loop.record_outcome(OutcomeRecord(action_type="deploy", status=OutcomeStatus.FAILURE))
        signals = loop.recent_signals()
        repeated = [s for s in signals if s.signal_type == SignalType.REPEATED_FAILURE]
        assert len(repeated) > 0

    def test_recommendation_adjustment_low(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        for _ in range(5):
            loop.record_outcome(OutcomeRecord(action_type="bad_action", status=OutcomeStatus.FAILURE))
        adjustments = loop.get_adjustments()
        bad = [a for a in adjustments if a.action_type == "bad_action"]
        assert len(bad) == 1
        assert bad[0].adjustment < 0

    def test_recommendation_adjustment_high(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        for _ in range(10):
            loop.record_outcome(OutcomeRecord(action_type="good_action", status=OutcomeStatus.SUCCESS))
        adjustments = loop.get_adjustments()
        good = [a for a in adjustments if a.action_type == "good_action"]
        assert len(good) == 1
        assert good[0].adjustment > 0

    def test_recent_outcomes(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        for i in range(5):
            loop.record_outcome(OutcomeRecord(action_type="test", description=f"#{i}", status=OutcomeStatus.SUCCESS))
        recent = loop.recent_outcomes(3)
        assert len(recent) == 3

    def test_summary(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        loop.record_outcome(OutcomeRecord(action_type="x", status=OutcomeStatus.SUCCESS))
        s = loop.summary()
        assert s["total_outcomes"] == 1
        assert "reliability_scores" in s

    def test_to_dict_serialization(self, temp_store):
        loop = OutcomeLearningLoop(store_path=temp_store)
        loop.record_outcome(OutcomeRecord(action_type="test", status=OutcomeStatus.SUCCESS))
        d = loop.to_dict()
        serialized = json.dumps(d, default=str)
        parsed = json.loads(serialized)
        assert "summary" in parsed
        assert "recent_outcomes" in parsed
        assert "adjustments" in parsed

    def test_persistence_reload(self, temp_store):
        loop1 = OutcomeLearningLoop(store_path=temp_store)
        loop1.record_outcome(OutcomeRecord(action_type="probe", status=OutcomeStatus.SUCCESS))
        loop1.record_outcome(OutcomeRecord(action_type="probe", status=OutcomeStatus.SUCCESS))

        loop2 = OutcomeLearningLoop(store_path=temp_store)
        assert loop2.get_reliability("probe") > 0.5
        assert len(loop2.recent_outcomes()) >= 2
