"""Tests for the AssistedExecutor — Phase 5.9."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_modes import (
    ExecutionMode,
    ExecutionModeManager,
    TransitionReason,
)
from substrate.organism.leverage_metrics import LeverageMetrics
from substrate.organism.assisted_executor import (
    ActionResult,
    AssistedExecutor,
)
from substrate.organism.maintenance_loop import ActionCategory


def _make_executor(mode: ExecutionMode = ExecutionMode.OBSERVE) -> AssistedExecutor:
    spine = EventSpine()
    mode_mgr = ExecutionModeManager(initial_mode=mode, event_spine=spine)
    leverage = LeverageMetrics(event_spine=spine)
    return AssistedExecutor(
        execution_mode=mode_mgr,
        event_spine=spine,
        leverage_metrics=leverage,
    )


def _make_assisted_executor() -> AssistedExecutor:
    spine = EventSpine()
    mode_mgr = ExecutionModeManager(initial_mode=ExecutionMode.OBSERVE, event_spine=spine)
    mode_mgr.promote(
        ExecutionMode.ASSISTED,
        reason=TransitionReason.OPERATOR_PROMOTION,
        justification="test promotion",
    )
    leverage = LeverageMetrics(event_spine=spine)
    return AssistedExecutor(
        execution_mode=mode_mgr,
        event_spine=spine,
        leverage_metrics=leverage,
    )


def test_blocked_in_observe_mode():
    executor = _make_executor(ExecutionMode.OBSERVE)
    result = executor.execute_action(
        action_id="test-1",
        category=ActionCategory.LOG_ROTATION,
        description="Rotate logs",
    )
    assert result.result == ActionResult.BLOCKED


def test_can_execute_in_assisted_mode():
    executor = _make_assisted_executor()
    result = executor.execute_action(
        action_id="test-1",
        category=ActionCategory.RUNTIME_REFRESH,
        description="Refresh runtime",
    )
    assert result.result in (ActionResult.SUCCESS, ActionResult.FAILED)
    assert result.result != ActionResult.BLOCKED


def test_audit_trail():
    executor = _make_assisted_executor()
    executor.execute_action(
        action_id="test-1",
        category=ActionCategory.RUNTIME_REFRESH,
        description="Refresh",
    )
    trail = executor.audit_trail(10)
    assert len(trail) == 1
    assert trail[0]["action_id"] == "test-1"


def test_critical_container_protection():
    executor = _make_assisted_executor()
    result = executor.execute_action(
        action_id="test-1",
        category=ActionCategory.CONTAINER_RESTART,
        description="Restart os-operator",
        params={"container": "os-operator"},
    )
    assert result.result == ActionResult.FAILED
    assert "critical" in result.output.lower() or "Refusing" in result.output


def test_to_dict():
    executor = _make_assisted_executor()
    executor.execute_action(
        action_id="test-1",
        category=ActionCategory.RUNTIME_REFRESH,
        description="Refresh",
    )
    d = executor.to_dict()
    assert d["total_executed"] >= 1
    assert d["can_execute"] is True


def test_event_emission():
    spine = EventSpine()
    mode_mgr = ExecutionModeManager(initial_mode=ExecutionMode.OBSERVE, event_spine=spine)
    mode_mgr.promote(
        ExecutionMode.ASSISTED,
        reason=TransitionReason.OPERATOR_PROMOTION,
        justification="test",
    )
    leverage = LeverageMetrics(event_spine=spine)
    executor = AssistedExecutor(
        execution_mode=mode_mgr,
        event_spine=spine,
        leverage_metrics=leverage,
    )
    executor.execute_action(
        action_id="test-1",
        category=ActionCategory.RUNTIME_REFRESH,
        description="Refresh",
    )
    events = spine.recent(limit=100)
    event_types = [e.event_type for e in events]
    assert "assisted_action_started" in event_types
    assert "assisted_action_completed" in event_types
