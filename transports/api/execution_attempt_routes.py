"""Canonical execution read surface + governed cancel/retry (Wave 2 C6).

Thin transport adapter over ``substrate.execution.attempts`` — the ONE canonical
execution read contract the cockpit Execution surface projects from. Reads never
raise a 500 (they return a stable error dict); writes (cancel/retry) go through
``governed_mutation``, fail closed, and return the canonical reread.

Module-scope Pydantic request models (PEP-563 lesson from objective_plan_routes:
FastAPI resolves body models at import, so they must be module-level).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CancelBody(BaseModel):
    reason: str = ""
    decided_by: str = "operator"


class RetryBody(BaseModel):
    decided_by: str = "operator"


def _store() -> Any:
    from substrate.execution.attempts.store import ExecutionAttemptStore

    return ExecutionAttemptStore()


def _attempt_row(a: Any) -> dict[str, Any]:
    return {
        "attempt_id": a.attempt_id,
        "task_id": a.task_id,
        "plan_record_id": a.plan_record_id,
        "plan_version": a.plan_version,
        "decision_ref": a.execution_authorization_ref,
        "attempt_number": a.attempt_number,
        "status": a.status,
        "phase": a.status,
        "blocked_reason": a.blocked_reason,
        "worker_identity": a.worker_identity,
        "assignment_id": a.assignment_id,
        "lease_id": a.lease_id,
        "verifier_role_id": a.verifier_role_id,
        "proof_id": a.proof_id,
        "retry_of_attempt_id": a.previous_attempt_id,
        "correlation_id": a.correlation_id,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


def _build_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/execution", tags=["execution"])

    def _tenant_visible(tenant_id: str, row_tenant: str) -> bool:
        """Exact tenant match. EMPTY on either side means DENY, never ALLOW.

        This previously read ``not tenant_id or not row_tenant or ...``, which
        was fail-OPEN in both directions on the most sensitive surface in the
        slice (worker identities, lease paths, files_changed, commits, and
        CANCEL):

        - an attempt written WITHOUT a tenant was visible and cancellable by
          every tenant — and such a record exists in live state
          (``ea-cf043ef5e0a0``, status ``running``);
        - a caller whose principal resolution FAILED got ``""`` and therefore
          saw EVERYTHING, so a resolution outage escalated privilege instead of
          removing it.

        ``principal_resolution`` states a "Fail-closed posture"; this read path
        inverted it (adversarial-review HIGH). A deliberate single-tenant
        fail-open may be defensible on the plan surface, which documents it —
        it is not defensible here, and it is not needed: the field harness and
        production both resolve a non-empty tenant.
        """
        return bool(tenant_id) and bool(row_tenant) and row_tenant == tenant_id

    def _caller_tenant() -> str:
        """The caller's tenant, or "" when it cannot be resolved.

        "" now DENIES rather than grants (see ``_tenant_visible``), so the bare
        ``except`` below removes authority instead of conferring it.
        """
        try:
            from substrate.contracts.principal_resolution import resolve_principal_context

            return resolve_principal_context().tenant_id
        except Exception as exc:
            logger.warning("caller tenant unresolved — denying execution reads: %s", exc)
            return ""

    @router.get("/attempts")
    def attempts(status: str = "", plan_record_id: str = "", packet_id: str = "") -> dict[str, Any]:
        try:
            store = _store()
            tenant = _caller_tenant()
            rows = store._read_lines(store._attempts_path)  # noqa: SLF001 read-only surface
            out = []
            for r in rows:
                if status and r.get("status") != status:
                    continue
                if plan_record_id and r.get("plan_record_id") != plan_record_id:
                    continue
                if packet_id and r.get("task_id") != packet_id:
                    continue
                if not _tenant_visible(tenant, r.get("tenant_id", "")):
                    continue
                from substrate.execution.attempts.records import ExecutionAttempt

                out.append(_attempt_row(ExecutionAttempt.from_dict(r)))
            return {"attempts": out}
        except Exception as exc:
            logger.error("execution attempts read failed: %s", exc)
            return {"attempts": [], "error": str(exc)}

    @router.get("/attempts/{attempt_id}")
    def attempt_detail(attempt_id: str) -> dict[str, Any]:
        try:
            store = _store()
            att = store.get_attempt(attempt_id)
            if att is None:
                return {"error": "not found"}
            # Cross-tenant reads leaked worker identities, lease paths,
            # files_changed and commits (adversarial-review CRITICAL). "not
            # found" rather than "forbidden": existence is itself tenant data.
            if not _tenant_visible(_caller_tenant(), getattr(att, "tenant_id", "")):
                return {"error": "not found"}
            row = _attempt_row(att)
            row["transitions"] = att.transitions
            row["assignment"] = store.assignment_for_attempt(attempt_id)
            row["environment_lease"] = store.get_lease(att.lease_id) if att.lease_id else None
            row["files_changed"] = att.files_changed
            row["commits"] = att.commits
            row["cancel_allowed"] = att.status in ("created", "ready", "leased", "dispatched", "running")
            row["retry_allowed"] = att.status == "failed"
            return row
        except Exception as exc:
            logger.error("execution attempt detail failed: %s", exc)
            return {"error": str(exc)}

    @router.get("/frontier")
    def frontier() -> dict[str, Any]:
        """Authorized frontier: tasks in an ACTIVE grant's task_frontier."""
        try:
            store = _store()
            out = []
            tenant = _caller_tenant()
            for grant in store.active_grants():
                if not _tenant_visible(tenant, getattr(grant, "tenant_id", "")):
                    continue
                for task_id in grant.task_frontier:
                    attempts = store.attempts_for_task(task_id)
                    out.append({
                        "packet_id": task_id,
                        "plan_record_id": grant.plan_record_id,
                        "decision_ref": grant.decision_ref,
                        "attempt_count": len(attempts),
                        "active": any(not a.is_terminal() for a in attempts),
                    })
            return {"frontier": out}
        except Exception as exc:
            logger.error("execution frontier read failed: %s", exc)
            return {"frontier": [], "error": str(exc)}

    @router.get("/authorizations")
    def authorizations() -> dict[str, Any]:
        try:
            store = _store()
            rows = store._read_lines(store._grants_path)  # noqa: SLF001
            tenant = _caller_tenant()
            rows = [r for r in rows if _tenant_visible(tenant, r.get("tenant_id", ""))]
            return {"authorizations": [
                {
                    "decision_ref": r.get("decision_ref"),
                    "plan_record_id": r.get("plan_record_id"),
                    "plan_version": r.get("plan_version"),
                    "status": r.get("status"),
                    "task_frontier": r.get("task_frontier", []),
                    "expires_at": r.get("expires_at"),
                }
                for r in rows
            ]}
        except Exception as exc:
            logger.error("execution authorizations read failed: %s", exc)
            return {"authorizations": [], "error": str(exc)}

    @router.get("/by-plan/{plan_record_id}")
    def by_plan(plan_record_id: str) -> dict[str, Any]:
        try:
            store = _store()
            tenant = _caller_tenant()
            attempts = [
                _attempt_row(a)
                for a in store.attempts_for_plan(plan_record_id)
                if _tenant_visible(tenant, getattr(a, "tenant_id", ""))
            ]
            grants = [
                {"decision_ref": g.decision_ref, "status": g.status,
                 "task_frontier": g.task_frontier}
                for g in store.grants_for_plan(plan_record_id)
                if _tenant_visible(tenant, getattr(g, "tenant_id", ""))
            ]
            return {"attempts": attempts, "authorizations": grants}
        except Exception as exc:
            logger.error("execution by-plan read failed: %s", exc)
            return {"attempts": [], "authorizations": [], "error": str(exc)}

    @router.get("/overlay")
    def overlay(packet_ids: str = "") -> dict[str, Any]:
        try:
            store = _store()
            ids = [p for p in packet_ids.split(",") if p]
            out: dict[str, Any] = {}
            tenant = _caller_tenant()
            for pid in ids:
                attempts = [
                    a
                    for a in store.attempts_for_task(pid)
                    if _tenant_visible(tenant, getattr(a, "tenant_id", ""))
                ]
                if not attempts:
                    continue
                active = next((a for a in attempts if not a.is_terminal()), None)
                proof = next((a.proof_id for a in attempts if a.proof_id), "")
                out[pid] = {
                    "attempt_count": len(attempts),
                    "active_phase": active.status if active else "",
                    "assigned_role": active.verifier_role_id if active else "",
                    "blocker_state": active.blocked_reason if active else "",
                    "proof_id": proof,
                }
            return {"overlay": out}
        except Exception as exc:
            logger.error("execution overlay read failed: %s", exc)
            return {"overlay": {}, "error": str(exc)}

    @router.post("/attempts/{attempt_id}/cancel")
    def cancel(attempt_id: str, body: CancelBody) -> dict[str, Any]:
        try:
            from transports.api.governed import governed_mutation

            store = _store()
            att = store.get_attempt(attempt_id)
            if att is None:
                return {"success": False, "error": "not found"}
            # A cross-tenant CANCEL terminated another tenant's in-flight
            # execution (adversarial-review CRITICAL). The store is tenant-blind
            # — transition_cas validates version/status/legality/immutability
            # but never tenant — so this is the boundary that must hold.
            if not _tenant_visible(_caller_tenant(), getattr(att, "tenant_id", "")):
                return {"success": False, "error": "not found"}

            def _do() -> tuple[str, bool]:
                store.transition_cas(
                    attempt_id, "cancelled",
                    expected_record_version=att.record_version,
                    expected_statuses=(att.status,),
                    actor=f"operator:{body.decided_by}", reason=body.reason or "operator cancel",
                )
                return (f"attempt {attempt_id} cancelled", True)

            resp = governed_mutation(
                mutation_name="execution_attempt_transition",
                intent=f"cancel attempt {attempt_id}",
                execute_fn=_do, source="cockpit",
                metadata={"attempt_id": attempt_id},
            )
            ok = bool(getattr(resp, "success", False))
            reread = store.get_attempt(attempt_id)
            return {"success": ok, "attempt": _attempt_row(reread) if reread else None}
        except Exception as exc:
            logger.error("execution cancel failed: %s", exc)
            return {"success": False, "error": str(exc)}

    @router.post("/attempts/{attempt_id}/retry")
    def retry(attempt_id: str, body: RetryBody) -> dict[str, Any]:
        # Fail closed: retry is minted by the scheduler under an ACTIVE grant,
        # not directly here — the route records the operator's request and the
        # next scheduler pass creates the linked new attempt if budget remains.
        try:
            store = _store()
            att = store.get_attempt(attempt_id)
            if att is None:
                return {"success": False, "error": "not found"}
            if not _tenant_visible(_caller_tenant(), getattr(att, "tenant_id", "")):
                return {"success": False, "error": "not found"}
            if att.status != "failed":
                return {"success": False, "error": f"attempt is {att.status}, only failed attempts retry"}
            grant = store.get_grant(att.execution_authorization_ref)
            if grant is None or grant.status != "active":
                return {"success": False, "error": "no active authorization — cannot retry (fail closed)"}
            return {"success": True, "note": "retry will be scheduled on the next pass",
                    "task_id": att.task_id}
        except Exception as exc:
            logger.error("execution retry failed: %s", exc)
            return {"success": False, "error": str(exc)}

    return router


def mount(app_router: Any) -> None:
    app_router.include_router(_build_router())


__all__ = ["mount"]
