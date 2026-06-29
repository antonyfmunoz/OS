"""Organism protocol — canonical contracts for the agent society layer.

Consolidates RuntimeAdapter Protocol and agent society data types
(AgentStatus, CritiqueResult, Deliverable, AgentMessage, WorkerSpec,
LearningSignal) from their implementation modules.
"""

from __future__ import annotations

from substrate.organism.runtime_graph import RuntimeAdapter  # noqa: F401
from substrate.organism.protocols import (  # noqa: F401
    AgentStatus,
    CritiqueResult,
    Deliverable,
    AgentMessage,
    WorkerSpec,
    LearningSignal,
)

__all__ = [
    "RuntimeAdapter",
    "AgentStatus",
    "CritiqueResult",
    "Deliverable",
    "AgentMessage",
    "WorkerSpec",
    "LearningSignal",
]
