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

# Risk classes that must NEVER execute without the governed spine. Only "low"
# is potentially eligible for degraded execution — and even then, only when the
# spec explicitly opts in via degraded_mode_allowed and its blast radius is local.
_DEGRADED_ELIGIBLE_RISK = frozenset({"low"})
_DEGRADED_ELIGIBLE_BLAST = frozenset({BlastRadius.LOCAL_RUNTIME, BlastRadius.LOCAL_FILE})


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
    # Wave 2 execution-authorization consumption (Amendment v1 clause 5).
    # Backward-compatible empty defaults; propagated onto the ActionEnvelope.
    authorization_ref: str = ""
    authorization_effect: str = ""
    authorized_subject_ids: list[str] = field(default_factory=list)
    authorized_scope_hash: str = ""
    authorization_expires_at: float = 0.0


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
    # True only for the narrow degraded-mode execution path (control plane down,
    # spec opted in, low-risk local). Callers/monitoring can surface this.
    degraded: bool = False
    # HTTP-equivalent status hint. 503 when the control plane is unavailable and
    # the mutation fails closed; None means "use the normal 200/422 mapping".
    http_status: int | None = None

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
        if self.degraded:
            d["degraded"] = True
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
            logger.warning("unregistered mutation rejected: %s", request.mutation_name)
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

    def _build_envelope(self, request: MutationRequest, spec: MutationSpec) -> ActionEnvelope:
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
            authorization_ref=request.authorization_ref,
            authorization_effect=request.authorization_effect,
            authorized_subject_ids=list(request.authorized_subject_ids),
            authorized_scope_hash=request.authorized_scope_hash,
            authorization_expires_at=request.authorization_expires_at,
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


# ── Fail-closed degraded-mode gate (control plane unavailable) ────────────
#
# This is the choke point BELOW the transport layer. When the organism daemon
# (and therefore the GovernedExecutionSpine) is unavailable, the transport shim
# in transports/api/governed.py delegates DOWN into this function rather than
# executing directly. The decision is a deterministic rules table keyed on the
# mutation's registered risk class and blast radius — no LLM, no network.
#
# Contract:
#   - Non-LOW risk (medium/high/critical), or any mutation whose spec does not
#     opt in via degraded_mode_allowed, or a non-local blast radius → FAIL CLOSED.
#     No execute_fn is ever called. No state changes.
#   - LOW risk + degraded_mode_allowed=True + LOCAL_RUNTIME/LOCAL_FILE → permitted,
#     and a mandatory degraded audit record is emitted BEFORE returning.


@dataclass
class DegradedDecision:
    """Result of the deterministic fail-closed evaluation."""

    allowed: bool
    reason: str
    spec: MutationSpec | None = None


def evaluate_degraded_mutation(
    request: MutationRequest,
    registry: MutationRegistry,
) -> DegradedDecision:
    """Deterministic rules table: may this mutation run without the spine?

    Pure function — inspects only the registered spec's risk class, blast radius,
    and degraded_mode_allowed opt-in. Never executes anything.
    """
    spec = registry.lookup(request.mutation_name)
    if spec is None:
        return DegradedDecision(
            allowed=False,
            reason=f"unregistered mutation: {request.mutation_name}",
        )

    if not spec.degraded_mode_allowed:
        return DegradedDecision(
            allowed=False,
            reason=(
                f"{request.mutation_name} not permitted in degraded mode "
                "(spec.degraded_mode_allowed is False)"
            ),
            spec=spec,
        )

    if spec.risk_level not in _DEGRADED_ELIGIBLE_RISK:
        return DegradedDecision(
            allowed=False,
            reason=(
                f"{request.mutation_name} risk={spec.risk_level} cannot run "
                "ungoverned (only low-risk permitted in degraded mode)"
            ),
            spec=spec,
        )

    if spec.blast_radius not in _DEGRADED_ELIGIBLE_BLAST:
        return DegradedDecision(
            allowed=False,
            reason=(
                f"{request.mutation_name} blast_radius={spec.blast_radius.value} "
                "cannot run ungoverned (only local blast radius permitted)"
            ),
            spec=spec,
        )

    return DegradedDecision(
        allowed=True,
        reason="low-risk local mutation with degraded_mode_allowed opt-in",
        spec=spec,
    )


