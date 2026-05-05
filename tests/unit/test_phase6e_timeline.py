"""Tests for Phase 6E Agent 5: Task Timeline Observability.

Covers:
1. TestTimelineBuilder — empty, executed, paused, cancelled tasks
2. TestTimelineSummary — each event type produces readable summary
3. TestTimelineDedup — duplicate events are deduplicated
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6e")
os.environ["UMH_TASK_BACKEND"] = "memory"

from umh.events.stream import Event, get_event_stream, publish, reset_event_stream
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    enqueue_task,
    execute_task,
    get_task,
    reset_tasks,
)
from umh.orchestrator.task_store import InMemoryTaskBackend, reset_task_store
from umh.orchestrator.timeline import (
    TimelineEntry,
    _summarize_event,
    build_task_timeline,
)


def _reset():
    """Reset all stores and event stream between tests."""
    reset_event_stream()
    reset_tasks()
    reset_task_store(backend=InMemoryTaskBackend())


# ── 1. TestTimelineBuilder ────────────────────────────────────────


class TestTimelineBuilder:
    def setup_method(self):
        _reset()

    def test_nonexistent_task_returns_empty(self):
        """Timeline for a task that doesn't exist returns empty list."""
        result = build_task_timeline("task_doesnotexist")
        assert result == []

    def test_enqueued_task_returns_minimal_timeline(self):
        """An enqueued-only task should have at least created + enqueued entries."""
        task = Task(
            steps=[TaskStep(operation="classify_intent")],
            issued_by="test-actor",
        )
        enqueue_task(task)

        timeline = build_task_timeline(task.id)
        assert len(timeline) >= 2

        types = [e.event_type for e in timeline]
        assert "task.created" in types
        assert "task.enqueued" in types

    def test_executed_task_has_ordered_events(self):
        """A fully executed task produces timeline in chronological order."""
        task = Task(
            steps=[
                TaskStep(operation="noop", inputs_template={"x": "1"}),
                TaskStep(operation="noop", inputs_template={"y": "2"}),
            ],
            issued_by="test-actor",
        )
        execute_task(task)

        timeline = build_task_timeline(task.id)
        assert len(timeline) >= 3  # created + started + step events + completed

        # Verify chronological order
        timestamps = [e.timestamp for e in timeline]
        assert timestamps == sorted(timestamps)

        types = [e.event_type for e in timeline]
        assert "task.created" in types
        assert "task.started" in types
        assert "task.completed" in types

    def test_cancelled_task_shows_cancellation(self):
        """A cancelled task's timeline includes the cancellation entry."""
        from umh.orchestrator.task import cancel_task

        task = Task(
            steps=[TaskStep(operation="noop")],
            issued_by="test-actor",
        )
        enqueue_task(task)
        cancel_task(task.id)

        timeline = build_task_timeline(task.id)
        types = [e.event_type for e in timeline]
        assert "task.cancelled" in types

    def test_timeline_entries_have_correct_structure(self):
        """Each entry must have timestamp, event_type, summary, details."""
        task = Task(
            steps=[TaskStep(operation="noop")],
            issued_by="test-actor",
        )
        enqueue_task(task)

        timeline = build_task_timeline(task.id)
        assert len(timeline) > 0

        for entry in timeline:
            assert isinstance(entry, TimelineEntry)
            assert isinstance(entry.timestamp, str)
            assert len(entry.timestamp) > 0
            assert isinstance(entry.event_type, str)
            assert len(entry.event_type) > 0
            assert isinstance(entry.summary, str)
            assert len(entry.summary) > 0
            assert isinstance(entry.details, dict)

    def test_to_dict_roundtrip(self):
        """TimelineEntry.to_dict() produces all required keys."""
        task = Task(
            steps=[TaskStep(operation="noop")],
            issued_by="test-actor",
        )
        enqueue_task(task)

        timeline = build_task_timeline(task.id)
        for entry in timeline:
            d = entry.to_dict()
            assert "timestamp" in d
            assert "event_type" in d
            assert "summary" in d
            assert "details" in d
            assert d["timestamp"] == entry.timestamp
            assert d["event_type"] == entry.event_type

    def test_synthesized_created_entry_when_no_event(self):
        """Task.created entry is synthesized even if no task.created event exists."""
        # Manually save a task without emitting events
        from umh.orchestrator.task import _save_task

        task = Task(
            steps=[TaskStep(operation="noop")],
            issued_by="test-actor",
        )
        _save_task(task)

        timeline = build_task_timeline(task.id)
        types = [e.event_type for e in timeline]
        assert "task.created" in types

        created_entry = [e for e in timeline if e.event_type == "task.created"][0]
        assert created_entry.timestamp == task.created_at
        assert created_entry.details["task_id"] == task.id

    def test_failed_task_includes_completion(self):
        """A failed task's timeline includes task.completed with failed status."""
        from umh.orchestrator.task import _save_task

        # Manually construct a failed task (execution engine may succeed on
        # arbitrary ops, so we set state directly to test the synthesized entry)
        task = Task(
            steps=[TaskStep(operation="will_fail")],
            issued_by="test-actor",
        )
        task.status = TaskStatus.FAILED
        task.error = "Step 0 (will_fail) failed: test"
        _save_task(task)

        timeline = build_task_timeline(task.id)
        types = [e.event_type for e in timeline]
        assert "task.completed" in types

        completed = [e for e in timeline if e.event_type == "task.completed"][0]
        assert "failed" in completed.summary.lower()
        assert completed.details["status"] == "failed"


