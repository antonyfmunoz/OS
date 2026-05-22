"""tests for agent base runtime — critique loop, deliverable production."""

import pytest
from substrate.organism.agent_runtime import AgentRuntime
from substrate.organism.protocols import AgentMessage, AgentStatus, CritiqueResult, Deliverable
from substrate.organism.store import OrganismStore


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


@pytest.fixture
def runtime(store):
    return AgentRuntime(
        agent_id="test-agent",
        agent_name="Test Agent",
        soul_doc="You are a test agent.",
        store=store,
        max_critique_iterations=2,
    )


def test_runtime_starts_idle(runtime):
    assert runtime.status == AgentStatus.IDLE


def test_runtime_processes_task(runtime):
    msg = AgentMessage(
        sender="advisor",
        recipient="test-agent",
        intent="delegate_task",
        payload={
            "task": "echo hello",
            "adapter": "shell",
            "operation": "query",
            "params": {"command": "echo hello"},
        },
    )
    deliverable = runtime.handle_task(msg)
    assert deliverable is not None
    assert deliverable.agent_id == "test-agent"
    assert deliverable.self_critique.score >= 1


def test_deliverable_persisted_to_store(runtime, store):
    msg = AgentMessage(
        sender="advisor",
        recipient="test-agent",
        intent="delegate_task",
        payload={
            "task": "echo test",
            "adapter": "shell",
            "operation": "query",
            "params": {"command": "echo test"},
        },
    )
    runtime.handle_task(msg)
    deliverables = store.list_deliverables(agent_id="test-agent")
    assert len(deliverables) == 1


def test_status_transitions(runtime):
    msg = AgentMessage(
        sender="advisor",
        recipient="test-agent",
        intent="delegate_task",
        payload={
            "task": "echo status",
            "adapter": "shell",
            "operation": "query",
            "params": {"command": "echo status"},
        },
    )
    assert runtime.status == AgentStatus.IDLE
    runtime.handle_task(msg)
    assert runtime.status == AgentStatus.IDLE
