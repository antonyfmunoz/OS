"""Adapter contracts — protocol definitions for execution surface bridges.

Adapters are PURE executors. They receive routed events and perform
side effects (Discord messages, Notion updates, workstation commands).
They never contain business logic or make decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class AdapterContext:
    """Immutable context passed to every adapter invocation.

    Carries the runtime snapshot and correlation metadata so adapters
    can trace their work back to the originating lifecycle session.
    """

    state_snapshot: dict[str, Any]
    runtime_session_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Adapter(Protocol):
    """Structural type for execution surface adapters.

    Any class implementing supports() and handle() satisfies this
    protocol — no inheritance required.
    """

    def supports(self, event_type: str) -> bool:
        """Return True if this adapter handles the given event type."""
        ...

    def handle(self, event: Any, context: AdapterContext) -> None:
        """Execute the side effect for the given event.

        Must not raise on transient failures — log and continue.
        Must not modify event or context.
        """
        ...
