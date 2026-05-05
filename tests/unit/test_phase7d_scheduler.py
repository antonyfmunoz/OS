"""Tests for Phase 7D: Scheduler Layer — core models, store, and runner.

Verifies:
- ScheduledWorkflow creation and defaults
- ScheduleType enum values
- SchedulePolicy defaults and serialization
- compute_next_run for interval, daily, weekly
- ScheduleStore CRUD operations
- SchedulerRunner tick logic and lifecycle
- Event emission on trigger
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from umh.scheduler.models import (
    SchedulePolicy,
    ScheduleType,
    ScheduledWorkflow,
    compute_next_run,
)
from umh.scheduler.store import get_schedule_store, reset_schedule_store
from umh.events.stream import get_event_stream, reset_event_stream


@pytest.fixture(autouse=True)
def clean_state():
    reset_schedule_store()
    reset_event_stream()
    yield
    reset_schedule_store()


# ── Workflow Model ────────────────────────────────────────────────


def test_create_workflow():
    """New workflow gets auto-generated id, created_at, and enabled=False."""
    wf = ScheduledWorkflow(
        name="daily check",
        objective="check system health",
        schedule_type=ScheduleType.DAILY,
        schedule_value="09:00",
    )
    assert wf.id.startswith("sched_")
    assert len(wf.id) > 6
    assert wf.created_at != ""
    assert wf.enabled is False


def test_workflow_default_disabled():
    """New workflows must default to enabled=False (safety invariant)."""
    wf = ScheduledWorkflow(
        name="test",
        objective="test",
        schedule_type=ScheduleType.INTERVAL,
        schedule_value="30",
    )
    assert wf.enabled is False


def test_workflow_to_dict():
    """to_dict() round-trips all fields correctly."""
    wf = ScheduledWorkflow(
        name="report",
        objective="generate report",
        schedule_type=ScheduleType.WEEKLY,
        schedule_value="mon 09:00",
    )
    d = wf.to_dict()
    assert d["name"] == "report"
    assert d["objective"] == "generate report"
    assert d["schedule_type"] == "weekly"
    assert d["schedule_value"] == "mon 09:00"
    assert d["enabled"] is False
    assert d["id"] == wf.id
    assert d["created_at"] == wf.created_at
    assert d["updated_at"] == wf.updated_at
    assert "policy" in d
    assert isinstance(d["policy"], dict)
    assert d["run_count"] == 0
    assert d["metadata"] == {}
    assert d["created_by"] == ""


def test_schedule_type_values():
    """All expected ScheduleType enum values exist."""
    assert ScheduleType.INTERVAL.value == "interval"
    assert ScheduleType.DAILY.value == "daily"
    assert ScheduleType.WEEKLY.value == "weekly"
    assert ScheduleType.CRON_LIKE.value == "cron_like"
    assert len(ScheduleType) == 4


# ── Policy ────────────────────────────────────────────────────────


def test_policy_defaults():
    """SchedulePolicy has correct defaults."""
    p = SchedulePolicy()
    assert p.require_approval_before_run is True
    assert p.allowed_capabilities == []
    assert p.max_runs_per_day == 24
    assert p.max_cost_usd == 0.0
    assert p.dry_run_only is False
    assert p.auto_execute_safe_tasks_only is True


def test_policy_to_dict():
    """Policy serialization includes all fields."""
    p = SchedulePolicy(max_runs_per_day=5, dry_run_only=True)
    d = p.to_dict()
    assert d["max_runs_per_day"] == 5
    assert d["dry_run_only"] is True
    assert d["require_approval_before_run"] is True
    assert d["allowed_capabilities"] == []
    assert d["max_cost_usd"] == 0.0
    assert d["auto_execute_safe_tasks_only"] is True


# ── compute_next_run ──────────────────────────────────────────────


def test_compute_next_run_interval():
    """Interval schedule adds N minutes to from_time."""
    base = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    result = compute_next_run(ScheduleType.INTERVAL, "30", from_time=base)
    expected = (base + timedelta(minutes=30)).isoformat()
    assert result == expected


def test_compute_next_run_daily():
    """Daily schedule computes next occurrence of HH:MM."""
    # If current time is before target, same day
    base = datetime(2026, 4, 27, 8, 0, 0, tzinfo=timezone.utc)
    result = compute_next_run(ScheduleType.DAILY, "09:00", from_time=base)
    parsed = datetime.fromisoformat(result)
    assert parsed.hour == 9
    assert parsed.minute == 0
    assert parsed.day == 27  # same day

    # If current time is after target, next day
    base_after = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    result_after = compute_next_run(ScheduleType.DAILY, "09:00", from_time=base_after)
    parsed_after = datetime.fromisoformat(result_after)
    assert parsed_after.day == 28  # next day


def test_compute_next_run_weekly():
    """Weekly schedule computes next occurrence of 'day HH:MM'."""
    # 2026-04-27 is a Monday
    base = datetime(2026, 4, 27, 8, 0, 0, tzinfo=timezone.utc)
    result = compute_next_run(ScheduleType.WEEKLY, "mon 09:00", from_time=base)
    parsed = datetime.fromisoformat(result)
    assert parsed.weekday() == 0  # Monday
    assert parsed.hour == 9
    assert parsed.minute == 0
    # Same day since 09:00 > 08:00
    assert parsed.day == 27

    # If we're past the target time, next week
    base_after = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    result_after = compute_next_run(ScheduleType.WEEKLY, "mon 09:00", from_time=base_after)
    parsed_after = datetime.fromisoformat(result_after)
    assert parsed_after.weekday() == 0  # Monday
    assert parsed_after.month == 5 and parsed_after.day == 4  # next Monday (May 4)


# ── Store CRUD ────────────────────────────────────────────────────


def _make_workflow(name: str = "test", **kwargs) -> ScheduledWorkflow:
    """Helper: create a workflow with sensible defaults."""
    defaults = {
        "name": name,
        "objective": f"objective for {name}",
        "schedule_type": ScheduleType.INTERVAL,
        "schedule_value": "30",
    }
    defaults.update(kwargs)
    return ScheduledWorkflow(**defaults)


def test_store_create_and_get():
    """Store.create() persists, Store.get() retrieves by id."""
    store = get_schedule_store()
    wf = _make_workflow("store-test")
    store.create(wf)

    retrieved = store.get(wf.id)
    assert retrieved is not None
    assert retrieved.id == wf.id
    assert retrieved.name == "store-test"


def test_store_list_all():
    """list_all() returns all stored workflows."""
    store = get_schedule_store()
    store.create(_make_workflow("a"))
    store.create(_make_workflow("b"))
    store.create(_make_workflow("c"))

    all_wf = store.list_all()
    assert len(all_wf) == 3
    names = {w.name for w in all_wf}
    assert names == {"a", "b", "c"}


def test_store_list_enabled():
    """list_enabled() returns only enabled workflows."""
    store = get_schedule_store()
    wf1 = _make_workflow("enabled-one")
    wf2 = _make_workflow("disabled-one")
    store.create(wf1)
    store.create(wf2)
    store.enable(wf1.id)

    enabled = store.list_enabled()
    assert len(enabled) == 1
    assert enabled[0].id == wf1.id


def test_store_enable():
    """enable() flips enabled flag to True."""
    store = get_schedule_store()
    wf = _make_workflow("to-enable")
    store.create(wf)
    assert wf.enabled is False

    result = store.enable(wf.id)
    assert result is not None
    assert result.enabled is True


def test_store_disable():
    """disable() flips enabled flag to False."""
    store = get_schedule_store()
    wf = _make_workflow("to-disable")
    store.create(wf)
    store.enable(wf.id)
    assert store.get(wf.id).enabled is True

    result = store.disable(wf.id)
    assert result is not None
    assert result.enabled is False


def test_store_delete():
    """delete() removes workflow; get() returns None after."""
    store = get_schedule_store()
    wf = _make_workflow("to-delete")
    store.create(wf)
    assert store.get(wf.id) is not None

    deleted = store.delete(wf.id)
    assert deleted is True
    assert store.get(wf.id) is None


def test_store_delete_nonexistent():
    """delete() returns False for non-existent id."""
    store = get_schedule_store()
    assert store.delete("sched_doesnotexist") is False


def test_store_update_run_status():
    """update_run_status() updates tracking fields."""
    store = get_schedule_store()
    wf = _make_workflow("run-track")
    store.create(wf)
    assert wf.run_count == 0

    store.update_run_status(wf.id, "completed", "2026-04-28T10:00:00+00:00")

    updated = store.get(wf.id)
    assert updated.run_count == 1
    assert updated.last_run_status == "completed"
    assert updated.last_run_at != ""
    assert updated.next_run_at == "2026-04-28T10:00:00+00:00"


# ── Runner ────────────────────────────────────────────────────────


def _mock_planning():
    """Return context managers that mock the planning pipeline."""
    from umh.planning.models import PlanStatus

    mock_plan = MagicMock()
    mock_plan.status = PlanStatus.VALIDATED
    mock_plan.plan_id = "eplan_test123"
    mock_plan.quality_score = {"verdict": "pass", "score": 1.0}
    mock_plan.objective = MagicMock()
    mock_plan.objective.dry_run = False

    mock_task = MagicMock()
    mock_task.id = "task_test123"
    mock_task.status = MagicMock(value="completed")

    mock_create = patch(
        "umh.planning.planner.create_plan_from_raw", return_value=mock_plan
    )
    mock_exec = patch(
        "umh.planning.planner.execute_plan", return_value=mock_task
    )
    return mock_create, mock_exec, mock_plan, mock_task


def test_runner_tick_no_schedules():
    """tick() with empty store returns empty list."""
    from umh.scheduler.runner import SchedulerRunner

    runner = SchedulerRunner()
    triggered = runner.tick()
    assert triggered == []


def test_runner_tick_disabled_schedule():
    """tick() skips disabled schedules."""
    from umh.scheduler.runner import SchedulerRunner

    store = get_schedule_store()
    wf = _make_workflow("disabled-tick")
    store.create(wf)
    assert wf.enabled is False

    runner = SchedulerRunner()
    triggered = runner.tick()
    assert triggered == []


def test_runner_tick_due_schedule():
    """tick() triggers enabled schedule with past next_run_at."""
    from umh.scheduler.runner import SchedulerRunner

    store = get_schedule_store()
    wf = _make_workflow("due-tick")
    wf.next_run_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    store.create(wf)
    store.enable(wf.id)

    mock_create, mock_exec, _, _ = _mock_planning()
    runner = SchedulerRunner()

    with mock_create, mock_exec:
        triggered = runner.tick()

    assert len(triggered) == 1
    assert triggered[0] == wf.id


def test_runner_tick_not_due():
    """tick() does not trigger schedule with future next_run_at."""
    from umh.scheduler.runner import SchedulerRunner

    store = get_schedule_store()
    wf = _make_workflow("future-tick")
    wf.next_run_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    store.create(wf)
    store.enable(wf.id)

    runner = SchedulerRunner()
    triggered = runner.tick()
    assert triggered == []


def test_runner_tick_emits_event():
    """tick() emits a schedule.triggered event."""
    from umh.scheduler.runner import SchedulerRunner

    store = get_schedule_store()
    wf = _make_workflow("event-tick")
    wf.next_run_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    store.create(wf)
    store.enable(wf.id)

    mock_create, mock_exec, _, _ = _mock_planning()
    runner = SchedulerRunner()

    stream = get_event_stream()
    events_before = stream.count()

    with mock_create, mock_exec:
        runner.tick()

    events_after = stream.list_events(limit=100)
    schedule_events = [
        e for e in events_after if e.type.startswith("schedule.")
    ]
    assert len(schedule_events) >= 1
    triggered_events = [e for e in schedule_events if e.type == "schedule.triggered"]
    assert len(triggered_events) >= 1


def test_runner_run_now():
    """run_now() triggers a schedule immediately regardless of next_run_at."""
    from umh.scheduler.runner import SchedulerRunner

    store = get_schedule_store()
    wf = _make_workflow("run-now-test")
    wf.next_run_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    store.create(wf)
    store.enable(wf.id)

    mock_create, mock_exec, _, mock_task = _mock_planning()
    runner = SchedulerRunner()

    with mock_create, mock_exec:
        result = runner.run_now(wf.id)

    assert result is not None
    assert "error" not in result or result.get("error") is None


def test_runner_run_now_nonexistent():
    """run_now() returns error for missing schedule id."""
    from umh.scheduler.runner import SchedulerRunner

    runner = SchedulerRunner()
    result = runner.run_now("sched_doesnotexist")
    assert result is not None
    assert "error" in result


def test_runner_start_stop():
    """start()/stop() lifecycle works without error."""
    from umh.scheduler.runner import SchedulerRunner

    runner = SchedulerRunner()
    assert runner.is_running() is False

    runner.start()
    assert runner.is_running() is True

    runner.stop()
    assert runner.is_running() is False
