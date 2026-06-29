"""MutationRouter — canonical choke point for all organism state mutations.

Every mutation enters the system through MutationRouter.execute().
The router builds an ActionEnvelope from the MutationRequest and
the corresponding MutationSpec, then submits it to the
GovernedExecutionSpine.

No mutation may bypass this path. No alternative mutation runtime
may exist.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from substrate.organism.action_envelope import (
    ActionEnvelope,
    BlastRadius,
    EnvelopeStatus,
    ExecutionConstraints,
    ReversibilityClass,
    RollbackStrategy,
    VerificationStrategy,
)
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.mutation_registry import MutationRegistry, MutationSpec

logger = logging.getLogger(__name__)


@dataclass
class MutationRequest:
    """What a route handler provides to the router."""

    mutation_name: str
    intent: str
    execute_fn: Callable[[], tuple[str, bool]]
    source: str = "cockpit"
    metadata: dict[str, Any] = field(default_factory=dict)
    risk_level: str | None = None
    blast_radius: BlastRadius | None = None
    reversibility: ReversibilityClass | None = None
    require_approval: bool | None = None
    verification_fn: Callable[[], bool] | None = None
    rollback_fn: Callable[[], bool] | None = None


@dataclass
class MutationResponse:
    """What the router returns to the route handler."""

    success: bool
    output: str = ""
    envelope_id: str = ""
    status: str = ""
    awaiting_approval: bool = False
    rejected_reason: str = ""
    envelope: ActionEnvelope | None = None

    def to_http_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "success": self.success,
            "envelope_id": self.envelope_id,
            "status": self.status,
        }
        if self.output:
            d["output"] = self.output
        if self.awaiting_approval:
            d["awaiting_approval"] = True
        if self.rejected_reason:
            d["rejected_reason"] = self.rejected_reason
        return d


class MutationRouter:
    """Routes MutationRequests through GovernedExecutionSpine.

    This is the single choke point for all organism state mutations.
    """

    def __init__(
        self,
        spine: GovernedExecutionSpine,
        registry: MutationRegistry,
    ) -> None:
        self._spine = spine
        self._registry = registry

    def execute(self, request: MutationRequest) -> MutationResponse:
        spec = self._registry.lookup(request.mutation_name)
        if spec is None:
            logger.warning(
                "unregistered mutation rejected: %s", request.mutation_name
            )
            return MutationResponse(
                success=False,
                output=f"unregistered mutation: {request.mutation_name}",
                status="rejected",
            )

        try:
            envelope = self._build_envelope(request, spec)
        except Exception as exc:
            logger.error("envelope build failed for %s: %s", request.mutation_name, exc)
            return MutationResponse(
                success=False,
                output=f"envelope build error: {exc}",
                status="error",
            )

        try:
            result = self._spine.submit(envelope)
        except Exception as exc:
            logger.error("spine submit failed for %s: %s", request.mutation_name, exc)
            return MutationResponse(
                success=False,
                output=f"spine error: {exc}",
                status="error",
                envelope_id=envelope.envelope_id,
            )

        return self._to_response(result)

    def _build_envelope(
        self, request: MutationRequest, spec: MutationSpec
    ) -> ActionEnvelope:
        verification = None
        if request.verification_fn is not None:
            verification = VerificationStrategy(
                description=f"verify:{request.mutation_name}",
                verify_fn=request.verification_fn,
            )

        rollback = None
        if request.rollback_fn is not None:
            rollback = RollbackStrategy(
                description=f"rollback:{request.mutation_name}",
                rollback_fn=request.rollback_fn,
            )

        return ActionEnvelope(
            intent=request.intent,
            action_type=spec.action_type,
            source=request.source,
            execute_fn=request.execute_fn,
            risk_level=request.risk_level or spec.risk_level,
            blast_radius=request.blast_radius or spec.blast_radius,
            reversibility=request.reversibility or spec.reversibility,
            verification=verification,
            rollback=rollback,
            constraints=ExecutionConstraints(
                max_retries=spec.max_retries,
                timeout_seconds=spec.timeout_seconds,
                require_approval=(
                    request.require_approval
                    if request.require_approval is not None
                    else spec.require_approval
                ),
            ),
            required_capabilities=list(spec.required_capabilities),
            metadata={
                "mutation_name": request.mutation_name,
                **request.metadata,
            },
        )

    def _to_response(self, envelope: ActionEnvelope) -> MutationResponse:
        awaiting = envelope.status == EnvelopeStatus.PROPOSED
        rejected = envelope.status == EnvelopeStatus.REJECTED

        if awaiting:
            success = True
        elif rejected:
            success = False
        else:
            success = envelope.result_success

        return MutationResponse(
            success=success,
            output=envelope.result_output,
            envelope_id=envelope.envelope_id,
            status=envelope.status.value,
            awaiting_approval=awaiting,
            rejected_reason=envelope.rejected_reason,
            envelope=envelope,
        )
