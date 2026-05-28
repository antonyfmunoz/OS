"""Cockpit spine router — GovernedExecutionSpine, Journal, MutationRegistry,
SpineGuard endpoints.

Extracted from cockpit.py (Phase 6.2) to keep the main cockpit under 3000 lines.
All routes are mounted under /api/umh/ via include_router in cockpit.py.

Auth model: configure() must be called before include_router(). It receives
the real operator-auth dependency from cockpit.py and wires it into every
privileged route. Calling any route before configure() returns 503.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)

spine_router: APIRouter = APIRouter()

_get_organism: Callable[[], Any] = lambda: None
_check_rate_limit: Callable[[str, str], None] = lambda action, client_id: None
_configured: bool = False


def configure(
    get_organism_fn: Callable[[], Any],
    check_rate_limit_fn: Callable[[str, str], None],
    require_operator_dep: Any,
) -> None:
    """Wire shared cockpit utilities and operator auth into the spine router.

    Must be called once from cockpit.py before include_router(). Rebuilds
    the router so privileged routes carry the real auth dependency.
    """
    global _get_organism, _check_rate_limit, _configured, spine_router

    _get_organism = get_organism_fn
    _check_rate_limit = check_rate_limit_fn
    _configured = True

    spine_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    """Construct the spine router with operator auth on privileged routes."""
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Read-only endpoints (no auth required) ─────────────────────────────

    r.add_api_route("/organism/spine", _spine_status, methods=["GET"])
    r.add_api_route("/organism/spine/pending", _spine_pending, methods=["GET"])
    r.add_api_route("/organism/spine/active", _spine_active, methods=["GET"])
    r.add_api_route("/organism/spine/completed", _spine_completed, methods=["GET"])
    r.add_api_route("/organism/spine/lifecycle/{envelope_id}", _spine_lifecycle, methods=["GET"])
    r.add_api_route("/organism/journal", _journal_status, methods=["GET"])
    r.add_api_route("/organism/journal/recent", _journal_recent, methods=["GET"])
    r.add_api_route("/organism/journal/lifecycle/{envelope_id}", _journal_lifecycle, methods=["GET"])
    r.add_api_route("/organism/journal/statistics", _journal_statistics, methods=["GET"])
    r.add_api_route("/organism/mutations", _mutation_registry, methods=["GET"])
    r.add_api_route("/organism/mutations/{mutation_name}", _mutation_detail, methods=["GET"])
    r.add_api_route("/organism/spine-guard", _spine_guard_status, methods=["GET"])
    r.add_api_route("/organism/spine-guard/blocked", _spine_guard_blocked, methods=["GET"])
    r.add_api_route("/organism/execution-doctrine", _execution_doctrine, methods=["GET"])
    r.add_api_route("/organism/reliability", _reliability_metrics, methods=["GET"])

    # ── Privileged endpoints (operator auth required) ──────────────────────

    r.add_api_route("/organism/spine/approve/{envelope_id}", _spine_approve, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/spine/reject/{envelope_id}", _spine_reject, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/spine/retry/{envelope_id}", _spine_retry, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/spine-guard/mode", _spine_guard_set_mode, methods=["POST"], dependencies=auth)

    return r


# ── GovernedExecutionSpine handlers ────────────────────────────────────────────


async def _spine_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.governed_spine.to_dict()


async def _spine_pending(limit: int = 50):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.pending_envelopes(limit)


async def _spine_active():
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.active_envelopes()


async def _spine_completed(limit: int = 50):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.completed_envelopes(limit)


async def _spine_lifecycle(envelope_id: str):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.governed_spine.envelope_lifecycle(envelope_id)


async def _spine_approve(envelope_id: str, request: Request):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)

    envelope = daemon.governed_spine.approve(envelope_id, approved_by=client_id)
    if envelope is None:
        return {"error": f"envelope {envelope_id} not found in pending queue"}
    logger.info("Spine envelope approved: %s by %s", envelope_id, client_id)
    return envelope.to_dict()


async def _spine_reject(envelope_id: str, payload: dict, request: Request):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)

    reason = str(payload.get("reason", "operator_rejected"))[:500]
    envelope = daemon.governed_spine.reject(envelope_id, reason=reason)
    if envelope is None:
        return {"error": f"envelope {envelope_id} not found in pending queue"}
    logger.info("Spine envelope rejected: %s by %s — %s", envelope_id, client_id, reason)
    return envelope.to_dict()


async def _spine_retry(envelope_id: str, request: Request):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    completed = daemon.governed_spine.completed_envelopes(500)
    target = None
    for env_dict in completed:
        if env_dict.get("envelope_id") == envelope_id:
            target = env_dict
            break

    if target is None:
        return {"error": f"envelope {envelope_id} not found in completed queue"}

    if target.get("status") not in ("failed", "verification_failed", "rolled_back"):
        return {"error": f"envelope {envelope_id} status is {target.get('status')} — only failed envelopes can be retried"}

    logger.info("Spine envelope retry requested: %s by %s", envelope_id, client_id)
    return {"acknowledged": True, "envelope_id": envelope_id, "note": "re-submit a new envelope for this action"}


# ── Execution Journal handlers ─────────────────────────────────────────────────


async def _journal_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.execution_journal.to_dict()


async def _journal_recent(limit: int = 50):
    daemon = _get_organism()
    if daemon is None:
        return []
    return [e.to_dict() for e in daemon.execution_journal.recent(limit)]


async def _journal_lifecycle(envelope_id: str):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.execution_journal.execution_lifecycle(envelope_id)


async def _journal_statistics():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.execution_journal.statistics()


# ── Mutation Registry handlers ─────────────────────────────────────────────────


async def _mutation_registry():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.mutation_registry.to_dict()


async def _mutation_detail(mutation_name: str):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    spec = daemon.mutation_registry.lookup(mutation_name)
    if spec is None:
        return {"error": f"mutation {mutation_name} not registered"}
    return spec.to_dict()


# ── SpineGuard handlers ───────────────────────────────────────────────────────


async def _spine_guard_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        **daemon.spine_guard.to_dict(),
        "recent_violations": daemon.spine_guard.recent_violations(),
    }


async def _spine_guard_blocked(limit: int = 20):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.spine_guard.blocked_violations(limit)


async def _spine_guard_set_mode(payload: dict, request: Request):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    from substrate.organism.spine_guard import GuardMode

    mode_str = str(payload.get("mode", "")).lower()
    valid_modes = {m.value: m for m in GuardMode}
    if mode_str not in valid_modes:
        return {
            "error": f"invalid mode: {mode_str}",
            "valid_modes": list(valid_modes.keys()),
        }

    new_mode = valid_modes[mode_str]
    old_mode = daemon.spine_guard.mode
    daemon.spine_guard.set_mode(new_mode)
    logger.info(
        "SpineGuard mode changed via cockpit: %s → %s by %s",
        old_mode.value, new_mode.value, client_id,
    )
    return {
        "old_mode": old_mode.value,
        "new_mode": new_mode.value,
        "changed_by": client_id,
    }


# ── Unified views ──────────────────────────────────────────────────────────────


async def _execution_doctrine():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    return {
        "execution_mode": daemon.execution_mode_manager.to_dict(),
        "spine": daemon.governed_spine.to_dict(),
        "spine_guard": daemon.spine_guard.to_dict(),
        "journal_statistics": daemon.execution_journal.statistics(),
        "mutation_registry": {
            "total_specs": len(daemon.mutation_registry.all_specs()),
            "by_risk": {
                risk: len(daemon.mutation_registry.specs_by_risk(risk))
                for risk in ("low", "medium", "high", "critical")
            },
        },
    }


async def _reliability_metrics():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    spine_stats = daemon.governed_spine.to_dict()
    journal_stats = daemon.execution_journal.statistics()

    return {
        "total_executed": spine_stats["total_executed"],
        "total_succeeded": spine_stats["total_succeeded"],
        "total_failed": spine_stats["total_failed"],
        "total_rejected": spine_stats["total_rejected"],
        "total_verified": spine_stats["total_verified"],
        "total_rolled_back": spine_stats["total_rolled_back"],
        "success_rate": spine_stats["success_rate"],
        "verification_rate": round(
            spine_stats["total_verified"] / max(spine_stats["total_succeeded"], 1), 4
        ),
        "rollback_rate": round(
            spine_stats["total_rolled_back"] / max(spine_stats["total_failed"], 1), 4
        ),
        "journal": journal_stats,
        "spine_guard": daemon.spine_guard.to_dict(),
    }
