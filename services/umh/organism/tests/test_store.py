"""tests for organism JSONL store."""

import pytest
from services.umh.organism.protocols import (
    AgentMessage,
    AgentStatus,
    CritiqueResult,
    Deliverable,
    LearningSignal,
)
from services.umh.organism.store import OrganismStore


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


def test_save_and_list_deliverables(store):
    d = Deliverable(
        agent_id="researcher-001",
        task_id="task-1",
        content="Found issues",
        self_critique=CritiqueResult(score=8, reasoning="good"),
    )
    store.save_deliverable(d)
    results = store.list_deliverables(agent_id="researcher-001")
    assert len(results) == 1
    assert results[0]["agent_id"] == "researcher-001"


def test_save_and_list_messages(store):
    msg = AgentMessage(
        sender="advisor",
        recipient="researcher-001",
        intent="delegate_task",
        payload={"task": "audit"},
    )
    store.save_message(msg)
    results = store.list_messages(recipient="researcher-001")
    assert len(results) == 1


def test_save_agent_state(store):
    store.save_agent_state(
        "researcher-001",
        {
            "status": "idle",
            "tasks_completed": 5,
            "last_task": "audit cognitive_loop.py",
        },
    )
    state = store.load_agent_state("researcher-001")
    assert state is not None
    assert state["tasks_completed"] == 5


def test_load_missing_agent_state(store):
    state = store.load_agent_state("nonexistent")
    assert state is None


def test_save_learning_signal(store):
    sig = LearningSignal(
        agent_id="researcher-001",
        deliverable_id="del-1",
        pattern_observed="state mutation outside canonical path",
        confidence=0.9,
    )
    store.save_learning_signal(sig)
    results = store.list_learning_signals()
    assert len(results) == 1
