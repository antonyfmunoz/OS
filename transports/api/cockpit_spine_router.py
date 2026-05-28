"""Cockpit spine router — GovernedExecutionSpine, Journal, MutationRegistry,
SpineGuard endpoints.

Extracted from cockpit.py (Phase 6.2) to keep the main cockpit under 3000 lines.
All routes are mounted under /api/umh/ via include_router in cockpit.py.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)

spine_router = APIRouter()

_get_organism: Callable[[], Any] = lambda: None
_check_rate_limit: Callable[[str, str], None] = lambda action, client_id: None
_require_operator_dep: Any = None


def configure(
    get_organism_fn: Callable[[], Any],
    check_rate_limit_fn: Callable[[str, str], None],
    require_operator_dep: Any,
) -> None:
    """Wire shared cockpit utilities into the spine router. Called once at mount time."""
    global _get_organism, _check_rate_limit, _require_operator_dep
    _get_organism = get_organism_fn
    _check_rate_limit = check_rate_limit_fn
    _require_operator_dep = require_operator_dep


def _operator_dep() -> list:
    if _require_operator_dep is not None:
        return [Depends(_require_operator_dep)]
    return []


# ── GovernedExecutionSpine endpoints ──────────────────────────────────────────


@spine_router.get("/organism/spine")
async def organism_spine_status():
    """GovernedExecutionSpine status: counters, success rate, queue depths."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.governed_spine.to_dict()


@spine_router.get("/organism/spine/pending")
async def organism_spine_pending(limit: int = 50):
    """Pending envelopes awaiting approval."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.pending_envelopes(limit)


@spine_router.get("/organism/spine/active")
async def organism_spine_active():
    """Currently executing envelopes."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.active_envelopes()


@spine_router.get("/organism/spine/completed")
async def organism_spine_completed(limit: int = 50):
    """Recently completed envelopes."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.completed_envelopes(limit)


@spine_router.get("/organism/spine/lifecycle/{envelope_id}")
async def organism_spine_lifecycle(envelope_id: str):
    """Full journal lifecycle for a specific envelope."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.governed_spine.envelope_lifecycle(envelope_id)


@spine_router.post("/organism/spine/approve/{envelope_id}")
async def organism_spine_approve(envelope_id: str, request: Request):
    """Approve a pending envelope for execution. Operator-auth required."""
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


@spine_router.post("/organism/spine/reject/{envelope_id}")
async def organism_spine_reject(envelope_id: str, payload: dict, request: Request):
    """Reject a pending envelope. Operator-auth required."""
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


@spine_router.post("/organism/spine/retry/{envelope_id}")
async def organism_spine_retry(envelope_id: str, request: Request):
    """Re-submit a failed envelope for execution. Operator-auth required."""
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


# ── Execution Journal endpoints ───────────────────────────────────────────────


@spine_router.get("/organism/journal")
async def organism_journal_status():
    """Execution journal statistics and recent entries."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.execution_journal.to_dict()


@spine_router.get("/organism/journal/recent")
async def organism_journal_recent(limit: int = 50):
    """Recent journal entries."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return [e.to_dict() for e in daemon.execution_journal.recent(limit)]


@spine_router.get("/organism/journal/lifecycle/{envelope_id}")
async def organism_journal_lifecycle(envelope_id: str):
    """Full journal lifecycle for a specific envelope."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.execution_journal.execution_lifecycle(envelope_id)


@spine_router.get("/organism/journal/statistics")
async def organism_journal_statistics():
    """Journal statistics: counts by phase, success rate, rollback/retry totals."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.execution_journal.statistics()


# ── Mutation Registry endpoints ───────────────────────────────────────────────


@spine_router.get("/organism/mutations")
async def organism_mutation_registry():
    """All registered mutation specs with risk profiles."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.mutation_registry.to_dict()


@spine_router.get("/organism/mutations/{mutation_name}")
async def organism_mutation_detail(mutation_name: str):
    """Detail for a specific mutation spec."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    spec = daemon.mutation_registry.lookup(mutation_name)
    if spec is None:
        return {"error": f"mutation {mutation_name} not registered"}
    return spec.to_dict()


# ── SpineGuard endpoints ─────────────────────────────────────────────────────


@spine_router.get("/organism/spine-guard")
async def organism_spine_guard():
    """Spine guard status, mode, counters, and recent violations."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        **daemon.spine_guard.to_dict(),
        "recent_violations": daemon.spine_guard.recent_violations(),
    }


@spine_router.get("/organism/spine-guard/blocked")
async def organism_spine_guard_blocked(limit: int = 20):
    """Recently blocked violations only."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.spine_guard.blocked_violations(limit)


@spine_router.post("/organism/spine-guard/mode")
async def organism_spine_guard_set_mode(payload: dict, request: Request):
    """Set SpineGuard enforcement mode. Operator-auth required.

    Valid modes: off, warn, block_high_risk, enforce_all
    """
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


# ── Execution Doctrine (unified control surface) ─────────────────────────────


@spine_router.get("/organism/execution-doctrine")
async def organism_execution_doctrine():
    """Unified view: execution mode + spine guard mode + spine stats + reliability."""
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


# ── Reliability metrics ──────────────────────────────────────────────────────


@spine_router.get("/organism/reliability")
async def organism_reliability_metrics():
    """Reliability metrics: success rate, verification rate, rollback stats."""
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
