"""UMH Agent Base — abstract agent framework for advisory agents.

All agents are READ-ONLY, ADVISORY, and STATELESS.
They NEVER call execute(), NEVER modify plans post-validation, NEVER mutate state.
Agents are pure functions that return structured data (AgentOutput).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from umh.core.clock import iso_now


class AgentRole(str, Enum):
    """Canonical agent roles in the multi-agent intelligence layer."""

    PLANNER = "planner"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"


@dataclass(frozen=True)
class AgentOutput:
    """Immutable structured output from an advisory agent run.

    Every agent returns one of these. The output dict is role-specific;
    the envelope fields (agent_role, agent_id, confidence, model_used,
    timestamp) are universal.
    """

    agent_role: str
    agent_id: str
    output: dict
    confidence: float = 1.0
    model_used: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        # frozen=True requires object.__setattr__ for defaults
        if not self.agent_id:
            object.__setattr__(
                self,
                "agent_id",
                f"{self.agent_role}_{uuid.uuid4().hex[:8]}",
            )
        if not self.timestamp:
            object.__setattr__(self, "timestamp", iso_now())

    def to_dict(self) -> dict:
        """Serialize to a plain dict for logging, event payloads, etc."""
        return {
            "agent_role": self.agent_role,
            "agent_id": self.agent_id,
            "output": self.output,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "timestamp": self.timestamp,
        }


class BaseAgent(ABC):
    """Abstract base for all UMH advisory agents.

    Subclasses implement ``role``, ``description``, and ``run``.
    ``run`` must be a pure function: no side effects, no state mutation.
    """

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        """The canonical role this agent fills."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description of what this agent does."""
        ...

    @abstractmethod
    def run(self, input_data: dict) -> AgentOutput:
        """Execute the agent's advisory logic and return structured output.

        Args:
            input_data: Role-specific input dict.

        Returns:
            AgentOutput with role-specific output payload.
        """
        ...
