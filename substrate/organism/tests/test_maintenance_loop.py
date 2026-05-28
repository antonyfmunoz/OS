"""Tests for the MaintenanceLoop — Phase 5.9."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
from substrate.organism.leverage_metrics import LeverageMetrics
from substrate.organism.operator_compression import OperatorCompression
from substrate.organism.workload_runner import WorkloadRunner
from substrate.organism.maintenance_loop import (
    MaintenanceLoop,
    MaintenanceCycleReport,
    MaintenanceRecommendation,
)


def _make_loop() -> MaintenanceLoop:
    spine = EventSpine()
    mode = ExecutionModeManager(initial_mode=ExecutionMode.OBSERVE, event_spine=spine)
    leverage = LeverageMetrics(event_spine=spine)
    compression = OperatorCompression(event_spine=spine)
    runner = WorkloadRunner(
        event_spine=spine,
        execution_mode=mode,
        leverage_metrics=leverage,
        operator_compression=compression,
    )
    return MaintenanceLoop(
        workload_runner=runner,
        execution_mode=mode,
        event_spine=spine,
    )


def test_maintenance_tick():
    loop = _make_loop()
    result = loop.maintenance_tick()
    assert isinstance(result, dict)
    assert "workloads_run" in result
    assert result["workloads_run"] >= 1
    assert "findings" in result


def test_cycle_count_increments():
    loop = _make_loop()
    loop.maintenance_tick()
    loop.maintenance_tick()
    assert loop._cycle_count == 2


def test_recent_reports():
    loop = _make_loop()
    loop.maintenance_tick()
    reports = loop.recent_reports(5)
    assert len(reports) == 1
    assert reports[0]["cycle_number"] == 1


def test_to_dict():
    loop = _make_loop()
    loop.maintenance_tick()
    d = loop.to_dict()
    assert d["cycle_count"] == 1
    assert d["total_reports"] == 1
    assert d["last_cycle"] is not None


def test_event_emission():
    spine = EventSpine()
    mode = ExecutionModeManager(initial_mode=ExecutionMode.OBSERVE, event_spine=spine)
    leverage = LeverageMetrics(event_spine=spine)
    compression = OperatorCompression(event_spine=spine)
    runner = WorkloadRunner(
        event_spine=spine,
        execution_mode=mode,
        leverage_metrics=leverage,
        operator_compression=compression,
    )
    loop = MaintenanceLoop(
        workload_runner=runner,
        execution_mode=mode,
        event_spine=spine,
    )
    loop.maintenance_tick()
    events = spine.recent(limit=100)
    event_types = [e.event_type for e in events]
    assert "maintenance_cycle_completed" in event_types
