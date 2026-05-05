"""
UMH Execution Interfaces — protocols for execution dispatch and observation.

Defines the contract between UMH execution types and platform-specific
execution backends.  EOS substrate, CLI runners, and future SaaS runtimes
all implement these protocols.

Pattern matches umh.goals.interfaces and umh.strategy.interfaces:
  - Protocol defines the contract
  - Null* provides a safe no-op default
  - Singleton management with lazy EOS adapter discovery
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from umh.execution.contract import ExecutionRequest, ExecutionResult, ExecutionStatus

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Execution Backend Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ExecutionBackend(Protocol):
    """Protocol for dispatching execution requests."""

    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...

    def can_handle(self, operation: str) -> bool: ...


class NullExecutionBackend:
    """No-op backend — rejects all requests."""

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.REJECTED,
            outputs={},
            error="No execution backend configured",
        )

    def can_handle(self, operation: str) -> bool:
        return False


# ---------------------------------------------------------------------------
# Execution Observer Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ExecutionObserver(Protocol):
    """Protocol for observing execution lifecycle events."""

    def on_request(self, request: ExecutionRequest) -> None: ...

    def on_result(self, result: ExecutionResult) -> None: ...


class NullExecutionObserver:
    """No-op observer — discards all events."""

    def on_request(self, request: ExecutionRequest) -> None:
        pass

    def on_result(self, result: ExecutionResult) -> None:
        pass


# ---------------------------------------------------------------------------
# Singleton management — same pattern as goals/strategy interfaces
# ---------------------------------------------------------------------------

_backend: ExecutionBackend | None = None
_observer: ExecutionObserver | None = None


def _default_backend() -> ExecutionBackend:
    from umh.adapters.bridge import discover_platform_adapter

    adapter = discover_platform_adapter(
        "umh.adapters.umh_execution", "get_execution_backend_adapter"
    )
    if adapter is not None:
        return adapter
    return NullExecutionBackend()


def get_execution_backend() -> ExecutionBackend:
    global _backend
    if _backend is None:
        _backend = _default_backend()
    return _backend


def set_execution_backend(backend: ExecutionBackend) -> None:
    global _backend
    _backend = backend


def reset_execution_backend() -> None:
    global _backend
    _backend = None


def _default_observer() -> ExecutionObserver:
    from umh.adapters.bridge import discover_platform_adapter

    adapter = discover_platform_adapter(
        "umh.adapters.umh_execution", "get_execution_observer_adapter"
    )
    if adapter is not None:
        return adapter
    return NullExecutionObserver()


def get_execution_observer() -> ExecutionObserver:
    global _observer
    if _observer is None:
        _observer = _default_observer()
    return _observer


def set_execution_observer(observer: ExecutionObserver) -> None:
    global _observer
    _observer = observer


def reset_execution_observer() -> None:
    global _observer
    _observer = None
