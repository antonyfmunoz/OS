"""Phase 23 tests — Cross-Session Memory + Temporal Pattern System v1.

Tests persistence, temporal decay, bootstrap rehydration, advisor integration,
safety controls, determinism, and hard invariants 50-54.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from umh.core.clock import iso_now
from umh.prediction.persistence import (
    FilePredictionBackend,
    PersistenceStats,
    _record_from_json,
    _record_to_json,
)
from umh.prediction.store import PredictionRecord, PredictionStatus, PredictionStore
from umh.prediction.temporal import DecayResult, TemporalWeighter
from umh.prediction.weights import PredictionWeight, WeightStore
from umh.runtime.bootstrap import PredictionBootstrapReport, RuntimeBootstrap


# ── helpers ──────────────────────────────────────────────────


def _make_record(
    pid: str = "pred_test001",
    goal: str = "test_goal",
    confidence: float = 0.7,
    source: str = "test_source",
    status: PredictionStatus = PredictionStatus.PENDING,
    tick: int = 1,
    actions: tuple[str, ...] = ("action_a",),
    entities: tuple[str, ...] = ("entity_a",),
) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=pid,
        intent_id=f"intent_{pid}",
        inferred_goal=goal,
        confidence=confidence,
        predicted_actions=actions,
        related_entities=entities,
        source=source,
        context_hash="abcdef1234567890",
        emitted_at=iso_now(),
        status=status,
        tick_emitted=tick,
    )


def _make_iso(hours_ago: float = 0.0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return dt.isoformat()


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


# ══════════════════════════════════════════════════════════════
# PART 1 — FilePredictionBackend: Record Persistence
# ══════════════════════════════════════════════════════════════


class TestRecordSerialization:
    def test_record_round_trip(self):
        rec = _make_record()
        data = _record_to_json(rec)
        restored = _record_from_json(data)
        assert restored.prediction_id == rec.prediction_id
        assert restored.inferred_goal == rec.inferred_goal
        assert restored.confidence == rec.confidence
        assert restored.predicted_actions == rec.predicted_actions
        assert restored.related_entities == rec.related_entities

    def test_record_with_matched_status(self):
        rec = _make_record(status=PredictionStatus.MATCHED)
        data = _record_to_json(rec)
        restored = _record_from_json(data)
        assert restored.status == PredictionStatus.MATCHED

    def test_record_with_all_statuses(self):
        for status in PredictionStatus:
            rec = _make_record(status=status)
            data = _record_to_json(rec)
            restored = _record_from_json(data)
            assert restored.status == status

    def test_record_preserves_metadata(self):
        rec = _make_record()
        rec.metadata["custom"] = "value"
        data = _record_to_json(rec)
        restored = _record_from_json(data)
        assert restored.metadata.get("custom") == "value"


class TestFilePredictionBackendRecords:
    def test_save_and_load_records(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        records = [_make_record(pid=f"pred_{i:03d}") for i in range(5)]
        save_stats = backend.save_records(records)
        assert save_stats.records_saved == 5

        loaded, load_stats = backend.load_records()
        assert load_stats.records_loaded == 5
        assert len(loaded) == 5
        assert loaded[0].prediction_id == "pred_000"

    def test_empty_load(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        loaded, stats = backend.load_records()
        assert len(loaded) == 0
        assert stats.records_loaded == 0

    def test_atomic_write_creates_file(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        backend.save_records([_make_record()])
        assert backend.records_path.exists()

    def test_corrupted_lines_skipped(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        records_path = backend.records_path
        os.makedirs(tmp_dir, exist_ok=True)
        with open(records_path, "w") as f:
            good = _record_to_json(_make_record(pid="good_001"))
            f.write(json.dumps(good) + "\n")
            f.write("THIS IS CORRUPTED JSON\n")
            f.write("{invalid json too\n")
            good2 = _record_to_json(_make_record(pid="good_002"))
            f.write(json.dumps(good2) + "\n")

        loaded, stats = backend.load_records()
        assert stats.records_loaded == 2
        assert stats.records_skipped == 2
        assert loaded[0].prediction_id == "good_001"
        assert loaded[1].prediction_id == "good_002"

    def test_empty_lines_skipped(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        with open(backend.records_path, "w") as f:
            good = _record_to_json(_make_record())
            f.write("\n\n" + json.dumps(good) + "\n\n")
        loaded, stats = backend.load_records()
        assert stats.records_loaded == 1

    def test_overwrite_replaces_file(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        backend.save_records([_make_record(pid="first")])
        backend.save_records([_make_record(pid="second")])
        loaded, _ = backend.load_records()
        assert len(loaded) == 1
        assert loaded[0].prediction_id == "second"

    def test_large_batch(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        records = [_make_record(pid=f"pred_{i:05d}") for i in range(500)]
        stats = backend.save_records(records)
        assert stats.records_saved == 500
        loaded, lstats = backend.load_records()
        assert lstats.records_loaded == 500


# ══════════════════════════════════════════════════════════════
# PART 2 — FilePredictionBackend: Weight Persistence
# ══════════════════════════════════════════════════════════════


class TestFilePredictionBackendWeights:
    def test_save_and_load_weights(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        weights = [
            {"pattern_key": "workflow_a", "weight": 1.5, "success_count": 3, "failure_count": 1},
            {"pattern_key": "workflow_b", "weight": 0.8, "success_count": 1, "failure_count": 4},
        ]
        stats = backend.save_weights(weights)
        assert stats.weights_saved == 2

        loaded, lstats = backend.load_weights()
        assert lstats.weights_loaded == 2
        assert loaded[0]["pattern_key"] == "workflow_a"
        assert loaded[1]["weight"] == 0.8

    def test_empty_weight_load(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        loaded, stats = backend.load_weights()
        assert len(loaded) == 0

    def test_corrupted_weight_file(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        with open(backend.weights_path, "w") as f:
            f.write("NOT VALID JSON")
        loaded, stats = backend.load_weights()
        assert len(loaded) == 0
        assert stats.weights_skipped == 0
        assert stats.errors

    def test_weight_file_not_array(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        with open(backend.weights_path, "w") as f:
            json.dump({"not": "array"}, f)
        loaded, stats = backend.load_weights()
        assert len(loaded) == 0
        assert stats.weights_skipped == 1

    def test_weight_entries_without_pattern_key_skipped(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        data = [
            {"pattern_key": "valid", "weight": 1.0},
            {"no_key": True, "weight": 0.5},
        ]
        os.makedirs(tmp_dir, exist_ok=True)
        with open(backend.weights_path, "w") as f:
            json.dump(data, f)
        loaded, stats = backend.load_weights()
        assert stats.weights_loaded == 1
        assert stats.weights_skipped == 1


# ══════════════════════════════════════════════════════════════
# PART 3 — FilePredictionBackend: Safety
# ══════════════════════════════════════════════════════════════


class TestPersistenceSafety:
    def test_nonexistent_dir_created(self, tmp_dir):
        sub = os.path.join(tmp_dir, "deep", "nested", "dir")
        backend = FilePredictionBackend(sub)
        backend.save_records([_make_record()])
        assert Path(sub).exists()

    def test_backend_exists_false_initially(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        assert not backend.exists()

    def test_backend_exists_after_save(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        backend.save_records([_make_record()])
        assert backend.exists()

    def test_readonly_dir_returns_error_stats(self):
        backend = FilePredictionBackend("/proc/nonexistent_dir_for_test")
        stats = backend.save_records([_make_record()])
        assert stats.errors


# ══════════════════════════════════════════════════════════════
# PART 4 — TemporalWeighter: Decay Logic
# ══════════════════════════════════════════════════════════════


class TestTemporalWeighterDecay:
    def test_no_decay_at_zero_age(self):
        tw = TemporalWeighter()
        result = tw.apply_decay(2.0, 0.0)
        assert result.decayed_weight == 2.0
        assert result.decay_factor == 1.0

    def test_decay_reduces_high_weight(self):
        tw = TemporalWeighter(decay_rate=0.01)
        result = tw.apply_decay(2.5, 100.0)
        assert result.decayed_weight < 2.5
        assert result.decayed_weight > 1.0

    def test_decay_increases_low_weight_toward_baseline(self):
        tw = TemporalWeighter(decay_rate=0.01)
        result = tw.apply_decay(0.3, 100.0)
        assert result.decayed_weight > 0.3
        assert result.decayed_weight <= 1.0

    def test_full_decay_converges_to_baseline(self):
        tw = TemporalWeighter(decay_rate=0.01)
        result = tw.apply_decay(3.0, 10000.0)
        assert abs(result.decayed_weight - 1.0) < 0.01

    def test_negative_age_treated_as_zero(self):
        tw = TemporalWeighter()
        result = tw.apply_decay(2.0, -5.0)
        assert result.decayed_weight == 2.0
        assert result.age_hours == 0.0

    def test_zero_decay_rate_preserves_weight(self):
        tw = TemporalWeighter(decay_rate=0.0)
        result = tw.apply_decay(2.5, 1000.0)
        assert result.decayed_weight == 2.5
        assert result.decay_factor == 1.0

    def test_decay_is_deterministic(self):
        tw = TemporalWeighter(decay_rate=0.005)
        r1 = tw.apply_decay(1.8, 48.0)
        r2 = tw.apply_decay(1.8, 48.0)
        assert r1.decayed_weight == r2.decayed_weight

    def test_decay_result_fields(self):
        tw = TemporalWeighter(decay_rate=0.01)
        result = tw.apply_decay(2.0, 50.0)
        assert result.original_weight == 2.0
        assert result.age_hours == 50.0
        assert 0 < result.decay_factor < 1
        assert result.decayed_weight > 0

    def test_weight_clamped_above(self):
        tw = TemporalWeighter(max_weight=3.0)
        result = tw.apply_decay(5.0, 0.0)
        assert result.decayed_weight == 3.0

    def test_weight_clamped_below(self):
        tw = TemporalWeighter(min_weight=0.1)
        result = tw.apply_decay(0.05, 0.0)
        assert result.decayed_weight == 0.1


class TestTemporalWeighterAgeCompute:
    def test_compute_age_hours(self):
        tw = TemporalWeighter()
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=24)
        age = tw.compute_age_hours(past.isoformat(), now.isoformat())
        assert abs(age - 24.0) < 0.01

    def test_compute_age_same_time(self):
        tw = TemporalWeighter()
        t = datetime.now(timezone.utc).isoformat()
        assert tw.compute_age_hours(t, t) == 0.0

    def test_compute_age_future_returns_zero(self):
        tw = TemporalWeighter()
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        assert tw.compute_age_hours(future.isoformat(), now.isoformat()) == 0.0

    def test_compute_age_invalid_returns_zero(self):
        tw = TemporalWeighter()
        assert tw.compute_age_hours("not-a-date", iso_now()) == 0.0
        assert tw.compute_age_hours(iso_now(), "bad") == 0.0

    def test_compute_age_naive_timestamps(self):
        tw = TemporalWeighter()
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=10)
        age = tw.compute_age_hours(
            past.replace(tzinfo=None).isoformat(),
            now.replace(tzinfo=None).isoformat(),
        )
        assert abs(age - 10.0) < 0.01


class TestTemporalWeighterConfig:
    def test_negative_decay_rate_rejected(self):
        with pytest.raises(ValueError, match="decay_rate"):
            TemporalWeighter(decay_rate=-0.1)

    def test_get_state(self):
        tw = TemporalWeighter(decay_rate=0.01, baseline=1.0)
        state = tw.get_state()
        assert state["decay_rate"] == 0.01
        assert state["baseline"] == 1.0

    def test_decay_result_to_dict(self):
        tw = TemporalWeighter()
        result = tw.apply_decay(1.5, 10.0)
        d = result.to_dict()
        assert "original_weight" in d
        assert "decayed_weight" in d
        assert "age_hours" in d
        assert "decay_factor" in d


# ══════════════════════════════════════════════════════════════
# PART 5 — WeightStore: last_updated + restore
# ══════════════════════════════════════════════════════════════


class TestWeightStoreTimestamp:
    def test_update_sets_last_updated(self):
        ws = WeightStore()
        ws.update_weight("p1", matched=True)
        ws.update_weight("p1", matched=True)
        pw = ws.get_weight("p1")
        assert pw.last_updated != ""

    def test_restore_weight(self):
        ws = WeightStore()
        ws.restore_weight("p1", weight=1.8, success_count=5, failure_count=2, last_updated="2026-01-01T00:00:00Z")
        pw = ws.get_weight("p1")
        assert pw.weight == 1.8
        assert pw.success_count == 5
        assert pw.failure_count == 2
        assert pw.last_updated == "2026-01-01T00:00:00Z"

    def test_restore_clamps_weight(self):
        ws = WeightStore()
        ws.restore_weight("p1", weight=10.0, success_count=0, failure_count=0)
        assert ws.get_weight("p1").weight == 3.0
        ws.restore_weight("p2", weight=-5.0, success_count=0, failure_count=0)
        assert ws.get_weight("p2").weight == 0.1

    def test_restore_clamps_negative_counts(self):
        ws = WeightStore()
        ws.restore_weight("p1", weight=1.0, success_count=-3, failure_count=-1)
        pw = ws.get_weight("p1")
        assert pw.success_count == 0
        assert pw.failure_count == 0

    def test_to_dict_includes_last_updated(self):
        ws = WeightStore()
        ws.restore_weight("p1", weight=1.5, success_count=3, failure_count=1, last_updated="2026-04-01T00:00:00Z")
        d = ws.get_weight("p1").to_dict()
        assert d["last_updated"] == "2026-04-01T00:00:00Z"


# ══════════════════════════════════════════════════════════════
# PART 6 — Bootstrap: Prediction Rehydration
# ══════════════════════════════════════════════════════════════


class TestPredictionBootstrap:
    def test_rehydrate_records(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        records = [_make_record(pid=f"pred_{i:03d}") for i in range(3)]
        backend.save_records(records)

        store = PredictionStore()
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend, store=store)

        assert report.records_loaded == 3
        assert report.records_restored == 3
        assert store.total == 3

    def test_rehydrate_weights(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        weights = [
            {"pattern_key": "p1", "weight": 1.5, "success_count": 3, "failure_count": 1, "last_updated": "2026-01-01T00:00:00Z"},
            {"pattern_key": "p2", "weight": 0.8, "success_count": 1, "failure_count": 4},
        ]
        backend.save_weights(weights)

        ws = WeightStore()
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend, weight_store=ws)

        assert report.weights_loaded == 2
        assert report.weights_restored == 2
        assert ws.get_weight("p1").weight == 1.5
        assert ws.get_weight("p2").weight == 0.8

    def test_rehydrate_both(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        backend.save_records([_make_record()])
        backend.save_weights([{"pattern_key": "p1", "weight": 2.0, "success_count": 5, "failure_count": 0}])

        store = PredictionStore()
        ws = WeightStore()
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend, store=store, weight_store=ws)

        assert report.records_restored == 1
        assert report.weights_restored == 1

    def test_rehydrate_empty_backend(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend)
        assert report.records_loaded == 0
        assert report.weights_loaded == 0
        assert not report.errors

    def test_rehydrate_corrupted_records(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        with open(backend.records_path, "w") as f:
            good = _record_to_json(_make_record(pid="good"))
            f.write(json.dumps(good) + "\n")
            f.write("CORRUPTED LINE\n")

        store = PredictionStore()
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend, store=store)
        assert report.records_loaded == 1
        assert report.records_skipped == 1
        assert store.total == 1

    def test_rehydrate_report_to_dict(self, tmp_dir):
        report = PredictionBootstrapReport()
        report.records_loaded = 5
        report.records_restored = 4
        report.records_skipped = 1
        d = report.to_dict()
        assert d["records_loaded"] == 5
        assert d["records_restored"] == 4
        assert d["records_skipped"] == 1


# ══════════════════════════════════════════════════════════════
# PART 7 — Advisor: Persistence + Temporal Integration
# ══════════════════════════════════════════════════════════════


class TestAdvisorPersistence:
    def _make_advisor(self, tmp_dir, **kwargs):
        from umh.prediction.calibrator import ConfidenceCalibrator, ThresholdAdapter
        from umh.prediction.evaluator import PredictionEvaluator
        from umh.prediction.metrics import PredictionMetrics
        from umh.runtime.advisor import AdvisorRuntime

        store = PredictionStore()
        ws = WeightStore()
        backend = FilePredictionBackend(tmp_dir)
        tw = TemporalWeighter()
        return AdvisorRuntime(
            prediction_store=store,
            weight_store=ws,
            persistence_backend=backend,
            temporal_weighter=tw,
            prediction_metrics=PredictionMetrics(),
            threshold_adapter=ThresholdAdapter(),
            confidence_calibrator=ConfidenceCalibrator(ws),
            prediction_evaluator=PredictionEvaluator(),
            **kwargs,
        )

    def test_tick_persists_state(self, tmp_dir):
        advisor = self._make_advisor(tmp_dir)
        advisor.start()
        result = advisor.tick()
        assert result["persisted"] is True
        backend = advisor.persistence_backend
        assert backend.exists()

    def test_tick_without_persistence(self):
        from umh.runtime.advisor import AdvisorRuntime
        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert result["persisted"] is False

    def test_state_includes_persistence_flag(self, tmp_dir):
        advisor = self._make_advisor(tmp_dir)
        state = advisor.get_state()
        assert state["persistence_enabled"] is True

    def test_state_includes_temporal_decay_rate(self, tmp_dir):
        advisor = self._make_advisor(tmp_dir)
        state = advisor.get_state()
        assert "temporal_decay_rate" in state

    def test_decayed_weights_available(self, tmp_dir):
        advisor = self._make_advisor(tmp_dir)
        advisor.weight_store.restore_weight(
            "test_pattern", weight=2.0, success_count=5, failure_count=1,
            last_updated=_make_iso(hours_ago=100),
        )
        decayed = advisor.get_decayed_weights()
        assert "test_pattern" in decayed
        assert decayed["test_pattern"] < 2.0

    def test_decayed_weights_empty_without_temporal(self):
        from umh.runtime.advisor import AdvisorRuntime
        advisor = AdvisorRuntime()
        assert advisor.get_decayed_weights() == {}


class TestAdvisorPersistenceRoundTrip:
    def test_records_survive_restart(self, tmp_dir):
        from umh.runtime.advisor import AdvisorRuntime

        backend = FilePredictionBackend(tmp_dir)
        store1 = PredictionStore()
        store1.append(_make_record(pid="persist_001"))
        store1.append(_make_record(pid="persist_002"))

        advisor1 = AdvisorRuntime(
            prediction_store=store1,
            persistence_backend=backend,
        )
        advisor1.start()
        advisor1.tick()

        store2 = PredictionStore()
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend, store=store2)
        assert report.records_restored == 2
        assert store2.total == 2

    def test_weights_survive_restart(self, tmp_dir):
        from umh.runtime.advisor import AdvisorRuntime

        backend = FilePredictionBackend(tmp_dir)
        ws1 = WeightStore()
        ws1.restore_weight("pattern_a", weight=1.8, success_count=4, failure_count=1)

        advisor1 = AdvisorRuntime(
            weight_store=ws1,
            persistence_backend=backend,
            prediction_store=PredictionStore(),
        )
        advisor1.start()
        advisor1.tick()

        ws2 = WeightStore()
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend, weight_store=ws2)
        assert report.weights_restored == 1
        assert ws2.get_weight("pattern_a").weight == 1.8


# ══════════════════════════════════════════════════════════════
# PART 8 — Loop Integration
# ══════════════════════════════════════════════════════════════


class TestLoopPersistence:
    def test_loop_tick_persists(self, tmp_dir):
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.loop import RuntimeLoop

        backend = FilePredictionBackend(tmp_dir)
        store = PredictionStore()
        store.append(_make_record())

        advisor = AdvisorRuntime(
            prediction_store=store,
            persistence_backend=backend,
        )
        loop = RuntimeLoop(advisor=advisor)
        loop.start()
        result = loop.tick()
        assert result["persisted"] is True
        assert backend.exists()


# ══════════════════════════════════════════════════════════════
# PART 9 — Safety Controls
# ══════════════════════════════════════════════════════════════


class TestSafetyControls:
    def test_decay_weight_never_exceeds_bounds(self):
        tw = TemporalWeighter(min_weight=0.1, max_weight=3.0)
        for w in [0.01, 0.1, 1.0, 3.0, 5.0, 100.0]:
            for age in [0, 1, 10, 100, 1000, 10000]:
                result = tw.apply_decay(w, age)
                assert 0.1 <= result.decayed_weight <= 3.0

    def test_persistence_failure_does_not_crash_advisor(self):
        from umh.runtime.advisor import AdvisorRuntime

        backend = FilePredictionBackend("/proc/nonexistent_impossible_path")
        advisor = AdvisorRuntime(
            persistence_backend=backend,
            prediction_store=PredictionStore(),
        )
        advisor.start()
        result = advisor.tick()
        assert result["persisted"] is False

    def test_rehydration_failure_does_not_crash(self):
        backend = FilePredictionBackend("/proc/nonexistent_impossible_path")
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend)
        assert report.records_loaded == 0
        assert report.weights_loaded == 0

    def test_system_works_without_persistence(self):
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert result["persisted"] is False
        assert result["tick"] == 1

    def test_system_works_without_temporal(self):
        from umh.runtime.advisor import AdvisorRuntime

        ws = WeightStore()
        advisor = AdvisorRuntime(weight_store=ws)
        assert advisor.get_decayed_weights() == {}


# ══════════════════════════════════════════════════════════════
# PART 10 — Determinism
# ══════════════════════════════════════════════════════════════


class TestDeterminism:
    def test_same_decay_same_result(self):
        tw = TemporalWeighter(decay_rate=0.005)
        r1 = tw.apply_decay(1.5, 72.0)
        r2 = tw.apply_decay(1.5, 72.0)
        assert r1.decayed_weight == r2.decayed_weight
        assert r1.decay_factor == r2.decay_factor

    def test_same_persistence_same_output(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        records = [_make_record(pid=f"det_{i}") for i in range(3)]
        backend.save_records(records)
        loaded1, _ = backend.load_records()
        loaded2, _ = backend.load_records()
        assert len(loaded1) == len(loaded2)
        for a, b in zip(loaded1, loaded2):
            assert a.prediction_id == b.prediction_id

    def test_same_rehydration_same_state(self, tmp_dir):
        backend = FilePredictionBackend(tmp_dir)
        backend.save_weights([
            {"pattern_key": "p1", "weight": 1.5, "success_count": 3, "failure_count": 1},
        ])

        ws1 = WeightStore()
        ws2 = WeightStore()
        bootstrap = RuntimeBootstrap()
        bootstrap.rehydrate_predictions(backend, weight_store=ws1)
        bootstrap.rehydrate_predictions(backend, weight_store=ws2)
        assert ws1.get_weight("p1").weight == ws2.get_weight("p1").weight


# ══════════════════════════════════════════════════════════════
# PART 11 — Hard Invariants 50-54
# ══════════════════════════════════════════════════════════════


class TestInvariantEnforcement:
    def test_inv50_historical_data_never_overwritten(self, tmp_dir):
        """INV50: Historical prediction data must never be overwritten."""
        backend = FilePredictionBackend(tmp_dir)
        rec1 = _make_record(pid="hist_001", status=PredictionStatus.MATCHED)
        backend.save_records([rec1])
        loaded1, _ = backend.load_records()
        assert loaded1[0].status == PredictionStatus.MATCHED

        rec2 = _make_record(pid="hist_002", status=PredictionStatus.PENDING)
        backend.save_records([rec1, rec2])
        loaded2, _ = backend.load_records()
        assert len(loaded2) == 2
        assert loaded2[0].prediction_id == "hist_001"
        assert loaded2[0].status == PredictionStatus.MATCHED

    def test_inv51_atomic_write_safety(self, tmp_dir):
        """INV51: Persistence must be append-only or atomic-write safe."""
        backend = FilePredictionBackend(tmp_dir)
        records = [_make_record(pid=f"atomic_{i}") for i in range(10)]
        backend.save_records(records)

        loaded, stats = backend.load_records()
        assert stats.records_loaded == 10
        assert stats.records_skipped == 0

    def test_inv52_time_decay_deterministic(self):
        """INV52: Time decay must be deterministic."""
        tw = TemporalWeighter(decay_rate=0.01)
        results = [tw.apply_decay(2.0, 100.0) for _ in range(10)]
        weights = [r.decayed_weight for r in results]
        assert len(set(weights)) == 1

    def test_inv53_rehydration_does_not_corrupt(self, tmp_dir):
        """INV53: Rehydration must not corrupt state."""
        backend = FilePredictionBackend(tmp_dir)
        original_records = [
            _make_record(pid="rehyd_001", status=PredictionStatus.MATCHED),
            _make_record(pid="rehyd_002", status=PredictionStatus.EXPIRED),
            _make_record(pid="rehyd_003"),
        ]
        backend.save_records(original_records)

        store = PredictionStore()
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate_predictions(backend, store=store)

        assert store.total == 3
        r1 = store.get("rehyd_001")
        assert r1 is not None
        assert r1.status == PredictionStatus.MATCHED
        r2 = store.get("rehyd_002")
        assert r2.status == PredictionStatus.EXPIRED

    def test_inv54_system_functions_without_persistence(self):
        """INV54: System must function without persistence (graceful fallback)."""
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.loop import RuntimeLoop

        advisor = AdvisorRuntime()
        loop = RuntimeLoop(advisor=advisor)
        loop.start()
        r1 = loop.tick()
        r2 = loop.tick()
        assert r1["tick"] == 1
        assert r2["tick"] == 2
        assert r1["persisted"] is False
        loop.stop()


# ══════════════════════════════════════════════════════════════
# PART 12 — Boundary Invariants
# ══════════════════════════════════════════════════════════════


_CHECKED_MODULES = [
    "/opt/OS/umh/prediction/persistence.py",
    "/opt/OS/umh/prediction/temporal.py",
]


class TestBoundaryInvariants:
    """No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell."""

    @pytest.mark.parametrize("module_path", _CHECKED_MODULES)
    def test_no_cells_import(self, module_path):
        content = Path(module_path).read_text()
        assert "from umh.cells" not in content
        assert "import umh.cells" not in content

    @pytest.mark.parametrize("module_path", _CHECKED_MODULES)
    def test_no_environments_import(self, module_path):
        content = Path(module_path).read_text()
        assert "from umh.environments" not in content
        assert "import umh.environments" not in content

    @pytest.mark.parametrize("module_path", _CHECKED_MODULES)
    def test_no_subprocess_import(self, module_path):
        content = Path(module_path).read_text()
        assert "import subprocess" not in content
        assert "from subprocess" not in content

    @pytest.mark.parametrize("module_path", _CHECKED_MODULES)
    def test_no_shell_execution(self, module_path):
        content = Path(module_path).read_text()
        for forbidden in ["os.system", "os.popen"]:
            assert forbidden not in content


# ══════════════════════════════════════════════════════════════
# PART 13 — Regression
# ══════════════════════════════════════════════════════════════


class TestRegression:
    def test_weight_store_backward_compatible(self):
        """Phase 22 WeightStore API works unchanged."""
        ws = WeightStore()
        ws.update_weight("p1", matched=True)
        ws.update_weight("p1", matched=False)
        pw = ws.get_weight("p1")
        assert pw.total_predictions == 2
        assert pw.success_rate == 0.5

    def test_prediction_store_backward_compatible(self):
        """Phase 21 PredictionStore API works unchanged."""
        store = PredictionStore()
        rec = _make_record()
        store.append(rec)
        assert store.total == 1
        assert store.pending_count == 1
        store.mark_matched(rec.prediction_id, matched_job_id="job_1")
        matched_rec = store.get(rec.prediction_id)
        assert matched_rec.status == PredictionStatus.MATCHED

    def test_advisor_backward_compatible(self):
        """AdvisorRuntime() without new params works identically to Phase 22."""
        from umh.runtime.advisor import AdvisorRuntime
        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert result["tick"] == 1
        assert result["persisted"] is False
        assert result["weights_updated"] == 0
        advisor.stop()

    def test_bootstrap_job_rehydration_unchanged(self):
        """Phase 18 bootstrap still works for jobs."""
        from umh.jobs.store import JobStore
        bootstrap = RuntimeBootstrap()
        store = JobStore()
        report = bootstrap.rehydrate(store)
        assert report.total_loaded == 0
