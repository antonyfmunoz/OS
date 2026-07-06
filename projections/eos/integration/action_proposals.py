"""EOS ActionProposal read seam — WP-P4-EOS-ACTION-PROPOSAL-READ-001.

The smallest read-only bridge from Beast-backed EOS agent_actions semantics
into the UMH governed approval surface: pending EOS action proposals rendered
as a UMH ApprovalRequest-shaped read model. Proves the Approval mapping from
the #182 seam map on real EOS data WITHOUT executing, approving, retrying, or
mutating anything.

Composition (all fail-closed, never raises):

1. Beast build safety   — eos_readiness()['source_build_safe'] must be True or
                          the surface reports itself not-build-safe with no rows.
2. Mapping source       — the #182 seam map (action_seam.load_eos_action_seam_map)
                          is the authority for the seam target; absent map → no rows.
3. EOS DB (env-gated)   — manifest.load_eos_config(); unset EOS_DATABASE_URL →
                          stable "disconnected" envelope. When configured, the
                          connection is opened READ-ONLY (set_session readonly)
                          so a write is mechanically impossible, and only the
                          pending-queue SELECT in tables.py runs.

Execution is disabled by contract: execute_enabled is False on the envelope and
on every row, and this module imports no executor, no provider adapter, and no
approve/reject path. Retry policy default per #182: human re-approval required.

Imports are downward only (projection → same-package/substrate). Flat shape:
scalars on the envelope plus the single `proposals` list of flat row dicts.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_PROJECTION_ID = "eos"
_SURFACE = "action_proposals"
_SEAM_ID = "approval-queue-row"

# Deterministic EOS action status → UMH ApprovalState vocabulary
# (substrate.types.ApprovalState values). `failed` is terminal after the retry
# budget — no longer actionable, hence EXPIRED. Unknown statuses map to PENDING
# (fail-safe: an unknown state is surfaced for a human, never hidden).
_STATUS_TO_APPROVAL_STATE = {
    "pending": "PENDING",
    "approved": "APPROVED",
    "executing": "APPROVED",
    "completed": "APPROVED",
    "rejected": "REJECTED",
    "failed": "EXPIRED",
}

# Deterministic action-type → governed target domain (representation only).
_ACTION_TYPE_DOMAIN = {
    "send_email": "external_communication",
    "create_task": "work_management",
    "create_document": "documents",
}


def _envelope(
    connection_status: str,
    source_build_safe: bool,
    beast_head: Any = None,
    seam_primitive: Any = None,
    seam_target: Any = None,
    proposals: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    rows = proposals or []
    return {
        "projection_id": _PROJECTION_ID,
        "surface": _SURFACE,
        "connection_status": connection_status,
        "source_build_safe": source_build_safe,
        "execute_enabled": False,
        "retry_policy": "human_reapproval_required",
        "beast_head": beast_head,
        "seam_id": _SEAM_ID,
        "seam_primitive": seam_primitive,
        "seam_target": seam_target,
        "proposal_count": len(rows),
        "proposals": rows,
        "error": error,
    }


def _proposal_to_dict(row: Any, provenance: dict[str, Any]) -> dict[str, Any]:
    """Render one AgentActionProposalRow as a flat ApprovalRequest-shaped dict."""
    status = str(row.status)
    return {
        "proposal_id": row.id,
        "agent_id": row.agent_id,
        "agent_name": row.agent_name,
        "user_id": row.user_id,
        "action_type": row.action_type,
        "target_domain": _ACTION_TYPE_DOMAIN.get(row.action_type),
        "requested_operation": row.action_name,
        "summary": row.description,
        "status": status,
        "approval_state": _STATUS_TO_APPROVAL_STATE.get(status, "PENDING"),
        "requires_approval": bool(row.requires_approval),
        "priority": row.priority,
        "retry_count": row.retry_count,
        "max_retries": row.max_retries,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "source": "eos_agent_actions",
        "beast_head": provenance.get("head"),
        "umh_primitive": "Approval",
        "execute_enabled": False,
    }


def eos_action_proposals(limit: int = 50) -> dict[str, Any]:
    """Return the EOS pending action-proposal queue as a UMH approval read model.

    Never raises. Env-disabled (EOS_DATABASE_URL unset) → stable "disconnected"
    envelope with zero rows. Beast source not build-safe → "source_not_build_safe"
    with zero rows. #182 seam map unavailable → "seam_map_unavailable" with zero
    rows. Read-only end to end: the DB session is opened readonly and only the
    canonical pending-queue SELECT runs.
    """
    # 1. Beast build safety — live truth, not a snapshot.
    source_build_safe = False
    beast_head = None
    try:
        from projections.eos.integration.readiness import eos_readiness

        readiness = eos_readiness()
        source_build_safe = readiness.get("source_build_safe") is True
        beast_head = readiness.get("beast_head")
    except Exception as exc:
        logger.debug("EOS readiness unavailable for action proposals: %s", exc)
        return _envelope("readiness_unavailable", False, error="readiness unavailable")

    if not source_build_safe:
        return _envelope("source_not_build_safe", False, beast_head=beast_head)

    # 2. Mapping source — the #182 seam map is the authority for this seam.
    try:
        from projections.eos.integration.action_seam import load_eos_action_seam_map

        seam_doc = load_eos_action_seam_map()
        seam_row = next((s for s in seam_doc.get("seams", []) if s.get("seam") == _SEAM_ID), None)
    except Exception as exc:
        logger.debug("EOS action seam map unavailable: %s", exc)
        seam_row = None

    if seam_row is None:
        return _envelope(
            "seam_map_unavailable",
            True,
            beast_head=beast_head,
            error="#182 seam map missing approval-queue-row",
        )
    seam_primitive = seam_row.get("umh_primitive")
    seam_target = seam_row.get("target_owner")

    # 3. EOS DB — env-gated, read-only.
    try:
        from projections.eos.integration.manifest import load_eos_config

        config = load_eos_config()
    except Exception as exc:
        logger.debug("EOS config load failed: %s", exc)
        config = {}

    if not config:
        return _envelope(
            "disconnected",
            True,
            beast_head=beast_head,
            seam_primitive=seam_primitive,
            seam_target=seam_target,
        )

    provenance = {"head": beast_head}
    try:
        import psycopg2

        from projections.eos.integration.tables import fetch_pending_agent_actions

        conn = psycopg2.connect(config["database_url"])
        try:
            # Mechanical read-only guarantee: any write in this session errors.
            conn.set_session(readonly=True)
            rows = fetch_pending_agent_actions(
                conn,
                user_ids=list(config.get("user_ids") or []),
                limit=limit,
            )
        finally:
            conn.close()
    except Exception as exc:
        logger.debug("EOS action-proposal read failed: %s", exc)
        return _envelope(
            "unavailable",
            True,
            beast_head=beast_head,
            seam_primitive=seam_primitive,
            seam_target=seam_target,
            error=str(exc),
        )

    proposals = [_proposal_to_dict(row, provenance) for row in rows]
    return _envelope(
        "connected",
        True,
        beast_head=beast_head,
        seam_primitive=seam_primitive,
        seam_target=seam_target,
        proposals=proposals,
    )
