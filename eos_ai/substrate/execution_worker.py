"""
Execution worker — scheduler handler that bridges requests to adapters.

Subscribes to ``execution_requested`` (and ``execution_retried``) events.
When an event arrives it deserializes the request, finds the adapter,
runs the primitive with a timeout, and emits exactly one result event.

CRITICAL INVARIANT: The worker handler NEVER returns mutations.
mutations=[] always. Workers are the execution plane. They do work and
report results via events. The control plane (result handler) is the
only thing that writes state.

Usage:
    from eos_ai.substrate.execution_worker import ExecutionWorker

    worker = ExecutionWorker(store)
    worker.register_adapter(my_adapter)
    scheduler.subscribe(
        "execution_requested",
        worker.handle_execution_requested,
        name="execution_worker",
    )
    scheduler.subscribe(
        "execution_retried",
        worker.handle_execution_requested,
        name="execution_worker_retry",
    )
"""

from __future__ import annotations

import sys
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from eos_ai.substrate.event_scheduler import (
    ExecutionResult as SchedulerExecutionResult,
    SchedulerEvent,
)
from eos_ai.substrate.execution_adapter import ExecutionAdapter
from eos_ai.substrate.execution_contract import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from eos_ai.substrate.execution_events import (
    build_execution_completed_event,
    build_execution_failed_event,
    build_execution_rejected_event,
    build_execution_timed_out_event,
)
from eos_ai.substrate.runtime_state_store import RuntimeStateStore

_LOG_PREFIX = "[substrate.execution_worker]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ExecutionWorker
# ---------------------------------------------------------------------------


