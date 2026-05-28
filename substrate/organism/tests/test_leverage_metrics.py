"""Tests for LeverageMetrics engine."""
from __future__ import annotations

import sys
import time

import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from substrate.organism.leverage_metrics import (
    LeverageMetrics,
    TaskRecord,
)


def test_empty_metrics():
    lm = LeverageMetrics()
    s = lm.summary()
    assert s["totals"]["tasks"] == 0
    assert s["dimensions"]["composite"] == 0.0


def test_record_task_updates_totals():
    lm = LeverageMetrics()
    lm.record_task(TaskRecord(
        task_id="t1",
        started_at=time.time() - 10,
        completed_at=time.time(),
        autonomous=True,
        success=True,
        estimated_manual_seconds=60,
    ))
    s = lm.summary()
    assert s["totals"]["tasks"] == 1
    assert s["totals"]["autonomous_resolutions"] == 1


def test_intervention_counted():
    lm = LeverageMetrics()
    lm.record_task(TaskRecord(
        task_id="t1",
        started_at=time.time() - 5,
        completed_at=time.time(),
        autonomous=False,
        required_intervention=True,
        success=True,
    ))
    assert lm.summary()["totals"]["interventions"] == 1
    assert lm.summary()["totals"]["autonomous_resolutions"] == 0


def test_time_compression():
    lm = LeverageMetrics()
    now = time.time()
    lm.record_task(TaskRecord(
        task_id="t1",
        started_at=now - 10,
        completed_at=now,
        estimated_manual_seconds=100,
    ))
    dims = lm.compute_dimensions()
    assert dims.time_compression > 0.5


def test_failure_recovery_speed():
    lm = LeverageMetrics()
    now = time.time()
    lm.record_task(TaskRecord(
        task_id="t-recovery",
        started_at=now - 5,
        completed_at=now,
        success=True,
    ))
    lm.record_failure_recovery(10.0)
    lm.record_failure_recovery(20.0)
    dims = lm.compute_dimensions()
    assert dims.failure_recovery_speed > 0


def test_bottleneck_inputs():
    lm = LeverageMetrics()
    now = time.time()
    lm.record_task(TaskRecord(
        task_id="t1", started_at=now - 5, completed_at=now,
        required_intervention=True, success=False, retries=2,
        escalated=True,
    ))
    inputs = lm.bottleneck_inputs()
    assert inputs["intervention_rate"] == 1.0
    assert inputs["failure_rate"] == 1.0
    assert inputs["retry_rate"] == 2.0
    assert inputs["escalation_rate"] == 1.0


def test_leverage_tick_returns_summary():
    lm = LeverageMetrics()
    result = lm.leverage_tick()
    assert "dimensions" in result
    assert "totals" in result


def test_cost_tracking():
    lm = LeverageMetrics()
    now = time.time()
    lm.record_task(TaskRecord(
        task_id="t1", started_at=now - 5, completed_at=now,
        cost_usd=0.05,
    ))
    assert lm.summary()["totals"]["cost_usd"] == 0.05


def test_operator_seconds_saved():
    lm = LeverageMetrics()
    now = time.time()
    lm.record_task(TaskRecord(
        task_id="t1",
        started_at=now - 10,
        completed_at=now,
        estimated_manual_seconds=120,
    ))
    assert lm.summary()["totals"]["operator_seconds_saved"] > 100


if __name__ == "__main__":
    test_empty_metrics()
    test_record_task_updates_totals()
    test_intervention_counted()
    test_time_compression()
    test_failure_recovery_speed()
    test_bottleneck_inputs()
    test_leverage_tick_returns_summary()
    test_cost_tracking()
    test_operator_seconds_saved()
    print("ALL LEVERAGE METRICS TESTS PASSED")
