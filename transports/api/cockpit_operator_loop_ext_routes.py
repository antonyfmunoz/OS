"""Cockpit operator loop extension routes — Phases 5-8.

Phase 5: Strategic Tick Loop
Phase 6: Projection Engine
Phase 7: Continuity Runtime
Phase 8: Presence Runtime

Split from cockpit_operator_loop_routes.py for the 3,000-line limit.
Mounted under /api/umh/ via include_router in cockpit.py.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

operator_loop_ext_router: APIRouter = APIRouter()

_configured: bool = False

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _audit_log(event_type: str, data: dict[str, Any]) -> None:
    """Append to JSONL audit trail."""
    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    entry = {
        "id": str(uuid4()),
        "event_type": event_type,
        "timestamp": time.time(),
        "data": data,
    }
    try:
        with open(audit_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.debug("audit log write failed: %s", e)


def configure(require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    operator_loop_ext_router.include_router(
        _build_router(require_operator_dep), tags=["operator-loop-ext"]
    )


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Phase 5: Strategic Tick Loop routes ────────────────────
    r.add_api_route("/tick/status", _tick_status, methods=["GET"], dependencies=auth)
    r.add_api_route("/tick/state", _tick_strategic_state, methods=["GET"], dependencies=auth)
    r.add_api_route("/tick/execute", _tick_execute, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/start", _tick_start, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/stop", _tick_stop, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/pause", _tick_pause, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/resume", _tick_resume, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/frequency", _tick_set_frequency, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/profiles", _tick_set_profiles, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/candidates", _tick_candidates, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/tick/candidates/{candidate_id}/accept",
        _tick_accept_candidate,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/tick/candidates/{candidate_id}/reject",
        _tick_reject_candidate,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route("/tick/drift", _tick_drift_warnings, methods=["GET"], dependencies=auth)
    r.add_api_route("/tick/history", _tick_history, methods=["GET"], dependencies=auth)

    # ── Phase 6: Projection Engine routes ─────────────────────
    r.add_api_route("/projection/status", _projection_status, methods=["GET"], dependencies=auth)
    r.add_api_route("/projection/state", _projection_state, methods=["GET"], dependencies=auth)
    r.add_api_route("/projection/run", _projection_run, methods=["POST"], dependencies=auth)
    r.add_api_route("/projection/trends", _projection_trends, methods=["GET"], dependencies=auth)
    r.add_api_route("/projection/risks", _projection_risks, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/projection/opportunities", _projection_opportunities, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/projection/accuracy", _projection_accuracy, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/projection/domain/{domain}", _projection_by_domain, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/projection/projected-reality",
        _projection_projected_reality,
        methods=["GET"],
        dependencies=auth,
    )
    r.add_api_route(
        "/projection/outcome", _projection_record_outcome, methods=["POST"], dependencies=auth
    )

    # ── Phase 7: Continuity Runtime routes ────────────────────
    r.add_api_route("/continuity/status", _continuity_status, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/continuity/snapshot", _continuity_snapshot, methods=["GET"], dependencies=auth
    )
    r.add_api_route("/continuity/capture", _continuity_capture, methods=["POST"], dependencies=auth)
    r.add_api_route("/continuity/depart", _continuity_depart, methods=["POST"], dependencies=auth)
    r.add_api_route("/continuity/resume", _continuity_resume, methods=["POST"], dependencies=auth)
    r.add_api_route("/continuity/brief", _continuity_brief, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/continuity/generate-brief",
        _continuity_generate_brief,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/continuity/timeline", _continuity_timeline, methods=["GET"], dependencies=auth
    )
    r.add_api_route("/continuity/lineage", _continuity_lineage, methods=["GET"], dependencies=auth)
    r.add_api_route("/continuity/handoff", _continuity_handoff, methods=["POST"], dependencies=auth)
    r.add_api_route(
        "/continuity/interaction", _continuity_interaction, methods=["POST"], dependencies=auth
    )

    # ── Phase 8: Presence Runtime routes ─────────────────────
    r.add_api_route("/presence/status", _presence_status, methods=["GET"], dependencies=auth)
    r.add_api_route("/presence/snapshot", _presence_snapshot, methods=["GET"], dependencies=auth)
    r.add_api_route("/presence/capture", _presence_capture, methods=["POST"], dependencies=auth)
    r.add_api_route("/presence/devices", _presence_devices, methods=["GET"], dependencies=auth)
    r.add_api_route("/presence/sessions", _presence_sessions, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/presence/session/register",
        _presence_register_session,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/presence/session/end", _presence_end_session, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/presence/session/heartbeat", _presence_heartbeat, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/presence/interaction", _presence_interaction, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/presence/profile", _presence_change_profile, methods=["POST"], dependencies=auth
    )
    r.add_api_route("/presence/attention", _presence_attention, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/presence/interruption", _presence_interruption, methods=["GET"], dependencies=auth
    )
    r.add_api_route("/presence/timeline", _presence_timeline, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/presence/history", _presence_session_history, methods=["GET"], dependencies=auth
    )

    return r


# ── Phase 5: Strategic Tick Loop helpers & handlers ────────────────


def _get_tick_loop():
    from substrate.organism.strategic_tick_loop import get_tick_loop

    return get_tick_loop()


def _tick_status(request: Request) -> dict:
    """Compact tick loop status."""
    try:
        loop = _get_tick_loop()
        return {"success": True, **loop.status()}
    except Exception as exc:
        logger.error("tick status failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _tick_strategic_state(request: Request) -> dict:
    """Full strategic state for cockpit command center."""
    try:
        loop = _get_tick_loop()
        return {"success": True, **loop.get_strategic_state()}
    except Exception as exc:
        logger.error("tick strategic state failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _tick_execute(request: Request) -> dict:
    """Execute one tick cycle manually."""
    tick_data = {}

    def _do_execute():
        loop = _get_tick_loop()
        record = loop.execute_tick()
        _audit_log(
            "tick_executed",
            {
                "tick_id": record.tick_id,
                "change_detected": record.change_detected,
                "analysis_ran": record.analysis_ran,
                "gaps_found": record.gaps_found,
            },
        )
        tick_data["tick"] = record.to_dict()
        return f"tick {record.tick_id} executed", True

    resp = governed_mutation(
        mutation_name="operator_loop_control",
        intent="execute tick cycle",
        execute_fn=_do_execute,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(tick_data)
    return result


async def _tick_start(request: Request) -> dict:
    """Start the tick loop."""
    body = await request.json()
    freq = body.get("frequency", "")
    tick_status = {}

    def _do_start():
        loop = _get_tick_loop()
        if freq:
            from substrate.organism.strategic_tick_loop import TickFrequency
            loop.frequency = TickFrequency(freq)
        loop.start()
        _audit_log("tick_started", {"frequency": loop.frequency.value})
        tick_status["status"] = loop.status()
        return "tick loop started", True

    resp = governed_mutation(
        mutation_name="operator_loop_control",
        intent="start tick loop",
        execute_fn=_do_start,
        source="cockpit",
        metadata={"frequency": freq} if freq else {},
    )
    result = resp.to_http_dict()
    result.update(tick_status)
    return result


def _tick_stop(request: Request) -> dict:
    """Stop the tick loop."""
    tick_status = {}

    def _do_stop():
        loop = _get_tick_loop()
        loop.stop()
        _audit_log("tick_stopped", {"cycle_count": loop.cycle_count})
        tick_status["status"] = loop.status()
        return "tick loop stopped", True

    resp = governed_mutation(
        mutation_name="operator_loop_control",
        intent="stop tick loop",
        execute_fn=_do_stop,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(tick_status)
    return result


def _tick_pause(request: Request) -> dict:
    """Pause the tick loop (maintains state)."""
    tick_status = {}

    def _do_pause():
        loop = _get_tick_loop()
        loop.pause()
        _audit_log("tick_paused", {"cycle_count": loop.cycle_count})
        tick_status["status"] = loop.status()
        return "tick loop paused", True

    resp = governed_mutation(
        mutation_name="operator_loop_control",
        intent="pause tick loop",
        execute_fn=_do_pause,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(tick_status)
    return result


def _tick_resume(request: Request) -> dict:
    """Resume the tick loop from paused state."""
    tick_status = {}

    def _do_resume():
        loop = _get_tick_loop()
        loop.resume()
        _audit_log("tick_resumed", {"cycle_count": loop.cycle_count})
        tick_status["status"] = loop.status()
        return "tick loop resumed", True

    resp = governed_mutation(
        mutation_name="operator_loop_control",
        intent="resume tick loop",
        execute_fn=_do_resume,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(tick_status)
    return result


async def _tick_set_frequency(request: Request) -> dict:
    """Set tick frequency."""
    body = await request.json()
    freq = body.get("frequency", "1m")
    tick_status = {}

    def _do_set_freq():
        from substrate.organism.strategic_tick_loop import TickFrequency
        loop = _get_tick_loop()
        loop.frequency = TickFrequency(freq)
        _audit_log("tick_frequency_changed", {"frequency": freq})
        tick_status["frequency"] = freq
        tick_status["status"] = loop.status()
        return f"tick frequency set to {freq}", True

    resp = governed_mutation(
        mutation_name="operator_loop_control",
        intent=f"set tick frequency to {freq}",
        execute_fn=_do_set_freq,
        source="cockpit",
        metadata={"frequency": freq},
    )
    result = resp.to_http_dict()
    result.update(tick_status)
    return result


async def _tick_set_profiles(request: Request) -> dict:
    """Set active profile modes for prioritization."""
    body = await request.json()
    profiles = body.get("profiles", [])

    def _do_set_profiles():
        loop = _get_tick_loop()
        loop.set_active_profiles(profiles)
        _audit_log("tick_profiles_set", {"profiles": profiles})
        return f"profiles set: {profiles}", True

    resp = governed_mutation(
        mutation_name="profile_mutate",
        intent=f"set tick profiles: {profiles}",
        execute_fn=_do_set_profiles,
        source="cockpit",
        metadata={"profiles": profiles},
    )
    result = resp.to_http_dict()
    if resp.success:
        result["profiles"] = profiles
    return result


def _tick_candidates(request: Request) -> dict:
    """Return candidate work queue."""
    try:
        loop = _get_tick_loop()
        pending = loop.candidate_queue.pending()
        all_items = loop.candidate_queue.all_items()
        return {
            "success": True,
            "pending": [i.to_dict() for i in pending],
            "pending_count": len(pending),
            "total": len(all_items),
            "all": [i.to_dict() for i in all_items],
        }
    except Exception as exc:
        logger.error("tick candidates failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _tick_accept_candidate(request: Request) -> dict:
    """Accept a candidate → transitions to ACCEPTED lifecycle."""
    candidate_id = request.path_params.get("candidate_id", "")

    def _do_accept():
        from substrate.organism.strategic_tick_loop import RecommendationLifecycle
        loop = _get_tick_loop()
        ok = loop.candidate_queue.update_lifecycle(
            candidate_id, RecommendationLifecycle.ACCEPTED
        )
        if ok:
            _audit_log("tick_candidate_accepted", {"candidate_id": candidate_id})
        return f"candidate {candidate_id} accepted", ok

    resp = governed_mutation(
        mutation_name="tick_candidate_decide",
        intent=f"accept candidate {candidate_id}",
        execute_fn=_do_accept,
        source="cockpit",
        metadata={"candidate_id": candidate_id},
    )
    return resp.to_http_dict()


def _tick_reject_candidate(request: Request) -> dict:
    """Reject a candidate → transitions to REJECTED lifecycle."""
    candidate_id = request.path_params.get("candidate_id", "")

    def _do_reject():
        from substrate.organism.strategic_tick_loop import RecommendationLifecycle
        loop = _get_tick_loop()
        ok = loop.candidate_queue.update_lifecycle(
            candidate_id, RecommendationLifecycle.REJECTED
        )
        if ok:
            _audit_log("tick_candidate_rejected", {"candidate_id": candidate_id})
        return f"candidate {candidate_id} rejected", ok

    resp = governed_mutation(
        mutation_name="tick_candidate_decide",
        intent=f"reject candidate {candidate_id}",
        execute_fn=_do_reject,
        source="cockpit",
        metadata={"candidate_id": candidate_id},
    )
    return resp.to_http_dict()


def _tick_drift_warnings(request: Request) -> dict:
    """Return current drift warnings."""
    try:
        loop = _get_tick_loop()
        warnings = loop.last_drift_warnings
        return {
            "success": True,
            "warnings": [w.to_dict() for w in warnings],
            "count": len(warnings),
        }
    except Exception as exc:
        logger.error("tick drift warnings failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _tick_history(request: Request) -> dict:
    """Return recent tick history."""
    try:
        loop = _get_tick_loop()
        history = loop.tick_history
        return {
            "success": True,
            "ticks": [t.to_dict() for t in history[-20:]],
            "count": len(history),
        }
    except Exception as exc:
        logger.error("tick history failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ── Phase 6: Projection Engine helpers & handlers ──────────────────


def _get_projection_engine():
    from substrate.organism.projection_engine import get_projection_engine

    return get_projection_engine()


def _projection_status(request: Request) -> dict:
    """Compact projection engine status."""
    try:
        engine = _get_projection_engine()
        return {"success": True, **engine.status()}
    except Exception as exc:
        logger.error("projection status failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _projection_state(request: Request) -> dict:
    """Full projection state for cockpit."""
    try:
        engine = _get_projection_engine()
        return {"success": True, **engine.get_projection_state()}
    except Exception as exc:
        logger.error("projection state failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _projection_run(request: Request) -> dict:
    """Run full projection cycle."""
    try:
        body = (
            await request.json()
            if request.headers.get("content-type") == "application/json"
            else {}
        )
    except Exception:
        body = {}

    horizons_raw = body.get("horizons")
    domains = body.get("domains")

    horizons = None
    if horizons_raw:
        from substrate.organism.projection_engine import TimeHorizon

        try:
            horizons = [TimeHorizon(h) for h in horizons_raw]
        except (ValueError, KeyError):
            pass

    proj_result = {}

    def _do_run():
        engine = _get_projection_engine()
        r = engine.run_projections(horizons=horizons, domains=domains)
        _audit_log(
            "projection_run",
            {
                "run_number": r.get("run_number"),
                "projection_count": r.get("projection_count"),
                "risk_count": r.get("risk_count"),
                "opportunity_count": r.get("opportunity_count"),
            },
        )
        proj_result.update(r)
        return f"projection run {r.get('run_number', '?')} complete", True

    resp = governed_mutation(
        mutation_name="projection_event",
        intent="run projection cycle",
        execute_fn=_do_run,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(proj_result)
    return result


def _projection_trends(request: Request) -> dict:
    """Return detected trends."""
    try:
        engine = _get_projection_engine()
        return {
            "success": True,
            "trends": [t.to_dict() for t in engine.last_trends],
            "count": len(engine.last_trends),
        }
    except Exception as exc:
        logger.error("projection trends failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _projection_risks(request: Request) -> dict:
    """Return strategic risks."""
    try:
        engine = _get_projection_engine()
        return {
            "success": True,
            "risks": [r.to_dict() for r in engine.last_risks],
            "count": len(engine.last_risks),
        }
    except Exception as exc:
        logger.error("projection risks failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _projection_opportunities(request: Request) -> dict:
    """Return strategic opportunities."""
    try:
        engine = _get_projection_engine()
        return {
            "success": True,
            "opportunities": [o.to_dict() for o in engine.last_opportunities],
            "count": len(engine.last_opportunities),
        }
    except Exception as exc:
        logger.error("projection opportunities failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _projection_accuracy(request: Request) -> dict:
    """Return projection accuracy metrics."""
    try:
        engine = _get_projection_engine()
        return {"success": True, **engine.accuracy_tracker.overall_accuracy()}
    except Exception as exc:
        logger.error("projection accuracy failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _projection_by_domain(request: Request) -> dict:
    """Return projections for a specific domain."""
    domain = request.path_params.get("domain", "")
    if not domain:
        return {"success": False, "error": "domain required"}
    try:
        engine = _get_projection_engine()
        projections = engine.get_projections_for_domain(domain)
        return {
            "success": True,
            "domain": domain,
            "projections": [p.to_dict() for p in projections],
            "count": len(projections),
        }
    except Exception as exc:
        logger.error("projection by domain failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _projection_projected_reality(request: Request) -> dict:
    """Return projected reality for gap analysis integration."""
    try:
        from substrate.organism.projection_engine import TimeHorizon

        horizon_str = request.query_params.get("horizon", "7d")
        try:
            horizon = TimeHorizon(horizon_str)
        except (ValueError, KeyError):
            horizon = TimeHorizon.WEEK

        engine = _get_projection_engine()
        projected = engine.get_projected_reality(horizon)
        return {"success": True, **projected}
    except Exception as exc:
        logger.error("projection projected reality failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _projection_record_outcome(request: Request) -> dict:
    """Record a projection outcome for accuracy tracking."""
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "invalid JSON body"}

    projection_id = body.get("projection_id", "")
    actual_state = body.get("actual_state", "")
    was_accurate = body.get("was_accurate", False)
    accuracy_score = body.get("accuracy_score", 0.0)

    if not projection_id:
        return {"success": False, "error": "projection_id required"}

    outcome_data = {}

    def _do_record():
        engine = _get_projection_engine()
        r = engine.record_outcome(projection_id, actual_state, was_accurate, accuracy_score)
        outcome_data.update(r)
        if r.get("success"):
            _audit_log(
                "projection_outcome_recorded",
                {"projection_id": projection_id, "was_accurate": was_accurate},
            )
        return f"projection outcome for {projection_id} recorded", r.get("success", False)

    resp = governed_mutation(
        mutation_name="outcome_record",
        intent=f"record projection outcome for {projection_id}",
        execute_fn=_do_record,
        source="cockpit",
        metadata={"projection_id": projection_id},
    )
    result = resp.to_http_dict()
    result.update(outcome_data)
    return result


# ── Phase 7: Continuity Runtime helpers & handlers ─────────────────────


def _get_continuity_runtime():
    from substrate.organism.continuity_runtime import get_continuity_runtime

    return get_continuity_runtime()


def _continuity_status(request: Request) -> dict:
    try:
        rt = _get_continuity_runtime()
        return {"success": True, **rt.status()}
    except Exception as exc:
        logger.error("continuity status failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _continuity_snapshot(request: Request) -> dict:
    try:
        rt = _get_continuity_runtime()
        snap = rt.get_snapshot()
        return {"success": True, "snapshot": snap}
    except Exception as exc:
        logger.error("continuity snapshot failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _continuity_capture(request: Request) -> dict:
    snap_data = {}

    def _do_capture():
        rt = _get_continuity_runtime()
        snap = rt.capture_snapshot()
        _audit_log("continuity_snapshot_captured", {"snapshot_id": snap.snapshot_id})
        snap_data["snapshot"] = snap.to_dict()
        return f"snapshot {snap.snapshot_id} captured", True

    resp = governed_mutation(
        mutation_name="continuity_mutate",
        intent="capture continuity snapshot",
        execute_fn=_do_capture,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(snap_data)
    return result


def _continuity_depart(request: Request) -> dict:
    snap_data = {}

    def _do_depart():
        rt = _get_continuity_runtime()
        snap = rt.record_departure()
        _audit_log("continuity_departure_recorded", {"snapshot_id": snap.snapshot_id})
        snap_data["snapshot"] = snap.to_dict()
        return f"departure recorded {snap.snapshot_id}", True

    resp = governed_mutation(
        mutation_name="continuity_mutate",
        intent="record departure",
        execute_fn=_do_depart,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(snap_data)
    return result


def _continuity_resume(request: Request) -> dict:
    resume_data = {}

    def _do_resume():
        rt = _get_continuity_runtime()
        report = rt.generate_resume()
        _audit_log(
            "continuity_resume_generated",
            {"total_changes": report.total_changes, "absence_seconds": report.absence_duration_seconds},
        )
        resume_data["report"] = report.to_dict()
        return "resume generated", True

    resp = governed_mutation(
        mutation_name="continuity_mutate",
        intent="generate resume report",
        execute_fn=_do_resume,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(resume_data)
    return result


def _continuity_brief(request: Request) -> dict:
    try:
        rt = _get_continuity_runtime()
        brief = rt.get_last_brief()
        return {"success": True, "brief": brief}
    except Exception as exc:
        logger.error("continuity brief failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _continuity_generate_brief(request: Request) -> dict:
    brief_data = {}

    def _do_brief():
        rt = _get_continuity_runtime()
        brief = rt.generate_brief(include_resume=False)
        _audit_log("continuity_brief_generated", {"brief_id": brief.brief_id})
        brief_data["brief"] = brief.to_dict()
        return f"brief {brief.brief_id} generated", True

    resp = governed_mutation(
        mutation_name="continuity_mutate",
        intent="generate continuity brief",
        execute_fn=_do_brief,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(brief_data)
    return result


def _continuity_timeline(request: Request) -> dict:
    try:
        rt = _get_continuity_runtime()
        since = float(request.query_params.get("since", "0"))
        event_type = request.query_params.get("type")
        limit = int(request.query_params.get("limit", "50"))
        events = rt.get_timeline(since=since, event_type=event_type, limit=limit)
        return {"success": True, "events": events}
    except Exception as exc:
        logger.error("continuity timeline failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _continuity_lineage(request: Request) -> dict:
    try:
        rt = _get_continuity_runtime()
        lineages = rt.build_lineage()
        return {"success": True, "lineages": [l.to_dict() for l in lineages]}
    except Exception as exc:
        logger.error("continuity lineage failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _continuity_handoff(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "invalid JSON body"}

    from_session = body.get("from_session_id", "")
    to_session = body.get("to_session_id", "")
    if not from_session or not to_session:
        return {"success": False, "error": "from_session_id and to_session_id required"}

    handoff_data = {}

    def _do_handoff():
        rt = _get_continuity_runtime()
        handoff = rt.record_session_handoff(
            from_session, to_session,
            body.get("from_profile", ""), body.get("to_profile", ""),
        )
        _audit_log(
            "continuity_handoff",
            {"from": from_session, "to": to_session, "handoff_id": handoff.handoff_id},
        )
        handoff_data["handoff"] = handoff.to_dict()
        return f"handoff {handoff.handoff_id} recorded", True

    resp = governed_mutation(
        mutation_name="continuity_mutate",
        intent=f"handoff from {from_session} to {to_session}",
        execute_fn=_do_handoff,
        source="cockpit",
        metadata={"from": from_session, "to": to_session},
    )
    result = resp.to_http_dict()
    result.update(handoff_data)
    return result


def _continuity_interaction(request: Request) -> dict:
    def _do_interact():
        rt = _get_continuity_runtime()
        rt.record_interaction()
        return "interaction recorded", True

    resp = governed_mutation(
        mutation_name="continuity_mutate",
        intent="record continuity interaction",
        execute_fn=_do_interact,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Phase 8: Presence Runtime handlers ────────────────────────────────


def _get_presence_runtime():
    from substrate.organism.presence_runtime import get_presence_runtime

    return get_presence_runtime()


def _presence_status(request: Request) -> dict:
    try:
        rt = _get_presence_runtime()
        return {"success": True, **rt.get_status()}
    except Exception as exc:
        logger.error("presence status failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _presence_snapshot(request: Request) -> dict:
    try:
        rt = _get_presence_runtime()
        snap = rt.get_snapshot()
        return {"success": True, "snapshot": snap}
    except Exception as exc:
        logger.error("presence snapshot failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _presence_capture(request: Request) -> dict:
    snap_data = {}

    def _do_capture():
        rt = _get_presence_runtime()
        snap = rt.capture_snapshot()
        _audit_log("presence_snapshot_captured", {"snapshot_id": snap.snapshot_id})
        snap_data["snapshot"] = snap.to_dict()
        return f"presence snapshot {snap.snapshot_id}", True

    resp = governed_mutation(
        mutation_name="presence_update",
        intent="capture presence snapshot",
        execute_fn=_do_capture,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(snap_data)
    return result


def _presence_devices(request: Request) -> dict:
    try:
        rt = _get_presence_runtime()
        return {"success": True, "devices": rt.get_devices()}
    except Exception as exc:
        logger.error("presence devices failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _presence_sessions(request: Request) -> dict:
    try:
        rt = _get_presence_runtime()
        return {"success": True, "sessions": rt.get_active_sessions()}
    except Exception as exc:
        logger.error("presence sessions failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _presence_register_session(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "invalid JSON body"}

    session_id = body.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id required"}

    session_data = {}

    def _do_register():
        rt = _get_presence_runtime()
        session = rt.register_session(
            session_id=session_id, host=body.get("host", ""),
            device_id=body.get("device_id", ""), profile_mode=body.get("profile_mode", ""),
            client_type=body.get("client_type", ""), control_surface=body.get("control_surface", ""),
            interaction_surface=body.get("interaction_surface", "none"),
        )
        _audit_log("presence_session_registered", {"session_id": session_id, "device_id": body.get("device_id", "")})
        session_data["session"] = session.to_dict()
        return f"session {session_id} registered", True

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"register presence session {session_id}",
        execute_fn=_do_register,
        source="cockpit",
        metadata={"session_id": session_id},
    )
    result = resp.to_http_dict()
    result.update(session_data)
    return result


async def _presence_end_session(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "invalid JSON body"}

    session_id = body.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id required"}

    session_data = {}

    def _do_end():
        rt = _get_presence_runtime()
        session = rt.end_session(session_id)
        _audit_log("presence_session_ended", {"session_id": session_id})
        session_data["session"] = session.to_dict() if session else None
        return f"session {session_id} ended", True

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"end presence session {session_id}",
        execute_fn=_do_end,
        source="cockpit",
        metadata={"session_id": session_id},
    )
    result = resp.to_http_dict()
    result.update(session_data)
    return result


async def _presence_heartbeat(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "invalid JSON body"}

    session_id = body.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id required"}

    def _do_heartbeat():
        rt = _get_presence_runtime()
        ok = rt.heartbeat(session_id, body.get("updates"))
        return f"heartbeat {session_id}", ok

    resp = governed_mutation(
        mutation_name="presence_update",
        intent=f"heartbeat session {session_id}",
        execute_fn=_do_heartbeat,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result["found"] = resp.success
    return result


async def _presence_interaction(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        body = {}

    interaction_data = {}

    def _do_interact():
        rt = _get_presence_runtime()
        r = rt.record_interaction(body.get("profile_mode", ""))
        interaction_data["attention"] = r
        return "interaction recorded", True

    resp = governed_mutation(
        mutation_name="presence_update",
        intent="record presence interaction",
        execute_fn=_do_interact,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(interaction_data)
    return result


async def _presence_change_profile(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "invalid JSON body"}

    profile = body.get("profile_mode", "")
    if not profile:
        return {"success": False, "error": "profile_mode required"}

    profile_data = {}

    def _do_change():
        rt = _get_presence_runtime()
        r = rt.change_profile(profile)
        _audit_log("presence_profile_changed", {"profile_mode": profile})
        profile_data.update(r)
        return f"profile changed to {profile}", True

    resp = governed_mutation(
        mutation_name="profile_mutate",
        intent=f"change presence profile to {profile}",
        execute_fn=_do_change,
        source="cockpit",
        metadata={"profile_mode": profile},
    )
    result = resp.to_http_dict()
    result.update(profile_data)
    return result


def _presence_attention(request: Request) -> dict:
    try:
        rt = _get_presence_runtime()
        return {"success": True, "attention": rt.get_attention_state()}
    except Exception as exc:
        logger.error("presence attention failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _presence_interruption(request: Request) -> dict:
    try:
        rt = _get_presence_runtime()
        is_critical = request.query_params.get("critical", "false").lower() == "true"
        return {
            "success": True,
            "interruption_level": rt.get_interruption_level(),
            "should_interrupt": rt.should_interrupt(is_critical),
            "recommendation_filter": rt.get_recommendation_filter(),
        }
    except Exception as exc:
        logger.error("presence interruption failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _presence_timeline(request: Request) -> dict:
    try:
        rt = _get_presence_runtime()
        since = float(request.query_params.get("since", "0"))
        event_type = request.query_params.get("type")
        limit = int(request.query_params.get("limit", "50"))
        events = rt.get_timeline(since=since, event_type=event_type, limit=limit)
        return {"success": True, "events": events}
    except Exception as exc:
        logger.error("presence timeline failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _presence_session_history(request: Request) -> dict:
    try:
        rt = _get_presence_runtime()
        return {"success": True, "history": rt.get_session_history()}
    except Exception as exc:
        logger.error("presence session history failed: %s", exc)
        return {"success": False, "error": str(exc)}
