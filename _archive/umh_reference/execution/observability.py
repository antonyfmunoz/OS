"""UMH Execution Observability — structured events and enhanced observer.

Provides:
  - ExecutionEvent: structured record of every execution
  - EnhancedExecutionObserver: replaces LoggingExecutionObserver with
    structured event emission and capability scoring
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from umh.execution.contract import (
    ExecutionClass,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from umh.execution.scoring import get_capability_scorer

_log = logging.getLogger(__name__)

_scorer = get_capability_scorer()


@dataclass(frozen=True)
class ExecutionEvent:
    """Structured record of a single execution."""

    execution_id: str
    operation: str
    capability_type: str  # maps to CapabilityType value
    execution_class: str  # maps to ExecutionClass value
    status: str  # maps to ExecutionStatus value
    latency_ms: int = 0
    model_used: str | None = None
    cost_usd: float = 0.0
    error: str | None = None
    issued_by: str = ""
    adapter: str = "spine"
    environment_id: str = "local"
    environment_type: str = "local"
    execution_mode: str = "real"
    max_tokens: int = 0
    enforcement_flags: tuple[str, ...] = ()
    approval_id: str | None = None
    approved_execution: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "execution_id": self.execution_id,
            "operation": self.operation,
            "capability_type": self.capability_type,
            "execution_class": self.execution_class,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "model_used": self.model_used,
            "cost_usd": self.cost_usd,
            "error": self.error,
            "issued_by": self.issued_by,
            "adapter": self.adapter,
            "environment_id": self.environment_id,
            "environment_type": self.environment_type,
            "execution_mode": self.execution_mode,
            "max_tokens": self.max_tokens,
            "enforcement_flags": list(self.enforcement_flags),
            "approval_id": self.approval_id,
            "approved_execution": self.approved_execution,
        }


def _classify_capability(request: ExecutionRequest) -> str:
    """Map an ExecutionRequest to a CapabilityType string."""
    if request.execution_class == ExecutionClass.LLM_CALL:
        return "llm_call"
    if request.operation == "shell_command":
        return "shell_command"
    if request.operation in (
        "file_read",
        "file_list",
        "file_stat",
        "file_write",
        "file_delete",
    ):
        return "file_operation"
    if request.operation.startswith("browser_"):
        return "browser_action"
    if request.operation.startswith("computer_"):
        return "computer_use"
    if request.operation.startswith("os_"):
        return "os_interaction"
    return request.execution_class.value


class EnhancedExecutionObserver:
    """Structured execution observer with event emission and scoring integration."""

    def __init__(self) -> None:
        self._pending: dict[
            str, tuple[ExecutionRequest, float, str, str, str, int, tuple[str, ...]]
        ] = {}

    def on_request(self, request: ExecutionRequest) -> None:
        """Record an incoming execution request."""
        try:
            from umh.execution.environment import (
                EnforcementVerdict,
                enforce_environment,
                select_environment,
            )

            env = select_environment(request)

            enforcement_flags: list[str] = []
            if request.constraints.sandbox:
                enforcement_flags.append("sandbox_requested")
            if request.constraints.max_tokens > 0:
                enforcement_flags.append(f"max_tokens={request.constraints.max_tokens}")
            if request.constraints.cost_limit_usd > 0:
                enforcement_flags.append(f"cost_limit=${request.constraints.cost_limit_usd:.4f}")

            enforcement = enforce_environment(request, env)
            if enforcement.verdict == EnforcementVerdict.ALLOW:
                enforcement_flags.append("environment_enforced")

            max_tokens = request.constraints.max_tokens or request.inputs.get("max_tokens", 0)

            self._pending[request.execution_id] = (
                request,
                time.monotonic(),
                env.id,
                env.env_type.value,
                env.execution_mode.value,
                max_tokens,
                tuple(enforcement_flags),
            )
            _log.info(
                "[ExecutionObserver] request: id=%s op=%s class=%s capability=%s "
                "env=%s max_tokens=%d issued_by=%s",
                request.execution_id,
                request.operation,
                request.execution_class.value,
                _classify_capability(request),
                env.id,
                max_tokens,
                request.issued_by,
            )
        except Exception:
            pass

    def on_result(self, result: ExecutionResult) -> None:
        """Record an execution result, build structured event, feed scorer."""
        try:
            request_info = self._pending.pop(result.execution_id, None)
            if request_info:
                request, start_time, env_id, env_type, exec_mode, max_tokens, enforcement_flags = (
                    request_info
                )
                capability_type = _classify_capability(request)
                issued_by = request.issued_by
                exec_class = request.execution_class.value
            else:
                capability_type = result.operation
                issued_by = ""
                exec_class = "unknown"
                env_id = "local"
                env_type = "local"
                exec_mode = "real"
                max_tokens = 0
                enforcement_flags = ()

            # Extract approval context from request metadata
            req_approval_id = None
            req_approved = False
            if request_info:
                req_approval_id = request.context.metadata.get("approval_id")
                req_approved = request.context.metadata.get("approved_execution", False)

            event = ExecutionEvent(
                execution_id=result.execution_id,
                operation=result.operation,
                capability_type=capability_type,
                execution_class=exec_class,
                status=result.status.value,
                latency_ms=result.latency_ms,
                model_used=result.model_used,
                cost_usd=result.cost_usd,
                error=result.error,
                issued_by=issued_by,
                environment_id=env_id,
                environment_type=env_type,
                execution_mode=exec_mode,
                max_tokens=max_tokens,
                enforcement_flags=enforcement_flags,
                approval_id=req_approval_id,
                approved_execution=req_approved,
            )

            approved_str = f" approved={req_approved}" if req_approved else ""
            approval_id_str = f" approval_id={req_approval_id}" if req_approval_id else ""
            _log.info(
                "[ExecutionObserver] result: id=%s op=%s capability=%s status=%s "
                "env=%s mode=%s%s%s max_tokens=%d model=%s latency=%dms cost=$%.6f",
                event.execution_id,
                event.operation,
                event.capability_type,
                event.status,
                event.environment_id,
                event.execution_mode,
                approved_str,
                approval_id_str,
                event.max_tokens,
                event.model_used or "none",
                event.latency_ms,
                event.cost_usd,
            )

            # Feed to capability scorer
            _scorer.record(event)

        except Exception:
            pass
