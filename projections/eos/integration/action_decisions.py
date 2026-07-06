"""EOS ActionProposal approval-command seam — WP-P4-EOS-ACTION-APPROVAL-COMMAND-001.

The smallest governed WRITE seam for EOS action proposals: approve or reject
one pending agent_actions row, record a proof-shaped result, and leave
execution disabled. This is the decision half of the #182
approve-reject-decision seam — NOT the executor packet.

What this module can do: transition ONE row pending→approved or
pending→rejected (atomic, enforced in SQL by the status='pending' predicate).

What this module can NEVER do (by construction, all regression-tested):
- execute the action (no executor import, no capability routing, no retry run)
- call any provider API (no adapters, no Google/LLM client SDKs)
- read or handle authentication-token material (that table is never touched)
- mutate CRM, tasks, documents, retry counters, outcome payloads, or params

Governance: the write is submitted through transports.api.governed
.governed_mutation — the canonical operation runtime (projection→transport
import is the sanctioned WRITE pattern, precedent projections/eos/workflows/
runner.py). When the organism daemon is down the mutation FAILS CLOSED
(503-equivalent, no state change) and this accessor reports it honestly.
The optional decision reason is carried in the mutation metadata (UMH-side
proof), never written into the EOS row — no schema touch.

Retry policy default per #182/#183: human re-approval required. Approving a
previously-failed proposal is NOT possible here (failed is not pending).

Fail-closed composition, mirroring the #183 read seam: live source_build_safe
→ #182 seam map as mapping authority → env-gated EOS DB. Never raises; every
path returns the same flat proof-shaped envelope.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_PROJECTION_ID = "eos"
_SURFACE = "action_decision"
_SEAM_ID = "approve-reject-decision"
_VALID_DECISIONS = ("approve", "reject")


def _envelope(
    proposal_id: str,
    decision: str,
    decided_by: str,
    reason: str | None,
    connection_status: str,
    source_build_safe: bool,
    beast_head: Any = None,
    seam_primitive: Any = None,
    seam_target: Any = None,
    decision_applied: bool = False,
    prior_status: str | None = None,
    new_status: str | None = None,
    decided_at: str | None = None,
    envelope_id: str = "",
    governance_status: str = "",
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "projection_id": _PROJECTION_ID,
        "surface": _SURFACE,
        "proposal_id": proposal_id,
        "decision": decision,
        "decided_by": decided_by,
        "reason": reason,
        "connection_status": connection_status,
        "source_build_safe": source_build_safe,
        "execute_enabled": False,
        "retry_policy": "human_reapproval_required",
        "beast_head": beast_head,
        "seam_id": _SEAM_ID,
        "seam_primitive": seam_primitive,
        "seam_target": seam_target,
        "decision_applied": decision_applied,
        "prior_status": prior_status,
        "new_status": new_status,
        "decided_at": decided_at,
        "envelope_id": envelope_id,
        "governance_status": governance_status,
        "error": error,
    }


def decide_action_proposal(
    proposal_id: str,
    decision: str,
    decided_by: str = "umh_operator",
    reason: str | None = None,
    mutation_runner: Any = None,
) -> dict[str, Any]:
    """Approve or reject ONE pending EOS action proposal through governance.

    `mutation_runner` is the governed submission callable; the transport route
    injects transports.api.governed.governed_mutation explicitly (C34 canonical
    mutation law), and when omitted this accessor lazily resolves the same
    canonical function — there is no ungoverned default.

    Never raises. Returns a flat proof-shaped envelope on every path:
    - invalid decision / blank id       → decision_applied=False, error set
    - Beast not build-safe              → "source_not_build_safe", no write
    - #182 seam map unavailable         → "seam_map_unavailable", no write
    - EOS env disabled                  → "disconnected", no write
    - governance (daemon) unavailable   → fail-closed, no write, reason surfaced
    - row not pending / absent          → decision_applied=False, prior status shown
    - success                           → decision_applied=True with proof fields
    """
    proposal_id = (proposal_id or "").strip()
    if decision not in _VALID_DECISIONS or not proposal_id:
        return _envelope(
            proposal_id,
            decision,
            decided_by,
            reason,
            "invalid_request",
            False,
            error=f"decision must be one of {list(_VALID_DECISIONS)} with a proposal id",
        )

    # 1. Beast build safety — live truth.
    try:
        from projections.eos.integration.readiness import eos_readiness

        readiness = eos_readiness()
        source_build_safe = readiness.get("source_build_safe") is True
        beast_head = readiness.get("beast_head")
    except Exception as exc:
        logger.debug("EOS readiness unavailable for action decision: %s", exc)
        return _envelope(
            proposal_id,
            decision,
            decided_by,
            reason,
            "readiness_unavailable",
            False,
            error="readiness unavailable",
        )

    if not source_build_safe:
        return _envelope(
            proposal_id,
            decision,
            decided_by,
            reason,
            "source_not_build_safe",
            False,
            beast_head=beast_head,
        )

    # 2. Mapping source — the #182 approve-reject-decision seam.
    try:
        from projections.eos.integration.action_seam import load_eos_action_seam_map

        seam_doc = load_eos_action_seam_map()
        seam_row = next((s for s in seam_doc.get("seams", []) if s.get("seam") == _SEAM_ID), None)
    except Exception as exc:
        logger.debug("EOS action seam map unavailable: %s", exc)
        seam_row = None

    if seam_row is None:
        return _envelope(
            proposal_id,
            decision,
            decided_by,
            reason,
            "seam_map_unavailable",
            True,
            beast_head=beast_head,
            error="#182 seam map missing approve-reject-decision",
        )
    seam_primitive = seam_row.get("umh_primitive")
    seam_target = seam_row.get("target_owner")

    # 3. EOS DB — env-gated.
    try:
        from projections.eos.integration.manifest import load_eos_config

        config = load_eos_config()
    except Exception as exc:
        logger.debug("EOS config load failed: %s", exc)
        config = {}

    if not config:
        return _envelope(
            proposal_id,
            decision,
            decided_by,
            reason,
            "disconnected",
            True,
            beast_head=beast_head,
            seam_primitive=seam_primitive,
            seam_target=seam_target,
        )

    user_ids = list(config.get("user_ids") or [])
    # Mutable capture for the bounded write's outcome, filled inside execute_fn
    # so the governed spine remains the only caller of the write.
    outcome: dict[str, Any] = {}

    def _execute() -> tuple[str, bool]:
        import psycopg2

        from projections.eos.integration.tables import (
            fetch_action_status,
            update_action_decision,
        )

        conn = psycopg2.connect(config["database_url"])
        try:
            updated = update_action_decision(
                conn, proposal_id, decision, decided_by, user_ids=user_ids
            )
            if updated is not None:
                outcome.update(updated)
                outcome["prior_status"] = "pending"
                return (f"proposal {proposal_id} {updated['status']}", True)
            current = fetch_action_status(conn, proposal_id, user_ids=user_ids)
            outcome["prior_status"] = current
            if current is None:
                return (f"proposal {proposal_id} not found", False)
            return (
                f"proposal {proposal_id} is '{current}', only pending rows accept decisions",
                False,
            )
        finally:
            conn.close()

    # 4. Governed write — the canonical runtime is the only mutation path.
    # The route injects governed_mutation; standalone callers resolve the same
    # canonical function here. Either way there is exactly one submission path.
    try:
        if mutation_runner is None:
            from transports.api.governed import governed_mutation

            mutation_runner = governed_mutation

        response = mutation_runner(
            mutation_name="eos_action_proposal_decision",
            intent=f"{decision} EOS action proposal {proposal_id}",
            execute_fn=_execute,
            source="eos_action_decision_seam",
            metadata={
                "projection_id": _PROJECTION_ID,
                "seam_id": _SEAM_ID,
                "proposal_id": proposal_id,
                "decision": decision,
                "decided_by": decided_by,
                "reason": reason or "",
                "execute_enabled": False,
            },
        )
    except Exception as exc:
        logger.debug("governed mutation submission failed: %s", exc)
        return _envelope(
            proposal_id,
            decision,
            decided_by,
            reason,
            "governance_unavailable",
            True,
            beast_head=beast_head,
            seam_primitive=seam_primitive,
            seam_target=seam_target,
            governance_status="unavailable",
            error=str(exc),
        )

    applied = bool(response.success) and outcome.get("status") is not None
    return _envelope(
        proposal_id,
        decision,
        decided_by,
        reason,
        "connected" if (response.success or outcome) else "governance_rejected",
        True,
        beast_head=beast_head,
        seam_primitive=seam_primitive,
        seam_target=seam_target,
        decision_applied=applied,
        prior_status=outcome.get("prior_status"),
        new_status=outcome.get("status"),
        decided_at=outcome.get("approved_at") or outcome.get("updated_at"),
        envelope_id=getattr(response, "envelope_id", "") or "",
        governance_status=getattr(response, "status", "") or "",
        error=None
        if applied
        else (getattr(response, "rejected_reason", "") or response.output or None),
    )
