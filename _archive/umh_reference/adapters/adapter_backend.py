"""Phase 76 adapter-to-backend bridge.

Wraps any MVPAdapter into an ExecutionBackend so it can be registered
in the backend registry and dispatched by the canonical execution engine.

Translation:
  ExecutionRequest  →  AdapterRequest  →  adapter.execute()  →  AdapterResult  →  ExecutionResult

The bridge never decides — it translates.  Governance happens upstream.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from umh.adapters.mvp_contract import (
    AdapterRequest,
    AdapterResult,
    AdapterStatus,
    MVPAdapter,
)
from umh.core.clock import iso_now as _iso_now
from umh.core.clock import now_ms as _now_ms
from umh.execution.contract import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)

_log = logging.getLogger(__name__)

_STATUS_MAP: dict[AdapterStatus, ExecutionStatus] = {
    AdapterStatus.SUCCESS: ExecutionStatus.SUCCEEDED,
    AdapterStatus.FAILURE: ExecutionStatus.FAILED,
    AdapterStatus.DENIED: ExecutionStatus.REJECTED,
    AdapterStatus.VALIDATION_FAILED: ExecutionStatus.REJECTED,
    AdapterStatus.UNSUPPORTED: ExecutionStatus.REJECTED,
    AdapterStatus.TIMEOUT: ExecutionStatus.TIMED_OUT,
    AdapterStatus.SIMULATED: ExecutionStatus.SUCCEEDED,
}


def _to_adapter_request(request: ExecutionRequest) -> AdapterRequest:
    """Translate ExecutionRequest into AdapterRequest."""
    capability = request.inputs.get("capability", request.operation)
    return AdapterRequest(
        request_id=request.execution_id,
        capability=capability,
        action=request.operation,
        environment=request.inputs.get("environment", "local"),
        inputs=request.inputs,
        constraints={
            "timeout_s": request.constraints.timeout_s,
            "max_tokens": request.constraints.max_tokens,
        },
        permissions={
            "authority_class": request.context.authority_class,
        },
        metadata={
            "correlation_id": request.correlation_id,
            "issued_by": request.issued_by,
        },
        trace_id=request.correlation_id,
    )


def _to_execution_result(
    request: ExecutionRequest,
    adapter_result: AdapterResult,
    latency_ms: int,
) -> ExecutionResult:
    """Translate AdapterResult into ExecutionResult."""
    status = _STATUS_MAP.get(adapter_result.status, ExecutionStatus.FAILED)

    outputs = dict(adapter_result.output)
    if adapter_result.observations:
        outputs["_observations"] = adapter_result.observations
    if adapter_result.status == AdapterStatus.SIMULATED:
        outputs["_simulated"] = True

    return ExecutionResult(
        execution_id=request.execution_id,
        correlation_id=request.correlation_id,
        causal_event_id=request.causal_event_id,
        operation=request.operation,
        status=status,
        outputs=outputs,
        error=adapter_result.error,
        started_at=adapter_result.metadata.get("started_at"),
        completed_at=_iso_now(),
        node_id="adapter",
        latency_ms=latency_ms,
    )


class AdapterExecutionBackend:
    """Wraps one or more MVPAdapters into an ExecutionBackend.

    Holds a mapping of capability → adapter.  When execute() is called,
    it looks up the adapter for the requested capability, runs validate(),
    then execute(), and translates the result back.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, MVPAdapter] = {}
        self._all_capabilities: set[str] = set()

    def register_adapter(self, adapter: Any) -> None:
        """Register an adapter for all its supported capabilities."""
        for cap in adapter.supported_capabilities:
            self._adapters[cap] = adapter
            self._all_capabilities.add(cap)
        _log.info(
            "Registered adapter %s for capabilities: %s",
            adapter.name,
            sorted(adapter.supported_capabilities),
        )

    def can_handle(self, operation: str) -> bool:
        return operation in self._all_capabilities

    @property
    def registered_capabilities(self) -> frozenset[str]:
        return frozenset(self._all_capabilities)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Translate, validate, execute, translate back."""
        adapter_request = _to_adapter_request(request)
        capability = adapter_request.capability

        adapter = self._adapters.get(capability)
        if adapter is None:
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.REJECTED,
                outputs={"error": f"No adapter for capability: {capability}"},
                error=f"No adapter registered for capability: {capability}",
                latency_ms=0,
            )

        start_ms = _now_ms()

        validation_error = adapter.validate(adapter_request)
        if validation_error is not None:
            return _to_execution_result(request, validation_error, _now_ms() - start_ms)

        try:
            adapter_result = adapter.execute(adapter_request)
        except Exception as e:
            _log.error("Adapter %s.execute() raised: %s", adapter.name, e)
            error_result = AdapterResult(
                request_id=adapter_request.request_id,
                adapter_name=adapter.name,
                capability=capability,
                action=adapter_request.action,
                status=AdapterStatus.FAILURE,
                error=str(e),
            )
            return _to_execution_result(request, error_result, _now_ms() - start_ms)

        return _to_execution_result(request, adapter_result, _now_ms() - start_ms)
