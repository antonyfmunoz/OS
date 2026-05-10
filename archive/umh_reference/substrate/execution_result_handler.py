"""
Control-plane handler that processes execution results.

Subscribes to execution_completed, execution_failed, execution_timed_out,
and execution_rejected events. Validates, deduplicates, writes outputs to
state, and emits lifecycle follow-up events.

This is the ONLY path for execution results to affect runtime state.

Usage:
    from umh.substrate.execution_result_handler import ExecutionResultHandler

    handler = ExecutionResultHandler(
        primitive_emission_map={"extract_response": ["response_extracted"]},
    )
    scheduler.subscribe("execution_completed", handler.handle_result)
    scheduler.subscribe("execution_failed", handler.handle_result)
    scheduler.subscribe("execution_timed_out", handler.handle_result)
    scheduler.subscribe("execution_rejected", handler.handle_result)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any

from umh.substrate.execution_contract import (
    ExecutionClass,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from umh.substrate.execution_events import build_execution_retried_event
from umh.substrate.event_scheduler import (
    ExecutionResult as SchedulerExecutionResult,
    SchedulerEvent,
)
from umh.substrate.runtime_state_store import RuntimeStateStore

_LOG_PREFIX = "[substrate.execution_result_handler]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionResultHandler:
    """Control-plane handler that processes execution results.

    Subscribes to execution result events. Validates, deduplicates,
    writes outputs to state, emits lifecycle follow-up events.

    Responsibilities:
    1. Validate result envelope (execution_id in in_flight)
    2. Idempotency dedup (completed_executions set)
    3. On SUCCEEDED: write outputs to state, emit lifecycle events per primitive contract
    4. On FAILED: retry if class allows, else emit failure
    5. On TIMED_OUT: treat as FAILED
    6. On REJECTED: route to fallback if available, else permanent failure
    """

    def __init__(
        self,
        primitive_emission_map: dict[str, list[str]] | None = None,
        primitive_conditional_map: dict[str, dict[str, str]] | None = None,
    ) -> None:
        # primitive_name -> list of event_types to emit unconditionally on success
        self._emissions = primitive_emission_map or {}
        # primitive_name -> {condition_string: event_type} to emit conditionally
        self._conditional_emissions = primitive_conditional_map or {}

    # ── Public API ─────────────────────────────────────────────────────

    def handle_result(
        self, store: RuntimeStateStore, event: SchedulerEvent
    ) -> SchedulerExecutionResult:
        """Unified handler for all execution result event types.

        Signature matches HandlerFn: (store, event) -> SchedulerExecutionResult.
        Routes by ExecutionStatus to the appropriate internal handler.
        """
        result_data = event.payload.get("result")
        if result_data is None:
            _log("event payload missing 'result' key, dropping")
            return SchedulerExecutionResult(
                metadata={"skipped": True, "reason": "missing_result_payload"}
            )

        result = ExecutionResult.from_dict(result_data)
        execution_id = result.execution_id

        # --- Idempotency check ---
        completed = store.get("completed_executions", [])
        if execution_id in completed:
            _log(f"duplicate execution_id={execution_id}, dropping")
            return SchedulerExecutionResult(
                metadata={"skipped": True, "reason": "duplicate_execution_id"}
            )

        # --- In-flight validation ---
        in_flight_key = f"in_flight_executions.{execution_id}"
        in_flight = store.get(in_flight_key)
        if in_flight is None:
            _log(f"no in-flight record for execution_id={execution_id}, dropping")
            return SchedulerExecutionResult(
                metadata={"skipped": True, "reason": "no_in_flight_record"}
            )

        # --- Route by status ---
        status = result.status
        if status == ExecutionStatus.SUCCEEDED:
            return self._handle_succeeded(store, event, result, in_flight)
        elif status == ExecutionStatus.FAILED:
            return self._handle_failed(store, event, result, in_flight)
        elif status == ExecutionStatus.TIMED_OUT:
            return self._handle_timed_out(store, event, result, in_flight)
        elif status == ExecutionStatus.REJECTED:
            return self._handle_rejected(store, event, result, in_flight)
        else:
            _log(f"unknown execution status: {status}")
            return SchedulerExecutionResult(
                metadata={"skipped": True, "reason": f"unknown_status_{status}"}
            )

    # ── SUCCEEDED ──────────────────────────────────────────────────────

    def _handle_succeeded(
        self,
        store: RuntimeStateStore,
        event: SchedulerEvent,
        result: ExecutionResult,
        in_flight: dict[str, Any],
    ) -> SchedulerExecutionResult:
        """Write outputs to state, mark complete, emit lifecycle events."""
        mutations: list[dict[str, Any]] = []
        emitted_events: list[SchedulerEvent] = []

        # Write each output key/value to state
        for key, value in result.outputs.items():
            mutations.append({"op": "SET", "key": key, "value": value})

        # Mark execution as completed in the dedup set
        mutations.append(
            {
                "op": "APPEND_UNIQUE",
                "key": "completed_executions",
                "value": result.execution_id,
            }
        )

        # Update in-flight record to completed
        in_flight_key = f"in_flight_executions.{result.execution_id}"
        mutations.append(
            {
                "op": "SET",
                "key": in_flight_key,
                "value": {
                    **in_flight,
                    "status": "completed",
                    "completed_at": result.completed_at or _utcnow(),
                    "node_id": result.node_id,
                },
            }
        )

        # Emit unconditional lifecycle events
        primitive_name = result.primitive_name
        session_name = event.session_name
        run_id = event.run_id

        for event_type in self._emissions.get(primitive_name, []):
            emitted_events.append(
                SchedulerEvent(
                    event_type=event_type,
                    session_name=session_name,
                    source="result_handler",
                    run_id=run_id,
                    payload={
                        "execution_id": result.execution_id,
                        "primitive_name": primitive_name,
                        "outputs": result.outputs,
                    },
                    metadata={
                        "triggered_by": "execution_succeeded",
                        "source_execution_id": result.execution_id,
                    },
                )
            )

        # Emit conditional lifecycle events
        for condition_str, event_type in self._conditional_emissions.get(
            primitive_name, {}
        ).items():
            if self._evaluate_condition(condition_str, result.outputs, store):
                emitted_events.append(
                    SchedulerEvent(
                        event_type=event_type,
                        session_name=session_name,
                        source="result_handler",
                        run_id=run_id,
                        payload={
                            "execution_id": result.execution_id,
                            "primitive_name": primitive_name,
                            "outputs": result.outputs,
                            "condition": condition_str,
                        },
                        metadata={
                            "triggered_by": "conditional_emission",
                            "condition": condition_str,
                            "source_execution_id": result.execution_id,
                        },
                    )
                )

        _log(
            f"SUCCEEDED execution_id={result.execution_id} "
            f"mutations={len(mutations)} events={len(emitted_events)}"
        )

        return SchedulerExecutionResult(
            mutations=mutations,
            emitted_events=emitted_events,
            metadata={"status": "succeeded", "execution_id": result.execution_id},
        )

    # ── FAILED ─────────────────────────────────────────────────────────

    def _handle_failed(
        self,
        store: RuntimeStateStore,
        event: SchedulerEvent,
        result: ExecutionResult,
        in_flight: dict[str, Any],
    ) -> SchedulerExecutionResult:
        """Retry if class allows and retries remain, else permanent failure."""
        mutations: list[dict[str, Any]] = []
        emitted_events: list[SchedulerEvent] = []

        execution_class_str = in_flight.get("execution_class", "pure")
        try:
            execution_class = ExecutionClass(execution_class_str)
        except ValueError:
            execution_class = ExecutionClass.PURE

        max_retries = in_flight.get("max_retries", 0)
        retry_count = in_flight.get("retry_count", 0)

        # Side effects never retry. Also stop if retries exhausted.
        if execution_class == ExecutionClass.SIDE_EFFECT or retry_count >= max_retries:
            return self._permanent_failure(result, in_flight)

        # Build retry
        return self._build_retry(event, result, in_flight, retry_count)

    # ── TIMED_OUT ──────────────────────────────────────────────────────

    def _handle_timed_out(
        self,
        store: RuntimeStateStore,
        event: SchedulerEvent,
        result: ExecutionResult,
        in_flight: dict[str, Any],
    ) -> SchedulerExecutionResult:
        """Treat timeout as failure — same retry logic."""
        return self._handle_failed(store, event, result, in_flight)

    # ── REJECTED ───────────────────────────────────────────────────────

    def _handle_rejected(
        self,
        store: RuntimeStateStore,
        event: SchedulerEvent,
        result: ExecutionResult,
        in_flight: dict[str, Any],
    ) -> SchedulerExecutionResult:
        """Route to fallback if available, else permanent failure."""
        fallback_node_id = in_flight.get("fallback_node_id")
        fallback_transport = in_flight.get("fallback_transport")

        if fallback_node_id:
            return self._build_fallback_retry(
                event, result, in_flight, fallback_node_id, fallback_transport
            )

        # No fallback — delegate to _handle_failed for permanent failure path
        return self._handle_failed(store, event, result, in_flight)

    # ── Retry / failure helpers ────────────────────────────────────────

    def _permanent_failure(
        self,
        result: ExecutionResult,
        in_flight: dict[str, Any],
    ) -> SchedulerExecutionResult:
        """Mark execution as permanently failed."""
        mutations: list[dict[str, Any]] = []

        in_flight_key = f"in_flight_executions.{result.execution_id}"
        mutations.append(
            {
                "op": "SET",
                "key": in_flight_key,
                "value": {
                    **in_flight,
                    "status": "failed",
                    "completed_at": result.completed_at or _utcnow(),
                    "error": result.error,
                },
            }
        )

        mutations.append(
            {
                "op": "APPEND_UNIQUE",
                "key": "completed_executions",
                "value": result.execution_id,
            }
        )

        _log(
            f"PERMANENT FAILURE execution_id={result.execution_id} error={result.error}"
        )

        return SchedulerExecutionResult(
            mutations=mutations,
            metadata={
                "status": "permanent_failure",
                "execution_id": result.execution_id,
                "error": result.error,
            },
        )

    def _build_retry(
        self,
        event: SchedulerEvent,
        result: ExecutionResult,
        in_flight: dict[str, Any],
        retry_count: int,
    ) -> SchedulerExecutionResult:
        """Build a retry request from the original in-flight record."""
        mutations: list[dict[str, Any]] = []
        emitted_events: list[SchedulerEvent] = []

        original_request_data = in_flight.get("original_request", {})
        new_retry_count = retry_count + 1

        # Rebuild request with incremented retry_count
        original_request_data["retry_count"] = new_retry_count
        new_request = ExecutionRequest.from_dict(original_request_data)

        # Update in-flight record to retrying
        in_flight_key = f"in_flight_executions.{result.execution_id}"
        mutations.append(
            {
                "op": "SET",
                "key": in_flight_key,
                "value": {
                    **in_flight,
                    "status": "retrying",
                    "retry_count": new_retry_count,
                },
            }
        )

        # Emit retry event
        retry_event = build_execution_retried_event(
            request=new_request,
            original_execution_id=result.execution_id,
            session_name=event.session_name,
            run_id=event.run_id,
        )
        emitted_events.append(retry_event)

        _log(
            f"RETRYING execution_id={result.execution_id} retry_count={new_retry_count}"
        )

        return SchedulerExecutionResult(
            mutations=mutations,
            emitted_events=emitted_events,
            metadata={
                "status": "retrying",
                "execution_id": result.execution_id,
                "retry_count": new_retry_count,
            },
        )

    def _build_fallback_retry(
        self,
        event: SchedulerEvent,
        result: ExecutionResult,
        in_flight: dict[str, Any],
        fallback_node_id: str,
        fallback_transport: str | None,
    ) -> SchedulerExecutionResult:
        """Build a retry targeting the fallback node."""
        mutations: list[dict[str, Any]] = []
        emitted_events: list[SchedulerEvent] = []

        original_request_data = in_flight.get("original_request", {})
        retry_count = in_flight.get("retry_count", 0) + 1

        # Retarget to fallback node
        original_request_data["retry_count"] = retry_count
        target_data = original_request_data.get("target", {})
        target_data["node_id"] = fallback_node_id
        if fallback_transport:
            target_data["transport"] = fallback_transport
        # Clear fallback so we don't loop
        target_data["fallback_node_id"] = None
        target_data["fallback_transport"] = None
        original_request_data["target"] = target_data

        new_request = ExecutionRequest.from_dict(original_request_data)

        # Update in-flight to retrying with fallback info
        in_flight_key = f"in_flight_executions.{result.execution_id}"
        mutations.append(
            {
                "op": "SET",
                "key": in_flight_key,
                "value": {
                    **in_flight,
                    "status": "retrying",
                    "retry_count": retry_count,
                    "fallback_used": True,
                },
            }
        )

        retry_event = build_execution_retried_event(
            request=new_request,
            original_execution_id=result.execution_id,
            session_name=event.session_name,
            run_id=event.run_id,
        )
        emitted_events.append(retry_event)

        _log(
            f"FALLBACK REROUTE execution_id={result.execution_id} "
            f"fallback_node={fallback_node_id}"
        )

        return SchedulerExecutionResult(
            mutations=mutations,
            emitted_events=emitted_events,
            metadata={
                "status": "fallback_reroute",
                "execution_id": result.execution_id,
                "fallback_node_id": fallback_node_id,
            },
        )

    # ── Condition evaluation ───────────────────────────────────────────

    @staticmethod
    def _evaluate_condition(
        condition: str,
        outputs: dict[str, Any],
        store: RuntimeStateStore,
    ) -> bool:
        """Evaluate a simple string condition against outputs and store.

        Supports:
            "key==value"  — equality check
            "key!=value"  — inequality check

        Looks up key in outputs first, then store.
        Compares string representations.
        """
        if "!=" in condition:
            parts = condition.split("!=", 1)
            if len(parts) != 2:
                return False
            key, expected = parts[0].strip(), parts[1].strip()
            actual = outputs.get(key)
            if actual is None:
                actual = store.get(key)
            return str(actual) != expected

        if "==" in condition:
            parts = condition.split("==", 1)
            if len(parts) != 2:
                return False
            key, expected = parts[0].strip(), parts[1].strip()
            actual = outputs.get(key)
            if actual is None:
                actual = store.get(key)
            return str(actual) == expected

        # Unsupported condition format
        _log(f"unsupported condition format: {condition}")
        return False