class ExecutionWorker:
    """Scheduler handler that bridges execution requests to adapters.

    INVARIANTS:
    - NEVER returns mutations (mutations list is always empty)
    - NEVER evaluates lifecycle guards
    - NEVER makes routing decisions
    - ALWAYS emits exactly one result event per request
    - ALWAYS includes adapter's node_id in result
    - ALWAYS checks state hash before/after for write enforcement
    """

    def __init__(self, store: RuntimeStateStore) -> None:
        self._adapters: dict[str, ExecutionAdapter] = {}  # node_id -> adapter
        self._store = store

    def register_adapter(self, adapter: ExecutionAdapter) -> None:
        """Register an adapter for a node."""
        self._adapters[adapter.node_id] = adapter
        _log(f"registered adapter: {adapter.adapter_id} for node {adapter.node_id}")

    def get_adapter(self, node_id: str) -> Optional[ExecutionAdapter]:
        """Get adapter for a node, or None."""
        return self._adapters.get(node_id)

    def handle_execution_requested(
        self, store: RuntimeStateStore, event: SchedulerEvent
    ) -> SchedulerExecutionResult:
        """Main scheduler handler. Signature matches HandlerFn type.

        Steps:
        1. Deserialize request from event payload
        2. Find adapter for target node
        3. Check adapter has required capability
        4. Snapshot state hash before execution
        5. Execute with timeout via threading
        6. Verify state hash unchanged after execution
        7. Emit exactly one result event

        Returns SchedulerExecutionResult with mutations=[] ALWAYS.
        """
        session_name = event.session_name
        run_id = event.run_id
        request_event_id = event.event_id

        # 1. Deserialize request
        try:
            request_dict = event.payload["request"]
            request = ExecutionRequest.from_dict(request_dict)
        except Exception as exc:
            _log(f"request deserialization failed: {exc}")
            # Build a minimal rejected result for the malformed request
            reject_result = ExecutionResult(
                execution_id=event.payload.get("request", {}).get(
                    "execution_id", "unknown"
                ),
                correlation_id=event.payload.get("request", {}).get(
                    "correlation_id", "unknown"
                ),
                causal_event_id=event.payload.get("request", {}).get(
                    "causal_event_id", request_event_id
                ),
                primitive_name=event.payload.get("request", {}).get(
                    "primitive_name", "unknown"
                ),
                status=ExecutionStatus.REJECTED,
                outputs={},
                error=f"deserialization_failed: {exc}",
                node_id="unknown",
            )
            reject_event = build_execution_rejected_event(
                result=reject_result,
                request_event_id=request_event_id,
                session_name=session_name,
                rejection_reason=f"deserialization_failed: {exc}",
                run_id=run_id,
            )
            return SchedulerExecutionResult(mutations=[], emitted_events=[reject_event])

        # 2. Find adapter
        adapter = self._adapters.get(request.target.node_id)
        if adapter is None:
            _log(f"no adapter for node: {request.target.node_id}")
            reject_result = ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.REJECTED,
                outputs={},
                error=f"no_adapter_for_node: {request.target.node_id}",
                node_id=request.target.node_id,
                idempotency_key=request.idempotency_key,
                retry_count=request.retry_count,
            )
            reject_event = build_execution_rejected_event(
                result=reject_result,
                request_event_id=request_event_id,
                session_name=session_name,
                rejection_reason=f"no_adapter_for_node: {request.target.node_id}",
                run_id=run_id,
            )
            return SchedulerExecutionResult(mutations=[], emitted_events=[reject_event])

        # 3. Check capability
        if request.primitive_name not in adapter.capabilities:
            _log(
                f"adapter {adapter.adapter_id} lacks capability: "
                f"{request.primitive_name}"
            )
            reject_result = ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.REJECTED,
                outputs={},
                error=(
                    f"capability_missing: {request.primitive_name} "
                    f"not in {sorted(adapter.capabilities)}"
                ),
                node_id=adapter.node_id,
                idempotency_key=request.idempotency_key,
                retry_count=request.retry_count,
            )
            reject_event = build_execution_rejected_event(
                result=reject_result,
                request_event_id=request_event_id,
                session_name=session_name,
                rejection_reason=(
                    f"capability_missing: {request.primitive_name} "
                    f"not in {sorted(adapter.capabilities)}"
                ),
                run_id=run_id,
            )
            return SchedulerExecutionResult(mutations=[], emitted_events=[reject_event])

        # 4. Snapshot state hash before execution
        hash_before = store.compute_state_hash()

        # 5. Execute with timeout via threading
        adapter_result: list[ExecutionResult | None] = [None]
        adapter_error: list[Exception | None] = [None]

        def _run_adapter() -> None:
            try:
                adapter_result[0] = adapter.execute(request)
            except Exception as exc:  # noqa: BLE001
                adapter_error[0] = exc

        thread = threading.Thread(target=_run_adapter, daemon=True)
        started_at = _iso_now()
        thread.start()
        thread.join(timeout=request.constraints.timeout_s)

        completed_at = _iso_now()

        # Check if thread is still alive (timeout)
        if thread.is_alive():
            _log(
                f"execution timed out after {request.constraints.timeout_s}s: "
                f"{request.execution_id}"
            )
            timeout_result = ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.TIMED_OUT,
                outputs={},
                error=f"timeout_after_{request.constraints.timeout_s}s",
                started_at=started_at,
                completed_at=completed_at,
                node_id=adapter.node_id,
                idempotency_key=request.idempotency_key,
                retry_count=request.retry_count,
            )
            timeout_event = build_execution_timed_out_event(
                result=timeout_result,
                request_event_id=request_event_id,
                session_name=session_name,
                run_id=run_id,
            )
            return SchedulerExecutionResult(
                mutations=[], emitted_events=[timeout_event]
            )

        # Check if adapter raised an exception
        if adapter_error[0] is not None:
            exc = adapter_error[0]
            _log(f"adapter raised: {type(exc).__name__}: {exc}")
            failed_result = ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=f"adapter_exception:{type(exc).__name__}: {exc}",
                started_at=started_at,
                completed_at=completed_at,
                node_id=adapter.node_id,
                idempotency_key=request.idempotency_key,
                retry_count=request.retry_count,
            )
            failed_event = build_execution_failed_event(
                result=failed_result,
                request_event_id=request_event_id,
                session_name=session_name,
                failure_reason=f"adapter_exception:{type(exc).__name__}: {exc}",
                run_id=run_id,
            )
            return SchedulerExecutionResult(mutations=[], emitted_events=[failed_event])

        # 6. Verify state hash unchanged
        result = adapter_result[0]
        assert result is not None  # thread completed without error → result set

        hash_after = store.compute_state_hash()
        if hash_after != hash_before:
            _log(
                f"STATE WRITE VIOLATION: hash changed during execution "
                f"({hash_before} -> {hash_after}) for {request.execution_id}"
            )
            violation_result = ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.FAILED,
                outputs={},
                error="state_write_violation",
                started_at=started_at,
                completed_at=completed_at,
                node_id=adapter.node_id,
                idempotency_key=request.idempotency_key,
                retry_count=request.retry_count,
            )
            violation_event = build_execution_failed_event(
                result=violation_result,
                request_event_id=request_event_id,
                session_name=session_name,
                failure_reason="state_write_violation",
                run_id=run_id,
            )
            return SchedulerExecutionResult(
                mutations=[], emitted_events=[violation_event]
            )

        # 7. Emit result event based on status
        if result.status == ExecutionStatus.SUCCEEDED:
            result_event = build_execution_completed_event(
                result=result,
                request_event_id=request_event_id,
                session_name=session_name,
                run_id=run_id,
            )
        elif result.status == ExecutionStatus.TIMED_OUT:
            result_event = build_execution_timed_out_event(
                result=result,
                request_event_id=request_event_id,
                session_name=session_name,
                run_id=run_id,
            )
        elif result.status == ExecutionStatus.REJECTED:
            result_event = build_execution_rejected_event(
                result=result,
                request_event_id=request_event_id,
                session_name=session_name,
                rejection_reason=result.error or "rejected_by_adapter",
                run_id=run_id,
            )
        else:
            # FAILED or any other status
            result_event = build_execution_failed_event(
                result=result,
                request_event_id=request_event_id,
                session_name=session_name,
                failure_reason=result.error or "unknown_failure",
                run_id=run_id,
            )

        return SchedulerExecutionResult(mutations=[], emitted_events=[result_event])


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = ["ExecutionWorker"]
