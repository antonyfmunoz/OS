"""Phase 21 — Prediction Memory + Accuracy Feedback System v1.

Tests cover:
  - PredictionRecord (creation, immutability of core fields, serialization)
  - PredictionStore (append-only, listing, status transitions, expiration, eviction)
  - PredictionEvaluator (matching, non-matching, determinism, one-to-one matching)
  - PredictionMetrics (accuracy, confidence calibration, source breakdown)
  - Advisor integration (storage, evaluation, expiration per tick, accuracy exposure)
  - Loop integration (completed_feedback pass-through)
  - Boundary invariants (no cells/environments/subprocess imports)
  - Determinism (same input → same output)
  - Regression (prior phase behavior unchanged)

Hard invariants:
  40. Predictions stored immutably once emitted
  41. Outcomes linked to originating predictions
  42. Accuracy computation does not mutate historical records
  43. Prediction evaluation is deterministic
  44. No retroactive rewriting of prediction data
"""

from __future__ import annotations

import ast
import os
from datetime import datetime, timezone
from typing import Any

import pytest

from umh.learning.feedback import ExecutionFeedback, FeedbackStore
from umh.prediction.evaluator import MatchResult, PredictionEvaluator
from umh.prediction.intent import UserIntent, make_intent_id
from umh.prediction.metrics import (
    ConfidenceBucket,
    PredictionAccuracy,
    PredictionMetrics,
    SourceAccuracy,
)
from umh.prediction.predictor import PredictionContext, Predictor
from umh.prediction.store import (
    PredictionRecord,
    PredictionStatus,
    PredictionStore,
    record_from_intent,
)


# ── helpers ──────────────────────────────────────────────────────────


def _make_intent(
    goal: str = "repeat_outreach",
    confidence: float = 0.8,
    actions: tuple[str, ...] = ("submit_outreach",),
    entities: tuple[str, ...] = ("outreach",),
    source: str = "repeated_workflow",
    intent_id: str = "",
) -> UserIntent:
    return UserIntent(
        intent_id=intent_id or make_intent_id(),
        inferred_goal=goal,
        confidence=confidence,
        predicted_actions=actions,
        related_entities=entities,
        source=source,
        timestamp="2026-04-29T09:00:00Z",
    )


def _make_feedback(
    task_type: str = "outreach",
    node_id: str = "node-1",
    success: bool = True,
    duration_ms: int = 500,
    job_id: str = "",
    timestamp: str = "2026-04-29T09:00:00+00:00",
) -> ExecutionFeedback:
    return ExecutionFeedback(
        job_id=job_id or f"job_{task_type}",
        node_id=node_id,
        task_type=task_type,
        success=success,
        duration_ms=duration_ms,
        timestamp=timestamp,
    )


def _make_record(
    goal: str = "repeat_outreach",
    confidence: float = 0.8,
    actions: tuple[str, ...] = ("submit_outreach",),
    entities: tuple[str, ...] = ("outreach",),
    source: str = "repeated_workflow",
    tick: int = 0,
) -> PredictionRecord:
    intent = _make_intent(
        goal=goal,
        confidence=confidence,
        actions=actions,
        entities=entities,
        source=source,
    )
    return record_from_intent(intent, tick=tick)


def _ref_time(hour: int = 9) -> datetime:
    return datetime(2026, 4, 29, hour, 0, 0, tzinfo=timezone.utc)


# ── PREDICTION RECORD ────────────────────────────────────────────────


