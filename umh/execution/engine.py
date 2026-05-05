"""
UMH Execution Engine — single canonical execution entry point.

Every execution in the system flows through ``execute()``.  It delegates
to the configured ``ExecutionBackend`` and notifies the configured
``ExecutionObserver`` before and after.

Two entry points, one engine:
  - ``execute(request)``           — full ExecutionRequest with all metadata
  - ``lightweight_execute(...)``   — builds request internally for quick tasks

Both route through the same backend + observer pipeline.

Usage:
    from umh.execution.engine import execute, lightweight_execute
    from umh.execution.contract import (
        ExecutionRequest, ExecutionClass, ExecutionConstraints,
        ExecutionTarget, ExecutionContext,
    )

    # Full path
    request = ExecutionRequest(...)
    result = execute(request)

    # Lightweight path (same engine, less ceremony)
    result = lightweight_execute("classify_intent", "Is this a greeting?")

The engine itself has zero platform dependencies.  Platform-specific
behavior is injected via ``set_execution_backend()`` and
``set_execution_observer()`` from ``umh.execution.interfaces``.
"""

from __future__ import annotations

import logging
import uuid
from enum import Enum

from umh.core.clock import iso_now as _iso_now
from umh.core.clock import now_ms as _now_ms

from umh.execution.contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget,
)
from umh.execution.interfaces import (
    get_execution_backend,
    get_execution_observer,
)

_log = logging.getLogger(__name__)


class LightweightTaskType(str, Enum):
    """Canonical lightweight task types for utility LLM calls."""

    CLASSIFY_INTENT = "classify_intent"
    EXTRACT_ENTITIES = "extract_entities"
    SUMMARIZE = "summarize"
    SHORT_RESPONSE = "short_response"
    VALIDATION = "validation"


def execute(request: ExecutionRequest) -> ExecutionResult:
    """Execute a request through the configured backend.

    1. Notify observer of incoming request
    2. Delegate to backend
    3. Notify observer of result
    4. Return result

    Never raises — returns a FAILED ExecutionResult on any error.
    """
    observer = get_execution_observer()
    backend = get_execution_backend()

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "execution.started",
        payload={
            "operation": request.operation,
            "execution_class": request.execution_class.value,
        },
        actor_id=request.issued_by,
        execution_id=request.execution_id,
    )

    try:
        observer.on_request(request)
    except Exception as e:
        _log.debug("Observer.on_request failed (non-fatal): %s", e)

    # Approval-aware pre-guard check
    approved_execution = False
    approval_id = request.inputs.get("approval_id")
    if approval_id and request.execution_class not in (
        ExecutionClass.PURE,
        ExecutionClass.LLM_CALL,
    ):
        from umh.execution.approval import get_approval_store
        from umh.execution.environment import _classify_capability

        store = get_approval_store()
        capability_type = _classify_capability(request)
        valid, reason = store.validate_for_execution(
            approval_id, request.operation, capability_type
        )
        if valid:
            approved_execution = True
            _log.info(
                "Execution APPROVED via approval_id=%s op=%s",
                approval_id,
                request.operation,
            )
        else:
            _log.warning(
                "Execution DENIED: invalid approval: %s op=%s",
                reason,
                request.operation,
            )
            result = ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.REJECTED,
                outputs={
                    "approval_invalid": True,
                    "approval_id": approval_id,
                    "reason": reason,
                },
                error=f"Invalid approval: {reason}",
                started_at=_iso_now(),
                completed_at=_iso_now(),
                latency_ms=0,
            )
            try:
                observer.on_result(result)
            except Exception:
                pass
            _publish_event(
                "execution.completed",
                payload={
                    "operation": result.operation,
                    "status": result.status.value,
                    "latency_ms": 0,
                },
                actor_id=request.issued_by,
                execution_id=result.execution_id,
            )
            return result

    # Security guard for non-LLM execution
    if request.execution_class not in (ExecutionClass.PURE, ExecutionClass.LLM_CALL):
        from umh.security.execution_guard import check_execution, GuardVerdict

        guard_result = check_execution(
            request.operation, request.inputs, approved_execution=approved_execution
        )
        if guard_result.verdict == GuardVerdict.REQUIRES_APPROVAL:
            from umh.execution.approval import get_approval_store
            from umh.execution.environment import _classify_capability

            store = get_approval_store()
            inputs_summary = ", ".join(f"{k}={v}" for k, v in list(request.inputs.items())[:5])
            approval = store.create_approval(
                execution_id=request.execution_id,
                operation=request.operation,
                capability_type=_classify_capability(request),
                risk_level="high",
                inputs_summary=inputs_summary or "(none)",
            )
            try:
                from umh.orchestrator.engine import get_orchestrator

                get_orchestrator().store_pending_request(request.execution_id, request.to_dict())
            except Exception:
                pass
            _log.warning(
                "Execution REQUIRES_APPROVAL: op=%s approval_id=%s",
                request.operation,
                approval.id,
            )
            result = ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.REJECTED,
                outputs={
                    "requires_approval": True,
                    "approval_id": approval.id,
                    "reason": guard_result.reason,
                },
                error=f"Requires approval: {guard_result.reason}",
                started_at=_iso_now(),
                completed_at=_iso_now(),
                latency_ms=0,
            )
            try:
                observer.on_result(result)
            except Exception:
                pass
            _publish_event(
                "execution.completed",
                payload={
                    "operation": result.operation,
                    "status": result.status.value,
                    "latency_ms": 0,
                    "requires_approval": True,
                    "approval_id": approval.id,
                },
                actor_id=request.issued_by,
                execution_id=result.execution_id,
            )
            return result

        if guard_result.verdict != GuardVerdict.ALLOW:
            _log.warning(
                "Execution DENIED by guard: op=%s reason=%s",
                request.operation,
                guard_result.reason,
            )
            result = ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.REJECTED,
                outputs={"guard_denied": True, "reason": guard_result.reason},
                error=f"Security guard denied: {guard_result.reason}",
                started_at=_iso_now(),
                completed_at=_iso_now(),
                latency_ms=0,
            )
            try:
                observer.on_result(result)
            except Exception:
                pass
            _publish_event(
                "execution.completed",
                payload={
                    "operation": result.operation,
                    "status": result.status.value,
                    "latency_ms": 0,
                },
                actor_id=request.issued_by,
                execution_id=result.execution_id,
            )
            return result

    # Thread approved_execution flag into context metadata for the adapter
    if approved_execution:
        from dataclasses import replace as _replace

        new_metadata = {
            **request.context.metadata,
            "approved_execution": True,
            "approval_id": approval_id,
        }
        new_context = _replace(request.context, metadata=new_metadata)
        request = _replace(request, context=new_context)

    start_ms = _now_ms()
    try:
        result = backend.execute(request)
    except Exception as e:
        _log.error("Backend.execute failed: %s", e)
        result = ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.FAILED,
            outputs={},
            error=str(e),
            started_at=_iso_now(),
            completed_at=_iso_now(),
            latency_ms=_now_ms() - start_ms,
        )

    # Consume approval after successful execution (single-use)
    if approved_execution and approval_id and result.status == ExecutionStatus.SUCCEEDED:
        from umh.execution.approval import get_approval_store

        get_approval_store().consume(approval_id)

    try:
        observer.on_result(result)
    except Exception as e:
        _log.debug("Observer.on_result failed (non-fatal): %s", e)

    _publish_event(
        "execution.completed",
        payload={
            "operation": result.operation,
            "status": result.status.value,
            "latency_ms": result.latency_ms,
        },
        actor_id=request.issued_by,
        execution_id=result.execution_id,
    )

    return result