def _emit_degraded_audit(
    request: MutationRequest, decision: DegradedDecision, status: str, output: str
) -> str:
    """Emit the mandatory degraded audit record to the execution ledger.

    Uses the existing ExecutionLedger (data/runtime/execution_ledger.jsonl),
    which persists standalone without the daemon. Returns the ledger entry id
    (empty string only if the ledger itself is unreachable, which is logged).
    """
    try:
        from substrate.organism.execution_ledger import get_execution_ledger

        ledger = get_execution_ledger()
        entry = ledger.record(
            request_id=f"degraded:{request.mutation_name}",
            executor_type="degraded_mode",
            description=f"[DEGRADED] {request.intent} ({decision.reason})",
            status=status,
        )
        return entry.entry_id
    except Exception as exc:  # ledger must never crash the mutation path
        logger.error("degraded audit record FAILED for %s: %s", request.mutation_name, exc)
        return ""


def route_mutation_degraded(
    request: MutationRequest,
    registry: MutationRegistry | None = None,
) -> MutationResponse:
    """Fail-closed entry point used when the control plane is unavailable.

    The transport shim calls this instead of executing directly. Non-eligible
    mutations are REJECTED with a 503-equivalent response and perform NO state
    change. Eligible low-risk local mutations execute and emit a degraded audit
    record.
    """
    if registry is None:
        # Registry is instance-agnostic (built-in specs only); safe to build
        # standalone when the daemon that would normally own it is down.
        registry = MutationRegistry()

    decision = evaluate_degraded_mutation(request, registry)

    if not decision.allowed:
        logger.warning(
            "control plane unavailable — FAIL CLOSED on %s: %s",
            request.mutation_name,
            decision.reason,
        )
        _emit_degraded_audit(
            request, decision, status="rejected_fail_closed", output=decision.reason
        )
        return MutationResponse(
            success=False,
            output=(
                "control plane unavailable; mutation rejected (fail-closed): " + decision.reason
            ),
            status="rejected_control_plane_unavailable",
            rejected_reason=decision.reason,
            degraded=True,
            http_status=503,
        )

    # Permitted degraded execution. Emit the audit record FIRST so there is a
    # durable record even if execute_fn raises.
    audit_id = _emit_degraded_audit(
        request, decision, status="degraded_executing", output=request.intent
    )
    logger.warning(
        "control plane unavailable — DEGRADED execution of %s (audit=%s)",
        request.mutation_name,
        audit_id,
    )

    try:
        output, success = request.execute_fn()
    except Exception as exc:
        logger.error("degraded execution failed for %s: %s", request.mutation_name, exc)
        _emit_degraded_audit(request, decision, status="degraded_failed", output=str(exc))
        return MutationResponse(
            success=False,
            output=str(exc),
            status="failed_degraded",
            degraded=True,
        )

    _emit_degraded_audit(
        request,
        decision,
        status="degraded_completed" if success else "degraded_failed",
        output=output,
    )
    return MutationResponse(
        success=success,
        output=output,
        status="completed_degraded",
        degraded=True,
    )


def route_mutation_governed(request: MutationRequest) -> Any:
    """Canonical substrate-native entry point: live spine when up, else fail-closed.

    This is the sibling of :func:`route_mutation_degraded` and the ONE place the
    daemon-backed router is constructed for substrate-native callers. Callers ask
    for governed routing; they never assemble a mutation runtime themselves.

    Resolution order:

    1. A live organism daemon registered on the canonical organism port
       (``substrate.sockets.organism_port``) → route through the full
       daemon-backed :class:`MutationRouter` → ``GovernedExecutionSpine``. This
       is what lets a HIGH-risk, degraded-disallowed mutation (e.g.
       ``execution_authorization_decision``) actually execute: the control plane
       is present, so the mutation is NOT degraded.
    2. No daemon → :func:`route_mutation_degraded`, the fail-closed gate that
       rejects any non-eligible mutation and only runs low-risk / LOCAL /
       degraded-opted-in specs, always audited.

    Router construction lives HERE rather than in the caller so that no caller
    builds a parallel mutation runtime of its own (the substrate-native loop
    invariant). Everything referenced is in-substrate: substrate never imports
    transports/.
    """
    # Resolved through module globals so a caller's monkeypatch of either symbol
    # (spine branch or degraded branch) is honoured at call time.
    try:
        from substrate.sockets.organism_port import get_organism

        daemon = get_organism()
        if daemon is not None:
            spine = getattr(daemon, "governed_spine", None)
            registry = getattr(daemon, "mutation_registry", None)
            if spine is not None and registry is not None:
                return globals()["MutationRouter"](spine=spine, registry=registry).execute(request)
    except Exception:  # noqa: BLE001 — never fail a mutation on router resolution; degrade below
        logger.debug("governed routing unavailable; falling back to degraded gate", exc_info=True)

    return globals()["route_mutation_degraded"](request)