class TestPredictionRecord:
    def test_creation(self) -> None:
        rec = _make_record()
        assert rec.prediction_id.startswith("pred_")
        assert rec.inferred_goal == "repeat_outreach"
        assert rec.confidence == 0.8
        assert rec.status == PredictionStatus.PENDING

    def test_from_intent(self) -> None:
        intent = _make_intent(intent_id="test_intent")
        rec = record_from_intent(intent, tick=5)
        assert rec.intent_id == "test_intent"
        assert rec.inferred_goal == intent.inferred_goal
        assert rec.confidence == intent.confidence
        assert rec.predicted_actions == intent.predicted_actions
        assert rec.related_entities == intent.related_entities
        assert rec.tick_emitted == 5

    def test_serialization(self) -> None:
        rec = _make_record()
        d = rec.to_dict()
        assert d["status"] == "pending"
        assert d["inferred_goal"] == "repeat_outreach"
        assert isinstance(d["predicted_actions"], list)
        assert isinstance(d["related_entities"], list)

    def test_context_hash_deterministic(self) -> None:
        intent = _make_intent(intent_id="a")
        r1 = record_from_intent(intent)
        r2 = record_from_intent(intent)
        assert r1.context_hash == r2.context_hash

    def test_context_hash_varies_by_goal(self) -> None:
        i1 = _make_intent(goal="goal_a")
        i2 = _make_intent(goal="goal_b")
        r1 = record_from_intent(i1)
        r2 = record_from_intent(i2)
        assert r1.context_hash != r2.context_hash

    def test_unique_prediction_ids(self) -> None:
        r1 = _make_record()
        r2 = _make_record()
        assert r1.prediction_id != r2.prediction_id


# ── PREDICTION STORE ─────────────────────────────────────────────────


class TestPredictionStore:
    def test_append_and_total(self) -> None:
        store = PredictionStore()
        store.append(_make_record())
        assert store.total == 1

    def test_list_pending(self) -> None:
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        pending = store.list_pending()
        assert len(pending) == 1
        assert pending[0].prediction_id == rec.prediction_id

    def test_get_by_id(self) -> None:
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.prediction_id == rec.prediction_id

    def test_get_missing_returns_none(self) -> None:
        store = PredictionStore()
        assert store.get("nonexistent") is None

    def test_mark_matched(self) -> None:
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        result = store.mark_matched(rec.prediction_id, matched_job_id="job_x")
        assert result is True
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.status == PredictionStatus.MATCHED
        assert found.matched_job_id == "job_x"
        assert found.resolved_at != ""

    def test_mark_matched_only_pending(self) -> None:
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        store.mark_missed(rec.prediction_id)
        result = store.mark_matched(rec.prediction_id)
        assert result is False

    def test_mark_missed(self) -> None:
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        result = store.mark_missed(rec.prediction_id)
        assert result is True
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.status == PredictionStatus.MISSED

    def test_mark_missed_only_pending(self) -> None:
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        store.mark_matched(rec.prediction_id)
        result = store.mark_missed(rec.prediction_id)
        assert result is False

    def test_expire_old_predictions(self) -> None:
        store = PredictionStore(expiry_ticks=10)
        rec = _make_record(tick=1)
        store.append(rec)
        expired = store.expire_old_predictions(current_tick=5)
        assert expired == 0
        expired = store.expire_old_predictions(current_tick=11)
        assert expired == 1
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.status == PredictionStatus.EXPIRED

    def test_expire_does_not_touch_resolved(self) -> None:
        store = PredictionStore(expiry_ticks=5)
        rec = _make_record(tick=1)
        store.append(rec)
        store.mark_matched(rec.prediction_id)
        expired = store.expire_old_predictions(current_tick=100)
        assert expired == 0

    def test_list_all(self) -> None:
        store = PredictionStore()
        for i in range(3):
            store.append(_make_record(goal=f"goal_{i}"))
        assert len(store.list_all()) == 3

    def test_list_resolved(self) -> None:
        store = PredictionStore()
        r1 = _make_record()
        r2 = _make_record()
        r3 = _make_record()
        store.append(r1)
        store.append(r2)
        store.append(r3)
        store.mark_matched(r1.prediction_id)
        store.mark_missed(r2.prediction_id)
        resolved = store.list_resolved()
        assert len(resolved) == 2

    def test_pending_count(self) -> None:
        store = PredictionStore()
        store.append(_make_record())
        store.append(_make_record())
        assert store.pending_count == 2
        store.mark_matched(store.list_pending()[0].prediction_id)
        assert store.pending_count == 1

    def test_eviction_on_overflow(self) -> None:
        store = PredictionStore(max_records=3)
        ids = []
        for i in range(5):
            rec = _make_record(goal=f"g_{i}")
            store.append(rec)
            ids.append(rec.prediction_id)
        assert store.total == 3
        assert store.get(ids[0]) is None
        assert store.get(ids[1]) is None
        assert store.get(ids[4]) is not None

    def test_clear(self) -> None:
        store = PredictionStore()
        store.append(_make_record())
        store.clear()
        assert store.total == 0
        assert store.list_pending() == []

    def test_status_forward_only(self) -> None:
        """Once resolved, a prediction cannot go back to PENDING."""
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        store.mark_matched(rec.prediction_id)
        result_missed = store.mark_missed(rec.prediction_id)
        assert result_missed is False
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.status == PredictionStatus.MATCHED


