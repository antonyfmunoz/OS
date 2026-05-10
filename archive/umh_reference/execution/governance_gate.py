"""UMH Governance Gate — mandatory pre-execution policy evaluation.

Every execution directive must pass through the governance gate before
reaching the execution engine.  The gate only decides — it never executes.

Decision outcomes:
  ALLOW             — proceed to execution
  NOTIFY            — proceed but log/alert
  APPROVE_REQUIRED  — pause for human approval
  ESCALATE          — forward to higher authority
  DENY              — reject outright

The gate wraps the existing ``check_governance()`` from
``umh.governance.authority`` and adds environment validation,
capability safety checks, and trace integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.governance.authority import (
    AuthorityLevel,
    GovernanceDecision,
    check_governance,
)


class GateOutcome(str, Enum):
    ALLOW = "allow"
    NOTIFY = "notify"
    APPROVE_REQUIRED = "approve_required"
    ESCALATE = "escalate"
    DENY = "deny"


@dataclass(frozen=True)
class GateDecision:
    """Result of a governance gate evaluation."""

    outcome: GateOutcome
    reason: str
    authority_level: AuthorityLevel
    governance_decision: GovernanceDecision | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    evaluated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "reason": self.reason,
            "authority_level": self.authority_level.name,
            "governance_decision": (
                self.governance_decision.to_dict() if self.governance_decision else None
            ),
            "metadata": self.metadata,
            "evaluated_at": self.evaluated_at,
        }


@dataclass(frozen=True)
class ExecutionDirective:
    """What the system wants to execute — input to the governance gate."""

    operation: str
    inputs: dict[str, Any] = field(default_factory=dict)
    environment: str = ""
    capability: str = ""
    authority: AuthorityLevel = AuthorityLevel.ANALYZE
    constraints: dict[str, Any] = field(default_factory=dict)


_SAFE_OPERATIONS = frozenset(
    {
        "answer_query",
        "check_status",
        "run_analysis",
        "process_input",
        "summarize",
        "classify_intent",
    }
)

_UNSAFE_OPERATIONS = frozenset(
    {
        "delete_data",
        "execute_shell",
        "send_external",
        "modify_config",
        "financial_transaction",
    }
)


def _check_capability_policy(
    directive: ExecutionDirective,
) -> dict[str, Any] | None:
    """Check capability + environment policy from Phase 76 definitions.

    Returns None if no capability-level policy applies (legacy operations
    pass through to the existing governance check).  Returns a dict with
    outcome/reason if the capability is defined and policy blocks it.
    """
    if not directive.capability:
        return None

    from umh.capabilities.definitions import get_capability
    from umh.environments.definitions import get_environment

    cap_def = get_capability(directive.capability)
    if cap_def is None:
        return None

    env_def = get_environment(directive.environment)
    if env_def is None:
        return {
            "outcome": GateOutcome.DENY,
            "reason": f"Unknown environment: {directive.environment}",
            "metadata": {"capability": directive.capability},
        }

    if directive.capability not in env_def.capabilities:
        return {
            "outcome": GateOutcome.DENY,
            "reason": (
                f"Capability '{directive.capability}' not allowed in "
                f"environment '{directive.environment}'"
            ),
            "metadata": {
                "capability": directive.capability,
                "environment": directive.environment,
                "allowed_capabilities": sorted(env_def.capabilities),
            },
        }

    if (
        directive.capability not in cap_def.allowed_environments
        and directive.environment not in cap_def.allowed_environments
    ):
        return {
            "outcome": GateOutcome.DENY,
            "reason": (
                f"Environment '{directive.environment}' not allowed for "
                f"capability '{directive.capability}'"
            ),
            "metadata": {
                "capability": directive.capability,
                "allowed_environments": sorted(cap_def.allowed_environments),
            },
        }

    if directive.authority < cap_def.authority_required:
        if cap_def.requires_approval:
            return {
                "outcome": GateOutcome.APPROVE_REQUIRED,
                "reason": (
                    f"Capability '{directive.capability}' requires "
                    f"{cap_def.authority_required.name} authority "
                    f"(have {directive.authority.name})"
                ),
                "metadata": {
                    "capability": directive.capability,
                    "requires_approval": True,
                },
            }
        return {
            "outcome": GateOutcome.DENY,
            "reason": (
                f"Capability '{directive.capability}' requires "
                f"{cap_def.authority_required.name} authority "
                f"(have {directive.authority.name})"
            ),
            "metadata": {"capability": directive.capability},
        }

    return None


def evaluate(
    directive: ExecutionDirective,
    user_id: str = "",
) -> GateDecision:
    """Evaluate a directive against governance policy.

    This is the single governance entry point for the MVP path.
    """
    now = _iso_now()

    if not directive.operation:
        return GateDecision(
            outcome=GateOutcome.DENY,
            reason="Empty operation",
            authority_level=directive.authority,
            evaluated_at=now,
        )

    if not directive.environment:
        return GateDecision(
            outcome=GateOutcome.DENY,
            reason="No environment specified — execution requires explicit environment",
            authority_level=directive.authority,
            evaluated_at=now,
        )

    if directive.operation in _UNSAFE_OPERATIONS:
        return GateDecision(
            outcome=GateOutcome.DENY,
            reason=f"Operation '{directive.operation}' is classified as unsafe",
            authority_level=directive.authority,
            evaluated_at=now,
            metadata={"blocked_operation": directive.operation},
        )

    cap_check = _check_capability_policy(directive)
    if cap_check is not None:
        return GateDecision(
            outcome=cap_check["outcome"],
            reason=cap_check["reason"],
            authority_level=directive.authority,
            evaluated_at=now,
            metadata=cap_check.get("metadata", {}),
        )

    gov = check_governance(
        operation=directive.operation,
        authority_level=directive.authority,
        constraints=directive.constraints,
    )

    if not gov.allowed:
        if directive.authority < AuthorityLevel.EXECUTE:
            return GateDecision(
                outcome=GateOutcome.APPROVE_REQUIRED,
                reason=gov.reason,
                authority_level=directive.authority,
                governance_decision=gov,
                evaluated_at=now,
            )
        return GateDecision(
            outcome=GateOutcome.DENY,
            reason=gov.reason,
            authority_level=directive.authority,
            governance_decision=gov,
            evaluated_at=now,
        )

    outcome = GateOutcome.ALLOW
    if gov.warnings:
        outcome = GateOutcome.NOTIFY

    return GateDecision(
        outcome=outcome,
        reason=gov.reason,
        authority_level=directive.authority,
        governance_decision=gov,
        evaluated_at=now,
        metadata={"user_id": user_id} if user_id else {},
    )


def execute_governed(
    directive: ExecutionDirective,
    user_id: str = "",
    trace_store: Any | None = None,
    backend_registry: Any | None = None,
) -> dict[str, Any]:
    """Full governed execution path — governance + backend + canonical engine.

    Flow:
      1. Create trace
      2. Evaluate governance gate
      3. If not ALLOW/NOTIFY → return non-execution result
      4. Select backend
      5. Execute through canonical engine
      6. Complete trace
      7. Return result with trace_id

    This is orchestration around the engine, NOT a replacement.
    """
    from umh.control.trace_store import get_trace_store
    from umh.execution.backend_registry import get_backend_registry

    ts = trace_store or get_trace_store()
    br = backend_registry or get_backend_registry()

    trace_id = ts.create_trace(
        user_id=user_id,
        input_summary=f"{directive.operation}: {str(directive.inputs)[:200]}",
    )

    ts.append_event(
        trace_id,
        "directive_received",
        {
            "operation": directive.operation,
            "environment": directive.environment,
            "authority": directive.authority.name,
        },
    )

    gate = evaluate(directive, user_id=user_id)

    ts.append_event(trace_id, "governance_decision", gate.to_dict())

    if gate.outcome not in (GateOutcome.ALLOW, GateOutcome.NOTIFY):
        ts.fail_trace(trace_id, f"Governance: {gate.outcome.value} — {gate.reason}")
        return {
            "success": False,
            "trace_id": trace_id,
            "governance": gate.to_dict(),
            "response": f"Blocked: {gate.reason}",
        }

    try:
        backend_result = br.select_backend(directive.environment, directive.capability)
    except ValueError as e:
        ts.append_event(trace_id, "backend_selection_failed", {"error": str(e)})
        ts.fail_trace(trace_id, str(e))
        return {
            "success": False,
            "trace_id": trace_id,
            "governance": gate.to_dict(),
            "response": f"Backend selection failed: {e}",
        }
    backend_name = backend_result["name"]
    backend = backend_result["backend"]

    ts.append_event(
        trace_id,
        "backend_selected",
        {
            "backend": backend_name,
            "environment": directive.environment,
        },
    )

    from umh.execution.contract import (
        ExecutionClass,
        ExecutionConstraints,
        ExecutionContext,
        ExecutionRequest,
        ExecutionTarget,
    )
    from umh.execution.engine import execute as engine_execute

    import uuid

    exec_id = f"exec_{uuid.uuid4().hex[:16]}"
    request = ExecutionRequest(
        execution_id=exec_id,
        correlation_id=trace_id,
        causal_event_id="",
        session_id="",
        operation=directive.operation,
        inputs=directive.inputs,
        execution_class=ExecutionClass.LLM_CALL,
        constraints=ExecutionConstraints(
            timeout_s=directive.constraints.get("timeout_s", 30),
        ),
        target=ExecutionTarget(node_id="local", transport="adapter"),
        context=ExecutionContext(
            user_id=user_id,
            authority_class=directive.authority.name.lower(),
            metadata={"trace_id": trace_id, "governed": True},
        ),
        issued_at=_iso_now(),
        issued_by="umh.execution.governance_gate",
        idempotency_key="",
    )

    from umh.execution.interfaces import set_execution_backend, reset_execution_backend

    previous_backend = None
    try:
        set_execution_backend(backend)
        result = engine_execute(request)
    except Exception as e:
        ts.append_event(trace_id, "execution_failed", {"error": str(e)})
        ts.fail_trace(trace_id, str(e))
        return {
            "success": False,
            "trace_id": trace_id,
            "governance": gate.to_dict(),
            "response": f"Execution failed: {e}",
            "execution_id": exec_id,
        }
    finally:
        reset_execution_backend()

    ts.append_event(
        trace_id,
        "execution_completed",
        {
            "status": result.status.value,
            "latency_ms": result.latency_ms,
        },
    )

    if result.status.value == "succeeded":
        ts.complete_trace(trace_id, result.to_dict())
    else:
        ts.fail_trace(trace_id, result.error or "execution_failed")

    return {
        "success": result.status.value == "succeeded",
        "trace_id": trace_id,
        "governance": gate.to_dict(),
        "response": result.outputs.get("response", str(result.outputs)),
        "execution_id": exec_id,
        "execution_result": result.to_dict(),
    }
