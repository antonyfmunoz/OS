"""Tests for BottleneckEngine."""
from __future__ import annotations

import sys

import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from substrate.organism.bottleneck_engine import (
    BottleneckCategory,
    BottleneckEngine,
    BottleneckSeverity,
)


def test_no_bottlenecks_on_clean_state():
    be = BottleneckEngine()
    detected = be.detect()
    assert len(detected) == 0


def test_high_failure_rate():
    be = BottleneckEngine()
    detected = be.detect(leverage_inputs={"failure_rate": 0.5})
    assert len(detected) == 1
    assert detected[0].category == BottleneckCategory.HIGH_FAILURE_RATE


def test_retry_storm():
    be = BottleneckEngine()
    detected = be.detect(leverage_inputs={"retry_rate": 0.5})
    assert len(detected) == 1
    assert detected[0].category == BottleneckCategory.RETRY_STORM


def test_repetitive_intervention():
    be = BottleneckEngine()
    detected = be.detect(leverage_inputs={"intervention_rate": 0.6})
    assert len(detected) == 1
    assert detected[0].category == BottleneckCategory.REPETITIVE_INTERVENTION


def test_high_latency():
    be = BottleneckEngine()
    detected = be.detect(leverage_inputs={"avg_latency_seconds": 120})
    assert len(detected) == 1
    assert detected[0].category == BottleneckCategory.HIGH_LATENCY


def test_slow_runtime():
    be = BottleneckEngine()
    detected = be.detect(runtime_stats=[
        {"runtime_id": "rt-1", "avg_latency_ms": 10000},
    ])
    assert len(detected) == 1
    assert detected[0].category == BottleneckCategory.SLOW_RUNTIME


def test_queue_buildup():
    be = BottleneckEngine()
    detected = be.detect(queue_depth=100)
    assert len(detected) == 1
    assert detected[0].category == BottleneckCategory.QUEUE_BUILDUP


def test_stalled_objective():
    import time
    be = BottleneckEngine()
    detected = be.detect(stalled_objectives=[
        {"objective_id": "obj-1", "last_progress_at": time.time() - 600},
    ])
    assert len(detected) == 1
    assert detected[0].category == BottleneckCategory.STALLED_OBJECTIVE


def test_recurrence_escalation():
    be = BottleneckEngine()
    for _ in range(6):
        be.detect(leverage_inputs={"failure_rate": 0.5})
    active = be.active
    assert any(b.severity == BottleneckSeverity.CRITICAL for b in active)


def test_multiple_detections():
    be = BottleneckEngine()
    detected = be.detect(
        leverage_inputs={"failure_rate": 0.5, "retry_rate": 0.5},
        queue_depth=100,
    )
    assert len(detected) == 3


def test_history():
    be = BottleneckEngine()
    be.detect(leverage_inputs={"failure_rate": 0.5})
    h = be.history(limit=10)
    assert len(h) == 1


def test_to_dict():
    be = BottleneckEngine()
    be.detect(leverage_inputs={"failure_rate": 0.5})
    d = be.to_dict()
    assert d["active_count"] == 1
    assert "by_severity" in d


def test_tick_engine_failure_rate():
    be = BottleneckEngine()
    detected = be.detect(tick_metrics={
        "total_stages_executed": 10,
        "total_stages_failed": 5,
    })
    assert len(detected) == 1
    assert detected[0].category == BottleneckCategory.FAILING_RECONCILIATION


if __name__ == "__main__":
    test_no_bottlenecks_on_clean_state()
    test_high_failure_rate()
    test_retry_storm()
    test_repetitive_intervention()
    test_high_latency()
    test_slow_runtime()
    test_queue_buildup()
    test_stalled_objective()
    test_recurrence_escalation()
    test_multiple_detections()
    test_history()
    test_to_dict()
    test_tick_engine_failure_rate()
    print("ALL BOTTLENECK ENGINE TESTS PASSED")