# ── PREDICTION EVALUATOR ─────────────────────────────────────────────


class TestPredictionEvaluator:
    def test_entity_match(self) -> None:
        evaluator = PredictionEvaluator()
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach", job_id="j1")
        results = evaluator.match_predictions([pred], [fb])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].matched_job_id == "j1"
        assert "entity_match" in results[0].match_reason

    def test_action_match(self) -> None:
        evaluator = PredictionEvaluator()
        pred = _make_record(
            entities=("other",),
            actions=("submit_outreach",),
        )
        fb = _make_feedback(task_type="outreach", job_id="j2")
        results = evaluator.match_predictions([pred], [fb])
        assert results[0].matched is True
        assert "action_match" in results[0].match_reason

    def test_goal_match(self) -> None:
        evaluator = PredictionEvaluator()
        pred = _make_record(
            goal="repeat_outreach",
            entities=("other",),
            actions=("do_something",),
        )
        fb = _make_feedback(task_type="outreach", job_id="j3")
        results = evaluator.match_predictions([pred], [fb])
        assert results[0].matched is True
        assert "goal_match" in results[0].match_reason

    def test_no_match(self) -> None:
        evaluator = PredictionEvaluator()
        pred = _make_record(
            goal="repeat_content",
            entities=("content",),
            actions=("submit_content",),
        )
        fb = _make_feedback(task_type="outreach", job_id="j4")
        results = evaluator.match_predictions([pred], [fb])
        assert results[0].matched is False
        assert results[0].matched_job_id == ""

    def test_one_job_matches_at_most_one_prediction(self) -> None:
        evaluator = PredictionEvaluator()
        p1 = _make_record(entities=("outreach",))
        p2 = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach", job_id="single_job")
        results = evaluator.match_predictions([p1, p2], [fb])
        matched = [r for r in results if r.matched]
        assert len(matched) == 1

    def test_multiple_jobs_match_multiple_predictions(self) -> None:
        evaluator = PredictionEvaluator()
        p1 = _make_record(entities=("outreach",), actions=("submit_outreach",))
        p2 = _make_record(
            goal="repeat_content",
            entities=("content",),
            actions=("submit_content",),
        )
        fb1 = _make_feedback(task_type="outreach", job_id="j_o")
        fb2 = _make_feedback(task_type="content", job_id="j_c")
        results = evaluator.match_predictions([p1, p2], [fb1, fb2])
        matched = [r for r in results if r.matched]
        assert len(matched) == 2

    def test_case_insensitive_matching(self) -> None:
        evaluator = PredictionEvaluator()
        pred = _make_record(entities=("Outreach",))
        fb = _make_feedback(task_type="outreach", job_id="j5")
        results = evaluator.match_predictions([pred], [fb])
        assert results[0].matched is True

    def test_empty_inputs(self) -> None:
        evaluator = PredictionEvaluator()
        assert evaluator.match_predictions([], []) == []
        assert evaluator.match_predictions([], [_make_feedback()]) == []

    def test_determinism(self) -> None:
        evaluator = PredictionEvaluator()
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach", job_id="j_det")
        r1 = evaluator.match_predictions([pred], [fb])
        r2 = evaluator.match_predictions([pred], [fb])
        assert r1[0].matched == r2[0].matched
        assert r1[0].match_reason == r2[0].match_reason

    def test_match_result_serialization(self) -> None:
        mr = MatchResult(
            prediction_id="pred_1",
            matched=True,
            matched_job_id="job_1",
            match_reason="entity_match:outreach",
        )
        d = mr.to_dict()
        assert d["prediction_id"] == "pred_1"
        assert d["matched"] is True