# ── 2. TestTimelineSummary ────────────────────────────────────────


class TestTimelineSummary:
    def _make_event(self, event_type: str, payload: dict | None = None) -> Event:
        return Event(
            id="evt_test",
            type=event_type,
            timestamp="2026-04-27T00:00:00+00:00",
            payload=payload or {},
        )

    def test_enqueued_summary(self):
        e = self._make_event("task.enqueued")
        assert _summarize_event(e) == "Task enqueued for background execution"

    def test_started_summary(self):
        e = self._make_event("task.started")
        assert _summarize_event(e) == "Task execution started"

    def test_step_started_summary(self):
        e = self._make_event("task.step.started", {"step_index": 2, "operation": "classify_intent"})
        assert _summarize_event(e) == "Step 2 started: classify_intent"

    def test_step_completed_summary(self):
        e = self._make_event("task.step.completed", {"step_index": 0, "status": "completed"})
        assert _summarize_event(e) == "Step 0 completed"

    def test_paused_summary(self):
        e = self._make_event("task.paused", {"reason": "needs human review"})
        assert _summarize_event(e) == "Task paused: needs human review"

    def test_paused_summary_default_reason(self):
        e = self._make_event("task.paused", {})
        assert _summarize_event(e) == "Task paused: awaiting approval"

    def test_resumed_summary(self):
        e = self._make_event("task.resumed")
        assert _summarize_event(e) == "Task resumed after approval"

    def test_completed_summary(self):
        e = self._make_event("task.completed", {"status": "completed"})
        assert _summarize_event(e) == "Task completed"

    def test_cancelled_summary(self):
        e = self._make_event("task.cancelled")
        assert _summarize_event(e) == "Task cancelled by operator"

    def test_retried_summary(self):
        e = self._make_event("task.retried", {"new_task_id": "task_abc123"})
        assert _summarize_event(e) == "Task retry requested → task_abc123"

    def test_unknown_event_type_returns_type(self):
        e = self._make_event("custom.something")
        assert _summarize_event(e) == "custom.something"


# ── 3. TestTimelineDedup ──────────────────────────────────────────


class TestTimelineDedup:
    def setup_method(self):
        _reset()

    def test_duplicate_events_deduplicated(self):
        """Events with same type and timestamp are deduplicated."""
        from umh.orchestrator.task import _save_task

        task = Task(
            steps=[TaskStep(operation="noop")],
            issued_by="test-actor",
        )
        _save_task(task)

        # Publish duplicate events manually
        ts = "2026-04-27T12:00:00+00:00"
        stream = get_event_stream()
        for _ in range(3):
            stream.publish(
                Event(
                    id=f"evt_dup_{_}",
                    type="task.started",
                    timestamp=ts,
                    payload={"task_id": task.id},
                )
            )

        timeline = build_task_timeline(task.id)
        started_entries = [e for e in timeline if e.event_type == "task.started"]
        assert len(started_entries) == 1

    def test_different_timestamps_not_deduplicated(self):
        """Events with same type but different timestamps are kept."""
        from umh.orchestrator.task import _save_task

        task = Task(
            steps=[TaskStep(operation="noop")],
            issued_by="test-actor",
        )
        _save_task(task)

        stream = get_event_stream()
        stream.publish(
            Event(
                id="evt_a",
                type="task.step.completed",
                timestamp="2026-04-27T12:00:00+00:00",
                payload={"task_id": task.id, "step_index": 0, "status": "completed"},
            )
        )
        stream.publish(
            Event(
                id="evt_b",
                type="task.step.completed",
                timestamp="2026-04-27T12:01:00+00:00",
                payload={"task_id": task.id, "step_index": 1, "status": "completed"},
            )
        )

        timeline = build_task_timeline(task.id)
        step_completed = [e for e in timeline if e.event_type == "task.step.completed"]
        assert len(step_completed) == 2

    def test_synthesized_not_duplicated_with_real(self):
        """If a real event exists, the synthesized version is not added."""
        task = Task(
            steps=[TaskStep(operation="noop")],
            issued_by="test-actor",
        )
        enqueue_task(task)

        # enqueue_task emits task.enqueued, but no task.created event.
        # The builder synthesizes task.created from task state.
        timeline = build_task_timeline(task.id)
        created = [e for e in timeline if e.event_type == "task.created"]
        # Should have exactly one synthesized created entry
        assert len(created) == 1