def dispatch_prompt(
    capability_name: str,
    operation: str,
    prompt: str,
    system_prompt: str,
    constraints: dict,
) -> tuple[str, bool, str | None]:
    """Execute a prompt through the appropriate adapter.

    This is the only path from the run loop to external adapters.
    Routes through the adapter registry — never calls adapters directly.

    Returns (response, success, error_or_none).
    """
    from umh.adapters.base import get_adapter

    try:
        if capability_name == "local_python":
            return (f"[local_python] Processed: {prompt[:100]}", True, None)

        llm = get_adapter("llm")
        response = llm.generate(prompt, system=system_prompt)
        return (response, True, None)
    except Exception as e:
        return (f"Execution failed: {e}", False, str(e))


def lightweight_execute(
    operation: str,
    prompt: str,
    *,
    system: str | None = None,
    task_type: LightweightTaskType | str = LightweightTaskType.SHORT_RESPONSE,
    max_tokens: int = 1024,
) -> ExecutionResult:
    """Execute a lightweight LLM task through the full engine pipeline.

    Builds an ExecutionRequest internally and routes through execute(),
    giving lightweight calls the same observer/backend/rate-limiting
    treatment as full run loop executions.

    This replaces direct dispatch_prompt() calls from gateway/services.
    """
    if isinstance(task_type, LightweightTaskType):
        task_type_str = task_type.value
    else:
        task_type_str = task_type

    from umh.context.builder import ContextBuilder
    from umh.context.types import ContextPriority, ContextSection

    builder = ContextBuilder(max_tokens=4_000)
    builder.add_section(
        ContextSection(
            name="task",
            content=f"Task: {task_type_str}",
            priority=ContextPriority.HIGH,
            source="lightweight_execute",
        )
    )
    if system:
        builder.add_section(
            ContextSection(
                name="system_instruction",
                content=system,
                priority=ContextPriority.CRITICAL,
                source="caller",
            )
        )

    ctx_result = builder.build(user_prompt=prompt)

    exec_id = f"exec_{uuid.uuid4().hex[:16]}"
    request = ExecutionRequest(
        execution_id=exec_id,
        correlation_id=exec_id,
        causal_event_id="",
        session_id="",
        operation=operation,
        inputs={
            "prompt": ctx_result.user_prompt,
            "system_prompt": ctx_result.system_prompt,
            "max_tokens": max_tokens,
        },
        execution_class=ExecutionClass.LLM_CALL,
        constraints=ExecutionConstraints(timeout_s=30, max_tokens=max_tokens),
        target=ExecutionTarget(node_id="local", transport="adapter"),
        context=ExecutionContext(metadata={"task_type": task_type_str, "lightweight": True}),
        issued_at=_iso_now(),
        issued_by="umh.execution.engine.lightweight_execute",
        idempotency_key="",
    )

    return execute(request)
