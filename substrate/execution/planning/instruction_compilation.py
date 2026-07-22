"""Instruction-compilation seam — typed model-call packaging for planning.

Plan §9 (Wave 1). Every NEW Wave 1 model call on the planning path (optional
enhancement/inference) is compiled through this seam before invocation:

    InstructionCompilationRequest → ModelExecutionPackage (immutable hash)

Hard properties:
  - compilation failure PREVENTS invocation (no fallback prompt strings);
  - rendering can never alter canonical operation identity, scope, authority,
    or proof requirements — those fields are copied verbatim and sealed by
    the package hash;
  - no hidden prompt-string contracts: everything the model sees is in the
    package, provenance included.

This is the planning seam only — no general execution runtime.
UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class InstructionCompilationError(RuntimeError):
    """Compilation failed — the model call MUST NOT proceed."""


@dataclass
class InstructionCompilationRequest:
    """Everything a planning model call is allowed to depend on."""

    operation_identity: dict[str, Any] = field(default_factory=dict)
    # canonical identity: {operation, tenant_id, plan_record_id/intent_id, ...}
    role_contract_id: str = ""
    skill_requirement_refs: list[dict[str, Any]] = field(default_factory=list)
    context_frame: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    tool_definitions: list[dict[str, Any]] = field(default_factory=list)
    model_profile: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    governance_constraints: list[str] = field(default_factory=list)
    verification_requirements: list[str] = field(default_factory=list)
    budgets: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModelExecutionPackage:
    """The compiled, sealed package a model invocation receives."""

    package_id: str = ""
    system_policy: str = ""
    assistant_identity: str = ""
    role_instructions: str = ""
    operation_instructions: str = ""
    ordered_context: list[dict[str, Any]] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)
    tool_limits: list[dict[str, Any]] = field(default_factory=list)
    output_schema: dict[str, Any] = field(default_factory=dict)
    evaluator: str = ""
    retry_stop_escalation: dict[str, Any] = field(default_factory=dict)
    versions: dict[str, str] = field(default_factory=dict)
    # Sealed canonical fields — rendering may NOT alter these.
    operation_identity: dict[str, Any] = field(default_factory=dict)
    governance_constraints: list[str] = field(default_factory=list)
    verification_requirements: list[str] = field(default_factory=list)
    package_hash: str = ""
    compiled_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def compute_hash(self) -> str:
        payload = {
            k: v for k, v in self.to_dict().items() if k not in ("package_hash", "compiled_at")
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:32]


def _resolve_assistant_identity() -> str:
    """Configured assistant name — never a hardcoded persona literal."""
    try:
        from substrate.organism.world_model import get_ai_name  # type: ignore[attr-defined]

        name = get_ai_name()
        if name:
            return name
    except Exception as exc:
        logger.debug("assistant identity resolution failed, using default: %s", exc)
    return "Assistant"


def compile_instruction_package(
    request: InstructionCompilationRequest,
) -> ModelExecutionPackage:
    """Compile one planning model call. Raises on any incompleteness.

    Two different ModelProfiles may render differently (order, emphasis), but
    the canonical operation identity, governance constraints, and verification
    requirements are copied VERBATIM and sealed under package_hash.
    """
    identity = request.operation_identity
    if not identity or not identity.get("operation"):
        raise InstructionCompilationError("operation_identity.operation is required")
    if not identity.get("tenant_id"):
        raise InstructionCompilationError("operation_identity.tenant_id is required")
    if not request.output_schema:
        raise InstructionCompilationError("output_schema is required — no free-text planning calls")
    if not request.model_profile.get("model"):
        raise InstructionCompilationError("model_profile.model is required")

    profile = request.model_profile
    ordered_context: list[dict[str, Any]] = []
    context_sections = [
        ("context_frame", request.context_frame),
        ("evidence", {"refs": request.evidence_refs}),
    ]
    if profile.get("context_order") == "evidence_first":
        context_sections.reverse()
    for name, payload in context_sections:
        ordered_context.append({"section": name, "payload": payload})

    provenance = [
        f"operation:{identity.get('operation')}",
        f"tenant:{identity.get('tenant_id')}",
        f"role:{request.role_contract_id or 'unbound'}",
    ] + [f"evidence:{ref.get('evidence_id', '?')}" for ref in request.evidence_refs]

    package = ModelExecutionPackage(
        package_id=f"mep-{hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:12]}",
        system_policy=(
            "Deterministic-first planning enhancement. Output MUST match the "
            "schema. You may refine content; you may NOT change scope, "
            "authority, targets, or proof requirements."
        ),
        assistant_identity=_resolve_assistant_identity(),
        role_instructions=f"Operate under role contract {request.role_contract_id}"
        if request.role_contract_id
        else "",
        operation_instructions=str(identity.get("operation", "")),
        ordered_context=ordered_context,
        provenance=provenance,
        tool_limits=list(request.tool_definitions),
        output_schema=dict(request.output_schema),
        evaluator="schema_validation",
        retry_stop_escalation={"max_retries": 1, "on_failure": "deterministic_fallback"},
        versions={"seam": "wave1-v1", "model": str(profile.get("model", ""))},
        operation_identity=dict(identity),
        governance_constraints=list(request.governance_constraints),
        verification_requirements=list(request.verification_requirements),
    )
    package.package_hash = package.compute_hash()
    return package


__all__ = [
    "InstructionCompilationError",
    "InstructionCompilationRequest",
    "ModelExecutionPackage",
    "compile_instruction_package",
]
