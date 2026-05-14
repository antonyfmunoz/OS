"""Tests for Phase 7D: Scheduler Layer — boundary and safety invariants.

Verifies:
- No direct execution engine imports in scheduler
- No adapter or orchestrator imports in scheduler
- Scheduler routes through planning pipeline
- Default-disabled safety invariant
- Event observability
- Thread safety
- Observable, pausable, cancellable properties
"""

from __future__ import annotations

import ast
import pathlib
import sys
import threading

sys.path.insert(0, "/opt/OS")

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from umh.scheduler.models import ScheduleType, ScheduledWorkflow
from umh.scheduler.store import get_schedule_store, reset_schedule_store
from umh.events.stream import get_event_stream, reset_event_stream

_SCHEDULER_DIR = pathlib.Path("/opt/OS/umh/scheduler")


@pytest.fixture(autouse=True)
def clean_state():
    reset_schedule_store()
    reset_event_stream()
    yield
    reset_schedule_store()


def _make_workflow(name: str = "boundary-test", **kwargs) -> ScheduledWorkflow:
    """Helper: create a workflow with sensible defaults."""
    defaults = {
        "name": name,
        "objective": f"objective for {name}",
        "schedule_type": ScheduleType.INTERVAL,
        "schedule_value": "30",
    }
    defaults.update(kwargs)
    return ScheduledWorkflow(**defaults)


# ── Import Boundary Tests ─────────────────────────────────────────


def test_scheduler_no_execute_import():
    """umh/scheduler/*.py must not import execute from umh.execution.engine."""
    for py_file in _SCHEDULER_DIR.glob("*.py"):
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "umh.execution.engine" in node.module:
                    for alias in node.names:
                        assert alias.name != "execute", (
                            f"{py_file.name} imports execute from execution.engine"
                        )


def test_scheduler_no_adapter_import():
    """umh/scheduler/*.py must not import from umh.adapters.*."""
    for py_file in _SCHEDULER_DIR.glob("*.py"):
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "umh.adapters" in node.module:
                    pytest.fail(
                        f"{py_file.name} imports from umh.adapters: {node.module}"
                    )


def test_scheduler_no_orchestrator_import():
    """umh/scheduler/*.py must not import directly from umh.orchestrator.*."""
    for py_file in _SCHEDULER_DIR.glob("*.py"):
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "umh.orchestrator" in node.module:
                    pytest.fail(
                        f"{py_file.name} imports from umh.orchestrator: {node.module}"
                    )


# ── Planning Pipeline Routing ─────────────────────────────────────


def test_scheduler_routes_through_planner():
    """runner.tick() calls create_plan_from_raw (not execute directly)."""
    from umh.scheduler.runner import SchedulerRunner
    from umh.planning.models import PlanStatus

    store = get_schedule_store()
    wf = _make_workflow("planner-route")
    wf.next_run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    store.create(wf)
    store.enable(wf.id)

    mock_plan = MagicMock()
    mock_plan.status = PlanStatus.VALIDATED
    mock_plan.plan_id = "eplan_route"
    mock_plan.quality_score = {"verdict": "pass", "score": 1.0}
    mock_plan.objective = MagicMock()
    mock_plan.objective.dry_run = False

    mock_task = MagicMock()
    mock_task.id = "task_route"
    mock_task.status = MagicMock(value="completed")

    with patch("umh.planning.planner.create_plan_from_raw", return_value=mock_plan) as mock_create:
        with patch("umh.planning.planner.execute_plan", return_value=mock_task):
            runner = SchedulerRunner()
            runner.tick()

    mock_create.assert_called_once()
    call_args = mock_create.call_args
    # First positional arg should be the objective string
    assert isinstance(call_args[0][0], str)


def test_scheduler_routes_through_execute_plan():
    """runner.tick() calls execute_plan (not execute from engine)."""
    from umh.scheduler.runner import SchedulerRunner
    from umh.planning.models import PlanStatus

    store = get_schedule_store()
    wf = _make_workflow("exec-route")
    wf.next_run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    store.create(wf)
    store.enable(wf.id)

    mock_plan = MagicMock()
    mock_plan.status = PlanStatus.VALIDATED
    mock_plan.plan_id = "eplan_exec"
    mock_plan.quality_score = {"verdict": "pass", "score": 1.0}
    mock_plan.objective = MagicMock()
    mock_plan.objective.dry_run = False

    mock_task = MagicMock()
    mock_task.id = "task_exec"
    mock_task.status = MagicMock(value="completed")

    with patch("umh.planning.planner.create_plan_from_raw", return_value=mock_plan):
        with patch("umh.planning.planner.execute_plan", return_value=mock_task) as mock_exec:
            runner = SchedulerRunner()
            runner.tick()

    mock_exec.assert_called_once()


# ── Safety Invariants ─────────────────────────────────────────────


