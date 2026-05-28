"""Tests for the WorkloadRunner — Phase 5.9."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
from substrate.organism.leverage_metrics import LeverageMetrics
from substrate.organism.operator_compression import OperatorCompression
from substrate.organism.workload_runner import (
    WorkloadRunner,
    WorkloadType,
    WorkloadOutcome,
    WorkloadRisk,
)


def _make_runner() -> WorkloadRunner:
    spine = EventSpine()
    mode = ExecutionModeManager(initial_mode=ExecutionMode.OBSERVE, event_spine=spine)
    leverage = LeverageMetrics(event_spine=spine)
    compression = OperatorCompression(event_spine=spine)
    return WorkloadRunner(
        event_spine=spine,
        execution_mode=mode,
        leverage_metrics=leverage,
        operator_compression=compression,
    )


def test_run_repo_health():
    runner = _make_runner()
    outcome = runner.run_workload(WorkloadType.REPO_HEALTH)
    assert outcome.success
    assert outcome.workload_type == WorkloadType.REPO_HEALTH
    assert outcome.findings


def test_run_disk_pressure():
    runner = _make_runner()
    outcome = runner.run_workload(WorkloadType.DISK_PRESSURE)
    assert outcome.success
    assert "pressure" in outcome.metrics


def test_run_memory_pressure():
    runner = _make_runner()
    outcome = runner.run_workload(WorkloadType.MEMORY_PRESSURE)
    assert outcome.success


def test_run_docker_health():
    runner = _make_runner()
    outcome = runner.run_workload(WorkloadType.DOCKER_HEALTH)
    assert isinstance(outcome, WorkloadOutcome)


def test_run_stale_branches():
    runner = _make_runner()
    outcome = runner.run_workload(WorkloadType.STALE_BRANCH_SCAN)
    assert outcome.success
    assert "total_branches" in outcome.metrics


def test_run_knowledge_staleness():
    runner = _make_runner()
    outcome = runner.run_workload(WorkloadType.KNOWLEDGE_STALENESS)
    assert outcome.success


def test_run_all_observe():
    runner = _make_runner()
    results = runner.run_all_observe()
    assert len(results) >= 5
    assert all(isinstance(r, WorkloadOutcome) for r in results)


def test_medium_risk_blocked_in_observe():
    runner = _make_runner()
    outcome = runner.run_workload(WorkloadType.LOG_ROTATION)
    assert outcome.success is False or "Blocked" in (outcome.error or "")


def test_to_dict():
    runner = _make_runner()
    runner.run_workload(WorkloadType.REPO_HEALTH)
    d = runner.to_dict()
    assert d["total_runs"] >= 1
    assert "success_rate" in d


def test_leverage_recording():
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
    runner.run_workload(WorkloadType.REPO_HEALTH)
    assert leverage._total_tasks >= 1


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
    runner.run_workload(WorkloadType.REPO_HEALTH)
    events = spine.recent(limit=100)
    event_types = [e.event_type for e in events]
    assert "workload_started" in event_types
    assert "workload_completed" in event_types
