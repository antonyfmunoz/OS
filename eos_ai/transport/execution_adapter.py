"""
Execution adapters — stateless wrappers around existing execution code.

Each adapter translates between the ExecutionRequest/ExecutionResult contract
and an underlying executor (local_executor, node_transport, etc.).

Adapters are stateless workers. They receive a request, run the primitive,
and return a result. They never make decisions about WHAT to run.

MUST NOT: Write to state store, emit events, make routing decisions,
          call other primitives.
MUST: Respect request.constraints.timeout_s,
      return REJECTED if primitive not in capabilities,
      return FAILED (not raise) on any error,
      include node_id in result.
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass
from typing import Any, Protocol

from eos_ai.transport.control_commands import ControlCommand
from eos_ai.transport.execution_contract import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)


def _log(msg: str) -> None:
    print(f"[substrate.execution_adapter] {msg}", file=sys.stderr)


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class ExecutionAdapter(Protocol):
    """Contract for execution plane adapters.

    Adapters are stateless workers. They receive a request, run the primitive,
    and return a result. They never make decisions about WHAT to run.

    MUST NOT: Write to state store, emit events, make routing decisions,
              call other primitives.
    MUST: Respect request.constraints.timeout_s,
          return REJECTED if primitive not in capabilities,
          return FAILED (not raise) on any error,
          include node_id in result.
    """

    @property
    def adapter_id(self) -> str: ...

    @property
    def node_id(self) -> str: ...

    @property
    def capabilities(self) -> frozenset[str]: ...

    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...

    def health(self) -> AdapterHealth: ...


# ---------------------------------------------------------------------------
# Health dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdapterHealth:
    """Point-in-time health reading from an adapter."""

    node_id: str
    status: str  # "healthy" | "degraded" | "unhealthy"
    detail: str = ""
    capabilities_count: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    request: ExecutionRequest,
    *,
    status: ExecutionStatus,
    outputs: dict[str, Any] | None = None,
    error: str | None = None,
    node_id: str = "",
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ExecutionResult:
    """Build an ExecutionResult from a request plus outcome fields."""
    return ExecutionResult(
        execution_id=request.execution_id,
        correlation_id=request.correlation_id,
        causal_event_id=request.causal_event_id,
        primitive_name=request.primitive_name,
        status=status,
        outputs=outputs or {},
        error=error,
        started_at=started_at,
        completed_at=completed_at,
        node_id=node_id,
        idempotency_key=request.idempotency_key,
        retry_count=request.retry_count,
    )


# ---------------------------------------------------------------------------
# LocalRuntimeAdapter
# ---------------------------------------------------------------------------


class LocalRuntimeAdapter:
    """Wraps local_executor.execute_command() behind the ExecutionAdapter protocol.

    Translates ExecutionRequest -> ControlCommand, calls the executor, and
    translates the result dict -> ExecutionResult. Stateless — no references
    to state stores, event logs, or other adapters.
    """

    def __init__(self) -> None:
        self._adapter_id = "local_runtime"
        self._node_id = "vps-primary"
        self._capabilities: frozenset[str] = frozenset(
            {"run_shell", "write_file", "run_python"}
        )

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def capabilities(self) -> frozenset[str]:
        return self._capabilities

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a request via local_executor. Never raises."""
        started_at = _iso_now()
        try:
            # Reject unknown primitives
            if request.primitive_name not in self._capabilities:
                return _make_result(
                    request,
                    status=ExecutionStatus.REJECTED,
                    error=f"primitive '{request.primitive_name}' not in capabilities",
                    node_id=self._node_id,
                    started_at=started_at,
                    completed_at=_iso_now(),
                )

            # Translate ExecutionRequest -> ControlCommand
            cmd = ControlCommand(
                action=request.primitive_name,
                payload=dict(request.inputs),
                issued_by=request.issued_by,
                node_id=self._node_id,
                target="local",
            )

            # Call the executor
            from eos_ai.substrate import local_executor

            result_dict = local_executor.execute_command(cmd)

            # Translate result dict -> ExecutionResult
            completed_at = _iso_now()
            ok = result_dict.get("ok", False)

            if ok:
                return _make_result(
                    request,
                    status=ExecutionStatus.SUCCEEDED,
                    outputs=result_dict,
                    node_id=self._node_id,
                    started_at=started_at,
                    completed_at=completed_at,
                )

            reason = result_dict.get("reason", "unknown_error")
            if reason == "timeout":
                return _make_result(
                    request,
                    status=ExecutionStatus.TIMED_OUT,
                    outputs=result_dict,
                    error=reason,
                    node_id=self._node_id,
                    started_at=started_at,
                    completed_at=completed_at,
                )

            return _make_result(
                request,
                status=ExecutionStatus.FAILED,
                outputs=result_dict,
                error=reason,
                node_id=self._node_id,
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as exc:  # noqa: BLE001
            _log(f"local execute error: {exc}")
            return _make_result(
                request,
                status=ExecutionStatus.FAILED,
                error=f"adapter_exception:{type(exc).__name__}: {exc}",
                node_id=self._node_id,
                started_at=started_at,
                completed_at=_iso_now(),
            )

    def health(self) -> AdapterHealth:
        """Local executor is always available when the process is running."""
        return AdapterHealth(
            node_id=self._node_id,
            status="healthy",
            detail="local executor in-process",
            capabilities_count=len(self._capabilities),
        )


# ---------------------------------------------------------------------------
# WorkstationAdapter
# ---------------------------------------------------------------------------


class WorkstationAdapter:
    """Wraps node_transport.send_task_via_http() behind the ExecutionAdapter protocol.

    Translates ExecutionRequest -> action dict for the HTTP endpoint, calls
    send_task_via_http, and translates the response -> ExecutionResult.
    Stateless — no references to state stores, event logs, or other adapters.
    """

    DEFAULT_CAPABILITIES: frozenset[str] = frozenset(
        {
            "speak_text",
            "play_sound",
            "open_url",
            "launch_app",
            "open_scene",
            "focus_app",
        }
    )

    def __init__(
        self,
        *,
        node_id: str = "antony-workstation",
        capabilities: frozenset[str] | None = None,
        host: str = "127.0.0.1",
        port: int = 7600,
    ) -> None:
        self._adapter_id = "workstation_runtime"
        self._node_id = node_id
        self._capabilities = (
            capabilities if capabilities is not None else self.DEFAULT_CAPABILITIES
        )
        self._host = host
        self._port = port

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def capabilities(self) -> frozenset[str]:
        return self._capabilities

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a request via HTTP to the workstation daemon. Never raises."""
        started_at = _iso_now()
        try:
            # Reject unknown primitives
            if request.primitive_name not in self._capabilities:
                return _make_result(
                    request,
                    status=ExecutionStatus.REJECTED,
                    error=f"primitive '{request.primitive_name}' not in capabilities",
                    node_id=self._node_id,
                    started_at=started_at,
                    completed_at=_iso_now(),
                )

            # Translate ExecutionRequest -> action dict for HTTP endpoint
            action_dict: dict[str, Any] = {
                "kind": request.primitive_name,
                "payload": dict(request.inputs),
                "execution_id": request.execution_id,
                "issued_by": request.issued_by,
            }

            # Call the async transport synchronously
            from eos_ai.transport.node_transport import send_task_via_http

            timeout_s = float(request.constraints.timeout_s)
            response = asyncio.run(
                send_task_via_http(
                    action_dict,
                    host=self._host,
                    port=self._port,
                    timeout_s=timeout_s,
                )
            )

            completed_at = _iso_now()

            # None means transport failure
            if response is None:
                return _make_result(
                    request,
                    status=ExecutionStatus.FAILED,
                    error="http_transport_failure: no response from workstation",
                    node_id=self._node_id,
                    started_at=started_at,
                    completed_at=completed_at,
                )

            # Parse response status
            resp_status = response.get("status", "error")
            if resp_status in ("ok", "succeeded"):
                return _make_result(
                    request,
                    status=ExecutionStatus.SUCCEEDED,
                    outputs=response,
                    node_id=self._node_id,
                    started_at=started_at,
                    completed_at=completed_at,
                )

            return _make_result(
                request,
                status=ExecutionStatus.FAILED,
                outputs=response,
                error=response.get("detail", f"workstation_error:{resp_status}"),
                node_id=self._node_id,
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as exc:  # noqa: BLE001
            _log(f"workstation execute error: {exc}")
            return _make_result(
                request,
                status=ExecutionStatus.FAILED,
                error=f"adapter_exception:{type(exc).__name__}: {exc}",
                node_id=self._node_id,
                started_at=started_at,
                completed_at=_iso_now(),
            )

    def health(self) -> AdapterHealth:
        """Check workstation health via HTTP. Never raises."""
        try:
            from eos_ai.transport.node_transport import check_http_health

            is_healthy = asyncio.run(
                check_http_health(host=self._host, port=self._port)
            )
            if is_healthy:
                return AdapterHealth(
                    node_id=self._node_id,
                    status="healthy",
                    detail=f"http transport reachable at {self._host}:{self._port}",
                    capabilities_count=len(self._capabilities),
                )
            return AdapterHealth(
                node_id=self._node_id,
                status="unhealthy",
                detail=f"http transport unreachable at {self._host}:{self._port}",
                capabilities_count=len(self._capabilities),
            )
        except Exception as exc:  # noqa: BLE001
            return AdapterHealth(
                node_id=self._node_id,
                status="unhealthy",
                detail=f"health_check_error: {exc}",
                capabilities_count=len(self._capabilities),
            )


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "ExecutionAdapter",
    "AdapterHealth",
    "LocalRuntimeAdapter",
    "WorkstationAdapter",
]
