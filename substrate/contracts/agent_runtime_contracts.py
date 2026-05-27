"""Agent runtime protocol — substrate-owned interface for LLM execution.

Concrete implementation lives in adapters/models/agent_runtime.py.
Substrate code imports this protocol, never the concrete class directly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from substrate.contracts.agent_types import AgentResult, TaskType
from substrate.state.context.context import EntrepreneurOSContext


@runtime_checkable
class AgentRuntimeProtocol(Protocol):
    """Interface that any agent runtime must satisfy."""

    def run(
        self,
        task_type: TaskType,
        prompt: str,
        venture_id: str | None = None,
        skill_name: str | None = None,
        max_tokens: int = 1024,
        agent: str = "default",
        system_extra: str | None = None,
        ctx: EntrepreneurOSContext | None = None,
        **kwargs,
    ) -> AgentResult: ...


def get_agent_runtime(ctx: EntrepreneurOSContext | None = None) -> AgentRuntimeProtocol:
    """Factory — returns the concrete AgentRuntime from adapters.

    This is the single boundary crossing point. Substrate code calls this
    factory instead of importing adapters directly.
    """
    from adapters.models.agent_runtime import AgentRuntime

    return AgentRuntime(ctx)
