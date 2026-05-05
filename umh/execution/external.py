"""UMH External Capability Interface — standard adapter contract for external tools.

External capabilities (browser automation, computer use, etc.) route through
the same execution pipeline as internal capabilities. This module defines the
adapter interface and the registry that maps capability types to adapters.

Every external adapter:
  - Receives an ExecutionRequest and EnvironmentSpec
  - Returns an ExecutionResult
  - Cannot bypass enforcement or the security guard
  - Is observed and scored like any internal execution
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from umh.execution.contract import ExecutionRequest, ExecutionResult, ExecutionStatus
from umh.execution.environment import EnvironmentSpec

_log = logging.getLogger(__name__)


class ExternalCapabilityAdapter(ABC):
    """Interface for external capability adapters.

    Subclasses implement execute() for a specific capability type
    (browser_action, computer_use, etc.). The adapter name is used
    in ExecutionEvent.adapter for observability.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Unique name for this adapter (used in logging and events)."""
        ...

    @property
    @abstractmethod
    def capability_type(self) -> str:
        """The capability type this adapter handles."""
        ...

    @abstractmethod
    def execute(self, request: ExecutionRequest, environment: EnvironmentSpec) -> ExecutionResult:
        """Execute the request in the given environment.

        Must return ExecutionResult — never raise.
        """
        ...

    def _not_implemented(self, request: ExecutionRequest, reason: str = "") -> ExecutionResult:
        """Standard NOT_IMPLEMENTED response for stub adapters."""
        msg = reason or f"Not implemented: {self.adapter_name}/{request.operation}"
        _log.info("[%s] not_implemented: %s", self.adapter_name, msg)
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.REJECTED,
            outputs={"not_implemented": True, "reason": msg, "adapter": self.adapter_name},
            error=msg,
        )


_ADAPTER_REGISTRY: dict[str, ExternalCapabilityAdapter] = {}


def register_adapter(adapter: ExternalCapabilityAdapter) -> None:
    """Register an external capability adapter."""
    _ADAPTER_REGISTRY[adapter.capability_type] = adapter
    _log.info(
        "[ExternalCapability] registered adapter '%s' for capability '%s'",
        adapter.adapter_name,
        adapter.capability_type,
    )


def get_adapter(capability_type: str) -> ExternalCapabilityAdapter | None:
    """Look up an adapter by capability type."""
    return _ADAPTER_REGISTRY.get(capability_type)


def list_adapters() -> dict[str, str]:
    """Return mapping of capability_type → adapter_name."""
    return {k: v.adapter_name for k, v in _ADAPTER_REGISTRY.items()}
