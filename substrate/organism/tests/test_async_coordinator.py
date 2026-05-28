"""Tests for async coordinator execution."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.async_coordinator import (
    AsyncCoordinator,
    AsyncObjective,
    AsyncObjectiveStatus,
)
from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.coordinator import OrganismCoordinator
from substrate.organism.runtime_graph import (
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)


def _make_coordinator() -> tuple[AsyncCoordinator, EventSpine]:
    spine = EventSpine()
    graph = RuntimeGraph()
    graph.register(
        "test-rt", RuntimeClass.LOCAL_MODEL,
        frozenset({RuntimeCapability.REASON}),
    )
    coordinator = OrganismCoordinator(graph)
    return AsyncCoordinator(coordinator=coordinator, spine=spine), spine


def test_submit_objective():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Build X", "description of X")
    assert obj_id != ""

    obj = ac.get(obj_id)
    assert obj is not None
    assert obj.title == "Build X"
    assert obj.status == AsyncObjectiveStatus.SUBMITTED


def test_advance_processes_submitted():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Task", "desc")
    advanced = ac.advance()

    assert len(advanced) >= 1
    obj = ac.get(obj_id)
    assert obj is not None
    assert obj.status in {
        AsyncObjectiveStatus.DECOMPOSED,
        AsyncObjectiveStatus.EXECUTING,
        AsyncObjectiveStatus.COMPLETED,
    }


def test_cancel_objective():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Cancelme", "desc")
    ac.cancel(obj_id)

    obj = ac.get(obj_id)
    assert obj is not None
    assert obj.status == AsyncObjectiveStatus.CANCELLED


def test_progress_tracking():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Track me", "desc")
    ac.advance()

    progress = ac.progress(obj_id)
    assert progress is not None
    assert "completion_rate" in progress
    assert "status" in progress


def test_emits_lifecycle_events():
    ac, spine = _make_coordinator()
    obj_id = ac.submit("Evented", "desc")
    ac.advance()

    events = spine.recent(limit=50)
    submit_events = [e for e in events if e.event_type == "async_objective_submitted"]
    assert len(submit_events) == 1
    assert submit_events[0].correlation_id == obj_id


def test_list_active():
    ac, _ = _make_coordinator()
    ac.submit("A", "desc")
    ac.submit("B", "desc")

    active = ac.list_active()
    assert len(active) == 2


def test_completed_not_in_active():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Quick", "desc")
    ac.advance()

    obj = ac.get(obj_id)
    if obj and obj.status == AsyncObjectiveStatus.COMPLETED:
        active = ac.list_active()
        assert all(a.objective_id != obj_id for a in active)


def test_dag_state():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("DAG task", "complex work", work_units=[
        {"title": "Step 1", "description": "first"},
        {"title": "Step 2", "description": "second", "blocked_by": [0]},
    ])

    dag = ac.dag_state(obj_id)
    assert dag is not None
    assert "work_units" in dag
