"""tests for organism protocols — deliverable, agent message, worker spec."""

import pytest
from substrate.organism.protocols import (
    Deliverable,
    AgentMessage,
    LearningSignal,
    WorkerSpec,
    AgentStatus,
    CritiqueResult,
)


def test_deliverable_creation():
    d = Deliverable(
        agent_id="researcher-001",
        task_id="task-abc",
        content="Found 3 state mutations outside canonical paths in cognitive_loop.py",
        self_critique=CritiqueResult(score=8, reasoning="thorough analysis, covered all methods"),
    )
    assert d.agent_id == "researcher-001"
    assert d.self_critique.score == 8
    assert d.self_critique.passed is True


def test_critique_result_threshold():
    low = CritiqueResult(score=4, reasoning="incomplete")
    assert low.passed is False
    high = CritiqueResult(score=7, reasoning="adequate")
    assert high.passed is True


def test_agent_message_creation():
    msg = AgentMessage(
        sender="advisor",
        recipient="researcher-001",
        intent="delegate_task",
        payload={"task": "audit cognitive_loop.py", "tools": ["read_file", "grep"]},
    )
    assert msg.sender == "advisor"
    assert msg.intent == "delegate_task"
    assert msg.conversation_id is not None


def test_worker_spec_creation():
    spec = WorkerSpec(
        parent_agent_id="researcher-001",
        task="grep for state mutations in cognitive_loop.py",
        environment_id="vps-prod",
        tools=["read_file", "grep", "git_log"],
        model_tier="sonnet",
        risk_class="READ_ONLY",
        timeout_s=60.0,
    )
    assert spec.environment_id == "vps-prod"
    assert spec.model_tier == "sonnet"
    assert "grep" in spec.tools


def test_learning_signal_creation():
    sig = LearningSignal(
        agent_id="researcher-001",
        deliverable_id="del-xyz",
        pattern_observed="cognitive_loop uses raw dict mutations instead of typed setters",
        confidence=0.85,
    )
    assert sig.confidence == 0.85