# ── PREDICTION METRICS ───────────────────────────────────────────────


class TestPredictionMetrics:
    def test_accuracy_all_matched(self) -> None:
        metrics = PredictionMetrics()
        records = [_make_record() for _ in range(5)]
        for r in records:
            r.status = PredictionStatus.MATCHED
        acc = metrics.compute_accuracy(records)
        assert acc.total_predictions == 5
        assert acc.matched == 5
        assert acc.accuracy_rate == 1.0

    def test_accuracy_mixed(self) -> None:
        metrics = PredictionMetrics()
        records = [_make_record() for _ in range(4)]
        records[0].status = PredictionStatus.MATCHED
        records[1].status = PredictionStatus.MATCHED
        records[2].status = PredictionStatus.MISSED
        records[3].status = PredictionStatus.EXPIRED
        acc = metrics.compute_accuracy(records)
        assert acc.matched == 2
        assert acc.missed == 1
        assert acc.expired == 1
        assert acc.accuracy_rate == 0.5

    def test_accuracy_no_resolved(self) -> None:
        metrics = PredictionMetrics()
        records = [_make_record()]
        acc = metrics.compute_accuracy(records)
        assert acc.pending == 1
        assert acc.accuracy_rate == 0.0

    def test_accuracy_empty(self) -> None:
        metrics = PredictionMetrics()
        acc = metrics.compute_accuracy([])
        assert acc.total_predictions == 0
        assert acc.accuracy_rate == 0.0

    def test_accuracy_from_store(self) -> None:
        metrics = PredictionMetrics()
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        store.mark_matched(rec.prediction_id)
        acc = metrics.compute_accuracy_from_store(store)
        assert acc.matched == 1
        assert acc.accuracy_rate == 1.0

    def test_accuracy_serialization(self) -> None:
        acc = PredictionAccuracy(
            total_predictions=10,
            pending=2,
            matched=5,
            missed=2,
            expired=1,
            accuracy_rate=0.625,
            miss_rate=0.375,
        )
        d = acc.to_dict()
        assert d["total_predictions"] == 10
        assert d["accuracy_rate"] == 0.625

    def test_confidence_calibration(self) -> None:
        metrics = PredictionMetrics()
        records = []
        for i in range(10):
            rec = _make_record(confidence=0.1 * i + 0.05)
            rec.status = PredictionStatus.MATCHED if i >= 5 else PredictionStatus.MISSED
            records.append(rec)
        buckets = metrics.compute_confidence_calibration(records, bucket_count=5)
        assert len(buckets) >= 1
        for b in buckets:
            assert 0.0 <= b.actual_accuracy <= 1.0
            assert b.count >= 1

    def test_confidence_calibration_empty(self) -> None:
        metrics = PredictionMetrics()
        buckets = metrics.compute_confidence_calibration([])
        assert buckets == []

    def test_confidence_bucket_serialization(self) -> None:
        bucket = ConfidenceBucket(
            bucket_low=0.6,
            bucket_high=0.8,
            count=10,
            matched=7,
            actual_accuracy=0.7,
            avg_confidence=0.72,
        )
        d = bucket.to_dict()
        assert d["bucket"] == "0.6-0.8"
        assert d["count"] == 10

    def test_source_accuracy(self) -> None:
        metrics = PredictionMetrics()
        records = [
            _make_record(source="repeated_workflow"),
            _make_record(source="repeated_workflow"),
            _make_record(source="continuation"),
        ]
        records[0].status = PredictionStatus.MATCHED
        records[1].status = PredictionStatus.MISSED
        records[2].status = PredictionStatus.MATCHED
        sa = metrics.compute_source_accuracy(records)
        assert len(sa) == 2
        by_source = {s.source: s for s in sa}
        assert by_source["continuation"].accuracy_rate == 1.0
        assert by_source["repeated_workflow"].accuracy_rate == 0.5

    def test_source_accuracy_empty(self) -> None:
        metrics = PredictionMetrics()
        assert metrics.compute_source_accuracy([]) == []

    def test_source_accuracy_serialization(self) -> None:
        sa = SourceAccuracy(
            source="repeated_workflow",
            total=10,
            matched=7,
            accuracy_rate=0.7,
        )
        d = sa.to_dict()
        assert d["source"] == "repeated_workflow"
        assert d["accuracy_rate"] == 0.7

    def test_accuracy_does_not_mutate_records(self) -> None:
        metrics = PredictionMetrics()
        rec = _make_record()
        rec.status = PredictionStatus.MATCHED
        records = [rec]
        original_status = rec.status
        metrics.compute_accuracy(records)
        metrics.compute_confidence_calibration(records)
        metrics.compute_source_accuracy(records)
        assert rec.status == original_status


