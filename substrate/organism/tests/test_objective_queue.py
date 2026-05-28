"""Tests for the continuous objective queue."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.objective_queue import (
    ObjectiveQueueStatus,
    ObjectiveRequest,
    ObjectiveQueue,
)


def _make_queue() -> tuple[ObjectiveQueue, EventSpine]:
    spine = EventSpine()
    return ObjectiveQueue(spine=spine), spine


def test_enqueue_and_peek():
    q, _ = _make_queue()
    req_id = q.enqueue("Build feature X", "Implement the thing", priority=3)
    assert req_id != ""

    peeked = q.peek()
    assert peeked is not None
    assert peeked.title == "Build feature X"
    assert peeked.priority == 3
    assert peeked.status == ObjectiveQueueStatus.QUEUED


def test_priority_ordering():
    q, _ = _make_queue()
    q.enqueue("Low", "low pri", priority=10)
    q.enqueue("High", "high pri", priority=1)
    q.enqueue("Mid", "mid pri", priority=5)

    peeked = q.peek()
    assert peeked is not None
    assert peeked.title == "High"


def test_dequeue():
    q, _ = _make_queue()
    q.enqueue("Task A", "desc", priority=1)
    q.enqueue("Task B", "desc", priority=2)

    item = q.dequeue()
    assert item is not None
    assert item.title == "Task A"
    assert item.status == ObjectiveQueueStatus.EXECUTING

    next_item = q.peek()
    assert next_item is not None
    assert next_item.title == "Task B"


def test_complete():
    q, _ = _make_queue()
    req_id = q.enqueue("Task", "desc")
    q.dequeue()
    q.complete(req_id, result={"output": "done"})

    item = q.get(req_id)
    assert item is not None
    assert item.status == ObjectiveQueueStatus.COMPLETED


def test_fail_and_retry():
    q, _ = _make_queue()
    req_id = q.enqueue("Flaky task", "desc", max_retries=3)
    q.dequeue()
    q.fail(req_id, error="timeout")

    item = q.get(req_id)
    assert item is not None
    assert item.status == ObjectiveQueueStatus.QUEUED
    assert item.attempt_count == 1


def test_fail_exhausts_retries():
    q, _ = _make_queue()
    req_id = q.enqueue("Bad task", "desc", max_retries=1)

    q.dequeue()
    q.fail(req_id, error="err1")
    q.dequeue()
    q.fail(req_id, error="err2")

    item = q.get(req_id)
    assert item is not None
    assert item.status == ObjectiveQueueStatus.FAILED


def test_dependency_ordering():
    q, _ = _make_queue()
    id_a = q.enqueue("A", "first")
    id_b = q.enqueue("B", "depends on A", depends_on=[id_a])

    peeked = q.peek()
    assert peeked is not None
    assert peeked.title == "A"

    q.dequeue()
    q.complete(id_a)

    peeked = q.peek()
    assert peeked is not None
    assert peeked.title == "B"


def test_blocked_item_not_dequeued():
    q, _ = _make_queue()
    id_a = q.enqueue("A", "first")
    q.enqueue("B", "depends on A", depends_on=[id_a])

    item = q.dequeue()
    assert item is not None
    assert item.title == "A"

    next_item = q.dequeue()
    assert next_item is None


def test_emits_events():
    q, spine = _make_queue()
    q.enqueue("Task", "desc")
    q.dequeue()

    events = spine.recent(limit=50)
    enqueue_events = [e for e in events if e.event_type == "objective_enqueued"]
    dequeue_events = [e for e in events if e.event_type == "objective_dequeued"]
    assert len(enqueue_events) == 1
    assert len(dequeue_events) == 1


def test_cancel():
    q, _ = _make_queue()
    req_id = q.enqueue("Cancellable", "desc")
    q.cancel(req_id)

    item = q.get(req_id)
    assert item is not None
    assert item.status == ObjectiveQueueStatus.CANCELLED


def test_queue_depth():
    q, _ = _make_queue()
    q.enqueue("A", "desc")
    q.enqueue("B", "desc")
    assert q.depth() == 2

    q.dequeue()
    assert q.depth() == 1


def test_list_by_status():
    q, _ = _make_queue()
    q.enqueue("A", "desc")
    q.enqueue("B", "desc")
    q.dequeue()

    queued = q.list_by_status(ObjectiveQueueStatus.QUEUED)
    executing = q.list_by_status(ObjectiveQueueStatus.EXECUTING)
    assert len(queued) == 1
    assert len(executing) == 1
