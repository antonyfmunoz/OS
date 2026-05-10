"""Phase 76 MVP adapter contract — typed request/result for all adapters.

Every MVP adapter receives an AdapterRequest and returns an AdapterResult.
Adapters never make governance decisions, never write traces directly,
and never mutate memory/world/profile.  The execution wrapper handles
all of that.

This module defines the contract types only — no execution logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class AdapterStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    VALIDATION_FAILED = "validation_failed"
    UNSUPPORTED = "unsupported"
    TIMEOUT = "timeout"
    SIMULATED = "simulated"


@dataclass(frozen=True)
class AdapterRequest:
    """What the execution layer asks an adapter to do."""

    request_id: str
    capability: str
    action: str
    environment: str
    inputs: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    permissions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "capability": self.capability,
            "action": self.action,
            "environment": self.environment,
            "inputs": self.inputs,
            "constraints": self.constraints,
            "metadata": self.metadata,
            "trace_id": self.trace_id,
        }


@dataclass(frozen=True)
class AdapterResult:
    """What an adapter returns after execution."""

    request_id: str
    adapter_name: str
    capability: str
    action: str
    status: AdapterStatus
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "adapter_name": self.adapter_name,
            "capability": self.capability,
            "action": self.action,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "observations": self.observations,
        }


@runtime_checkable
class MVPAdapter(Protocol):
    """Protocol that all Phase 76 adapters must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def supported_capabilities(self) -> frozenset[str]: ...

    @property
    def supported_environments(self) -> frozenset[str]: ...

    def validate(self, request: AdapterRequest) -> AdapterResult | None:
        """Pre-flight check.  Return AdapterResult with failure status to reject,
        or None to proceed to execute()."""
        ...

    def execute(self, request: AdapterRequest) -> AdapterResult:
        """Execute the adapter action.  Must not raise."""
        ...
