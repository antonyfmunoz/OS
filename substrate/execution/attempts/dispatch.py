"""Instruction compilation for execution attempts.

This is the FIRST production consumer of the Wave 1 instruction-compilation seam
(``substrate.execution.planning.instruction_compilation``), closing convergence
ledger #11. Each attempt receives ONE sealed :class:`ModelExecutionPackage`:
canonical Task identity + Role/Skill instructions + bounded context + allowed
tools + governance constraints (the authorization bounds) + verification
requirements + budgets, all sealed under an immutable ``package_hash``. A
compilation failure BLOCKS dispatch — there are no hidden/unregistered prompt
strings, and the worker cannot alter tenant/scope/authority/verification/proof
obligations.

The real-worker dispatch itself (spawning the CPU-gated subprocess in the lease
worktree) is wired in C4; here we own package compilation + the sealed-hash
contract that C4 dispatch consumes.
"""

from __future__ import annotations

import logging
from typing import Any

from substrate.execution.planning.instruction_compilation import (
    InstructionCompilationError,
    InstructionCompilationRequest,
    ModelExecutionPackage,
    compile_instruction_package,
)

logger = logging.getLogger(__name__)


class DispatchBlocked(RuntimeError):
    """Raised when an attempt cannot be dispatched (fail closed). The attempt is
    transitioned to BLOCKED by the caller — never dispatched with a fake result."""


# The machine-readable result contract every worker must return.
ATTEMPT_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["status", "summary"],
    "properties": {
        "status": {"type": "string", "enum": ["succeeded", "failed"]},
        "summary": {"type": "string"},
        "files_changed": {"type": "array", "items": {"type": "string"}},
        "commits": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "additionalProperties": True,
}


def compile_attempt_package(
    *,
    attempt: Any,
    packet: Any,
    assignment: Any,
    grant: Any,
) -> ModelExecutionPackage:
    """Compile the sealed execution package for one attempt. Raises
    :class:`DispatchBlocked` on compilation failure (dispatch must not proceed)."""
    operation_identity = {
        "operation": "execute_work_packet",
        "tenant_id": getattr(grant, "tenant_id", ""),
        "task_id": getattr(attempt, "task_id", ""),
        "attempt_id": getattr(attempt, "attempt_id", ""),
        "plan_record_id": getattr(attempt, "plan_record_id", ""),
        "plan_version": getattr(attempt, "plan_version", 0),
        "execution_authorization_ref": getattr(attempt, "execution_authorization_ref", ""),
    }

    context_frame = {
        "title": getattr(packet, "title", ""),
        "intent": getattr(packet, "user_intent", ""),
        "desired_end_state": getattr(packet, "desired_end_state", ""),
        "constraints": list(getattr(packet, "constraints", []) or []),
        "success_criteria": getattr(packet, "validation_plan", ""),
    }

    # Governance constraints ARE the authorization bounds — sealed into the hash.
    governance_constraints = [
        f"authorization_ref={getattr(grant, 'decision_ref', '')}",
        f"authorized_scope_hash={getattr(grant, 'authorized_scope_hash', '')}",
        f"risk_ceiling={getattr(grant, 'risk_ceiling', '')}",
        f"authorized_tasks={sorted(getattr(grant, 'task_frontier', []) or [])}",
        f"allowed_tools={sorted(getattr(assignment, 'tool_profile', []) or [])}",
        f"environment_class={getattr(assignment, 'environment_class', '')}",
    ]

    verification_requirements = list(
        getattr(grant, "verification_obligations", []) or []
    )
    if getattr(packet, "validation_plan", ""):
        verification_requirements.append(getattr(packet, "validation_plan"))

    budgets = {
        "cost_limit_usd": getattr(grant, "cost_limit_usd", 0.0),
        "cost_enforceable": getattr(grant, "cost_enforceable", False),
        "timeout_seconds": getattr(attempt, "timeout_seconds", 600) or 600,
        "max_turns": getattr(attempt, "max_turns", 30) or 30,
    }

    request = InstructionCompilationRequest(
        operation_identity=operation_identity,
        role_contract_id=getattr(assignment, "role_contract_id", ""),
        skill_requirement_refs=list(getattr(assignment, "skill_requirement_refs", []) or []),
        context_frame=context_frame,
        tool_definitions=[{"tool": t} for t in (getattr(assignment, "tool_profile", []) or [])],
        model_profile=dict(getattr(assignment, "model_profile", {}) or {}),
        output_schema=ATTEMPT_RESULT_SCHEMA,
        governance_constraints=governance_constraints,
        verification_requirements=verification_requirements,
        budgets=budgets,
    )

    try:
        package = compile_instruction_package(request)
    except InstructionCompilationError as exc:
        raise DispatchBlocked(
            f"instruction compilation failed for attempt "
            f"{getattr(attempt, 'attempt_id', '')}: {exc}"
        ) from exc
    return package


__all__ = ["compile_attempt_package", "DispatchBlocked", "ATTEMPT_RESULT_SCHEMA"]