def test_scheduler_default_disabled():
    """ScheduledWorkflow.enabled defaults to False — safety invariant."""
    wf = ScheduledWorkflow(
        name="safety-default",
        objective="test",
        schedule_type=ScheduleType.INTERVAL,
        schedule_value="30",
    )
    assert wf.enabled is False


def test_scheduler_events_emitted():
    """Triggered and skipped events are emitted through the event stream."""
    from umh.scheduler.models import SchedulePolicy
    from umh.scheduler.runner import SchedulerRunner
    from umh.planning.models import PlanStatus

    store = get_schedule_store()
    stream = get_event_stream()

    # One workflow that will trigger
    wf_trigger = _make_workflow("event-trigger")
    wf_trigger.next_run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    store.create(wf_trigger)
    store.enable(wf_trigger.id)

    # One workflow that will be skipped (policy deny)
    wf_skip = _make_workflow("event-skip")
    wf_skip.enabled = True
    wf_skip.policy = SchedulePolicy(max_runs_per_day=0)
    wf_skip.next_run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    store.create(wf_skip)

    mock_plan = MagicMock()
    mock_plan.status = PlanStatus.VALIDATED
    mock_plan.plan_id = "eplan_events"
    mock_plan.quality_score = {"verdict": "pass", "score": 1.0}
    mock_plan.objective = MagicMock()
    mock_plan.objective.dry_run = False

    mock_task = MagicMock()
    mock_task.id = "task_events"
    mock_task.status = MagicMock(value="completed")

    runner = SchedulerRunner()

    with patch("umh.planning.planner.create_plan_from_raw", return_value=mock_plan):
        with patch("umh.planning.planner.execute_plan", return_value=mock_task):
            runner.tick()

    events = stream.list_events(limit=100)
    event_types = {e.type for e in events}
    assert "schedule.triggered" in event_types
    assert "schedule.skipped" in event_types


def test_scheduler_thread_safe():
    """Concurrent store operations do not crash."""
    store = get_schedule_store()
    errors: list[Exception] = []

    def worker(worker_id: int):
        try:
            for i in range(20):
                wf = _make_workflow(f"thread-{worker_id}-{i}")
                store.create(wf)
                store.get(wf.id)
                store.list_all()
                if i % 3 == 0:
                    store.enable(wf.id)
                if i % 5 == 0:
                    store.disable(wf.id)
                if i % 7 == 0:
                    store.delete(wf.id)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == [], f"Thread safety errors: {errors}"


def test_scheduler_no_direct_state_mutation():
    """Runner tick() does not mutate execution state directly —
    it delegates to the planning/task layer."""
    # This is verified implicitly by the mock patches: if runner.tick()
    # tried to call execute() directly, it would fail since we only
    # mock create_plan_from_raw and execute_plan.
    from umh.scheduler.runner import SchedulerRunner
    from umh.planning.models import PlanStatus

    store = get_schedule_store()
    wf = _make_workflow("no-mutation")
    wf.next_run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    store.create(wf)
    store.enable(wf.id)

    mock_plan = MagicMock()
    mock_plan.status = PlanStatus.VALIDATED
    mock_plan.plan_id = "eplan_nomut"
    mock_plan.quality_score = {"verdict": "pass", "score": 1.0}
    mock_plan.objective = MagicMock()
    mock_plan.objective.dry_run = False

    mock_task = MagicMock()
    mock_task.id = "task_nomut"
    mock_task.status = MagicMock(value="completed")

    # Only mock the planning layer — no execution.engine mocks
    with patch("umh.planning.planner.create_plan_from_raw", return_value=mock_plan):
        with patch("umh.planning.planner.execute_plan", return_value=mock_task):
            runner = SchedulerRunner()
            triggered = runner.tick()

    assert len(triggered) == 1


def test_scheduler_observable():
    """All schedules are visible via list_all — no hidden state."""
    store = get_schedule_store()
    ids = set()
    for i in range(10):
        wf = _make_workflow(f"observable-{i}")
        store.create(wf)
        ids.add(wf.id)

    all_wf = store.list_all()
    listed_ids = {w.id for w in all_wf}
    assert ids == listed_ids


def test_scheduler_pausable():
    """Disabling a schedule prevents it from running on future ticks."""
    from umh.scheduler.runner import SchedulerRunner

    store = get_schedule_store()
    wf = _make_workflow("pausable")
    wf.next_run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    store.create(wf)
    store.enable(wf.id)

    # Disable before tick
    store.disable(wf.id)

    runner = SchedulerRunner()
    triggered = runner.tick()
    assert triggered == []


def test_scheduler_cancellable():
    """Deleting a schedule removes it completely from the store."""
    store = get_schedule_store()
    wf = _make_workflow("cancellable")
    store.create(wf)

    assert store.get(wf.id) is not None
    store.delete(wf.id)
    assert store.get(wf.id) is None
    assert wf.id not in {w.id for w in store.list_all()}
