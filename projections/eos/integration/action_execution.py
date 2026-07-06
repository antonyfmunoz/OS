"""EOS approved-action executor seam — WP-P4-EOS-EXECUTOR-ACTIVATE-001.

Activates the approve → execute → record lifecycle for the SMALLEST safe
subset: approved, NON-PROVIDER action types only (create_task,
create_document — both verified pure EOS-DB inserts at Beast head 9c8725f).
This is the execution half of the #182 execution-dispatch seam.

The executor guard is fail-closed on every axis:
- Beast source not build-safe / unverified / runtime not ready → refuse.
- Action type outside the allowlist (anything provider-coupled, e.g.
  send_email) → refuse; the allowlist is ALSO enforced inside the atomic
  claim SQL, so a non-allowlisted row can never even be claimed.
- Only an APPROVED row executes: the claim is a single atomic UPDATE guarded
  by status='approved' — pending/rejected/completed/failed/executing rows are
  unclaimable, and double execution is structurally impossible.
- Governance: the whole execution submits through governed_mutation (route-
  injected per the C34 law, canonical lazy default) — daemon down → fail
  closed, nothing claimed, nothing executed.

Recording (the Proof/Trace half of #182): success → completed + execution_result
+ completed_at; failure → EOS-faithful retry policy: retry_count+1 and back to
'pending' (the HUMAN re-approval queue) while retries remain, else terminal
'failed' — never an auto-retry. Failure text is truncated and scrubbed of
DSN-like material before storage or response.

This module never imports provider SDKs, never reads token material, and
never echoes action parameters into responses or logs.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_PROJECTION_ID = "eos"
_SURFACE = "action_execution"
_SEAM_ID = "execution-dispatch"

_DSN_PATTERN = re.compile(r"[a-z]+(?:ql)?://\S+")


def _safe_error(exc_text: str) -> str:
    """Bound and scrub an execution error before it is stored or returned."""
    scrubbed = _DSN_PATTERN.sub("<redacted-uri>", str(exc_text))
    return scrubbed[:300]


def _envelope(
    proposal_id: str,
    executed_by: str,
    connection_status: str,
    source_build_safe: bool,
    beast_head: Any = None,
    seam_primitive: Any = None,
    seam_target: Any = None,
    action_type: str | None = None,
    execution_applied: bool = False,
    prior_status: str | None = None,
    new_status: str | None = None,
    result_ref: str | None = None,
    executed_at: str | None = None,
    requeued_for_reapproval: bool = False,
    retry_count: int | None = None,
    max_retries: int | None = None,
    envelope_id: str = "",
    governance_status: str = "",
    error: str | None = None,
) -> dict[str, Any]:
    from projections.eos.integration.tables import EXECUTABLE_ACTION_TYPES

    return {
        "projection_id": _PROJECTION_ID,
        "surface": _SURFACE,
        "proposal_id": proposal_id,
        "executed_by": executed_by,
        "connection_status": connection_status,
        "source_build_safe": source_build_safe,
        "executor_scope": "non_provider_allowlist",
        "allowed_action_types": ",".join(sorted(EXECUTABLE_ACTION_TYPES)),
        "retry_policy": "human_reapproval_required",
        "beast_head": beast_head,
        "seam_id": _SEAM_ID,
        "seam_primitive": seam_primitive,
        "seam_target": seam_target,
        "action_type": action_type,
        "execution_applied": execution_applied,
        "prior_status": prior_status,
        "new_status": new_status,
        "result_ref": result_ref,
        "executed_at": executed_at,
        "requeued_for_reapproval": requeued_for_reapproval,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "envelope_id": envelope_id,
        "governance_status": governance_status,
        "error": error,
    }


def execute_action_proposal(
    proposal_id: str,
    executed_by: str = "umh_operator",
    mutation_runner: Any = None,
) -> dict[str, Any]:
    """Execute ONE approved, allowlisted, non-provider EOS action proposal.

    `mutation_runner` is the governed submission callable; the transport route
    injects transports.api.governed.governed_mutation (C34), and when omitted
    this accessor lazily resolves the same canonical function.

    Never raises. Flat proof-shaped envelope on every path:
    - blank id                         → invalid_request
    - Beast unsafe/unverified/not-ready→ refused, nothing touched
    - #182 seam map unavailable        → refused, nothing touched
    - env disabled                     → disconnected, nothing touched
    - governance unavailable           → fail-closed, nothing claimed
    - row not approved / not allowlisted / absent → refusal with honest reason
    - handler success                  → executing→completed with proof fields
    - handler failure                  → retry policy applied, safe error
    """
    proposal_id = (proposal_id or "").strip()
    if not proposal_id:
        return _envelope(
            proposal_id,
            executed_by,
            "invalid_request",
            False,
            error="a proposal id is required",
        )

    # 1. Beast source guard — stricter than the read/decision seams: the
    #    executor also requires VERIFIED verification and runtime readiness.
    try:
        from projections.eos.integration.readiness import eos_readiness

        readiness = eos_readiness()
        source_build_safe = readiness.get("source_build_safe") is True
        beast_head = readiness.get("beast_head")
        beast_ok = (
            source_build_safe
            and readiness.get("beast_verification") == "VERIFIED"
            and readiness.get("beast_runtime_ready") == "yes"
        )
    except Exception as exc:
        logger.debug("EOS readiness unavailable for execution: %s", exc)
        return _envelope(
            proposal_id,
            executed_by,
            "readiness_unavailable",
            False,
            error="readiness unavailable",
        )

    if not beast_ok:
        return _envelope(
            proposal_id,
            executed_by,
            "source_not_build_safe",
            source_build_safe,
            beast_head=beast_head,
            error="executor requires source_build_safe + VERIFIED + runtime_ready",
        )

    # 2. Mapping source — the #182 execution-dispatch seam.
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
            executed_by,
            "seam_map_unavailable",
            True,
            beast_head=beast_head,
            error="#182 seam map missing execution-dispatch",
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
            executed_by,
            "disconnected",
            True,
            beast_head=beast_head,
            seam_primitive=seam_primitive,
            seam_target=seam_target,
        )

    user_ids = list(config.get("user_ids") or [])
    outcome: dict[str, Any] = {}

    def _execute() -> tuple[str, bool]:
        import psycopg2

        from projections.eos.integration.tables import (
            EXECUTABLE_ACTION_TYPES,
            claim_action_for_execution,
            fetch_action_exec_state,
            insert_document_from_action,
            insert_task_from_action,
            record_action_execution_outcome,
        )

        conn = psycopg2.connect(config["database_url"])
        try:
            claimed = claim_action_for_execution(conn, proposal_id, user_ids=user_ids)
            if claimed is None:
                state = fetch_action_exec_state(conn, proposal_id, user_ids=user_ids)
                if state is None:
                    outcome["refusal"] = "not_found"
                    return (f"proposal {proposal_id} not found", False)
                outcome["prior_status"] = state["status"]
                outcome["action_type"] = state["action_type"]
                if state["action_type"] not in EXECUTABLE_ACTION_TYPES:
                    outcome["refusal"] = "action_type_not_allowlisted"
                    return (
                        f"action_type '{state['action_type']}' is not in the "
                        "non-provider allowlist; provider-coupled actions stay blocked",
                        False,
                    )
                outcome["refusal"] = "not_approved"
                return (
                    f"proposal {proposal_id} is '{state['status']}', only approved rows execute",
                    False,
                )

            outcome["prior_status"] = "approved"
            outcome["action_type"] = claimed["action_type"]
            outcome["executed_at"] = claimed["executed_at"]
            params = claimed.get("parameters") or {}

            try:
                if claimed["action_type"] == "create_task":
                    ref = insert_task_from_action(conn, claimed["agent_id"], params)
                    result = {"task_id": ref, "executed_via": "umh_governed_executor"}
                else:
                    ref = insert_document_from_action(conn, claimed["user_id"], params)
                    result = {"document_id": ref, "executed_via": "umh_governed_executor"}
            except Exception as handler_exc:
                recorded = record_action_execution_outcome(
                    conn, proposal_id, success=False, error=_safe_error(str(handler_exc))
                )
                outcome["failure"] = _safe_error(str(handler_exc))
                if recorded:
                    outcome.update(recorded)
                return (
                    f"execution of {proposal_id} failed: {_safe_error(str(handler_exc))}",
                    False,
                )

            recorded = record_action_execution_outcome(
                conn, proposal_id, success=True, result=result
            )
            outcome["result_ref"] = ref
            if recorded:
                outcome.update(recorded)
            return (f"proposal {proposal_id} executed: {claimed['action_type']}", True)
        finally:
            conn.close()

    # 4. Governed execution — the canonical runtime is the only path.
    try:
        if mutation_runner is None:
            from transports.api.governed import governed_mutation

            mutation_runner = governed_mutation

        response = mutation_runner(
            mutation_name="eos_action_proposal_execute",
            intent=f"execute approved EOS action proposal {proposal_id}",
            execute_fn=_execute,
            source="eos_action_execution_seam",
            metadata={
                "projection_id": _PROJECTION_ID,
                "seam_id": _SEAM_ID,
                "proposal_id": proposal_id,
                "executed_by": executed_by,
                "executor_scope": "non_provider_allowlist",
            },
        )
    except Exception as exc:
        logger.debug("governed execution submission failed: %s", exc)
        return _envelope(
            proposal_id,
            executed_by,
            "governance_unavailable",
            True,
            beast_head=beast_head,
            seam_primitive=seam_primitive,
            seam_target=seam_target,
            governance_status="unavailable",
            error=_safe_error(str(exc)),
        )

    applied = bool(response.success) and outcome.get("result_ref") is not None
    new_status = outcome.get("status")
    return _envelope(
        proposal_id,
        executed_by,
        "connected" if (response.success or outcome) else "governance_rejected",
        True,
        beast_head=beast_head,
        seam_primitive=seam_primitive,
        seam_target=seam_target,
        action_type=outcome.get("action_type"),
        execution_applied=applied,
        prior_status=outcome.get("prior_status"),
        new_status=new_status,
        result_ref=outcome.get("result_ref"),
        executed_at=outcome.get("recorded_at") or outcome.get("executed_at"),
        requeued_for_reapproval=(not applied and new_status == "pending"),
        retry_count=outcome.get("retry_count"),
        max_retries=outcome.get("max_retries"),
        envelope_id=getattr(response, "envelope_id", "") or "",
        governance_status=getattr(response, "status", "") or "",
        error=None
        if applied
        else (
            outcome.get("failure")
            or getattr(response, "rejected_reason", "")
            or response.output
            or None
        ),
    )