# ── ADVISOR INTEGRATION ──────────────────────────────────────────────


class TestAdvisorPredictionFeedback:
    def _build_advisor(self) -> Any:
        from umh.runtime.advisor import AdvisorRuntime

        return AdvisorRuntime(
            predictor=Predictor(),
            predictive_planner=__import__(
                "umh.prediction.planner", fromlist=["PredictivePlanner"]
            ).PredictivePlanner(),
            prediction_store=PredictionStore(),
            prediction_evaluator=PredictionEvaluator(),
            prediction_metrics=PredictionMetrics(),
        )

    def _make_context_with_feedback(
        self, n: int = 5
    ) -> PredictionContext:
        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(n)
        )
        return PredictionContext(recent_feedback=feedbacks, current_hour=9)

    def test_predictions_stored_on_tick(self) -> None:
        advisor = self._build_advisor()
        advisor.start()
        ctx = self._make_context_with_feedback()
        result = advisor.tick(prediction_context=ctx)
        assert result["predictions_stored"] >= 1
        assert advisor.prediction_store is not None
        assert advisor.prediction_store.total >= 1
        advisor.stop()

    def test_predictions_evaluated_against_feedback(self) -> None:
        advisor = self._build_advisor()
        advisor.start()

        ctx = self._make_context_with_feedback()
        advisor.tick(prediction_context=ctx)

        completed = [_make_feedback(task_type="outreach", job_id="completed_j1")]
        result = advisor.tick(completed_feedback=completed)
        assert result["predictions_matched"] >= 1
        advisor.stop()

    def test_predictions_expire_over_ticks(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        store = PredictionStore(expiry_ticks=3)
        advisor = AdvisorRuntime(
            predictor=Predictor(),
            predictive_planner=__import__(
                "umh.prediction.planner", fromlist=["PredictivePlanner"]
            ).PredictivePlanner(),
            prediction_store=store,
            prediction_evaluator=PredictionEvaluator(),
            prediction_metrics=PredictionMetrics(),
        )
        advisor.start()

        ctx = self._make_context_with_feedback()
        advisor.tick(prediction_context=ctx)
        first_tick_count = store.total
        assert first_tick_count >= 1

        advisor._prediction_context = None

        for _ in range(4):
            advisor.tick()

        all_records = store.list_all()
        first_tick_records = all_records[:first_tick_count]
        expired = [r for r in first_tick_records if r.status == PredictionStatus.EXPIRED]
        assert len(expired) >= 1
        pending_first = [r for r in first_tick_records if r.status == PredictionStatus.PENDING]
        assert len(pending_first) == 0

        advisor.stop()

    def test_accuracy_exposed(self) -> None:
        advisor = self._build_advisor()
        advisor.start()
        ctx = self._make_context_with_feedback()
        advisor.tick(prediction_context=ctx)
        completed = [_make_feedback(task_type="outreach", job_id="cj1")]
        advisor.tick(completed_feedback=completed)
        acc = advisor.get_prediction_accuracy()
        assert acc is not None
        assert acc.total_predictions >= 1
        advisor.stop()

    def test_state_includes_prediction_store_info(self) -> None:
        advisor = self._build_advisor()
        advisor.start()
        state = advisor.get_state()
        assert "prediction_store_total" in state
        assert "prediction_store_pending" in state
        advisor.stop()

    def test_advisor_without_store_unchanged(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert result["predictions_stored"] == 0
        assert result["predictions_matched"] == 0
        assert result["predictions_expired"] == 0
        assert advisor.get_prediction_accuracy() is None
        advisor.stop()

    def test_clear_predictions_clears_store(self) -> None:
        advisor = self._build_advisor()
        advisor.start()
        ctx = self._make_context_with_feedback()
        advisor.tick(prediction_context=ctx)
        assert advisor.prediction_store is not None
        assert advisor.prediction_store.total >= 1
        advisor.clear_predictions()
        assert advisor.prediction_store.total == 0
        advisor.stop()


# ── LOOP INTEGRATION ─────────────────────────────────────────────────


class TestLoopPredictionFeedback:
    def test_loop_passes_completed_feedback(self) -> None:
        from umh.prediction.planner import PredictivePlanner
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.loop import RuntimeLoop

        advisor = AdvisorRuntime(
            predictor=Predictor(),
            predictive_planner=PredictivePlanner(),
            prediction_store=PredictionStore(),
            prediction_evaluator=PredictionEvaluator(),
            prediction_metrics=PredictionMetrics(),
        )
        loop = RuntimeLoop(advisor=advisor)
        loop.start()

        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        loop.tick(prediction_context=ctx)

        completed = [_make_feedback(task_type="outreach", job_id="done_j")]
        result = loop.tick(completed_feedback=completed)
        assert result["predictions_matched"] >= 1

        loop.stop()

    def test_loop_without_feedback_unchanged(self) -> None:
        from umh.runtime.loop import RuntimeLoop

        loop = RuntimeLoop()
        loop.start()
        result = loop.tick()
        assert result["predictions_stored"] == 0
        assert result["predictions_matched"] == 0
        assert result["predictions_expired"] == 0
        loop.stop()


# ── DETERMINISM ──────────────────────────────────────────────────────


class TestPredictionFeedbackDeterminism:
    def test_same_predictions_same_matches(self) -> None:
        evaluator = PredictionEvaluator()
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach", job_id="j_det")
        r1 = evaluator.match_predictions([pred], [fb])
        r2 = evaluator.match_predictions([pred], [fb])
        assert r1[0].matched == r2[0].matched
        assert r1[0].match_reason == r2[0].match_reason

    def test_same_records_same_accuracy(self) -> None:
        metrics = PredictionMetrics()
        records = [_make_record() for _ in range(5)]
        for i, r in enumerate(records):
            r.status = PredictionStatus.MATCHED if i < 3 else PredictionStatus.MISSED
        a1 = metrics.compute_accuracy(records)
        a2 = metrics.compute_accuracy(records)
        assert a1.accuracy_rate == a2.accuracy_rate
        assert a1.matched == a2.matched

    def test_context_hash_determinism(self) -> None:
        intent = _make_intent(intent_id="stable")
        r1 = record_from_intent(intent)
        r2 = record_from_intent(intent)
        assert r1.context_hash == r2.context_hash


# ── INVARIANT ENFORCEMENT ────────────────────────────────────────────


class TestInvariants:
    def test_inv40_predictions_stored_immutably(self) -> None:
        """Inv 40: core fields of PredictionRecord cannot be changed after store."""
        store = PredictionStore()
        rec = _make_record()
        original_goal = rec.inferred_goal
        original_confidence = rec.confidence
        original_actions = rec.predicted_actions
        store.append(rec)
        store.mark_matched(rec.prediction_id)
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.inferred_goal == original_goal
        assert found.confidence == original_confidence
        assert found.predicted_actions == original_actions

    def test_inv41_outcomes_linked_to_predictions(self) -> None:
        """Inv 41: matched predictions carry the matched_job_id."""
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        store.mark_matched(rec.prediction_id, matched_job_id="real_job_42")
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.matched_job_id == "real_job_42"

    def test_inv42_accuracy_does_not_mutate_records(self) -> None:
        """Inv 42: metrics computation is read-only."""
        metrics = PredictionMetrics()
        rec = _make_record()
        rec.status = PredictionStatus.MATCHED
        rec.resolved_at = "2026-04-29T10:00:00Z"
        before_status = rec.status
        before_resolved = rec.resolved_at
        metrics.compute_accuracy([rec])
        metrics.compute_confidence_calibration([rec])
        metrics.compute_source_accuracy([rec])
        assert rec.status == before_status
        assert rec.resolved_at == before_resolved

    def test_inv43_evaluation_deterministic(self) -> None:
        """Inv 43: same inputs → same match results."""
        evaluator = PredictionEvaluator()
        pred = _make_record(entities=("outreach",))
        fb = _make_feedback(task_type="outreach", job_id="j43")
        r1 = evaluator.match_predictions([pred], [fb])
        r2 = evaluator.match_predictions([pred], [fb])
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2):
            assert a.matched == b.matched
            assert a.match_reason == b.match_reason

    def test_inv44_no_retroactive_rewriting(self) -> None:
        """Inv 44: resolved predictions cannot be re-resolved."""
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        store.mark_matched(rec.prediction_id, matched_job_id="first_match")
        result = store.mark_missed(rec.prediction_id)
        assert result is False
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.status == PredictionStatus.MATCHED
        assert found.matched_job_id == "first_match"


# ── BOUNDARY INVARIANTS ──────────────────────────────────────────────

_PHASE21_FILES = [
    os.path.join(os.path.dirname(__file__), "..", "..", "umh", "prediction", "store.py"),
    os.path.join(os.path.dirname(__file__), "..", "..", "umh", "prediction", "evaluator.py"),
    os.path.join(os.path.dirname(__file__), "..", "..", "umh", "prediction", "metrics.py"),
]


class TestBoundaryInvariants:
    @pytest.mark.parametrize("filepath", _PHASE21_FILES)
    def test_no_cells_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                assert "umh.cells" not in mod, f"cells import in {filepath}"

    @pytest.mark.parametrize("filepath", _PHASE21_FILES)
    def test_no_environments_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                assert "umh.environments" not in mod, f"environments import in {filepath}"

    @pytest.mark.parametrize("filepath", _PHASE21_FILES)
    def test_no_subprocess_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                names = [a.name for a in node.names] if hasattr(node, "names") else []
                full = mod + " ".join(names)
                assert "subprocess" not in full, f"subprocess import in {filepath}"

    @pytest.mark.parametrize("filepath", _PHASE21_FILES)
    def test_no_shell_true(self, filepath: str) -> None:
        source = open(filepath).read()
        assert "shell=True" not in source, f"shell=True in {filepath}"


# ── REGRESSION ───────────────────────────────────────────────────────


class TestRegression:
    def test_phase20_predictor_unchanged(self) -> None:
        p = Predictor()
        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        intents = p.predict_intent(ctx, now=_ref_time())
        assert len(intents) >= 1

    def test_phase20_planner_unchanged(self) -> None:
        from umh.prediction.planner import PredictivePlanner

        planner = PredictivePlanner()
        intent = _make_intent()
        result = planner.predict_plan(intent)
        assert result is not None
        assert result.speculative is True

    def test_phase19_feedback_store_unchanged(self) -> None:
        store = FeedbackStore()
        fb = _make_feedback()
        store.record(fb)
        assert store.total == 1

    def test_advisor_backward_compat(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert "predictions_generated" in result
        assert "predictions_stored" in result
        assert "predictions_matched" in result
        assert "predictions_expired" in result
        advisor.stop()
