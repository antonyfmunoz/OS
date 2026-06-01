"""Cockpit context assimilation routes — source registry, ingestion,
diagnostics, proposals, reconciliation, permissions, environment discovery,
and cross-source reconciliation.

All routes are mounted under /api/umh/ via include_router in cockpit.py.

Auth model: configure() must be called before include_router(). It receives
the real operator-auth dependency from cockpit.py and wires it into every
privileged route.

Phase 13.3. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

context_assimilation_router: APIRouter = APIRouter()

_require_operator: Any = None
_configured: bool = False


def configure(
    require_operator_dep: Any,
) -> None:
    global _require_operator, _configured, context_assimilation_router
    _require_operator = require_operator_dep
    _configured = True
    context_assimilation_router = _build_router(require_operator_dep)


def _get_engine():
    from substrate.organism.context_ingestion_engine import ContextIngestionEngine
    return ContextIngestionEngine()


def _get_diagnostic_engine():
    from substrate.organism.diagnostic_engine import DiagnosticEngine
    return DiagnosticEngine()


def _get_reconciliation_engine():
    from substrate.organism.reconciliation_engine import ReconciliationEngine
    return ReconciliationEngine()


def _get_dex_reconciliation():
    from substrate.organism.dex_reconciliation import DexReconciliation
    return DexReconciliation()


def _get_permission_engine():
    from substrate.organism.permission_dialogue import SocraticPermissionEngine
    return SocraticPermissionEngine()


def _get_env_store():
    from substrate.organism.environment_discovery import EnvironmentDiscoveryStore
    return EnvironmentDiscoveryStore()


def _get_cross_source():
    from substrate.organism.cross_source_reconciler import CrossSourceReconciler
    return CrossSourceReconciler()


def _get_sync_store():
    from substrate.organism.sync_policy import SyncPolicyStore
    return SyncPolicyStore()


def _get_proposal_store():
    from substrate.organism.canonical_update import ProposalStore
    return ProposalStore()


def _get_report_store():
    from substrate.organism.context_diagnostic import DiagnosticReportStore
    return DiagnosticReportStore()


def _get_session_store():
    from substrate.organism.reconciliation_session import ReconciliationSessionStore
    return ReconciliationSessionStore()


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Read-only endpoints ────────────────────────────────────────────

    r.add_api_route(
        "/organism/context-assimilation",
        _context_assimilation_overview,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/sources",
        _list_sources,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/jobs",
        _list_jobs,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/diagnostics",
        _list_diagnostics,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/diagnostics/{report_id}",
        _get_diagnostic,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/proposals",
        _list_proposals,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/proposals/{proposal_id}",
        _get_proposal,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/reconciliation-sessions",
        _list_sessions,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/reconciliation-sessions/{session_id}",
        _get_session,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/sync-policies",
        _list_sync_policies,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/permissions",
        _list_permissions,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/environment",
        _environment_overview,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/environment/devices",
        _list_devices,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/environment/apps",
        _list_apps,
        methods=["GET"],
    )
    r.add_api_route(
        "/organism/context-assimilation/cross-source-signals",
        _list_cross_source_signals,
        methods=["GET"],
    )

    # ── Privileged endpoints (operator auth required) ──────────────────

    r.add_api_route(
        "/organism/context-assimilation/ingest",
        _trigger_ingestion,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/context-assimilation/reconciliation-sessions/start",
        _start_reconciliation,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/context-assimilation/proposals/{proposal_id}/approve",
        _approve_proposal,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/context-assimilation/proposals/{proposal_id}/reject",
        _reject_proposal,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/context-assimilation/instantiation-diagnostic",
        _run_instantiation_diagnostic,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/context-assimilation/permissions/{request_id}/decide",
        _decide_permission,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/context-assimilation/permissions/{request_id}/revoke",
        _revoke_permission,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/context-assimilation/cross-source-signals/{signal_id}/confirm",
        _confirm_cross_source,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/context-assimilation/cross-source-signals/{signal_id}/reject",
        _reject_cross_source,
        methods=["POST"],
        dependencies=auth,
    )

    return r


# ── Handler implementations ────────────────────────────────────────────


async def _context_assimilation_overview():
    try:
        engine = _get_engine()
        diag_store = _get_report_store()
        prop_store = _get_proposal_store()
        sess_store = _get_session_store()
        perm_engine = _get_permission_engine()
        env_store = _get_env_store()
        cross_src = _get_cross_source()
        return {
            "sources": engine.registry.summary(),
            "ingestion": engine.summarize_ingestion(),
            "diagnostics": {"total": diag_store.count()},
            "proposals": {"total": prop_store.count(), "pending": prop_store.pending_count()},
            "sessions": {"total": sess_store.count()},
            "permissions": perm_engine.summary(),
            "environment": env_store.summary(),
            "cross_source": cross_src.summary(),
            "phase": "13.3",
            "external_writes_disabled": True,
            "no_canonical_update_without_approval": True,
        }
    except Exception as exc:
        logger.error("Context assimilation overview error: %s", exc)
        return {"error": "internal_error"}


async def _list_sources():
    try:
        engine = _get_engine()
        sources = engine.list_sources()
        return {"sources": [s.to_dict() for s in sources], "total": len(sources)}
    except Exception as exc:
        logger.error("List sources error: %s", exc)
        return {"error": "internal_error"}


async def _list_jobs():
    try:
        engine = _get_engine()
        jobs = engine.job_store.list_jobs()
        return {"jobs": [j.to_dict() for j in jobs], "total": len(jobs)}
    except Exception as exc:
        logger.error("List jobs error: %s", exc)
        return {"error": "internal_error"}


async def _list_diagnostics():
    try:
        store = _get_report_store()
        reports = store.list_reports()
        return {"diagnostics": [r.to_dict() for r in reports], "total": len(reports)}
    except Exception as exc:
        logger.error("List diagnostics error: %s", exc)
        return {"error": "internal_error"}


async def _get_diagnostic(report_id: str):
    try:
        store = _get_report_store()
        report = store.get_report(report_id)
        if not report:
            return {"error": "not_found"}
        return report.to_dict()
    except Exception as exc:
        logger.error("Get diagnostic error: %s", exc)
        return {"error": "internal_error"}


async def _list_proposals():
    try:
        store = _get_proposal_store()
        proposals = store.list_proposals()
        return {"proposals": [p.to_dict() for p in proposals], "total": len(proposals)}
    except Exception as exc:
        logger.error("List proposals error: %s", exc)
        return {"error": "internal_error"}


async def _get_proposal(proposal_id: str):
    try:
        store = _get_proposal_store()
        prop = store.get_proposal(proposal_id)
        if not prop:
            return {"error": "not_found"}
        return prop.to_dict()
    except Exception as exc:
        logger.error("Get proposal error: %s", exc)
        return {"error": "internal_error"}


async def _list_sessions():
    try:
        store = _get_session_store()
        sessions = store.list_sessions()
        return {"sessions": [s.to_dict() for s in sessions], "total": len(sessions)}
    except Exception as exc:
        logger.error("List sessions error: %s", exc)
        return {"error": "internal_error"}


async def _get_session(session_id: str):
    try:
        store = _get_session_store()
        session = store.get_session(session_id)
        if not session:
            return {"error": "not_found"}
        return session.to_dict()
    except Exception as exc:
        logger.error("Get session error: %s", exc)
        return {"error": "internal_error"}


async def _list_sync_policies():
    try:
        store = _get_sync_store()
        policies = store.list_policies()
        return {"policies": [p.to_dict() for p in policies], "total": len(policies)}
    except Exception as exc:
        logger.error("List sync policies error: %s", exc)
        return {"error": "internal_error"}


async def _list_permissions():
    try:
        engine = _get_permission_engine()
        requests = engine.list_requests()
        return {
            "permissions": [r.to_dict() for r in requests],
            "total": len(requests),
            "pending": engine.pending_count(),
            "summary": engine.summary(),
        }
    except Exception as exc:
        logger.error("List permissions error: %s", exc)
        return {"error": "internal_error"}


async def _environment_overview():
    try:
        store = _get_env_store()
        return {
            "summary": store.summary(),
            "devices": [d.to_dict() for d in store.list_devices()],
            "apps_count": len(store.list_apps()),
            "scopes_count": len(store.list_scopes()),
        }
    except Exception as exc:
        logger.error("Environment overview error: %s", exc)
        return {"error": "internal_error"}


async def _list_devices():
    try:
        store = _get_env_store()
        devices = store.list_devices()
        return {"devices": [d.to_dict() for d in devices], "total": len(devices)}
    except Exception as exc:
        logger.error("List devices error: %s", exc)
        return {"error": "internal_error"}


async def _list_apps():
    try:
        store = _get_env_store()
        apps = store.list_apps()
        return {"apps": [a.to_dict() for a in apps], "total": len(apps)}
    except Exception as exc:
        logger.error("List apps error: %s", exc)
        return {"error": "internal_error"}


async def _list_cross_source_signals():
    try:
        reconciler = _get_cross_source()
        signals = reconciler.list_signals()
        return {
            "signals": [s.to_dict() for s in signals],
            "total": len(signals),
            "actionable": len(reconciler.list_actionable()),
        }
    except Exception as exc:
        logger.error("List cross-source signals error: %s", exc)
        return {"error": "internal_error"}


async def _trigger_ingestion(request: Request):
    try:
        body = await request.json()
        source_id = body.get("source_id", "")
        job_type = body.get("job_type", "scan")
        engine = _get_engine()
        if not source_id:
            seeds = engine.seed_local_sources()
            return {"action": "seeded", "sources": [s.to_dict() for s in seeds]}
        if job_type == "audit":
            job = engine.run_local_audit_ingestion(source_id)
        elif job_type == "artifact":
            job = engine.run_local_artifact_ingestion(source_id)
        else:
            job = engine.run_metadata_scan(source_id)
        if not job:
            return {"error": "ingestion_failed"}
        return {"job": job.to_dict()}
    except Exception as exc:
        logger.error("Trigger ingestion error: %s", exc)
        return {"error": "internal_error"}


async def _start_reconciliation(request: Request):
    try:
        body = await request.json()
        topic = body.get("topic", "")
        scope = body.get("scope", "full")
        mode = body.get("mode", "exploration")
        if not topic:
            return {"error": "topic_required"}
        engine = _get_reconciliation_engine()
        session = engine.start_session(topic=topic, scope=scope, mode=mode)
        engine.attach_sources(session.session_id)
        return {"session": session.to_dict()}
    except Exception as exc:
        logger.error("Start reconciliation error: %s", exc)
        return {"error": "internal_error"}


async def _approve_proposal(proposal_id: str):
    try:
        store = _get_proposal_store()
        if not store.approve(proposal_id):
            return {"error": "not_found"}
        return {"status": "approved", "proposal_id": proposal_id}
    except Exception as exc:
        logger.error("Approve proposal error: %s", exc)
        return {"error": "internal_error"}


async def _reject_proposal(proposal_id: str):
    try:
        store = _get_proposal_store()
        if not store.reject(proposal_id):
            return {"error": "not_found"}
        return {"status": "rejected", "proposal_id": proposal_id}
    except Exception as exc:
        logger.error("Reject proposal error: %s", exc)
        return {"error": "internal_error"}


async def _run_instantiation_diagnostic():
    try:
        engine = _get_engine()
        engine.seed_local_sources()
        sources = engine.list_sources()
        for src in sources:
            if not engine.prevent_duplicate_ingestion(src.source_id):
                engine.run_local_audit_ingestion(src.source_id)
        diag = _get_diagnostic_engine()
        report = diag.build_diagnostic_report(scope="instantiation")
        return {
            "report": report.to_dict(),
            "sources_analyzed": len(sources),
            "external_writes_disabled": True,
        }
    except Exception as exc:
        logger.error("Instantiation diagnostic error: %s", exc)
        return {"error": "internal_error"}


async def _decide_permission(request_id: str, request: Request):
    try:
        body = await request.json()
        choice = body.get("choice", "")
        remember = body.get("remember", False)
        engine = _get_permission_engine()
        if not engine.decide(request_id, choice, remember=remember):
            return {"error": "invalid_request_or_choice"}
        return {"status": "decided", "request_id": request_id, "choice": choice}
    except Exception as exc:
        logger.error("Decide permission error: %s", exc)
        return {"error": "internal_error"}


async def _revoke_permission(request_id: str):
    try:
        engine = _get_permission_engine()
        if not engine.revoke(request_id):
            return {"error": "not_found"}
        return {"status": "revoked", "request_id": request_id}
    except Exception as exc:
        logger.error("Revoke permission error: %s", exc)
        return {"error": "internal_error"}


async def _confirm_cross_source(signal_id: str):
    try:
        reconciler = _get_cross_source()
        if not reconciler.confirm_signal(signal_id):
            return {"error": "not_found_or_permission_denied"}
        return {"status": "confirmed", "signal_id": signal_id}
    except Exception as exc:
        logger.error("Confirm cross-source error: %s", exc)
        return {"error": "internal_error"}


async def _reject_cross_source(signal_id: str):
    try:
        reconciler = _get_cross_source()
        if not reconciler.reject_signal(signal_id):
            return {"error": "not_found"}
        return {"status": "rejected", "signal_id": signal_id}
    except Exception as exc:
        logger.error("Reject cross-source error: %s", exc)
        return {"error": "internal_error"}
