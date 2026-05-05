"""World protocols — contracts for world model interaction."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WorldModelReader(Protocol):
    """Read-only access to the world model for context building."""

    def get_context_for_prompt(self, query: str) -> str: ...


@runtime_checkable
class WorldModelWriter(Protocol):
    """Mutation access to the world model after execution."""

    def update_from_interaction(
        self, input_text: str, response: str, outcome: str = "neutral"
    ) -> None: ...
