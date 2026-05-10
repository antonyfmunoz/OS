"""Runtime context — immutable execution metadata for a single lifecycle run.

Pure container. No logic. Passed through the lifecycle so every layer
can trace its work back to the originating request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable context for a single lifecycle invocation.

    Fields:
        runtime_session_id:   owning session identifier
        transport:            ingress channel (discord, voice, api, etc.)
        timestamp:            ISO-8601 UTC timestamp of the request
        correlation_id:       links all events/mutations in this run
        requested_profile_id: profile to activate (None = use default)
        trigger:              what initiated this run
    """

    runtime_session_id: str
    transport: str
    timestamp: str
    correlation_id: str
    requested_profile_id: str | None = None
    trigger: str = "manual"
    intent_text: str = ""
    previous_session: dict | None = None
    objective: str | None = None
    progress: dict | None = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(
                self,
                "timestamp",
                datetime.now(timezone.utc).isoformat(),
            )
